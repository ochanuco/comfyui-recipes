"""Decode a ComfyUI PNG and apply Yukari's delivery background and stroke."""

from __future__ import annotations

import io
import json
import string

import cv2
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


def background_mask(pixels: np.ndarray, tolerance: int, *,
                    seed: np.ndarray | None = None) -> np.ndarray:
    """Every backdrop region that reaches the frame edge.

    `seed` defaults to the corner patch's own median; `cut_backdrop` passes
    the delivery's own nominal backdrop colour instead, since it is
    tolerancing against a known constant, not discovering an unknown one.
    """
    if seed is None:
        seed = _corner_seed(pixels)
    candidates = np.abs(pixels - seed).max(axis=2) <= tolerance
    structure = ndimage.generate_binary_structure(2, 1)
    labels, _ = ndimage.label(candidates, structure=structure)
    edges = np.concatenate(
        [labels[0], labels[-1], labels[:, 0], labels[:, -1]])
    reaching = np.unique(edges[edges > 0])
    return np.isin(labels, reaching)


def enclosed_mask(pixels: np.ndarray, found: np.ndarray, tolerance: int, *,
                  minimum_area: int = 16,
                  seed: np.ndarray | None = None) -> np.ndarray:
    """Backdrop the figure encloses, as regions rather than as pixels.

    Interior linework holds pixels within the tolerance of the backdrop, so
    the colour test alone claims specks along every stroke. Only components
    of at least `minimum_area` survive. `seed` is `background_mask`'s own.
    """
    if seed is None:
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


def local_backdrop(pixels: np.ndarray, figure: np.ndarray,
                   band: int) -> np.ndarray:
    """The backdrop colour read locally, from well outside `figure`.

    A normalised Gaussian blur of the pixels the matte puts well outside the
    figure, because a bigger redraw shades the backdrop toward the figure and
    a single global sample would claim that shading as figure.
    """
    outside = ~ndimage.binary_dilation(figure, iterations=band * 2)
    sigma = band * 4
    weight = ndimage.gaussian_filter(outside.astype(float), sigma)
    return np.stack(
        [ndimage.gaussian_filter(pixels[..., c] * outside, sigma)
         for c in range(3)], axis=-1) / np.maximum(weight, 1e-6)[..., None]


def refine_matte(pixels: np.ndarray, figure: np.ndarray, band: int,
                 tolerance: int) -> np.ndarray:
    """Retrace the matte's edge by colour, `band` pixels either side of it.

    The matte model loses the thin strands and the hard threshold then
    cuts what it kept into stubs; the redraw's flat backdrop makes the colour
    test exact there, against `local_backdrop`'s own read of it. Islands
    smaller than band*band are the backdrop's own grain and go.
    """
    if band < 1:
        return figure
    local = local_backdrop(pixels, figure, band)
    edge = (ndimage.binary_dilation(figure, iterations=band)
            & ~ndimage.binary_erosion(figure, iterations=band))
    refined = figure.copy()
    refined[edge] = (np.abs(pixels - local).max(axis=2) > tolerance)[edge]
    labels, count = ndimage.label(refined)
    if not count:
        return refined
    sizes = ndimage.sum(refined, labels, range(1, count + 1))
    return np.isin(labels, 1 + np.nonzero(sizes >= band * band)[0])


def soft_clamped(figure: np.ndarray, soft: np.ndarray) -> np.ndarray:
    """`refine_matte`'s figure, bounded by the matte model's own soft output.

    The colour retrace may only add a pixel the model gave any coverage and
    may not drop one it was sure of: a cast shadow drawn against the figure
    fails the colour test as backdrop, and the figure's own light passages
    pass it as figure.
    """
    return ((figure & (soft > delivery_style.MATTE_SOFT_SUPPORT))
            | (soft > delivery_style.MATTE_SOFT_CERTAIN))


