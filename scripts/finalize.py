"""Finalize one chimera generation: 2048 print, clean background, record.

    uv run scripts/finalize.py <short_id> [--denoise 0.45]

Takes the picked generation's embedded graph, replays pass 1 byte-identical
and chains an image-space 2048 pass onto it (surface-preserving, the same
route every approved print has used), flattens background junk and strokes
the figure, then ingests both the raw print and the delivered version into
chimera as a refinement batch and posts the delivered one to Discord.

The pass-2 negative gets the kick toe ban and SHADE_BAN. (closed eyes:1.4)
is deliberately NOT added: the jelly line renders with ^_^ and the ban would
fight it. If an open-eyed pose comes through here, add it per-run.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import urllib.request
import uuid
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate
import outline_stroke
import post_renders
import recolor_bg
import refine_from_history as rf
import yukari_recipe as yr

WORKDIR = Path(__file__).resolve().parent.parent / ".local/_nogit/finalize"
BACKDROP_HEX = "#c7e5e9"
STROKE_HEX = "#6a3494"


def clean_background(data: bytes) -> tuple[bytes, str]:
    """Largest-component background flatten + repaint + stroke, as one step.

    Two sweeps: components the flood never touched (doodles in open backdrop),
    then, after the repaint, anything left floating on backdrop colour inside
    pockets the flood could not reach (the dress-glass gap class of junk).
    """
    backdrop = recolor_bg.parse_color(BACKDROP_HEX)
    pixels = np.array(Image.open(io.BytesIO(data)).convert("RGB")).astype(int)
    bg = recolor_bg.background_mask(pixels, 18)
    labels, n = ndimage.label(~bg)
    if n > 1:
        sizes = ndimage.sum(np.ones_like(labels), labels, range(1, n + 1))
        junk = (~bg) & (labels != 1 + int(np.argmax(sizes)))
        pixels[junk] = backdrop
    pixels, _ = recolor_bg.repaint(pixels, backdrop, enclosed_tolerance=4)
    off = np.abs(pixels - backdrop).sum(axis=2) > 30
    labels, n = ndimage.label(off)
    if n > 1:
        sizes = ndimage.sum(np.ones_like(labels), labels, range(1, n + 1))
        junk = off & (labels != 1 + int(np.argmax(sizes)))
        pixels[junk] = backdrop
    pixels, width, _ = outline_stroke.stroke(pixels.astype(float), STROKE_HEX,
                                             enclosed_tolerance=4)
    out = io.BytesIO()
    Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8)).save(out, "PNG")
    return out.getvalue(), f"clean-p{width:.0f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("short_id")
    parser.add_argument("--denoise", type=float, default=0.45)
    args = parser.parse_args()

    generate._CREDS = generate.credentials()
    ctx = generate.api("GET", f"/api/v1/generations/{args.short_id}/context")
    request = urllib.request.Request(
        f"{generate.BASE}/g/{args.short_id}/image",
        headers={**generate._CREDS, "User-Agent": post_renders.USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        picked = response.read()
    base = json.loads(Image.open(io.BytesIO(picked)).info["prompt"])
    seed = base["3"]["inputs"]["seed"]

    prefix = f"fin-{args.short_id}"
    pos = base["6"]["inputs"]["text"]
    p2_neg = ("(toes:1.55), " + yr.SHADE_BAN + base["7"]["inputs"]["text"])
    graph = rf.chain_pass(base, 2048, args.denoise, prefix,
                          prompt=(pos, p2_neg))
    prompt_id = rf.post(graph)
    print(f"{prefix} {prompt_id}")

    deadline = time.time() + 20 * 60
    while time.time() < deadline:
        entry = json.loads(urllib.request.urlopen(
            f"{comfy_base()}/history/{prompt_id}", timeout=20).read()
        ).get(prompt_id)
        if entry and post_renders.images_of(entry):
            image = post_renders.images_of(entry)[-1]
            break
        time.sleep(10)
    else:
        raise SystemExit(f"{prompt_id} timed out")
    raw = generate.fetch(image)

    delivered, tag = clean_background(raw)
    WORKDIR.mkdir(parents=True, exist_ok=True)
    stem = Path(image["filename"]).stem
    delivered_name = f"{stem}-{tag}-delivered.png"
    (WORKDIR / image["filename"]).write_bytes(raw)
    (WORKDIR / delivered_name).write_bytes(delivered)

    git = generate.git_metadata()
    batch = generate.api("POST", "/api/v1/batches", {
        "idempotency_key": str(uuid.uuid4()),
        "raw_instruction": f"{args.short_id} を高解像度化",
        "recipe": "yukari",
        "parameters": {"kind": "hires-chain",
                       "base_generation": args.short_id,
                       "size": 2048, "denoise": args.denoise},
        "git_commit": git["commit"], "git_dirty": git["dirty"],
        "references": [{"source_generation_id": args.short_id,
                        "purpose": "rebuild", "aspect": "composition",
                        "instruction": "この生成の 2048 プリント"}],
        "refinement": {"source_batch_id": ctx["batch"]["id"],
                       "actor": "human", "reason": "採用作の高解像度化"},
    })
    job = generate.api("POST", f"/api/v1/batches/{batch['id']}/jobs",
                       {"idempotency_key": str(uuid.uuid4()),
                        "seed": seed, "index": 0})
    generate.api("PATCH", f"/api/v1/jobs/{job['id']}",
                 {"status": "queued", "comfy_prompt_id": prompt_id})
    generate.api("PATCH", f"/api/v1/jobs/{job['id']}", {"status": "completed"})
    urls = []
    for idx, (name, data) in enumerate([(image["filename"], raw),
                                        (delivered_name, delivered)]):
        row = generate.api("POST", f"/api/v1/jobs/{job['id']}/generations",
                           multipart=({"seed": seed, "original_filename": name,
                                       "comfy_output_index": idx}, name, data))
        urls.append(row["canonical_url"])
        print(f"{name} -> {row['canonical_url']}")
    generate.api("PATCH", f"/api/v1/jobs/{job['id']}", {"status": "ingested"})
    generate.api("PATCH", f"/api/v1/batches/{batch['id']}",
                 {"status": "completed"})

    generate.notify(f"**finalize** `{args.short_id}`\n"
                    f"**file** `{delivered_name}`\n"
                    f"**chimera** {urls[1]}", delivered_name, delivered)
    print(f"batch {batch.get('short_id', batch['id'])} done")


def comfy_base() -> str:
    import comfy_host
    return comfy_host.base_url()


if __name__ == "__main__":
    main()
