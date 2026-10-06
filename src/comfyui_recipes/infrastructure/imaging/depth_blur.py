"""Depth-of-field blur: a lens-disc circle of confusion that grows with
distance from a focus point, applied to the figure in linear light. Where the
figure is out of focus its silhouette fades into PAPER and the matte widens to
take the fade in. Key-coloured pockets the matte encloses stay raw, for
delivery's own key cut. `blur_layered` instead blurs the delivered picture in
depth slices composited back to front, so a blurred near object spreads over
what stands behind it: the figure keeps its own depth, the sticker rim and
shadow take the depth of the nearest figure pixel, the backdrop sits on the
far plane."""

from __future__ import annotations

import io

import cv2
import numpy as np
from scipy import ndimage
from PIL import Image

from ...domain.yukari import delivery_style

LEVELS = 8
K_FRACTION = 0.024
DEPTH_PERCENTILES = (2, 98)
FOCUS_WINDOW_FRACTION = 0.015
ALPHA_EPSILON = 1e-4
MATTE_THRESHOLD = 0.5
SPREAD_CUT = 0.04
STICKER_TOLERANCE = 6
STICKER_CLOSING = 2
SLICES = 16
OWN_SLICE = 0.5
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


def _key_pixels(rgb: np.ndarray) -> np.ndarray:
    pixels = rgb.astype(np.float32)
    key = np.median(pixels[:8, :8].reshape(-1, 3), axis=0)
    if key[1] - max(key[0], key[2]) < delivery_style.ENCLOSED_KEY_MIN_GREEN_EXCESS:
        return np.zeros(rgb.shape[:2], bool)
    return np.abs(pixels - key).max(axis=2) <= delivery_style.MATTE_EDGE_TOLERANCE


def depth_blur(rgb: np.ndarray, depth: np.ndarray, alpha: np.ndarray,
               focus_x: float, focus_y: float, f_number: float
               ) -> tuple[np.ndarray, np.ndarray]:
    """`rgb` is HxWx3 uint8, `depth` HxW float with higher = nearer, `alpha`
    HxW float 0..1. Returns the blurred picture and the matte widened to
    where the out-of-focus figure fades into PAPER; pixels outside that
    matte, and key-coloured pockets inside the matte, come back untouched."""
    height, width = alpha.shape
    long_side = max(width, height)
    source_alpha = alpha
    pocket = _key_pixels(rgb) & (source_alpha > MATTE_THRESHOLD)
    alpha = np.where(pocket, 0.0, alpha).astype(np.float32)
    inside = alpha > MATTE_THRESHOLD
    normalised = _normalised_depth(depth, inside)
    if normalised is None or not inside.any():
        return rgb, source_alpha
    d_focus = _focus_depth(normalised, focus_x, focus_y)
    radius = _spread_outward(
        K_FRACTION * long_side * np.abs(normalised - d_focus) / f_number, inside)
    r_max = float(radius.max())
    if r_max <= 0:
        return rgb, source_alpha
    position = np.minimum(radius / r_max, 1.0) * (LEVELS - 1)

    source = _to_linear(rgb.astype(np.float32)).astype(np.float32)
    colour = np.zeros_like(source)
    cover = np.zeros_like(alpha, dtype=np.float32)
    spread = np.zeros_like(alpha, dtype=np.float32)
    for level in range(LEVELS):
        weight = np.clip(1.0 - np.abs(position - level), 0.0, 1.0)
        if not weight.any():
            continue
        level_radius = r_max * level / (LEVELS - 1)
        if level_radius < 0.5:
            layer, layer_cover = source, np.ones_like(alpha)
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
            spread += layer_cover * weight
        colour += layer * weight[..., None]
        cover += layer_cover * weight
    cover = np.clip(cover, 0.0, 1.0)
    paper = _to_linear(np.array(PAPER, np.float32))
    painted = _to_srgb(colour * cover[..., None] + paper * (1.0 - cover[..., None]))
    widened = (inside | (spread > SPREAD_CUT)) & ~pocket
    result = np.where(widened[..., None], painted, rgb.astype(np.float32))
    matte = np.maximum(source_alpha, widened.astype(np.float32))
    return np.clip(np.rint(result), 0, 255).astype(np.uint8), matte


def _sticker_mask(composite: np.ndarray, figure: np.ndarray,
                  backdrop_rgb: np.ndarray | None) -> np.ndarray:
    if backdrop_rgb is None:
        return figure
    differs = np.abs(composite.astype(np.float32)
                     - backdrop_rgb.astype(np.float32)).max(axis=2) > STICKER_TOLERANCE
    differs = ndimage.binary_closing(differs, iterations=STICKER_CLOSING)
    return ndimage.binary_fill_holes(differs) | figure


