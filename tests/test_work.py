"""Tests for the resident requests-queue worker.

All collaborators are fakes: this suite never opens a network socket and
never calls the real generate()/finalize() use cases (those are covered
separately in test_generate_application.py and test_finalize_application.py).
"""

from __future__ import annotations

import dataclasses
import tempfile
import threading
import time
import unittest
from pathlib import Path

from comfyui_recipes.application.generate import GenerateServices
from comfyui_recipes.application.work import (
    Heartbeat,
    HubListener,
    ProgressRelay,
    WorkServices,
    execute,
    finalize_arguments,
    masked_redraw_arguments,
    release_claims,
    repair_arguments,
    work,
    work_once,
)
from comfyui_recipes.domain.repair.controlnet import DEFAULT_CONTROL_STRENGTH
from comfyui_recipes.domain.repair.loras import DEFAULT_PART_LORA_WEIGHT
from comfyui_recipes.domain.yukari.dials import DIALS as YUKARI_DIALS
from comfyui_recipes.domain.yukari.recipe import TOE_GUARD
from comfyui_recipes.domain.yukari_sketch.dials import DIALS as SKETCH_DIALS


class ManagementFake:
    def __init__(self, claim_responses=None, dry_run_items=None,
                context=None, batch=None):
        self.calls = []
        self.claim_responses = list(claim_responses or [])
        self.claim_error = None
        self.dry_run_items = dry_run_items or []
        self.running_items = []
        # A finalize/repair/masked_redraw row's dial resolution fetches the
        # source generation's context, then its batch, for `batch.recipe`.
        self.context = context if context is not None else {"batch": {"id": "batch-1"}}
        self.batch = batch if batch is not None else {"id": "batch-1", "recipe": "yukari"}

    def request(self, method, path, payload=None, multipart=None):
        self.calls.append((method, path, payload, multipart))
        if method == "POST" and path == "/api/v1/requests/claim":
            if self.claim_error is not None:
                raise self.claim_error
            if self.claim_responses:
                next_item = self.claim_responses.pop(0)
                if isinstance(next_item, BaseException):
                    raise next_item
                return next_item
            return None
        if method == "GET" and path.startswith("/api/v1/requests?status=queued"):
            return {"items": self.dry_run_items}
        if method == "GET" and path.startswith("/api/v1/requests?status=running"):
            return {"items": self.running_items}
        if method == "PATCH" and path.startswith("/api/v1/requests/"):
            return {}
        if method == "GET" and path.endswith("/context"):
            return self.context
        if method == "GET" and path.startswith("/api/v1/batches/"):
            return self.batch
        raise AssertionError(f"unexpected management call: {method} {path}")


class FakeHubConnection:
    """A scripted Connection: pops dicts/exceptions from `script`, else idles.

    An empty script makes recv() behave like a real timeout -- it sleeps a
    short, bounded time and returns None -- so a listener with nothing left
    to read does not busy-loop.
    """

    def __init__(self, script=None, idle_timeout_cap=0.05):
        self.script = list(script or [])
        self.sent = []
        self.closed = False
        self.idle_timeout_cap = idle_timeout_cap

    def send(self, message):
        self.sent.append(message)

    def recv(self, timeout):
        if self.closed:
            raise ConnectionError("closed")
        if self.script:
            item = self.script.pop(0)
            if isinstance(item, BaseException):
                raise item
            return item
        time.sleep(min(timeout, self.idle_timeout_cap) if timeout else self.idle_timeout_cap)
        return None

    def close(self):
        self.closed = True


class GatedHubConnection:
    """Like FakeHubConnection, but the message after `pre_script` is held back
    until the test calls `release.set()` -- lets a test synchronize with an
    in-progress `wake.wait()` before delivering the message that ends it.
    """

    def __init__(self, pre_script, gated_message):
        self.pre_script = list(pre_script)
        self.gated_message = gated_message
        self.release = threading.Event()
        self.sent = []
        self.closed = False

    def send(self, message):
        self.sent.append(message)

    def recv(self, timeout):
        if self.pre_script:
            item = self.pre_script.pop(0)
            if isinstance(item, BaseException):
                raise item
            return item
        if self.release.wait(timeout=min(timeout, 2) if timeout else 2):
            self.release.clear()
            return self.gated_message
        return None

    def close(self):
        self.closed = True


class HubFactory:
    """A `services.hub`/`services.progress_feed` factory: one connection (or
    exception) per call, consumed in order.
    """

    def __init__(self, connections):
        self.connections = list(connections)

    def __call__(self):
        next_item = self.connections.pop(0)
        if isinstance(next_item, BaseException):
            raise next_item
        return next_item


class RecordingHeartbeat:
    def __init__(self, management, row_id, worker_id, *, interval=30, emit=print):
        self.management = management
        self.row_id = row_id
        self.worker_id = worker_id
        self.interval = interval
        self.emit = emit
        self.events = []

    def __enter__(self):
        self.events.append("start")
        return self

    def __exit__(self, *exc_info):
        self.events.append("stop")
        return False


def make_generate_services(directory: Path, **overrides) -> GenerateServices:
    defaults = dict(
        management=None, comfyui=None, state=None, notifier=None,
        graph_builder=lambda generation, seed, prefix: {},
        git_metadata=lambda: {"commit": "c", "dirty": False},
        conflicts=lambda *_: [], output_root=directory, measure=None,
        emit=lambda message: None,
    )
    defaults.update(overrides)
    return GenerateServices(**defaults)


