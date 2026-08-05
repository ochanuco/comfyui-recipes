#!/usr/bin/env python3
"""Repaint the flat background of a generated portrait to an exact colour.

Prompt tags such as "grey background" only get the model into the right area;
the actual value drifts between seeds. For a plain backdrop it is cheaper to
generate against any flat colour and set the real one here.

Only pixels reachable from the image border are touched, so a white dress or a
pale cape -- surrounded by the figure rather than by the edge -- is left alone.
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--color", required=True, help="target background, e.g. #C1C3C2")
    parser.add_argument(
        "--tolerance",
        type=int,
        default=18,
        help="per-channel distance from the corner colour still counted as background",
    )
    parser.add_argument(
        "--suffix",
        default="-bg",
        help="appended to the stem; pass '' to overwrite in place",
    )
    parser.add_argument(
        "--enclosed-tolerance",
        type=int,
        default=4,
        help="tighter match used for backdrop the border flood cannot reach",
    )
    parser.add_argument("--outdir", type=Path)
    return parser.parse_args()


def parse_color(text: str) -> tuple[int, int, int]:
    value = text.lstrip("#")
    if len(value) != 6:
        raise SystemExit(f"expected a 6-digit hex colour, got {text!r}")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def background_mask(pixels: np.ndarray, tolerance: int) -> np.ndarray:
    """Flood from every border pixel that matches the corner colour."""
    height, width, _ = pixels.shape
    seed = pixels[0, 0]
    mask = np.zeros((height, width), dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    def push(y: int, x: int) -> None:
        if not mask[y, x] and int(np.abs(pixels[y, x] - seed).max()) <= tolerance:
            mask[y, x] = True
            queue.append((y, x))

    for x in range(width):
        push(0, x)
        push(height - 1, x)
    for y in range(height):
        push(y, 0)
        push(y, width - 1)

    while queue:
        y, x = queue.popleft()
        if y > 0:
            push(y - 1, x)
        if y < height - 1:
            push(y + 1, x)
        if x > 0:
            push(y, x - 1)
        if x < width - 1:
            push(y, x + 1)
    return mask


def enclosed_mask(pixels: np.ndarray, found: np.ndarray, tolerance: int) -> np.ndarray:
    """Backdrop walled off from the border, e.g. between a staff and the body.

    Matched on a much tighter tolerance than the border flood: the backdrop is a
    single flat value, while a white dress carries shading and will not qualify.
    """
    seed = pixels[0, 0]
    exact = np.abs(pixels - seed).max(axis=2) <= tolerance
    return exact & ~found


def main() -> int:
    args = parse_args()
    color = parse_color(args.color)

    for path in args.images:
        pixels = np.array(Image.open(path).convert("RGB")).astype(int)
        mask = background_mask(pixels, args.tolerance)
        if args.enclosed_tolerance >= 0:
            mask |= enclosed_mask(pixels, mask, args.enclosed_tolerance)
        share = mask.mean() * 100
        if share < 5:
            print(f"{path.name}: only {share:.1f}% matched, skipping (not a flat backdrop?)")
            continue

        pixels[mask] = color
        outdir = args.outdir or path.parent
        outdir.mkdir(parents=True, exist_ok=True)
        out = outdir / f"{path.stem}{args.suffix}{path.suffix}"
        Image.fromarray(pixels.astype(np.uint8)).save(out)
        print(f"{path.name}: {share:.1f}% repainted -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
