#!/usr/bin/env python3
"""Normalize a render's saturation to the delivered palette, in HSV.

Six prompt attempts could not lower the purple end of the tights -- (muted
colors)+(desaturated) doubled it, (dusty purple) raised it, a vividness guard
left the mean flat and pushed the peak up -- and the drift is not even a
constant: lounge renders 3x stand's saturation, lap about half that. When the
tag describing the defect does nothing at any weight, the defect is implied by
something else; here it is the pose, and the delivery corrects it instead.

Saturation is scaled and nothing else: value and hue are untouched, so the
purple-to-black run down the leg keeps its shape and the lineart keeps its
weight. The factor comes from the palette, not from this tool (recolor_bg's
--color rule): measure the figure's light band (V >= FIGURE_LIGHT_V, the pale
dress and hair) and scale by FIGURE_LIGHT_SAT_TARGET / measured, clamped to
1.0 -- a render already at the palette passes through untouched, and a pale
one is never pushed up. An explicit factor overrides, for probes only.

    uv run scripts/desat.py <in.png> <out.png>            # normalize
    uv run scripts/desat.py <in.png> <out.png> <factor>   # probe override
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

import recolor_bg  # noqa: E402
from yukari.delivery_style import (  # noqa: E402
    FIGURE_LIGHT_SAT_TARGET, FIGURE_LIGHT_V, FIGURE_MIDTONE_V,
)


def figure_mask(im: np.ndarray) -> np.ndarray:
    mask = recolor_bg.background_mask(im.astype(int), 18)
    mask |= recolor_bg.enclosed_mask(im.astype(int), mask, 4)
    return ~mask


def normalize_factor(im: np.ndarray) -> tuple[float, float]:
    """(factor, measured light-band mean) for one render."""
    hsv = np.asarray(Image.fromarray(im).convert("HSV")).astype(float)
    light = figure_mask(im) & (hsv[..., 2] >= FIGURE_LIGHT_V)
    measured = float(hsv[..., 1][light].mean()) if light.any() else 0.0
    if measured <= FIGURE_LIGHT_SAT_TARGET:
        return 1.0, measured
    return FIGURE_LIGHT_SAT_TARGET / measured, measured


def main() -> None:
    im = Image.open(sys.argv[1]).convert("RGB")
    px = np.asarray(im)
    if len(sys.argv) > 3:
        f = float(sys.argv[3])
        print(f"factor {f:.2f} (explicit)")
    else:
        f, measured = normalize_factor(px)
        print(f"factor {f:.2f} (light band {measured:.1f} -> "
              f"target {FIGURE_LIGHT_SAT_TARGET})")
    hsv = np.asarray(im.convert("HSV")).astype(np.float32)
    hsv[..., 1] *= f
    out = Image.fromarray(hsv.clip(0, 255).astype(np.uint8), "HSV").convert("RGB")
    out.save(sys.argv[2])

    fig = figure_mask(px)
    for lab, img in (("before", im), ("after", out)):
        hsv_i = np.asarray(img.convert("HSV")).astype(int)
        mid = fig & (hsv_i[..., 2] >= FIGURE_MIDTONE_V)
        s = hsv_i[..., 1][mid]
        print(f"{lab:>6}: figure sat mean {s.mean():5.1f}  "
              f"p90 {np.percentile(s, 90):5.0f}  >60 {(s > 60).mean():5.2%}")


if __name__ == "__main__":
    main()
