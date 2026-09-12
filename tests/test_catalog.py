"""Tests for the published recipe catalog.

All collaborators are fakes or pure functions: this suite never opens a
network socket.
"""

from __future__ import annotations

import re
import unittest

from comfyui_recipes.application.catalog import build_catalog, publish_catalog
from comfyui_recipes.application.generate import validate_request
from comfyui_recipes.application.work import (
    _KNOWN_FINALIZE_OPTIONS,
    _KNOWN_REPAIR_OPTIONS,
    finalize_arguments,
    repair_arguments,
)
from comfyui_recipes.domain.generation.patches import (
    NUMBER_TARGETS,
    STRING_TARGETS,
    TEXT_TARGETS,
    parse_patches,
)

GIT = {"commit": "abc123", "branch": "dev/catalog-publish", "dirty": False}

_DIAL_WORD = re.compile(r"^[a-z][a-z0-9-]*$")

# scope -> the real option/target keys a dial in that scope may name.
_DIAL_SCOPE_KEYS = {
    "finalize": _KNOWN_FINALIZE_OPTIONS,
    "repair": _KNOWN_REPAIR_OPTIONS,
    "patches": set(NUMBER_TARGETS),
}


def _request(recipe: str, parameters: dict) -> dict:
    return {
        "schema_version": 1,
        "request": {"count": 1, "instruction": "test"},
        "generation": {"recipe": recipe, "parameters": parameters},
        "semantic": {"summary": "test arm"},
    }


# One legal dummy value per KNOWN_PARAMETERS key, used to probe whether
# validate_request accepts or rejects it for a given recipe.
_DUMMY_VALUES = {
    "hires": 1024, "denoise": 0.5, "costume": "default", "character": "yukari",
    "character_id": "char-1", "arm": "a", "expression": "doya",
    "layerdiffuse": True,
}


