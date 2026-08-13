#!/usr/bin/env python3
"""Draw the line last: extract lineart from a finished render and multiply it back on.

This is the "最後に線を引く" control. Nothing is re-diffused -- the colour image is
final and the line is a compositing step, so its strength is a continuous dial
(blend_factor) instead of a tag weight that the sampler may or may not honour.

The point of running it before building anything with ControlNet is to settle how
much line is actually wanted. A target strength found here can then be reproduced
by whichever mechanism is cheapest; picking the mechanism first would mean
building it twice.

The aux preprocessors emit white lines on black for ControlNet consumption, so
the extract is inverted before it can be multiplied over the colour. The raw
extract is saved too -- it is what a ControlNet pass would be conditioned on, so
it is worth looking at on its own.
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

PREPROCESSORS = {
    "anime": "AnimeLineArtPreprocessor",
    "manga": "Manga2Anime_LineArt_Preprocessor",
    "standard": "LineartStandardPreprocessor",
}


def build(filename: str, tag: str, node: str, factors: list[float],
          width: int, height: int, resolution: int, tuning: dict) -> dict:
    graph = {
        "1": {"class_type": "LoadImage", "inputs": {"image": filename}},
        "2": {"class_type": node, "inputs": {
            "image": ["1", 0], "resolution": resolution, **tuning}},
        # The preprocessor resizes to its own working resolution; ImageBlend needs
        # both inputs to agree, so force it back to the source size.
        "3": {"class_type": "ImageScale", "inputs": {
            "image": ["2", 0], "upscale_method": "lanczos",
            "width": width, "height": height, "crop": "disabled"}},
        "4": {"class_type": "ImageInvert", "inputs": {"image": ["3", 0]}},
        "5": {"class_type": "SaveImage", "inputs": {
            "images": ["3", 0], "filename_prefix": f"lx-{tag}-raw"}},
    }
    node_id = 10
    for factor in factors:
        blend, save = str(node_id), str(node_id + 1)
        graph[blend] = {"class_type": "ImageBlend", "inputs": {
            "image1": ["1", 0], "image2": ["4", 0],
            "blend_factor": factor, "blend_mode": "multiply"}}
        graph[save] = {"class_type": "SaveImage", "inputs": {
            "images": [blend, 0],
            "filename_prefix": f"lx-{tag}-m{int(round(factor * 100)):02d}"}}
        node_id += 2
    return graph


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", nargs="+", help="output/ basenames, e.g. hs-heavy-nf")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8188)
    parser.add_argument("--kind", choices=sorted(PREPROCESSORS), default="anime")
    parser.add_argument("--factor", action="append", type=float, default=[])
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1280)
    # The anime extractor found only the silhouette on a flat-coloured render: it
    # is a learned model for pulling drawn lines out of drawn art, and a grey
    # shadow boundary is not one. LineartStandard is XDoG-ish and fires on the
    # luminance step itself, so its sensitivity is the dial that matters here --
    # a small sigma keeps thin detail, a low threshold lets weak edges through.
    parser.add_argument("--sigma", type=float, help="LineartStandard guassian_sigma")
    parser.add_argument("--threshold", type=int, help="LineartStandard intensity_threshold")
    # Extraction at 1024 on a 1280-tall source already loses the thinnest strands.
    parser.add_argument("--resolution", type=int, default=1280)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    factors = args.factor or [0.3, 0.5, 0.7]
    node = PREPROCESSORS[args.kind]
    tuning: dict = {}
    if args.kind == "standard":
        if args.sigma is not None:
            tuning["guassian_sigma"] = args.sigma
        if args.threshold is not None:
            tuning["intensity_threshold"] = args.threshold
    elif args.sigma is not None or args.threshold is not None:
        raise SystemExit("--sigma/--threshold only apply to --kind standard")
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    for source in args.sources:
        src = OUTPUT_DIR / f"{source}_00001_.png"
        if not src.exists():
            raise SystemExit(f"no such render: {src}")
        filename = f"lx-src-{source}.png"
        shutil.copyfile(src, INPUT_DIR / filename)
        suffix = "".join(f"-{k[0]}{v}" for k, v in
                         (("sigma", args.sigma), ("threshold", args.threshold)) if v is not None)
        tag = f"{source}-{args.kind}{suffix}"
        print(f"{tag:30s} {node} {tuning} x{factors}")
        if args.dry_run:
            continue
        req = urllib.request.Request(
            f"http://{args.host}:{args.port}/prompt",
            data=json.dumps({"prompt": build(
                filename, tag, node, factors, args.width, args.height,
                args.resolution, tuning)}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            print("   ->", json.load(resp)["prompt_id"])


if __name__ == "__main__":
    main()
