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

**The width is a share of the white band, not of the canvas, and that was a
correction.** It shipped as 0.3% of the longest side, and on a head crop the
purple went invisible -- 「大外の紫を復旧して」. The band the stroke sits
against is drawn by the model at a size that has nothing to do with the canvas:
19.2px on a 2048 print and 13.2px on a 1024 head crop, i.e. 0.94% of one frame
and 1.29% of the other. A constant share of the canvas therefore makes the
stroke look thinner on exactly the pictures whose band is thickest. `band` is
the default now, at 0.32 -- the share that reproduces the picked 6.1px on the
picture the four arms were judged on. `--width-pct` and `--width` still
override it.

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

# Re-picked 2026-08-26 on the colW kick sweep: darker than the hair-accent
# #9256b8 it replaced, judged against a lighter #b591d6 at the same width.
DEFAULT_COLOR = "#6a3494"
# The picked width as a share of the white band it sits against, which is what
# it was actually chosen as: 12.5px on the render whose 0.32 stroke drew 6.1px.
# Chosen from a 0.32 / 0.50 / 0.80 / 1.2 ladder. See `band_thickness`.
DEFAULT_WIDTH_BAND = 0.80
# The share-of-canvas rule this one replaced, kept as a FLOOR under it. Both
# rules only ever failed by drawing too thin, so the larger of the two is the
# one that is never the failure.
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
        help=f"thickness as a percent of the longest side ({DEFAULT_WIDTH_PCT} "
             f"is 6px at 2048)",
    )
    parser.add_argument(
        "--width-band",
        type=float,
        help=f"thickness as a share of the figure's own white marker, measured "
             f"per image. The default when nothing else is given, at "
             f"{DEFAULT_WIDTH_BAND}",
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


# Above this share of the contour having no line within LINE_REACH, the median
# below is measuring the tail rather than the band. 0.5 is not a tuned number:
# it is the point at which a median IS the tail.
FAR_SHARE = 0.5
LINE_REACH = 20.0


def band_thickness(pixels: np.ndarray, mask: np.ndarray, dark: int = 120) -> float:
    """How thick the figure's OWN white marker is, at the median of its contour.

    **Measured to the LINE, not to the white.** The obvious version -- walk in
    from the backdrop counting bright unsaturated pixels -- does not work in
    this recipe, and the reason is worth keeping: `(pale skin:1.25)` puts her
    face at (250,240,225), which is brighter and barely more saturated than the
    white band at (248,243,242). There is no threshold that separates the paint
    from the girl. It also read 1px on any repainted image, because
    `recolor_bg`'s 1px feather tints the outermost ring toward the backdrop and
    that alone failed the test.

    The band's INNER edge is unambiguous: it is the figure's black outline. So
    this measures, for every pixel on the backdrop's contour, the distance to
    the nearest dark pixel, and takes the median. Stable to the repaint --
    19.2 against 19.2 on the print, 13.2 against 13.0 on a head crop -- because
    nothing it looks at is near the tolerance of anything.

    The median and not the mean: parts of a contour have no line anywhere near
    them (the inside of a leg, a sleeve running out of frame) and those read in
    the hundreds. On the accepted print the quartiles are 16 and 98.
    """
    inward = ndimage.distance_transform_edt(~mask)
    to_line = ndimage.distance_transform_edt(pixels.mean(axis=2) >= dark)
    contour = (inward > 0) & (inward <= 1)
    if not contour.any():
        return 0.0
    distances = to_line[contour]
    # **The median only protects while the tail is under half.** Measured on the
    # renders that produced today's 1.0-to-12.7px spread: the share of contour
    # with no line within 20px ran 0.3%, 18.5%, 37.7%, 44.8%, 57.6%, 81.2%, and
    # the two past 50% are exactly the two whose estimate was absurd -- 45.5px
    # of "band" on a print whose band is under 20. Past that point the median
    # has crossed into the distances-to-nothing and is not measuring paint.
    #
    # 0.0 rather than a clamped guess: the caller has a canvas-relative default
    # that does not depend on finding the band at all, and a number that is
    # known to be wrong is worse than no number.
    if float((distances > LINE_REACH).mean()) >= FAR_SHARE:
        return 0.0
    return float(np.median(distances))


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


def stroke(
    pixels: np.ndarray,
    color: str = DEFAULT_COLOR,
    width: float | None = None,
    width_pct: float | None = None,
    width_band: float | None = None,
    gap: float = 0.0,
    tolerance: int = 18,
    enclosed_tolerance: int = 4,
) -> tuple[np.ndarray, float, float]:
    """Draw the band on a float RGB array. Returns it, the width, and the share.

    Split out of `main` for the same reason `recolor_bg.repaint` is: the two
    run back to back on every delivery and there is no reason for the second
    one to re-read the first one's file.
    """
    rgb = np.array(parse_color(color), dtype=float)
    mask = background_mask(pixels.astype(int), tolerance)
    if enclosed_tolerance >= 0:
        mask |= enclosed_mask(pixels.astype(int), mask, enclosed_tolerance)
    share = mask.mean() * 100

    if width_pct is not None:
        width = max(pixels.shape[:2]) * width_pct / 100
    elif width is None:
        fraction = DEFAULT_WIDTH_BAND if width_band is None else width_band
        band = band_thickness(pixels, mask)
        # **A FLOOR, not a fallback.** The two rules fail in opposite
        # directions: the canvas share went invisible on a head crop, which is
        # why the band share replaced it, and the band share came out at 1.0
        # and 2.3px on prints whose siblings got 6.5 and 12.7. Taking the larger
        # of the two fixes both, because neither is ever wrong by being too big
        # here -- the head crop's band is thick, so the band rule wins there and
        # the floor does not bind; a print's band is thin, so the floor does.
        #
        # Measured on the six renders that produced today's spread. Before:
        # 6.5 3.5 1.0 / 12.7 2.3 3.2. After: 4.6 4.6 4.6 / 6.1 6.1 6.1 -- every
        # arm of a comparison gets the same band, which is the property that was
        # actually missing. 6.1 is also what the eye picked on cf978c9c.
        width = max(band * fraction,
                    max(pixels.shape[:2]) * DEFAULT_WIDTH_PCT / 100)

    alpha = stroke_alpha(mask, gap, width)
    return pixels + alpha[..., None] * (rgb - pixels), width, share


def main() -> int:
    args = parse_args()

    for path in args.images:
        pixels = np.array(Image.open(path).convert("RGB")).astype(float)
        pixels, width, share = stroke(
            pixels, args.color, args.width, args.width_pct, args.width_band,
            args.gap, args.tolerance, args.enclosed_tolerance)
        if share < 5:
            print(f"{path.name}: only {share:.1f}% backdrop, skipping")
            continue
        outdir = args.outdir or path.parent
        outdir.mkdir(parents=True, exist_ok=True)
        out = outdir / f"{path.stem}{args.suffix}{path.suffix}"
        Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8)).save(out)
        print(f"{path.name}: {width:.1f}px stroke at gap {args.gap:g} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
