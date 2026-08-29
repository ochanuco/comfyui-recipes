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


def background_mask(pixels: np.ndarray, tolerance: int) -> np.ndarray:
    """Every backdrop region that reaches the frame edge."""
    seed = pixels[0, 0]
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
    seed = pixels[0, 0]
    candidates = (np.abs(pixels - seed).max(axis=2) <= tolerance) & ~found
    labels, count = ndimage.label(
        candidates, ndimage.generate_binary_structure(2, 2))
    if not count:
        return candidates
    sizes = ndimage.sum(candidates, labels, range(1, count + 1))
    return np.isin(labels, 1 + np.nonzero(sizes >= minimum_area)[0])


def repaint(pixels: np.ndarray, color: tuple[int, int, int], *,
            tolerance: int = 18, enclosed_tolerance: int = 4,
            feather: int = 1, feather_tolerance: int = 54) -> tuple[np.ndarray, float]:
    mask = background_mask(pixels, tolerance)
    if enclosed_tolerance >= 0:
        mask |= enclosed_mask(pixels, mask, enclosed_tolerance)
    share = mask.mean() * 100
    seed = pixels[0, 0]
    if feather > 0:
        band = ndimage.binary_dilation(mask, iterations=feather) & ~mask
        distance = np.abs(pixels - seed).max(axis=2)
        alpha = np.clip(
            (feather_tolerance - distance)
            / max(feather_tolerance - tolerance, 1), 0.0, 1.0)
        alpha[~band] = 0.0
        pixels = np.clip(
            pixels + alpha[..., None] * (np.array(color) - seed), 0, 255)
    pixels[mask] = color
    return pixels, share


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


def clean_background(data: bytes) -> tuple[bytes, str]:
    backdrop_rgb = parse_color(delivery_style.BACKDROP)
    pixels = np.array(Image.open(io.BytesIO(data)).convert("RGB")).astype(int)
    background = background_mask(pixels, 18)
    labels, count = ndimage.label(~background)
    if count > 1:
        sizes = ndimage.sum(np.ones_like(labels), labels, range(1, count + 1))
        pixels[(~background) & (labels != 1 + int(np.argmax(sizes)))] = backdrop_rgb
    pixels, _ = repaint(pixels, backdrop_rgb, enclosed_tolerance=4)
    off_backdrop = np.abs(pixels - backdrop_rgb).sum(axis=2) > 30
    labels, count = ndimage.label(off_backdrop)
    if count > 1:
        sizes = ndimage.sum(np.ones_like(labels), labels, range(1, count + 1))
        pixels[off_backdrop & (labels != 1 + int(np.argmax(sizes)))] = backdrop_rgb

    px = pixels.astype(float)
    height, width = px.shape[:2]
    px2 = np.array(Image.fromarray(np.clip(px, 0, 255).astype(np.uint8))
                   .resize((width * 2, height * 2), Image.BILINEAR)).astype(float)
    bg2 = background_mask(px2.astype(int), 18)
    bg2 |= enclosed_mask(px2.astype(int), bg2, 4)

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