def shadow_cut(pixels: np.ndarray, figure: np.ndarray, soft: np.ndarray,
               band: int) -> np.ndarray:
    """`figure` without the cast shadow it throws on the backdrop.

    The matte model reads the floor shadow under a heel or inside a curl of
    hair as figure. A shadow pixel is grey and moderately darker than the
    local backdrop (`delivery_style.SHADOW_*`), not one the model was certain
    of, and connected to the outside through other shadow pixels, so the
    figure's own greys stay. Islands the cut severs go with it.
    """
    if band < 1:
        return figure
    local = local_backdrop(pixels, figure, band)
    darker = local.mean(axis=2) - pixels.mean(axis=2)
    shadow = ((pixels.max(axis=2) - pixels.min(axis=2) < delivery_style.SHADOW_CHROMA)
              & (darker > delivery_style.SHADOW_DARK_NEAR)
              & (darker < delivery_style.SHADOW_DARK_FAR)
              & (soft <= delivery_style.MATTE_SOFT_CERTAIN))
    outside = ~figure
    reaching = ndimage.binary_propagation(outside, mask=outside | shadow)
    cut = figure & ~(shadow & reaching)
    labels, count = ndimage.label(cut)
    if not count:
        return cut
    sizes = ndimage.sum(cut, labels, range(1, count + 1))
    return np.isin(labels, 1 + np.nonzero(sizes >= band * band)[0])


def enclosed_cut(pixels: np.ndarray, figure: np.ndarray,
                 tolerance: int) -> np.ndarray:
    """`figure` without the key-coloured pockets it encloses.

    The matte model fills the gap a loop of hair closes around the backdrop
    and is certain of it, so neither the edge retrace nor `soft_clamped`
    reaches it. A no-op unless the raw backdrop (`_corner_seed`) is a green
    key (`delivery_style.ENCLOSED_KEY_MIN_GREEN_EXCESS`).
    """
    key = _corner_seed(pixels)
    if key[1] - max(key[0], key[2]) < delivery_style.ENCLOSED_KEY_MIN_GREEN_EXCESS:
        key = _pocket_key(pixels, figure)
        if key is None:
            return figure
    return figure & ~enclosed_mask(pixels, ~figure, tolerance, seed=key)


def _pocket_key(pixels: np.ndarray, region: np.ndarray) -> np.ndarray | None:
    """The green key found inside `region` when the corners are not it.

    A drawn frame line closes the raw's green off from the white outside it,
    so the corners read as a white backdrop while the matte keeps the whole
    green pocket as figure. The key is the median of the region's green
    pixels, once there are `ENCLOSED_POCKET_MIN_AREA` of them.
    """
    excess = pixels[..., 1] - np.maximum(pixels[..., 0], pixels[..., 2])
    inside = region & (excess >= delivery_style.ENCLOSED_KEY_MIN_GREEN_EXCESS)
    if int(inside.sum()) < delivery_style.ENCLOSED_POCKET_MIN_AREA:
        return None
    return np.median(pixels[inside], axis=0)


def pocket_window(pixels: np.ndarray, figure: np.ndarray,
                  tolerance: int) -> np.ndarray | None:
    """Where the backdrop goes when the key came from a pocket, else None.

    Inside the frame line the raw's green is the other side of the picture
    and takes the backdrop; the white beyond the line is left as it is. The
    window is the key-coloured field outside the cut figure, in regions.
    `figure` is the silhouette after `enclosed_cut`.
    """
    key = _corner_seed(pixels)
    if key[1] - max(key[0], key[2]) >= delivery_style.ENCLOSED_KEY_MIN_GREEN_EXCESS:
        return None
    key = _pocket_key(pixels, ~figure)
    if key is None:
        return None
    return enclosed_mask(pixels, figure, tolerance, seed=key)


def keyed_coverage(pixels: np.ndarray, figure: np.ndarray, local: np.ndarray,
                   band: int, tolerance: int) -> np.ndarray:
    """Figure coverage as a ramp on the figure's outermost pixel ring.

    1 inside the ring-eroded figure, 0 outside the figure entirely; the ring
    itself ramps by each pixel's own colour distance from the local
    backdrop, reaching 1 at `delivery_style.KEY_EDGE_RAMP` tolerances out.
    """
    if band < 1:
        return figure.astype(float)
    inside = ndimage.binary_erosion(
        figure, iterations=delivery_style.KEY_EDGE_RING_PX)
    distance = np.abs(pixels - local).max(axis=2)
    ramp = np.clip(distance / (delivery_style.KEY_EDGE_RAMP * tolerance), 0.0, 1.0)
    coverage = np.where(inside, 1.0, ramp)
    coverage[~figure] = 0.0
    return coverage


