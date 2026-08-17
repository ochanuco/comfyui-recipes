#!/usr/bin/env python3
"""Refine one already-rendered prompt by replaying its exact graph plus a second pass.

The first pass is taken verbatim from /history, so the composition it decided is
the composition that gets redrawn -- no reconstruction from the recipe, and no
chance of a tag-order difference changing the picture.
"""
import json
import sys
import urllib.request

HOST = "192.168.7.253"
PORT = 8188
SRC = "4c146593-e261-4b0c-9baa-807ca2be0421"
HIRES = 2048


def fetch_prompt(pid):
    with urllib.request.urlopen(f"http://{HOST}:{PORT}/history/{pid}", timeout=20) as r:
        d = json.load(r)
    return d[pid]["prompt"][2]


def post(graph):
    req = urllib.request.Request(
        f"http://{HOST}:{PORT}/prompt",
        data=json.dumps({"prompt": graph}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["prompt_id"]


def sizes(base):
    w = base["5"]["inputs"]["width"]
    h = base["5"]["inputs"]["height"]
    longest = max(w, h)
    return (round(HIRES * w / longest / 8) * 8, round(HIRES * h / longest / 8) * 8)


def latent_route(base, denoise, prefix):
    """The recipe's own --hires path: bicubic on the latent, denoise 0.60."""
    g = json.loads(json.dumps(base))
    w, h = sizes(base)
    g["10"] = {"class_type": "LatentUpscale", "inputs": {
        "samples": ["3", 0], "upscale_method": "bicubic",
        "width": w, "height": h, "crop": "disabled"}}
    g["11"] = {"class_type": "KSampler", "inputs": {
        "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
        "latent_image": ["10", 0], "seed": g["3"]["inputs"]["seed"],
        "steps": 30, "cfg": 5.0, "sampler_name": "dpmpp_2m",
        "scheduler": "karras", "denoise": denoise}}
    g["8"]["inputs"]["samples"] = ["11", 0]
    g["9"]["inputs"]["filename_prefix"] = prefix
    return g


def image_route(base, denoise, prefix):
    """The nape session's path: decode, resample in image space with lanczos,
    encode back. The resampler gets eight times the detail to interpolate."""
    g = json.loads(json.dumps(base))
    w, h = sizes(base)
    g["8"]["inputs"]["samples"] = ["3", 0]          # decode the first pass
    g["12"] = {"class_type": "ImageScale", "inputs": {
        "image": ["8", 0], "upscale_method": "lanczos",
        "width": w, "height": h, "crop": "disabled"}}
    g["13"] = {"class_type": "VAEEncode", "inputs": {
        "pixels": ["12", 0], "vae": ["4", 2]}}
    g["11"] = {"class_type": "KSampler", "inputs": {
        "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
        "latent_image": ["13", 0], "seed": g["3"]["inputs"]["seed"],
        "steps": 30, "cfg": 5.0, "sampler_name": "dpmpp_2m",
        "scheduler": "karras", "denoise": denoise}}
    g["14"] = {"class_type": "VAEDecode", "inputs": {
        "samples": ["11", 0], "vae": ["4", 2]}}
    g["9"]["inputs"]["images"] = ["14", 0]
    g["9"]["inputs"]["filename_prefix"] = prefix
    return g


if __name__ == "__main__":
    base = fetch_prompt(SRC)
    print("first pass:", base["5"]["inputs"], "seed", base["3"]["inputs"]["seed"])
    print("second pass size:", sizes(base))
    for name, graph in [
        ("rf-latent-060", latent_route(base, 0.60, "rf-latent-060")),
        ("rf-image-045", image_route(base, 0.45, "rf-image-045")),
        ("rf-image-060", image_route(base, 0.60, "rf-image-060")),
    ]:
        print(name, post(graph), flush=True)
