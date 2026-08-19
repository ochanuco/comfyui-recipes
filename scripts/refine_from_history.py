#!/usr/bin/env python3
"""Refine one already-rendered prompt by replaying its exact graph plus another pass.

The earlier passes are taken verbatim from /history, so the composition they
decided is the composition that gets redrawn -- no reconstruction from the
recipe, and no chance of a tag-order difference changing the picture.

    refine_from_history.py <prompt_id>                       # second pass, 2048
    refine_from_history.py <prompt_id> --chain               # append to a refined one
    refine_from_history.py <prompt_id> --chain --pose boss --denoise 0.60

`--chain` appends onto a render that already has a second pass instead of
replacing it, and `--pose` re-encodes the prompt from the current recipe rather
than reusing the stored one -- which is how a picture whose shading was already
approved takes corrections made to the recipe afterwards.

**A cheap pass deletes; it does not add.** At 0.35 the chained pass removed a
button placket the recipe had since banned and left newly-added halter straps as
a faint suggestion. 0.60 drew the straps properly and the approved shading still
survived. Removing something the prompt now forbids is nearly free; drawing
something the base does not contain costs real denoise.
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


def last_decode(graph):
    """The node holding the finished picture: the VAEDecode SaveImage reads."""
    return graph["9"]["inputs"]["images"][0]


def chain_pass(base, size, denoise, prefix, prompt=None):
    """Append one more image-space pass onto whatever the graph already ends in.

    Node ids are allocated above whatever the graph already uses, so this can be
    applied to a render that was itself produced this way. Fixed ids worked
    exactly once: chaining onto a chained graph silently overwrote the previous
    pass and drew the same picture again.
    """
    g = json.loads(json.dumps(base))
    n = max(int(k) for k in g) + 1
    scale, encode, sample, decode = str(n), str(n + 1), str(n + 2), str(n + 3)
    pos, neg = ["6", 0], ["7", 0]
    if prompt:
        p_pos, p_neg = str(n + 4), str(n + 5)
        g[p_pos] = {"class_type": "CLIPTextEncode",
                    "inputs": {"clip": ["4", 1], "text": prompt[0]}}
        g[p_neg] = {"class_type": "CLIPTextEncode",
                    "inputs": {"clip": ["4", 1], "text": prompt[1]}}
        pos, neg = [p_pos, 0], [p_neg, 0]
    tail = last_decode(g)
    # Aspect, not a square. This read `width: size, height: size`, which is the
    # same number for the square renders it had only ever been run on and a
    # squash for anything else -- found when `kick` arrived at 1024x1536. The
    # sizes() helper is what the other two routes already use.
    w, h = sizes(g)
    g[scale] = {"class_type": "ImageScale", "inputs": {
        "image": [tail, 0], "upscale_method": "lanczos",
        "width": w, "height": h, "crop": "disabled"}}
    g[encode] = {"class_type": "VAEEncode",
                 "inputs": {"pixels": [scale, 0], "vae": ["4", 2]}}
    g[sample] = {"class_type": "KSampler", "inputs": {
        "model": ["4", 0], "positive": pos, "negative": neg,
        "latent_image": [encode, 0], "seed": g["3"]["inputs"]["seed"],
        "steps": 30, "cfg": 5.0, "sampler_name": "dpmpp_2m",
        "scheduler": "karras", "denoise": denoise}}
    g[decode] = {"class_type": "VAEDecode",
                 "inputs": {"samples": [sample, 0], "vae": ["4", 2]}}
    g["9"]["inputs"]["images"] = [decode, 0]
    g["9"]["inputs"]["filename_prefix"] = prefix
    return g


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
    ap.add_argument("--chain", action="store_true",
                    help="append a pass onto a render that already has one")
    ap.add_argument("--pose",
                    help="with --chain, re-encode the prompt from the current "
                         "recipe for this pose instead of reusing the stored one")
    args = ap.parse_args()

    HOST, PORT, HIRES = args.host, args.port, args.hires
    base = fetch_prompt(args.prompt_id)
    print("first pass:", base["5"]["inputs"], "seed", base["3"]["inputs"]["seed"])
    print("second pass:", sizes(base))
    if args.chain:
        prompt = None
        if args.pose:
            import yukari_recipe
            fresh = yukari_recipe.build(args.pose, base["3"]["inputs"]["seed"], "tmp")
            prompt = (fresh["6"]["inputs"]["text"], fresh["7"]["inputs"]["text"])
        jobs = [(args.prefix, chain_pass(base, args.hires, args.denoise,
                                         args.prefix, prompt))]
    elif args.sweep:
        jobs = [(f"{args.prefix}-latent-060", latent_route(base, 0.60, f"{args.prefix}-latent-060")),
                (f"{args.prefix}-image-045", image_route(base, 0.45, f"{args.prefix}-image-045")),
                (f"{args.prefix}-image-060", image_route(base, 0.60, f"{args.prefix}-image-060"))]
    else:
        route = image_route if args.route == "image" else latent_route
        jobs = [(args.prefix, route(base, args.denoise, args.prefix))]
    for name, graph in jobs:
        print(name, post(graph), flush=True)
