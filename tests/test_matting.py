"""Matting stage: trimap, known-region forcing and the PNG round trip."""

from __future__ import annotations

import io
import unittest

import numpy as np
from PIL import Image

from comfyui_recipes.infrastructure.imaging import matting


def rgb_png(pixels: np.ndarray) -> bytes:
    output = io.BytesIO()
    Image.fromarray(pixels.astype(np.uint8)).save(output, "PNG")
    return output.getvalue()


def figure_mask(size=64, box=(16, 48, 16, 48)) -> np.ndarray:
    figure = np.zeros((size, size), dtype=bool)
    top, bottom, left, right = box
    figure[top:bottom, left:right] = True
    return figure


class TrimapTest(unittest.TestCase):
    def test_trimap_marks_the_eroded_core_figure_and_the_far_backdrop(self):
        known = matting.trimap(figure_mask(), 4)
        self.assertEqual(set(np.unique(known)), {0, 128, 255})
        self.assertTrue((known[20:44, 20:44] == 255).all())
        self.assertEqual(known[0, 0], 0)

    def test_trimap_unknown_band_straddles_the_figure_edge(self):
        known = matting.trimap(figure_mask(), 3)
        self.assertEqual(known[12, 32], 0)
        self.assertEqual(known[13, 32], 128)
        self.assertEqual(known[18, 32], 128)
        self.assertEqual(known[19, 32], 255)
        self.assertEqual(known[44, 32], 255)
        self.assertEqual(known[45, 32], 128)
        self.assertEqual(known[50, 32], 128)
        self.assertEqual(known[51, 32], 0)


class FinishTest(unittest.TestCase):
    def test_finish_forces_the_known_regions_onto_the_alpha(self):
        px = np.full((8, 8, 3), 100.0)
        known = np.full((8, 8), matting.UNKNOWN, dtype=np.uint8)
        known[:, :2] = matting.KNOWN_FIGURE
        known[:, 6:] = matting.KNOWN_BACKDROP
        alpha = np.full((8, 8), 0.5)
        _, out = matting.finish(px, alpha, known, lambda rgb, a: rgb)
        self.assertTrue((out[:, :2] == 1.0).all())
        self.assertTrue((out[:, 6:] == 0.0).all())
        self.assertTrue((out[:, 2:6] == 0.5).all())

    def test_finish_keeps_the_raw_pixels_where_alpha_is_zero(self):
        px = np.zeros((8, 8, 3))
        px[...] = (10.0, 20.0, 30.0)
        px[:, 6:] = (200.0, 100.0, 50.0)
        known = np.full((8, 8), matting.UNKNOWN, dtype=np.uint8)
        known[:, 6:] = matting.KNOWN_BACKDROP
        known[:, :2] = matting.KNOWN_FIGURE
        alpha = np.full((8, 8), 0.5)

        def foreground(rgb, a):
            return np.zeros_like(rgb)

        colour, out = matting.finish(px, alpha, known, foreground)
        np.testing.assert_array_equal(colour[:, 6:], px[:, 6:])
        self.assertEqual(float(colour[4, 0].max()), 0.0)
        self.assertTrue((out[:, 6:] == 0.0).all())

    def test_finish_clips_the_models_alpha_to_the_unit_range(self):
        px = np.full((4, 4, 3), 50.0)
        known = np.full((4, 4), matting.UNKNOWN, dtype=np.uint8)
        alpha = np.array([[-0.5, 1.5, 0.25, 0.75]] * 4)
        _, out = matting.finish(px, alpha, known, lambda rgb, a: rgb)
        np.testing.assert_array_equal(out[0], [0.0, 1.0, 0.25, 0.75])


class MattePngTest(unittest.TestCase):
    def test_matte_png_round_trips_with_a_stand_in_model(self):
        pixels = np.full((64, 64, 3), (210, 230, 235), dtype=np.uint8)
        pixels[16:48, 16:48] = (40, 40, 40)
        soft = np.zeros((64, 64), dtype=np.uint8)
        soft[16:48, 16:48] = 255
        seen = {}

        def predict(rgb, known):
            seen["rgb"], seen["known"] = rgb, known
            return np.full(known.shape, 0.5)

        image_png, alpha_png = matting.matte_png(
            rgb_png(pixels), rgb_png(soft), predict, lambda rgb, alpha: rgb)
        image = np.array(Image.open(io.BytesIO(image_png)))
        alpha_img = Image.open(io.BytesIO(alpha_png))
        alpha = np.array(alpha_img)
        self.assertEqual(alpha_img.mode, "L")
        self.assertEqual(image.shape, (64, 64, 3))
        self.assertEqual(seen["rgb"].dtype, np.uint8)
        self.assertEqual(seen["known"].shape, (64, 64))
        self.assertEqual(alpha[32, 32], 255)
        self.assertEqual(alpha[0, 0], 0)
        unknown = seen["known"] == matting.UNKNOWN
        self.assertTrue(unknown.any())
        self.assertTrue((alpha[unknown] == 128).all())
        np.testing.assert_array_equal(image[0, 0], pixels[0, 0])
        np.testing.assert_allclose(image[32, 32], (40, 40, 40), atol=1)


if __name__ == "__main__":
    unittest.main()
