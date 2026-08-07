#!/usr/bin/env python3
"""Erase a stray figure from a portrait's backdrop by inpainting over it.

Some checkpoints fill empty backdrop with a second character -- a flat black
silhouette carrying eyes, standing beside the subject. Nine prompt-side attempts
failed to stop it (raising the anti-shadow and anti-monster negatives made it
larger, removing the sticker/outline block made it larger still, and neither
background weights nor solo-focus tags moved it), and it is seed-dependent, so
it is dealt with after the fact instead.

Repainting the backdrop cannot remove it: the sticker outline wraps subject and
intruder together, so a border flood stops at the intruder and a connected-
component pass finds one blob covering both. What separates them is colour --
the intruder is drawn in flat black and flat white, while everything legitimate
nearby (a tan staff, a teal cape, yellow gloves) is chromatic. So the mask is
built from achromatic extremes and the chromatic pixels are given back.

The generation settings are read from the source PNG's own `prompt` chunk, so
the same checkpoint, LoRAs and VAE are reused without restating them. The
positive prompt is replaced with a backdrop-only one: the original asks for a
girl, and would draw another one into the hole.

    uv run scripts/erase_intruder.py output/hf-4051776310_00001_.png \
        --zone 90 0 590 530 --dry-run     # check the mask overlay first
    uv run scripts/erase_intruder.py output/hf-4051776310_00001_.png \
        --zone 90 0 590 530

Run it again on its own output to clear thin remnants, narrowing --zone to keep
the subject's own dark hair out of the second mask.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, binary_fill_holes, label

# The hole is filled with backdrop, not with whatever the portrait asked for.
INPAINT_POSITIVE = (
    "masterpiece, best quality, absurdres, "
    "(simple background:1.5), (grey background:1.6), plain background, "
    "(flat background:1.4), (no scenery:1.3), empty"
)
INPAINT_NEGATIVE_EXTRA = (
    ", 1girl, 2girls, face, eyes, hair, person, character, monster, "
    "silhouette, shadow, object, pattern, gradient"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", type=Path, help="a PNG written by ComfyUI (carries its own graph)")
    parser.add_argument("--zone", type=int, nargs=4, required=True,
                        metavar=("X0", "Y0", "X1", "Y1"),
                        help="the corner the intruder occupies; keep it clear of the subject")
    parser.add_argument("--dark", type=int, default=70,
                        help="max channel below which a pixel counts as the intruder's black")
    parser.add_argument("--white", type=int, default=205,
                        help="min channel above which a pixel counts as its white")
    parser.add_argument("--saturation", type=int, default=40,
                        help="above this, a pixel is chromatic and therefore protected")
    parser.add_argument("--min-blob", type=int, default=2500,
                        help="smaller runs of black or white are outline strokes, not the figure")
    parser.add_argument("--grow", type=int, default=3, help="dilation passes of a 9x9 kernel")
    parser.add_argument("--seed", type=int, default=77120445)
    parser.add_argument("--prefix", default="erased")
    parser.add_argument("--dry-run", action="store_true",
                        help="write the mask and an overlay, queue nothing")
    parser.add_argument("--comfy-root", type=Path, default=Path(".local/ComfyUI"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8188)
    return parser.parse_args()


def build_mask(pixels: np.ndarray, args: argparse.Namespace) -> np.ndarray:
    height, width, _ = pixels.shape
    x0, y0, x1, y1 = args.zone
    zone = np.zeros((height, width), dtype=bool)
    zone[y0:y1, x0:x1] = True

    saturation = pixels.max(axis=2) - pixels.min(axis=2)
    extreme = (pixels.max(axis=2) < args.dark) | (pixels.min(axis=2) > args.white)

    labels, _ = label(extreme & zone)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    blobs = np.isin(labels, np.where(sizes > args.min_blob)[0])

    mask = binary_fill_holes(blobs)
    mask = binary_dilation(mask, np.ones((9, 9)), iterations=args.grow) & zone
    # Hand back the staff, cape and gloves the dilation ran over. The intruder's
    # own iris is chromatic too, but it is walled in by masked eye-white, so
    # filling holes afterwards recovers it.
    mask &= saturation <= args.saturation
    return binary_fill_holes(mask) & zone


def wait_for(host: str, port: int, prompt_id: str) -> list[str]:
    while True:
        time.sleep(5)
        with urllib.request.urlopen(f"http://{host}:{port}/history/{prompt_id}") as response:
            history = json.loads(response.read())
        if history:
            return [image["filename"]
                    for entry in history.values()
                    for output in entry.get("outputs", {}).values()
                    for image in output.get("images", [])]


def build_graph(source: dict, args: argparse.Namespace) -> dict:
    graph = json.loads(json.dumps(source))
    positive = next(k for k, n in graph.items()
                    if n.get("class_type") == "CLIPTextEncode" and "sage" in n["inputs"]["text"])
    negative = next(k for k, n in graph.items()
                    if n.get("class_type") == "CLIPTextEncode" and k != positive)
    sampler = next(k for k, n in graph.items() if n.get("class_type") == "KSampler")
    decode = next(k for k, n in graph.items() if n.get("class_type") == "VAEDecode")

    graph[positive]["inputs"]["text"] = INPAINT_POSITIVE
    graph[negative]["inputs"]["text"] += INPAINT_NEGATIVE_EXTRA

    graph["80"] = {"class_type": "LoadImage", "inputs": {"image": "intruder-src.png"}}
    graph["81"] = {"class_type": "LoadImage", "inputs": {"image": "intruder-mask.png"}}
    graph["82"] = {"class_type": "ImageToMask", "inputs": {"image": ["81", 0], "channel": "red"}}
    graph["83"] = {"class_type": "VAEEncode",
                   "inputs": {"pixels": ["80", 0], "vae": graph[decode]["inputs"]["vae"]}}
    # A noise mask rather than VAEEncodeForInpaint: everything outside the mask
    # is preserved exactly, which is the point -- the rest of the image is good.
    graph["84"] = {"class_type": "SetLatentNoiseMask",
                   "inputs": {"samples": ["83", 0], "mask": ["82", 0]}}

    graph[sampler]["inputs"]["latent_image"] = ["84", 0]
    graph[sampler]["inputs"]["denoise"] = 1.0
    graph[sampler]["inputs"]["seed"] = args.seed
    for node in graph.values():
        if node.get("class_type") == "SaveImage":
            node["inputs"]["filename_prefix"] = args.prefix
    empty = next((k for k, n in graph.items() if n.get("class_type") == "EmptyLatentImage"), None)
    if empty:
        del graph[empty]
    return graph


def main() -> int:
    args = parse_args()
    image = Image.open(args.image)
    graph = image.text.get("prompt")
    if graph is None and not args.dry_run:
        raise SystemExit(f"{args.image} has no prompt metadata; it was not written by ComfyUI")

    pixels = np.array(image.convert("RGB")).astype(int)
    mask = build_mask(pixels, args)
    share = mask.mean() * 100
    print(f"mask covers {share:.2f}% of the image")
    if share == 0:
        raise SystemExit("nothing matched -- widen --zone or relax --dark/--white")

    overlay_path = args.image.with_name(f"{args.image.stem}-maskoverlay.png")
    overlay = pixels.copy()
    overlay[mask] = (overlay[mask] * 0.3 + np.array([255, 0, 0]) * 0.7).astype(int)
    Image.fromarray(overlay.astype(np.uint8)).save(overlay_path)
    print(f"overlay -> {overlay_path}")

    if args.dry_run:
        print("dry run: check the overlay, then rerun without --dry-run")
        return 0

    inputs = args.comfy_root / "input"
    inputs.mkdir(parents=True, exist_ok=True)
    shutil.copy(args.image, inputs / "intruder-src.png")
    Image.fromarray(np.repeat((mask * 255).astype(np.uint8)[:, :, None], 3, axis=2)).save(
        inputs / "intruder-mask.png")

    payload = json.dumps({"prompt": build_graph(json.loads(graph), args)}).encode("utf-8")
    request = urllib.request.Request(
        f"http://{args.host}:{args.port}/prompt",
        data=payload, headers={"Content-Type": "application/json"})
    try:
        response = json.loads(urllib.request.urlopen(request).read())
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"ComfyUI rejected the prompt: {exc.read().decode()}") from exc

    for name in wait_for(args.host, args.port, response["prompt_id"]):
        print(f"wrote {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
