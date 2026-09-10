from __future__ import annotations

import io
import json
import re
import unittest

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from comfyui_recipes.domain.yukari import delivery_style
from comfyui_recipes.infrastructure.imaging.palette import repin_skin_png
from comfyui_recipes.infrastructure.imaging.delivery import (
    background_mask,
    band_alphas,
    clean_background,
    compose,
    down2,
    graph_from_png,
    keep_scene,
    parse_color,
    refine_matte,
    stroke_alpha,
    transparent,
)


def png(pixels: np.ndarray, prompt: str | None = None) -> bytes:
    output = io.BytesIO()
    metadata = PngInfo()
    if prompt is not None:
        metadata.add_text("prompt", prompt)
    Image.fromarray(pixels.astype(np.uint8)).save(
        output, "PNG", pnginfo=metadata)
    return output.getvalue()


def matte(shape, box):
    """A hard matte with one rectangular figure, as the worker would send it."""
    mask = np.zeros(shape, dtype=np.uint8)
    top, bottom, left, right = box
    mask[top:bottom, left:right] = 255
    return png(mask)


class DeliveryTest(unittest.TestCase):
    def test_graph_metadata_validation(self):
        pixels = np.zeros((2, 2, 3), dtype=np.uint8)
        with self.assertRaisesRegex(SystemExit, "no ComfyUI prompt"):
            graph_from_png(png(pixels))
        with self.assertRaisesRegex(SystemExit, "invalid ComfyUI prompt"):
            graph_from_png(png(pixels, "not-json"))
        self.assertEqual(graph_from_png(png(pixels, json.dumps({"3": {}}))),
                         {"3": {}})

    def test_parse_color_rejects_non_hexadecimal_input(self):
        self.assertEqual(parse_color("#c7e5e9"), (199, 229, 233))
        with self.assertRaisesRegex(SystemExit, "6-digit hex"):
            parse_color("gggggg")

    def test_background_mask_claims_every_region_reaching_the_frame(self):
        # A figure that crosses the frame cuts the backdrop into pieces. Each
        # piece that still reaches an edge is backdrop; keeping only the
        # corner's piece is what left half a head crop at the render's own
        # colour, with the stroke drawn along the seam between the two halves.
        pixels = np.zeros((12, 12, 3), dtype=int)
        pixels[:, 5:7] = 255
        mask = background_mask(pixels, 0)
        self.assertEqual(int(mask.sum()), 12 * 12 - 24)
        self.assertTrue(mask[0, 0])
        self.assertTrue(mask[0, 11])
        self.assertFalse(mask[0, 5])

    def test_background_mask_leaves_regions_walled_off_from_the_frame(self):
        # Backdrop enclosed by the figure is `enclosed_mask`'s job, on its own
        # much tighter tolerance; the flood must not reach it.
        pixels = np.zeros((12, 12, 3), dtype=int)
        pixels[4:9, 4:9] = 255
        pixels[6, 6] = 0
        mask = background_mask(pixels, 0)
        self.assertTrue(mask[0, 0])
        self.assertFalse(mask[6, 6])

    def test_refine_matte_retraces_the_edge_by_colour_and_drops_grain(self):
        pixels = np.full((40, 40, 3), (58, 67, 81), dtype=int)
        pixels[10:30, 10:30] = (190, 170, 220)
        # A strand the matte lost, a strand the matte cut short, and a
        # backdrop speck the matte never had.
        pixels[20, 30:33] = (190, 170, 220)
        pixels[24, 8:10] = (190, 170, 220)
        pixels[2, 2] = (200, 200, 200)
        figure = np.zeros((40, 40), dtype=bool)
        figure[10:30, 10:30] = True
        figure[24, 9] = True
        refined = refine_matte(pixels, figure, 3, 20)
        self.assertTrue(refined[20, 30:33].all())
        self.assertTrue(refined[24, 8:10].all())
        self.assertFalse(refined[2, 2])
        self.assertTrue(refined[10:30, 10:30].all())
        self.assertFalse(refined[0:5, 10:40].any())

    def test_refine_matte_reads_the_backdrop_locally_under_a_gradient(self):
        # The backdrop darkens by 40 toward the figure: a single corner
        # reference would claim the shaded ring as figure.
        ramp = np.linspace(0, 40, 60)
        pixels = np.zeros((60, 60, 3), dtype=int) + (58, 67, 81)
        pixels = pixels + ramp[None, :, None].astype(int)
        pixels[20:40, 20:40] = (190, 170, 220)
        figure = np.zeros((60, 60), dtype=bool)
        figure[20:40, 20:40] = True
        refined = refine_matte(pixels, figure, 3, 20)
        self.assertTrue((refined == figure).all())

    def test_refine_matte_is_identity_below_one_pixel_of_band(self):
        pixels = np.zeros((8, 8, 3), dtype=int)
        figure = np.zeros((8, 8), dtype=bool)
        figure[2:6, 2:6] = True
        self.assertIs(refine_matte(pixels, figure, 0, 20), figure)

    def test_keep_scene_returns_the_redraw_untouched(self):
        pixels = np.full((32, 32, 3), (210, 230, 235), dtype=np.uint8)
        data = png(pixels)
        kept, tag = keep_scene(data, matte(pixels.shape[:2], (8, 24, 10, 22)))
        self.assertEqual(kept, data)
        self.assertEqual(tag, "scene")

    def test_clean_background_preserves_size_and_clean_width_tag(self):
        pixels = np.full((32, 32, 3), (210, 230, 235), dtype=np.uint8)
        pixels[8:24, 10:22] = (40, 40, 40)
        cleaned, tag = clean_background(png(pixels), matte(pixels.shape[:2],
                                                           (8, 24, 10, 22)))
        self.assertEqual(Image.open(io.BytesIO(cleaned)).size, (32, 32))
        self.assertRegex(tag, r"^clean-w\d+-p\d+$")

    def test_clean_background_band_widths_derive_from_longest_side_and_each_other(self):
        pixels = np.full((30, 50, 3), (210, 230, 235), dtype=np.uint8)
        pixels[8:24, 15:35] = (20, 20, 20)
        _, tag = clean_background(png(pixels), matte(pixels.shape[:2],
                                                     (8, 24, 15, 35)))
        match = re.match(r"^clean-w(\d+)-p(\d+)$", tag)
        self.assertIsNotNone(match)
        white_w = max(30, 50) * delivery_style.WHITE_WIDTH_PCT / 100
        purple_w = white_w * delivery_style.STROKE_WIDTH_BAND
        self.assertEqual(match.group(1), f"{white_w:.0f}")
        self.assertEqual(match.group(2), f"{purple_w:.0f}")

    def test_clean_background_composites_purple_under_white_under_figure(self):
        # Walking outward from the figure's edge should cross the white band
        # first, the purple band second, and only then the flat backdrop --
        # the layer order the delivery is supposed to draw them in.
        height = width = 240
        pixels = np.full((height, width, 3), (233, 229, 199), dtype=np.uint8)
        pixels[80:160, 80:160] = (10, 10, 10)
        cleaned, _ = clean_background(png(pixels), matte(pixels.shape[:2],
                                                         (80, 160, 80, 160)))
        arr = np.array(Image.open(io.BytesIO(cleaned)).convert("RGB")).astype(int)

        backdrop = np.array(parse_color(delivery_style.BACKDROP))
        purple = np.array(parse_color(delivery_style.STROKE))
        white = np.array([255, 255, 255])

        row = height // 2
        cols = np.arange(160, width)
        strip = arr[row, cols]

        def first_match(color, tolerance=20):
            distance = np.abs(strip - color).sum(axis=1)
            hits = np.where(distance <= tolerance)[0]
            self.assertTrue(hits.size, f"strip never reaches {color}")
            return cols[hits[0]]

        white_at = first_match(white)
        purple_at = first_match(purple)
        backdrop_at = first_match(backdrop)
        self.assertLess(white_at, purple_at)
        self.assertLess(purple_at, backdrop_at)

    def test_transparent_frames_the_cutout_with_the_sticker_bands(self):
        pixels = np.full((256, 256, 3), (210, 230, 235), dtype=np.uint8)
        pixels[64:192, 64:160] = (40, 40, 40)
        cut, tag = transparent(png(pixels), matte(pixels.shape[:2], (64, 192, 64, 160)))
        image = Image.open(io.BytesIO(cut))
        self.assertEqual(image.mode, "RGBA")
        self.assertEqual(image.size, (256, 256))
        arr = np.array(image)
        purple = np.array(parse_color(delivery_style.STROKE))
        white = np.array([255, 255, 255])
        # Inside the figure: its own pixels, opaque.
        np.testing.assert_array_equal(arr[128, 100, :3], (40, 40, 40))
        self.assertEqual(arr[128, 100, 3], 255)
        # 256 * 1.3% = 3.3px of white, then 0.8x that of purple, then nothing.
        np.testing.assert_array_equal(arr[128, 162, :3], white)
        self.assertEqual(arr[128, 162, 3], 255)
        np.testing.assert_array_equal(arr[128, 164, :3], purple)
        self.assertEqual(arr[128, 164, 3], 255)
        self.assertEqual(arr[128, 172, 3], 0)
        self.assertEqual(arr[0, 0, 3], 0)
        self.assertEqual(tag, "transparent-w3-p3")

    def test_transparent_keeps_the_retrace_inside_the_soft_matte(self):
        pixels = np.full((256, 256, 3), (210, 230, 235), dtype=np.uint8)
        pixels[64:192, 64:160] = (40, 40, 40)
        pixels[64:192, 160:161] = (150, 150, 150)   # backdrop shading at the edge
        pixels[120:136, 159:160] = (215, 228, 232)  # a light passage at the edge
        soft = np.zeros((256, 256), dtype=np.uint8)
        soft[64:192, 64:160] = 255
        cut, _ = transparent(png(pixels), png(soft))
        arr = np.array(Image.open(io.BytesIO(cut)))
        # The shading column is band, not figure: the white band paints over
        # it, and the figure's own edge stays where the soft matte put it.
        np.testing.assert_array_equal(arr[128, 161, :3], (255, 255, 255))
        self.assertGreater(arr[128, 160, :3].min(), 200)
        np.testing.assert_array_equal(arr[128, 159, :3], (215, 228, 232))
        self.assertEqual(arr[128, 159, 3], 255)

    def test_stroke_alpha_ramps_over_one_pixel_at_the_outer_edge(self):
        mask = np.ones((1, 12), dtype=bool)
        mask[0, 0] = False
        # edge_smooth=0.0: gaussian_filter is a no-op, isolating the raw ramp
        # math this test checks from the boundary-rounding blur.
        alpha = stroke_alpha(mask, 0.0, 5.0, 0.0)
        self.assertEqual(alpha[0, 1], 1.0)
        self.assertEqual(alpha[0, 5], 0.5)
        self.assertEqual(alpha[0, 6], 0.0)

    def test_down2_averages_each_2x2_block(self):
        block = np.array([[1.0, 3.0], [5.0, 7.0]])
        self.assertEqual(float(down2(block)[0, 0]), 4.0)

    def _disc_figure(self, size=200, radius=40):
        figure = np.zeros((size, size), dtype=bool)
        yy, xx = np.mgrid[0:size, 0:size]
        cy = cx = size / 2
        figure[(yy - cy) ** 2 + (xx - cx) ** 2 <= radius ** 2] = True
        return figure, cy, cx, radius

    def test_band_alphas_light_thins_the_purple_band_toward_the_light(self):
        figure, cy, cx, radius = self._disc_figure()
        _, purple = band_alphas(figure, light="ne")
        r = 2 ** -0.5
        steps = np.arange(0, 40)

        def band_width(dx, dy):
            ys = np.clip((cy + (radius + steps) * dy).round().astype(int), 0, 199)
            xs = np.clip((cx + (radius + steps) * dx).round().astype(int), 0, 199)
            return purple[ys, xs].sum()

        thin_side = band_width(r, -r)    # toward the ne light
        thick_side = band_width(-r, r)   # away from it, sw
        self.assertGreater(thick_side, thin_side * 2)

    def test_band_alphas_antialiases_the_purple_edge_on_a_diagonal(self):
        # The rows around a disc's own 45-degree point are the worst case for
        # staircasing. Ramping off the raw distance transform inherits the
        # boundary's steps and collapses the band edge onto a handful of
        # repeated coverage levels there; rounding the field off first spreads
        # it over many. At STROKE_EDGE_SMOOTH = 0 this band yields 9 distinct
        # levels, at 1.0 it yields 26.
        figure, cy, _, radius = self._disc_figure()
        r = 2 ** -0.5
        row_center = int(cy - radius * r)
        rows = np.arange(row_center - 15, row_center + 15)
        _, purple = band_alphas(figure)
        values = purple[rows].ravel()
        intermediate = values[(values > 0.05) & (values < 0.95)]
        self.assertGreater(intermediate.size, 0)
        self.assertGreater(len(np.unique(np.round(intermediate, 3))), 15)

    def test_band_alphas_without_light_matches_omitting_the_argument(self):
        figure, *_ = self._disc_figure()
        white_a, purple_a = band_alphas(figure)
        white_b, purple_b = band_alphas(figure, light=None)
        np.testing.assert_array_equal(white_a, white_b)
        np.testing.assert_array_equal(purple_a, purple_b)

    def test_band_alphas_unknown_light_key_raises(self):
        figure, *_ = self._disc_figure()
        with self.assertRaises(ValueError) as context:
            band_alphas(figure, light="north")
        message = str(context.exception)
        for key in ("n", "ne", "e", "se", "s", "sw", "w", "nw"):
            self.assertIn(repr(key), message)

    def test_transparent_light_appends_a_tag_suffix(self):
        pixels = np.full((256, 256, 3), (210, 230, 235), dtype=np.uint8)
        pixels[64:192, 64:160] = (40, 40, 40)
        _, tag = transparent(png(pixels), matte(pixels.shape[:2], (64, 192, 64, 160)),
                             light="ne")
        self.assertEqual(tag, "transparent-w3-p3-light-ne")

    def test_clean_background_light_appends_a_tag_suffix(self):
        pixels = np.full((32, 32, 3), (210, 230, 235), dtype=np.uint8)
        pixels[8:24, 10:22] = (40, 40, 40)
        _, tag = clean_background(png(pixels), matte(pixels.shape[:2], (8, 24, 10, 22)),
                                  light="sw")
        self.assertRegex(tag, r"^clean-w\d+-p\d+-light-sw$")

    def test_clean_background_backdrop_stripes_tag_and_pattern(self):
        pixels = np.full((64, 64, 3), (210, 230, 235), dtype=np.uint8)
        pixels[16:48, 16:48] = (40, 40, 40)
        cleaned, tag = clean_background(
            png(pixels), matte(pixels.shape[:2], (16, 48, 16, 48)),
            backdrop="stripes")
        self.assertRegex(tag, r"^clean-w\d+-p\d+-bg-stripes$")
        arr = np.array(Image.open(io.BytesIO(cleaned)).convert("RGB"))
        corners = [tuple(arr[0, 0]), tuple(arr[0, -1]),
                  tuple(arr[-1, 0]), tuple(arr[-1, -1])]
        self.assertGreater(len(set(corners)), 1)

    def test_clean_background_backdrop_colour_tag_suffix(self):
        pixels = np.full((32, 32, 3), (210, 230, 235), dtype=np.uint8)
        pixels[8:24, 10:22] = (40, 40, 40)
        _, tag = clean_background(png(pixels), matte(pixels.shape[:2], (8, 24, 10, 22)),
                                  backdrop="#c7e5e9")
        self.assertRegex(tag, r"^clean-w\d+-p\d+-bg-c7e5e9$")

    def test_clean_background_backdrop_none_tag_unchanged(self):
        pixels = np.full((32, 32, 3), (210, 230, 235), dtype=np.uint8)
        pixels[8:24, 10:22] = (40, 40, 40)
        _, tag = clean_background(png(pixels), matte(pixels.shape[:2], (8, 24, 10, 22)))
        self.assertRegex(tag, r"^clean-w\d+-p\d+$")


