"""Decode a ComfyUI PNG and apply Yukari's delivery background and stroke."""

from __future__ import annotations

import io
import json
import string

import numpy as np
from PIL import Image
from scipy import ndimage

from ...domain.yukari import delivery_style
from . import backdrops


def image_size(data: bytes) -> tuple[int, int]:
    return Image.open(io.BytesIO(data)).size


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


def directional_stroke_alpha(mask: np.ndarray, gap: float, w_min: float,
                             w_max: float, light: tuple[float, float],
                             smooth: float) -> np.ndarray:
    """Coverage of a purple band whose width follows the outline's own normal.

    Thin where the outward normal faces `light` (image coordinates, x right,
    y down), thick on the opposite side. The normal is read from the
    gradient of a Gaussian-blurred distance field rather than the raw one, so
    a hair strand or a notch does not flip the width pixel to pixel.
    """
    distance = ndimage.distance_transform_edt(mask)
    field = ndimage.gaussian_filter(distance, smooth)
    ny, nx = np.gradient(field)
    norm = np.hypot(nx, ny)
    norm[norm == 0] = 1.0
    facing = (nx / norm) * light[0] + (ny / norm) * light[1]
    k = (1.0 - facing) / 2.0
    k = k * k * (3 - 2 * k)
    width = w_min + (w_max - w_min) * k
    width = ndimage.gaussian_filter(width, smooth / 2)
    outer = np.clip(gap + width + 0.5 - distance, 0.0, 1.0)
    inner = np.clip(distance - gap + 0.5, 0.0, 1.0)
    alpha = outer * inner
    alpha[~mask] = 0.0
    return alpha


def keep_scene(data: bytes, matte: bytes) -> tuple[bytes, str]:
    """Deliver the redraw as drawn, background included."""
    return data, "scene"


def _band_widths(height: int, width: int) -> tuple[float, float]:
    white_w = max(height, width) * delivery_style.WHITE_WIDTH_PCT / 100
    purple_w = white_w * delivery_style.STROKE_WIDTH_BAND
    return white_w, purple_w


