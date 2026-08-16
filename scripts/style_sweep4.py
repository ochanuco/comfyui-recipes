#!/usr/bin/env python3
"""Fourth Hamakaze sweep: interior hair linework on the two accepted faces.

db-real (c1ed7c64) and db-tall (3a9cdbb0) are the accepted results from sweep 3.
Both are kept byte-identical here except for one hair/line block, so the axis is
only "how much drawn line lands inside the hair mass", not the face.

Two constraints come out of earlier work rather than guesswork:

- "thin lineart" is not usable on this character. The warm-room scene's
  (thin lineart:1.45) block lowered ink coverage on 3/3 seeds when copied onto
  Hamakaze -- the qualifier is obeyed literally. The block that did work drops
  "thin" and keeps (black outline), (defined lines), (crisp lines).
- (flat color:1.3) is the suspected suppressor: it forbids interior tonal
  separation, and hair strand lines are exactly that. So it gets its own rung
  (nf) instead of being bundled into the line block, otherwise a win could not
  be attributed.
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

CHAR = (
    "best quality, absurdres, 1girl, solo, hamakaze (kancolle), (grey hair:1.3), "
    "short hair, (hair over one eye:1.35), (eyes visible through hair:1.2), "
    "(blue eyes:1.25), (hairclip:1.25), hair ornament, (serafuku:1.3), "
    "(white shirt:1.25), (blue sailor collar:1.35), (yellow neckerchief:1.3), "
    "(white gloves:1.3), kantai collection, (solo:1.5), (upper body:1.4), "
    "looking at viewer, (closed mouth:1.2)"
)

FACE_SUB = "(smug:1.4), (half-closed eyes:1.3), (tareme:1.2), eyelashes, (pale skin:1.15)"
FACES = {
    "real": FACE_SUB + ", (realistic:1.3)",
    "tall": FACE_SUB + ", (tall female:1.35), (mature female:1.2)",
}

RENDER_FLAT = (
    "(flat color:1.3), (simple background:1.3), (grey background:1.2), "
    "(white outline:1.6), outline, sticker, (soft shading:1.3), smooth shading"
)
# Same block with flat color released; everything else about the look is meant
# to stay identical, so it is derived rather than retyped.
RENDER_NOFLAT = RENDER_FLAT.replace("(flat color:1.3), ", "")
assert RENDER_NOFLAT != RENDER_FLAT, "the flat-colour tag moved; fix this replacement"

LINE = "(black lineart:1.35), (defined lines:1.25), (crisp lines:1.2)"
STRAND = "(detailed hair:1.3), (defined hair strands:1.35), hair strand outline"

# (suffix, extra tags appended after the face block, render block)
RUNGS = [
    ("ln", LINE, RENDER_FLAT),
    ("st", STRAND, RENDER_FLAT),
    ("nf", "", RENDER_NOFLAT),
    ("ab", f"{LINE}, {STRAND}", RENDER_FLAT),
    ("abc", f"{LINE}, {STRAND}", RENDER_NOFLAT),
]

NEG = (
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text, (disembodied eye:1.4), "
    "(impasto:1.25), (painterly:1.25), (oil painting (medium):1.2), "
    "(heavy shading:1.2), (detailed shading:1.2)"
)


def build(face: str, extra: str, render: str, prefix: str) -> dict:
    positive = f"{CHAR}, {face}, {render}" if not extra else f"{CHAR}, {face}, {extra}, {render}"
    return {
        "4": {"class_type": "DiffusersLoader", "inputs": {"model_path": BASE_MODEL}},
        "60": {"class_type": "LoraLoader", "inputs": {
            "model": ["4", 0], "clip": ["4", 1], "lora_name": LORA[0],
            "strength_model": LORA[1], "strength_clip": LORA[1]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["60", 1], "text": positive}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["60", 1], "text": NEG}},
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
    parser.add_argument("--face", action="append", default=[], choices=sorted(FACES))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    for face_key in args.face or sorted(FACES):
        for suffix, extra, render in RUNGS:
            prefix = f"hr-{face_key}-{suffix}"
            print(f"{prefix:14s} {extra or '(no line tags)'}"
                  f"{'  [flat released]' if 'flat color' not in render else ''}")
            if args.dry_run:
                continue
            req = urllib.request.Request(
                f"http://{args.host}:{args.port}/prompt",
                data=json.dumps({"prompt": build(
                    FACES[face_key], extra, render, prefix)}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                print("   ->", json.load(resp)["prompt_id"])


if __name__ == "__main__":
    main()
