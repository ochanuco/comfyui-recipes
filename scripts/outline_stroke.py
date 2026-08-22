#!/usr/bin/env python3
"""Draw a second marker outline outside the one the model already drew.

Every figure in this recipe carries `(white outline:1.6)` -- a thick white
marker band that the model paints itself, and that reads as the sticker edge of
the drawing. This adds a coloured band immediately outside it: purple, at
Yukari's own hue, so the cut-out has a second stroke around it.

**Why this is not a prompt tag.** Danbooru's outline tags name one outline. Two
concentric bands, at fixed widths, in a stated colour, is a value the model has
no way to hold across seeds -- the same reason `recolor_bg.py` exists. The band
is added to the picture, not cut out of it, and the drawing underneath is
untouched: the stroke lives entirely in backdrop pixels.

Run it AFTER `recolor_bg.py`. The backdrop is found the same way -- flood from
the border, plus enclosed pockets -- so the stroke follows the figure exactly
where the repaint stopped, including the gaps between an arm and the body.

    uv run scripts/recolor_bg.py print.png --color '#c7e5e9'
    uv run scripts/outline_stroke.py print-bg.png

**The defaults are a starting point, not the recipe.** Four widths were shown
against the accepted `swelter` print and the thinnest won -- `#9256b8` at 6px on
2048, an accent rather than a second band of equal weight -- with the note that
it should be chosen per picture: 「これは絵の雰囲気で変えるべき」. So the default
here is that pick and nothing more. Reach for a heavier stroke when the drawing
can carry one.

Width is a share of the longest side by default (`--width-pct`, 0.3, which is
6px at 2048) because the number is tied to the print. `--width` sets pixels
instead when the size is known. For scale: the white band the stroke sits
against measures about 15px at 2048, so 10-14px reads as its equal.

The outer edge gets one pixel of falloff. Without it the band is a hard step
against a flat backdrop, which is precisely the fringe that
`recolor_bg.py --feather` was written to stop.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from recolor_bg import background_mask, enclosed_mask, parse_color

# The picked arm: thin, and the same hue as the hair's most saturated tenth.
DEFAULT_COLOR = "#9256b8"
DEFAULT_WIDTH_PCT = 0.3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument(
        "--color",
        default=DEFAULT_COLOR,
        help=f"stroke colour; default {DEFAULT_COLOR}, Yukari's hair accent at marker weight",
    )
    parser.add_argument(
        "--width",
        type=float,
        help="stroke thickness in pixels, measured outward from the figure",
    )
    parser.add_argument(
        "--width-pct",
        type=float,
        help=f"thickness as a percent of the longest side; wins over --width. "
             f"Default {DEFAULT_WIDTH_PCT}, i.e. 6px at 2048",
    )
    parser.add_argument(
        "--gap",
        type=float,
        default=0.0,
        help="backdrop left untouched between the white band and the stroke",
    )
    parser.add_argument(
        "--tolerance",
        type=int,
        default=18,
        help="per-channel distance from the corner colour still counted as background",
    )
    parser.add_argument(
        "--enclosed-tolerance",
        type=int,
        default=4,
        help="tighter match for backdrop the border flood cannot reach; -1 to skip",
    )
    parser.add_argument("--suffix", default="-edge", help="appended to the stem")
    parser.add_argument("--outdir", type=Path)
    return parser.parse_args()


def stroke_alpha(mask: np.ndarray, gap: float, width: float) -> np.ndarray:
    """Coverage of the band, gap..gap+width pixels out into the backdrop.

    `distance_transform_edt` on the backdrop gives each backdrop pixel its
    distance to the nearest figure pixel, so the first ring out is 1. Both
    edges are ramped over one pixel; the inner ramp does nothing at gap 0 and
    keeps the stroke from stepping when it is pushed away from the figure.
    """
    distance = ndimage.distance_transform_edt(mask)
    outer = np.clip(gap + width + 0.5 - distance, 0.0, 1.0)
    inner = np.clip(distance - gap + 0.5, 0.0, 1.0)
    alpha = outer * inner
    alpha[~mask] = 0.0
    return alpha


def main() -> int:
    args = parse_args()
    color = np.array(parse_color(args.color), dtype=float)

    for path in args.images:
        pixels = np.array(Image.open(path).convert("RGB")).astype(float)
        mask = background_mask(pixels.astype(int), args.tolerance)
        if args.enclosed_tolerance >= 0:
            mask |= enclosed_mask(pixels.astype(int), mask, args.enclosed_tolerance)
        share = mask.mean() * 100
        if share < 5:
            print(f"{path.name}: only {share:.1f}% backdrop, skipping")
            continue

        if args.width_pct is not None:
            width = max(pixels.shape[:2]) * args.width_pct / 100
        elif args.width is not None:
            width = args.width
        else:
            width = max(pixels.shape[:2]) * DEFAULT_WIDTH_PCT / 100

        alpha = stroke_alpha(mask, args.gap, width)
        pixels = pixels + alpha[..., None] * (color - pixels)
        outdir = args.outdir or path.parent
        outdir.mkdir(parents=True, exist_ok=True)
        out = outdir / f"{path.stem}{args.suffix}{path.suffix}"
        Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8)).save(out)
        print(
            f"{path.name}: {alpha.sum():.0f}px of stroke, {width:.1f}px wide "
            f"at gap {args.gap:g} -> {out}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
