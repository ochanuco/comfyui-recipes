"""Unit tests for declarative request-time RenderSpec patches.

Pure domain logic plus one round trip through the ComfyUI graph encoder;
no network.
"""

from __future__ import annotations

import unittest

from comfyui_recipes.domain.generation.patches import (
    Patch,
    apply_patches,
    parse_patches,
)
from comfyui_recipes.domain.yukari.recipe import render_spec
from comfyui_recipes.infrastructure.comfyui.yukari_graph import build, build_graph


def _patch(**fields):
    base = {"target": "prompt.positive", "op": "append", "value": " extra",
            "reason": "test"}
    base.update(fields)
    return base


class ParsePatchesTest(unittest.TestCase):
    def test_rejects_non_list(self):
        with self.assertRaises(ValueError):
            parse_patches({"target": "render.cfg"})

    def test_rejects_non_dict_element(self):
        with self.assertRaises(ValueError):
            parse_patches(["not a dict"])

    def test_rejects_unknown_target(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="prompt.expression")])

    def test_rejects_unknown_key(self):
        with self.assertRaises(ValueError):
            parse_patches([{**_patch(), "extra": "nope"}])

    def test_rejects_missing_reason(self):
        patch = _patch()
        del patch["reason"]
        with self.assertRaises(ValueError):
            parse_patches([patch])

    def test_rejects_empty_reason(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(reason="")])

    def test_rejects_replace_missing_old(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(op="replace", value="new")])

    def test_rejects_remove_with_value(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(op="remove", old="x", value="y")])

    def test_rejects_append_with_old(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(op="append", value="x", old="y")])

    def test_rejects_set_on_text_target(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(op="set", value="x")])

    def test_rejects_append_on_number_target(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.cfg", op="append", value=1)])

    def test_rejects_steps_zero(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.steps", op="set", value=0,
                                  reason="test")])

    def test_rejects_steps_bool(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.steps", op="set", value=True,
                                  reason="test")])

    def test_rejects_denoise_over_one(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="hires.denoise", op="set", value=1.5,
                                  reason="test")])

    def test_rejects_cfg_zero(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.cfg", op="set", value=0,
                                  reason="test")])

    def test_rejects_width_non_int(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.width", op="set",
                                  value=1280.5, reason="test")])

    def test_rejects_width_below_64(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.width", op="set", value=32,
                                  reason="test")])

    def test_rejects_width_not_multiple_of_8(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.width", op="set", value=100,
                                  reason="test")])

    def test_rejects_height_non_int(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.height", op="set",
                                  value=2048.5, reason="test")])

    def test_rejects_height_below_64(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.height", op="set", value=32,
                                  reason="test")])

    def test_rejects_height_not_multiple_of_8(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.height", op="set", value=100,
                                  reason="test")])

    def test_rejects_non_set_op_on_string_target(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.model", op="append",
                                  value="x", reason="test")])

    def test_rejects_empty_string_target_value(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.sampler", op="set", value="",
                                  reason="test")])

    def test_accepts_each_op_as_patch_tuple(self):
        raw = [
            _patch(target="prompt.positive", op="append", value=" a",
                   reason="r1"),
            _patch(target="prompt.negative", op="prepend", value="b ",
                   reason="r2"),
            _patch(target="prompt.hires.positive", op="replace", old="x",
                   value="y", reason="r3"),
            {"target": "prompt.hires.negative", "op": "remove", "old": "z",
             "reason": "r4"},
            _patch(target="render.cfg", op="set", value=4.5, reason="r5"),
            _patch(target="render.steps", op="set", value=20, reason="r6"),
            _patch(target="hires.denoise", op="set", value=0.5, reason="r7"),
        ]
        parsed = parse_patches(raw)
        self.assertEqual(len(parsed), len(raw))
        self.assertTrue(all(isinstance(p, Patch) for p in parsed))
        self.assertEqual(parsed[0], Patch("prompt.positive", "append", " a",
                                          None, "r1"))
        self.assertEqual(parsed[4], Patch("render.cfg", "set", 4.5, None,
                                          "r5"))


