#!/usr/bin/env python3
"""Redraw the legwear stripes as geometry: even bands, a line at every edge.

Asking the model for even stripes does not work -- (evenly spaced stripes) and
(uniform stripes) make it draw fewer and fainter stripes rather than better
spaced ones, and on one render the pattern vanished into a solid colour. Band
width is not something the prompt controls, only band presence.

So the model draws the legwear and this draws the pattern. Bands are laid out
perpendicular to each leg's own axis at a fixed period, which makes them even by
construction, and each boundary gets a drawn line, which is what separates a
striped garment from a colour gradient.

The mask comes from a render that already has stripes, for the reason
recolor_stripes.py explains: a light band lies between two dark ones and an edge
does not. A plain white pair of tights has no such handle -- nothing in it tells
white legwear from a white frill or a white sticker border -- and rendering a
colour-keyed twin to difference against does not work either, because changing
the colour word moves the composition.

    uv run scripts/stripe_paint.py in.png --out out.png \\
        --light "#F2DCC6" --dark "#B07BD8" --period 90
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from recolor_stripes import drop_small, sandwiched


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--light", default="#F2DCC6", help="colour of one band")
    parser.add_argument("--dark", default="#B07BD8", help="colour of the other")
    parser.add_argument("--line", default="#4A3A56", help="colour of the boundary")
    parser.add_argument(
        "--period", type=float, default=90.0, help="one light plus one dark band, in px"
    )
    parser.add_argument("--line-width", type=float, default=4.0)
    parser.add_argument("--radius", type=int, default=80)
    parser.add_argument("--min-area", type=int, default=4000)
    parser.add_argument(
        "--keep-fraction",
        type=float,
        default=0.25,
        help="drop regions smaller than this share of the biggest one",
    )
    parser.add_argument("--hue-low", type=int, default=175)
    parser.add_argument("--hue-high", type=int, default=215)
    parser.add_argument("--sat-min", type=int, default=60)
    parser.add_argument("--dark-val-min", type=int, default=150)
    parser.add_argument("--light-sat-max", type=int, default=45)
    parser.add_argument("--light-val-min", type=int, default=185)
    parser.add_argument("--dump-mask", type=Path)
    return parser.parse_args()


def rgb_of(text: str) -> np.ndarray:
    text = text.lstrip("#")
    return np.array([int(text[i : i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def legwear_mask(hsv: np.ndarray, args: argparse.Namespace) -> np.ndarray:
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    dark = (
        (hue > args.hue_low)
        & (hue < args.hue_high)
        & (sat > args.sat_min)
        & (val > args.dark_val_min)
    )
    light = (sat < args.light_sat_max) & (val > args.light_val_min)
    both = (light & sandwiched(dark, args.radius)) | (dark & sandwiched(light, args.radius))
    # Discard the strays first. Her hair is white with violet shadows and passes
    # the sandwich test on a scatter of pixels; joining the bands up before
    # throwing those away drags the head into the same region as the legs.
    both = drop_small(both, args.min_area)
    # Now bridge band to band, by half a period each way -- enough to close the
    # gap between two bands, not enough to reach the dress. No hole filling: the
    # bands wrap around the figure, and filling the ring they make would take
    # the whole torso with it.
    reach = max(1, int(args.period // 2))
    solid = ndimage.binary_dilation(both, iterations=reach)
    solid = ndimage.binary_erosion(solid, iterations=reach)
    solid = drop_small(solid, args.min_area)
    # A fixed area floor cannot separate a leg from the patch that survives up
    # at the hood, because both are large. Relative size can: the legs are the
    # subject of the pattern and everything else is an order of magnitude below.
    labels, count = ndimage.label(solid)
    if count > 1:
        areas = np.bincount(labels.ravel())
        areas[0] = 0
        keep = areas >= areas.max() * args.keep_fraction
        keep[0] = False
        solid = keep[labels]
    return solid


def main() -> None:
    args = parse_args()
    image = Image.open(args.image).convert("RGB")
    rgb = np.asarray(image).astype(np.float32)
    hsv = np.asarray(image.convert("HSV")).astype(np.int16)

    mask = legwear_mask(hsv, args)
    if args.dump_mask:
        Image.fromarray((mask * 255).astype(np.uint8)).save(args.dump_mask)
    if not mask.any():
        raise SystemExit("no legwear found")

    light, dark, line = rgb_of(args.light), rgb_of(args.dark), rgb_of(args.line)
    labels, count = ndimage.label(mask)
    ys, xs = np.mgrid[0 : rgb.shape[0], 0 : rgb.shape[1]]

    for label in range(1, count + 1):
        part = labels == label
        py, px = np.nonzero(part)
        # The bands run across the leg, so they are level sets of the position
        # along its long axis. Each leg gets its own, since they point different
        # ways -- one shin can be vertical while the other lies flat.
        coords = np.stack([py - py.mean(), px - px.mean()])
        axis = np.linalg.eigh(np.cov(coords))[1][:, -1]
        along = (ys[part] - py.mean()) * axis[0] + (xs[part] - px.mean()) * axis[1]

        phase = np.mod(along, args.period)
        is_dark = phase < args.period / 2
        on_line = (phase < args.line_width) | (phase > args.period / 2 - args.line_width) & (
            phase < args.period / 2
        )
        on_line |= phase > args.period - args.line_width

        # Keep the render's own shading by scaling with each pixel's brightness.
        band = rgb[part]
        ratio = (band.mean(axis=1) / np.percentile(band.mean(axis=1), 60))[:, None]
        painted = np.where(is_dark[:, None], dark[None, :], light[None, :]) * ratio
        painted[on_line] = line
        rgb[part] = np.clip(painted, 0, 255)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb.astype(np.uint8)).save(args.out)
    print(f"{args.out}  ({count} legs, {int(mask.sum())} px)")


if __name__ == "__main__":
    main()