def unpremultiply(pixels: np.ndarray, local: np.ndarray,
                  coverage: np.ndarray) -> np.ndarray:
    """Solve for the figure's own colour under a fractional edge coverage.

    Where 0 < coverage < 1 the pixel is figure blended into the local
    backdrop at that ratio; dividing the blend's departure from the backdrop
    by coverage recovers the figure colour the blend was mixed from.
    """
    soft = (coverage > 0) & (coverage < 1)
    safe = np.where(soft, coverage, 1.0)[..., None]
    solved = np.clip(local + (pixels - local) / safe, 0, 255)
    return np.where(soft[..., None], solved, pixels)


def _key_channels(key: np.ndarray) -> tuple[int, list[int]]:
    """`key`'s dominant channel index and the other two, in channel order."""
    dominant = int(np.argmax(key))
    return dominant, [channel for channel in range(3) if channel != dominant]


def _key_excess(key: np.ndarray) -> float:
    dominant, others = _key_channels(key)
    return float(key[dominant] - max(key[others[0]], key[others[1]]))


def figure_rim(figure: np.ndarray, band: int) -> np.ndarray:
    """`figure`'s outermost `band` pixels, the only place the key can spill.

    A drawn figure has no bounced light, so the key's tint exists only where
    the edge blends into the backdrop. Despilling past that takes the key's
    chroma out of the figure's own colours: a yellow-green key turns the
    skin pink.
    """
    if band < 1:
        return figure
    return figure & ~ndimage.binary_erosion(figure, iterations=band)


def despill(pixels: np.ndarray, region: np.ndarray, key: np.ndarray) -> np.ndarray:
    """Remove the key colour's own chroma from every `region` pixel.

    A no-op unless `key` is a chromatic key: its dominant channel has to
    clear the larger of the other two by `delivery_style.KEY_DESPILL_MIN_EXCESS`.
    Where it does, each region pixel's chroma (its departure from its own
    grey) is projected onto the key's chroma direction and the positive part
    subtracted, so a teal key leaves neither green nor cyan behind; a single
    channel cap only strips the dominant channel and leaves the rest of the
    key's tint in place.
    """
    if _key_excess(key) < delivery_style.KEY_DESPILL_MIN_EXCESS:
        return pixels
    direction = key - key.mean()
    direction = direction / np.linalg.norm(direction)
    chroma = pixels - pixels.mean(axis=2, keepdims=True)
    along = np.clip((chroma * direction).sum(axis=2), 0.0, None)
    cleared = np.clip(pixels - along[..., None] * direction, 0, 255)
    return np.where(region[..., None], cleared, pixels)


def stroke_alpha(mask: np.ndarray, gap: float, width: float,
                 edge_smooth: float) -> np.ndarray:
    """Coverage of the band, gap..gap+width pixels out into the backdrop.

    `distance_transform_edt` on the backdrop gives each backdrop pixel its
    distance to the nearest figure pixel, so the first ring out is 1. The
    ramps read that distance blurred by `edge_smooth`, not the raw one: a
    ramp follows the shape of the boundary it measures from, so a jagged
    `mask` needs the field rounded before it is ramped, not just softened.
    Both edges are ramped over one pixel; the inner ramp does nothing at gap
    0 and keeps the stroke from stepping when it is pushed away from the
    figure.
    """
    distance = ndimage.distance_transform_edt(mask)
    smoothed = ndimage.gaussian_filter(distance, edge_smooth)
    outer = np.clip(gap + width + 0.5 - smoothed, 0.0, 1.0)
    inner = np.clip(smoothed - gap + 0.5, 0.0, 1.0)
    alpha = outer * inner
    alpha[~mask] = 0.0
    return alpha


