"""Depth-of-field blur: a circle of confusion that grows with distance from a
focus point, applied to the figure only."""

from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image

LEVELS = 8
R_MAX_FRACTION = 0.06
K_FRACTION = 0.06
DEPTH_PERCENTILES = (2, 98)
FOCUS_WINDOW_FRACTION = 0.015
ALPHA_EPSILON = 1e-4
MATTE_THRESHOLD = 0.5


def _normalised_depth(depth: np.ndarray, inside: np.ndarray) -> np.ndarray | None:
    sample = depth[inside] if inside.any() else depth.ravel()
    low, high = np.percentile(sample, DEPTH_PERCENTILES)
    if high - low < 1e-6:
        return None
    return np.clip((depth - low) / (high - low), 0.0, 1.0)


def _focus_depth(depth: np.ndarray, focus_x: float, focus_y: float) -> float:
    height, width = depth.shape
    radius = max(1, round(FOCUS_WINDOW_FRACTION * max(width, height)))
    cx = min(width - 1, int(focus_x * width))
    cy = min(height - 1, int(focus_y * height))
    window = depth[max(0, cy - radius):cy + radius + 1,
                   max(0, cx - radius):cx + radius + 1]
    return float(np.median(window))


def depth_blur(rgb: np.ndarray, depth: np.ndarray, alpha: np.ndarray,
               focus_x: float, focus_y: float, f_number: float) -> np.ndarray:
    """`rgb` is HxWx3 uint8, `depth` HxW float with higher = nearer, `alpha`
    HxW float 0..1. Pixels outside the matte come back untouched."""
    height, width = alpha.shape
    long_side = max(width, height)
    inside = alpha > MATTE_THRESHOLD
    normalised = _normalised_depth(depth, inside)
    if normalised is None or not inside.any():
        return rgb
    d_focus = _focus_depth(normalised, focus_x, focus_y)
    r_max = R_MAX_FRACTION * long_side
    radius = np.minimum(
        r_max, K_FRACTION * long_side * np.abs(normalised - d_focus) / f_number)
    position = radius / r_max * (LEVELS - 1)

    source = rgb.astype(np.float32)
    premultiplied = np.concatenate(
        [source * alpha[..., None], alpha[..., None]], axis=-1).astype(np.float32)
    blended = np.zeros_like(source)
    for level in range(LEVELS):
        weight = np.clip(1.0 - np.abs(position - level), 0.0, 1.0)
        if not weight.any():
            continue
        sigma = r_max * level / (LEVELS - 1) / 2
        if sigma == 0:
            layer = source
        else:
            blurred = cv2.GaussianBlur(premultiplied, (0, 0), sigma)
            coverage = blurred[..., 3:4]
            layer = np.where(coverage > ALPHA_EPSILON,
                             blurred[..., :3] / np.maximum(coverage, ALPHA_EPSILON),
                             source)
        blended += layer * weight[..., None]
    result = np.where(inside[..., None], blended, source)
    return np.clip(np.rint(result), 0, 255).astype(np.uint8)


def depth_blur_png(image_png: bytes, depth_png: bytes, matte_png: bytes,
                   focus_x: float, focus_y: float, f_number: float) -> bytes:
    rgb = np.array(Image.open(io.BytesIO(image_png)).convert("RGB"))
    height, width = rgb.shape[:2]
    depth = np.array(Image.open(io.BytesIO(depth_png)).convert("L"),
                     dtype=np.float32)
    matte = np.array(Image.open(io.BytesIO(matte_png)).convert("L"),
                     dtype=np.float32) / 255.0
    depth = cv2.resize(depth, (width, height), interpolation=cv2.INTER_LINEAR)
    matte = cv2.resize(matte, (width, height), interpolation=cv2.INTER_LINEAR)
    out = depth_blur(rgb, depth, matte, focus_x, focus_y, f_number)
    output = io.BytesIO()
    Image.fromarray(out, "RGB").save(output, "PNG")
    return output.getvalue()
