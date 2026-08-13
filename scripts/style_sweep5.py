#!/usr/bin/env python3
"""Fifth Hamakaze sweep: drive main lines into the flat-filled hair mass.

hr-real-st (682a6e05) is the accepted direction -- (detailed hair), (defined hair
strands) and hair strand outline put strand lines at the parting and the hair
ends. What they do not do is divide the crown: that mass stays empty, and what
occupies it instead is a single large specular highlight the base draws by
default.

So this sweep separates the two candidate reasons the crown stays empty and
tests each on its own rung before combining them:

- the mass is forbidden from carrying interior variation -- (flat color:1.3);
  sweep 4's nf rung released it alone and barely moved, so here it is only
  released in combination.
- the mass is already occupied -- the highlight blob leaves no room for a line,
  which makes (shiny hair)/(hair highlights) in the negative a line lever rather
  than a gloss one.

Cel shading gets a rung too. It is not a line tag, but hard shadow edges divide
a flat mass into shapes, which is the same read as a drawn strand boundary and
may reach the crown where a strand tag does not.

Held from sweep 4: hassaku, the "real" face, seed, framing, and the strand block
itself, so any change is attributable to the rung.
"""

from __future__ import annotations

import argparse
import json
import urllib.request

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

STRAND = "(detailed hair:1.3), (defined hair strands:1.35), hair strand outline"
STRAND_HEAVY = "(detailed hair:1.5), (defined hair strands:1.55), (hair strand outline:1.3)"

RENDER_FLAT = (
    "(flat color:1.3), (simple background:1.3), (grey background:1.2), "
    "(white outline:1.6), outline, sticker, (soft shading:1.3), smooth shading"
)
RENDER_NOFLAT = RENDER_FLAT.replace("(flat color:1.3), ", "")
assert RENDER_NOFLAT != RENDER_FLAT, "the flat-colour tag moved; fix this replacement"

NEG_BASE = (
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text, (disembodied eye:1.4), "
    "(impasto:1.25), (painterly:1.25), (oil painting (medium):1.2), "
    "(heavy shading:1.2), (detailed shading:1.2)"
)
# Clearing the crown so a line has somewhere to land. Named as a line lever on
# purpose -- it is the blob, not the shading level, that is in the way.
NEG_NOGLOSS = NEG_BASE + ", (shiny hair:1.3), (glossy hair:1.25), (hair highlights:1.2)"

# (prefix, strand block, extra positive, render block, negative, lora strength)
RUNGS = [
    ("hs-nf",       STRAND,       "", RENDER_NOFLAT, NEG_BASE,    0.8),
    ("hs-heavy",    STRAND_HEAVY, "", RENDER_FLAT,   NEG_BASE,    0.8),
    ("hs-heavy-nf", STRAND_HEAVY, "", RENDER_NOFLAT, NEG_BASE,    0.8),
    ("hs-nogloss",  STRAND,       "", RENDER_FLAT,   NEG_NOGLOSS, 0.8),
    ("hs-lora11",   STRAND,       "", RENDER_FLAT,   NEG_BASE,    1.1),
    ("hs-lineart",  STRAND, "(lineart:1.35), (black lineart:1.4)", RENDER_NOFLAT, NEG_BASE, 0.8),
    ("hs-cel",      STRAND,
     "(cel shading:1.45), (sharp shadow edges:1.35), (two-tone shading:1.3)",
     RENDER_FLAT, NEG_BASE, 0.8),
    ("hs-all",      STRAND_HEAVY, "", RENDER_NOFLAT, NEG_NOGLOSS, 1.1),
]


def build(strand, extra, render, negative, lora_strength, prefix) -> dict:
    parts = [CHAR, FACE, strand] + ([extra] if extra else []) + [render]
    return {
        "4": {"class_type": "DiffusersLoader", "inputs": {"model_path": BASE_MODEL}},
        "60": {"class_type": "LoraLoader", "inputs": {
            "model": ["4", 0], "clip": ["4", 1], "lora_name": "outlined-ill.safetensors",
            "strength_model": lora_strength, "strength_clip": lora_strength}},
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
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8188)
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    for prefix, strand, extra, render, negative, lora in RUNGS:
        if args.only and prefix not in args.only:
            continue
        notes = []
        if strand is STRAND_HEAVY:
            notes.append("strands up")
        if "flat color" not in render:
            notes.append("flat released")
        if negative is NEG_NOGLOSS:
            notes.append("gloss negated")
        if lora != 0.8:
            notes.append(f"lora {lora}")
        if extra:
            notes.append(extra)
        print(f"{prefix:13s} {' + '.join(notes)}")
        if args.dry_run:
            continue
        req = urllib.request.Request(
            f"http://{args.host}:{args.port}/prompt",
            data=json.dumps({"prompt": build(
                strand, extra, render, negative, lora, prefix)}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            print("   ->", json.load(resp)["prompt_id"])


if __name__ == "__main__":
    main()