def directional_stroke_alpha(mask: np.ndarray, gap: float, w_min: float,
                             w_max: float, light: tuple[float, float],
                             smooth: float, edge_smooth: float) -> np.ndarray:
    """Coverage of a purple band whose width follows the outline's own normal.

    Thin where the outward normal faces `light` (image coordinates, x right,
    y down), thick on the opposite side. The normal is read from the
    gradient of a Gaussian-blurred distance field rather than the raw one, so
    a hair strand or a notch does not flip the width pixel to pixel. The edge
    ramps take a separate, much smaller `edge_smooth` blur: `smooth` is sized
    to ignore real shape, which is exactly what an edge must follow.
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
    smoothed = ndimage.gaussian_filter(distance, edge_smooth)
    outer = np.clip(gap + width + 0.5 - smoothed, 0.0, 1.0)
    inner = np.clip(smoothed - gap + 0.5, 0.0, 1.0)
    alpha = outer * inner
    alpha[~mask] = 0.0
    return alpha


def _polygon_coverage(region: np.ndarray, eps_pct: float,
                      supersample: int = 2) -> np.ndarray:
    """Coverage of `region`'s outer shape, polygon-simplified.

    Supersamples `supersample`x, straightens each contour with
    `cv2.approxPolyDP` at `eps_pct` percent of the longest side, fills the
    outer contours and clears the holes, then area-downsamples back to 1x --
    the shape-simplifying counterpart to `STROKE_EDGE_SMOOTH`'s ramp blur.
    Holes (background the shape encloses, e.g. between an arm and the body)
    survive because only contours with a parent in the hierarchy are cleared.
    """
    height, width = region.shape
    scaled = cv2.resize(region.astype(np.uint8) * 255,
                        (width * supersample, height * supersample),
                        interpolation=cv2.INTER_LINEAR)
    contours, hierarchy = cv2.findContours(
        (scaled > 127).astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    canvas = np.zeros_like(scaled)
    if contours:
        eps = max(height, width) * supersample * eps_pct / 100
        polygons = [cv2.approxPolyDP(contour, eps, True) for contour in contours]
        for index, polygon in enumerate(polygons):
            if hierarchy[0][index][3] == -1:
                cv2.fillPoly(canvas, [polygon], 255, lineType=cv2.LINE_AA)
        for index, polygon in enumerate(polygons):
            if hierarchy[0][index][3] != -1:
                cv2.fillPoly(canvas, [polygon], 0, lineType=cv2.LINE_AA)
    return cv2.resize(canvas, (width, height),
                      interpolation=cv2.INTER_AREA).astype(float) / 255


def _directional_region(mask: np.ndarray, w_min: float, w_max: float,
                        light: tuple[float, float], smooth: float) -> np.ndarray:
    """The region grown out from `mask`, its width shaded by `light`.

    Same width field as `directional_stroke_alpha` -- thin where the
    outline's own outward normal faces `light`, thick opposite -- but
    thresholded to a hard region instead of ramped: `_polygon_coverage` is
    the edge treatment for this region, not a gaussian ramp.
    """
    distance = ndimage.distance_transform_edt(~mask)
    field = ndimage.gaussian_filter(distance, smooth)
    ny, nx = np.gradient(field)
    norm = np.hypot(nx, ny)
    norm[norm == 0] = 1.0
    facing = (nx / norm) * light[0] + (ny / norm) * light[1]
    k = (1.0 - facing) / 2.0
    k = k * k * (3 - 2 * k)
    width = w_min + (w_max - w_min) * k
    width = ndimage.gaussian_filter(width, smooth / 2)
    return distance <= width


def keep_scene(data: bytes, matte: bytes) -> tuple[bytes, str]:
    """Deliver the redraw as drawn, background included."""
    return data, "scene"


def _band_widths(height: int, width: int) -> tuple[float, float]:
    white_w = max(height, width) * delivery_style.WHITE_WIDTH_PCT / 100
    purple_w = white_w * delivery_style.STROKE_WIDTH_BAND
    return white_w, purple_w


def band_alphas(figure: np.ndarray, light: str | None = None,
                eps_pct: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Coverage of the white band and the purple band outside `figure`.

    `eps_pct` (default `delivery_style.STROKE_CUT_EPS_PCT`) is the
    Douglas-Peucker epsilon, as a percent of the longest side, each band's
    outer outline is simplified to -- straight, angular segments instead of
    the smooth ramp, for a hand-cut rather than die-cut edge. At
    `eps_pct <= 0` this is exactly the old smooth geometry: the 2x
    `Image.NEAREST` upscale adds no information -- the boundary is the
    source pixel grid's staircase, just bigger -- so the bands are ramped
    from a distance field blurred by `delivery_style.STROKE_EDGE_SMOOTH` and
    averaged back down, rounding that staircase off instead of merely
    softening it. `light`, one of `delivery_style.STROKE_LIGHTS`' keys,
    shades the purple band's width by direction instead of drawing it at the
    uniform width; the white band is never shaded.
    """
    height, width = figure.shape
    white_w, purple_w = _band_widths(height, width)
    light_vec = None
    if light is not None:
        if light not in delivery_style.STROKE_LIGHTS:
            valid = ", ".join(repr(key) for key in sorted(delivery_style.STROKE_LIGHTS))
            raise ValueError(f"light must be null or one of {valid}, got {light!r}")
        light_vec = delivery_style.STROKE_LIGHTS[light]

    eps = delivery_style.STROKE_CUT_EPS_PCT if eps_pct is None else eps_pct
    if eps <= 0:
        bg2 = ~(np.array(Image.fromarray(figure)
                         .resize((width * 2, height * 2), Image.NEAREST)))
        white_a = down2(stroke_alpha(bg2, 0.0, white_w * 2,
                                     delivery_style.STROKE_EDGE_SMOOTH))
        if light_vec is None:
            purple_a = down2(stroke_alpha(bg2, white_w * 2, purple_w * 2,
                                          delivery_style.STROKE_EDGE_SMOOTH))
        else:
            purple_a = down2(directional_stroke_alpha(
                bg2, white_w * 2,
                purple_w * 2 * delivery_style.STROKE_LIGHT_THIN,
                purple_w * 2 * delivery_style.STROKE_LIGHT_THICK,
                light_vec, delivery_style.STROKE_LIGHT_SMOOTH * purple_w * 2,
                delivery_style.STROKE_EDGE_SMOOTH))
        return white_a, purple_a

    distance = ndimage.distance_transform_edt(~figure)
    white_a = _polygon_coverage(distance <= white_w, eps)
    white_mask = white_a >= 0.5
    if light_vec is None:
        purple_region = ndimage.distance_transform_edt(~white_mask) <= purple_w
    else:
        purple_region = _directional_region(
            white_mask, purple_w * delivery_style.STROKE_LIGHT_THIN,
            purple_w * delivery_style.STROKE_LIGHT_THICK, light_vec,
            delivery_style.STROKE_LIGHT_SMOOTH * purple_w)
    purple_a = _polygon_coverage(purple_region, eps)
    white_a = np.where(figure, 0.0, white_a)
    purple_a = np.where(figure, 0.0, purple_a)
    return white_a, purple_a


