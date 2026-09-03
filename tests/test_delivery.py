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
    clean_background,
    down2,
    graph_from_png,
    parse_color,
    refine_matte,
    stroke_alpha,
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

    def test_stroke_alpha_ramps_over_one_pixel_at_the_outer_edge(self):
        mask = np.ones((1, 12), dtype=bool)
        mask[0, 0] = False
        alpha = stroke_alpha(mask, 0.0, 5.0)
        self.assertEqual(alpha[0, 1], 1.0)
        self.assertEqual(alpha[0, 5], 0.5)
        self.assertEqual(alpha[0, 6], 0.0)

    def test_down2_averages_each_2x2_block(self):
        block = np.array([[1.0, 3.0], [5.0, 7.0]])
        self.assertEqual(float(down2(block)[0, 0]), 4.0)


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
