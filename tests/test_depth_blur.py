"""Depth-of-field blur: imaging function and graph wiring."""

from __future__ import annotations

import unittest

import numpy as np

from comfyui_recipes.infrastructure.comfyui.refinement_graph import (
    DEPTH_CKPT, DEPTH_NODE, chain_pass)
from comfyui_recipes.infrastructure.imaging.depth_blur import depth_blur

SIZE = 128


def blurred(*args) -> np.ndarray:
    return depth_blur(*args)[0]


def striped_image() -> np.ndarray:
    columns = (np.arange(SIZE) % 4 < 2) * 200 + 20
    return np.repeat(np.stack([columns] * 3, axis=-1)[None], SIZE, axis=0).astype(np.uint8)


def near_left_depth() -> np.ndarray:
    depth = np.zeros((SIZE, SIZE), np.float32)
    depth[:, :SIZE // 2] = 1.0
    return depth


def variance(image: np.ndarray, columns: slice) -> float:
    return float(image[:, columns, 0].astype(np.float32).var())


class DepthBlurTest(unittest.TestCase):
    def setUp(self):
        self.image = striped_image()
        self.depth = near_left_depth()
        self.matte = np.ones((SIZE, SIZE), np.float32)

    def test_focus_depth_stays_sharp_and_far_side_blurs(self):
        out = blurred(self.image, self.depth, self.matte, 0.1, 0.5, 1.0)
        near = slice(0, SIZE // 2 - 8)
        far = slice(SIZE // 2 + 8, SIZE)
        np.testing.assert_array_equal(out[:, near], self.image[:, near])
        self.assertLess(variance(out, far), 0.5 * variance(self.image, far))

    def test_larger_f_number_blurs_less(self):
        far = slice(SIZE // 2 + 8, SIZE)
        wide = blurred(self.image, self.depth, self.matte, 0.1, 0.5, 1.4)
        narrow = blurred(self.image, self.depth, self.matte, 0.1, 0.5, 11.0)
        self.assertLess(variance(wide, far), variance(narrow, far))

    def test_f_numbers_below_one_keep_blurring_more(self):
        far = slice(SIZE // 2 + 8, SIZE)
        depth = np.tile(np.linspace(1.0, 0.0, SIZE, dtype=np.float32), (SIZE, 1))
        brighter = blurred(self.image, depth, self.matte, 0.0, 0.5, 0.7)
        one = blurred(self.image, depth, self.matte, 0.0, 0.5, 1.0)
        self.assertLess(variance(brighter, far), variance(one, far))

    def test_sharp_pixels_do_not_bleed_into_the_blur(self):
        image = np.zeros((SIZE, SIZE, 3), np.uint8)
        image[:, :SIZE // 2] = (255, 0, 0)
        image[:, SIZE // 2:] = (0, 0, 255)
        out = blurred(image, self.depth, self.matte, 0.1, 0.5, 0.7)
        self.assertLessEqual(int(out[:, SIZE // 2:, 0].max()), 1)

    def test_outside_the_widened_matte_is_untouched(self):
        matte = self.matte.copy()
        matte[:, SIZE - 32:] = 0.0
        out, widened = depth_blur(self.image, self.depth, matte, 0.1, 0.5, 1.4)
        outside = widened < 0.5
        self.assertTrue(outside[:, SIZE - 8:].all())
        np.testing.assert_array_equal(out[outside], self.image[outside])

    def test_key_colour_does_not_bleed_into_the_figure(self):
        image = np.zeros((SIZE, SIZE, 3), np.uint8)
        image[...] = (0, 255, 0)
        image[:, :SIZE // 2] = (255, 0, 0)
        matte = np.zeros((SIZE, SIZE), np.float32)
        matte[:, :SIZE // 2] = 1.0
        depth = np.zeros((SIZE, SIZE), np.float32)
        depth[:, :SIZE // 4] = 1.0
        out, widened = depth_blur(image, depth, matte, 0.9, 0.5, 1.0)
        figure = widened > 0.5
        excess = out[..., 1].astype(int) - out[..., 2].astype(int)
        self.assertLessEqual(int(excess[figure].max()), 1)
        np.testing.assert_array_equal(out[~figure], image[~figure])

    def test_out_of_focus_silhouette_fades_into_paper(self):
        image = np.zeros((SIZE, SIZE, 3), np.uint8)
        image[...] = (0, 255, 0)
        image[:, :SIZE // 2] = (255, 0, 0)
        matte = np.zeros((SIZE, SIZE), np.float32)
        matte[:, :SIZE // 2] = 1.0
        depth = np.zeros((SIZE, SIZE), np.float32)
        depth[:, :SIZE // 4] = 1.0
        out, widened = depth_blur(image, depth, matte, 0.1, 0.5, 0.7)
        edge = SIZE // 2 + 1
        self.assertEqual(float(widened[0, edge]), 1.0)
        self.assertGreater(int(out[0, edge, 1]), 100)
        self.assertGreater(int(out[0, edge, 0]), int(out[0, edge, 1]))
        self.assertLess(int(out[0, SIZE // 2 - 2, 1]), int(out[0, edge, 1]))

    def test_in_focus_silhouette_keeps_its_matte(self):
        image = np.zeros((SIZE, SIZE, 3), np.uint8)
        image[:, :SIZE // 2] = (255, 0, 0)
        matte = np.zeros((SIZE, SIZE), np.float32)
        matte[:, :SIZE // 2] = 1.0
        depth = np.zeros((SIZE, SIZE), np.float32)
        depth[:, :SIZE // 4] = 1.0
        _, widened = depth_blur(image, depth, matte, 0.45, 0.5, 0.7)
        self.assertEqual(float(widened[0, SIZE // 2 + 1]), 0.0)

    def test_flat_depth_returns_the_image(self):
        out = blurred(self.image, np.zeros_like(self.depth), self.matte,
                         0.5, 0.5, 1.0)
        np.testing.assert_array_equal(out, self.image)


def base_graph() -> dict:
    return {
        "3": {"class_type": "KSampler",
              "inputs": {"seed": 7, "positive": ["6", 0], "negative": ["7", 0]}},
        "4": {"class_type": "DiffusersLoader", "inputs": {}},
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"width": 832, "height": 1664}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "p"}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "n"}},
        "8": {"class_type": "VAEDecode",
              "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0], "filename_prefix": "base"}},
    }


DOF = ((0.82, 0.55), 2.8)


def find(graph: dict, class_type: str) -> tuple[str, dict]:
    matches = [(key, node) for key, node in graph.items()
               if node.get("class_type") == class_type]
    assert len(matches) == 1, class_type
    return matches[0]


class DepthBlurGraphTest(unittest.TestCase):
    def assert_blur_between_repin_and_deliver(self, graph: dict) -> None:
        repin_id, _ = find(graph, "YukariRepin")
        depth_id, depth = find(graph, DEPTH_NODE)
        blur_id, blur = find(graph, "YukariDepthBlur")
        _, deliver = find(graph, "YukariDeliver")
        self.assertEqual(depth["inputs"]["ckpt_name"], DEPTH_CKPT)
        self.assertEqual(depth["inputs"]["image"], [repin_id, 0])
        self.assertEqual(blur["inputs"]["image"], [repin_id, 0])
        self.assertEqual(blur["inputs"]["depth"], [depth_id, 0])
        self.assertEqual(deliver["inputs"]["matte"], [blur_id, 1])
        self.assertEqual(
            (blur["inputs"]["focus_x"], blur["inputs"]["focus_y"],
             blur["inputs"]["f_number"]), (0.82, 0.55, 2.8))
        self.assertEqual(deliver["inputs"]["image"], [blur_id, 0])

    def test_redraw_route(self):
        graph = chain_pass(base_graph(), 2048, 0.45, "fin", canvas=(832, 1664),
                           matte_model="birefnet", deliver=True, repin=True,
                           dof=DOF)
        self.assert_blur_between_repin_and_deliver(graph)

    def test_deliver_only_route(self):
        graph = chain_pass(base_graph(), 2048, 0.45, "fin", canvas=(832, 1664),
                           matte_model="birefnet", deliver=True, repin=True,
                           deliver_only=True, source_image="src.png", dof=DOF)
        self.assert_blur_between_repin_and_deliver(graph)

    def test_without_dof_the_graph_is_unchanged(self):
        for deliver_only in (False, True):
            kwargs = dict(canvas=(832, 1664), matte_model="birefnet",
                          deliver=True, repin=True, deliver_only=deliver_only,
                          source_image="src.png")
            plain = chain_pass(base_graph(), 2048, 0.45, "fin", **kwargs)
            explicit = chain_pass(base_graph(), 2048, 0.45, "fin", dof=None, **kwargs)
            self.assertEqual(plain, explicit)
            classes = {node.get("class_type") for node in plain.values()}
            self.assertNotIn("YukariDepthBlur", classes)
            self.assertNotIn(DEPTH_NODE, classes)


if __name__ == "__main__":
    unittest.main()
