#!/usr/bin/env python3
"""Third Hamakaze style sweep: push the face off "young and deformed", Danbooru tags only.

Sweep 2 established that LoRA strength is not the lever -- outlined-ill from 0.8
to 1.3, usnr with its trigger to 1.1, and moe-2000s all leave the same face. The
older st-ukiyoe/st-water/st-retro set says the same thing from the tag side:
naming a look ("ukiyo-e", "watercolor") moves the palette and nothing else. Only
st-chibi moved, and it moved by changing proportions.

So this sweep only touches tags that name a construction rather than a look, and
only tags that exist in Danbooru's vocabulary -- invented descriptors like
"defined jawline" or "realistic proportions" are outside the model's training
vocabulary and were dropped rather than reworded.

Two things in the accepted recipe are pulling toward the young, deformed read and
both are addressed here: (petite), (large eyes), (large iris) and small mouth in
the positive, and (realistic:1.1) sitting in the negative, where it pushes away
from adult proportions as a side effect of banning oil-paint rendering.

Framing is bust-up on purpose. At 1024x1536 full body the head is ~250px, which
is too small to judge a face on -- the notes already record one wrong call made
from contact-sheet tiles.
"""

from __future__ import annotations

import argparse
import json
import urllib.request

from comfy_host import DEFAULT_HOST, DEFAULT_PORT

BASE_MODEL = "hassaku-il-v22"
LORA = ("outlined-ill.safetensors", 0.8)
SEED = 111222333
WIDTH, HEIGHT = 1024, 1280

# Character and costume: held byte-identical across every variant so the only
# axis that moves is the face block.
CHAR = (
    "best quality, absurdres, 1girl, solo, hamakaze (kancolle), (grey hair:1.3), "
    "short hair, (hair over one eye:1.35), (eyes visible through hair:1.2), "
    "(blue eyes:1.25), (hairclip:1.25), hair ornament, (serafuku:1.3), "
    "(white shirt:1.25), (blue sailor collar:1.35), (yellow neckerchief:1.3), "
    "(white gloves:1.3), kantai collection, (solo:1.5), (upper body:1.4), "
    "looking at viewer, (closed mouth:1.2)"
)

RENDER = (
    "(flat color:1.3), (simple background:1.3), (grey background:1.2), "
    "(white outline:1.6), outline, sticker, (soft shading:1.3), smooth shading"
)

# The accepted recipe's face block, and the same block with the five tags that
# make a face read young removed. Everything downstream builds on SUB.
FACE_CTL = (
    "(smug:1.4), (half-closed eyes:1.3), (tareme:1.3), (large eyes:1.3), "
    "2000s (style), eyelashes, (large iris:1.25), thin eyebrows, small mouth, "
    "(petite:1.2), (pale skin:1.25)"
)
FACE_SUB = "(smug:1.4), (half-closed eyes:1.3), (tareme:1.2), eyelashes, (pale skin:1.15)"
# tsurime is the Danbooru opposite of tareme; swapping them is a construction
# change, not a restyle, which is why it gets its own rung.
FACE_TSURIME = (
    "(smug:1.4), (half-closed eyes:1.3), (tsurime:1.4), (narrow eyes:1.2), "
    "(thick eyebrows:1.15), eyelashes, (pale skin:1.15)"
)

NEG_CORE = (
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text, (disembodied eye:1.4)"
)
ANTI_PAINT = (
    ", (impasto:1.25), (painterly:1.25), (oil painting (medium):1.2), "
    "(heavy shading:1.2), (detailed shading:1.2)"
)
NEG_CTL = NEG_CORE + ANTI_PAINT + ", (realistic:1.1)"
NEG_SUB = NEG_CORE + ANTI_PAINT  # realistic released

VARIANTS = [
    ("db-ctl", FACE_CTL, NEG_CTL),
    ("db-sub", FACE_SUB, NEG_SUB),
    ("db-mature", FACE_SUB + ", (mature female:1.4), (aged up:1.3), eyeshadow", NEG_SUB),
    ("db-tsurime", FACE_TSURIME, NEG_SUB),
    ("db-tall", FACE_SUB + ", (tall female:1.35), (mature female:1.2)", NEG_SUB),
    ("db-90s", FACE_SUB + ", (1990s (style):1.5), (retro artstyle:1.35), thick eyebrows", NEG_SUB),
    ("db-80s", FACE_SUB + ", (1980s (style):1.5), (retro artstyle:1.35)", NEG_SUB),
    ("db-real", FACE_SUB + ", (realistic:1.3)", NEG_SUB),
    ("db-manga", FACE_SUB + ", (screentone:1.5), (halftone:1.3), (greyscale:1.2), "
                            "(traditional media:1.2)", NEG_SUB),
    ("db-all", FACE_TSURIME + ", (mature female:1.4), (aged up:1.3), (tall female:1.3), "
                              "(realistic:1.15)", NEG_SUB),
]


def build(face: str, negative: str, prefix: str) -> dict:
    return {
        "4": {"class_type": "DiffusersLoader", "inputs": {"model_path": BASE_MODEL}},
        "60": {"class_type": "LoraLoader", "inputs": {
            "model": ["4", 0], "clip": ["4", 1], "lora_name": LORA[0],
            "strength_model": LORA[1], "strength_clip": LORA[1]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["60", 1], "text": f"{CHAR}, {face}, {RENDER}"}},
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

    for prefix, face, negative in VARIANTS:
        if args.only and prefix not in args.only:
            continue
        print(f"{prefix:12s} {face[:88]}")
        if args.dry_run:
            continue
        req = urllib.request.Request(
            f"http://{args.host}:{args.port}/prompt",
            data=json.dumps({"prompt": build(face, negative, prefix)}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            print("   ->", json.load(resp)["prompt_id"])


if __name__ == "__main__":
    main()