def _push_pull(rgb: np.ndarray, known: np.ndarray) -> np.ndarray:
    levels = []
    colour, weight = rgb * known[..., None], known.astype(np.float32)
    while min(weight.shape) > 8:
        levels.append((colour, weight))
        colour, weight = cv2.pyrDown(colour), cv2.pyrDown(weight)
    filled = colour / np.maximum(weight, 1e-6)[..., None]
    for colour, weight in reversed(levels):
        up = cv2.resize(filled, (weight.shape[1], weight.shape[0]),
                        interpolation=cv2.INTER_LINEAR)
        own = colour / np.maximum(weight, 1e-6)[..., None]
        trust = np.clip(weight * 4, 0, 1)[..., None]
        filled = own * trust + up * (1 - trust)
    return filled


def _blur_layer(rgb: np.ndarray, alpha: np.ndarray, radius: float
                ) -> tuple[np.ndarray, np.ndarray]:
    """Premultiplied colour and alpha of the layer after the lens disc."""
    if radius < 0.5:
        return rgb * alpha[..., None], alpha
    premultiplied = np.concatenate(
        [rgb * alpha[..., None], alpha[..., None]], axis=-1).astype(np.float32)
    gathered = cv2.filter2D(premultiplied, -1, _disc(radius),
                            borderType=cv2.BORDER_REPLICATE)
    return gathered[..., :3], np.clip(gathered[..., 3], 0.0, 1.0)


def _picture_depth(composite: np.ndarray, normalised: np.ndarray,
                   figure: np.ndarray, backdrop_rgb: np.ndarray | None
                   ) -> np.ndarray:
    sticker = _sticker_mask(composite, figure, backdrop_rgb)
    depth = np.where(sticker, _spread_outward(normalised, figure), 0.0)
    return np.where(figure, normalised, depth)


def blur_layered(composite: np.ndarray, depth: np.ndarray,
                 figure_matte: np.ndarray, focus_x: float, focus_y: float,
                 f_number: float, backdrop_rgb: np.ndarray | None) -> np.ndarray:
    """`composite` is the delivered HxWx3 uint8 picture, `depth` HxW float with
    higher = nearer, `figure_matte` HxW float 0..1. `backdrop_rgb` is what the
    delivery painted behind the sticker, or None when the kept scene is the
    backdrop. The picture is cut into depth slices, each blurred with its own
    disc and composited back to front; behind a nearer slice a slice continues
    with colour filled from its own pixels."""
    height, width = figure_matte.shape
    figure = figure_matte > MATTE_THRESHOLD
    normalised = _normalised_depth(depth, figure)
    if normalised is None or not figure.any():
        return composite
    picture_depth = _picture_depth(composite, normalised, figure, backdrop_rgb)
    d_focus = _focus_depth(picture_depth, focus_x, focus_y)
    scale = K_FRACTION * max(width, height) / f_number

    ground = _to_linear(composite.astype(np.float32)).astype(np.float32)
    centres = np.linspace(0.0, 1.0, SLICES)
    step = centres[1] - centres[0]
    colour = np.zeros_like(ground)
    cover = np.zeros((height, width), np.float32)
    seen = np.zeros((height, width), np.float32)
    for index, centre in enumerate(centres):
        weight = np.clip(1.0 - np.abs(picture_depth - centre) / step, 0.0, 1.0)
        if not weight.any():
            continue
        seen = seen + weight
        alpha = np.where(seen > ALPHA_EPSILON,
                         weight / np.maximum(seen, ALPHA_EPSILON), 0.0)
        rgb = ground
        hidden = picture_depth > centre + step
        own = weight > OWN_SLICE
        if hidden.any() and index < SLICES - 1 and own.any():
            rgb = np.where(hidden[..., None],
                           _push_pull(ground, own.astype(np.float32)), ground)
            alpha = np.where(hidden, 1.0, alpha)
        layer, layer_alpha = _blur_layer(
            rgb, alpha.astype(np.float32), scale * abs(centre - d_focus))
        colour = layer + colour * (1.0 - layer_alpha[..., None])
        cover = layer_alpha + cover * (1.0 - layer_alpha)
    painted = _to_srgb(colour / np.maximum(cover, ALPHA_EPSILON)[..., None])
    return np.clip(np.rint(painted), 0, 255).astype(np.uint8)


def blur_layered_png(composite_png: bytes, depth_png: bytes, matte_png: bytes,
                     focus_x: float, focus_y: float, f_number: float,
                     backdrop: str | None) -> bytes:
    from . import backdrops

    rgb = np.array(Image.open(io.BytesIO(composite_png)).convert("RGB"))
    height, width = rgb.shape[:2]
    depth = np.array(Image.open(io.BytesIO(depth_png)).convert("L"),
                     dtype=np.float32)
    matte = np.array(Image.open(io.BytesIO(matte_png)).convert("L"),
                     dtype=np.float32) / 255.0
    depth = cv2.resize(depth, (width, height), interpolation=cv2.INTER_LINEAR)
    matte = cv2.resize(matte, (width, height), interpolation=cv2.INTER_LINEAR)
    backdrop_rgb = backdrops.render(backdrop, height, width) if backdrop else None
    out = blur_layered(rgb, depth, matte, focus_x, focus_y, f_number, backdrop_rgb)
    output = io.BytesIO()
    Image.fromarray(out, "RGB").save(output, "PNG")
    return output.getvalue()


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
