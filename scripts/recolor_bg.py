#!/usr/bin/env python3
"""Repaint the flat background of a generated portrait to an exact colour.

Only pixels reachable from the image border are touched, so a white dress or
a pale cape -- surrounded by the figure rather than by the edge -- is left
alone.

Inside the mask the colour is SET. Outside it, within `--feather` pixels,
each pixel is SHIFTED toward the colour by how much backdrop it looks like
it contains, instead of repainting the blended edge outright.
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


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
    parser.add_argument(
        "--feather",
        type=int,
        default=1,
        help="how many pixels beyond the mask may be partly shifted; 1 is "
             "measured, 2 tints the white outline, 0 is the old hard edge",
    )
    parser.add_argument(
        "--feather-tolerance",
        type=int,
        default=54,
        help="distance from the backdrop colour at which the partial shift "
             "reaches zero; three times --tolerance by default",
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


def repaint(
    pixels: np.ndarray,
    color: tuple[int, int, int],
    tolerance: int = 18,
    enclosed_tolerance: int = 4,
    feather: int = 1,
    feather_tolerance: int = 54,
) -> tuple[np.ndarray, float]:
    """The repaint itself, on an int RGB array. Returns the array and the share.

    The caller decides what to do with a low share: below about 5% the
    backdrop the flood found is not a backdrop, and repainting it anyway
    paints the figure.
    """
    mask = background_mask(pixels, tolerance)
    if enclosed_tolerance >= 0:
        mask |= enclosed_mask(pixels, mask, enclosed_tolerance)
    share = mask.mean() * 100

    seed = pixels[0, 0]
    if feather > 0:
        # How much backdrop each edge pixel looks like it holds: linear from 1
        # at --tolerance down to 0 at --feather-tolerance, zero outside the band.
        band = ndimage.binary_dilation(mask, iterations=feather) & ~mask
        far = max(feather_tolerance - tolerance, 1)
        distance = np.abs(pixels - seed).max(axis=2)
        alpha = np.clip((feather_tolerance - distance) / far, 0.0, 1.0)
        alpha[~band] = 0.0
        # SHIFTED, not set: only the pixel's backdrop component moves.
        pixels = pixels + alpha[..., None] * (np.array(color) - seed)
        pixels = np.clip(pixels, 0, 255)
    pixels[mask] = color
    return pixels, share


def main() -> int:
    args = parse_args()
    color = parse_color(args.color)

    for path in args.images:
        pixels = np.array(Image.open(path).convert("RGB")).astype(int)
        pixels, share = repaint(
            pixels, color, args.tolerance, args.enclosed_tolerance,
            args.feather, args.feather_tolerance)
        if share < 5:
            print(f"{path.name}: only {share:.1f}% matched, skipping (not a flat backdrop?)")
            continue
        outdir = args.outdir or path.parent
        outdir.mkdir(parents=True, exist_ok=True)
        out = outdir / f"{path.stem}{args.suffix}{path.suffix}"
        Image.fromarray(pixels.astype(np.uint8)).save(out)
        edge = "" if args.feather <= 0 else f", {args.feather}px feathered"
        print(f"{path.name}: {share:.1f}% repainted{edge} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