def rgba_png(pixels: np.ndarray, alpha: np.ndarray) -> bytes:
    """A layerdiffuse render's own RGBA, alpha unrefined."""
    output = io.BytesIO()
    Image.fromarray(np.dstack([pixels, alpha]).astype(np.uint8), "RGBA").save(
        output, "PNG")
    return output.getvalue()


class ComposeTest(unittest.TestCase):
    def test_compose_returns_rgb_of_the_same_size(self):
        pixels = np.full((32, 32, 3), (40, 40, 40), dtype=np.uint8)
        alpha = np.zeros((32, 32), dtype=np.uint8)
        alpha[8:24, 10:22] = 255
        composed, tag = compose(rgba_png(pixels, alpha))
        image = Image.open(io.BytesIO(composed))
        self.assertEqual(image.mode, "RGB")
        self.assertEqual(image.size, (32, 32))
        self.assertTrue(tag.startswith("compose-"))

    def test_compose_uses_the_backdrop_colour_where_alpha_is_zero(self):
        pixels = np.full((32, 32, 3), (40, 40, 40), dtype=np.uint8)
        alpha = np.zeros((32, 32), dtype=np.uint8)
        alpha[8:24, 10:22] = 255
        composed, _ = compose(rgba_png(pixels, alpha))
        arr = np.array(Image.open(io.BytesIO(composed)).convert("RGB"))
        backdrop = np.array(parse_color(delivery_style.BACKDROP))
        np.testing.assert_array_equal(arr[0, 0], backdrop)

    def test_compose_keeps_the_figures_own_colour_where_alpha_is_full(self):
        pixels = np.full((32, 32, 3), (40, 40, 40), dtype=np.uint8)
        alpha = np.zeros((32, 32), dtype=np.uint8)
        alpha[8:24, 10:22] = 255
        composed, _ = compose(rgba_png(pixels, alpha))
        arr = np.array(Image.open(io.BytesIO(composed)).convert("RGB"))
        np.testing.assert_array_equal(arr[16, 16], pixels[16, 16])

    def test_compose_draws_the_stroke_band_just_outside_the_figure(self):
        pixels = np.full((240, 240, 3), (40, 40, 40), dtype=np.uint8)
        alpha = np.zeros((240, 240), dtype=np.uint8)
        alpha[80:160, 80:160] = 255
        composed, _ = compose(rgba_png(pixels, alpha))
        arr = np.array(Image.open(io.BytesIO(composed)).convert("RGB")).astype(int)
        backdrop = np.array(parse_color(delivery_style.BACKDROP))
        row = 120
        cols = np.arange(160, 240)
        strip = arr[row, cols]

        def not_backdrop(tolerance=20):
            distance = np.abs(strip - backdrop).sum(axis=1)
            hits = np.where(distance > tolerance)[0]
            self.assertTrue(hits.size, "no band pixel found just outside the figure")
            return cols[hits[0]]

        self.assertLess(not_backdrop(), 165)

    def test_compose_honors_an_explicit_backdrop(self):
        pixels = np.full((32, 32, 3), (40, 40, 40), dtype=np.uint8)
        alpha = np.zeros((32, 32), dtype=np.uint8)
        alpha[8:24, 10:22] = 255
        composed, _ = compose(rgba_png(pixels, alpha), backdrop="#112233")
        arr = np.array(Image.open(io.BytesIO(composed)).convert("RGB"))
        np.testing.assert_array_equal(arr[0, 0], np.array(parse_color("#112233")))

    def test_compose_backdrop_stripes_tag_suffix_and_pattern(self):
        pixels = np.full((64, 64, 3), (40, 40, 40), dtype=np.uint8)
        alpha = np.zeros((64, 64), dtype=np.uint8)
        alpha[16:48, 16:48] = 255
        composed, tag = compose(rgba_png(pixels, alpha), backdrop="stripes")
        self.assertRegex(tag, r"^compose-w\d+-p\d+-bg-stripes$")
        arr = np.array(Image.open(io.BytesIO(composed)).convert("RGB"))
        corners = [tuple(arr[0, 0]), tuple(arr[0, -1]),
                  tuple(arr[-1, 0]), tuple(arr[-1, -1])]
        self.assertGreater(len(set(corners)), 1)

    def test_compose_band_less_tag_and_no_band_drawn(self):
        pixels = np.full((240, 240, 3), (40, 40, 40), dtype=np.uint8)
        alpha = np.zeros((240, 240), dtype=np.uint8)
        alpha[80:160, 80:160] = 255
        composed, tag = compose(rgba_png(pixels, alpha), bands=False)
        self.assertEqual(tag, "compose-flat")
        arr = np.array(Image.open(io.BytesIO(composed)).convert("RGB")).astype(int)
        backdrop = np.array(parse_color(delivery_style.BACKDROP))
        row = 120
        outside = arr[row, 160:240]
        np.testing.assert_array_equal(outside, np.broadcast_to(backdrop, outside.shape))

    def test_compose_band_less_keeps_the_figures_own_colour(self):
        pixels = np.full((32, 32, 3), (40, 40, 40), dtype=np.uint8)
        alpha = np.zeros((32, 32), dtype=np.uint8)
        alpha[8:24, 10:22] = 255
        composed, _ = compose(rgba_png(pixels, alpha), bands=False)
        arr = np.array(Image.open(io.BytesIO(composed)).convert("RGB"))
        np.testing.assert_array_equal(arr[16, 16], pixels[16, 16])

    def test_compose_band_less_honors_an_explicit_backdrop(self):
        pixels = np.full((32, 32, 3), (40, 40, 40), dtype=np.uint8)
        alpha = np.zeros((32, 32), dtype=np.uint8)
        alpha[8:24, 10:22] = 255
        composed, tag = compose(rgba_png(pixels, alpha), backdrop="#112233", bands=False)
        arr = np.array(Image.open(io.BytesIO(composed)).convert("RGB"))
        np.testing.assert_array_equal(arr[0, 0], np.array(parse_color("#112233")))
        self.assertEqual(tag, "compose-flat-bg-112233")


