#!/usr/bin/env python3
"""Measure the scratchy-fill failure: stray line inside areas that should be flat.

A cel render is a small number of long contours around large flat fills. The
failure this catches is the fill going scratchy -- short fold and highlight
strokes sprayed across the inside of a garment -- while the contours stay fine.
By eye that reads as "rough sketch", and by eye it is also indistinguishable
from ordinary seed variation, which is why it needs a number: one render against
one render cannot separate a tag's effect from the sample it happened to draw.

Method. A pixel is flat if the luminance variation in a wide neighbourhood is
low; erode that mask so contours and their surroundings drop out. Then count
Canny edge pixels surviving inside the mask, per thousand flat pixels.

    uv run scripts/flat_scratch.py out/sb-111222333_00001_.png ...

Calibration, on this recipe at 1024x1536 (measure again before trusting these
numbers at another size -- the window is in pixels, so it does not scale):

    0.06 - 0.22   clean. Every render without the surface block landed here.
    0.53 - 0.99   scratchy. Every render carrying the surface block landed here,
                  with no overlap: (taut fabric), (stretched fabric),
                  (soft shading), smooth fabric, (specular highlights),
                  light streaks.
    2.04          lb-lap, where the costume dissolved outright.

What it does not measure: staging, anatomy, duplicates, or whether the costume
is the right one. It answers one question only. An earlier version counted short
edge components across the whole frame and ranked the best render worst, because
it could not tell a gold trim line from a stray fold -- restricting the count to
flat interiors is the whole idea, not an optimisation.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def flat_scratch(
    path: Path, win: int = 25, flat_std: float = 6.0, erode: int = 9,
    lo: int = 30, hi: int = 90,
) -> tuple[float, int]:
    """Return (edge pixels per 1000 flat pixels, flat area in pixels)."""
    bgr = cv2.imread(str(path))
    if bgr is None:
        raise SystemExit(f"cannot read {path}")
    grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    g = grey.astype(np.float32)

    # Local standard deviation via two box filters, rather than a per-pixel
    # window: E[x^2] - E[x]^2, clamped because rounding can take it negative.
    mean = cv2.blur(g, (win, win))
    sq = cv2.blur(g * g, (win, win))
    std = np.sqrt(np.maximum(sq - mean * mean, 0))

    flat = (std < flat_std).astype(np.uint8)
    # A contour raises the local std of everything within half a window of it,
    # so the mask already excludes its surroundings; the erode is what keeps a
    # thin sliver of fill from hugging the line and counting it.
    flat = cv2.erode(flat, np.ones((erode, erode), np.uint8))

    edges = (cv2.Canny(grey, lo, hi) > 0).astype(np.uint8)
    area = int(flat.sum())
    if area == 0:
        return float("nan"), 0
    return float((edges & flat).sum()) / area * 1000.0, area


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--win", type=int, default=25)
    parser.add_argument("--flat-std", type=float, default=6.0)
    parser.add_argument("--erode", type=int, default=9)
    args = parser.parse_args()

    for path in args.images:
        score, area = flat_scratch(
            path, win=args.win, flat_std=args.flat_std, erode=args.erode
        )
        verdict = "clean" if score < 0.25 else "SCRATCHY"
        print(f"{path.name:34} {score:6.3f}  flat={area:8d}  {verdict}")


if __name__ == "__main__":
    main()
