"""Tests for turning a request row's JSON `options` into use-case kwargs."""

from __future__ import annotations

import unittest

from comfyui_recipes.application.finalize import RECIPE_DEFAULT
from comfyui_recipes.application.request_options import (
    finalize_arguments,
    masked_redraw_arguments,
    repair_arguments,
)
from comfyui_recipes.domain.repair.controlnet import DEFAULT_CONTROL_STRENGTH
from comfyui_recipes.domain.repair.loras import DEFAULT_PART_LORA_WEIGHT

# Synthetic dial vocabularies for exercising resolve_dial()'s word lookup --
# not any recipe's own published words.
_FINALIZE_DIALS = {
    "denoise": {"keep": 0.45, "tidy": 0.65, "redraw": 0.8},
    "keep_legwear": {"on": 0.62},
    "repair_lora": {"on": DEFAULT_PART_LORA_WEIGHT},
    "repair_denoise": {"keep": 0.6},
}
_REPAIR_DIALS = {
    "denoise": {"keep": 0.6},
    "lora": {"on": DEFAULT_PART_LORA_WEIGHT},
}
_DENOISE_ONLY_DIALS = {"denoise": {"keep": 0.45}}


class FinalizeArgumentsTest(unittest.TestCase):
    def test_defaults_are_false_and_null(self):
        arguments = finalize_arguments({})
        self.assertEqual(arguments, {
            "denoise": None, "apply_repin": RECIPE_DEFAULT,
            "apply_skin": False, "apply_recolor": False, "keep_legwear": None,
            "size": None, "deliver_size": None,
            "latent_route": None,
            "finalizer": None, "keep_scene": False, "transparent": None,
            "backdrop": RECIPE_DEFAULT, "upscale": None,
            "stroke_light": RECIPE_DEFAULT,
            "repair": None, "repair_regions": [], "repair_denoise": 0.6,
            "repair_pad": 1.0, "repair_size": None, "repair_lora": None,
            "repair_seeds": None,
            "keep_regions": [], "keep_strength": 0.25,
            "deliver_only": RECIPE_DEFAULT,
        })

    def test_repin_absent_resolves_to_the_recipe_default_sentinel(self):
        self.assertIs(finalize_arguments({})["apply_repin"], RECIPE_DEFAULT)

    def test_repin_present_false_passes_through(self):
        self.assertIs(finalize_arguments({"repin": False})["apply_repin"], False)

    def test_deliver_only_absent_resolves_to_the_recipe_default_sentinel(self):
        self.assertIs(finalize_arguments({})["deliver_only"], RECIPE_DEFAULT)

    def test_deliver_only_present_false_passes_through(self):
        self.assertIs(finalize_arguments({"deliver_only": False})["deliver_only"], False)

    def test_deliver_only_true_is_validated_as_a_boolean(self):
        self.assertIs(finalize_arguments({"deliver_only": True})["deliver_only"], True)

    def test_deliver_only_rejects_a_non_boolean(self):
        with self.assertRaisesRegex(ValueError, "deliver_only"):
            finalize_arguments({"deliver_only": "yes"})

    def test_backdrop_absent_resolves_to_the_recipe_default_sentinel(self):
        self.assertIs(finalize_arguments({})["backdrop"], RECIPE_DEFAULT)

    def test_backdrop_explicit_null_passes_through(self):
        self.assertIsNone(finalize_arguments({"backdrop": None})["backdrop"])

    def test_backdrop_hex_colour_passes_through(self):
        self.assertEqual(
            finalize_arguments({"backdrop": "#ffffff"})["backdrop"], "#ffffff")

    def test_backdrop_a_named_colour_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "backdrop"):
            finalize_arguments({"backdrop": "white"})

    def test_backdrop_a_pattern_name_is_accepted(self):
        self.assertEqual(
            finalize_arguments({"backdrop": "stripes"})["backdrop"], "stripes")

    def test_backdrop_an_unknown_pattern_name_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "backdrop"):
            finalize_arguments({"backdrop": "plaid"})

    def test_backdrop_c7e5e9_colour_is_still_accepted(self):
        self.assertEqual(
            finalize_arguments({"backdrop": "#c7e5e9"})["backdrop"], "#c7e5e9")

    def test_upscale_null_passes_through(self):
        self.assertIsNone(finalize_arguments({})["upscale"])

    def test_upscale_a_known_method_passes_through(self):
        self.assertEqual(
            finalize_arguments({"upscale": "nearest-exact"})["upscale"],
            "nearest-exact")

    def test_upscale_an_unknown_method_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "upscale"):
            finalize_arguments({"upscale": "mitchell"})

    def test_keep_legwear_true_becomes_default_cut(self):
        self.assertEqual(finalize_arguments({"keep_legwear": True})["keep_legwear"], 0.62)

    def test_stroke_light_absent_resolves_to_the_recipe_default_sentinel(self):
        self.assertIs(finalize_arguments({})["stroke_light"], RECIPE_DEFAULT)

    def test_stroke_light_explicit_null_passes_through(self):
        self.assertIsNone(finalize_arguments({"stroke_light": None})["stroke_light"])

    def test_stroke_light_a_known_key_passes_through(self):
        self.assertEqual(
            finalize_arguments({"stroke_light": "ne"})["stroke_light"], "ne")

    def test_stroke_light_an_unknown_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "stroke_light"):
            finalize_arguments({"stroke_light": "north"})

    def test_stroke_light_a_boolean_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "stroke_light"):
            finalize_arguments({"stroke_light": True})

    def test_deliver_size_null_passes_through(self):
        self.assertIsNone(finalize_arguments({})["deliver_size"])

    def test_deliver_size_an_integer_passes_through(self):
        self.assertEqual(
            finalize_arguments({"deliver_size": 1536})["deliver_size"], 1536)

    def test_deliver_size_a_boolean_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "deliver_size"):
            finalize_arguments({"deliver_size": True})

    def test_deliver_size_a_string_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "deliver_size"):
            finalize_arguments({"deliver_size": "1536"})

    def test_deliver_size_zero_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "deliver_size"):
            finalize_arguments({"deliver_size": 0})

    def test_keep_legwear_number_passes_through(self):
        self.assertEqual(finalize_arguments({"keep_legwear": 0.4})["keep_legwear"], 0.4)

    def test_route_pixel_forces_latent_route_false(self):
        self.assertIs(finalize_arguments({"route": "pixel"})["latent_route"], False)

    def test_route_latent_forces_latent_route_true(self):
        self.assertIs(finalize_arguments({"route": "latent"})["latent_route"], True)

    def test_booleans_and_size_and_finalizer_pass_through(self):
        arguments = finalize_arguments({
            "repin": True, "recolor": True, "skin": True,
            "keep_scene": True, "size": 2048, "finalizer": "some-model",
            "denoise": 0.5, "transparent": True,
        })
        self.assertEqual(arguments["apply_repin"], True)
        self.assertEqual(arguments["apply_recolor"], True)
        self.assertEqual(arguments["apply_skin"], True)
        self.assertEqual(arguments["keep_scene"], True)
        self.assertEqual(arguments["size"], 2048)
        self.assertEqual(arguments["finalizer"], "some-model")
        self.assertEqual(arguments["denoise"], 0.5)
        self.assertIs(arguments["transparent"], True)

    def test_transparent_false_passes_through(self):
        self.assertIs(finalize_arguments({"transparent": False})["transparent"], False)

    def test_repair_null_passes_through(self):
        self.assertIsNone(finalize_arguments({})["repair"])

    def test_repair_parts_pass_through(self):
        self.assertEqual(
            finalize_arguments({"repair": ["hands", "feet"]})["repair"],
            ["hands", "feet"])

    def test_repair_empty_list_passes_through(self):
        self.assertEqual(finalize_arguments({"repair": []})["repair"], [])

    def test_repair_unknown_part_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "repair"):
            finalize_arguments({"repair": ["elbows"]})

    def test_repair_regions_default_empty(self):
        self.assertEqual(finalize_arguments({})["repair_regions"], [])

    def test_repair_regions_pass_through(self):
        self.assertEqual(
            finalize_arguments({"repair_regions": [[0.1, 0.2, 0.3, 0.4]]})["repair_regions"],
            [[0.1, 0.2, 0.3, 0.4]])

    def test_repair_regions_out_of_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "region"):
            finalize_arguments({"repair_regions": [[0, 0, 1, 1.5]]})

    def test_repair_denoise_default(self):
        self.assertEqual(finalize_arguments({})["repair_denoise"], 0.6)

    def test_repair_denoise_out_of_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "repair_denoise"):
            finalize_arguments({"repair_denoise": 1.5})

    def test_repair_pad_default(self):
        self.assertEqual(finalize_arguments({})["repair_pad"], 1.0)

    def test_repair_pad_out_of_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "repair_pad"):
            finalize_arguments({"repair_pad": 4})

    def test_repair_size_default(self):
        # `None` (the option omitted) reaches finalize() as its own "caller
        # omitted this" sentinel -- see repair_seeds below for the analogous
        # case.
        self.assertIsNone(finalize_arguments({})["repair_size"])

    def test_repair_seeds_default(self):
        self.assertIsNone(finalize_arguments({})["repair_seeds"])

    def test_repair_seeds_out_of_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "repair_seeds"):
            finalize_arguments({"repair_seeds": 9})
        with self.assertRaisesRegex(ValueError, "repair_seeds"):
            finalize_arguments({"repair_seeds": 0})

    def test_repair_seeds_accepts_the_full_range(self):
        for value in (1, 8):
            with self.subTest(value=value):
                self.assertEqual(
                    finalize_arguments({"repair_seeds": value})["repair_seeds"], value)

    def test_repair_seeds_must_be_an_integer(self):
        with self.assertRaisesRegex(ValueError, "repair_seeds"):
            finalize_arguments({"repair_seeds": 2.5})

    def test_repair_size_not_a_multiple_of_8_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "repair_size"):
            finalize_arguments({"repair_size": 1001})

    def test_repair_regions_allowed_without_repair_parts(self):
        arguments = finalize_arguments({"repair_regions": [[0.0, 0.0, 0.1, 0.1]]})
        self.assertIsNone(arguments["repair"])
        self.assertEqual(arguments["repair_regions"], [[0.0, 0.0, 0.1, 0.1]])

    def test_repair_lora_default_null(self):
        self.assertIsNone(finalize_arguments({})["repair_lora"])

    def test_repair_lora_true_becomes_the_default_weight(self):
        self.assertEqual(
            finalize_arguments({"repair_lora": True})["repair_lora"],
            DEFAULT_PART_LORA_WEIGHT)

    def test_repair_lora_number_passes_through(self):
        self.assertEqual(
            finalize_arguments({"repair_lora": 0.5})["repair_lora"], 0.5)

    def test_repair_lora_out_of_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "repair_lora"):
            finalize_arguments({"repair_lora": 0})
        with self.assertRaisesRegex(ValueError, "repair_lora"):
            finalize_arguments({"repair_lora": 2.5})

    def test_repair_lora_a_string_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "repair_lora"):
            finalize_arguments({"repair_lora": "on"})

    def test_denoise_word_resolves_through_dials(self):
        dials = _FINALIZE_DIALS
        self.assertEqual(finalize_arguments({"denoise": "tidy"}, dials)["denoise"], 0.65)
        self.assertEqual(finalize_arguments({"denoise": "redraw"}, dials)["denoise"], 0.8)

    def test_denoise_unknown_word_names_the_key_and_word(self):
        dials = _FINALIZE_DIALS
        with self.assertRaises(ValueError) as ctx:
            finalize_arguments({"denoise": "blurry"}, dials)
        self.assertIn("denoise", str(ctx.exception))
        self.assertIn("blurry", str(ctx.exception))

    def test_word_on_a_recipe_with_no_dial_for_that_key_is_rejected(self):
        # A recipe that publishes only a `denoise` dial -- a word for a key
        # it has no vocabulary for fails the same way as an unknown word.
        with self.assertRaisesRegex(ValueError, "keep_legwear"):
            finalize_arguments({"keep_legwear": "on"}, _DENOISE_ONLY_DIALS)

    def test_keep_legwear_word_resolves_to_the_same_constant_as_true(self):
        dials = _FINALIZE_DIALS
        self.assertEqual(finalize_arguments({"keep_legwear": "on"}, dials)["keep_legwear"], 0.62)

    def test_repair_lora_word_resolves_through_dials(self):
        dials = _FINALIZE_DIALS
        self.assertEqual(
            finalize_arguments({"repair_lora": "on"}, dials)["repair_lora"],
            DEFAULT_PART_LORA_WEIGHT)

    def test_repair_denoise_word_resolves_through_dials(self):
        dials = _FINALIZE_DIALS
        self.assertEqual(
            finalize_arguments({"repair_denoise": "keep"}, dials)["repair_denoise"], 0.6)

    def test_keep_regions_default_empty(self):
        self.assertEqual(finalize_arguments({})["keep_regions"], [])

    def test_keep_regions_pass_through_as_floats(self):
        arguments = finalize_arguments({"keep_regions": [[0, 0.25, 1, 0.75]]})
        self.assertEqual(arguments["keep_regions"], [[0.0, 0.25, 1.0, 0.75]])

    def test_keep_regions_out_of_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "region"):
            finalize_arguments({"keep_regions": [[0, 0, 1, 1.5]]})

    def test_keep_strength_default(self):
        self.assertEqual(finalize_arguments({})["keep_strength"], 0.25)

    def test_keep_strength_must_be_strictly_between_zero_and_one(self):
        with self.assertRaisesRegex(ValueError, "keep_strength"):
            finalize_arguments({"keep_strength": 0})
        with self.assertRaisesRegex(ValueError, "keep_strength"):
            finalize_arguments({"keep_strength": 1})

    def test_keep_strength_a_string_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "keep_strength"):
            finalize_arguments({"keep_strength": "0.25"})

    def test_a_number_is_unaffected_by_dials_being_given(self):
        dials = _FINALIZE_DIALS
        self.assertEqual(finalize_arguments({"denoise": 0.7}, dials)["denoise"], 0.7)

    def test_unknown_key_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            finalize_arguments({"nope": True})
        self.assertIn("nope", str(ctx.exception))

    def test_removed_redraw_options_are_rejected_as_unknown(self):
        with self.assertRaises(ValueError) as ctx:
            finalize_arguments({"handdrawn": True, "toe_guard": 1.5})
        message = str(ctx.exception)
        self.assertIn("handdrawn", message)
        self.assertIn("toe_guard", message)

    def test_wrong_type_is_rejected_with_the_offending_key_named(self):
        cases = [
            {"repin": "yes"},
            {"denoise": "0.5"},
            {"keep_legwear": "wide"},
            {"route": "sideways"},
            {"finalizer": 123},
            {"size": 2048.5},
            {"upscale": 123},
            {"transparent": "yes"},
        ]
        for options in cases:
            with self.subTest(options=options), self.assertRaises(ValueError) as ctx:
                finalize_arguments(options)
            key = next(iter(options))
            self.assertIn(key, str(ctx.exception))

    def test_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            finalize_arguments([])


