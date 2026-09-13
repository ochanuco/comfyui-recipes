from __future__ import annotations

import unittest

import numpy as np
from PIL import Image

from comfyui_recipes.domain.yukari.delivery_style import REPIN_DARK, REPIN_LIGHT
from comfyui_recipes.infrastructure.imaging.palette import palette_window, repin

KNEE, RATIO = REPIN_LIGHT
DARK_KNEE, DARK_RATIO = REPIN_DARK


def compressed(saturation: float) -> float:
    return KNEE + (saturation - KNEE) * RATIO


def dark_compressed(saturation: float) -> float:
    return DARK_KNEE + (saturation - DARK_KNEE) * DARK_RATIO


def swatch(hsv_center: tuple[int, int, int]) -> np.ndarray:
    """64x64 flat #808080 backdrop, a 32x32 centre block at the given HSV."""
    pixels = np.full((64, 64, 3), 0x80, dtype=np.uint8)
    hsv = np.zeros((32, 32, 3), dtype=np.uint8)
    hsv[..., 0], hsv[..., 1], hsv[..., 2] = hsv_center
    block = np.array(Image.fromarray(hsv, "HSV").convert("RGB"))
    pixels[16:48, 16:48] = block
    return pixels


def center_hsv(rgb: np.ndarray) -> np.ndarray:
    hsv = np.array(Image.fromarray(rgb).convert("HSV")).astype(float)
    return hsv[16:48, 16:48]


class CyanWindowTest(unittest.TestCase):
    def test_bright_cyan_is_compressed_toward_the_light_knee(self):
        pixels = swatch((128, 150, 230))
        rgb, _ = repin(pixels)
        center = center_hsv(rgb)
        self.assertAlmostEqual(center[..., 1].mean(), compressed(150), delta=2)
        self.assertAlmostEqual(center[..., 0].mean(), 128, delta=1)

    def test_dark_cyan_is_exempt_from_the_dark_band(self):
        pixels = swatch((128, 200, 60))
        rgb, _ = repin(pixels)
        center = center_hsv(rgb)
        self.assertAlmostEqual(center[..., 1].mean(), 200, delta=2)

    def test_dark_green_outside_the_exemptions_is_still_crushed(self):
        pixels = swatch((90, 200, 60))
        rgb, _ = repin(pixels)
        center = center_hsv(rgb)
        self.assertAlmostEqual(center[..., 1].mean(), dark_compressed(200),
                                delta=2)

    def test_purple_only_render_is_unchanged_by_the_new_window(self):
        pixels = swatch((191, 150, 230))
        rgb, _ = repin(pixels)
        center = center_hsv(rgb)
        self.assertAlmostEqual(center[..., 1].mean(), compressed(150), delta=2)

        eased = swatch((200, 150, 230))
        input_h = center_hsv(eased)[..., 0].mean()
        rgb_eased, _ = repin(eased)
        center_eased = center_hsv(rgb_eased)
        expected_h = input_h * (1 - 0.7) + 0.7 * 191
        self.assertAlmostEqual(center_eased[..., 0].mean(), expected_h, delta=2)

    def test_palette_window_skin_is_the_entry_repin_skin_png_uses(self):
        window = palette_window("skin")
        self.assertEqual(window["hue"], (0.0, 48.0))
        self.assertEqual(window["hue_target"], 17.8)


if __name__ == "__main__":
    unittest.main()