def make_services(directory: Path, management, *, heartbeats=None,
                  generate=None, finalize=None, finalize_services=None,
                  repair=None, repair_services=None,
                  masked_redraw=None, masked_redraw_services=None,
                  branch="dev/requests-worker", emit=None, sleep=None,
                  kinds=("generate", "finalize")) -> WorkServices:
    kwargs = dict(
        management=management,
        generate_services=make_generate_services(Path(directory)),
        finalize_services=(finalize_services if finalize_services is not None
                          else "finalize-services"),
        repair_services=(repair_services if repair_services is not None
                         else "repair-services"),
        masked_redraw_services=(masked_redraw_services
                                if masked_redraw_services is not None
                                else "masked-redraw-services"),
        git_metadata=lambda: {"branch": branch},
        worker_id="test-worker",
        emit=(emit or (lambda message: None)),
        kinds=kinds,
    )
    if heartbeats is not None:
        def factory(management, row_id, worker_id, *, interval=30, emit=print):
            instance = RecordingHeartbeat(
                management, row_id, worker_id, interval=interval, emit=emit)
            heartbeats.append(instance)
            return instance
        kwargs["heartbeat"] = factory
    if generate is not None:
        kwargs["generate"] = generate
    if finalize is not None:
        kwargs["finalize"] = finalize
    if repair is not None:
        kwargs["repair"] = repair
    if masked_redraw is not None:
        kwargs["masked_redraw"] = masked_redraw
    if sleep is not None:
        kwargs["sleep"] = sleep
    return WorkServices(**kwargs)


def make_hub_services(directory: Path, *, hub=None, progress_feed=None,
                      sleep=None, emit=None, ping_interval=0.05, backoff_max=1,
                      clock=None, kinds=("generate", "finalize")) -> WorkServices:
    kwargs = dict(
        management=ManagementFake(),
        generate_services=make_generate_services(Path(directory)),
        finalize_services="finalize-services",
        repair_services="repair-services",
        masked_redraw_services="masked-redraw-services",
        git_metadata=lambda: {"branch": "dev/requests-worker"},
        worker_id="test-worker",
        emit=(emit or (lambda message: None)),
        kinds=kinds,
        hub=hub,
        progress_feed=progress_feed,
        ping_interval=ping_interval,
        backoff_max=backoff_max,
    )
    if sleep is not None:
        kwargs["sleep"] = sleep
    if clock is not None:
        kwargs["clock"] = clock
    return WorkServices(**kwargs)


def repair_row(**overrides):
    row = {
        "id": "req-3", "kind": "repair", "status": "running",
        "recipe_ref": "dev/requests-worker", "run_id": None, "attempt": 1,
        "payload": {"generation_id": "gen-1", "options": {}},
    }
    row.update(overrides)
    return row


def masked_redraw_row(**overrides):
    row = {
        "id": "req-4", "kind": "masked_redraw", "status": "running",
        "recipe_ref": "dev/requests-worker", "run_id": None, "attempt": 1,
        "payload": {"generation_id": "gen-1", "options": {
            "regions": [[0.1, 0.1, 0.5, 0.5]], "prompt_patch": "a dress"}},
    }
    row.update(overrides)
    return row


def generate_row(**overrides):
    row = {
        "id": "req-1", "kind": "generate", "status": "running",
        "recipe_ref": "dev/requests-worker", "run_id": None, "attempt": 1,
        "payload": {"schema_version": 1, "request": {"count": 1},
                    "generation": {"recipe": "yukari"}, "semantic": {}},
    }
    row.update(overrides)
    return row


def finalize_row(**overrides):
    row = {
        "id": "req-2", "kind": "finalize", "status": "running",
        "recipe_ref": "dev/requests-worker", "run_id": None, "attempt": 1,
        "payload": {"generation_id": "gen-1", "options": {}},
    }
    row.update(overrides)
    return row


