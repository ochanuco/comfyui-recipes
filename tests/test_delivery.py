from __future__ import annotations

import io
import json
import unittest

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from comfyui_recipes.infrastructure.imaging.delivery import (
    background_mask,
    clean_background,
    graph_from_png,
    parse_color,
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

    def test_background_mask_uses_top_left_four_connected_component(self):
        pixels = np.full((3, 3, 3), 255, dtype=int)
        pixels[0, 0] = 0
        pixels[2, 2] = 0
        mask = background_mask(pixels, 0)
        self.assertEqual(int(mask.sum()), 1)
        self.assertTrue(mask[0, 0])
        self.assertFalse(mask[2, 2])

        pixels[0, 1] = 0
        self.assertEqual(int(background_mask(pixels, 0).sum()), 2)

    def test_clean_background_preserves_size_and_clean_width_tag(self):
        pixels = np.full((32, 32, 3), (210, 230, 235), dtype=np.uint8)
        pixels[8:24, 10:22] = (40, 40, 40)
        cleaned, tag = clean_background(png(pixels))
        self.assertEqual(Image.open(io.BytesIO(cleaned)).size, (32, 32))
        self.assertRegex(tag, r"^clean-p\d+$")


if __name__ == "__main__":
    unittest.main()