class ApplyPatchesTest(unittest.TestCase):
    def setUp(self):
        self.spec = render_spec("lounge", 555666777, "prefix")
        self.hires_spec = render_spec(
            "lounge", 555666777, "prefix", hires=2048)

    def test_append_and_prepend_positive(self):
        patches = parse_patches([
            _patch(target="prompt.positive", op="append", value=" tail",
                   reason="r"),
            _patch(target="prompt.positive", op="prepend", value="head ",
                   reason="r"),
        ])
        result = apply_patches(self.spec, patches)
        self.assertEqual(
            result.prompts.positive,
            "head " + self.spec.prompts.positive + " tail")

    def test_append_negative(self):
        patches = parse_patches([
            _patch(target="prompt.negative", op="append", value=", extra",
                   reason="r")])
        result = apply_patches(self.spec, patches)
        self.assertEqual(
            result.prompts.negative, self.spec.prompts.negative + ", extra")

    def test_replace_existing_needle(self):
        needle = "(pale skin:1.25)"
        self.assertIn(needle, self.spec.prompts.positive)
        patches = parse_patches([
            _patch(target="prompt.positive", op="replace", old=needle,
                   value="(pale skin:1.2)", reason="r")])
        result = apply_patches(self.spec, patches)
        self.assertNotIn(needle, result.prompts.positive)
        self.assertIn("(pale skin:1.2)", result.prompts.positive)

    def test_replace_missing_needle_raises(self):
        patches = parse_patches([
            _patch(target="prompt.positive", op="replace",
                   old="no such text in the prompt", value="x", reason="r")])
        with self.assertRaises(ValueError):
            apply_patches(self.spec, patches)

    def test_remove_missing_needle_raises(self):
        patches = parse_patches([
            {"target": "prompt.negative", "op": "remove",
             "old": "no such text in the prompt", "reason": "r"}])
        with self.assertRaises(ValueError):
            apply_patches(self.spec, patches)

    def test_hires_negative_append(self):
        patches = parse_patches([
            _patch(target="prompt.hires.negative", op="append", value=", x",
                   reason="r")])
        result = apply_patches(self.hires_spec, patches)
        self.assertEqual(
            result.hires.negative, self.hires_spec.hires.negative + ", x")

    def test_hires_positive_materializes_from_patched_pass1(self):
        self.assertIsNone(self.hires_spec.hires.positive)
        patches = parse_patches([
            _patch(target="prompt.positive", op="append", value=" pass1tail",
                   reason="r"),
            _patch(target="prompt.hires.positive", op="append",
                   value=" pass2tail", reason="r"),
        ])
        result = apply_patches(self.hires_spec, patches)
        expected = self.hires_spec.prompts.positive + " pass1tail pass2tail"
        self.assertEqual(result.hires.positive, expected)

    def test_hires_targets_require_hires_spec(self):
        for patch_dict in (
            _patch(target="prompt.hires.positive", op="append", value=" x",
                  reason="r"),
            _patch(target="prompt.hires.negative", op="append", value=" x",
                  reason="r"),
            _patch(target="hires.denoise", op="set", value=0.5, reason="r"),
        ):
            with self.subTest(patch_dict=patch_dict):
                patches = parse_patches([patch_dict])
                with self.assertRaises(ValueError):
                    apply_patches(self.spec, patches)

    def test_number_sets(self):
        patches = parse_patches([
            _patch(target="render.cfg", op="set", value=4.5, reason="r"),
            _patch(target="render.steps", op="set", value=20, reason="r"),
            _patch(target="hires.denoise", op="set", value=0.4, reason="r"),
        ])
        result = apply_patches(self.hires_spec, patches)
        self.assertEqual(result.cfg, 4.5)
        self.assertEqual(result.steps, 20)
        self.assertEqual(result.hires.denoise, 0.4)

    def test_string_sets(self):
        patches = parse_patches([
            _patch(target="render.model", op="set", value="other.safetensors",
                  reason="r"),
            _patch(target="render.sampler", op="set", value="euler",
                  reason="r"),
            _patch(target="render.scheduler", op="set", value="normal",
                  reason="r"),
        ])
        result = apply_patches(self.spec, patches)
        self.assertEqual(result.model_path, "other.safetensors")
        self.assertEqual(result.sampler_name, "euler")
        self.assertEqual(result.scheduler, "normal")

    def test_width_and_height_sets(self):
        patches = parse_patches([
            _patch(target="render.width", op="set", value=1280, reason="r"),
            _patch(target="render.height", op="set", value=2048, reason="r"),
        ])
        result = apply_patches(self.spec, patches)
        self.assertEqual(result.width, 1280)
        self.assertEqual(result.height, 2048)

    def test_empty_patches_returns_equal_spec(self):
        result = apply_patches(self.spec, ())
        self.assertEqual(result, self.spec)

    def test_original_spec_is_unchanged(self):
        original_positive = self.spec.prompts.positive
        patches = parse_patches([
            _patch(target="prompt.positive", op="append", value=" tail",
                   reason="r")])
        apply_patches(self.spec, patches)
        self.assertEqual(self.spec.prompts.positive, original_positive)

    def test_encoded_graph_reflects_cfg_and_hires_denoise_patches(self):
        patches = parse_patches([
            _patch(target="render.cfg", op="set", value=4.5, reason="r"),
            _patch(target="hires.denoise", op="set", value=0.4, reason="r"),
        ])
        patched = apply_patches(self.hires_spec, patches)
        graph = build_graph(patched)
        self.assertEqual(graph["3"]["inputs"]["cfg"], 4.5)
        self.assertEqual(graph["11"]["inputs"]["denoise"], 0.4)

    def test_unpatched_encoding_matches_legacy_builder(self):
        spec = render_spec("lounge", 555666777, "prefix")
        patched = apply_patches(spec, parse_patches([]))
        self.assertEqual(
            build_graph(patched), build("lounge", 555666777, "prefix"))


if __name__ == "__main__":
    unittest.main()
