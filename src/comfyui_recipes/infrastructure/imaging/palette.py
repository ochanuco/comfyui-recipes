"""Measure and pin a render's colour against Yukari's delivery palette.

`repin` scales each material window's saturation toward its own per-band
target (V untouched, scaling only ever down) so materials that drift by
different amounts are corrected separately instead of by one global factor.
`measure`/`verdict` score a render against the acceptance bands. Values live
in `domain.yukari.delivery_style`; this module only applies them.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image
from scipy import ndimage

from .delivery import background_mask, enclosed_mask
from ...domain.yukari.delivery_style import (
    ACCENT_KEEP, ACCENT_RAMP, BACKDROP_SPREAD_MAX, BG_SAT_MAX,
    FIGURE_LIGHT_SAT_TARGET, FIGURE_LIGHT_V, FIGURE_MIDTONE_V,
    FIGURE_SAT_MEAN_MAX, FIGURE_SAT_P90_MAX, PALETTE_WINDOWS, REPIN_DARK,
    REPIN_LIGHT, REPIN_MID, REPIN_WARM_EXEMPT, SAT_BAND,
)

H_TARGET_BLEND = 0.7   # hue is eased toward the target, not snapped


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def window_w(H, lo, hi, feather=10.0):
    return smoothstep((H - (lo - feather)) / feather) * \
        smoothstep(((hi + feather) - H) / feather)


def band_w(V, feather=30.0):
    w = smoothstep((V - (FIGURE_LIGHT_V - feather)) / (2 * feather))
    return w, 1.0 - w


def figure_mask(im: np.ndarray) -> np.ndarray:
    mask = background_mask(im.astype(int), 18)
    mask |= enclosed_mask(im.astype(int), mask, 4)
    return ~mask


def legwear_mask(im: np.ndarray, col_cut: float) -> np.ndarray:
    """The asserted-legwear region, to be kept verbatim through `repin`.

    Geometry does the separating: the tights and the hair drift into the
    same purple band, so colour alone cannot tell them apart. `col_cut` is
    the column (as a width share) the legs stay left of -- a property of the
    composition, chosen by the caller per picture.
    """
    hsv = np.array(Image.fromarray(im).convert("HSV")).astype(float)
    fig = figure_mask(im)
    columns = np.arange(fig.shape[1])[None, :]
    legs = (fig & (columns < int(fig.shape[1] * col_cut))
            & ((hsv[..., 2] < 110) | (hsv[..., 1] > 60)))
    legs = ndimage.binary_closing(legs, iterations=3)
    labels, count = ndimage.label(legs)
    if count:
        sizes = ndimage.sum(legs, labels, range(1, count + 1))
        legs = labels == (1 + int(np.argmax(sizes)))
    return ndimage.binary_dilation(legs, iterations=3)


def repin(im: np.ndarray,
          protect: np.ndarray | None = None) -> tuple[np.ndarray, list[str]]:
    """RGB array in, RGB array out, plus a report of what moved.

    Saturation is compressed per V band toward tv639u's knees rather than
    scaled by a measured factor, so the curve is the same for every picture
    and a pale render passes through untouched. `protect` marks pixels kept
    verbatim; the correction fades to zero over a feathered edge.
    """
    hsv = np.array(Image.fromarray(im).convert("HSV")).astype(float)
    fig = figure_mask(im)
    keep = (ndimage.gaussian_filter(protect.astype(float), 5)
            if protect is not None else 0.0)
    if protect is not None:
        keep = np.maximum(keep, protect.astype(float))
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    a_start, a_width = ACCENT_RAMP
    accent = smoothstep((S - a_start) / a_width)

    def compress(knee_ratio):
        knee, ratio = knee_ratio
        kept = ratio + (ACCENT_KEEP - ratio) * accent
        return np.where(S > knee, knee + (S - knee) * kept, S)

    w_base = fig * smoothstep((S - 10) / 20) * (1 - keep)
    wl, _ = band_w(V)
    wd = smoothstep((90 - V) / 30)
    lo, hi = PALETTE_WINDOWS[0]["hue"]
    w_chroma = window_w(H, lo, hi) * w_base * (1 - wd)
    w_dark = w_base * wd * (1 - window_w(H, *REPIN_WARM_EXEMPT))
    target_c = wl * compress(REPIN_LIGHT) + (1 - wl) * compress(REPIN_MID)
    target_d = compress(REPIN_DARK)
    new_S = S + w_chroma * (target_c - S) + w_dark * (target_d - S)
    ease = w_chroma * H_TARGET_BLEND * (1 - accent)
    new_H = H * (1 - ease) + PALETTE_WINDOWS[0]["hue_target"] * ease

    moved = np.abs(new_S - S) > 2
    report = [f"compressed {moved.mean() * 100:.1f}% of frame "
              f"(accent kept {float((accent > 0.5).mean()) * 100:.1f}%)"]
    out = np.stack([new_H, new_S.clip(0, 255), V], axis=-1)
    rgb = np.array(Image.fromarray(out.clip(0, 255).astype(np.uint8), "HSV")
                   .convert("RGB"))
    return rgb, report


def repin_png(data: bytes,
              keep_legwear: float | None = None) -> tuple[bytes, list[str]]:
    im = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    protect = None
    report_head = []
    if keep_legwear is not None:
        protect = legwear_mask(im, keep_legwear)
        report_head = [f"legwear kept verbatim: {protect.mean() * 100:.1f}% "
                       f"of frame (cut {keep_legwear})"]
    rgb, report = repin(im, protect)
    output = io.BytesIO()
    Image.fromarray(rgb).save(output, format="PNG")
    return output.getvalue(), report_head + report


def measure(data: bytes) -> dict:
    im = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    hsv = np.array(Image.fromarray(im).convert("HSV")).astype(float)
    edge = np.concatenate([im[:30].reshape(-1, 3), im[-30:].reshape(-1, 3),
                           im[:, :30].reshape(-1, 3), im[:, -30:].reshape(-1, 3)])
    bg = np.median(edge, axis=0).astype(int)
    bg_hsv = np.array(Image.fromarray(bg[None, None].astype(np.uint8))
                      .convert("HSV")).astype(float)[0, 0]
    mask = background_mask(im.astype(int), 18)
    mask |= enclosed_mask(im.astype(int), mask, 4)
    c = 40
    corners = [im[:c, :c], im[:c, -c:], im[-c:, :c], im[-c:, -c:]]
    corner_means = [x.reshape(-1, 3).mean() for x in corners]
    mid = ~mask & (hsv[..., 2] >= FIGURE_MIDTONE_V)
    fig_s = hsv[..., 1][mid] if mid.any() else np.zeros(1)
    light = ~mask & (hsv[..., 2] >= FIGURE_LIGHT_V)
    light_s = float(hsv[..., 1][light].mean()) if light.any() else 0.0
    return {"bg": tuple(bg), "bg_sat": float(bg_hsv[1]),
            "sat": float(hsv[..., 1].mean()),
            "fig_sat_mean": float(fig_s.mean()),
            "fig_sat_p90": float(np.percentile(fig_s, 90)),
            "light_sat": light_s,
            "norm_factor": min(1.0, FIGURE_LIGHT_SAT_TARGET / light_s)
            if light_s else 1.0,
            "corner_spread": float(max(corner_means) - min(corner_means))}


def verdict(m: dict) -> list[str]:
    fails = []
    if not SAT_BAND[0] <= m["sat"] <= SAT_BAND[1]:
        fails.append(f"mean saturation {m['sat']:.1f} outside {SAT_BAND}")
    if m["bg_sat"] > BG_SAT_MAX:
        fails.append(f"background saturation {m['bg_sat']:.1f} > {BG_SAT_MAX}")
    if m["fig_sat_mean"] > FIGURE_SAT_MEAN_MAX:
        fails.append(f"figure midtone saturation {m['fig_sat_mean']:.1f} > "
                     f"{FIGURE_SAT_MEAN_MAX}")
    if m["fig_sat_p90"] > FIGURE_SAT_P90_MAX:
        fails.append(f"figure midtone p90 saturation {m['fig_sat_p90']:.1f} > "
                     f"{FIGURE_SAT_P90_MAX}")
    if m["corner_spread"] > BACKDROP_SPREAD_MAX:
        fails.append(f"backdrop not flat: corner spread "
                     f"{m['corner_spread']:.1f} > {BACKDROP_SPREAD_MAX} "
                     f"(gradient backdrop starves the flood mask; every "
                     f"figure number above is suspect)")
    return fails


def summarize(data: bytes) -> dict:
    """`measure` plus its `verdict`, under one key -- one injection point."""
    m = measure(data)
    m["fails"] = verdict(m)
    return m
