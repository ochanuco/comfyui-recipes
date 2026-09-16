"""Named procedural backdrops for the sticker and compose delivery paths."""

from __future__ import annotations

import io

import numpy as np
from PIL import Image

from ...domain.yukari import delivery_style


def _grid(height: int, width: int) -> tuple[np.ndarray, np.ndarray]:
    """Pixel coordinates normalised by the longest side, x right / y down."""
    yy, xx = np.mgrid[0:height, 0:width].astype(float)
    longest = max(height, width)
    return xx / longest, yy / longest


def _palette() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Stripes' own lavender/light/white triad, shared by every pattern."""
    from .delivery import parse_color

    base = np.array(parse_color(delivery_style.STRIPES_BASE), dtype=float)
    white = np.array([255.0, 255.0, 255.0])
    light = (base * (1 - delivery_style.STRIPES_CONTRAST)
            + white * delivery_style.STRIPES_CONTRAST)
    return base, light, white


def _edge(v: np.ndarray, soft: float = 0.004) -> np.ndarray:
    """A soft step at `v == 0`, ramped over `soft` widths."""
    return np.clip(v / soft + 0.5, 0.0, 1.0)


def _paint(img: np.ndarray, colour: np.ndarray, t: np.ndarray) -> np.ndarray:
    return img * (1 - t[..., None]) + colour[None, None, :] * t[..., None]


def _flat(height: int, width: int, colour: np.ndarray) -> np.ndarray:
    return np.broadcast_to(colour, (height, width, 3)).astype(float).copy()


def _burst(img: np.ndarray, x: np.ndarray, y: np.ndarray, strength: float) -> np.ndarray:
    """White radial burst in stripes' own geometry, blended in at `strength`."""
    cx = x.max() * delivery_style.STRIPES_BURST_CENTER[0]
    cy = y.max() * delivery_style.STRIPES_BURST_CENTER[1]
    ang = np.arctan2(y - cy, x - cx)
    rays = np.clip(
        ((ang * delivery_style.STRIPES_BURST_RAYS / (2 * np.pi)) % 1.0 - 0.5) / 0.03 + 0.5,
        0.0, 1.0)
    dist = np.hypot(x - cx, y - cy)
    fade = np.clip(1 - dist / delivery_style.STRIPES_BURST_REACH, 0.0, 1.0) ** 1.5
    t = rays * fade * strength
    white = np.array([255.0, 255.0, 255.0])
    return img * (1 - t[..., None]) + white[None, None, :] * t[..., None]


def stripes(height: int, width: int) -> np.ndarray:
    """Diagonal lavender bands with a white radial burst behind the figure."""
    x, y = _grid(height, width)
    base, light, _white = _palette()

    band = ((x + y) / delivery_style.STRIPES_PITCH) % 1.0
    stripe = _edge(band - 0.5, 0.01)
    img = (light[None, None, :] * (1 - stripe[..., None])
          + base[None, None, :] * stripe[..., None])

    img = _burst(img, x, y, delivery_style.STRIPES_BURST)
    return np.clip(img, 0, 255)


def dots(height: int, width: int) -> np.ndarray:
    """Large white polka dots on lavender, offset rows."""
    x, y = _grid(height, width)
    base, light, _white = _palette()
    cell = delivery_style.DOTS_CELL
    row = np.floor(y / cell)
    gx = ((x + cell / 2 * (row % 2)) % cell) - cell / 2
    gy = (y % cell) - cell / 2
    radius = cell * delivery_style.DOTS_RADIUS_SHARE
    t = _edge(radius - np.hypot(gx, gy), delivery_style.DOTS_EDGE_SOFT)
    img = _paint(_flat(height, width, base), light, t)
    return np.clip(img, 0, 255)


def gingham(height: int, width: int) -> np.ndarray:
    """Lavender gingham: overlapping translucent bands, darker at crossings."""
    x, y = _grid(height, width)
    base, light, _white = _palette()
    cell = delivery_style.GINGHAM_CELL
    half_band = cell * delivery_style.GINGHAM_BAND_SHARE
    bx = _edge(half_band - np.abs((x % cell) - cell / 2), delivery_style.GINGHAM_EDGE_SOFT)
    by = _edge(half_band - np.abs((y % cell) - cell / 2), delivery_style.GINGHAM_EDGE_SOFT)
    img = _flat(height, width, light)
    img = _paint(img, base, delivery_style.GINGHAM_BAND_ALPHA * bx)
    img = _paint(img, base, delivery_style.GINGHAM_BAND_ALPHA * by)
    return np.clip(img, 0, 255)


