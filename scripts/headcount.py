#!/usr/bin/env python3
"""How many bodies are in a render, without opening it.

Filters by area share, not width: a block must hold at least `--min-share`
of total figure pixels to count as a body.

    uv run scripts/headcount.py <filename-on-the-worker> ...
    uv run scripts/headcount.py --detail ...      # every block, filtered or not

Filenames are fetched through `/view` -- the worker's disk is not this one.

It counts blobs, not people: two figures that overlap in every column are
one block. `--detail`'s height fraction (of frame height) tells a figure,
tall for its width, from a limb lying flat.
"""

from __future__ import annotations

import argparse
import io
import sys
import urllib.parse
import urllib.request

import numpy as np
from PIL import Image

sys.path.insert(0, "scripts")
from comfy_host import base_url


def blocks(a: np.ndarray) -> tuple[np.ndarray, list[tuple[int, int]]]:
    h, w, _ = a.shape
    border = np.concatenate([a[:4].reshape(-1, 3), a[-4:].reshape(-1, 3),
                             a[:, :4].reshape(-1, 3), a[:, -4:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    fig = (np.abs(a - bg).sum(axis=2) > 60) & (a.mean(axis=2) < 225)
    on = fig.sum(axis=0) > h * 0.04
    runs, start = [], None
    for x, v in enumerate(list(on) + [False]):
        if v and start is None:
            start = x
        elif not v and start is not None:
            runs.append((start, x))
            start = None
    return fig, runs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="+")
    ap.add_argument("--min-share", type=float, default=0.02)
    ap.add_argument("--detail", action="store_true")
    args = ap.parse_args()

    for name in args.names:
        url = base_url() + "/view?" + urllib.parse.urlencode(
            {"filename": name, "type": "output"})
        with urllib.request.urlopen(url, timeout=30) as r:
            a = np.asarray(Image.open(io.BytesIO(r.read())).convert("RGB")).astype(float)
        fig, runs = blocks(a)
        h = fig.shape[0]
        total = fig.sum()
        kept = [(x0, x1) for x0, x1 in runs
                if fig[:, x0:x1].sum() / total >= args.min_share]
        n = len(kept)
        print(f"{name:<48} {'ONE' if n == 1 else f'{n} bodies':>9}"
              f"   {len(runs) - n} block(s) below {args.min_share:.0%} ignored")
        if args.detail:
            for x0, x1 in runs:
                seg = fig[:, x0:x1]
                share = seg.sum() / total
                rows = np.where(seg.any(axis=1))[0]
                tall = (rows[-1] - rows[0]) / h if len(rows) else 0.0
                mark = " " if (x0, x1) in kept else "x"
                print(f"   {mark} x {x0:4d}-{x1:4d}  width {x1 - x0:4d}"
                      f"  {share:6.2%} of figure  {tall:5.1%} of frame height")


if __name__ == "__main__":
    main()
