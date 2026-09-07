"""ComfyUI graph transformation for the repair pass: a masked local redraw.

Crop the masked region, resample it in place with the source's own model,
LoRA and prompts, and stitch it back -- instead of the redraw+matte+deliver
chain `refinement_graph.chain_pass` builds, which redraws the whole canvas.
"""

from __future__ import annotations

import itertools
import json
from collections.abc import Callable, Mapping

# Reused from refinement_graph's own delivery tail, so a source graph that
# already carries a matte/delivered pair keeps the same suffix convention.
MATTE_SUFFIX = "-matte"
DELIVERED_SUFFIX = "-delivered"

_INPAINT_CROP_DEFAULTS = {
    "downscale_algorithm": "lanczos",
    "upscale_algorithm": "lanczos",
    "preresize": False,
    "preresize_mode": "ensure minimum resolution",
    "preresize_min_width": 1024,
    "preresize_min_height": 1024,
    "preresize_max_width": 16384,
    "preresize_max_height": 16384,
    "mask_fill_holes": True,
    "mask_expand_pixels": 0,
    "mask_invert": False,
    "mask_blend_pixels": 32,
    "mask_hipass_filter": 0.1,
    "extend_for_outpainting": False,
    "extend_up_factor": 1.0,
    "extend_down_factor": 1.0,
    "extend_left_factor": 1.0,
    "extend_right_factor": 1.0,
    "context_from_mask_extend_factor": 1.5,
    "output_resize_to_target_size": True,
    "output_padding": "32",
    "device_mode": "gpu (much faster)",
}


def _is_ref(value: object) -> bool:
    return isinstance(value, list) and len(value) == 2


def _consumers(graph: Mapping) -> dict[str, list[str]]:
    consumers: dict[str, list[str]] = {key: [] for key in graph}
    for key, node in graph.items():
        for value in node.get("inputs", {}).values():
            if _is_ref(value) and value[0] in graph:
                consumers[value[0]].append(key)
    return consumers


def _reaches(graph: Mapping, consumers: Mapping[str, list[str]], start: str,
            class_type: str) -> bool:
    stack = list(consumers.get(start, []))
    seen: set[str] = set()
    while stack:
        node_id = stack.pop()
        if node_id in seen:
            continue
        seen.add(node_id)
        if graph[node_id].get("class_type") == class_type:
            return True
        stack.extend(consumers.get(node_id, []))
    return False


def _find_decode(graph: Mapping) -> str:
    """The one VAEDecode that is the source's finished picture.

    A base graph can carry a dangling first-pass VAEDecode (no consumer) and
    a redraw VAEDecode that a later pass re-encodes -- neither is it.
    """
    consumers = _consumers(graph)
    candidates = [
        key for key, node in graph.items()
        if node.get("class_type") == "VAEDecode" and consumers.get(key)
        and not _reaches(graph, consumers, key, "VAEEncode")]
    if len(candidates) != 1:
        raise ValueError(
            "expected exactly one final VAEDecode reachable without a "
            f"re-sample, found {len(candidates)}: {sorted(candidates)}")
    return candidates[0]


def _find_sampler(graph: Mapping, decode_id: str) -> str:
    """The KSampler feeding `decode_id`, through any Latent*/SetLatentNoiseMask hop."""
    node_id = graph[decode_id]["inputs"]["samples"][0]
    seen: set[str] = set()
    while graph[node_id].get("class_type") != "KSampler":
        if node_id in seen:
            raise ValueError(
                f"could not trace a KSampler upstream of VAEDecode {decode_id!r}")
        seen.add(node_id)
        inputs = graph[node_id].get("inputs", {})
        if "samples" not in inputs:
            raise ValueError(
                f"could not trace a KSampler upstream of VAEDecode {decode_id!r}")
        node_id = inputs["samples"][0]
    return node_id


def _upstream(graph: Mapping, refs: list[list | None]) -> set[str]:
    """Every node reachable by following input refs from `refs`' target nodes."""
    keep: set[str] = set()
    stack = [ref[0] for ref in refs if ref is not None]
    while stack:
        node_id = stack.pop()
        if node_id in keep:
            continue
        keep.add(node_id)
        for value in graph[node_id].get("inputs", {}).values():
            if _is_ref(value) and value[0] in graph:
                stack.append(value[0])
    return keep


def source_prompts(graph: Mapping) -> tuple[str, str]:
    """The source's own final positive/negative CLIPTextEncode text."""
    decode_id = _find_decode(graph)
    sampler_id = _find_sampler(graph, decode_id)
    inputs = graph[sampler_id]["inputs"]
    positive = graph[inputs["positive"][0]]["inputs"]["text"]
    negative = graph[inputs["negative"][0]]["inputs"]["text"]
    return positive, negative


