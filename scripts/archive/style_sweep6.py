#!/usr/bin/env python3
"""Sixth Hamakaze sweep: carry the main line into the grey shadow shapes.

hs-cel (e33d07fb) is the accepted direction for the shadow itself -- grey
two-tone shapes with a hard edge -- but the line does not follow the shadow into
those areas, and hs-cel scored only 15.1% crown edge density against 23.0% for
hs-heavy-nf.

Its positive is self-contradictory, which is the first thing fixed here: it asks
for (cel shading:1.45) and (sharp shadow edges:1.35) while also asking for
(soft shading:1.3) and smooth shading. Hard shadow shapes and gradient shading
are the two halves of a choice, not a stack -- mixing them has failed before.
cl-soft keeps the pair so the cost of the contradiction is measured rather than
assumed.

The rest of the sweep carries over what sweep 5 established: strand tags only
pay at the raised weights, and they only pay with (flat color) released -- the
two are superadditive (+23% and +28% alone, +68% together). Both are constants
here, and the new axis is how hard the shadow edge is stated and whether an
explicit lineart block rides along with it.
"""

from __future__ import annotations

import argparse
import json
import urllib.request

from comfy_host import DEFAULT_HOST, DEFAULT_PORT

BASE_MODEL = "hassaku-il-v22"
SEED = 111222333
WIDTH, HEIGHT = 1024, 1280

CHAR = (
    "best quality, absurdres, 1girl, solo, hamakaze (kancolle), (grey hair:1.3), "
    "short hair, (hair over one eye:1.35), (eyes visible through hair:1.2), "
    "(blue eyes:1.25), (hairclip:1.25), hair ornament, (serafuku:1.3), "
    "(white shirt:1.25), (blue sailor collar:1.35), (yellow neckerchief:1.3), "
    "(white gloves:1.3), kantai collection, (solo:1.5), (upper body:1.4), "
    "looking at viewer, (closed mouth:1.2)"
)
FACE = "(smug:1.4), (half-closed eyes:1.3), (tareme:1.2), eyelashes, (pale skin:1.15), (realistic:1.3)"
STRAND = "(detailed hair:1.5), (defined hair strands:1.55), (hair strand outline:1.3)"

CEL = "(cel shading:1.45), (sharp shadow edges:1.35), (two-tone shading:1.3)"
CEL_HARD = ("(cel shading:1.6), (sharp shadow edges:1.5), (two-tone shading:1.4), "
            "(hard shadow edge:1.25)")
LINE = "(black lineart:1.4), (lineart:1.35), (defined lines:1.25)"

# Base render block with both the flat-colour tag and the gradient pair present,
# so every variant below is expressed as a removal from one string rather than a
# retyped list that could drift.
RENDER_FULL = (
    "(flat color:1.3), (simple background:1.3), (grey background:1.2), "
    "(white outline:1.6), outline, sticker, (soft shading:1.3), smooth shading"
)
RENDER_NOSOFT = RENDER_FULL.replace(", (soft shading:1.3), smooth shading", "")
RENDER_NOSOFT_NOFLAT = RENDER_NOSOFT.replace("(flat color:1.3), ", "")
assert RENDER_NOSOFT != RENDER_FULL, "the gradient pair moved; fix this replacement"
assert RENDER_NOSOFT_NOFLAT != RENDER_NOSOFT, "the flat-colour tag moved; fix this replacement"

NEG = (
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text, (disembodied eye:1.4), "
    "(impasto:1.25), (painterly:1.25), (oil painting (medium):1.2), "
    "(heavy shading:1.2), (detailed shading:1.2)"
)
# Banning the gradient outright rather than only declining to ask for it.
NEG_HARD = NEG + ", (gradient:1.3), (smooth shading:1.25), (blurry lines:1.2)"

# (prefix, shadow block, line block, render block, negative)
RUNGS = [
    ("cl-base",    CEL,      "",   RENDER_NOSOFT,        NEG),
    ("cl-nf",      CEL,      "",   RENDER_NOSOFT_NOFLAT, NEG),
    ("cl-ln",      CEL,      LINE, RENDER_NOSOFT,        NEG),
    ("cl-ln-nf",   CEL,      LINE, RENDER_NOSOFT_NOFLAT, NEG),
    ("cl-hard",    CEL_HARD, LINE, RENDER_NOSOFT,        NEG),
    ("cl-hard-nf", CEL_HARD, LINE, RENDER_NOSOFT_NOFLAT, NEG),
    ("cl-soft",    CEL,      LINE, RENDER_FULL,          NEG),
    ("cl-max",     CEL_HARD, LINE, RENDER_NOSOFT_NOFLAT, NEG_HARD),
]


def build(shadow, line, render, negative, prefix) -> dict:
    parts = [CHAR, FACE, STRAND, shadow] + ([line] if line else []) + [render]
    return {
        "4": {"class_type": "DiffusersLoader", "inputs": {"model_path": BASE_MODEL}},
        "60": {"class_type": "LoraLoader", "inputs": {
            "model": ["4", 0], "clip": ["4", 1], "lora_name": "outlined-ill.safetensors",
            "strength_model": 0.8, "strength_clip": 0.8}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["60", 1], "text": ", ".join(parts)}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["60", 1], "text": negative}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {
            "batch_size": 1, "width": WIDTH, "height": HEIGHT}},
        "3": {"class_type": "KSampler", "inputs": {
            "model": ["60", 0], "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["5", 0], "seed": SEED, "steps": 30, "cfg": 5.0,
            "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {
            "images": ["8", 0], "filename_prefix": prefix}},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    for prefix, shadow, line, render, negative in RUNGS:
        if args.only and prefix not in args.only:
            continue
        notes = ["cel hard" if shadow is CEL_HARD else "cel"]
        if line:
            notes.append("lineart")
        notes.append("gradient kept" if "soft shading" in render else "gradient dropped")
        if "flat color" not in render:
            notes.append("flat released")
        if negative is NEG_HARD:
            notes.append("gradient negated")
        print(f"{prefix:12s} {' + '.join(notes)}")
        if args.dry_run:
            continue
        req = urllib.request.Request(
            f"http://{args.host}:{args.port}/prompt",
            data=json.dumps({"prompt": build(shadow, line, render, negative, prefix)}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            print("   ->", json.load(resp)["prompt_id"])


if __name__ == "__main__":
    main()
