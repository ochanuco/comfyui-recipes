from __future__ import annotations

import unittest

import prompt_lint

from comfyui_recipes.domain.yukari.recipe import negative, positive


class PromptLintScriptTest(unittest.TestCase):
    def test_request_prompts_use_overrides_with_recipe_fallbacks(self):
        request = {"generation": {
            "parameters": {"pose": "lounge", "costume": "roomwear"},
            "prompt": "explicit positive",
        }}
        actual_positive, actual_negative = prompt_lint.request_prompts(request)
        self.assertEqual(actual_positive, "explicit positive")
        self.assertEqual(actual_negative, negative("lounge", "roomwear"))

        request["generation"]["negative_prompt"] = "explicit negative"
        del request["generation"]["prompt"]
        actual_positive, actual_negative = prompt_lint.request_prompts(request)
        self.assertEqual(actual_positive, positive("lounge", "roomwear"))
        self.assertEqual(actual_negative, "explicit negative")


if __name__ == "__main__":
    unittest.main()
