#!/usr/bin/env python3
"""Draw a second marker outline outside the one the model already drew.

Every figure carries a white outline already; this adds a second coloured
band immediately outside it, in Yukari's own hue. The band is added to the
picture, not cut from it -- the drawing underneath is untouched.

Run it AFTER `recolor_bg.py`. The backdrop is found the same way -- flood
from the border, plus enclosed pockets -- so the stroke follows the figure
exactly where the repaint stopped.

    uv run scripts/recolor_bg.py print.png --color '#c7e5e9'
    uv run scripts/outline_stroke.py print-bg.png

The defaults are a starting point, not the recipe; reach for a heavier
stroke when the drawing can carry one. Width defaults to a share of the
figure's own white band, not the canvas -- a constant canvas share looks
thin on exactly the pictures whose band is thickest.

The outer edge gets one pixel of falloff, avoiding a hard step against the
flat backdrop.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from recolor_bg import background_mask, enclosed_mask, parse_color

from comfyui_recipes.domain.yukari import delivery_style

# Re-exported from yukari/delivery_style.py -- these names are this tool's API.
DEFAULT_COLOR = delivery_style.STROKE
DEFAULT_WIDTH_BAND = delivery_style.STROKE_WIDTH_BAND
# This tool's own floor when nothing else determines the width.
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


# Above this share of the contour having no line within LINE_REACH, the
# median measures the unlined tail rather than the band.
FAR_SHARE = 0.5
LINE_REACH = 20.0


def band_thickness(pixels: np.ndarray, mask: np.ndarray, dark: int = 120) -> float:
    """How thick the figure's OWN white marker is, at the median of its contour.

    Measured to the line, not the white: skin tone and the white band can't be
    told apart by threshold. The inner edge is unambiguous (the figure's black
    outline), so this takes the median distance from each backdrop-contour
    pixel to the nearest dark pixel -- median because unlined stretches of
    contour (an arm's inside, a sleeve running out of frame) read in the
    hundreds.
    """
    inward = ndimage.distance_transform_edt(~mask)
    to_line = ndimage.distance_transform_edt(pixels.mean(axis=2) >= dark)
    contour = (inward > 0) & (inward <= 1)
    if not contour.any():
        return 0.0
    distances = to_line[contour]
    # Past FAR_SHARE, the median is measuring distance-to-nothing, not paint.
    # Returns 0.0 rather than a clamped guess: the caller's canvas-relative
    # default doesn't need this value, and a wrong number is worse than none.
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
    """Draw the band on a float RGB array. Returns it, the width, and the share."""
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
        # A floor, not a fallback: max() means neither term can be too big --
        # the canvas floor only binds where the measured band is thin, and
        # the band term wins wherever it is thick.
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
