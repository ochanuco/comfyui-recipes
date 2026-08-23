#!/usr/bin/env python3
"""How jagged a silhouette is, in three numbers, without opening the picture.

Written the second time this was needed. The first version was a throwaway in
.local/ and the numbers it produced are quoted in `docs/render-notes.md` under
the upscale-ratio finding; there is no way to rerun them, which is the whole
argument for this file existing.

Row by row down the left side of the figure, at the first pixel that stops
being backdrop:

  stair    run length of an unchanged edge x across consecutive rows. A slanted
           edge should move every row or two; long runs are a visible staircase
  AA       how many partly-blended pixels the backdrop-to-figure transition
           takes. 0 is a hard step, 2 is a drawn edge
  hard     share of rows whose transition takes no partial pixel at all

**Read it within a pose, between arms.** Across poses it measures how slanted
the silhouette happens to be, and this project's record of image statistics
against the user's eye is 0-7.

    uv run scripts/edge_profile.py a.png b.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from recolor_bg import background_mask, enclosed_mask


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--tolerance", type=int, default=18)
    parser.add_argument(
        "--reach",
        type=int,
        default=24,
        help="how far past the edge to look for the value the ramp climbs to",
    )
    return parser.parse_args()


def profile(path: Path, tolerance: int, reach: int) -> dict:
    pixels = np.array(Image.open(path).convert("RGB")).astype(int)
    mask = background_mask(pixels, tolerance)
    mask |= enclosed_mask(pixels, mask, 4)
    distance = np.abs(pixels - pixels[0, 0]).max(axis=2)

    edges, blends = [], []
    for y in range(pixels.shape[0]):
        row = mask[y]
        if row[0] == False or row.all():          # noqa: E712 -- figure at x=0
            continue
        inside = np.flatnonzero(~row)
        if not len(inside):
            continue
        x = inside[0]
        edges.append((y, x))
        # The ramp is measured against what it climbs TO, not against a fixed
        # window. A fixed one counts the whole `(white outline:1.6)` band --
        # 35 from the backdrop, well inside any threshold loose enough to catch
        # a blend -- and reports an AA of 30 pixels, which is the band's width.
        run = distance[y, x:x + reach]
        top = float(run.max()) if len(run) else 0.0
        if top <= tolerance:
            continue
        n = int(((run > 0.15 * top) & (run < 0.85 * top)).sum())
        blends.append(n)

    runs, current = [], 1
    for (y0, x0), (y1, x1) in zip(edges, edges[1:]):
        if y1 == y0 + 1 and x1 == x0:
            current += 1
        else:
            runs.append(current)
            current = 1
    runs.append(current)
    blends = np.array(blends) if blends else np.zeros(1)
    return {"rows": len(edges), "stair_mean": float(np.mean(runs)),
            "stair_max": int(np.max(runs)), "aa": float(blends.mean()),
            "hard": float((blends == 0).mean() * 100)}


def main() -> int:
    args = parse_args()
    for path in args.images:
        r = profile(path, args.tolerance, args.reach)
        print(f"{path.name:52s} stair mean {r['stair_mean']:4.1f} "
              f"max {r['stair_max']:3d}   AA {r['aa']:4.2f}   "
              f"hard {r['hard']:4.1f}%   ({r['rows']} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