def redraw_canvas(graph: Mapping) -> tuple[int, int]:
    """The (width, height) of the final sampler's own canvas.

    Reads whatever feeds the final KSampler's `latent_image`: a `LatentUpscale`
    or an `ImageScale` -> `VAEEncode` pair gives the redraw's own dimensions;
    a plain raw graph samples straight off an `EmptyLatentImage`.
    """
    decode_id = _find_decode(graph)
    sampler_id = _find_sampler(graph, decode_id)
    latent_ref = graph[sampler_id]["inputs"]["latent_image"]
    node = graph[latent_ref[0]]
    class_type = node.get("class_type")
    if class_type in ("LatentUpscale", "EmptyLatentImage"):
        return node["inputs"]["width"], node["inputs"]["height"]
    if class_type == "VAEEncode":
        image_node = graph[node["inputs"]["pixels"][0]]
        if image_node.get("class_type") == "ImageScale":
            return image_node["inputs"]["width"], image_node["inputs"]["height"]
    raise ValueError(
        f"could not read the redraw canvas size from latent_image node "
        f"{latent_ref[0]!r} ({class_type!r})")


def _splice_reroll(graph: dict, allocate: Callable[[], str], *, image_ref: list,
                   mask_name: str, positive: str, negative: str,
                   model_ref: list, positive_clip_ref: list,
                   negative_clip_ref: list, vae_ref: list, steps: int, cfg: float,
                   sampler_name: str, scheduler: str, seed: int, denoise: float,
                   size: int) -> tuple[str, list]:
    """Adds the crop/resample/stitch reroll subgraph to `graph` (mutated).

    Returns `(crop_id, repaired_ref)`: `crop_id` so a caller that spliced
    `image_ref` from its own graph's output can exclude the crop's own input
    when rewiring every other consumer of that output; `repaired_ref` is the
    stitch node's `[id, 0]` output.
    """
    load_mask = allocate()
    graph[load_mask] = {"class_type": "LoadImage", "inputs": {"image": mask_name}}
    to_mask = allocate()
    graph[to_mask] = {"class_type": "ImageToMask", "inputs": {
        "image": [load_mask, 0], "channel": "red"}}
    crop = allocate()
    graph[crop] = {"class_type": "InpaintCropImproved", "inputs": {
        **_INPAINT_CROP_DEFAULTS,
        "image": image_ref, "mask": [to_mask, 0],
        "output_target_width": size, "output_target_height": size}}
    stitcher_ref, cropped_image_ref, cropped_mask_ref = (
        [crop, 0], [crop, 1], [crop, 2])

    positive_id = allocate()
    graph[positive_id] = {"class_type": "CLIPTextEncode", "inputs": {
        "clip": positive_clip_ref, "text": positive}}
    negative_id = allocate()
    graph[negative_id] = {"class_type": "CLIPTextEncode", "inputs": {
        "clip": negative_clip_ref, "text": negative}}

    encode = allocate()
    graph[encode] = {"class_type": "VAEEncode", "inputs": {
        "pixels": cropped_image_ref, "vae": vae_ref}}
    noise_mask = allocate()
    graph[noise_mask] = {"class_type": "SetLatentNoiseMask", "inputs": {
        "samples": [encode, 0], "mask": cropped_mask_ref}}
    sample = allocate()
    graph[sample] = {"class_type": "KSampler", "inputs": {
        "model": model_ref, "positive": [positive_id, 0],
        "negative": [negative_id, 0], "latent_image": [noise_mask, 0],
        "seed": seed, "steps": steps, "cfg": cfg,
        "sampler_name": sampler_name, "scheduler": scheduler, "denoise": denoise}}
    decode = allocate()
    graph[decode] = {"class_type": "VAEDecode", "inputs": {
        "samples": [sample, 0], "vae": vae_ref}}
    stitch = allocate()
    graph[stitch] = {"class_type": "InpaintStitchImproved", "inputs": {
        "stitcher": stitcher_ref, "inpainted_image": [decode, 0]}}
    return crop, [stitch, 0]


def _redraw_pass(graph: Mapping) -> dict:
    """The final sampler/decode's own model, CLIP, VAE refs and sampling settings."""
    decode_id = _find_decode(graph)
    sampler_id = _find_sampler(graph, decode_id)
    sampler_inputs = graph[sampler_id]["inputs"]
    return {
        "decode_id": decode_id,
        "model_ref": sampler_inputs["model"],
        "positive_clip_ref": graph[sampler_inputs["positive"][0]]["inputs"]["clip"],
        "negative_clip_ref": graph[sampler_inputs["negative"][0]]["inputs"]["clip"],
        "vae_ref": graph[decode_id]["inputs"]["vae"],
        "steps": sampler_inputs["steps"],
        "cfg": sampler_inputs["cfg"],
        "sampler_name": sampler_inputs["sampler_name"],
        "scheduler": sampler_inputs["scheduler"],
        "seed": sampler_inputs["seed"],
    }


