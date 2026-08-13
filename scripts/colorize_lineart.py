#!/usr/bin/env python3
"""Second pass of "line first, then colour": colour an authored lineart via ControlNet.

Pass 1 (ln-lineart / ln-coloring) established the thing every prompt-side sweep
had failed to get: with no fill available, hassaku draws the bangs as strands
rather than as a plane. Six extractors across three sensitivities could not
recover those lines from a finished flat-coloured render, because they were
never drawn -- so the line has to exist before the colour does.

This pass holds that lineart with a ControlNet and renders colour under it. The
axis is ControlNet strength and how long it stays engaged: too weak and the
colour pass redraws the hair as a mass again, which is the failure this whole
approach exists to avoid; too strong and the render is a tinted line drawing
with no shading of its own.

The lineart is black-on-white and the ControlNets here expect white-on-black, so
it is inverted before it is handed over.
"""

from __future__ import annotations

import argparse
import json
import shutil
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO / ".local/ComfyUI/output"
INPUT_DIR = REPO / ".local/ComfyUI/input"

# invert: canny and softedge are trained on white-on-black edge maps, so a
# black-on-white lineart has to be flipped for them. lineart_anime is trained on
# the drawing itself and takes it as it is -- feeding it an inverted one is
# handing it a photographic negative of what it expects.
CONTROLNETS = {
    "canny": ("noob-canny-fp16.safetensors", True),
    "softedge": ("ill-softedge-fp16.safetensors", True),
    "lineart": ("noob-lineart-anime-fp16.safetensors", False),
}

# The colour prompt, minus every tag that flattens a mass. (flat color) and the
# sticker block are deliberately gone: they are what erased the strand lines in
# the first place, and the ControlNet is now what holds the drawing together.
POSITIVE = (
    "best quality, absurdres, 1girl, solo, hamakaze (kancolle), (grey hair:1.3), "
    "short hair, (hair over one eye:1.35), (eyes visible through hair:1.2), "
    "(blue eyes:1.25), (hairclip:1.25), hair ornament, (serafuku:1.3), "
    "(white shirt:1.25), (blue sailor collar:1.35), (yellow neckerchief:1.3), "
    "kantai collection, (solo:1.5), (upper body:1.4), looking at viewer, "
    "(closed mouth:1.2), (smug:1.4), (half-closed eyes:1.3), (tareme:1.2), "
    "eyelashes, (pale skin:1.15), (realistic:1.3), "
    "(detailed hair:1.5), (defined hair strands:1.55), (hair strand outline:1.3), "
    "(black lineart:1.35), (defined lines:1.25), "
    "(cel shading:1.45), (sharp shadow edges:1.35), (two-tone shading:1.3), "
    "(simple background:1.3), (grey background:1.2)"
)
NEGATIVE = (
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text, (disembodied eye:1.4), "
    "(impasto:1.25), (painterly:1.25), (oil painting (medium):1.2), "
    "(monochrome:1.3), (greyscale:1.3), (sketch:1.2)"
)

RUNGS = [
    ("s60-e80", 0.6, 0.8),
    # Strength and reach are separate questions and the first ladder confounded
    # them. Releasing at 80% hands the last fifth of the render back to the
    # colour pass, which is where a lineart's extra bangs detail was suspected of
    # being redrawn away; this rung holds the same strength to the end instead.
    ("s60-e100", 0.6, 1.0),
    ("s80-e80", 0.8, 0.8),
    ("s80-e100", 0.8, 1.0),
    ("s100-e100", 1.0, 1.0),
]


def build(filename: str, controlnet: str, invert: bool, strength: float,
          end: float, seed: int, prefix: str) -> dict:
    hint = ["2", 0] if invert else ["1", 0]
    graph = {
        "1": {"class_type": "LoadImage", "inputs": {"image": filename}},
        "4": {"class_type": "DiffusersLoader", "inputs": {"model_path": "hassaku-il-v22"}},
        "11": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": controlnet}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": POSITIVE}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": NEGATIVE}},
        "12": {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["6", 0], "negative": ["7", 0], "control_net": ["11", 0],
            "image": hint, "strength": strength,
            "start_percent": 0.0, "end_percent": end}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {
            "batch_size": 1, "width": 1024, "height": 1280}},
        "3": {"class_type": "KSampler", "inputs": {
            "model": ["4", 0], "positive": ["12", 0], "negative": ["12", 1],
            "latent_image": ["5", 0], "seed": seed, "steps": 30, "cfg": 5.0,
            "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {
            "images": ["8", 0], "filename_prefix": prefix}},
    }
    if invert:
        graph["2"] = {"class_type": "ImageInvert", "inputs": {"image": ["1", 0]}}
    return graph


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--line", default="ln-lineart", help="output/ basename of the pass-1 lineart")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8188)
    parser.add_argument("--controlnet", choices=sorted(CONTROLNETS), default="canny")
    parser.add_argument("--seed", type=int, default=111222333)
    parser.add_argument(
        "--only", action="append", default=[], choices=[r[0] for r in RUNGS],
        help="run just these strength rungs; the ladder is for comparing, "
             "s60-e80 is the one to use")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    src = OUTPUT_DIR / f"{args.line}_00001_.png"
    if not src.exists():
        raise SystemExit(f"no such lineart: {src}")
    filename = f"cz-src-{args.line}.png"
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, INPUT_DIR / filename)

    controlnet, invert = CONTROLNETS[args.controlnet]
    for suffix, strength, end in RUNGS:
        if args.only and suffix not in args.only:
            continue
        prefix = f"cz-{args.line}-{args.controlnet}-{suffix}"
        print(f"{prefix:34s} strength={strength} end={end}"
              f" hint={'inverted' if invert else 'as drawn'}")
        if args.dry_run:
            continue
        req = urllib.request.Request(
            f"http://{args.host}:{args.port}/prompt",
            data=json.dumps({"prompt": build(
                filename, controlnet, invert, strength, end,
                args.seed, prefix)}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            print("   ->", json.load(resp)["prompt_id"])


if __name__ == "__main__":
    main()
