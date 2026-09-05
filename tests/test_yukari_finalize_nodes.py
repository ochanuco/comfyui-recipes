"""Node-pack tests for comfy_nodes/yukari_finalize.

The pack lives outside src/ so ComfyUI can reach it through a junction named
after the package; sys.path is extended here the same way, by resolving this
file's own path rather than relying on the working directory.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from comfy_nodes.yukari_finalize import bridge, nodes  # noqa: E402


class FakeTensor:
    """Stand-in for a torch tensor: only what the bridge calls on one."""

    def __init__(self, array):
        self.array = np.asarray(array)

    def cpu(self):
        return self

    def numpy(self):
        return self.array

    def __getitem__(self, index):
        return FakeTensor(self.array[index])


class FakeTorch:
    @staticmethod
    def from_numpy(array):
        return FakeTensor(array)


def swatch() -> np.ndarray:
    """64x64 flat #808080 backdrop with a saturated 32x32 centre block."""
    pixels = np.full((64, 64, 3), 0x80, dtype=np.uint8)
    hsv = np.zeros((32, 32, 3), dtype=np.uint8)
    hsv[..., 0], hsv[..., 1], hsv[..., 2] = (10, 180, 160)
    pixels[16:48, 16:48] = np.array(Image.fromarray(hsv, "HSV").convert("RGB"))
    return pixels


def matte_array() -> np.ndarray:
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[16:48, 16:48] = 255
    return mask


def image_tensor(pixels: np.ndarray) -> FakeTensor:
    return FakeTensor((pixels.astype(np.float32) / 255.0)[None, ...])


def mask_tensor(mask: np.ndarray) -> FakeTensor:
    return FakeTensor((mask.astype(np.float32) / 255.0)[None, ...])


class BridgeTest(unittest.TestCase):
    def test_array_png_round_trip_rgb(self):
        pixels = swatch()
        data = bridge.array_to_png(pixels, "RGB")
        back = bridge.png_to_array(data, "RGB")
        np.testing.assert_array_equal(back, pixels)

    def test_array_png_round_trip_l(self):
        mask = matte_array()
        data = bridge.array_to_png(mask, "L")
        back = bridge.png_to_array(data, "L")
        np.testing.assert_array_equal(back, mask)

    def test_image_tensor_round_trips_through_png(self):
        pixels = swatch()
        with mock.patch.dict(sys.modules, {"torch": FakeTorch()}):
            data = bridge.image_to_png(image_tensor(pixels))
            back = bridge.png_to_image(data)
        self.assertEqual(back.array.shape, (1, 64, 64, 3))
        np.testing.assert_allclose(
            (back.array[0] * 255.0).round(), pixels, atol=1)

    def test_mask_tensor_becomes_an_l_png(self):
        mask = matte_array()
        data = bridge.mask_to_png(mask_tensor(mask))
        back = bridge.png_to_array(data, "L")
        np.testing.assert_array_equal(back, mask)


class NodeMappingTest(unittest.TestCase):
    def test_node_class_mappings_cover_the_four_nodes(self):
        self.assertEqual(set(nodes.NODE_CLASS_MAPPINGS), {
            "YukariRepinSkin", "YukariRepin", "YukariRecolor", "YukariDeliver",
        })
        self.assertEqual(
            set(nodes.NODE_DISPLAY_NAME_MAPPINGS),
            set(nodes.NODE_CLASS_MAPPINGS))

    def test_importing_the_package_does_not_require_comfyui(self):
        for name in list(sys.modules):
            if name == "comfy_nodes" or name.startswith("comfy_nodes."):
                del sys.modules[name]
        import comfy_nodes.yukari_finalize as reimported
        self.assertIn("YukariDeliver", reimported.NODE_CLASS_MAPPINGS)


class NodeRunTest(unittest.TestCase):
    def setUp(self):
        self._torch_patch = mock.patch.dict(
            sys.modules, {"torch": FakeTorch()})
        self._torch_patch.start()
        self.addCleanup(self._torch_patch.stop)

    def test_repin_skin_wiring_returns_an_image_and_a_report_string(self):
        node = nodes.YukariRepinSkin()
        pixels = swatch()
        image, report = node.run(image_tensor(pixels), image_tensor(pixels))
        self.assertEqual(image.array.shape, (1, 64, 64, 3))
        self.assertIsInstance(report, str)

    def test_repin_wiring_returns_an_image_and_a_report_string(self):
        node = nodes.YukariRepin()
        image, report = node.run(
            image_tensor(swatch()), keep_legwear=False, keep_legwear_cut=0.62)
        self.assertEqual(image.array.shape, (1, 64, 64, 3))
        self.assertIsInstance(report, str)

    def test_recolor_wiring_returns_an_image_and_a_report_string(self):
        node = nodes.YukariRecolor()
        image, report = node.run(image_tensor(swatch()))
        self.assertEqual(image.array.shape, (1, 64, 64, 3))
        self.assertIsInstance(report, str)

    def test_deliver_wiring_returns_an_image_and_a_tag(self):
        node = nodes.YukariDeliver()
        image, tag = node.run(
            image_tensor(swatch()), mask_tensor(matte_array()), keep_scene=False)
        self.assertEqual(image.array.shape[0], 1)
        self.assertEqual(image.array.shape[-1], 3)
        self.assertTrue(tag.startswith("clean-"))

    def test_deliver_keep_scene_returns_the_redraw_uncut(self):
        node = nodes.YukariDeliver()
        pixels = swatch()
        image, tag = node.run(
            image_tensor(pixels), mask_tensor(matte_array()), keep_scene=True)
        self.assertEqual(tag, "scene")
        np.testing.assert_allclose(
            (image.array[0] * 255.0).round(), pixels, atol=1)


if __name__ == "__main__":
    unittest.main()
