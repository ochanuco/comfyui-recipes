#!/usr/bin/env python3
"""Colour an authored lineart with the bangs conditioned separately from the rest.

Every global dial has now failed to raise the bangs against the side hair. Seven
lineart variants, three linearts through the colour pass, four ControlNet
strength/reach settings: the lineart can reach a bangs-to-side ratio of 0.70, and
the colour pass lands at 0.59-0.65 regardless of what it is handed or how hard
the ControlNet holds it. A tag that helps the bangs helps the side hair by the
same amount, because it is the same prompt for both.

So this stops asking globally. ConditioningSetMask pins a second, strand-heavy
prompt to a rectangle over the bangs, ConditioningCombine adds it to the ordinary
one, and the ControlNet is applied after the combine so the line still holds
everywhere. No custom nodes -- this is all core ComfyUI.

The mask is a rectangle rather than a traced silhouette on purpose: a rectangle
is reproducible and has three numbers to tune, and the question being asked first
is whether regional conditioning moves the ratio at all. If it does, a real mask
is worth cutting.
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

WIDTH, HEIGHT = 1024, 1280
CONTROLNET = "noob-canny-fp16.safetensors"

# The box the measurements use is x 300-760, y 30-300. The mask is a little wider
# and taller so the feather falls outside the region being scored rather than
# across it.
MASK = {"x": 240, "y": 0, "w": 580, "h": 360, "feather": 48}

BASE = (
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

# Only what the bangs are short of. Naming the character or the costume here
# would put a second face in the region.
REGION = (
    "(detailed hair:1.7), (defined hair strands:1.8), (hair strand outline:1.5), "
    "(parted bangs:1.4), (hair between eyes:1.3), "
    "(black lineart:1.45), (defined lines:1.35), (crisp lines:1.25)"
)

# (shading:1.3) belonged to the lineart pass and cancels the (cel shading:1.45)
# the colour prompt asks for; it is not carried over here.
NEGATIVE = (
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text, (disembodied eye:1.4), "
    "(impasto:1.25), (painterly:1.25), (oil painting (medium):1.2), "
    "(monochrome:1.3), (greyscale:1.3), (sketch:1.2)"
)


def build(filename: str, region_strength: float, cn_strength: float,
          cn_end: float, seed: int, prefix: str) -> dict:
    m = MASK
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": filename}},
        "2": {"class_type": "ImageInvert", "inputs": {"image": ["1", 0]}},
        "4": {"class_type": "DiffusersLoader", "inputs": {"model_path": "hassaku-il-v22"}},
        "11": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": CONTROLNET}},

        # An empty full-size mask with a filled rectangle added into it.
        "20": {"class_type": "SolidMask", "inputs": {
            "value": 0.0, "width": WIDTH, "height": HEIGHT}},
        "21": {"class_type": "SolidMask", "inputs": {
            "value": 1.0, "width": m["w"], "height": m["h"]}},
        "22": {"class_type": "MaskComposite", "inputs": {
            "destination": ["20", 0], "source": ["21", 0],
            "x": m["x"], "y": m["y"], "operation": "add"}},
        "23": {"class_type": "FeatherMask", "inputs": {
            "mask": ["22", 0], "left": m["feather"], "top": 0,
            "right": m["feather"], "bottom": m["feather"]}},

        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": BASE}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": NEGATIVE}},
        "30": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": REGION}},
        "31": {"class_type": "ConditioningSetMask", "inputs": {
            "conditioning": ["30", 0], "mask": ["23", 0],
            "strength": region_strength, "set_cond_area": "default"}},
        "32": {"class_type": "ConditioningCombine", "inputs": {
            "conditioning_1": ["6", 0], "conditioning_2": ["31", 0]}},

        # After the combine, so the line is held over the whole frame and not
        # only outside the region.
        "12": {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["32", 0], "negative": ["7", 0], "control_net": ["11", 0],
            "image": ["2", 0], "strength": cn_strength,
            "start_percent": 0.0, "end_percent": cn_end}},

        "5": {"class_type": "EmptyLatentImage", "inputs": {
            "batch_size": 1, "width": WIDTH, "height": HEIGHT}},
        "3": {"class_type": "KSampler", "inputs": {
            "model": ["4", 0], "positive": ["12", 0], "negative": ["12", 1],
            "latent_image": ["5", 0], "seed": seed, "steps": 30, "cfg": 5.0,
            "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {
            "images": ["8", 0], "filename_prefix": prefix}},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--line", default="lb-parted", help="output/ basename of the lineart")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8188)
    parser.add_argument("--region-strength", action="append", type=float, default=[],
                        help="ConditioningSetMask strength; repeat for a ladder")
    parser.add_argument("--cn-strength", type=float, default=0.6)
    parser.add_argument("--cn-end", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=111222333)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    src = OUTPUT_DIR / f"{args.line}_00001_.png"
    if not src.exists():
        raise SystemExit(f"no such lineart: {src}")
    filename = f"br-src-{args.line}.png"
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, INPUT_DIR / filename)

    for strength in args.region_strength or [0.0, 0.6, 1.0, 1.5]:
        prefix = f"br-{args.line}-r{int(round(strength * 100)):03d}"
        print(f"{prefix:26s} region={strength}  cn={args.cn_strength}/{args.cn_end}")
        if args.dry_run:
            continue
        req = urllib.request.Request(
            f"http://{args.host}:{args.port}/prompt",
            data=json.dumps({"prompt": build(
                filename, strength, args.cn_strength, args.cn_end,
                args.seed, prefix)}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            print("   ->", json.load(resp)["prompt_id"])


if __name__ == "__main__":
    main()
