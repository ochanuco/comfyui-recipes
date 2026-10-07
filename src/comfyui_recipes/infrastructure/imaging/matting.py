"""Per-pixel alpha for the delivery cut: a trimap from the retraced matte,
solved by a matting model, with the figure's own colour recovered under it.

The model and the foreground estimator are passed in, so this module stays
numpy-only; the worker's node pack supplies both.
"""

from __future__ import annotations

import io
from collections.abc import Callable

import numpy as np
from PIL import Image
from scipy import ndimage

from ...domain.yukari import delivery_style
from . import delivery

# (rgb uint8 HxWx3, trimap uint8 HxW of 0/128/255) -> alpha float HxW in 0..1
Predict = Callable[[np.ndarray, np.ndarray], np.ndarray]
# (rgb float HxWx3 in 0..1, alpha float HxW) -> foreground float HxWx3 in 0..1
Foreground = Callable[[np.ndarray, np.ndarray], np.ndarray]

KNOWN_FIGURE = 255
UNKNOWN = 128
KNOWN_BACKDROP = 0


def trimap(figure: np.ndarray, width: int) -> np.ndarray:
    known = np.full(figure.shape, UNKNOWN, dtype=np.uint8)
    known[ndimage.binary_erosion(figure, iterations=width)] = KNOWN_FIGURE
    known[~ndimage.binary_dilation(figure, iterations=width)] = KNOWN_BACKDROP
    return known


def _starts(length: int, tile: int, step: int) -> list[int]:
    if length <= tile:
        return [0]
    starts = list(range(0, length - tile, step))
    return starts + [length - tile]


def _feather(size: int, overlap: int) -> np.ndarray:
    index = np.arange(size, dtype=float)
    return np.clip(np.minimum(index + 1, size - index) / max(overlap, 1), 0.0, 1.0)


def tiled(predict: Predict, rgb: np.ndarray, known: np.ndarray, tile: int,
          overlap: int) -> np.ndarray:
    """`predict` over the tiles that hold unknown pixels, feathered together.
    Pixels no tile visits keep the trimap's own 0 or 1."""
    height, width = known.shape
    unknown = known == UNKNOWN
    total = np.zeros(known.shape)
    weight = np.zeros(known.shape)
    step = tile - overlap
    for top in _starts(height, tile, step):
        for left in _starts(width, tile, step):
            window = (slice(top, top + tile), slice(left, left + tile))
            if not unknown[window].any():
                continue
            alpha = predict(rgb[window], known[window])
            feather = np.outer(_feather(alpha.shape[0], overlap),
                               _feather(alpha.shape[1], overlap))
            total[window] += alpha * feather
            weight[window] += feather
    alpha = (known == KNOWN_FIGURE).astype(float)
    solved = unknown & (weight > 0)
    alpha[solved] = total[solved] / weight[solved]
    return alpha


def finish(px: np.ndarray, alpha: np.ndarray, known: np.ndarray,
           foreground: Foreground) -> tuple[np.ndarray, np.ndarray]:
    """The trimap's known regions forced onto `alpha`, and the figure's colour
    under it: estimated where alpha > 0 and despilled of the raw key on the
    soft edge, the raw pixel where alpha is 0."""
    alpha = np.clip(alpha, 0.0, 1.0)
    alpha[known == KNOWN_FIGURE] = 1.0
    alpha[known == KNOWN_BACKDROP] = 0.0
    colour = np.clip(foreground(px / 255.0, alpha), 0.0, 1.0) * 255.0
    edge = (alpha > 0) & ~ndimage.binary_erosion(alpha >= 1.0)
    colour = delivery.despill(colour, ndimage.binary_dilation(edge, iterations=2),
                              delivery._corner_seed(px))
    return np.where((alpha > 0)[..., None], colour, px), alpha


def matte_png(data: bytes, matte: bytes, predict: Predict,
              foreground: Foreground) -> tuple[bytes, bytes]:
    """The foreground picture (RGB PNG) and its alpha (L PNG) for `data`,
    from the matte model's soft output `matte`."""
    px = np.array(Image.open(io.BytesIO(data)).convert("RGB")).astype(float)
    soft = np.array(Image.open(io.BytesIO(matte)).convert("L"))
    known = trimap(delivery.cut_figure(px, soft), delivery_style.MATTING_TRIMAP_PX)
    alpha = tiled(predict, px.astype(np.uint8), known,
                  delivery_style.MATTING_TILE_PX,
                  delivery_style.MATTING_TILE_OVERLAP_PX)
    colour, alpha = finish(px, alpha, known, foreground)
    image_out, alpha_out = io.BytesIO(), io.BytesIO()
    Image.fromarray(np.clip(np.rint(colour), 0, 255).astype(np.uint8)).save(
        image_out, "PNG")
    Image.fromarray(np.clip(np.rint(alpha * 255), 0, 255).astype(np.uint8),
                    "L").save(alpha_out, "PNG")
    return image_out.getvalue(), alpha_out.getvalue()