def repair_graph(source: Mapping, *, image_name: str, mask_name: str,
                 positive: str, negative: str, seed: int, denoise: float,
                 size: int, prefix: str) -> dict:
    graph = json.loads(json.dumps(source))
    pass_ = _redraw_pass(graph)
    decode_id = pass_["decode_id"]

    # The loaders/LoRA the redraw needs -- not `sampler_id` itself, and not
    # the latent/pass-1 chain feeding it, since neither ref reaches those.
    keep = _upstream(graph, [pass_["model_ref"], pass_["vae_ref"],
                            pass_["positive_clip_ref"], pass_["negative_clip_ref"]])

    consumers = _consumers(graph)
    tail: set[str] = set()
    stack = list(consumers.get(decode_id, []))
    while stack:
        node_id = stack.pop()
        if node_id in tail:
            continue
        tail.add(node_id)
        stack.extend(consumers.get(node_id, []))
    # A tail node can depend on a sibling that is not itself downstream of
    # the decode (a matte model loader feeding a background-removal node
    # alongside the decode's own image input) -- pull those in too.
    dependency_stack = [
        value[0] for node_id in tail
        for value in graph[node_id].get("inputs", {}).values()
        if _is_ref(value) and value[0] in graph and value[0] != decode_id]
    while dependency_stack:
        node_id = dependency_stack.pop()
        if node_id in keep or node_id in tail:
            continue
        tail.add(node_id)
        dependency_stack.extend(
            value[0] for value in graph[node_id].get("inputs", {}).values()
            if _is_ref(value) and value[0] in graph and value[0] != decode_id)

    result = {node_id: graph[node_id] for node_id in keep}

    ids = itertools.count(max((int(key) for key in graph), default=0) + 1)

    def allocate() -> str:
        return str(next(ids))

    load_image = allocate()
    result[load_image] = {"class_type": "LoadImage", "inputs": {"image": image_name}}

    _, repaired_ref = _splice_reroll(
        result, allocate, image_ref=[load_image, 0], mask_name=mask_name,
        positive=positive, negative=negative, model_ref=pass_["model_ref"],
        positive_clip_ref=pass_["positive_clip_ref"],
        negative_clip_ref=pass_["negative_clip_ref"], vae_ref=pass_["vae_ref"],
        steps=pass_["steps"], cfg=pass_["cfg"], sampler_name=pass_["sampler_name"],
        scheduler=pass_["scheduler"], seed=seed, denoise=denoise, size=size)
    stitch = repaired_ref[0]

    direct_save = False
    for node_id in tail:
        node = graph[node_id]
        inputs = node.get("inputs", {})
        for key, value in list(inputs.items()):
            if _is_ref(value) and value[0] == decode_id:
                inputs[key] = repaired_ref
        if node.get("class_type") == "SaveImage":
            images_ref = inputs.get("images")
            prefix_now = inputs.get("filename_prefix", "")
            if _is_ref(images_ref) and images_ref[0] == stitch:
                inputs["filename_prefix"] = prefix
                direct_save = True
            elif prefix_now.endswith(MATTE_SUFFIX):
                inputs["filename_prefix"] = prefix + MATTE_SUFFIX
            elif prefix_now.endswith(DELIVERED_SUFFIX):
                inputs["filename_prefix"] = prefix + DELIVERED_SUFFIX
            else:
                inputs["filename_prefix"] = prefix
        result[node_id] = node

    if not direct_save:
        save = allocate()
        result[save] = {"class_type": "SaveImage", "inputs": {
            "images": repaired_ref, "filename_prefix": prefix}}

    return result


def splice_repair(graph: Mapping, *, mask_name: str, positive: str, negative: str,
                  denoise: float, size: int, seed: int | None = None) -> dict:
    """Splice a masked reroll into an already-built graph (e.g. `chain_pass`'s).

    Unlike `repair_graph`, nothing is pruned or renamed: the reroll's image
    input is the final decode's own output (no staged-source LoadImage), every
    other consumer of that output is rewired onto the stitch, and every
    SaveImage prefix is left exactly as the caller built it.
    """
    result = json.loads(json.dumps(graph))
    pass_ = _redraw_pass(result)
    decode_id = pass_["decode_id"]

    ids = itertools.count(max((int(key) for key in result), default=0) + 1)

    def allocate() -> str:
        return str(next(ids))

    crop_id, repaired_ref = _splice_reroll(
        result, allocate, image_ref=[decode_id, 0], mask_name=mask_name,
        positive=positive, negative=negative, model_ref=pass_["model_ref"],
        positive_clip_ref=pass_["positive_clip_ref"],
        negative_clip_ref=pass_["negative_clip_ref"], vae_ref=pass_["vae_ref"],
        steps=pass_["steps"], cfg=pass_["cfg"], sampler_name=pass_["sampler_name"],
        scheduler=pass_["scheduler"],
        seed=pass_["seed"] if seed is None else seed,
        denoise=denoise, size=size)

    for node_id, node in result.items():
        if node_id == crop_id:
            continue
        for key, value in list(node.get("inputs", {}).items()):
            if _is_ref(value) and value[0] == decode_id:
                node["inputs"][key] = repaired_ref

    return result