if __name__ == "__main__":
    unittest.main()


class SkinPinTest(unittest.TestCase):
    def source(self):
        """A warm low-saturation cheek with a high-saturation lip inside it."""
        pixels = np.full((256, 256, 3), (210, 230, 235), dtype=np.uint8)
        pixels[64:192, 64:192] = (247, 226, 209)   # cheek: warm, S ~ 25
        pixels[120:136, 112:144] = (222, 40, 40)   # lip: warm, S ~ 200
        return pixels

    def test_the_cheek_is_pinned_to_the_skin_hue(self):
        source = self.source()
        redrawn = source.copy()
        redrawn[64:192, 64:192] = (226, 209, 247)  # the redraw's lavender cheek
        out, report = repin_skin_png(png(source), png(redrawn))
        hsv = np.array(Image.open(io.BytesIO(out)).convert("HSV"))
        target = delivery_style.PALETTE_WINDOWS[1]["hue_target"]
        self.assertAlmostEqual(float(hsv[96, 96, 0]), target, delta=3)
        self.assertIn("skin pinned", report[0])

    def test_the_lip_keeps_its_own_hue(self):
        source = self.source()
        out, _ = repin_skin_png(png(source), png(source))
        hsv = np.array(Image.open(io.BytesIO(out)).convert("HSV"))
        before = np.array(Image.fromarray(source).convert("HSV"))
        self.assertAlmostEqual(float(hsv[128, 128, 0]), float(before[128, 128, 0]),
                               delta=2)


    def test_a_face_the_base_drew_lavender_is_left_alone(self):
        source = self.source()
        source[64:192, 64:192] = (226, 209, 247)   # no skin drawn anywhere
        redrawn = source.copy()
        out, report = repin_skin_png(png(source), png(redrawn))
        self.assertEqual(out, png(redrawn))
        self.assertIn("not pinned", report[0])

    def test_the_hue_turns_the_short_way_round(self):
        # 191 down to 18 crosses green; the short way crosses red.
        source = self.source()
        redrawn = source.copy()
        redrawn[64:192, 64:192] = (226, 209, 247)
        out, _ = repin_skin_png(png(source), png(redrawn))
        hsv = np.array(Image.open(io.BytesIO(out)).convert("HSV"))
        cheek = hsv[64:192, 64:192, 0].astype(int)
        self.assertFalse(((cheek > 60) & (cheek < 150)).any())