class RepairArgumentsTest(unittest.TestCase):
    def test_defaults(self):
        arguments = repair_arguments({})
        self.assertEqual(arguments, {
            "parts": ["hands", "feet"], "regions": [], "denoise": 0.6,
            "seeds": [1, 2, 3, 4], "size": 1024, "pad": 1.0, "lora": None,
            "model": None,
            "control": None, "control_strength": DEFAULT_CONTROL_STRENGTH,
        })

    def test_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            repair_arguments([])

    def test_unknown_key_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            repair_arguments({"nope": True})
        self.assertIn("nope", str(ctx.exception))

    def test_parts_must_be_hands_or_feet(self):
        with self.assertRaisesRegex(ValueError, "parts"):
            repair_arguments({"parts": ["elbows"]})

    def test_parts_empty_list_is_valid_with_regions(self):
        arguments = repair_arguments({"parts": [], "regions": [[0, 0, 1, 1]]})
        self.assertEqual(arguments["parts"], [])

    def test_parts_and_regions_both_empty_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "parts or regions"):
            repair_arguments({"parts": [], "regions": []})

    def test_regions_must_be_four_numbers_in_0_1(self):
        with self.assertRaisesRegex(ValueError, "region"):
            repair_arguments({"regions": [[0, 0, 1]]})
        with self.assertRaisesRegex(ValueError, "region"):
            repair_arguments({"regions": [[0, 0, 1, 1.5]]})
        with self.assertRaisesRegex(ValueError, "region"):
            repair_arguments({"regions": [["a", 0, 1, 1]]})

    def test_regions_pass_through_as_floats(self):
        arguments = repair_arguments({"regions": [[0, 0.25, 1, 0.75]]})
        self.assertEqual(arguments["regions"], [[0.0, 0.25, 1.0, 0.75]])

    def test_denoise_must_be_in_0_1(self):
        with self.assertRaisesRegex(ValueError, "denoise"):
            repair_arguments({"denoise": 0})
        with self.assertRaisesRegex(ValueError, "denoise"):
            repair_arguments({"denoise": 1.5})
        with self.assertRaisesRegex(ValueError, "denoise"):
            repair_arguments({"denoise": "0.5"})

    def test_denoise_one_is_valid(self):
        self.assertEqual(repair_arguments({"denoise": 1})["denoise"], 1.0)

    def test_seeds_must_be_a_non_empty_list_of_ints(self):
        with self.assertRaisesRegex(ValueError, "seeds"):
            repair_arguments({"seeds": []})
        with self.assertRaisesRegex(ValueError, "seeds"):
            repair_arguments({"seeds": [1.5]})
        with self.assertRaisesRegex(ValueError, "seeds"):
            repair_arguments({"seeds": [True]})

    def test_size_must_be_a_multiple_of_8_at_least_256(self):
        with self.assertRaisesRegex(ValueError, "size"):
            repair_arguments({"size": 200})
        with self.assertRaisesRegex(ValueError, "size"):
            repair_arguments({"size": 1001})
        with self.assertRaisesRegex(ValueError, "size"):
            repair_arguments({"size": 1024.0})

    def test_pad_must_be_between_half_and_three(self):
        with self.assertRaisesRegex(ValueError, "pad"):
            repair_arguments({"pad": 0.4})
        with self.assertRaisesRegex(ValueError, "pad"):
            repair_arguments({"pad": 3.1})

    def test_pad_bounds_are_inclusive(self):
        self.assertEqual(repair_arguments({"pad": 0.5})["pad"], 0.5)
        self.assertEqual(repair_arguments({"pad": 3})["pad"], 3.0)

    def test_lora_default_null(self):
        self.assertIsNone(repair_arguments({})["lora"])

    def test_lora_true_becomes_the_default_weight(self):
        self.assertEqual(
            repair_arguments({"lora": True})["lora"], DEFAULT_PART_LORA_WEIGHT)

    def test_lora_number_passes_through(self):
        self.assertEqual(repair_arguments({"lora": 0.5})["lora"], 0.5)

    def test_lora_out_of_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "lora"):
            repair_arguments({"lora": 0})
        with self.assertRaisesRegex(ValueError, "lora"):
            repair_arguments({"lora": 2.5})

    def test_lora_a_string_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "lora"):
            repair_arguments({"lora": "on"})

    def test_denoise_word_resolves_through_dials(self):
        dials = _REPAIR_DIALS
        self.assertEqual(repair_arguments({"denoise": "keep"}, dials)["denoise"], 0.6)

    def test_lora_word_resolves_through_dials(self):
        dials = _REPAIR_DIALS
        self.assertEqual(
            repair_arguments({"lora": "on"}, dials)["lora"], DEFAULT_PART_LORA_WEIGHT)

    def test_unknown_word_names_the_key_and_word(self):
        dials = _REPAIR_DIALS
        with self.assertRaises(ValueError) as ctx:
            repair_arguments({"denoise": "fuzzy"}, dials)
        self.assertIn("denoise", str(ctx.exception))
        self.assertIn("fuzzy", str(ctx.exception))

    def test_model_default_null(self):
        self.assertIsNone(repair_arguments({})["model"])

    def test_model_passes_through(self):
        self.assertEqual(repair_arguments({"model": "anima"})["model"], "anima")

    def test_unknown_model_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "model"):
            repair_arguments({"model": "nope"})

    def test_control_default_null(self):
        self.assertIsNone(repair_arguments({})["control"])

    def test_control_lineart_passes_through(self):
        self.assertEqual(repair_arguments({"control": "lineart"})["control"], "lineart")

    def test_control_unknown_word_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "control"):
            repair_arguments({"control": "nope"})

    def test_control_not_a_string_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "control"):
            repair_arguments({"control": True})

    def test_control_strength_default(self):
        self.assertEqual(
            repair_arguments({})["control_strength"], DEFAULT_CONTROL_STRENGTH)

    def test_control_strength_number_passes_through(self):
        self.assertEqual(
            repair_arguments({"control_strength": 0.5})["control_strength"], 0.5)

    def test_control_strength_out_of_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "control_strength"):
            repair_arguments({"control_strength": 0})
        with self.assertRaisesRegex(ValueError, "control_strength"):
            repair_arguments({"control_strength": 2.5})


