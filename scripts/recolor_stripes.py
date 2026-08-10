#!/usr/bin/env python3
"""Repaint one colour of the striped legwear without touching the rest.

Prompt tags can move a colour between categories -- white to black, purple to
green -- but not within one. "off-white" and "skin colored" land on the same
point as "white" and change nothing, and raising their weight only makes the
white whiter. Yukari also has white hair and white frills, so the whole image is
anchored to the same white the legwear inherits. Same reasoning as
recolor_bg.py: get the model into the right area, set the actual value here.

Selecting the legwear is the whole problem, since her dress is purple and her
hair is white. What is true only of the stripes is that both colours occur
within a few pixels of each other, so the mask is the intersection of the two
dilated colour masks: a pixel counts as legwear when there is white AND purple
nearby. A flat lavender dress fails that test, and so does white hair.

Shading is kept by scaling the target colour with each pixel's own brightness,
so the highlight bands down the shin survive the repaint.

    uv run scripts/recolor_stripes.py in.png --out out.png --to "#F0DCC8"
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--to", required=True, help="target colour, e.g. #F0DCC8")
    parser.add_argument(
        "--which",
        choices=["light", "dark"],
        default="light",
        help="which of the two stripe colours to repaint",
    )
    parser.add_argument(
        "--radius",
        type=int,
        default=21,
        help="how far apart the two colours may be and still count as one stripe "
        "pattern; must exceed a band's width or the mask comes out hollow",
    )
    parser.add_argument(
        "--min-area",
        type=int,
        default=4000,
        help="discard selected regions smaller than this many pixels. 4000 is "
        "where the last of the hair goes without a band going with it; 8000 "
        "starts eating the short bands around the ankle",
    )
    parser.add_argument(
        "--shrink",
        type=int,
        help="unused by the current mask; kept so old command lines still parse",
    )
    parser.add_argument("--hue-low", type=int, default=175)
    parser.add_argument("--hue-high", type=int, default=215)
    parser.add_argument("--sat-min", type=int, default=60)
    parser.add_argument(
        "--dark-val-min",
        type=int,
        default=150,
        help="below this brightness a violet pixel is a shadow, not a stripe",
    )
    parser.add_argument(
        "--light-sat-max",
        type=int,
        default=45,
        help="above this saturation a pale pixel is a colour, not the light band",
    )
    parser.add_argument("--light-val-min", type=int, default=185)
    parser.add_argument(
        "--alpha",
        type=float,
        default=1.0,
        help="how strongly the new colour replaces the old; below 1 it is "
        "laid over instead, which is how a sheer band is faked",
    )
    parser.add_argument("--dump-mask", type=Path)
    return parser.parse_args()


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    """Grow a boolean mask. MaxFilter wants an odd window and an 8-bit image."""
    if radius <= 0:
        return mask
    size = radius * 2 + 1
    grown = Image.fromarray((mask * 255).astype(np.uint8)).filter(
        ImageFilter.MaxFilter(size)
    )
    return np.asarray(grown) > 127


def erode(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask
    size = radius * 2 + 1
    shrunk = Image.fromarray((mask * 255).astype(np.uint8)).filter(
        ImageFilter.MinFilter(size)
    )
    return np.asarray(shrunk) > 127


def near_above(mask: np.ndarray, reach: int) -> np.ndarray:
    """True where `mask` holds anywhere in the `reach` rows above this one."""
    out = np.zeros_like(mask)
    for shift in range(1, reach + 1):
        out[shift:] |= mask[:-shift]
    return out


def near_below(mask: np.ndarray, reach: int) -> np.ndarray:
    out = np.zeros_like(mask)
    for shift in range(1, reach + 1):
        out[:-shift] |= mask[shift:]
    return out


def near_left(mask: np.ndarray, reach: int) -> np.ndarray:
    out = np.zeros_like(mask)
    for shift in range(1, reach + 1):
        out[:, shift:] |= mask[:, :-shift]
    return out


def near_right(mask: np.ndarray, reach: int) -> np.ndarray:
    out = np.zeros_like(mask)
    for shift in range(1, reach + 1):
        out[:, :-shift] |= mask[:, shift:]
    return out


def drop_small(mask: np.ndarray, min_area: int) -> np.ndarray:
    """Keep only regions of at least `min_area` pixels."""
    if min_area <= 0:
        return mask
    from scipy import ndimage

    labels, count = ndimage.label(mask)
    if count == 0:
        return mask
    areas = np.bincount(labels.ravel())
    keep = np.zeros(areas.shape, dtype=bool)
    keep[1:] = areas[1:] >= min_area
    return keep[labels]


def sandwiched(mask: np.ndarray, reach: int) -> np.ndarray:
    """True where `mask` lies on both sides -- vertically or horizontally.

    One axis is not enough: the bands run across the leg, so on a leg lying
    diagonally they are steep enough that the rows above and below a light band
    are still light. Either axis will do, and an edge -- border or frill -- has
    the other colour on one side only, so it fails both.
    """
    return (near_above(mask, reach) & near_below(mask, reach)) | (
        near_left(mask, reach) & near_right(mask, reach)
    )


def main() -> None:
    args = parse_args()
    rgb = np.asarray(Image.open(args.image).convert("RGB")).astype(np.float32)
    hsv = np.asarray(Image.open(args.image).convert("HSV")).astype(np.int16)
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    # The value floor is what keeps her hair out. Its shadows are violet at
    # roughly the saturation of the stripes -- 95 against 108 on the render this
    # was tuned against -- so saturation alone cannot tell them apart, and the
    # hair blob is far too big for --min-area to catch. Brightness can: those
    # shadows sit near 113 where the stripe purple sits near 194.
    dark = (
        (hue > args.hue_low)
        & (hue < args.hue_high)
        & (sat > args.sat_min)
        & (val > args.dark_val_min)
    )
    light = (sat < args.light_sat_max) & (val > args.light_val_min)

    # Proximity alone is not enough: the sticker border and the dress frill are
    # white and sit right against the stripes, so any radius wide enough to
    # bridge a band also swallows them, and eroding it back off punches holes in
    # the middle of the legwear instead.
    #
    # What separates them is which side the other colour is on. A light band of
    # legwear is *between* two dark ones; the border and the frill have dark on
    # their inner side only. So look up and down separately and require both.
    other = dark if args.which == "light" else light
    target = light if args.which == "light" else dark
    target_mask = target & sandwiched(other, args.radius)
    # Her hair is white with violet shadows in it, which is a stripe pattern as
    # far as the test above is concerned, and it fires on a scatter of pixels
    # there and along the frill. They are invisible in the repaint and then the
    # refine pass turns them into streaks across the whole picture, so drop
    # everything that is not part of a band-sized region.
    target_mask = drop_small(target_mask, args.min_area)

    if args.dump_mask:
        Image.fromarray((target_mask * 255).astype(np.uint8)).save(args.dump_mask)

    if not target_mask.any():
        raise SystemExit("nothing selected -- widen --radius or the colour bounds")

    to = np.array(
        [int(args.to.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)], dtype=np.float32
    )
    # Each pixel keeps its own brightness relative to the band's base tone, so
    # the shading and the gloss highlights come through the new colour.
    band = rgb[target_mask]
    base = np.percentile(band.mean(axis=1), 60)
    ratio = (band.mean(axis=1) / base)[:, None]
    painted = np.clip(to[None, :] * ratio, 0, 255)
    # Partial alpha is how sheer legwear gets faked. It cannot be asked for:
    # the tights are drawn as solid white, so there is no skin underneath for
    # the sampler to reveal, and a masked pass at any denoise keeps returning
    # opaque bands. Laying skin tone over the light bands at less than full
    # strength puts the missing colour there instead of hoping for it.
    if args.alpha < 1.0:
        painted = band * (1 - args.alpha) + painted * args.alpha
    rgb[target_mask] = painted

    args.out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb.astype(np.uint8)).save(args.out)
    print(f"{args.out}  ({int(target_mask.sum())} px repainted)")


if __name__ == "__main__":
    main()