def moons(height: int, width: int) -> np.ndarray:
    """Small white crescents scattered on a staggered lattice, weak burst behind."""
    x, y = _grid(height, width)
    base, light, _white = _palette()
    cell = delivery_style.MOONS_CELL
    row = np.floor(y / cell)
    gx = ((x + cell / 2 * (row % 2)) % cell) - cell / 2
    gy = (y % cell) - cell / 2
    hole_dx, hole_dy = delivery_style.MOONS_HOLE_OFFSET
    moon = (_edge(delivery_style.MOONS_RADIUS - np.hypot(gx, gy))
           * (1 - _edge(delivery_style.MOONS_HOLE_RADIUS
                       - np.hypot(gx - hole_dx, gy - hole_dy))))
    img = _paint(_flat(height, width, base), light, moon)
    img = _burst(img, x, y, delivery_style.MOONS_BURST)
    return np.clip(img, 0, 255)


def halftone(height: int, width: int) -> np.ndarray:
    """White halftone dots growing toward the lower-left, big faint crescent behind."""
    x, y = _grid(height, width)
    base, _light, white = _palette()
    cell = delivery_style.HALFTONE_CELL
    gx, gy = (x % cell) - cell / 2, (y % cell) - cell / 2
    t = np.clip((y - x + 0.5) / delivery_style.HALFTONE_GRADIENT_SPAN, 0, 1)
    radius = cell * (delivery_style.HALFTONE_RADIUS_MIN
                     + delivery_style.HALFTONE_RADIUS_GROWTH * t)
    img = _paint(_flat(height, width, base), white,
                delivery_style.HALFTONE_DOT_ALPHA
                * _edge(radius - np.hypot(gx, gy), delivery_style.HALFTONE_EDGE_SOFT))
    ax = x.max() * delivery_style.HALFTONE_CRESCENT_CENTER[0]
    ay = y.max() * delivery_style.HALFTONE_CRESCENT_CENTER[1]
    hole_dx, hole_dy = delivery_style.HALFTONE_CRESCENT_HOLE_OFFSET
    crescent = (_edge(delivery_style.HALFTONE_CRESCENT_RADIUS - np.hypot(x - ax, y - ay))
               * (1 - _edge(delivery_style.HALFTONE_CRESCENT_HOLE_RADIUS
                           - np.hypot(x - ax + hole_dx, y - ay - hole_dy))))
    img = _paint(img, white, delivery_style.HALFTONE_CRESCENT_ALPHA * crescent)
    return np.clip(img, 0, 255)


def sunburst(height: int, width: int) -> np.ndarray:
    """Alternating wide wedges from behind the figure, no bands."""
    x, y = _grid(height, width)
    base, light, _white = _palette()
    cx = x.max() * delivery_style.SUNBURST_CENTER[0]
    cy = y.max() * delivery_style.SUNBURST_CENTER[1]
    ang = np.arctan2(y - cy, x - cx)
    wedge = _edge(((ang * delivery_style.SUNBURST_WEDGES / (2 * np.pi)) % 1.0) - 0.5,
                 delivery_style.SUNBURST_EDGE_SOFT)
    img = _paint(_flat(height, width, light), base, wedge)
    return np.clip(img, 0, 255)


def chevron(height: int, width: int) -> np.ndarray:
    """Horizontal zigzag bands."""
    x, y = _grid(height, width)
    base, light, _white = _palette()
    zig = (delivery_style.CHEVRON_AMPLITUDE
          * np.abs(((x / delivery_style.CHEVRON_PERIOD) % 1.0) * 2 - 1))
    band = ((y + zig) / delivery_style.CHEVRON_PITCH) % 1.0
    img = _paint(_flat(height, width, light), base,
                _edge(band - 0.5, delivery_style.CHEVRON_EDGE_SOFT))
    return np.clip(img, 0, 255)


def checker(height: int, width: int) -> np.ndarray:
    """Diagonal checkerboard, lavender and light, weak burst behind."""
    x, y = _grid(height, width)
    base, light, _white = _palette()
    diagonal = delivery_style.CHECKER_CELL * 2 ** 0.5
    u, v = (x + y) / diagonal, (x - y) / diagonal
    c = (np.floor(u) + np.floor(v)) % 2
    img = _paint(_flat(height, width, light), base, c)
    img = _burst(img, x, y, delivery_style.CHECKER_BURST)
    return np.clip(img, 0, 255)


PATTERNS = {
    "stripes": stripes,
    "dots": dots,
    "gingham": gingham,
    "moons": moons,
    "halftone": halftone,
    "sunburst": sunburst,
    "chevron": chevron,
    "checker": checker,
}


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


def thumbnail(name: str) -> bytes:
    """PNG bytes of the named pattern alone, at the catalog's thumbnail size."""
    width = delivery_style.BACKDROP_THUMBNAIL_WIDTH
    height = delivery_style.BACKDROP_THUMBNAIL_HEIGHT
    pixels = np.clip(PATTERNS[name](height, width), 0, 255).astype(np.uint8)
    output = io.BytesIO()
    Image.fromarray(pixels, "RGB").save(output, "PNG")
    return output.getvalue()
