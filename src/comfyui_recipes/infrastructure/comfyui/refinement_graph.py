"""ComfyUI graph transformation for the delivery redraw."""

from __future__ import annotations

import json

# Both images come out of one submission, so the matte is the redraw's own
# alpha rather than a second pass's guess at it.
MATTE_SUFFIX = "-matte"


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
               sampling: tuple[int, float] | None = None) -> dict:
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
    clip_ref = graph["6"]["inputs"].get("clip", ["4", 1])
    tail = graph[graph["9"]["inputs"]["images"][0]]
    if tail.get("class_type") != "VAEDecode":
        raise ValueError(
            "base graph's SaveImage must be fed by a VAEDecode, got "
            f"{tail.get('class_type')!r}")
    vae_ref = tail["inputs"].get("vae", ["4", 2])
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
    positive, negative = ["6", 0], ["7", 0]
    if prompt:
        positive_id, negative_id = str(next_id + 4), str(next_id + 5)
        graph[positive_id] = {"class_type": "CLIPTextEncode", "inputs": {
            "clip": clip_ref, "text": prompt[0]}}
        graph[negative_id] = {"class_type": "CLIPTextEncode", "inputs": {
            "clip": clip_ref, "text": prompt[1]}}
        positive, negative = [positive_id, 0], [negative_id, 0]
    width, height = sizes(graph, size)
    # Two routes to the bigger latent, and they do not draw the same picture.
    # Pixel space is faithful; the latent route leaves a staircase on hard
    # contours that the redraw turns into visible stroke, which is the hand in
    # the line this delivery is judged on.
    if latent_route:
        graph[scale] = {"class_type": "LatentUpscale", "inputs": {
            "samples": ["3", 0], "upscale_method": "bicubic",
            "width": width, "height": height, "crop": "disabled"}}
        latent_in = [scale, 0]
    else:
        graph[scale] = {"class_type": "ImageScale", "inputs": {
            "image": graph["9"]["inputs"]["images"], "upscale_method": "bicubic",
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
    if matte_model:
        loader, remove, to_image, save = (
            str(next_id + offset) for offset in range(6, 10))
        graph[loader] = {"class_type": "LoadBackgroundRemovalModel", "inputs": {
            "bg_removal_name": matte_model}}
        graph[remove] = {"class_type": "RemoveBackground", "inputs": {
            "bg_removal_model": [loader, 0], "image": [decode, 0]}}
        graph[to_image] = {"class_type": "MaskToImage", "inputs": {
            "mask": [remove, 0]}}
        graph[save] = {"class_type": "SaveImage", "inputs": {
            "images": [to_image, 0], "filename_prefix": prefix + MATTE_SUFFIX}}
    return graph