def band_alphas(figure: np.ndarray,
                light: str | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Coverage of the white band and the purple band outside `figure`.

    Drawn from a hard boundary at 2x and averaged down, so the edge of each
    band is a half-pixel gradient rather than a staircase. `light`, one of
    `delivery_style.STROKE_LIGHTS`' keys, shades the purple band's width by
    direction instead of drawing it at the uniform width; the white band is
    never shaded.
    """
    height, width = figure.shape
    bg2 = ~(np.array(Image.fromarray(figure)
                     .resize((width * 2, height * 2), Image.NEAREST)))
    white_w, purple_w = _band_widths(height, width)
    white_a = down2(stroke_alpha(bg2, 0.0, white_w * 2))
    if light is None:
        purple_a = down2(stroke_alpha(bg2, white_w * 2, purple_w * 2))
    else:
        if light not in delivery_style.STROKE_LIGHTS:
            valid = ", ".join(repr(key) for key in sorted(delivery_style.STROKE_LIGHTS))
            raise ValueError(f"light must be null or one of {valid}, got {light!r}")
        purple_a = down2(directional_stroke_alpha(
            bg2, white_w * 2,
            purple_w * 2 * delivery_style.STROKE_LIGHT_THIN,
            purple_w * 2 * delivery_style.STROKE_LIGHT_THICK,
            delivery_style.STROKE_LIGHTS[light],
            delivery_style.STROKE_LIGHT_SMOOTH * purple_w * 2))
    return white_a, purple_a


def _bands_over(white_a: np.ndarray, purple_a: np.ndarray,
                flat: np.ndarray) -> np.ndarray:
    white_rgb = np.array([255.0, 255.0, 255.0])
    purple_rgb = np.array(parse_color(delivery_style.STROKE), dtype=float)
    bands = flat + purple_a[..., None] * (purple_rgb - flat)
    return bands + white_a[..., None] * (white_rgb - bands)


def sticker(px: np.ndarray, figure: np.ndarray, coverage: np.ndarray,
           backdrop_rgb, light: str | None = None) -> np.ndarray:
    """Frame `figure` on `backdrop_rgb`, white band then purple band outside it.

    `coverage` is the figure's own per-pixel alpha in 0..1; the composite is
    coverage * px + (1 - coverage) * (the stroke bands over the backdrop).
    `figure` alone decides where the bands sit -- coverage may be soft at the
    edge the bands are drawn from a hard boundary.
    """
    white_a, purple_a = band_alphas(figure, light)
    # backdrop_rgb may be a 3-vector or a full (H, W, 3) pattern; either
    # broadcasts onto px.shape unchanged.
    flat = np.broadcast_to(np.array(backdrop_rgb, dtype=float), px.shape).copy()
    bands = _bands_over(white_a, purple_a, flat)
    return bands + coverage[..., None] * (px - bands)


def _backdrop_tag_suffix(backdrop: str | None) -> str:
    if not backdrop:
        return ""
    name = backdrop if backdrop in backdrops.PATTERNS else backdrop.lstrip("#")
    return f"-bg-{name}"


def clean_background(data: bytes, matte: bytes, light: str | None = None,
                     backdrop: str | None = None) -> tuple[bytes, str]:
    """Frame the figure the matte cuts out, in the delivery's own colours.

    The matte is the authority on the silhouette. Colour cannot be: repin
    moves the figure's own colours, and the pale hair lands inside the
    backdrop's tolerance once it has.
    """
    px = np.array(Image.open(io.BytesIO(data)).convert("RGB")).astype(float)
    figure = np.array(Image.open(io.BytesIO(matte)).convert("L")) > 127
    height, width = px.shape[:2]
    figure = refine_matte(
        px, figure,
        int(max(height, width) * delivery_style.MATTE_EDGE_BAND_PCT / 100),
        delivery_style.MATTE_EDGE_TOLERANCE)
    backdrop_rgb = backdrops.render(backdrop, height, width)
    composite = sticker(px, figure, figure.astype(float), backdrop_rgb, light)
    white_w, purple_w = _band_widths(height, width)

    output = io.BytesIO()
    Image.fromarray(np.clip(composite, 0, 255).astype(np.uint8)).save(output, "PNG")
    tag = f"clean-w{white_w:.0f}-p{purple_w:.0f}" + _backdrop_tag_suffix(backdrop)
    return output.getvalue(), tag + (f"-light-{light}" if light else "")


def compose(data: bytes, backdrop: str | None = None,
           light: str | None = None) -> tuple[bytes, str]:
    """Composite an RGBA figure onto the sticker backdrop, unrefined.

    The alpha is a layerdiffuse render's own -- islands and holes are left
    as drawn, unlike `clean_background`'s birefnet matte, which `refine_matte`
    retraces because the model loses strands `refine_matte` was written to
    put back.
    """
    rgba = Image.open(io.BytesIO(data)).convert("RGBA")
    px = np.array(rgba)[..., :3].astype(float)
    alpha = np.array(rgba)[..., 3]
    figure = alpha > 127
    coverage = alpha.astype(float) / 255.0
    height, width = px.shape[:2]
    backdrop_rgb = backdrops.render(backdrop, height, width)
    composite = sticker(px, figure, coverage, backdrop_rgb, light)
    white_w, purple_w = _band_widths(height, width)

    output = io.BytesIO()
    Image.fromarray(np.clip(composite, 0, 255).astype(np.uint8)).save(output, "PNG")
    tag = f"compose-w{white_w:.0f}-p{purple_w:.0f}" + _backdrop_tag_suffix(backdrop)
    return output.getvalue(), tag + (f"-light-{light}" if light else "")


def transparent(data: bytes, matte: bytes,
                light: str | None = None) -> tuple[bytes, str]:
    """Cut the figure out and frame it with the sticker bands on alpha 0.

    The refined matte is the authority on the silhouette, same as
    `clean_background`, but clamped to the soft birefnet matte's support:
    the colour retrace on its own claims the backdrop's shading as figure
    and cuts holes in the figure's light passages. It gets a sub-pixel ramp
    of its own so the strands it retraced keep their coverage, and the soft
    matte only adds coverage inside the 1-px ring around it. The white and
    purple bands are the same as `clean_background`'s; outside them the
    alpha is 0 instead of the backdrop.
    """
    px = np.array(Image.open(io.BytesIO(data)).convert("RGB")).astype(np.uint8)
    soft = np.array(Image.open(io.BytesIO(matte)).convert("L"))
    height, width = px.shape[:2]
    figure = refine_matte(
        px.astype(float), soft > 127,
        int(max(height, width) * delivery_style.MATTE_EDGE_BAND_PCT / 100),
        delivery_style.MATTE_EDGE_TOLERANCE)
    figure = ((figure & (soft > delivery_style.MATTE_SOFT_SUPPORT))
              | (soft > delivery_style.MATTE_SOFT_CERTAIN))

    halo = ndimage.binary_dilation(figure, iterations=1)
    ramp = ndimage.gaussian_filter(figure.astype(float), 0.6)
    coverage = np.maximum(ramp, soft / 255.0)
    coverage[~halo] = 0.0
    coverage[ndimage.binary_erosion(figure, iterations=1)] = 1.0

    white_a, purple_a = band_alphas(figure, light)
    band_alpha = np.clip(white_a + purple_a, 0.0, 1.0)
    band_rgb = _bands_over(white_a, purple_a, np.zeros(px.shape))
    band_rgb = band_rgb / np.maximum(band_alpha, 1e-6)[..., None]
    # Figure over bands, straight alpha out.
    alpha = coverage + (1.0 - coverage) * band_alpha
    premultiplied = (coverage[..., None] * px
                     + ((1.0 - coverage) * band_alpha)[..., None] * band_rgb)
    rgb = premultiplied / np.maximum(alpha, 1e-6)[..., None]
    rgb[alpha <= 0.0] = 0.0

    rgba = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8),
                      np.clip(alpha * 255, 0, 255).astype(np.uint8)])
    white_w, purple_w = _band_widths(height, width)
    output = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(output, "PNG")
    tag = f"transparent-w{white_w:.0f}-p{purple_w:.0f}"
    return output.getvalue(), tag + (f"-light-{light}" if light else "")
