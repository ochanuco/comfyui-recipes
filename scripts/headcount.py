#!/usr/bin/env python3
"""How many bodies are in a render, without opening it.

Replaces `.local/_solo.py`, which counted column blocks in the figure mask and
called each one a body. That is wrong in a way that only shows up on some poses:
a block one pixel wide counts the same as a girl. In one session it reported
two bodies on two `seiza` renders and four and six on two `flop` renders, and
every one of those extra blocks was a 1-4px sliver -- a stray mark at the frame
edge, or a `motion lines` stroke on the flat backdrop, which is a comic
convention drawn as separate marks BY DEFINITION. A pose carrying motion lines
could not be counted by the old tool at all.

So a block has to be big enough to be a person before it is called one. The
filter is area share, not width: a figure lying down is wide and short, one
standing is narrow and tall, and neither is bounded usefully by a width rule.
`--min-share` is the fraction of total figure pixels a block must hold; 2% is
far below any real second figure (the smallest chibi clone recorded in this
repo's notes is several percent) and far above every false positive seen.

    uv run scripts/headcount.py <filename-on-the-worker> ...
    uv run scripts/headcount.py --detail ...      # every block, filtered or not

Filenames are fetched through `/view` -- the worker's disk is not this one.

**It counts blobs, not people.** Two figures that overlap in every column are
one block. It is a smoke alarm for the clone problem this recipe keeps hitting,
in the direction that matters: it does not miss a second girl standing clear of
her, which is the failure that has actually occurred here.
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
        total = fig.sum()
        kept = [(x0, x1) for x0, x1 in runs
                if fig[:, x0:x1].sum() / total >= args.min_share]
        n = len(kept)
        print(f"{name:<48} {'ONE' if n == 1 else f'{n} bodies':>9}"
              f"   {len(runs) - n} block(s) below {args.min_share:.0%} ignored")
        if args.detail:
            for x0, x1 in runs:
                share = fig[:, x0:x1].sum() / total
                mark = " " if (x0, x1) in kept else "x"
                print(f"   {mark} x {x0:4d}-{x1:4d}  width {x1 - x0:4d}"
                      f"  {share:6.2%} of figure")


if __name__ == "__main__":
    main()
