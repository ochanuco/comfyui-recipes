"""Named procedural backdrops for the sticker and compose delivery paths."""

from __future__ import annotations

import numpy as np

from ...domain.yukari import delivery_style


def stripes(height: int, width: int) -> np.ndarray:
    """Diagonal lavender bands with a white radial burst behind the figure."""
    from .delivery import parse_color

    yy, xx = np.mgrid[0:height, 0:width].astype(float)
    longest = max(height, width)
    x, y = xx / longest, yy / longest

    base = np.array(parse_color(delivery_style.STRIPES_BASE), dtype=float)
    white = np.array([255.0, 255.0, 255.0])

    band = ((x + y) / delivery_style.STRIPES_PITCH) % 1.0
    stripe = np.clip((band - 0.5) / 0.01 + 0.5, 0.0, 1.0)
    light = base * (1 - delivery_style.STRIPES_CONTRAST) + white * delivery_style.STRIPES_CONTRAST
    img = (light[None, None, :] * (1 - stripe[..., None])
          + base[None, None, :] * stripe[..., None])

    cx = x.max() * delivery_style.STRIPES_BURST_CENTER[0]
    cy = y.max() * delivery_style.STRIPES_BURST_CENTER[1]
    ang = np.arctan2(y - cy, x - cx)
    rays = np.clip(
        ((ang * delivery_style.STRIPES_BURST_RAYS / (2 * np.pi)) % 1.0 - 0.5) / 0.03 + 0.5,
        0.0, 1.0)
    dist = np.hypot(x - cx, y - cy)
    fade = np.clip(1 - dist / delivery_style.STRIPES_BURST_REACH, 0.0, 1.0) ** 1.5
    t = rays * fade * delivery_style.STRIPES_BURST
    img = img * (1 - t[..., None]) + white[None, None, :] * t[..., None]
    return np.clip(img, 0, 255)


PATTERNS = {"stripes": stripes}


def render(backdrop: str | None, height: int, width: int) -> np.ndarray:
    """The delivery backdrop as a full `(height, width, 3)` float array.

    `None` is the flat delivery default; a `PATTERNS` key is that procedural
    pattern; anything else must be a `#RRGGBB` colour, broadcast flat.
    """
    from .delivery import parse_color

    if backdrop in PATTERNS:
        return PATTERNS[backdrop](height, width)
    color = parse_color(backdrop if backdrop is not None else delivery_style.BACKDROP)
    return np.broadcast_to(
        np.array(color, dtype=float), (height, width, 3)).copy()


def is_backdrop(value: str) -> bool:
    """True for a `PATTERNS` key or a parseable `#RRGGBB` colour."""
    if value in PATTERNS:
        return True
    from .delivery import parse_color

    try:
        parse_color(value)
    except SystemExit:
        return False
    return True
