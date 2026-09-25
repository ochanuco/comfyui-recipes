"""ComfyUI graph transformation for the delivery redraw."""

from __future__ import annotations

import json
from collections.abc import Callable

from ...domain.yukari.delivery_style import STROKE_LIGHTS
from ..imaging import backdrops
from .base_graph import base_roles

# Both images come out of one submission, so the matte is the redraw's own
# alpha rather than a second pass's guess at it.
MATTE_SUFFIX = "-matte"
# The delivered composite: background cut, white band, purple stroke.
DELIVERED_SUFFIX = "-delivered"
# A matte_model of this form names a ComfyUI-RMBG model instead of a core
# background-removal model file.
RMBG_MATTE_PREFIX = "rmbg:"


def sizes(width: int, height: int, longest_side: int) -> tuple[int, int]:
    longest = max(width, height)
    return (round(longest_side * width / longest / 8) * 8,
            round(longest_side * height / longest / 8) * 8)


def _matte_nodes(graph: dict, allocate: Callable[[], str], image_ref: list,
                 matte_model: str) -> list:
    if matte_model.startswith(RMBG_MATTE_PREFIX):
        node_id = allocate()
        graph[node_id] = {"class_type": "BiRefNetRMBG", "inputs": {
            "image": image_ref, "model": matte_model[len(RMBG_MATTE_PREFIX):],
            "sensitivity": 1.0, "mask_blur": 0, "mask_offset": 0,
            "invert_output": False, "refine_foreground": False,
            "background": "Alpha", "background_color": "#222222"}}
        return [node_id, 1]
    bg_loader = allocate()
    graph[bg_loader] = {"class_type": "LoadBackgroundRemovalModel", "inputs": {
        "bg_removal_name": matte_model}}
    remove = allocate()
    graph[remove] = {"class_type": "RemoveBackground", "inputs": {
        "bg_removal_model": [bg_loader, 0], "image": image_ref}}
    return [remove, 0]


def _deliver_only_tail(graph: dict, allocate: Callable[[], str], image_ref: list,
                       matte_model: str, prefix: str, *, skin: bool, repin: bool,
                       recolor: bool, keep_legwear: float | None, keep_scene: bool,
                       transparent: bool, backdrop: str | None,
                       stroke_light: str | None, deliver_size: int | None,
                       canvas: tuple[int, int],
                       source_image: str | None = None) -> list:
    """Appends the deliver-only chain onto `graph` (mutated). Returns the
    delivered picture's ref. `image_ref` may already be someone else's
    redraw or stitch, so `source_image` -- the unedited picture `skin`
    reads its original tones from -- is loaded fresh rather than reused.
    """
    # A raw output alongside the matte and the delivered one, same three-way
    # split finalize() classifies every other route by.
    raw_save = allocate()
    graph[raw_save] = {"class_type": "SaveImage", "inputs": {
        "images": image_ref, "filename_prefix": prefix}}
    matte_ref = _matte_nodes(graph, allocate, image_ref, matte_model)
    to_image = allocate()
    graph[to_image] = {"class_type": "MaskToImage", "inputs": {"mask": matte_ref}}
    matte_save = allocate()
    graph[matte_save] = {"class_type": "SaveImage", "inputs": {
        "images": [to_image, 0], "filename_prefix": prefix + MATTE_SUFFIX}}
    if skin:
        load_source = allocate()
        graph[load_source] = {"class_type": "LoadImage", "inputs": {"image": source_image}}
        repin_skin_id = allocate()
        graph[repin_skin_id] = {"class_type": "YukariRepinSkin", "inputs": {
            "image": image_ref, "source": [load_source, 0]}}
        image_ref = [repin_skin_id, 0]
    if recolor:
        recolor_id = allocate()
        graph[recolor_id] = {"class_type": "YukariRecolor", "inputs": {"image": image_ref}}
        image_ref = [recolor_id, 0]
    elif repin:
        repin_id = allocate()
        graph[repin_id] = {"class_type": "YukariRepin", "inputs": {
            "image": image_ref,
            "keep_legwear": keep_legwear is not None,
            "keep_legwear_cut": keep_legwear if keep_legwear is not None else 0.62}}
        image_ref = [repin_id, 0]
    deliver_id = allocate()
    graph[deliver_id] = {"class_type": "YukariDeliver", "inputs": {
        "image": image_ref, "matte": matte_ref, "keep_scene": keep_scene,
        "transparent": transparent, "stroke_light": stroke_light or "",
        "backdrop": backdrop or ""}}
    delivered_ref = [deliver_id, 0]
    width, height = canvas
    longest = max(width, height)
    if deliver_size is not None and deliver_size < longest:
        target = (round(width * deliver_size / longest),
                 round(height * deliver_size / longest))
        deliver_scale = allocate()
        graph[deliver_scale] = {"class_type": "ImageScale", "inputs": {
            "image": delivered_ref, "upscale_method": "lanczos",
            "width": target[0], "height": target[1], "crop": "disabled"}}
        delivered_ref = [deliver_scale, 0]
    save_delivered = allocate()
    graph[save_delivered] = {"class_type": "SaveImage", "inputs": {
        "images": delivered_ref, "filename_prefix": prefix + DELIVERED_SUFFIX}}
    return delivered_ref


