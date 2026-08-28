#!/usr/bin/env python3
"""Repackage a lineart as a black-line transparent PNG.

The pipeline's lineart is opaque everywhere -- extracts come back white-on-black
for ControlNet, authored drawings are black-on-white -- and the only way to lay
one over a colour image has been multiply compositing. This turns either form
into the same thing as a portable file: RGB solid black, alpha = line intensity.
Compositing that PNG over anything is pixel-identical to the multiply, so it is
an export format, not a new mechanism; nothing downstream (ControlNet, ImageBlend)
consumes alpha and none of it changes.

Purely local: Pillow + numpy, no GPU, no graph.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from comfy_host import DEFAULT_HOST, DEFAULT_PORT, ensure_local

REPO = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO / ".local/ComfyUI/output"


def to_alpha(src: Path, dest: Path) -> str:
    gray = np.asarray(Image.open(src).convert("L"))
    # Polarity by majority: a lineart is mostly background. Bright background
    # means dark lines (authored drawing), dark background means bright lines
    # (preprocessor extract); either way alpha is "how much line is here", so
    # anti-aliased edges keep their partial coverage.
    dark_lines = gray.mean() > 127
    alpha = 255 - gray if dark_lines else gray
    rgba = np.zeros((*gray.shape, 4), dtype=np.uint8)
    rgba[..., 3] = alpha
    Image.fromarray(rgba, "RGBA").save(dest)
    return "black-on-white" if dark_lines else "white-on-black"


def resolve(source: str, host: str, port: int) -> Path:
    path = Path(source)
    if path.exists():
        return path
    return ensure_local(f"{source}_00001_.png", OUTPUT_DIR, host=host, port=port)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", nargs="+",
                        help="local paths, or output/ basenames e.g. lx-hs-cel-anime-raw")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    for source in args.sources:
        src = resolve(source, args.host, args.port)
        if not src.exists():
            raise SystemExit(f"no such lineart: {src}")
        dest = src.with_name(f"{src.stem}-alpha.png")
        polarity = to_alpha(src, dest)
        print(f"{src.name}  ({polarity})  ->  {dest}")


if __name__ == "__main__":
    main()