def outside_mask(figure: np.ndarray, light: str | None = None,
                 eps_pct: float | None = None) -> np.ndarray:
    """Pixels outside the purple band's own outer edge.

    Not `figure`, not the white band, not the purple band -- the same
    geometry `band_alphas` draws, so a hole the bands still reach (an arm
    against the body, narrower than the two bands together) stays inside
    while backdrop beyond the purple band's outer edge comes back `True`.
    """
    white_a, purple_a = band_alphas(figure, light, eps_pct)
    return ~figure & (white_a < 0.5) & (purple_a < 0.5)


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


def _cut_tag_suffix() -> str:
    """Marks a delivery's tag with the rim eps it was cut at, if any."""
    eps = delivery_style.STROKE_CUT_EPS_PCT
    return f"-cut{eps:g}" if eps > 0 else ""


def clean_background(data: bytes, matte: bytes, light: str | None = None,
                     backdrop: str | None = None) -> tuple[bytes, str]:
    """Frame the figure the matte cuts out, in the delivery's own colours.

    The matte is the authority on the silhouette. Colour cannot be: repin
    moves the figure's own colours, and the pale hair lands inside the
    backdrop's tolerance once it has. The refined matte is clamped to the
    soft matte's support (`soft_clamped`) and loses the cast shadow the
    model kept (`shadow_cut`). The matte's own edge band gets a
    soft, colour-distance coverage instead of a binary one, its figure
    pixels un-premultiplied against the local backdrop; a chromatic raw
    backdrop (a green screen) also gets despilled from the figure's rim.
    """
    px = np.array(Image.open(io.BytesIO(data)).convert("RGB")).astype(float)
    soft = np.array(Image.open(io.BytesIO(matte)).convert("L"))
    height, width = px.shape[:2]
    band = int(max(height, width) * delivery_style.MATTE_EDGE_BAND_PCT / 100)
    tolerance = delivery_style.MATTE_EDGE_TOLERANCE
    figure = soft_clamped(refine_matte(px, soft > 127, band, tolerance), soft)
    figure = shadow_cut(px, figure, soft, band)
    figure = enclosed_cut(px, figure, tolerance)
    local = local_backdrop(px, figure, band)
    coverage = keyed_coverage(px, figure, local, band, tolerance)
    key = _corner_seed(px)
    window = pocket_window(px, figure, tolerance)
    px = despill(unpremultiply(px, local, coverage),
                 figure_rim(figure, band), key)
    backdrop_rgb = backdrops.render(backdrop, height, width)
    if window is not None:
        backdrop_rgb = np.where(window[..., None], backdrop_rgb, key)
    composite = sticker(px, figure, coverage, backdrop_rgb, light)
    white_w, purple_w = _band_widths(height, width)

    keyed = _key_excess(key) >= delivery_style.KEY_DESPILL_MIN_EXCESS
    output = io.BytesIO()
    Image.fromarray(np.clip(composite, 0, 255).astype(np.uint8)).save(output, "PNG")
    tag = (f"clean-w{white_w:.0f}-p{purple_w:.0f}"
          + _backdrop_tag_suffix(backdrop) + _cut_tag_suffix()
          + ("-key" if keyed else ""))
    return output.getvalue(), tag + (f"-light-{light}" if light else "")