class FinalizeArgumentsTest(unittest.TestCase):
    def test_defaults_are_false_and_null(self):
        arguments = finalize_arguments({})
        self.assertEqual(arguments, {
            "denoise": None, "handdrawn": False, "apply_repin": False,
            "apply_skin": False, "apply_recolor": False, "keep_legwear": None,
            "toe_guard": None, "size": None, "deliver_size": None,
            "latent_route": None,
            "finalizer": None, "keep_scene": False, "transparent": None,
            "backdrop": None, "upscale": None, "lora_strength": None,
            "stroke_light": None,
            "repair": None, "repair_regions": [], "repair_denoise": 0.6,
            "repair_pad": 1.0, "repair_size": 1024, "repair_lora": None,
            "keep_regions": [], "keep_strength": 0.25, "sketch_redraw": None,
            "deliver_only": False,
        })

    def test_deliver_only_true_is_validated_as_a_boolean(self):
        self.assertIs(finalize_arguments({"deliver_only": True})["deliver_only"], True)

    def test_deliver_only_rejects_a_non_boolean(self):
        with self.assertRaisesRegex(ValueError, "deliver_only"):
            finalize_arguments({"deliver_only": "yes"})

    def test_backdrop_null_passes_through(self):
        self.assertIsNone(finalize_arguments({})["backdrop"])

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

    def test_lora_strength_null_passes_through(self):
        self.assertIsNone(finalize_arguments({})["lora_strength"])

    def test_lora_strength_a_number_passes_through(self):
        self.assertEqual(
            finalize_arguments({"lora_strength": 1.2})["lora_strength"], 1.2)

    def test_lora_strength_above_the_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "lora_strength"):
            finalize_arguments({"lora_strength": 3})

    def test_lora_strength_a_boolean_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "lora_strength"):
            finalize_arguments({"lora_strength": True})

    def test_stroke_light_null_passes_through(self):
        self.assertIsNone(finalize_arguments({})["stroke_light"])

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

    def test_toe_guard_true_becomes_the_recipe_constant(self):
        self.assertEqual(finalize_arguments({"toe_guard": True})["toe_guard"], TOE_GUARD)

    def test_toe_guard_number_passes_through(self):
        self.assertEqual(finalize_arguments({"toe_guard": 1.2})["toe_guard"], 1.2)

    def test_booleans_and_size_and_finalizer_pass_through(self):
        arguments = finalize_arguments({
            "repin": True, "recolor": True, "handdrawn": True, "skin": True,
            "keep_scene": True, "size": 2048, "finalizer": "some-model",
            "denoise": 0.5, "transparent": True,
        })
        self.assertEqual(arguments["apply_repin"], True)
        self.assertEqual(arguments["apply_recolor"], True)
        self.assertEqual(arguments["handdrawn"], True)
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
        self.assertEqual(finalize_arguments({})["repair_size"], 1024)

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
        dials = SKETCH_DIALS["finalize"]
        self.assertEqual(finalize_arguments({"denoise": "tidy"}, dials)["denoise"], 0.65)
        self.assertEqual(finalize_arguments({"denoise": "redraw"}, dials)["denoise"], 0.8)

    def test_denoise_unknown_word_names_the_key_and_word(self):
        dials = SKETCH_DIALS["finalize"]
        with self.assertRaises(ValueError) as ctx:
            finalize_arguments({"denoise": "blurry"}, dials)
        self.assertIn("denoise", str(ctx.exception))
        self.assertIn("blurry", str(ctx.exception))

    def test_word_on_a_recipe_with_no_dial_for_that_key_is_rejected(self):
        # yukari (IL) publishes only a `denoise` dial -- a word for a key it
        # has no vocabulary for fails the same way as an unknown word.
        with self.assertRaisesRegex(ValueError, "toe_guard"):
            finalize_arguments({"toe_guard": "on"}, YUKARI_DIALS["finalize"])

    def test_keep_legwear_word_resolves_to_the_same_constant_as_true(self):
        dials = SKETCH_DIALS["finalize"]
        self.assertEqual(finalize_arguments({"keep_legwear": "on"}, dials)["keep_legwear"], 0.62)

    def test_toe_guard_word_resolves_to_the_recipe_constant(self):
        dials = SKETCH_DIALS["finalize"]
        self.assertEqual(finalize_arguments({"toe_guard": "on"}, dials)["toe_guard"], TOE_GUARD)

    def test_lora_strength_word_resolves_through_dials(self):
        dials = SKETCH_DIALS["finalize"]
        self.assertEqual(finalize_arguments({"lora_strength": "raw"}, dials)["lora_strength"], 1.5)
        self.assertEqual(
            finalize_arguments({"lora_strength": "recipe"}, dials)["lora_strength"], 0.8)

    def test_repair_lora_word_resolves_through_dials(self):
        dials = SKETCH_DIALS["finalize"]
        self.assertEqual(
            finalize_arguments({"repair_lora": "on"}, dials)["repair_lora"],
            DEFAULT_PART_LORA_WEIGHT)

    def test_repair_denoise_word_resolves_through_dials(self):
        dials = SKETCH_DIALS["finalize"]
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
        dials = SKETCH_DIALS["finalize"]
        self.assertEqual(finalize_arguments({"denoise": 0.7}, dials)["denoise"], 0.7)

    def test_sketch_redraw_null_passes_through(self):
        self.assertIsNone(finalize_arguments({})["sketch_redraw"])

    def test_sketch_redraw_string_passes_through(self):
        self.assertEqual(
            finalize_arguments({"sketch_redraw": "cinema"})["sketch_redraw"], "cinema")

    def test_sketch_redraw_empty_string_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "sketch_redraw"):
            finalize_arguments({"sketch_redraw": ""})

    def test_sketch_redraw_non_string_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "sketch_redraw"):
            finalize_arguments({"sketch_redraw": True})

    def test_unknown_key_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            finalize_arguments({"nope": True})
        self.assertIn("nope", str(ctx.exception))

    def test_wrong_type_is_rejected_with_the_offending_key_named(self):
        cases = [
            {"repin": "yes"},
            {"denoise": "0.5"},
            {"keep_legwear": "wide"},
            {"route": "sideways"},
            {"finalizer": 123},
            {"size": 2048.5},
            {"toe_guard": "on"},
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
        dials = SKETCH_DIALS["repair"]
        self.assertEqual(repair_arguments({"denoise": "keep"}, dials)["denoise"], 0.6)

    def test_lora_word_resolves_through_dials(self):
        dials = SKETCH_DIALS["repair"]
        self.assertEqual(
            repair_arguments({"lora": "on"}, dials)["lora"], DEFAULT_PART_LORA_WEIGHT)

    def test_unknown_word_names_the_key_and_word(self):
        dials = SKETCH_DIALS["repair"]
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
        dials = SKETCH_DIALS["repair"]
        self.assertEqual(
            masked_redraw_arguments(self._valid(denoise="keep"), dials)["denoise"], 0.6)

    def test_unknown_denoise_word_names_the_key_and_word(self):
        dials = SKETCH_DIALS["repair"]
        with self.assertRaises(ValueError) as ctx:
            masked_redraw_arguments(self._valid(denoise="blurry"), dials)
        self.assertIn("denoise", str(ctx.exception))
        self.assertIn("blurry", str(ctx.exception))


class ExecuteTest(unittest.TestCase):
    def test_recipe_ref_mismatch_fails_without_executing(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            services = make_services(
                directory, ManagementFake(),
                generate=lambda *a, **k: calls.append((a, k)))
            row = generate_row(recipe_ref="other-branch")
            with self.assertRaises(SystemExit) as ctx:
                execute(services, row)
            self.assertEqual(str(ctx.exception), "recipe_ref not served: other-branch")
            self.assertEqual(calls, [])

    def test_generate_kind_writes_the_request_file_and_derives_the_key_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                calls.append((path, key_prefix))
                return {"batch_id": "b1", "generation_ids": ["g1"]}

            services = make_services(directory, ManagementFake(), generate=fake_generate)
            result = execute(services, generate_row())
            self.assertEqual(result, {"batch_id": "b1", "generation_ids": ["g1"]})
            self.assertEqual(len(calls), 1)
            path, key_prefix = calls[0]
            self.assertEqual(path, Path(directory) / "requests" / "req-1.json")
            self.assertTrue(path.exists())
            self.assertEqual(key_prefix, "request:req-1")

    def test_finalize_kind_maps_options_and_uses_the_configured_services(self):
        with tempfile.TemporaryDirectory() as directory:
            finalize_calls = []

            def fake_finalize(generation_id, finalize_services, **kwargs):
                finalize_calls.append((generation_id, finalize_services, kwargs))
                return {"batch_id": "b2", "generation_ids": ["g2"]}

            services = make_services(
                directory, ManagementFake(), finalize=fake_finalize,
                finalize_services="finalize-services-sentinel")
            row = finalize_row(payload={
                "generation_id": "gen-1",
                "options": {"repin": True, "keep_legwear": True, "route": "pixel"},
            })
            result = execute(services, row)
            self.assertEqual(result, {
                "batch_id": "b2", "generation_ids": ["g2"],
                "resolved_options": {"repin": True, "keep_legwear": 0.62, "route": "pixel"},
            })
            self.assertEqual(finalize_calls[0][0], "gen-1")
            self.assertEqual(finalize_calls[0][1], "finalize-services-sentinel")
            self.assertEqual(finalize_calls[0][2]["apply_repin"], True)
            self.assertEqual(finalize_calls[0][2]["keep_legwear"], 0.62)
            self.assertIs(finalize_calls[0][2]["latent_route"], False)
            self.assertIs(finalize_calls[0][2]["keep_scene"], False)
            self.assertIn("context", finalize_calls[0][2])

    def test_finalize_kind_with_bad_options_fails_before_finalizing(self):
        with tempfile.TemporaryDirectory() as directory:
            finalize_calls = []
            services = make_services(
                directory, ManagementFake(),
                finalize=lambda *a, **k: finalize_calls.append((a, k)))
            row = finalize_row(payload={
                "generation_id": "gen-1", "options": {"nope": True}})
            with self.assertRaises(SystemExit) as ctx:
                execute(services, row)
            self.assertIn("nope", str(ctx.exception))
            self.assertEqual(finalize_calls, [])

    def test_finalize_kind_without_generation_id_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            services = make_services(directory, ManagementFake())
            row = finalize_row(payload={"options": {}})
            with self.assertRaises(SystemExit):
                execute(services, row)

    def test_finalize_resolves_words_against_the_source_batchs_recipe(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(
                batch={"id": "batch-1", "recipe": "yukari-sketch"})
            services = make_services(
                directory, management,
                finalize=lambda generation_id, finalize_services, **kwargs: {
                    "batch_id": "b2", "generation_ids": ["g2"]})
            row = finalize_row(payload={
                "generation_id": "gen-1",
                "options": {"denoise": "tidy", "repin": True, "keep_legwear": True},
            })
            result = execute(services, row)
            self.assertEqual(result["resolved_options"], {
                "denoise": 0.65, "repin": True, "keep_legwear": 0.62,
            })

    def test_finalize_word_unknown_to_the_source_recipe_fails_the_request(self):
        with tempfile.TemporaryDirectory() as directory:
            # yukari (IL, the default fake recipe) has no `redraw` word.
            services = make_services(
                directory, ManagementFake(),
                finalize=lambda *a, **k: (_ for _ in ()).throw(
                    AssertionError("finalize must not run")))
            row = finalize_row(payload={
                "generation_id": "gen-1", "options": {"denoise": "redraw"}})
            with self.assertRaisesRegex(SystemExit, "denoise"):
                execute(services, row)

    def test_finalize_payload_ignores_extra_keys_such_as_chimeras_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            services = make_services(
                directory, ManagementFake(),
                finalize=lambda generation_id, finalize_services, **kwargs: {
                    "batch_id": "b2", "generation_ids": ["g2"]})
            row = finalize_row(payload={
                "generation_id": "gen-1", "options": {},
                "profile": {"name": "cinema-tidy", "version": 3},
            })
            result = execute(services, row)
            self.assertEqual(result["batch_id"], "b2")

    def test_unsupported_kind_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            services = make_services(directory, ManagementFake())
            with self.assertRaises(SystemExit):
                execute(services, generate_row(kind="probe"))

    def test_repair_kind_maps_options_and_uses_the_configured_services(self):
        with tempfile.TemporaryDirectory() as directory:
            repair_calls = []

            def fake_repair(generation_id, repair_services, **kwargs):
                repair_calls.append((generation_id, repair_services, kwargs))
                return {"batch_id": "b3", "generation_ids": ["g3"]}

            services = make_services(
                directory, ManagementFake(), repair=fake_repair,
                repair_services="repair-services-sentinel")
            row = repair_row(payload={
                "generation_id": "gen-1",
                "options": {"parts": ["feet"], "seeds": [7]},
            })
            result = execute(services, row)
            self.assertEqual(result, {
                "batch_id": "b3", "generation_ids": ["g3"],
                "resolved_options": {"parts": ["feet"], "seeds": [7]},
            })
            self.assertEqual(repair_calls[0][0], "gen-1")
            self.assertEqual(repair_calls[0][1], "repair-services-sentinel")
            self.assertEqual(repair_calls[0][2]["parts"], ["feet"])
            self.assertEqual(repair_calls[0][2]["seeds"], [7])
            self.assertIn("context", repair_calls[0][2])
            self.assertIn("batch", repair_calls[0][2])

    def test_repair_kind_with_bad_options_fails_before_repairing(self):
        with tempfile.TemporaryDirectory() as directory:
            repair_calls = []
            services = make_services(
                directory, ManagementFake(),
                repair=lambda *a, **k: repair_calls.append((a, k)))
            row = repair_row(payload={
                "generation_id": "gen-1", "options": {"nope": True}})
            with self.assertRaises(SystemExit) as ctx:
                execute(services, row)
            self.assertIn("nope", str(ctx.exception))
            self.assertEqual(repair_calls, [])

    def test_repair_kind_without_generation_id_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            services = make_services(directory, ManagementFake())
            row = repair_row(payload={"options": {}})
            with self.assertRaises(SystemExit):
                execute(services, row)

    def test_masked_redraw_kind_maps_options_and_uses_the_configured_services(self):
        with tempfile.TemporaryDirectory() as directory:
            masked_redraw_calls = []

            def fake_masked_redraw(generation_id, masked_redraw_services, **kwargs):
                masked_redraw_calls.append((generation_id, masked_redraw_services, kwargs))
                return {"batch_id": "b4", "generation_ids": ["g4"]}

            services = make_services(
                directory, ManagementFake(), masked_redraw=fake_masked_redraw,
                masked_redraw_services="masked-redraw-services-sentinel")
            row = masked_redraw_row(payload={
                "generation_id": "gen-1",
                "options": {"regions": [[0.1, 0.1, 0.5, 0.5]],
                            "prompt_patch": "a dress", "seeds": [7]},
            })
            result = execute(services, row)
            self.assertEqual(result, {
                "batch_id": "b4", "generation_ids": ["g4"],
                "resolved_options": {"regions": [[0.1, 0.1, 0.5, 0.5]],
                                     "prompt_patch": "a dress", "seeds": [7]},
            })
            self.assertEqual(masked_redraw_calls[0][0], "gen-1")
            self.assertEqual(masked_redraw_calls[0][1], "masked-redraw-services-sentinel")
            self.assertEqual(masked_redraw_calls[0][2]["regions"], [[0.1, 0.1, 0.5, 0.5]])
            self.assertEqual(masked_redraw_calls[0][2]["prompt_patch"], "a dress")
            self.assertEqual(masked_redraw_calls[0][2]["seeds"], [7])
            self.assertIn("context", masked_redraw_calls[0][2])
            self.assertIn("batch", masked_redraw_calls[0][2])

    def test_masked_redraw_kind_with_bad_options_fails_before_running(self):
        with tempfile.TemporaryDirectory() as directory:
            masked_redraw_calls = []
            services = make_services(
                directory, ManagementFake(),
                masked_redraw=lambda *a, **k: masked_redraw_calls.append((a, k)))
            row = masked_redraw_row(payload={
                "generation_id": "gen-1", "options": {"nope": True}})
            with self.assertRaises(SystemExit) as ctx:
                execute(services, row)
            self.assertIn("nope", str(ctx.exception))
            self.assertEqual(masked_redraw_calls, [])

    def test_masked_redraw_kind_without_generation_id_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            services = make_services(directory, ManagementFake())
            row = masked_redraw_row(payload={
                "options": {"regions": [[0.1, 0.1, 0.5, 0.5]], "prompt_patch": "a dress"}})
            with self.assertRaises(SystemExit):
                execute(services, row)


class WorkOnceTest(unittest.TestCase):
    def test_no_queued_row_returns_false_and_makes_no_further_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(claim_responses=[None])
            services = make_services(directory, management)
            self.assertFalse(work_once(services))
            self.assertEqual(management.calls, [
                ("POST", "/api/v1/requests/claim",
                 {"worker_id": "test-worker", "kinds": ["generate", "finalize"]}, None)])

    def test_done_row_patches_status_done_with_the_result(self):
        with tempfile.TemporaryDirectory() as directory:
            row = generate_row()
            management = ManagementFake(claim_responses=[row])

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                return {"batch_id": "b1", "generation_ids": ["g1"]}

            services = make_services(directory, management, generate=fake_generate)
            self.assertTrue(work_once(services))
            patch_call = next(
                call for call in management.calls
                if call[0] == "PATCH" and call[1] == "/api/v1/requests/req-1")
            self.assertEqual(
                patch_call[2],
                {"status": "done", "result": {"batch_id": "b1", "generation_ids": ["g1"]},
                 "worker_id": "test-worker"})

    def test_failed_row_patches_status_failed_with_the_error_message(self):
        with tempfile.TemporaryDirectory() as directory:
            row = generate_row()
            management = ManagementFake(claim_responses=[row])

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                raise RuntimeError("boom")

            services = make_services(directory, management, generate=fake_generate)
            self.assertTrue(work_once(services))
            patch_call = next(
                call for call in management.calls
                if call[0] == "PATCH" and call[1] == "/api/v1/requests/req-1")
            self.assertEqual(patch_call[2], {"status": "failed", "error": "boom",
                                             "worker_id": "test-worker"})

    def test_recipe_ref_mismatch_reports_failed_with_the_exact_message(self):
        with tempfile.TemporaryDirectory() as directory:
            row = generate_row(recipe_ref="other-branch")
            management = ManagementFake(claim_responses=[row])
            calls = []
            services = make_services(
                directory, management, generate=lambda *a, **k: calls.append((a, k)))
            self.assertTrue(work_once(services))
            self.assertEqual(calls, [])
            patch_call = next(
                call for call in management.calls
                if call[0] == "PATCH" and call[1] == "/api/v1/requests/req-1")
            self.assertEqual(
                patch_call[2],
                {"status": "failed", "error": "recipe_ref not served: other-branch",
                 "worker_id": "test-worker"})

    def test_heartbeat_is_started_and_stopped_around_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            row = generate_row()
            management = ManagementFake(claim_responses=[row])
            heartbeats = []

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                self.assertEqual(heartbeats[0].events, ["start"])
                return {"batch_id": "b1", "generation_ids": []}

            services = make_services(
                directory, management, heartbeats=heartbeats, generate=fake_generate)
            work_once(services)
            self.assertEqual(len(heartbeats), 1)
            self.assertEqual(heartbeats[0].row_id, "req-1")
            self.assertEqual(heartbeats[0].events, ["start", "stop"])

    def test_keyboard_interrupt_from_the_executor_propagates_and_marks_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            row = generate_row()
            management = ManagementFake(claim_responses=[row])
            heartbeats = []

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                raise KeyboardInterrupt

            services = make_services(
                directory, management, heartbeats=heartbeats, generate=fake_generate)
            with self.assertRaises(KeyboardInterrupt):
                work_once(services)
            self.assertFalse(any(call[0] == "PATCH" for call in management.calls))
            self.assertEqual(heartbeats[0].events, ["start", "stop"])

    def test_claim_failure_is_emitted_and_does_not_raise(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake()
            management.claim_error = SystemExit("403 forbidden")
            messages = []
            services = make_services(directory, management, emit=messages.append)
            self.assertFalse(work_once(services))
            self.assertTrue(any("403" in message for message in messages))

    def test_dry_run_does_not_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(dry_run_items=[generate_row()])
            services = make_services(directory, management)
            self.assertFalse(work_once(services, dry_run=True))
            self.assertFalse(
                any(call[1] == "/api/v1/requests/claim" for call in management.calls))
            self.assertTrue(
                any(call[1].startswith("/api/v1/requests?status=queued")
                    for call in management.calls))


class WorkLoopTest(unittest.TestCase):
    def test_once_claims_exactly_once_and_never_sleeps(self):
        with tempfile.TemporaryDirectory() as directory:
            row = generate_row()
            management = ManagementFake(claim_responses=[row])

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                return {"batch_id": "b1", "generation_ids": []}

            def no_sleep(seconds):
                raise AssertionError("must not sleep when --once")

            services = make_services(
                directory, management, generate=fake_generate, sleep=no_sleep)
            work(services, once=True)
            claim_calls = [call for call in management.calls
                          if call[1] == "/api/v1/requests/claim"]
            self.assertEqual(len(claim_calls), 1)

    def test_sleeps_only_when_nothing_was_claimed(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(claim_responses=[None])
            sleeps = []

            def sleep_then_stop(seconds):
                sleeps.append(seconds)
                raise KeyboardInterrupt

            services = make_services(directory, management, sleep=sleep_then_stop)
            work(services, once=False)  # must not raise
            self.assertEqual(sleeps, [30])

    def test_keyboard_interrupt_stops_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(claim_responses=[None])
            messages = []

            def interrupt(seconds):
                raise KeyboardInterrupt

            services = make_services(
                directory, management, sleep=interrupt, emit=messages.append)
            work(services, once=False)
            self.assertTrue(any("stopped" in message for message in messages))


class PublishCatalogAtStartupTest(unittest.TestCase):
    def test_failing_catalog_publish_does_not_prevent_work_from_starting(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(claim_responses=[None])
            messages = []

            def interrupt(seconds):
                raise KeyboardInterrupt

            services = make_services(
                directory, management, sleep=interrupt, emit=messages.append)
            work(services, once=False)  # must not raise
            self.assertTrue(
                any("catalog publish failed" in message for message in messages))

    def test_successful_publish_puts_to_the_branchs_catalog_before_the_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(claim_responses=[None])
            calls = []
            management.put_catalog = lambda recipe_ref, catalog: calls.append(
                (recipe_ref, catalog)) or {}

            def interrupt(seconds):
                raise KeyboardInterrupt

            services = make_services(directory, management, sleep=interrupt)
            work(services, once=False)
            self.assertEqual(len(calls), 1)
            recipe_ref, catalog = calls[0]
            self.assertEqual(recipe_ref, "dev/requests-worker")
            self.assertEqual(catalog["git_branch"], "dev/requests-worker")

    def test_no_catalog_flag_skips_publish_entirely(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(claim_responses=[None])
            calls = []
            management.put_catalog = lambda recipe_ref, catalog: calls.append(
                (recipe_ref, catalog)) or {}

            def interrupt(seconds):
                raise KeyboardInterrupt

            services = make_services(directory, management, sleep=interrupt)
            work(services, once=False, publish_catalog=False)
            self.assertEqual(calls, [])

    def test_dry_run_skips_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(claim_responses=[None])
            calls = []
            management.put_catalog = lambda recipe_ref, catalog: calls.append(
                (recipe_ref, catalog)) or {}
            services = make_services(directory, management)
            work(services, once=True, dry_run=True)
            self.assertEqual(calls, [])


class ReleaseClaimsTest(unittest.TestCase):
    def _services(self, management, emit=None):
        with tempfile.TemporaryDirectory() as directory:
            return make_services(Path(directory), management, emit=emit)

    def test_release_hands_each_running_row_back_to_the_queue(self):
        management = ManagementFake()
        management.running_items = [{"id": "req-1"}, {"id": "req-2"}]
        release_claims(self._services(management))
        patched = [(path, payload) for method, path, payload, _ in management.calls
                   if method == "PATCH"]
        self.assertEqual(patched, [
            ("/api/v1/requests/req-1",
             {"status": "queued", "worker_id": "test-worker"}),
            ("/api/v1/requests/req-2",
             {"status": "queued", "worker_id": "test-worker"}),
        ])

    def test_release_asks_only_for_its_own_running_rows(self):
        management = ManagementFake()
        release_claims(self._services(management))
        queried = [path for method, path, _, _ in management.calls if method == "GET"]
        self.assertEqual(
            queried, ["/api/v1/requests?status=running&worker_id=test-worker"])

    def test_release_reports_the_status_the_row_landed_in(self):
        management = ManagementFake()
        management.running_items = [{"id": "req-1"}]

        def request(method, path, payload=None, multipart=None):
            management.calls.append((method, path, payload, multipart))
            if method == "GET":
                return {"items": management.running_items}
            return {"status": "failed", "error": "released after max attempts"}

        management.request = request
        emitted = []
        release_claims(self._services(management, emit=emitted.append))
        self.assertIn("released req-1: failed", emitted)

    def test_release_survives_an_unreachable_server(self):
        management = ManagementFake()

        def request(method, path, payload=None, multipart=None):
            raise SystemExit("connection refused")

        management.request = request
        emitted = []
        release_claims(self._services(management, emit=emitted.append))
        self.assertTrue(any("release query failed" in line for line in emitted))

    def test_dry_run_releases_nothing(self):
        management = ManagementFake()
        management.running_items = [{"id": "req-1"}]
        with tempfile.TemporaryDirectory() as directory:
            services = make_services(Path(directory), management)
            work(services, once=True, dry_run=True)
        self.assertFalse(any(method == "PATCH" for method, _, _, _ in management.calls))


class DrainTest(unittest.TestCase):
    def test_a_drained_worker_claims_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake()
            messages = []
            services = dataclasses.replace(
                make_services(Path(directory), management,
                              emit=messages.append),
                draining=lambda: True)
            work(services, publish_catalog=False)
            self.assertFalse(any(call[1] == "/api/v1/requests/claim"
                                 for call in management.calls))
            self.assertIn("draining: no new work claimed", messages)

    def test_the_request_in_flight_finishes_before_the_worker_leaves(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(claim_responses=[generate_row()])
            finished = []
            asked = []

            def fake_generate(path, generate_services, **kwargs):
                asked.append(True)
                return {"batch_id": "b", "generation_ids": ["g"]}

            services = dataclasses.replace(
                make_services(Path(directory), management,
                              generate=fake_generate),
                draining=lambda: bool(asked),
                drained=lambda: finished.append(True))
            work(services, publish_catalog=False)
            self.assertEqual(len(asked), 1)
            self.assertEqual(finished, [True])
            self.assertTrue(any(
                call[1].startswith("/api/v1/requests/") and call[2]
                and call[2].get("status") == "done"
                for call in management.calls))

    def test_leaving_without_a_drain_does_not_acknowledge_one(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(claim_responses=[None])
            finished = []

            def interrupt(seconds):
                raise KeyboardInterrupt

            services = dataclasses.replace(
                make_services(Path(directory), management, sleep=interrupt),
                draining=lambda: False,
                drained=lambda: finished.append(True))
            work(services, publish_catalog=False)
            self.assertEqual(finished, [])

    def test_an_unreadable_drain_signal_does_not_stop_the_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(claim_responses=[None])
            messages = []

            def explode():
                raise OSError("permission denied")

            def interrupt(seconds):
                raise KeyboardInterrupt

            services = dataclasses.replace(
                make_services(Path(directory), management, sleep=interrupt,
                              emit=messages.append),
                draining=explode)
            work(services, publish_catalog=False)
            self.assertTrue(any("drain check failed" in m for m in messages))
            self.assertTrue(any(call[1] == "/api/v1/requests/claim"
                                for call in management.calls))


class HeartbeatTest(unittest.TestCase):
    def test_sends_running_with_the_worker_id_until_stopped(self):
        import threading

        calls = []
        seen = threading.Event()

        class Management:
            def request(self, method, path, payload=None, multipart=None):
                calls.append((method, path, payload))
                seen.set()
                return {}

        heartbeat = Heartbeat(Management(), "req-1", "test-worker", interval=0.01)
        with heartbeat:
            self.assertTrue(seen.wait(2))
        self.assertEqual(calls[0], ("PATCH", "/api/v1/requests/req-1",
                                    {"status": "running", "worker_id": "test-worker"}))


class HubListenerTest(unittest.TestCase):
    def test_hello_sent_first_and_wake_set_after_connect(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = FakeHubConnection(script=[
                {"type": "hello_ack", "server_time": "t"},
            ])
            services = make_hub_services(
                directory, hub=HubFactory([connection]))
            wake = threading.Event()
            listener = HubListener(services, wake).start()
            try:
                self.assertTrue(wake.wait(2))
                self.assertEqual(connection.sent[0], {
                    "type": "hello", "worker_id": "test-worker",
                    "kinds": ["generate", "finalize"]})
            finally:
                listener.stop()
            self.assertTrue(connection.closed)

    def test_queued_message_sets_wake(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = FakeHubConnection(script=[
                {"type": "hello_ack", "server_time": "t"},
                {"type": "queued", "request_id": "r1", "kind": "generate",
                 "recipe_ref": "ref"},
            ])
            services = make_hub_services(directory, hub=HubFactory([connection]))
            wake = threading.Event()
            listener = HubListener(services, wake).start()
            try:
                self.assertTrue(wake.wait(2))
            finally:
                listener.stop()

    def test_unknown_message_types_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = FakeHubConnection(script=[
                {"type": "pong"}, {"type": "mystery", "foo": "bar"},
            ])
            services = make_hub_services(directory, hub=HubFactory([connection]))
            wake = threading.Event()
            listener = HubListener(services, wake).start()
            try:
                self.assertTrue(wake.wait(2))  # from the initial connect
                wake.clear()
                time.sleep(0.2)
                self.assertFalse(wake.is_set())
            finally:
                listener.stop()

    def test_ping_sent_on_recv_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = FakeHubConnection(script=[])
            services = make_hub_services(
                directory, hub=HubFactory([connection]), ping_interval=0.01)
            wake = threading.Event()
            listener = HubListener(services, wake).start()
            try:
                self.assertTrue(wake.wait(2))
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline and not any(
                        message.get("type") == "ping" for message in connection.sent):
                    time.sleep(0.01)
                self.assertTrue(
                    any(message.get("type") == "ping" for message in connection.sent))
            finally:
                listener.stop()

    def test_reconnect_backoff_doubles_up_to_backoff_max(self):
        with tempfile.TemporaryDirectory() as directory:
            # The factory itself fails (the Upgrade is refused) every time, so
            # backoff never gets the post-connect reset -- it grows monotonically.
            factory = HubFactory([ConnectionError("refused") for _ in range(6)])
            sleeps = []
            holder: dict = {}

            def fake_sleep(seconds):
                sleeps.append(seconds)
                if len(sleeps) >= 5:
                    holder["listener"]._stop.set()

            services = make_hub_services(
                directory, hub=factory, sleep=fake_sleep, backoff_max=8)
            listener = HubListener(services, threading.Event())
            holder["listener"] = listener
            listener.start()
            listener._thread.join(2)
            self.assertEqual(sleeps, [1, 2, 4, 8, 8])

    def test_wake_set_again_after_a_reconnect(self):
        with tempfile.TemporaryDirectory() as directory:
            first = FakeHubConnection(script=[])
            second = FakeHubConnection(script=[])
            # A real, short pause between the closed first connection and the
            # reconnect attempt gives the test time to observe and clear the
            # first wake before the second one fires -- an instant retry
            # could collapse the two into a single observed set().
            services = make_hub_services(
                directory, hub=HubFactory([first, second]),
                sleep=lambda seconds: time.sleep(0.2))
            wake = threading.Event()
            listener = HubListener(services, wake).start()
            try:
                self.assertTrue(wake.wait(2))
                wake.clear()
                first.close()  # simulate the server dropping the first socket
                self.assertTrue(wake.wait(2))
            finally:
                listener.stop()

    def test_send_progress_is_a_no_op_when_not_connected(self):
        with tempfile.TemporaryDirectory() as directory:
            services = make_hub_services(directory)
            listener = HubListener(services, threading.Event())
            listener.send_progress("r1", "submit")  # must not raise

    def test_send_progress_forwards_the_message_when_connected(self):
        with tempfile.TemporaryDirectory() as directory:
            services = make_hub_services(directory)
            listener = HubListener(services, threading.Event())
            connection = FakeHubConnection()
            listener._connection = connection
            listener.send_progress("r1", "sampling", step=3, total=10)
            self.assertEqual(connection.sent, [{
                "type": "progress", "request_id": "r1", "phase": "sampling",
                "step": 3, "total": 10}])

    def test_send_progress_omits_none_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            services = make_hub_services(directory)
            listener = HubListener(services, threading.Event())
            connection = FakeHubConnection()
            listener._connection = connection
            listener.send_progress("r1", "submit")
            self.assertEqual(connection.sent, [{
                "type": "progress", "request_id": "r1", "phase": "submit"}])


class ProgressRelayTest(unittest.TestCase):
    def test_forwards_progress_only_while_current_is_set_and_with_the_id(self):
        with tempfile.TemporaryDirectory() as directory:
            feed = GatedHubConnection(
                pre_script=[{"step": 1, "total": 5}], gated_message={"step": 2, "total": 5})
            services = make_hub_services(
                directory, progress_feed=lambda: feed, sleep=lambda seconds: None)
            sent = []

            class RecordingListener:
                def send_progress(self, request_id, phase, **fields):
                    sent.append((request_id, phase, fields))

            relay = ProgressRelay(services, RecordingListener())
            relay.current = None
            relay.start()
            try:
                # First event (step 1) is delivered with current still None --
                # give the background thread a moment to have dropped it.
                time.sleep(0.2)
                self.assertEqual(sent, [])
                relay.current = "req-9"
                feed.release.set()
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline and not sent:
                    time.sleep(0.01)
            finally:
                relay.stop()
            self.assertEqual(sent, [("req-9", "sampling", {"step": 2, "total": 5})])


class WorkWithHubTest(unittest.TestCase):
    def test_idle_wait_is_woken_by_a_queued_message_not_by_the_full_interval(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(claim_responses=[
                generate_row(), None, KeyboardInterrupt()])
            connection = GatedHubConnection(
                pre_script=[{"type": "hello_ack", "server_time": "t"}],
                gated_message={"type": "queued", "request_id": "req-1",
                              "kind": "generate", "recipe_ref": "dev/requests-worker"})
            claimed = []

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                claimed.append(1)
                return {"batch_id": "b1", "generation_ids": []}

            services = make_services(directory, management, generate=fake_generate)
            services = dataclasses.replace(
                services, hub=HubFactory([connection]), ping_interval=0.05,
                backoff_max=1)

            done = threading.Event()

            def run():
                work(services, interval=30, once=False)
                done.set()

            worker = threading.Thread(target=run, daemon=True)
            start = time.monotonic()
            worker.start()
            # let pass 1 (claim generate_row) and pass 2 (claim None, enter
            # the idle wait) happen, then deliver the queued message.
            time.sleep(0.3)
            connection.release.set()
            self.assertTrue(done.wait(5))
            elapsed = time.monotonic() - start
            self.assertLess(elapsed, 5)
            self.assertEqual(len(claimed), 1)


class WorkOnceHubTest(unittest.TestCase):
    def test_sends_submit_phase_for_a_generate_row_after_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            row = generate_row()
            management = ManagementFake(claim_responses=[row])
            sent = []

            class RecordingListener:
                def send_progress(self, request_id, phase, **fields):
                    sent.append((request_id, phase))

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                return {"batch_id": "b1", "generation_ids": []}

            services = make_services(directory, management, generate=fake_generate)
            work_once(services, listener=RecordingListener())
            self.assertIn(("req-1", "submit"), sent)

    def test_sends_finalize_phase_for_a_finalize_row_after_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            row = finalize_row()
            management = ManagementFake(claim_responses=[row])
            sent = []

            class RecordingListener:
                def send_progress(self, request_id, phase, **fields):
                    sent.append((request_id, phase))

            def fake_finalize(generation_id, finalize_services, **kwargs):
                return {"batch_id": "b2", "generation_ids": []}

            services = make_services(directory, management, finalize=fake_finalize)
            work_once(services, listener=RecordingListener())
            self.assertIn(("req-2", "finalize"), sent)

    def test_relay_current_is_set_during_execute_and_cleared_after(self):
        with tempfile.TemporaryDirectory() as directory:
            row = generate_row()
            management = ManagementFake(claim_responses=[row])
            observed = {}

            class FakeRelay:
                current = None

            relay = FakeRelay()

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                observed["during"] = relay.current
                return {"batch_id": "b1", "generation_ids": []}

            services = make_services(directory, management, generate=fake_generate)
            work_once(services, relay=relay)
            self.assertEqual(observed["during"], "req-1")
            self.assertIsNone(relay.current)


if __name__ == "__main__":
    unittest.main()
