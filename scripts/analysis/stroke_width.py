#!/usr/bin/env python3
"""Measure lineart stroke width, in pixels and relative to the head.

The notes quote stroke figures constantly -- 1.91px here, 3.82 there, "the line
does not respond to tags" -- and there was no tool for it; every number was
measured by hand and none of them can be re-checked. This is that tool.

Method: dark pixels are thresholded out, then horizontal and vertical runs of
dark are collected and the median taken. Runs longer than `--max-run` are
dropped as fills rather than lines -- the black cardigan is a large dark area
and would otherwise drown the contours it is drawn with.

    uv run scripts/analysis/stroke_width.py .local/ComfyUI/output/one-d60_00001_.png
    uv run scripts/analysis/stroke_width.py out/*.png --max-run 24

**Absolute px is the less useful half.** The line reads heavy or fine relative
to the figure, not to the canvas, so a render twice the size with twice the
stroke looks identical. `stroke/1000px` normalises by the long edge and is what
two different canvases can be compared on.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def runs(mask: np.ndarray, max_run: int) -> np.ndarray:
    """Lengths of consecutive True runs along every row, both axes summed."""
    out = []
    for arr in (mask, mask.T):
        padded = np.zeros((arr.shape[0], arr.shape[1] + 2), dtype=bool)
        padded[:, 1:-1] = arr
        diff = np.diff(padded.astype(np.int8), axis=1)
        starts = np.argwhere(diff == 1)
        ends = np.argwhere(diff == -1)
        if len(starts) and len(starts) == len(ends):
            lengths = ends[:, 1] - starts[:, 1]
            out.append(lengths[(lengths > 0) & (lengths <= max_run)])
    return np.concatenate(out) if out else np.array([])


def measure(path: Path, threshold: int, max_run: int) -> dict:
    image = Image.open(path).convert("L")
    grey = np.asarray(image)
    lengths = runs(grey < threshold, max_run)
    longest = max(image.size)
    if not len(lengths):
        return {"file": path.name, "size": image.size, "n": 0}
    # The median is an integer count and lands on 3 or 4 with nothing between,
    # which is too coarse to compare two renders of the same picture. The mean
    # moves continuously and is what the normalised figure is built from.
    return {
        "file": path.name,
        "size": image.size,
        "n": len(lengths),
        "median": float(np.median(lengths)),
        "mean": float(np.mean(lengths)),
        "p90": float(np.percentile(lengths, 90)),
        # The comparable number: mean stroke per 1000px of long edge.
        "norm": float(np.mean(lengths)) * 1000.0 / longest,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--threshold", type=int, default=110,
                        help="a pixel is line if its luminance is below this")
    parser.add_argument("--max-run", type=int, default=16,
                        help="runs longer than this are fills, not lines")
    args = parser.parse_args()

    print(f"{'file':<34} {'canvas':>11} {'median':>7} {'mean':>6} {'p90':>6} {'per 1000px':>11}")
    for path in args.paths:
        r = measure(path, args.threshold, args.max_run)
        if not r["n"]:
            print(f"{r['file']:<34} {'x'.join(map(str, r['size'])):>11}  no lineart found")
            continue
        print(f"{r['file']:<34} {'x'.join(map(str, r['size'])):>11} "
              f"{r['median']:>7.2f} {r['mean']:>6.2f} {r['p90']:>6.1f} {r['norm']:>11.3f}")


if __name__ == "__main__":
    main()