# Below this alpha, the band-less compose drops a pixel outright: a
# layerdiffuse raw's own low-alpha haze skirt reads near-white for tens of
# pixels past the figure, and composited at its raw alpha/255 it bakes in as
# a pale glow the redraw then treats as picture. Above HAZE_ALPHA_CEIL a
# pixel keeps its own coverage unchanged; between the two it ramps linearly,
# so a real antialiased edge is thinned rather than cut.
HAZE_ALPHA_FLOOR = 32
HAZE_ALPHA_CEIL = 64


def _dehaze_coverage(alpha: np.ndarray) -> np.ndarray:
    raw = alpha.astype(float) / 255.0
    ramp = np.clip((alpha.astype(float) - HAZE_ALPHA_FLOOR)
                   / (HAZE_ALPHA_CEIL - HAZE_ALPHA_FLOOR), 0.0, 1.0)
    return raw * ramp


def compose(data: bytes, backdrop: str | None = None,
           light: str | None = None, bands: bool = True) -> tuple[bytes, str]:
    """Composite an RGBA figure onto a flat backdrop, unrefined.

    The alpha is a layerdiffuse render's own -- islands and holes are left
    as drawn, unlike `clean_background`'s birefnet matte, which `refine_matte`
    retraces because the model loses strands `refine_matte` was written to
    put back. `bands=False` skips the white/purple ring and plain
    alpha-composites the figure onto the backdrop instead: the redraw that
    follows moves the silhouette, so the transparent finalize path draws its
    own band afterward, from the redrawn pixels' own matte. That path leaves
    `backdrop` unset -- `delivery_style.BACKDROP` is the only flat colour this
    module already owns, so the band-less compose reads it too rather than
    adding a second one.
    """
    rgba = Image.open(io.BytesIO(data)).convert("RGBA")
    px = np.array(rgba)[..., :3].astype(float)
    alpha = np.array(rgba)[..., 3]
    coverage = alpha.astype(float) / 255.0
    height, width = px.shape[:2]
    backdrop_rgb = backdrops.render(backdrop, height, width)
    if bands:
        figure = alpha > 127
        composite = sticker(px, figure, coverage, backdrop_rgb, light)
        white_w, purple_w = _band_widths(height, width)
        tag = (f"compose-w{white_w:.0f}-p{purple_w:.0f}"
              + _backdrop_tag_suffix(backdrop) + _cut_tag_suffix())
    else:
        dehazed = _dehaze_coverage(alpha)
        composite = dehazed[..., None] * px + (1.0 - dehazed[..., None]) * backdrop_rgb
        tag = "compose-flat" + _backdrop_tag_suffix(backdrop)

    output = io.BytesIO()
    Image.fromarray(np.clip(composite, 0, 255).astype(np.uint8)).save(output, "PNG")
    return output.getvalue(), tag + (f"-light-{light}" if light else "")


def compose_outside_mask(data: bytes, light: str | None = None) -> bytes:
    """`outside_mask` for a `compose`'s own RGBA input, PNG-encoded (mode L).

    Reads its figure the same way `compose` does, off the same alpha and at
    the same scale, so `YukariCompose`'s MASK output carries exactly the
    geometry its own IMAGE output drew the bands from -- the redraw that
    follows moves both to a different scale together.
    """
    rgba = Image.open(io.BytesIO(data)).convert("RGBA")
    figure = np.array(rgba)[..., 3] > 127
    output = io.BytesIO()
    Image.fromarray(outside_mask(figure, light).astype(np.uint8) * 255,
                    "L").save(output, "PNG")
    return output.getvalue()


