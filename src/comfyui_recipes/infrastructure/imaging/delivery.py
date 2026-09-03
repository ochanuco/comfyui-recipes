"""Decode a ComfyUI PNG and apply Yukari's delivery background and stroke."""

from __future__ import annotations

import io
import json
import string

import numpy as np
from PIL import Image
from scipy import ndimage

from ...domain.yukari import delivery_style


def graph_from_png(data: bytes) -> dict:
    prompt = Image.open(io.BytesIO(data)).info.get("prompt")
    if prompt is None:
        raise SystemExit("PNG has no ComfyUI prompt metadata")
    try:
        graph = json.loads(prompt)
    except (json.JSONDecodeError, TypeError) as error:
        raise SystemExit("PNG has invalid ComfyUI prompt metadata") from error
    if not isinstance(graph, dict):
        raise SystemExit("PNG has invalid ComfyUI prompt metadata")
    return graph


def parse_color(text: str) -> tuple[int, int, int]:
    value = text.lstrip("#")
    if len(value) != 6 or any(character not in string.hexdigits
                              for character in value):
        raise SystemExit(f"expected a 6-digit hex colour, got {text!r}")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _corner_seed(pixels: np.ndarray) -> np.ndarray:
    """The backdrop colour, as the corner patch's median.

    The single pixel (0, 0) can be a lone grain spike 20+ off the field it
    sits in, and the whole flood dies against it while every corner still
    averages flat -- a delivered picture with no die-cut at all.
    """
    return np.median(pixels[:8, :8].reshape(-1, 3), axis=0)


def background_mask(pixels: np.ndarray, tolerance: int) -> np.ndarray:
    """Every backdrop region that reaches the frame edge."""
    seed = _corner_seed(pixels)
    candidates = np.abs(pixels - seed).max(axis=2) <= tolerance
    structure = ndimage.generate_binary_structure(2, 1)
    labels, _ = ndimage.label(candidates, structure=structure)
    edges = np.concatenate(
        [labels[0], labels[-1], labels[:, 0], labels[:, -1]])
    reaching = np.unique(edges[edges > 0])
    return np.isin(labels, reaching)


def enclosed_mask(pixels: np.ndarray, found: np.ndarray, tolerance: int, *,
                  minimum_area: int = 16) -> np.ndarray:
    """Backdrop the figure encloses, as regions rather than as pixels.

    Interior linework holds pixels within the tolerance of the backdrop, so
    the colour test alone claims specks along every stroke. Only components
    of at least `minimum_area` survive.
    """
    seed = _corner_seed(pixels)
    candidates = (np.abs(pixels - seed).max(axis=2) <= tolerance) & ~found
    labels, count = ndimage.label(
        candidates, ndimage.generate_binary_structure(2, 2))
    if not count:
        return candidates
    sizes = ndimage.sum(candidates, labels, range(1, count + 1))
    return np.isin(labels, 1 + np.nonzero(sizes >= minimum_area)[0])


def corner_spread(data: bytes) -> float:
    """Brightness spread across the four 40px corners of a decoded PNG."""
    pixels = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    c = 40
    corners = [pixels[:c, :c], pixels[:c, -c:], pixels[-c:, :c], pixels[-c:, -c:]]
    means = [corner.reshape(-1, 3).mean() for corner in corners]
    return float(max(means) - min(means))


