"""ComfyUI graph transformation for the delivery redraw."""

from __future__ import annotations

import json

from ...domain.yukari.delivery_style import STROKE_LIGHTS
from ..imaging import backdrops

# Both images come out of one submission, so the matte is the redraw's own
# alpha rather than a second pass's guess at it.
MATTE_SUFFIX = "-matte"
# The delivered composite: background cut, white band, purple stroke.
DELIVERED_SUFFIX = "-delivered"


def sizes(graph: dict, longest_side: int) -> tuple[int, int]:
    width = graph["5"]["inputs"]["width"]
    height = graph["5"]["inputs"]["height"]
    longest = max(width, height)
    return (round(longest_side * width / longest / 8) * 8,
            round(longest_side * height / longest / 8) * 8)


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
               deliver: bool = False, transparent: bool = False,
               compose: bool = False, backdrop: str | None = None,
               redraw_lora: tuple[str, float, float] | None = None,
               upscale: str = "bicubic",
               deliver_size: int | None = None,
               stroke_light: str | None = None) -> dict:
    if upscale not in ("bicubic", "nearest-exact", "bilinear", "lanczos"):
        raise ValueError(f"unsupported upscale method: {upscale!r}")
    if stroke_light is not None and stroke_light not in STROKE_LIGHTS:
        valid = ", ".join(repr(key) for key in sorted(STROKE_LIGHTS))
        raise ValueError(f"stroke_light must be null or one of {valid}, got {stroke_light!r}")
    if backdrop is not None and not backdrops.is_backdrop(backdrop):
        valid = ", ".join(repr(key) for key in sorted(backdrops.PATTERNS))
        raise ValueError(
            f"backdrop must be null, a #RRGGBB colour or one of {valid}, got {backdrop!r}")
    required = {"3", "4", "5", "6", "7", "9"}
    missing = sorted(required - base.keys(), key=int)
    if missing:
        raise ValueError(
            f"base graph is missing required node IDs: {', '.join(missing)}")
    unsupported = [key for key in base
                   if not isinstance(key, str) or not key.isdecimal()]
    if unsupported:
        raise ValueError(
            "base graph has unsupported non-numeric node IDs: "
            + ", ".join(map(repr, unsupported)))
    graph = json.loads(json.dumps(base))
    next_id = max(int(key) for key in graph) + 1
    scale, encode, sample, decode = (
        str(next_id + offset) for offset in range(4))
    # Where the model, CLIP and VAE come from is read off the base pass rather
    # than assumed: a single DiffusersLoader answers all three from node 4, a
    # split-file model answers them from three separate loaders.
    model_ref = graph["3"]["inputs"].get("model", ["4", 0])
    # A layerdiffuse base samples through its own LayeredDiffusionApply node,
    # so the redraw's model is what that node itself sampled, not the node.
    apply_node = graph.get(model_ref[0], {})
    if apply_node.get("class_type") == "LayeredDiffusionApply":
        model_ref = apply_node["inputs"]["model"]
    clip_ref = graph["6"]["inputs"].get("clip", ["4", 1])
    tail = graph[graph["9"]["inputs"]["images"][0]]
    while tail.get("class_type") in ("JoinImageWithAlpha", "LayeredDiffusionDecode"):
        image_key = "image" if "image" in tail["inputs"] else "images"
        tail = graph[tail["inputs"][image_key][0]]
    if tail.get("class_type") != "VAEDecode":
        raise ValueError(
            "base graph's SaveImage must be fed by a VAEDecode, got "
            f"{tail.get('class_type')!r}")
    vae_ref = tail["inputs"].get("vae", ["4", 2])
    compose_id = None
    if compose:
        if matte_model or deliver:
            raise ValueError(
                "compose cannot be combined with matte_model or deliver")
        join_ref = graph["9"]["inputs"]["images"]
        join_node = graph.get(join_ref[0], {})
        if join_node.get("class_type") != "JoinImageWithAlpha":
            raise ValueError(
                "compose requires the base graph's SaveImage to be fed "
                f"directly by a JoinImageWithAlpha node, got "
                f"{join_node.get('class_type')!r}")
        compose_id = str(next_id + 11)
        graph[compose_id] = {"class_type": "YukariCompose", "inputs": {
            "image": join_ref, "backdrop": backdrop or "",
            "stroke_light": stroke_light or ""}}
    if loader:
        # A different checkpoint redraws: its own model, CLIP and VAE, with the
        # base prompts re-encoded through its CLIP.
        loader_id = str(next_id + 10)
        graph[loader_id] = {"class_type": "DiffusersLoader",
                            "inputs": {"model_path": loader}}
        model_ref, clip_ref, vae_ref = (
            [loader_id, 0], [loader_id, 1], [loader_id, 2])
        if prompt is None:
            prompt = (graph["6"]["inputs"]["text"], graph["7"]["inputs"]["text"])
    if redraw_lora:
        while graph.get(model_ref[0], {}).get("class_type") == "LoraLoader":
            model_ref = graph[model_ref[0]]["inputs"]["model"]
        while graph.get(clip_ref[0], {}).get("class_type") == "LoraLoader":
            clip_ref = graph[clip_ref[0]]["inputs"]["clip"]
        lora_name, strength_model, strength_clip = redraw_lora
        lora_id = str(next_id + 12)
        graph[lora_id] = {"class_type": "LoraLoader", "inputs": {
            "model": model_ref, "clip": clip_ref, "lora_name": lora_name,
            "strength_model": strength_model, "strength_clip": strength_clip}}
        model_ref, clip_ref = [lora_id, 0], [lora_id, 1]
    positive, negative = ["6", 0], ["7", 0]
    if prompt:
        positive_id, negative_id = str(next_id + 4), str(next_id + 5)
        graph[positive_id] = {"class_type": "CLIPTextEncode", "inputs": {
            "clip": clip_ref, "text": prompt[0]}}
        graph[negative_id] = {"class_type": "CLIPTextEncode", "inputs": {
            "clip": clip_ref, "text": prompt[1]}}
        positive, negative = [positive_id, 0], [negative_id, 0]
    width, height = sizes(graph, size)
    longest = max(width, height)
    deliver_target = None
    if deliver_size is not None and deliver_size < longest:
        deliver_target = (round(width * deliver_size / longest),
                          round(height * deliver_size / longest))
    # Two routes to the bigger latent, and they do not draw the same picture.
    # Pixel space is faithful; the latent route leaves a staircase on hard
    # contours that the redraw turns into visible stroke, which is the hand in
    # the line this delivery is judged on.
    if latent_route and not compose:
        graph[scale] = {"class_type": "LatentUpscale", "inputs": {
            "samples": ["3", 0], "upscale_method": "bicubic",
            "width": width, "height": height, "crop": "disabled"}}
        latent_in = [scale, 0]
    elif compose and latent_route:
        graph[encode] = {"class_type": "VAEEncode", "inputs": {
            "pixels": [compose_id, 0], "vae": vae_ref}}
        graph[scale] = {"class_type": "LatentUpscale", "inputs": {
            "samples": [encode, 0], "upscale_method": "bicubic",
            "width": width, "height": height, "crop": "disabled"}}
        latent_in = [scale, 0]
    else:
        # The composited backdrop only exists as pixels, so a plain compose
        # redraw has to start from it, not from the RGBA.
        image_ref = [compose_id, 0] if compose else graph["9"]["inputs"]["images"]
        graph[scale] = {"class_type": "ImageScale", "inputs": {
            "image": image_ref, "upscale_method": upscale,
            "width": width, "height": height, "crop": "disabled"}}
        graph[encode] = {"class_type": "VAEEncode", "inputs": {
            "pixels": [scale, 0], "vae": vae_ref}}
        latent_in = [encode, 0]
    # Steps, cfg and seed are the base pass's own: a checkpoint that was tuned
    # at a different cfg must be redrawn the way it was drawn. The sampler is
    # the base pass's own too, unless the caller overrides it.
    base_sampler = graph["3"]["inputs"]
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
    graph["9"]["inputs"]["images"] = [decode, 0]
    graph["9"]["inputs"]["filename_prefix"] = prefix
    if compose and deliver_target is not None:
        # compose is the whole delivered picture here -- no separate
        # YukariDeliver node downstream to scale instead.
        deliver_scale = str(max(int(key) for key in graph) + 1)
        graph[deliver_scale] = {"class_type": "ImageScale", "inputs": {
            "image": [decode, 0], "upscale_method": "lanczos",
            "width": deliver_target[0], "height": deliver_target[1],
            "crop": "disabled"}}
        graph["9"]["inputs"]["images"] = [deliver_scale, 0]
    if deliver and not matte_model:
        raise ValueError("deliver requires matte_model")
    if matte_model:
        bg_loader, remove, to_image, save = (
            str(next_id + offset) for offset in range(6, 10))
        graph[bg_loader] = {"class_type": "LoadBackgroundRemovalModel", "inputs": {
            "bg_removal_name": matte_model}}
        graph[remove] = {"class_type": "RemoveBackground", "inputs": {
            "bg_removal_model": [bg_loader, 0], "image": [decode, 0]}}
        graph[to_image] = {"class_type": "MaskToImage", "inputs": {
            "mask": [remove, 0]}}
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
                "image": image_ref, "matte": [remove, 0],
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
