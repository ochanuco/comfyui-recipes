#!/usr/bin/env python3
"""Collapse a render to a fixed number of colours, after the fact.

Nothing in the prompt controls how many colours come out. Two renders from the
same recipe measured 29 and 41 distinct colours, and the one at 41 was the one
that read as "the art style has changed" -- not because the line moved, it was
1.91px in both, but because the shading had gone from flat fills to gradients.

So this is the same move as scripts/recolor_bg.py: stop asking the sampler for
something it does not control and set it afterwards. Median-cut quantisation
with dithering off maps every pixel to the nearest of N colours, which is what
flat cel shading already is -- the gradients collapse back into bands.

    uv run scripts/analysis/flatten_palette.py out/ns-1886970040_00001_.png --colors 30
    uv run scripts/analysis/flatten_palette.py out/*.png --colors 30 --measure-only

DO NOT USE THIS ON YUKARI'S RENDERS. It costs her the colour it was meant to
tidy. At --colors 30 her purple went from 9.3% of the frame to 4.0% and its
saturation from 28.5 to 23.0: the eyes go grey, the dress goes near-neutral, the
pink cuffs disappear. Median cut spends its palette where the pixels are, and
this composition is mostly backdrop, black garment and white hair, so the small
coloured areas are what gets dropped.

Whole-frame mean saturation does NOT show this -- it read 30.8 before and 30.3
after, which is how the damage was missed on first inspection. Measure the
coloured region, not the image.

Dithering is off deliberately. It would scatter intermediate pixels to fake the
missing colours, which is the opposite of the point.

The count reported here is NOT the quantiser's N. It buckets each channel to 4
bits and counts buckets holding at least 0.3% of the frame, which is the measure
every earlier note in this repo used -- a palette of 30 typically reports well
under 30, because most of those colours are small highlights. Compare like with
like: the 29-vs-41 pair above is in these units.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def measure(image: Image.Image, floor: float = 0.003) -> int:
    """Distinct colours holding at least `floor` of the frame, 4 bits/channel."""
    array = np.asarray(image.convert("RGB"))
    coarse = (array >> 4) << 4
    _, counts = np.unique(coarse.reshape(-1, 3), axis=0, return_counts=True)
    return int((counts / counts.sum() >= floor).sum())


def flatten(image: Image.Image, colors: int) -> Image.Image:
    return image.convert("RGB").quantize(
        colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
    ).convert("RGB")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--colors", type=int, default=30)
    parser.add_argument("--suffix", default="-flat")
    parser.add_argument("--outdir", type=Path)
    parser.add_argument("--measure-only", action="store_true")
    args = parser.parse_args()

    for path in args.images:
        image = Image.open(path)
        before = measure(image)
        if args.measure_only:
            print(f"{path.name:44} {before:3d}")
            continue
        flat = flatten(image, args.colors)
        outdir = args.outdir or path.parent
        outdir.mkdir(parents=True, exist_ok=True)
        out = outdir / f"{path.stem}{args.suffix}{path.suffix}"
        flat.save(out)
        print(f"{path.name:44} {before:3d} -> {measure(flat):3d}  {out}")


if __name__ == "__main__":
    main()