class BuildCatalogTest(unittest.TestCase):
    def test_schema_version_and_git_metadata(self):
        catalog = build_catalog(GIT)
        self.assertEqual(catalog["schema_version"], 1)
        self.assertEqual(catalog["git_commit"], "abc123")
        self.assertEqual(catalog["git_branch"], "dev/catalog-publish")
        self.assertIs(catalog["git_dirty"], False)
        self.assertIn("generated_at", catalog)

    def test_is_pure_and_takes_no_io(self):
        # Calling twice must not raise and must agree on everything but the
        # timestamp -- build_catalog does no I/O of its own.
        first = build_catalog(GIT)
        second = build_catalog(GIT)
        first.pop("generated_at")
        second.pop("generated_at")
        self.assertEqual(first, second)

    def test_every_recipe_has_every_pose_with_non_empty_prompts_and_canvas(self):
        catalog = build_catalog(GIT)
        names = {recipe["name"] for recipe in catalog["recipes"]}
        self.assertEqual(names, {"yukari", "yukari-anima", "yukari-sketch"})
        for recipe in catalog["recipes"]:
            self.assertTrue(recipe["poses"], recipe["name"])
            for pose in recipe["poses"]:
                with self.subTest(recipe=recipe["name"], pose=pose["name"]):
                    self.assertTrue(pose["positive"])
                    self.assertTrue(pose["negative"])
                    canvas = pose["canvas"]
                    self.assertEqual(len(canvas), 2)
                    for side in canvas:
                        self.assertIsInstance(side, int)
                        self.assertGreater(side, 0)

    def test_anima_poses_carry_an_expression_others_do_not(self):
        catalog = build_catalog(GIT)
        by_name = {recipe["name"]: recipe for recipe in catalog["recipes"]}
        for pose in by_name["yukari-anima"]["poses"]:
            self.assertIn("expression", pose)
            self.assertIsInstance(pose["expression"], str)
        for recipe_name in ("yukari", "yukari-sketch"):
            for pose in by_name[recipe_name]["poses"]:
                self.assertNotIn("expression", pose)

    def test_anima_recipe_lists_its_expressions(self):
        catalog = build_catalog(GIT)
        by_name = {recipe["name"]: recipe for recipe in catalog["recipes"]}
        self.assertIn("expressions", by_name["yukari-anima"])
        self.assertNotIn("expressions", by_name["yukari"])
        self.assertNotIn("expressions", by_name["yukari-sketch"])

    def test_sketch_poses_carry_parent_and_departures(self):
        catalog = build_catalog(GIT)
        by_name = {recipe["name"]: recipe for recipe in catalog["recipes"]}
        poses = {pose["name"]: pose for pose in by_name["yukari-sketch"]["poses"]}
        self.assertEqual(poses["date"]["parent"], "cinema")
        self.assertIn("departures", poses["date"])
        self.assertEqual(poses["date"]["departures"]["parent"], "cinema")
        for name in ("cinema", "stand", "bust"):
            self.assertIsNone(poses[name]["parent"])
        self.assertEqual(poses["bust"]["canvas"], [1024, 1024])
        self.assertEqual(
            [part["text"] for part in poses["bust"]["parts"]
             if part["name"] in ("proportion", "legwear", "body")],
            ["adult, ", "", "pale skin, "])
        expected_face = {
            "cinema": None,
            "stand": None,
            "bust": None,
            "smug": ("(tareme:1.2), (jitome:1.4), (half-closed eyes:1.2), "
                     "(confident:1.18), (tiny one-corner smirk:1.1), "
                     "closed mouth, looking at viewer, "),
            "date": ("(tareme:1.2), (jitome:1.25), (half-closed eyes:1.15), "
                     "(smirk:1.2), (smug:1.15), closed mouth, (blush:1.1), "
                     "(head tilt:1.1), looking at viewer, "),
            "cafe": ("(tareme:1.2), (jitome:1.2), (upturned eyes:1.3), "
                     "(looking up:1.15), looking at viewer, (light "
                     "smile:1.1), (parted lips:1.2), (blush:1.15), (head "
                     "tilt:1.1), "),
            "home": ("(tareme:1.2), (jitome:1.15), (half-closed "
                     "eyes:1.25), (head back:1.3), (looking up:1.15), "
                     "(open mouth:1.25), (exhausted:1.25), (sigh:1.15), "
                     "(blush:1.1), "),
            "bath": ("(tareme:1.2), (jitome:1.2), (half-closed eyes:1.2), "
                     "(looking down:1.25), closed mouth, (blush:1.3), "
                     "(flushed:1.2), "),
        }
        for name, face in expected_face.items():
            with self.subTest(pose=name):
                self.assertEqual(poses[name]["face"], face)

    def test_recipe_parameters_agree_with_validate_request(self):
        catalog = build_catalog(GIT)
        for recipe in catalog["recipes"]:
            name = recipe["name"]
            pose = recipe["poses"][0]["name"]
            for key in recipe["parameters"]["rejected"]:
                with self.subTest(recipe=name, key=key, expect="rejected"):
                    request = _request(
                        name, {"pose": pose, key: _DUMMY_VALUES[key]})
                    with self.assertRaises(SystemExit):
                        validate_request(request)
            for key in recipe["parameters"]["allowed"]:
                if key == "pose":
                    continue
                with self.subTest(recipe=name, key=key, expect="allowed"):
                    request = _request(
                        name, {"pose": pose, key: _DUMMY_VALUES[key]})
                    validate_request(request)  # must not raise

    def test_patches_block_lists_every_target(self):
        catalog = build_catalog(GIT)
        patches = catalog["patches"]
        self.assertEqual(set(patches["text"]["targets"]), set(TEXT_TARGETS))
        self.assertEqual(set(patches["number"]), set(NUMBER_TARGETS))
        self.assertEqual(set(patches["string"]), set(STRING_TARGETS))
        for target in NUMBER_TARGETS:
            self.assertEqual(patches["number"][target]["op"], "set")
            self.assertIsInstance(patches["number"][target]["constraints"], str)
        for target in STRING_TARGETS:
            self.assertEqual(patches["string"][target]["op"], "set")
        self.assertEqual(
            patches["string"]["render.layerdiffuse_config"]["values"],
            ["SDXL, Attention Injection", "SDXL, Conv Injection"])
        self.assertIsNone(patches["string"]["render.model"]["values"])

    def test_patches_block_carries_the_part_target_and_identity_override(self):
        catalog = build_catalog(GIT)
        patches = catalog["patches"]
        self.assertEqual(patches["text"]["part_target"], "prompt.positive.<part>")
        self.assertIn("identity_override", patches["overrides"])
        self.assertTrue(patches["overrides"]["identity_override"])

    def test_sketch_and_anima_poses_carry_parts_that_join_into_positive(self):
        catalog = build_catalog(GIT)
        by_name = {recipe["name"]: recipe for recipe in catalog["recipes"]}
        for recipe_name in ("yukari-sketch", "yukari-anima"):
            for pose in by_name[recipe_name]["poses"]:
                with self.subTest(recipe=recipe_name, pose=pose["name"]):
                    self.assertIn("parts", pose)
                    self.assertTrue(pose["parts"])
                    for part in pose["parts"]:
                        self.assertEqual(set(part), {"name", "text"})
                    joined = "".join(part["text"] for part in pose["parts"])
                    self.assertEqual(joined, pose["positive"])

    def test_yukari_poses_carry_no_parts_key(self):
        catalog = build_catalog(GIT)
        by_name = {recipe["name"]: recipe for recipe in catalog["recipes"]}
        for pose in by_name["yukari"]["poses"]:
            self.assertNotIn("parts", pose)

    def test_recipe_level_parts_and_identity_tags(self):
        catalog = build_catalog(GIT)
        by_name = {recipe["name"]: recipe for recipe in catalog["recipes"]}
        self.assertEqual(by_name["yukari"]["parts"], [])
        self.assertEqual(
            by_name["yukari-sketch"]["parts"],
            ["quality", "identity", "costume", "pose", "proportion",
             "background", "legwear", "face", "body", "finish"])
        self.assertEqual(
            by_name["yukari-anima"]["parts"],
            ["quality", "identity", "pose", "mouth", "mood", "eyes",
             "gesture", "costume", "scene", "body", "background", "face",
             "style"])
        for recipe_name in ("yukari", "yukari-sketch", "yukari-anima"):
            with self.subTest(recipe=recipe_name):
                tags = by_name[recipe_name]["identity_tags"]
                self.assertTrue(tags)
                self.assertEqual(tags, sorted(set(tags)))
                for tag in tags:
                    self.assertNotIn("(", tag)
                    self.assertNotIn(":", tag)


