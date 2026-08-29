from __future__ import annotations

import io
import json
import re
import unittest

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from comfyui_recipes.domain.yukari import delivery_style
from comfyui_recipes.infrastructure.imaging.delivery import (
    background_mask,
    clean_background,
    down2,
    graph_from_png,
    parse_color,
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
        pixels = np.full((3, 3, 3), 255, dtype=int)
        pixels[0, 0] = 0
        pixels[2, 2] = 0
        mask = background_mask(pixels, 0)
        self.assertEqual(int(mask.sum()), 2)
        self.assertTrue(mask[0, 0])
        self.assertTrue(mask[2, 2])

    def test_background_mask_leaves_regions_walled_off_from_the_frame(self):
        # Backdrop enclosed by the figure is `enclosed_mask`'s job, on its own
        # much tighter tolerance; the flood must not reach it.
        pixels = np.full((5, 5, 3), 255, dtype=int)
        pixels[0, 0] = 0
        pixels[2, 2] = 0
        mask = background_mask(pixels, 0)
        self.assertTrue(mask[0, 0])
        self.assertFalse(mask[2, 2])

    def test_clean_background_preserves_size_and_clean_width_tag(self):
        pixels = np.full((32, 32, 3), (210, 230, 235), dtype=np.uint8)
        pixels[8:24, 10:22] = (40, 40, 40)
        cleaned, tag = clean_background(png(pixels))
        self.assertEqual(Image.open(io.BytesIO(cleaned)).size, (32, 32))
        self.assertRegex(tag, r"^clean-w\d+-p\d+$")

    def test_clean_background_band_widths_derive_from_longest_side_and_each_other(self):
        pixels = np.full((30, 50, 3), (210, 230, 235), dtype=np.uint8)
        pixels[8:24, 15:35] = (20, 20, 20)
        _, tag = clean_background(png(pixels))
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
        cleaned, _ = clean_background(png(pixels))
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
