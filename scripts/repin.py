#!/usr/bin/env python3
"""Pin a render's colour to the palette, leaving the brushwork alone.

The model drifts saturation per pose and per material -- lounge paints its
purples at five times the palette while the same render's skin is only off
by half -- and no prompt lever moves it (six wordings, muted color, limited
palette, all on record). A single desaturation factor can only average those
errors; this pins each material window separately.

V is never touched: shading, stroke texture and lineart weight are the
render's own. Within each `PALETTE_WINDOWS` hue window the saturation is
scaled toward that window's per-band target (light/mid split at
FIGURE_LIGHT_V, blended continuously in V so no boundary shows) and the hue
is eased toward the window's target where one is set. Scaling only ever goes
down -- a render paler than the palette is left alone. Window edges and the
low-S floor are feathered, so nothing bands.

The values are not this tool's to choose (recolor_bg's --color rule): the
windows and targets live in `yukari.delivery_style.PALETTE_WINDOWS`, frozen
from the reference stand's measurement.

    uv run scripts/repin.py <in.png> <out.png>
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

import recolor_bg  # noqa: E402
from yukari.delivery_style import (  # noqa: E402
    FIGURE_LIGHT_V, PALETTE_WINDOWS,
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
    mask = recolor_bg.background_mask(im.astype(int), 18)
    mask |= recolor_bg.enclosed_mask(im.astype(int), mask, 4)
    return ~mask


def repin(im: np.ndarray) -> tuple[np.ndarray, list[str]]:
    """RGB array in, RGB array out, plus one report line per window."""
    hsv = np.array(Image.fromarray(im).convert("HSV")).astype(float)
    fig = figure_mask(im)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    new_H, new_S = H.copy(), S.copy()
    report = []
    for win in PALETTE_WINDOWS:
        lo, hi = win["hue"]
        sel = fig & (V >= 80) & (S > 20) & (H >= lo) & (H <= hi)
        measured = []
        for m in (sel & (V >= FIGURE_LIGHT_V), sel & (V < FIGURE_LIGHT_V)):
            measured.append(float(S[m].mean()) if m.any() else 0.0)
        f_light = min(1.0, win["sat_light"] / measured[0]) if measured[0] > 1 else 1.0
        f_mid = min(1.0, win["sat_mid"] / measured[1]) if measured[1] > 1 else 1.0
        w = window_w(H, lo, hi) * fig * smoothstep((S - 10) / 20)
        wl, wm = band_w(V)
        factor = wl * f_light + wm * f_mid
        new_S = new_S * (1 - w) + new_S * factor * w
        if win["hue_target"] is not None:
            new_H = (new_H * (1 - w * H_TARGET_BLEND)
                     + win["hue_target"] * (w * H_TARGET_BLEND))
        report.append(f"{win['name']}: measured {measured[0]:.1f}/{measured[1]:.1f}"
                      f" -> factor {f_light:.2f}/{f_mid:.2f}")
    out = np.stack([new_H, new_S, V], axis=-1)
    rgb = np.array(Image.fromarray(out.clip(0, 255).astype(np.uint8), "HSV")
                   .convert("RGB"))
    return rgb, report


def main() -> None:
    im = np.array(Image.open(sys.argv[1]).convert("RGB"))
    rgb, report = repin(im)
    for line in report:
        print(line)
    Image.fromarray(rgb).save(sys.argv[2])
    print(sys.argv[2])


if __name__ == "__main__":
    main()