class DialsTest(unittest.TestCase):
    def test_every_recipe_publishes_a_dials_block(self):
        catalog = build_catalog(GIT)
        for recipe in catalog["recipes"]:
            with self.subTest(recipe=recipe["name"]):
                self.assertIn("dials", recipe)
                self.assertLessEqual(set(recipe["dials"]), set(_DIAL_SCOPE_KEYS))

    def test_sketch_is_the_only_recipe_with_repair_or_patches_dials(self):
        catalog = build_catalog(GIT)
        by_name = {recipe["name"]: recipe for recipe in catalog["recipes"]}
        self.assertEqual(set(by_name["yukari-sketch"]["dials"]),
                         {"finalize", "repair", "patches"})
        for recipe_name in ("yukari", "yukari-anima"):
            self.assertEqual(set(by_name[recipe_name]["dials"]), {"finalize"})

    def test_dial_keys_are_real_option_keys_of_their_scope(self):
        catalog = build_catalog(GIT)
        for recipe in catalog["recipes"]:
            for scope, options in recipe["dials"].items():
                with self.subTest(recipe=recipe["name"], scope=scope):
                    self.assertLessEqual(set(options), _DIAL_SCOPE_KEYS[scope])

    def test_dial_words_match_the_naming_pattern(self):
        catalog = build_catalog(GIT)
        for recipe in catalog["recipes"]:
            for scope, options in recipe["dials"].items():
                for key, words in options.items():
                    for word in words:
                        with self.subTest(
                                recipe=recipe["name"], scope=scope, key=key, word=word):
                            self.assertRegex(word, _DIAL_WORD)

    def test_dial_values_satisfy_their_option_s_own_range(self):
        # Runs each dial value through the exact validator its option uses at
        # request time -- a value out of range raises there, same as a
        # caller-supplied number out of range would.
        catalog = build_catalog(GIT)
        for recipe in catalog["recipes"]:
            for scope, options in recipe["dials"].items():
                for key, words in options.items():
                    for word in words:
                        with self.subTest(
                                recipe=recipe["name"], scope=scope, key=key, word=word):
                            if scope == "finalize":
                                finalize_arguments({key: word}, options)
                            elif scope == "repair":
                                repair_arguments({"parts": ["hands"], key: word}, options)
                            else:
                                parse_patches(
                                    [{"target": key, "op": "set", "value": word,
                                      "reason": "catalog pin"}],
                                    options)


class PublishCatalogTest(unittest.TestCase):
    def test_puts_the_given_document_to_the_branchs_catalog_path(self):
        calls = []

        class ManagementFake:
            def put_catalog(self, recipe_ref, catalog):
                calls.append((recipe_ref, catalog))
                return {"ok": True}

        document = {"schema_version": 1}
        response = publish_catalog(ManagementFake(), GIT, catalog=document)
        self.assertEqual(response, {"ok": True})
        self.assertEqual(calls, [("dev/catalog-publish", document)])

    def test_builds_the_document_itself_when_none_is_given(self):
        calls = []

        class ManagementFake:
            def put_catalog(self, recipe_ref, catalog):
                calls.append((recipe_ref, catalog))
                return {}

        publish_catalog(ManagementFake(), GIT)
        self.assertEqual(len(calls), 1)
        recipe_ref, catalog = calls[0]
        self.assertEqual(recipe_ref, "dev/catalog-publish")
        self.assertEqual(catalog["git_branch"], "dev/catalog-publish")


if __name__ == "__main__":
    unittest.main()
