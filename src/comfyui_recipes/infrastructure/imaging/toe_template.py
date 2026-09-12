"""Synthetic reference-hint image for the repair reroll's ControlNet signal.

Owned by the ControlNet lane, not shared with the pose-driven repair mask
rendering in `masks.py`.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageDraw

# Toe layout as (center_x, center_y, radius, height_ratio) fractions of the
# frame, big toe first, five decreasing-size ellipses fanned across a
# sole-forward view, spaced so no two outlines touch.
_TOE_LAYOUT = (
    (0.78, 0.34, 0.075, 1.3),
    (0.60, 0.24, 0.065, 1.25),
    (0.44, 0.20, 0.055, 1.2),
    (0.30, 0.23, 0.045, 1.15),
    (0.19, 0.30, 0.038, 1.1),
)


def reference_hint(size: int) -> bytes:
    """A synthetic sole-forward toe-lineart template, `size`x`size`, PNG.

    Black outlines on white -- five separate ellipses in a fan, the topology
    a ControlNet conditioning hook is meant to force, independent of any
    specific render's actual proportions.
    """
    canvas = Image.new("L", (size, size), 255)
    draw = ImageDraw.Draw(canvas)
    line_width = max(2, round(size / 200))
    for cx_frac, cy_frac, r_frac, height_ratio in _TOE_LAYOUT:
        cx, cy, r = cx_frac * size, cy_frac * size, r_frac * size
        rx, ry = r, r * height_ratio
        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry),
                    outline=0, width=line_width)
    pixels = np.array(canvas)
    output = io.BytesIO()
    Image.fromarray(pixels, "L").convert("RGB").save(output, "PNG")
    return output.getvalue()
