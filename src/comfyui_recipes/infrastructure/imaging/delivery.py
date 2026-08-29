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
    seed = pixels[0, 0]
    candidates = np.abs(pixels - seed).max(axis=2) <= tolerance
    structure = ndimage.generate_binary_structure(2, 1)
    labels, _ = ndimage.label(candidates, structure=structure)
    seed_label = labels[0, 0]
    return candidates & (labels == seed_label)


def enclosed_mask(pixels: np.ndarray, found: np.ndarray,
                  tolerance: int) -> np.ndarray:
    seed = pixels[0, 0]
    return (np.abs(pixels - seed).max(axis=2) <= tolerance) & ~found


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


def band_thickness(pixels: np.ndarray, mask: np.ndarray,
                   dark: int = 120) -> float:
    inward = ndimage.distance_transform_edt(~mask)
    to_line = ndimage.distance_transform_edt(pixels.mean(axis=2) >= dark)
    contour = (inward > 0) & (inward <= 1)
    if not contour.any():
        return 0.0
    distances = to_line[contour]
    if float((distances > 20.0).mean()) >= 0.5:
        return 0.0
    return float(np.median(distances))


def stroke(pixels: np.ndarray, color: str, *, tolerance: int = 18,
           enclosed_tolerance: int = 4) -> tuple[np.ndarray, float]:
    mask = background_mask(pixels.astype(int), tolerance)
    mask |= enclosed_mask(pixels.astype(int), mask, enclosed_tolerance)
    width = max(
        band_thickness(pixels, mask) * delivery_style.STROKE_WIDTH_BAND,
        max(pixels.shape[:2]) * delivery_style.STROKE_WIDTH_PCT / 100,
    )
    distance = ndimage.distance_transform_edt(mask)
    alpha = np.clip(width + 0.5 - distance, 0.0, 1.0)
    alpha *= np.clip(distance + 0.5, 0.0, 1.0)
    alpha[~mask] = 0.0
    rgb = np.array(parse_color(color), dtype=float)
    return pixels + alpha[..., None] * (rgb - pixels), width


def clean_background(data: bytes) -> tuple[bytes, str]:
    backdrop = parse_color(delivery_style.BACKDROP)
    pixels = np.array(Image.open(io.BytesIO(data)).convert("RGB")).astype(int)
    background = background_mask(pixels, 18)
    labels, count = ndimage.label(~background)
    if count > 1:
        sizes = ndimage.sum(np.ones_like(labels), labels, range(1, count + 1))
        pixels[(~background) & (labels != 1 + int(np.argmax(sizes)))] = backdrop
    pixels, _ = repaint(pixels, backdrop, enclosed_tolerance=4)
    off_backdrop = np.abs(pixels - backdrop).sum(axis=2) > 30
    labels, count = ndimage.label(off_backdrop)
    if count > 1:
        sizes = ndimage.sum(np.ones_like(labels), labels, range(1, count + 1))
        pixels[off_backdrop & (labels != 1 + int(np.argmax(sizes)))] = backdrop
    pixels, width = stroke(pixels.astype(float), delivery_style.STROKE)
    output = io.BytesIO()
    Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8)).save(output, "PNG")
    return output.getvalue(), f"clean-p{width:.0f}"
