from __future__ import annotations

import unittest

import numpy as np

from comfyui_recipes.domain.yukari import delivery_style
from comfyui_recipes.infrastructure.imaging.backdrops import (
    PATTERNS,
    is_backdrop,
    render,
    stripes,
)
from comfyui_recipes.infrastructure.imaging.delivery import parse_color


class StripesTest(unittest.TestCase):
    def test_shape_and_range(self):
        img = stripes(64, 48)
        self.assertEqual(img.shape, (64, 48, 3))
        self.assertTrue((img >= 0).all())
        self.assertTrue((img <= 255).all())

    def test_deterministic(self):
        np.testing.assert_array_equal(stripes(40, 40), stripes(40, 40))

    def test_not_flat(self):
        img = stripes(64, 64)
        self.assertGreater(float(img.std()), 0.0)


class RenderTest(unittest.TestCase):
    def test_none_matches_the_flat_default_backdrop(self):
        img = render(None, 10, 12)
        expected = np.array(parse_color(delivery_style.BACKDROP), dtype=float)
        self.assertTrue((img == expected).all())

    def test_a_hex_colour_is_flat(self):
        img = render("#ff0000", 10, 12)
        self.assertTrue((img == np.array([255.0, 0.0, 0.0])).all())

    def test_a_pattern_key_dispatches_to_its_function(self):
        np.testing.assert_array_equal(render("stripes", 20, 24), stripes(20, 24))

    def test_an_unknown_name_raises(self):
        with self.assertRaises(SystemExit):
            render("plaid", 10, 10)

    def test_shape_is_always_height_width_three(self):
        for backdrop in (None, "#112233", "stripes"):
            self.assertEqual(render(backdrop, 5, 7).shape, (5, 7, 3))


class IsBackdropTest(unittest.TestCase):
    def test_a_pattern_key_is_valid(self):
        self.assertTrue(is_backdrop("stripes"))

    def test_a_hex_colour_is_valid(self):
        self.assertTrue(is_backdrop("#c7e5e9"))

    def test_an_unknown_name_is_invalid(self):
        self.assertFalse(is_backdrop("plaid"))

    def test_patterns_registry_holds_stripes(self):
        self.assertEqual(set(PATTERNS), {"stripes"})


if __name__ == "__main__":
    unittest.main()
