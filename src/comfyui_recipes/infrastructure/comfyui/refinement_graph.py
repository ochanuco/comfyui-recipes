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
               matte_model: str | None = None) -> dict:
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
    positive, negative = ["6", 0], ["7", 0]
    if prompt:
        positive_id, negative_id = str(next_id + 4), str(next_id + 5)
        graph[positive_id] = {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["4", 1], "text": prompt[0]}}
        graph[negative_id] = {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["4", 1], "text": prompt[1]}}
        positive, negative = [positive_id, 0], [negative_id, 0]
    tail = graph[graph["9"]["inputs"]["images"][0]]
    if tail.get("class_type") != "VAEDecode":
        raise ValueError(
            "base graph's SaveImage must be fed by a VAEDecode, got "
            f"{tail.get('class_type')!r}")
    width, height = sizes(graph, size)
    # The upscale runs in pixel space, through the base pass's own decode.
    # Upscaling the latent instead puts a staircase on every hard contour
    # (one latent pixel is eight image pixels) that survives the redraw at
    # the delivery denoise; only a much deeper redraw could paint over it.
    graph[scale] = {"class_type": "ImageScale", "inputs": {
        "image": graph["9"]["inputs"]["images"], "upscale_method": "bicubic",
        "width": width, "height": height, "crop": "disabled"}}
    graph[encode] = {"class_type": "VAEEncode", "inputs": {
        "pixels": [scale, 0], "vae": ["4", 2]}}
    graph[sample] = {"class_type": "KSampler", "inputs": {
        "model": ["4", 0], "positive": positive, "negative": negative,
        "latent_image": [encode, 0], "seed": graph["3"]["inputs"]["seed"],
        "steps": 30, "cfg": 5.0, "sampler_name": "dpmpp_2m",
        "scheduler": "karras", "denoise": denoise}}
    graph[decode] = {"class_type": "VAEDecode", "inputs": {
        "samples": [sample, 0], "vae": ["4", 2]}}
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
