"""Unit tests for declarative request-time RenderSpec patches.

Pure domain logic plus one round trip through the ComfyUI graph encoder;
no network.
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from comfyui_recipes.domain.generation.patches import (
    Patch,
    apply_patches,
    parse_patches,
)
from comfyui_recipes.domain.yukari.recipe import render_spec
from comfyui_recipes.domain.yukari_anima.recipe import render_spec as anima_render_spec
from comfyui_recipes.domain.yukari_sketch.recipe import render_spec as sketch_render_spec
from comfyui_recipes.infrastructure.comfyui import anima_graph
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

    def test_rejects_layerdiffuse_weight_below_range(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.layerdiffuse_weight",
                                  op="set", value=-1.5, reason="test")])

    def test_rejects_layerdiffuse_weight_above_range(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.layerdiffuse_weight",
                                  op="set", value=3.5, reason="test")])

    def test_rejects_lora_strength_below_range(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.lora_strength", op="set",
                                  value=-0.1, reason="test")])

    def test_rejects_lora_strength_above_range(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.lora_strength", op="set",
                                  value=2.1, reason="test")])

    def test_rejects_layerdiffuse_config_not_in_enum(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.layerdiffuse_config",
                                  op="set", value="bogus", reason="test")])

    def test_accepts_new_number_and_string_targets(self):
        parsed = parse_patches([
            _patch(target="render.layerdiffuse_weight", op="set", value=0.7,
                  reason="r"),
            _patch(target="render.lora_strength", op="set", value=1.1,
                  reason="r"),
            _patch(target="render.layerdiffuse_config", op="set",
                  value="SDXL, Conv Injection", reason="r"),
        ])
        self.assertEqual(parsed[0], Patch("render.layerdiffuse_weight", "set",
                                          0.7, None, "r"))
        self.assertEqual(parsed[1], Patch("render.lora_strength", "set", 1.1,
                                          None, "r"))
        self.assertEqual(parsed[2], Patch("render.layerdiffuse_config", "set",
                                          "SDXL, Conv Injection", None, "r"))

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

    def test_number_target_word_resolves_through_dials(self):
        dials = {"render.lora_strength": {"recipe": 0.8, "raw": 1.5}}
        parsed = parse_patches([_patch(
            target="render.lora_strength", op="set", value="raw",
            reason="r")], dials)
        self.assertEqual(parsed[0], Patch("render.lora_strength", "set", 1.5,
                                          None, "r"))

    def test_number_target_unknown_word_names_the_word(self):
        dials = {"render.lora_strength": {"recipe": 0.8, "raw": 1.5}}
        with self.assertRaisesRegex(ValueError, "punchy"):
            parse_patches([_patch(
                target="render.lora_strength", op="set", value="punchy",
                reason="r")], dials)

    def test_number_target_word_with_no_dials_for_that_target_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(
                target="render.lora_strength", op="set", value="raw",
                reason="r")])

    def test_number_target_word_still_enforces_its_own_range(self):
        dials = {"render.lora_strength": {"blown_out": 5.0}}
        with self.assertRaises(ValueError):
            parse_patches([_patch(
                target="render.lora_strength", op="set", value="blown_out",
                reason="r")], dials)

    def test_loras_accepts_a_list_of_name_strength_pairs(self):
        parsed = parse_patches([_patch(
            target="render.loras", op="set",
            value=[["a.safetensors", 0.8], ["b.safetensors", 1.2]],
            reason="r")])
        self.assertEqual(parsed[0], Patch(
            "render.loras", "set",
            (("a.safetensors", 0.8), ("b.safetensors", 1.2)), None, "r"))

    def test_loras_rejects_non_set_op(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(
                target="render.loras", op="append",
                value=[["a.safetensors", 0.8]], reason="r")])

    def test_loras_rejects_empty_list(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(target="render.loras", op="set", value=[],
                                  reason="r")])

    def test_loras_rejects_a_name_not_ending_in_safetensors(self):
        with self.assertRaisesRegex(ValueError, "safetensors"):
            parse_patches([_patch(
                target="render.loras", op="set", value=[["a.ckpt", 0.8]],
                reason="r")])

    def test_loras_rejects_an_empty_name(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(
                target="render.loras", op="set", value=[["", 0.8]], reason="r")])

    def test_loras_rejects_a_strength_out_of_range(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(
                target="render.loras", op="set",
                value=[["a.safetensors", 2.1]], reason="r")])
        with self.assertRaises(ValueError):
            parse_patches([_patch(
                target="render.loras", op="set",
                value=[["a.safetensors", -0.1]], reason="r")])

    def test_loras_rejects_a_pair_that_is_not_length_two(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(
                target="render.loras", op="set",
                value=[["a.safetensors"]], reason="r")])


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

    def test_layerdiffuse_weight_and_config_sets(self):
        patches = parse_patches([
            _patch(target="render.layerdiffuse_weight", op="set", value=0.7,
                  reason="r"),
            _patch(target="render.layerdiffuse_config", op="set",
                  value="SDXL, Conv Injection", reason="r"),
        ])
        result = apply_patches(self.spec, patches)
        self.assertEqual(result.layerdiffuse_weight, 0.7)
        self.assertEqual(result.layerdiffuse_config, "SDXL, Conv Injection")

    def test_lora_strength_set_updates_every_lora_entry(self):
        spec = replace(self.spec, loras=(("a.safetensors", 0.5),
                                         ("b.safetensors", 0.7)))
        patches = parse_patches([
            _patch(target="render.lora_strength", op="set", value=1.1,
                  reason="r")])
        result = apply_patches(spec, patches)
        self.assertEqual(result.loras, (("a.safetensors", 1.1),
                                        ("b.safetensors", 1.1)))

    def test_lora_strength_without_loras_raises(self):
        patches = parse_patches([
            _patch(target="render.lora_strength", op="set", value=1.0,
                  reason="r")])
        with self.assertRaises(ValueError):
            apply_patches(self.spec, patches)

    def test_loras_replaces_spec_loras(self):
        spec = replace(self.spec, loras=(("a.safetensors", 0.5),))
        patches = parse_patches([_patch(
            target="render.loras", op="set",
            value=[["c.safetensors", 0.9], ["d.safetensors", 1.4]],
            reason="r")])
        result = apply_patches(spec, patches)
        self.assertEqual(result.loras, (("c.safetensors", 0.9),
                                        ("d.safetensors", 1.4)))

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

    def test_render_loras_patch_encodes_a_lora_loader_model_only_chain(self):
        spec = anima_render_spec("coffee", 7, "prefix")
        patches = parse_patches([_patch(
            target="render.loras", op="set",
            value=[["anima-sketch-style-chosen.safetensors", 0.8]],
            reason="r")])
        patched = apply_patches(spec, patches)
        graph = anima_graph.build_graph(patched)
        loader_ids = [node_id for node_id, node in graph.items()
                     if node.get("class_type") == "LoraLoaderModelOnly"]
        self.assertEqual(len(loader_ids), 1)
        self.assertEqual(
            graph[loader_ids[0]]["inputs"],
            {"model": ["1", 0],
             "lora_name": "anima-sketch-style-chosen.safetensors",
             "strength_model": 0.8})
        self.assertEqual(graph["3"]["inputs"]["model"], [loader_ids[0], 0])


class PartTargetPatchTest(unittest.TestCase):
    def setUp(self):
        self.sketch_spec = sketch_render_spec("cinema", 7, "prefix")
        self.anima_spec = anima_render_spec("coffee", 7, "prefix")
        self.yukari_spec = render_spec("lounge", 555666777, "prefix")

    def test_parts_join_back_into_the_whole_positive(self):
        joined = "".join(text for _, text in self.sketch_spec.positive_parts)
        self.assertEqual(joined, self.sketch_spec.prompts.positive)
        joined = "".join(text for _, text in self.anima_spec.positive_parts)
        self.assertEqual(joined, self.anima_spec.prompts.positive)

    def test_yukari_has_no_parts(self):
        self.assertEqual(self.yukari_spec.positive_parts, ())

    def test_append_edits_only_the_named_part(self):
        patches = parse_patches([_patch(
            target="prompt.positive.background", op="append",
            value="(overcast:1.1), ", reason="r")])
        result = apply_patches(self.sketch_spec, patches)
        parts = dict(result.positive_parts)
        self.assertTrue(parts["background"].endswith("(overcast:1.1), "))
        for name, text in dict(self.sketch_spec.positive_parts).items():
            if name != "background":
                self.assertEqual(parts[name], text)
        self.assertEqual(
            result.prompts.positive,
            "".join(text for _, text in result.positive_parts))

    def test_replace_and_remove_keep_separators_clean(self):
        patches = parse_patches([_patch(
            target="prompt.positive.face", op="replace",
            old="(tareme:1.2)", value="(tareme:1.3)", reason="r")])
        result = apply_patches(self.sketch_spec, patches)
        self.assertIn("(tareme:1.3), (half-closed eyes:1.2)",
                      result.prompts.positive)
        self.assertNotIn(",,", result.prompts.positive)
        self.assertNotIn("  ", result.prompts.positive)

        patches = parse_patches([
            {"target": "prompt.positive.mood", "op": "remove",
             "old": "(excited:1.1), ", "reason": "r"}])
        result = apply_patches(anima_render_spec("cinema", 7, "p"), patches)
        self.assertNotIn("(excited:1.1)", result.prompts.positive)
        self.assertNotIn(", , ", result.prompts.positive)
        self.assertNotIn(",,", result.prompts.positive)

    def test_prepend_to_a_part(self):
        patches = parse_patches([_patch(
            target="prompt.positive.mouth", op="prepend",
            value="(grin:1.1), ", reason="r")])
        result = apply_patches(self.anima_spec, patches)
        self.assertTrue(dict(result.positive_parts)["mouth"]
                        .startswith("(grin:1.1), "))

    def test_unknown_part_raises_and_names_the_valid_parts(self):
        patches = parse_patches([_patch(
            target="prompt.positive.nope", op="append", value="x",
            reason="r")])
        with self.assertRaises(ValueError) as ctx:
            apply_patches(self.sketch_spec, patches)
        message = str(ctx.exception)
        self.assertIn("quality", message)
        self.assertIn("finish", message)

    def test_part_target_on_a_recipe_without_parts_raises(self):
        patches = parse_patches([_patch(
            target="prompt.positive.face", op="append", value="x",
            reason="r")])
        with self.assertRaises(ValueError):
            apply_patches(self.yukari_spec, patches)

    def test_dotted_sub_part_is_an_unknown_target(self):
        with self.assertRaises(ValueError):
            parse_patches([_patch(
                target="prompt.positive.face.extra", op="append",
                value="x", reason="r")])

    def test_replace_missing_needle_in_a_part_raises(self):
        patches = parse_patches([_patch(
            target="prompt.positive.face", op="replace",
            old="no such text here", value="x", reason="r")])
        with self.assertRaises(ValueError):
            apply_patches(self.sketch_spec, patches)


if __name__ == "__main__":
    unittest.main()
