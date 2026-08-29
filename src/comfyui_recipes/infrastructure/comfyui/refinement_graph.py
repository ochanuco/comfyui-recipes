"""ComfyUI graph transformation for the delivery redraw."""

from __future__ import annotations

import json


def sizes(graph: dict, longest_side: int) -> tuple[int, int]:
    width = graph["5"]["inputs"]["width"]
    height = graph["5"]["inputs"]["height"]
    longest = max(width, height)
    return (round(longest_side * width / longest / 8) * 8,
            round(longest_side * height / longest / 8) * 8)


def chain_pass(base: dict, size: int, denoise: float, prefix: str,
               prompt: tuple[str, str] | None = None) -> dict:
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
    scale, sample, decode = (str(next_id + offset) for offset in range(3))
    positive, negative = ["6", 0], ["7", 0]
    if prompt:
        positive_id, negative_id = str(next_id + 3), str(next_id + 4)
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
    graph[scale] = {"class_type": "LatentUpscale", "inputs": {
        "samples": tail["inputs"]["samples"], "upscale_method": "bicubic",
        "width": width, "height": height, "crop": "disabled"}}
    graph[sample] = {"class_type": "KSampler", "inputs": {
        "model": ["4", 0], "positive": positive, "negative": negative,
        "latent_image": [scale, 0], "seed": graph["3"]["inputs"]["seed"],
        "steps": 30, "cfg": 5.0, "sampler_name": "dpmpp_2m",
        "scheduler": "karras", "denoise": denoise}}
    graph[decode] = {"class_type": "VAEDecode", "inputs": {
        "samples": [sample, 0], "vae": ["4", 2]}}
    graph["9"]["inputs"]["images"] = [decode, 0]
    graph["9"]["inputs"]["filename_prefix"] = prefix
    return graph
