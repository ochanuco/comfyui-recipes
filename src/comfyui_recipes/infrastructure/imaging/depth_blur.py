"""Depth-of-field blur: a lens-disc circle of confusion that grows with
distance from a focus point, applied to the figure in linear light. Where the
figure is out of focus its silhouette fades into PAPER and the matte widens to
take the fade in."""

from __future__ import annotations

import io

import cv2
import numpy as np
from scipy import ndimage
from PIL import Image

LEVELS = 8
K_FRACTION = 0.024
DEPTH_PERCENTILES = (2, 98)
FOCUS_WINDOW_FRACTION = 0.015
ALPHA_EPSILON = 1e-4
MATTE_THRESHOLD = 0.5
SPREAD_CUT = 0.04
PAPER = (255, 255, 255)


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


def _disc(radius: float) -> np.ndarray:
    reach = int(np.ceil(radius))
    y, x = np.mgrid[-reach:reach + 1, -reach:reach + 1]
    kernel = np.clip(radius + 0.5 - np.hypot(x, y), 0.0, 1.0).astype(np.float32)
    return kernel / kernel.sum()


def _to_linear(rgb: np.ndarray) -> np.ndarray:
    c = rgb / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _to_srgb(linear: np.ndarray) -> np.ndarray:
    c = np.clip(linear, 0.0, 1.0)
    return 255.0 * np.where(c <= 0.0031308, c * 12.92,
                            1.055 * c ** (1 / 2.4) - 0.055)


def _spread_outward(radius: np.ndarray, inside: np.ndarray) -> np.ndarray:
    _, (rows, cols) = ndimage.distance_transform_edt(~inside, return_indices=True)
    return radius[rows, cols]


def depth_blur(rgb: np.ndarray, depth: np.ndarray, alpha: np.ndarray,
               focus_x: float, focus_y: float, f_number: float
               ) -> tuple[np.ndarray, np.ndarray]:
    """`rgb` is HxWx3 uint8, `depth` HxW float with higher = nearer, `alpha`
    HxW float 0..1. Returns the blurred picture and the matte widened to
    where the out-of-focus figure fades into PAPER; pixels outside that
    matte come back untouched."""
    height, width = alpha.shape
    long_side = max(width, height)
    inside = alpha > MATTE_THRESHOLD
    normalised = _normalised_depth(depth, inside)
    if normalised is None or not inside.any():
        return rgb, alpha
    d_focus = _focus_depth(normalised, focus_x, focus_y)
    radius = _spread_outward(
        K_FRACTION * long_side * np.abs(normalised - d_focus) / f_number, inside)
    r_max = float(radius.max())
    if r_max <= 0:
        return rgb, alpha
    position = np.minimum(radius / r_max, 1.0) * (LEVELS - 1)

    source = _to_linear(rgb.astype(np.float32)).astype(np.float32)
    colour = np.zeros_like(source)
    cover = np.zeros_like(alpha, dtype=np.float32)
    for level in range(LEVELS):
        weight = np.clip(1.0 - np.abs(position - level), 0.0, 1.0)
        if not weight.any():
            continue
        level_radius = r_max * level / (LEVELS - 1)
        if level_radius < 0.5:
            layer, layer_cover = source, alpha
        else:
            kernel = _disc(level_radius)
            contributes = alpha * np.clip(
                (radius - 0.5 * level_radius) / (0.5 * level_radius), 0.0, 1.0)
            premultiplied = np.concatenate(
                [source * contributes[..., None], contributes[..., None]],
                axis=-1).astype(np.float32)
            gathered = cv2.filter2D(premultiplied, -1, kernel,
                                    borderType=cv2.BORDER_REPLICATE)
            weight_sum = gathered[..., 3:4]
            layer = np.where(weight_sum > ALPHA_EPSILON,
                             gathered[..., :3] / np.maximum(weight_sum, ALPHA_EPSILON),
                             source)
            layer_cover = cv2.filter2D(alpha.astype(np.float32), -1, kernel,
                                       borderType=cv2.BORDER_REPLICATE)
        colour += layer * weight[..., None]
        cover += layer_cover * weight
    cover = np.clip(cover, 0.0, 1.0)
    paper = _to_linear(np.array(PAPER, np.float32))
    painted = _to_srgb(colour * cover[..., None] + paper * (1.0 - cover[..., None]))
    widened = inside | (cover > SPREAD_CUT)
    result = np.where(widened[..., None], painted, rgb.astype(np.float32))
    matte = np.maximum(alpha, widened.astype(np.float32))
    return np.clip(np.rint(result), 0, 255).astype(np.uint8), matte


def depth_blur_png(image_png: bytes, depth_png: bytes, matte_png: bytes,
                   focus_x: float, focus_y: float, f_number: float
                   ) -> tuple[bytes, bytes]:
    rgb = np.array(Image.open(io.BytesIO(image_png)).convert("RGB"))
    height, width = rgb.shape[:2]
    depth = np.array(Image.open(io.BytesIO(depth_png)).convert("L"),
                     dtype=np.float32)
    matte = np.array(Image.open(io.BytesIO(matte_png)).convert("L"),
                     dtype=np.float32) / 255.0
    depth = cv2.resize(depth, (width, height), interpolation=cv2.INTER_LINEAR)
    matte = cv2.resize(matte, (width, height), interpolation=cv2.INTER_LINEAR)
    out, widened = depth_blur(rgb, depth, matte, focus_x, focus_y, f_number)
    image_out, matte_out = io.BytesIO(), io.BytesIO()
    Image.fromarray(out, "RGB").save(image_out, "PNG")
    Image.fromarray(np.clip(np.rint(widened * 255.0), 0, 255).astype(np.uint8),
                    "L").save(matte_out, "PNG")
    return image_out.getvalue(), matte_out.getvalue()