def _deliver_only_graph(source_image: str, matte_model: str, prefix: str, *,
                        skin: bool, repin: bool, recolor: bool,
                        keep_legwear: float | None, keep_scene: bool,
                        transparent: bool, backdrop: str | None,
                        stroke_light: str | None, deliver_size: int | None,
                        canvas: tuple[int, int]) -> dict:
    # A self-contained graph: nothing here depends on the base pass that
    # produced source_image, so it carries none of that pass's own nodes.
    graph: dict = {}
    cursor = 1

    def allocate() -> str:
        nonlocal cursor
        node_id = str(cursor)
        cursor += 1
        return node_id

    load_id = allocate()
    graph[load_id] = {"class_type": "LoadImage", "inputs": {"image": source_image}}
    _deliver_only_tail(
        graph, allocate, [load_id, 0], matte_model, prefix,
        skin=skin, repin=repin, recolor=recolor, keep_legwear=keep_legwear,
        keep_scene=keep_scene, transparent=transparent, backdrop=backdrop,
        stroke_light=stroke_light, deliver_size=deliver_size, canvas=canvas,
        source_image=source_image)
    return graph


def chain_pass(base: dict, size: int, denoise: float, prefix: str,
               prompt: tuple[str, str] | None = None,
               matte_model: str | None = None,
               latent_route: bool = False,
               sampler: tuple[str, str] | None = None,
               loader: str | None = None,
               sampling: tuple[int, float] | None = None, *,
               skin: bool = False, repin: bool = False, recolor: bool = False,
               keep_legwear: float | None = None, keep_scene: bool = False,
               source_image: str | None = None,
               keep_mask_image: str | None = None,
               deliver: bool = False, transparent: bool = False,
               backdrop: str | None = None,
               upscale: str = "bicubic",
               deliver_size: int | None = None,
               stroke_light: str | None = None,
               deliver_only: bool = False,
               redraw_from_source: bool = False,
               canvas: tuple[int, int]) -> dict:
    if redraw_from_source and not source_image:
        raise ValueError("redraw_from_source requires source_image")
    if upscale not in ("bicubic", "nearest-exact", "bilinear", "lanczos"):
        raise ValueError(f"unsupported upscale method: {upscale!r}")
    if stroke_light is not None and stroke_light not in STROKE_LIGHTS:
        valid = ", ".join(repr(key) for key in sorted(STROKE_LIGHTS))
        raise ValueError(f"stroke_light must be null or one of {valid}, got {stroke_light!r}")
    if backdrop is not None and not backdrops.is_backdrop(backdrop):
        valid = ", ".join(repr(key) for key in sorted(backdrops.PATTERNS))
        raise ValueError(
            f"backdrop must be null, a #RRGGBB colour or one of {valid}, got {backdrop!r}")
    unsupported = [key for key in base
                   if not isinstance(key, str) or not key.isdecimal()]
    if unsupported:
        raise ValueError(
            "base graph has unsupported non-numeric node IDs: "
            + ", ".join(map(repr, unsupported)))
    if deliver_only:
        if not source_image:
            raise ValueError("deliver_only requires source_image")
        if not matte_model:
            raise ValueError("deliver_only requires matte_model")
        return _deliver_only_graph(
            source_image, matte_model, prefix, skin=skin, repin=repin,
            recolor=recolor, keep_legwear=keep_legwear, keep_scene=keep_scene,
            transparent=transparent, backdrop=backdrop,
            stroke_light=stroke_light, deliver_size=deliver_size, canvas=canvas)
    graph = json.loads(json.dumps(base))
    roles = base_roles(graph)
    if latent_route and roles.stitched:
        raise ValueError(
            "latent_route is not supported on a stitched base: its sampler's "
            "latent is the inpaint crop, not the whole picture")
    next_id = max(int(key) for key in graph) + 1
    scale, encode, sample, decode = (
        str(next_id + offset) for offset in range(4))
    # Read off the base pass rather than assumed: a single DiffusersLoader
    # answers model/CLIP/VAE from node 4, a split-file model from three
    # separate loaders.
    model_ref = graph[roles.sampler_id]["inputs"].get("model", ["4", 0])
    # A layerdiffuse base samples through its own LayeredDiffusionApply node,
    # so the redraw's model is what that node itself sampled, not the node.
    apply_node = graph.get(model_ref[0], {})
    if apply_node.get("class_type") == "LayeredDiffusionApply":
        model_ref = apply_node["inputs"]["model"]
    clip_ref = graph[roles.positive_id]["inputs"].get("clip", ["4", 1])
    vae_ref = graph[roles.decode_id]["inputs"].get("vae", ["4", 2])
    if loader:
        # A different checkpoint redraws: its own model, CLIP and VAE, with the
        # base prompts re-encoded through its CLIP.
        loader_id = str(next_id + 10)
        if loader.endswith(".safetensors"):
            graph[loader_id] = {"class_type": "CheckpointLoaderSimple",
                                "inputs": {"ckpt_name": loader}}
        else:
            graph[loader_id] = {"class_type": "DiffusersLoader",
                                "inputs": {"model_path": loader}}
        model_ref, clip_ref, vae_ref = (
            [loader_id, 0], [loader_id, 1], [loader_id, 2])
        if prompt is None:
            prompt = (graph[roles.positive_id]["inputs"]["text"],
                      graph[roles.negative_id]["inputs"]["text"])
    positive, negative = (graph[roles.sampler_id]["inputs"]["positive"],
                         graph[roles.sampler_id]["inputs"]["negative"])
    if prompt:
        positive_id, negative_id = str(next_id + 4), str(next_id + 5)
        graph[positive_id] = {"class_type": "CLIPTextEncode", "inputs": {
            "clip": clip_ref, "text": prompt[0]}}
        graph[negative_id] = {"class_type": "CLIPTextEncode", "inputs": {
            "clip": clip_ref, "text": prompt[1]}}
        positive, negative = [positive_id, 0], [negative_id, 0]
    width, height = sizes(*canvas, size)
    longest = max(width, height)
    deliver_target = None
    if deliver_size is not None and deliver_size < longest:
        deliver_target = (round(width * deliver_size / longest),
                          round(height * deliver_size / longest))
    # The routes to the bigger latent draw different pictures: pixel space
    # is faithful, the latent route leaves a staircase on hard contours
    # that the redraw turns into visible stroke.
    if latent_route and not source_image:
        graph[scale] = {"class_type": "LatentUpscale", "inputs": {
            "samples": [roles.sampler_id, 0], "upscale_method": "bicubic",
            "width": width, "height": height, "crop": "disabled"}}
        latent_in = [scale, 0]
    elif latent_route and source_image:
        # A source image outside the base graph (a repaired raw's own
        # picture) replaces the base sampler's latent as the thing upscaled.
        source_load_id = str(next_id + 13)
        graph[source_load_id] = {"class_type": "LoadImage", "inputs": {
            "image": source_image}}
        graph[encode] = {"class_type": "VAEEncode", "inputs": {
            "pixels": [source_load_id, 0], "vae": vae_ref}}
        graph[scale] = {"class_type": "LatentUpscale", "inputs": {
            "samples": [encode, 0], "upscale_method": "bicubic",
            "width": width, "height": height, "crop": "disabled"}}
        latent_in = [scale, 0]
    else:
        if redraw_from_source:
            # A repaired raw's own uploaded picture, not the base graph's
            # un-repaired SaveImage output.
            source_load_id = str(next_id + 13)
            graph[source_load_id] = {"class_type": "LoadImage", "inputs": {
                "image": source_image}}
            image_ref = [source_load_id, 0]
        else:
            image_ref = graph[roles.save_id]["inputs"]["images"]
        graph[scale] = {"class_type": "ImageScale", "inputs": {
            "image": image_ref, "upscale_method": upscale,
            "width": width, "height": height, "crop": "disabled"}}
        graph[encode] = {"class_type": "VAEEncode", "inputs": {
            "pixels": [scale, 0], "vae": vae_ref}}
        latent_in = [encode, 0]
    if keep_mask_image is not None:
        keep_load_id = str(next_id + 14)
        graph[keep_load_id] = {"class_type": "LoadImage", "inputs": {
            "image": keep_mask_image}}
        keep_to_mask_id = str(next_id + 15)
        graph[keep_to_mask_id] = {"class_type": "ImageToMask", "inputs": {
            "image": [keep_load_id, 0], "channel": "red"}}
        keep_noise_mask_id = str(next_id + 16)
        graph[keep_noise_mask_id] = {"class_type": "SetLatentNoiseMask", "inputs": {
            "samples": latent_in, "mask": [keep_to_mask_id, 0]}}
        latent_in = [keep_noise_mask_id, 0]
    # Steps, cfg and seed are the base pass's own: a checkpoint that was tuned
    # at a different cfg must be redrawn the way it was drawn. The sampler is
    # the base pass's own too, unless the caller overrides it.
    base_sampler = graph[roles.sampler_id]["inputs"]
    sampler_name, scheduler = (
        sampler if sampler is not None
        else (base_sampler.get("sampler_name", "dpmpp_2m"),
              base_sampler.get("scheduler", "karras")))
    steps, cfg = (
        sampling if sampling is not None
        else (base_sampler.get("steps", 30), base_sampler.get("cfg", 5.0)))
    graph[sample] = {"class_type": "KSampler", "inputs": {
        "model": model_ref, "positive": positive, "negative": negative,
        "latent_image": latent_in, "seed": base_sampler["seed"],
        "steps": steps,
        "cfg": cfg,
        "sampler_name": sampler_name,
        "scheduler": scheduler,
        "denoise": denoise}}
    graph[decode] = {"class_type": "VAEDecode", "inputs": {
        "samples": [sample, 0], "vae": vae_ref}}
    graph[roles.save_id]["inputs"]["images"] = [decode, 0]
    graph[roles.save_id]["inputs"]["filename_prefix"] = prefix
    if deliver and not matte_model:
        raise ValueError("deliver requires matte_model")
    if matte_model:
        cursor = next_id + 6

        def allocate() -> str:
            nonlocal cursor
            node_id = str(cursor)
            cursor += 1
            return node_id

        matte_ref = _matte_nodes(graph, allocate, [decode, 0], matte_model)
        to_image = allocate()
        graph[to_image] = {"class_type": "MaskToImage", "inputs": {
            "mask": matte_ref}}
        save = allocate()
        graph[save] = {"class_type": "SaveImage", "inputs": {
            "images": [to_image, 0], "filename_prefix": prefix + MATTE_SUFFIX}}
        if deliver:
            if skin and not source_image:
                raise ValueError("skin requires source_image")
            # Not a fixed offset: an overriding `loader` claims next_id + 10
            # for its own DiffusersLoader, so the free id has to be read off
            # the graph as it stands rather than assumed.
            cursor = max(int(key) for key in graph) + 1

            def allocate() -> str:
                nonlocal cursor
                node_id = str(cursor)
                cursor += 1
                return node_id

            image_ref = [decode, 0]
            if skin:
                load_source = allocate()
                graph[load_source] = {"class_type": "LoadImage", "inputs": {
                    "image": source_image}}
                repin_skin_id = allocate()
                graph[repin_skin_id] = {"class_type": "YukariRepinSkin", "inputs": {
                    "image": image_ref, "source": [load_source, 0]}}
                image_ref = [repin_skin_id, 0]
            if recolor:
                recolor_id = allocate()
                graph[recolor_id] = {"class_type": "YukariRecolor", "inputs": {
                    "image": image_ref}}
                image_ref = [recolor_id, 0]
            elif repin:
                repin_id = allocate()
                graph[repin_id] = {"class_type": "YukariRepin", "inputs": {
                    "image": image_ref,
                    "keep_legwear": keep_legwear is not None,
                    "keep_legwear_cut": (keep_legwear if keep_legwear is not None
                                         else 0.62)}}
                image_ref = [repin_id, 0]
            deliver_id = allocate()
            graph[deliver_id] = {"class_type": "YukariDeliver", "inputs": {
                "image": image_ref, "matte": matte_ref,
                "keep_scene": keep_scene, "transparent": transparent,
                "stroke_light": stroke_light or "", "backdrop": backdrop or ""}}
            delivered_ref = [deliver_id, 0]
            if deliver_target is not None:
                deliver_scale = allocate()
                graph[deliver_scale] = {"class_type": "ImageScale", "inputs": {
                    "image": delivered_ref, "upscale_method": "lanczos",
                    "width": deliver_target[0], "height": deliver_target[1],
                    "crop": "disabled"}}
                delivered_ref = [deliver_scale, 0]
            save_delivered = allocate()
            graph[save_delivered] = {"class_type": "SaveImage", "inputs": {
                "images": delivered_ref,
                "filename_prefix": prefix + DELIVERED_SUFFIX}}
    return graph