class MaskedRedrawArgumentsTest(unittest.TestCase):
    def _valid(self, **overrides):
        options = {"regions": [[0.1, 0.1, 0.5, 0.5]], "prompt_patch": "a dress"}
        options.update(overrides)
        return options

    def test_defaults(self):
        arguments = masked_redraw_arguments(self._valid())
        self.assertEqual(arguments, {
            "regions": [[0.1, 0.1, 0.5, 0.5]], "prompt_patch": "a dress",
            "denoise": 0.45, "mask_padding": 0.0, "mask_feather": 32.0,
            "size": 1024, "seeds": [1, 2, 3, 4],
        })

    def test_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            masked_redraw_arguments([])

    def test_unknown_key_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            masked_redraw_arguments(self._valid(nope=True))
        self.assertIn("nope", str(ctx.exception))

    def test_regions_empty_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "region"):
            masked_redraw_arguments(self._valid(regions=[]))

    def test_regions_out_of_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "region"):
            masked_redraw_arguments(self._valid(regions=[[0, 0, 1, 1.5]]))

    def test_overlapping_regions_are_not_rejected(self):
        # _regions_argument only validates shape/range; chimera already
        # enforces ordering and non-overlap before the row is queued.
        arguments = masked_redraw_arguments(self._valid(
            regions=[[0.1, 0.1, 0.5, 0.5], [0.2, 0.2, 0.6, 0.6]]))
        self.assertEqual(
            arguments["regions"], [[0.1, 0.1, 0.5, 0.5], [0.2, 0.2, 0.6, 0.6]])

    def test_prompt_patch_empty_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "prompt_patch"):
            masked_redraw_arguments(self._valid(prompt_patch=""))

    def test_prompt_patch_not_a_string_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "prompt_patch"):
            masked_redraw_arguments(self._valid(prompt_patch=1))

    def test_prompt_patch_over_4096_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "prompt_patch"):
            masked_redraw_arguments(self._valid(prompt_patch="x" * 4097))

    def test_prompt_patch_exactly_4096_is_valid(self):
        arguments = masked_redraw_arguments(self._valid(prompt_patch="x" * 4096))
        self.assertEqual(len(arguments["prompt_patch"]), 4096)

    def test_denoise_upper_bound_is_0_75_not_1(self):
        arguments = masked_redraw_arguments(self._valid(denoise=0.75))
        self.assertEqual(arguments["denoise"], 0.75)
        with self.assertRaisesRegex(ValueError, "denoise"):
            masked_redraw_arguments(self._valid(denoise=0.76))

    def test_mask_padding_bounds(self):
        arguments = masked_redraw_arguments(self._valid(mask_padding=512))
        self.assertEqual(arguments["mask_padding"], 512.0)
        with self.assertRaisesRegex(ValueError, "mask_padding"):
            masked_redraw_arguments(self._valid(mask_padding=513))

    def test_mask_feather_bounds(self):
        arguments = masked_redraw_arguments(self._valid(mask_feather=256))
        self.assertEqual(arguments["mask_feather"], 256.0)
        with self.assertRaisesRegex(ValueError, "mask_feather"):
            masked_redraw_arguments(self._valid(mask_feather=257))

    def test_size_must_be_a_multiple_of_8_at_least_256(self):
        arguments = masked_redraw_arguments(self._valid(size=256))
        self.assertEqual(arguments["size"], 256)
        with self.assertRaisesRegex(ValueError, "size"):
            masked_redraw_arguments(self._valid(size=200))
        with self.assertRaisesRegex(ValueError, "size"):
            masked_redraw_arguments(self._valid(size=1001))

    def test_seeds_up_to_16_are_valid_17_is_rejected(self):
        arguments = masked_redraw_arguments(self._valid(seeds=list(range(16))))
        self.assertEqual(len(arguments["seeds"]), 16)
        with self.assertRaisesRegex(ValueError, "seeds"):
            masked_redraw_arguments(self._valid(seeds=list(range(17))))

    def test_seeds_must_be_a_non_empty_list_of_ints(self):
        with self.assertRaisesRegex(ValueError, "seeds"):
            masked_redraw_arguments(self._valid(seeds=[]))
        with self.assertRaisesRegex(ValueError, "seeds"):
            masked_redraw_arguments(self._valid(seeds=[1.5]))
        with self.assertRaisesRegex(ValueError, "seeds"):
            masked_redraw_arguments(self._valid(seeds=[True]))

    def test_denoise_word_resolves_through_the_repair_scope_dials(self):
        dials = _REPAIR_DIALS
        self.assertEqual(
            masked_redraw_arguments(self._valid(denoise="keep"), dials)["denoise"], 0.6)

    def test_unknown_denoise_word_names_the_key_and_word(self):
        dials = _REPAIR_DIALS
        with self.assertRaises(ValueError) as ctx:
            masked_redraw_arguments(self._valid(denoise="blurry"), dials)
        self.assertIn("denoise", str(ctx.exception))
        self.assertIn("blurry", str(ctx.exception))


