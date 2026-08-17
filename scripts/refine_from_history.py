#!/usr/bin/env python3
"""Refine one already-rendered prompt by replaying its exact graph plus a second pass.

The first pass is taken verbatim from /history, so the composition it decided is
the composition that gets redrawn -- no reconstruction from the recipe, and no
chance of a tag-order difference changing the picture.
"""
import argparse
import json
import urllib.request

from comfy_host import DEFAULT_HOST, DEFAULT_PORT

HOST = DEFAULT_HOST
PORT = DEFAULT_PORT
HIRES = 2048

DEFAULT_HIRES = 2048


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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("prompt_id", help="a finished prompt id from /history")
    ap.add_argument("--prefix", default="rf")
    ap.add_argument("--hires", type=int, default=DEFAULT_HIRES)
    ap.add_argument("--denoise", type=float, default=0.45)
    ap.add_argument("--route", choices=("image", "latent"), default="image",
                    help="image-space lanczos, or the recipe's latent bicubic")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--sweep", action="store_true",
                    help="submit all three measured combinations instead of one")
    args = ap.parse_args()

    HOST, PORT, HIRES = args.host, args.port, args.hires
    base = fetch_prompt(args.prompt_id)
    print("first pass:", base["5"]["inputs"], "seed", base["3"]["inputs"]["seed"])
    print("second pass:", sizes(base))
    if args.sweep:
        jobs = [(f"{args.prefix}-latent-060", latent_route(base, 0.60, f"{args.prefix}-latent-060")),
                (f"{args.prefix}-image-045", image_route(base, 0.45, f"{args.prefix}-image-045")),
                (f"{args.prefix}-image-060", image_route(base, 0.60, f"{args.prefix}-image-060"))]
    else:
        route = image_route if args.route == "image" else latent_route
        jobs = [(args.prefix, route(base, args.denoise, args.prefix))]
    for name, graph in jobs:
        print(name, post(graph), flush=True)