def transparent(data: bytes, matte: bytes,
                light: str | None = None) -> tuple[bytes, str]:
    """Cut the figure out and frame it with the sticker bands on alpha 0.

    The refined matte, clamped to the soft matte's support and without the
    cast shadow, is the authority on the silhouette, same as
    `clean_background`. It gets a sub-pixel ramp
    of its own so the strands it retraced keep their coverage, and the soft
    matte only adds coverage inside the 1-px ring around it. The white and
    purple bands are the same as `clean_background`'s; outside them the
    alpha is 0 instead of the backdrop.
    """
    px = np.array(Image.open(io.BytesIO(data)).convert("RGB")).astype(np.uint8)
    soft = np.array(Image.open(io.BytesIO(matte)).convert("L"))
    height, width = px.shape[:2]
    band = int(max(height, width) * delivery_style.MATTE_EDGE_BAND_PCT / 100)
    figure = refine_matte(
        px.astype(float), soft > 127, band, delivery_style.MATTE_EDGE_TOLERANCE)
    figure = shadow_cut(px.astype(float), soft_clamped(figure, soft), soft, band)
    opened = enclosed_cut(
        px.astype(float), figure, delivery_style.MATTE_EDGE_TOLERANCE)
    soft = np.where(figure & ~opened, 0, soft)
    figure = opened

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
    tag = f"transparent-w{white_w:.0f}-p{purple_w:.0f}" + _cut_tag_suffix()
    return output.getvalue(), tag + (f"-light-{light}" if light else "")


def cut_backdrop(data: bytes, outside_mask: bytes,
                 backdrop: str | None = None) -> tuple[bytes, bytes, str]:
    """Turn a redrawn picture's flat backdrop into transparency.

    A compose-then-redraw bakes the white band and purple rim into the
    picture before the redraw runs, so nothing downstream cuts a silhouette
    from a matte model -- the backdrop itself is the only thing left to cut,
    by colour, against `backdrops.render`'s own flat fill. Colour alone
    cannot bound that cut: the redraw retints and textures the flat fill, so
    the tolerance against it (`delivery_style.CUT_BACKDROP_TOLERANCE`) is
    generous, and the figure's own light passages (pale hair, a pale prop)
    sit inside it too. `outside_mask` -- `compose_outside_mask`'s own output,
    at the compose's own scale -- bounds the colour test instead: resized to
    this picture and dilated by `delivery_style.CUT_BACKDROP_MARGIN` (a
    share of the white band's own width, absorbing the redraw's edge drift),
    a pixel outside it is kept whatever colour the redraw gave it. A pattern
    backdrop has no single colour to tolerance against. The kept edge is
    softened by one pixel so the rim's outer boundary is not aliased.
    """
    if backdrop in backdrops.PATTERNS:
        raise ValueError(
            f"cut_backdrop needs a flat colour, got pattern {backdrop!r}")
    px = np.array(Image.open(io.BytesIO(data)).convert("RGB")).astype(float)
    height, width = px.shape[:2]
    outside_img = Image.open(io.BytesIO(outside_mask)).convert("L")
    outside = np.array(
        outside_img.resize((width, height), Image.BILINEAR)) > 127
    margin = round(_band_widths(height, width)[0] * delivery_style.CUT_BACKDROP_MARGIN)
    if margin > 0:
        outside = ndimage.binary_dilation(outside, iterations=margin)
    seed = backdrops.render(backdrop, height, width)[0, 0]
    tolerance = delivery_style.CUT_BACKDROP_TOLERANCE
    cut = outside & (np.abs(px - seed).max(axis=2) <= tolerance)
    coverage = np.clip(
        ndimage.gaussian_filter((~cut).astype(float), 0.6), 0.0, 1.0)

    rgb = np.clip(px, 0, 255).astype(np.uint8)
    alpha = np.clip(coverage * 255, 0, 255).astype(np.uint8)
    rgba = np.dstack([rgb, alpha])
    output = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(output, "PNG")
    matte_output = io.BytesIO()
    Image.fromarray(alpha, "L").save(matte_output, "PNG")
    return output.getvalue(), matte_output.getvalue(), f"cutbg-t{tolerance}"
