"""Repaint a render's fills from a measured palette, keeping its own linework.

`repin` only ever nudges the render's own saturation, so a washed-out black
stays washed out -- V is untouched by design. `recolor` instead detects the
render's own linework, labels the fills it encloses, classifies each fill as
a material, and asserts that material's colour outright: it fixes value as
well as hue and saturation, at the cost of trusting the classifier instead
of the render. Targets live in `domain.yukari.delivery_style`; this module
only applies them.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image
from scipy import ndimage

from .palette import figure_mask
from ...domain.yukari.delivery_style import (
    RECOLOR_ACCENT_S, RECOLOR_DARK_V, RECOLOR_HAIR_S, RECOLOR_KEEP_V,
    RECOLOR_LEG_CY, RECOLOR_LEG_MIN_AREA, RECOLOR_LEG_STOPS, RECOLOR_LINE_MAX,
    RECOLOR_LINE_RELIEF, RECOLOR_LINE_WINDOW, RECOLOR_SKIN_HUE,
    RECOLOR_TARGETS, RECOLOR_WHITE_S,
)


def lines(im: np.ndarray) -> np.ndarray:
    """The render's own linework: dark, and darker than what it bounds."""
    fig = figure_mask(im)
    grey = np.array(Image.fromarray(im).convert("L")).astype(float)
    relief = ndimage.maximum_filter(grey, RECOLOR_LINE_WINDOW) - grey
    return fig & (grey < RECOLOR_LINE_MAX) & (relief > RECOLOR_LINE_RELIEF)


def classify(h: float, s: float, v: float, cy: float, area: float) -> str | None:
    lo, hi = RECOLOR_SKIN_HUE
    warm = h < lo or h > hi
    if v < RECOLOR_DARK_V:
        return "tights" if cy > RECOLOR_LEG_CY else "hoodie"
    if cy > RECOLOR_LEG_CY and area >= RECOLOR_LEG_MIN_AREA and not warm:
        return "tights"
    if s > RECOLOR_ACCENT_S:
        return None
    if warm:
        return "skin"
    if s < RECOLOR_WHITE_S:
        return "white"
    if s < RECOLOR_HAIR_S:
        return "hair"
    return "dress"


def _paint_tights(region: np.ndarray, out_h, out_s, out_v, V, top: int,
                  height: int) -> None:
    rows = np.where(region)[0]
    cy = (rows - top) / height
    stops = RECOLOR_LEG_STOPS
    xs = [stop[0] for stop in stops]
    target_h = np.interp(cy, xs, [stop[1][0] for stop in stops])
    target_s = np.interp(cy, xs, [stop[1][1] for stop in stops])
    target_v = np.interp(cy, xs, [stop[1][2] for stop in stops])
    keep = RECOLOR_KEEP_V["tights"]
    out_h[region] = target_h
    out_s[region] = target_s
    out_v[region] = np.clip(
        target_v + (V[region] - np.median(V[region])) * keep, 0, 255)


def recolor(im: np.ndarray) -> tuple[np.ndarray, list[str]]:
    """RGB array in, RGB array out, plus a report of each material's share.

    Regions are the fills the render's own linework encloses -- figure_mask
    finds the figure, `lines` finds the linework, ndimage.label enumerates
    what is left. Each region is classified once from its median HSV and its
    centroid height, normalised to the FIGURE's own bounding box rather than
    the canvas, since where the figure sits on the canvas is not part of its
    shape. Painting keeps a share of the region's own V against the target,
    so the render's own shading still reads under the asserted colour.
    """
    hsv = np.array(Image.fromarray(im).convert("HSV")).astype(float)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    fig = figure_mask(im)
    line = lines(im)
    labels, count = ndimage.label(fig & ~line)

    rows = np.where(fig.any(axis=1))[0]
    top, bottom = int(rows.min()), int(rows.max())
    height = max(bottom - top, 1)

    out_h, out_s, out_v = H.copy(), S.copy(), V.copy()
    total = int(fig.sum())
    claimed: dict[str, int] = {}
    for index in range(1, count + 1):
        region = labels == index
        h = float(np.median(H[region]))
        s = float(np.median(S[region]))
        v = float(np.median(V[region]))
        cy = (float(np.mean(np.where(region)[0])) - top) / height
        material = classify(h, s, v, cy, int(region.sum()) / total)
        if material is None:
            continue
        if material == "tights":
            _paint_tights(region, out_h, out_s, out_v, V, top, height)
        else:
            t_h, t_s, t_v = RECOLOR_TARGETS[material]
            keep = RECOLOR_KEEP_V[material]
            out_h[region] = t_h
            out_s[region] = t_s
            out_v[region] = np.clip(t_v + (V[region] - v) * keep, 0, 255)
        claimed[material] = claimed.get(material, 0) + int(region.sum())

    out = np.stack([out_h, out_s.clip(0, 255), out_v.clip(0, 255)], axis=-1)
    rgb = np.array(Image.fromarray(out.clip(0, 255).astype(np.uint8), "HSV")
                   .convert("RGB"))
    rgb[line] = im[line]

    share = ", ".join(f"{material} {count_ / total * 100:.1f}%"
                      for material, count_ in
                      sorted(claimed.items(), key=lambda kv: -kv[1]))
    report = [share] if share else []
    return rgb, report


def recolor_png(data: bytes) -> tuple[bytes, list[str]]:
    im = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    rgb, report = recolor(im)
    output = io.BytesIO()
    Image.fromarray(rgb).save(output, format="PNG")
    return output.getvalue(), report
