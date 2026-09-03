from __future__ import annotations

import unittest

from comfyui_recipes.domain.generation.models import PromptPair
from comfyui_recipes.domain.yukari.prompt_style import (
    DOT_BAN,
    HAND_BAN,
    HANDDRAWN_FINISH,
    SHADE_BAN,
    SURFACE,
    THIN,
)
from comfyui_recipes.domain.yukari.recipe import refinement_prompt, render_spec


class YukariRecipeDomainTest(unittest.TestCase):
    def test_refinement_prompt_owns_finish_and_negative_guards(self):
        base = PromptPair("subject, " + THIN, "base negative")
        prompt = refinement_prompt(base, handdrawn=True)
        self.assertNotIn(THIN, prompt.positive)
        self.assertTrue(prompt.positive.endswith(HANDDRAWN_FINISH))
        self.assertEqual(
            prompt.negative, HAND_BAN + SHADE_BAN + DOT_BAN + "base negative")

        guarded = refinement_prompt(base, toe_guard=1.55)
        self.assertEqual(
            guarded.negative,
            "(toes:1.55), " + HAND_BAN + SHADE_BAN + DOT_BAN + "base negative")

        barefoot = refinement_prompt(PromptPair("barefoot", "negative"),
                                     toe_guard=1.55)
        self.assertEqual(barefoot.negative,
                         HAND_BAN + SHADE_BAN + DOT_BAN + "negative")

    def test_refinement_prompt_drops_pass1_only_tags(self):
        prompt = refinement_prompt(
            PromptPair("a, sketch, (rough lines:1.2), b", "n"))
        self.assertEqual(prompt.positive, "a, b")
        self.assertEqual(prompt.negative, HAND_BAN + SHADE_BAN + DOT_BAN + "n")

    def test_hires_dimensions_must_be_at_least_one_latent_pixel(self):
        for hires in (-8, 1):
            with self.subTest(hires=hires), self.assertRaises(ValueError):
                render_spec("lounge", 42, "test", hires=hires)
        self.assertIsNone(render_spec("lounge", 42, "test").hires)

    def test_surface_carries_no_outline_tag(self):
        # The die-cut edge is drawn by the delivery now; a tag creeping back
        # in here would draw it twice without either side noticing.
        self.assertNotIn("outline", SURFACE)


if __name__ == "__main__":
    unittest.main()