def down2(pixels: np.ndarray) -> np.ndarray:
    """2x2 box-downsample."""
    height, width = pixels.shape[:2]
    trimmed = pixels[:height - height % 2, :width - width % 2]
    return trimmed.reshape(
        height // 2, 2, width // 2, 2, *pixels.shape[2:]).mean(axis=(1, 3))


def refine_matte(pixels: np.ndarray, figure: np.ndarray, band: int,
                 tolerance: int) -> np.ndarray:
    """Retrace the matte's edge by colour, `band` pixels either side of it.

    The matte model loses the thin strands and the hard threshold then
    cuts what it kept into stubs; the redraw's flat backdrop makes the colour
    test exact there. The backdrop is read locally -- a normalised blur of
    the pixels the matte puts well outside the figure -- because a bigger
    redraw shades it toward the figure. Islands smaller than band*band are
    the backdrop's own grain and go.
    """
    if band < 1:
        return figure
    outside = ~ndimage.binary_dilation(figure, iterations=band * 2)
    sigma = band * 4
    weight = ndimage.gaussian_filter(outside.astype(float), sigma)
    local = np.stack(
        [ndimage.gaussian_filter(pixels[..., c] * outside, sigma)
         for c in range(3)], axis=-1) / np.maximum(weight, 1e-6)[..., None]
    edge = (ndimage.binary_dilation(figure, iterations=band)
            & ~ndimage.binary_erosion(figure, iterations=band))
    refined = figure.copy()
    refined[edge] = (np.abs(pixels - local).max(axis=2) > tolerance)[edge]
    labels, count = ndimage.label(refined)
    if not count:
        return refined
    sizes = ndimage.sum(refined, labels, range(1, count + 1))
    return np.isin(labels, 1 + np.nonzero(sizes >= band * band)[0])


def stroke_alpha(mask: np.ndarray, gap: float, width: float) -> np.ndarray:
    """Coverage of the band, gap..gap+width pixels out into the backdrop.

    `distance_transform_edt` on the backdrop gives each backdrop pixel its
    distance to the nearest figure pixel, so the first ring out is 1. Both
    edges are ramped over one pixel; the inner ramp does nothing at gap 0 and
    keeps the stroke from stepping when it is pushed away from the figure.
    """
    distance = ndimage.distance_transform_edt(mask)
    outer = np.clip(gap + width + 0.5 - distance, 0.0, 1.0)
    inner = np.clip(distance - gap + 0.5, 0.0, 1.0)
    alpha = outer * inner
    alpha[~mask] = 0.0
    return alpha


def clean_background(data: bytes, matte: bytes) -> tuple[bytes, str]:
    """Frame the figure the matte cuts out, in the delivery's own colours.

    The matte is the authority on the silhouette. Colour cannot be: repin
    moves the figure's own colours, and the pale hair lands inside the
    backdrop's tolerance once it has.
    """
    backdrop_rgb = parse_color(delivery_style.BACKDROP)
    px = np.array(Image.open(io.BytesIO(data)).convert("RGB")).astype(float)
    figure = np.array(Image.open(io.BytesIO(matte)).convert("L")) > 127
    height, width = px.shape[:2]
    figure = refine_matte(
        px, figure,
        int(max(height, width) * delivery_style.MATTE_EDGE_BAND_PCT / 100),
        delivery_style.MATTE_EDGE_TOLERANCE)
    px[~figure] = backdrop_rgb

    bg2 = ~(np.array(Image.fromarray(figure)
                     .resize((width * 2, height * 2), Image.NEAREST)))

    white_w = max(height, width) * delivery_style.WHITE_WIDTH_PCT / 100
    purple_w = white_w * delivery_style.STROKE_WIDTH_BAND
    white_a = down2(stroke_alpha(bg2, 0.0, white_w * 2))
    purple_a = down2(stroke_alpha(bg2, white_w * 2, purple_w * 2))
    fig_a = down2((~bg2).astype(float))

    white_rgb = np.array([255.0, 255.0, 255.0])
    purple_rgb = np.array(parse_color(delivery_style.STROKE), dtype=float)
    flat = np.broadcast_to(np.array(backdrop_rgb, dtype=float), px.shape).copy()

    composite = flat + purple_a[..., None] * (purple_rgb - flat)
    composite = composite + white_a[..., None] * (white_rgb - composite)
    composite = composite + fig_a[..., None] * (px - composite)

    output = io.BytesIO()
    Image.fromarray(np.clip(composite, 0, 255).astype(np.uint8)).save(output, "PNG")
    return output.getvalue(), f"clean-w{white_w:.0f}-p{purple_w:.0f}"
