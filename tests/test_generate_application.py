"""Adapter-level tests for the generate use case.

All collaborators below are fakes: this suite never opens a network socket.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from comfyui_recipes.application.generate import (
    GenerateServices,
    _image_output_path,
    _output_directory,
    batch_payload,
    generate,
    request_generation,
    request_graph,
    validate_request,
)


class ManagementFake:
    def __init__(self):
        self.calls = []

    def request(self, method, path, payload=None, multipart=None):
        self.calls.append((method, path, payload, multipart))
        if method == "POST" and path == "/api/v1/batches":
            return {"id": "batch-id", "short_id": "batch"}
        if path.endswith("/generations"):
            return {"id": "generation", "short_id": "gen", "canonical_url": "https://example/g"}
        return {}

    def resolve_character(self, name):
        return "character-id"

    def put_semantic(self, generation_id, semantic):
        self.calls.append(("semantic", generation_id, semantic))
        return {}


class ComfyFake:
    def __init__(self):
        self.submits = []
        self.waits = []
        self.fetches = []

    def submit(self, graph):
        self.submits.append(graph)
        return "prompt-id"

    def wait_for(self, prompt_id):
        self.waits.append(prompt_id)
        return []

    def fetch(self, image):
        self.fetches.append(image)
        return b"image"


class StateFake:
    def __init__(self, state):
        self.state = state
        self.saved = []

    def load(self, path):
        return self.state

    def save(self, path, state):
        self.saved.append(json.loads(json.dumps(state)))


class NullNotifier:
    def send(self, *args):
        raise AssertionError("no notification expected in this test")


class RecordingNotifier:
    def __init__(self):
        self.calls = []

    def send(self, *args):
        self.calls.append(args)


def base_request(**generation):
    return {
        "schema_version": 1,
        "request": {"count": 1, "instruction": "test", "seeds": [42]},
        "generation": {"recipe": "yukari", "parameters": {"pose": "lounge"}, **generation},
        "semantic": {"summary": "test arm"},
    }


class GenerateApplicationTest(unittest.TestCase):
    def test_validate_request_rejects_schema_and_semantic(self):
        with self.assertRaises(SystemExit):
            validate_request({**base_request(), "schema_version": 2})
        missing = base_request()
        del missing["semantic"]
        with self.assertRaises(SystemExit):
            validate_request(missing)

    def test_validate_request_rejects_malformed_nested_values(self):
        invalid = [
            [],
            {**base_request(), "request": None},
            {**base_request(), "request": []},
            {**base_request(), "generation": []},
            {**base_request(), "semantic": []},
            {**base_request(), "generation": {
                "recipe": "yukari", "parameters": None}},
            {**base_request(), "request": {
                "count": 1, "instruction": "test", "seeds": "42"}},
            {**base_request(), "request": {
                "count": 1, "instruction": "test", "seeds": [True]}},
        ]
        for request in invalid:
            with self.subTest(request=request), self.assertRaises(SystemExit):
                validate_request(request)

    def test_validate_request_rejects_unknown_parameters(self):
        request = base_request()
        request["generation"]["parameters"]["expression"] = "smile"
        with self.assertRaises(SystemExit):
            validate_request(request)

    def test_validate_request_allows_unknown_parameters_in_graph_mode(self):
        request = base_request(
            graph={"a": {"class_type": "KSampler", "inputs": {}}})
        request["generation"]["parameters"]["expression"] = "smile"
        validate_request(request)

    def test_validate_request_rejects_patches_with_graph(self):
        request = base_request(
            graph={"a": {"class_type": "KSampler", "inputs": {}}},
            patches=[{"target": "render.cfg", "op": "set", "value": 4.5,
                     "reason": "test"}])
        with self.assertRaises(SystemExit):
            validate_request(request)

    def test_validate_request_rejects_patches_with_prompt_override(self):
        request = base_request(
            prompt="override",
            patches=[{"target": "render.cfg", "op": "set", "value": 4.5,
                     "reason": "test"}])
        with self.assertRaises(SystemExit):
            validate_request(request)

    def test_validate_request_rejects_malformed_patch_shape(self):
        request = base_request(patches=[
            {"target": "render.cfg", "op": "set", "value": 4.5}])
        with self.assertRaises(SystemExit):
            validate_request(request)

    def test_validate_request_accepts_well_formed_patches(self):
        request = base_request(patches=[
            {"target": "render.cfg", "op": "set", "value": 4.5,
             "reason": "test"}])
        validate_request(request)

    def test_validate_request_accepts_experiment_block(self):
        request = base_request()
        request["experiment"] = {"experiment_id": "exp-1", "run_id": "run-1"}
        validate_request(request)
        request["experiment"]["overrides"] = {"patches": [
            {"target": "render.cfg", "op": "set", "value": 4.5,
             "reason": "test"}]}
        validate_request(request)

    def test_validate_request_accepts_explicit_null_experiment(self):
        request = base_request()
        request["experiment"] = None
        validate_request(request)

    def test_validate_request_rejects_malformed_experiment(self):
        invalid = [
            {**base_request(), "experiment": []},
            {**base_request(), "experiment": {"run_id": "run-1"}},
            {**base_request(), "experiment": {
                "experiment_id": "", "run_id": "run-1"}},
            {**base_request(), "experiment": {
                "experiment_id": 1, "run_id": "run-1"}},
            {**base_request(), "experiment": {"experiment_id": "exp-1"}},
            {**base_request(), "experiment": {
                "experiment_id": "exp-1", "run_id": ""}},
            {**base_request(), "experiment": {
                "experiment_id": "exp-1", "run_id": 1}},
            {**base_request(), "experiment": {
                "experiment_id": "exp-1", "run_id": "run-1",
                "overrides": []}},
            {**base_request(), "experiment": {
                "experiment_id": "exp-1", "run_id": "run-1",
                "overrides": {"patches": [
                    {"target": "nope", "op": "set", "value": 1,
                     "reason": "test"}]}}},
        ]
        for request in invalid:
            with self.subTest(request=request), self.assertRaises(SystemExit):
                validate_request(request)

    def test_validate_request_rejects_experiment_patches_with_generation_patches(self):
        request = base_request(patches=[
            {"target": "render.cfg", "op": "set", "value": 4.5,
             "reason": "test"}])
        request["experiment"] = {
            "experiment_id": "exp-1", "run_id": "run-1",
            "overrides": {"patches": [
                {"target": "render.steps", "op": "set", "value": 20,
                 "reason": "test"}]}}
        with self.assertRaises(SystemExit):
            validate_request(request)

    def test_validate_request_rejects_experiment_patches_with_graph(self):
        request = base_request(
            graph={"a": {"class_type": "KSampler", "inputs": {}}})
        request["experiment"] = {
            "experiment_id": "exp-1", "run_id": "run-1",
            "overrides": {"patches": [
                {"target": "render.cfg", "op": "set", "value": 4.5,
                 "reason": "test"}]}}
        with self.assertRaises(SystemExit):
            validate_request(request)

    def test_validate_request_rejects_experiment_patches_with_prompt_override(self):
        request = base_request(prompt="override")
        request["experiment"] = {
            "experiment_id": "exp-1", "run_id": "run-1",
            "overrides": {"patches": [
                {"target": "render.cfg", "op": "set", "value": 4.5,
                 "reason": "test"}]}}
        with self.assertRaises(SystemExit):
            validate_request(request)

    def test_request_generation_lifts_experiment_patches(self):
        patches = [{"target": "render.cfg", "op": "set", "value": 4.5,
                   "reason": "test"}]
        request = base_request()
        request["experiment"] = {
            "experiment_id": "exp-1", "run_id": "run-1",
            "overrides": {"patches": patches}}
        generation = request_generation(request)
        self.assertEqual(generation["patches"], patches)

    def test_request_generation_leaves_existing_generation_patches_alone(self):
        own_patches = [{"target": "render.steps", "op": "set", "value": 20,
                        "reason": "test"}]
        experiment_patches = [{"target": "render.cfg", "op": "set",
                               "value": 4.5, "reason": "test"}]
        request = base_request(patches=own_patches)
        request["experiment"] = {
            "experiment_id": "exp-1", "run_id": "run-1",
            "overrides": {"patches": experiment_patches}}
        generation = request_generation(request)
        self.assertEqual(generation["patches"], own_patches)

    def test_request_graph_applies_experiment_override_patches(self):
        from comfyui_recipes.domain.generation.models import PromptPair, RenderSpec

        def builder(*args, **kwargs):
            return RenderSpec(
                model_path="m", prompts=PromptPair("base positive", "base neg"),
                width=8, height=8, seed=42, steps=30, cfg=5.0,
                sampler_name="s", scheduler="k", denoise=1.0,
                filename_prefix="p")

        def encode(spec):
            return {"6": {"inputs": {"text": spec.prompts.positive}},
                    "7": {"inputs": {"text": spec.prompts.negative}}}

        request = base_request()
        request["experiment"] = {
            "experiment_id": "exp-1", "run_id": "run-1",
            "overrides": {"patches": [
                {"target": "prompt.positive", "op": "append",
                 "value": ", extra tag", "reason": "test"}]}}
        generation = request_generation(request)
        graph = request_graph(generation, 42, "prefix", builder, encode)
        self.assertEqual(graph["6"]["inputs"]["text"], "base positive, extra tag")

    def test_batch_payload_forwards_experiment(self):
        request = base_request()
        request["experiment"] = {
            "experiment_id": "exp-1", "run_id": "run-1",
            "overrides": {"patches": [
                {"target": "render.cfg", "op": "set", "value": 4.5,
                 "reason": "test"}]}}
        payload = batch_payload(request, {"commit": "c", "dirty": False}, "key")
        self.assertEqual(payload["experiment"], request["experiment"])

    def test_output_paths_must_remain_inside_configured_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self.assertEqual(_output_directory(root, "batch"), root / "batch")
            for identifier in ("../escape", "/tmp/escape", r"..\escape"):
                with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                    _output_directory(root, identifier)
            output = root / "batch"
            output.mkdir()
            self.assertEqual(
                _image_output_path(output, "render.png"), output / "render.png")
            for filename in ("../escape.png", "/tmp/escape.png"):
                with self.subTest(filename=filename), self.assertRaises(ValueError):
                    _image_output_path(output, filename)

    def test_request_graph_explicit_graph_rewrites_job_fields_only(self):
        original = {"a": {"class_type": "KSampler", "inputs": {"seed": 1}},
                    "b": {"class_type": "SaveImage", "inputs": {"filename_prefix": "old"}}}
        graph = request_graph({"recipe": "probe", "graph": original}, 99, "new",
                              lambda *a, **k: None, lambda s: None)
        self.assertEqual(graph["a"]["inputs"]["seed"], 99)
        self.assertEqual(graph["b"]["inputs"]["filename_prefix"], "new")
        self.assertEqual(original["a"]["inputs"]["seed"], 1)

    def test_request_graph_builds_yukari_and_applies_overrides(self):
        from comfyui_recipes.domain.generation.models import PromptPair, RenderSpec

        seen = {}

        def builder(*args, **kwargs):
            seen["args"] = args
            seen["kwargs"] = kwargs
            return RenderSpec(
                model_path="m", prompts=PromptPair("built", "built-neg"),
                width=8, height=8, seed=42, steps=30, cfg=5.0,
                sampler_name="s", scheduler="k", denoise=1.0,
                filename_prefix="p")

        def encode(spec):
            seen["spec"] = spec
            return {"6": {"inputs": {"text": spec.prompts.positive}},
                    "7": {"inputs": {"text": spec.prompts.negative}}}

        generation = base_request(prompt="override", negative_prompt="override-neg")["generation"]
        graph = request_graph(generation, 42, "prefix", builder, encode)
        self.assertEqual(seen["args"], ("lounge", 42, "prefix"))
        # No costume/hires/denoise/expression in generation.parameters, so
        # none is forwarded -- the recipe's own default applies instead of
        # this layer inventing one.
        self.assertEqual(seen["kwargs"], {})
        self.assertEqual(seen["spec"].prompts.positive, "override")
        self.assertEqual(seen["spec"].prompts.negative, "override-neg")
        self.assertEqual(graph["6"]["inputs"]["text"], "override")
        self.assertEqual(graph["7"]["inputs"]["text"], "override-neg")

    def test_request_graph_forwards_only_present_optional_parameters(self):
        from comfyui_recipes.domain.generation.models import PromptPair, RenderSpec

        seen = {}

        def builder(*args, **kwargs):
            seen["args"] = args
            seen["kwargs"] = kwargs
            return RenderSpec(
                model_path="m", prompts=PromptPair("built", "built-neg"),
                width=8, height=8, seed=42, steps=30, cfg=5.0,
                sampler_name="s", scheduler="k", denoise=1.0,
                filename_prefix="p")

        def encode(spec):
            return {"6": {"inputs": {"text": spec.prompts.positive}},
                    "7": {"inputs": {"text": spec.prompts.negative}}}

        generation = base_request()["generation"]
        generation["parameters"] = {
            "pose": "coffee", "costume": "outing", "expression": "doya"}
        request_graph(generation, 7, "prefix", builder, encode)
        self.assertEqual(seen["args"], ("coffee", 7, "prefix"))
        self.assertEqual(
            seen["kwargs"], {"costume": "outing", "expression": "doya"})

    def test_generate_resume_ingested_job_does_not_submit_or_create_job(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            path.write_text(json.dumps(base_request()))
            management = ManagementFake()
            comfy = ComfyFake()
            state = StateFake({
                "idempotency_key": "fixed-key", "batch_id": "old-batch",
                "seeds": [42], "jobs": [{"idempotency_key": "job-key",
                                           "job_id": "job-id",
                                           "comfy_prompt_id": "old-prompt",
                                           "status": "ingested"}],
            })
            services = GenerateServices(
                management, comfy, state, NullNotifier(),
                lambda generation, seed, prefix: {"6": {"inputs": {"text": "x"}}},
                lambda: {"commit": "commit", "dirty": False}, lambda *_: [],
                Path(directory), lambda message: None)
            generate(path, services)
            self.assertEqual(comfy.submits, [])
            self.assertEqual(comfy.waits, [])
            self.assertEqual(comfy.fetches, [])
            self.assertFalse(any(call[1].endswith("/jobs") for call in management.calls))
            self.assertTrue(any(call[1] == "/api/v1/batches/batch-id" and call[2] == {"status": "completed"}
                                for call in management.calls))

    def test_generate_resume_skips_registered_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            path.write_text(json.dumps(base_request()))
            management = ManagementFake()
            comfy = ComfyFake()
            comfy.wait_for = lambda prompt_id: [{"filename": "render.png"}]
            state = StateFake({
                "idempotency_key": "fixed-key", "seeds": [42],
                "jobs": [{"idempotency_key": "job-key", "job_id": "job-id",
                          "comfy_prompt_id": "old-prompt", "status": "failed",
                          "generations": [{"id": "generation",
                                           "short_id": "gen",
                                           "canonical_url": "https://example/g",
                                           "status": "registered"}]}],
            })
            services = GenerateServices(
                management, comfy, state, NullNotifier(),
                lambda generation, seed, prefix: {},
                lambda: {"commit": "commit", "dirty": False}, lambda *_: [],
                Path(directory), lambda message: None)
            generate(path, services)
            self.assertEqual(comfy.fetches, [])
            self.assertFalse(any(call[0] == "POST" and call[1].endswith("/generations")
                                 for call in management.calls))
            self.assertEqual(state.state["jobs"][0]["status"], "ingested")

    def test_generate_reuses_output_idempotency_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            path.write_text(json.dumps(base_request()))
            management = ManagementFake()
            comfy = ComfyFake()
            comfy.wait_for = lambda prompt_id: [{"filename": "render.png"}]
            state = StateFake({
                "idempotency_key": "fixed-key", "seeds": [42],
                "jobs": [{"idempotency_key": "job-key", "job_id": "job-id",
                          "comfy_prompt_id": "old-prompt", "status": "failed",
                          "generations": [{"idempotency_key": "output-key",
                                           "comfy_output_index": 0}]}],
            })
            services = GenerateServices(
                management, comfy, state, RecordingNotifier(),
                lambda generation, seed, prefix: {},
                lambda: {"commit": "commit", "dirty": False}, lambda *_: [],
                Path(directory), lambda message: None)
            generate(path, services)
            call = next(call for call in management.calls
                        if call[0] == "POST" and call[1].endswith("/generations"))
            self.assertEqual(call[3][0]["idempotency_key"], "output-key")
            self.assertEqual(
                state.state["jobs"][0]["generations"][0]["status"],
                "registered")

    def test_generate_records_patches_in_semantic_attributes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            patches = [{"target": "render.cfg", "op": "set", "value": 4.5,
                       "reason": "test"}]
            path.write_text(json.dumps(base_request(patches=patches)))
            management = ManagementFake()
            comfy = ComfyFake()
            comfy.wait_for = lambda prompt_id: [{"filename": "render.png"}]
            state = StateFake({
                "idempotency_key": "fixed-key", "seeds": [42],
                "jobs": [{"idempotency_key": "job-key", "job_id": "job-id",
                          "comfy_prompt_id": "old-prompt", "status": "failed"}],
            })
            services = GenerateServices(
                management, comfy, state, RecordingNotifier(),
                lambda generation, seed, prefix: {
                    "6": {"inputs": {"text": "x"}}, "7": {"inputs": {"text": "y"}}},
                lambda: {"commit": "commit", "dirty": False}, lambda *_: [],
                Path(directory), lambda message: None)
            generate(path, services)
            semantic_call = next(
                call for call in management.calls if call[0] == "semantic")
            self.assertEqual(semantic_call[2]["attributes"]["patches"], patches)

    def test_generate_records_palette_from_measure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            path.write_text(json.dumps(base_request()))
            management = ManagementFake()
            comfy = ComfyFake()
            comfy.wait_for = lambda prompt_id: [{"filename": "render.png"}]
            state = StateFake({
                "idempotency_key": "fixed-key", "seeds": [42],
                "jobs": [{"idempotency_key": "job-key", "job_id": "job-id",
                          "comfy_prompt_id": "old-prompt", "status": "failed"}],
            })
            services = GenerateServices(
                management, comfy, state, RecordingNotifier(),
                lambda generation, seed, prefix: {
                    "6": {"inputs": {"text": "x"}}, "7": {"inputs": {"text": "y"}}},
                lambda: {"commit": "commit", "dirty": False}, lambda *_: [],
                Path(directory), lambda message: None,
                measure=lambda data: {"fig_sat_mean": 40.0, "light_sat": 20.0,
                                       "fails": ["mean saturation too high"]})
            generate(path, services)
            semantic_call = next(
                call for call in management.calls if call[0] == "semantic")
            palette = semantic_call[2]["attributes"]["palette"]
            self.assertIn("verdict", palette)
            self.assertTrue(palette["verdict"].startswith("FAIL"))

    def test_generate_survives_measure_raising(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            path.write_text(json.dumps(base_request()))
            management = ManagementFake()
            comfy = ComfyFake()
            comfy.wait_for = lambda prompt_id: [{"filename": "render.png"}]
            state = StateFake({
                "idempotency_key": "fixed-key", "seeds": [42],
                "jobs": [{"idempotency_key": "job-key", "job_id": "job-id",
                          "comfy_prompt_id": "old-prompt", "status": "failed"}],
            })

            def broken_measure(data):
                raise ValueError("bad image")

            services = GenerateServices(
                management, comfy, state, RecordingNotifier(),
                lambda generation, seed, prefix: {
                    "6": {"inputs": {"text": "x"}}, "7": {"inputs": {"text": "y"}}},
                lambda: {"commit": "commit", "dirty": False}, lambda *_: [],
                Path(directory), lambda message: None,
                measure=broken_measure)
            generate(path, services)
            self.assertEqual(state.state["jobs"][0]["status"], "ingested")

    def test_generate_attaches_batch_to_experiment_run(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            request = base_request()
            request["experiment"] = {"experiment_id": "exp-1", "run_id": "run-1"}
            path.write_text(json.dumps(request))
            management = ManagementFake()
            comfy = ComfyFake()
            state = StateFake({
                "idempotency_key": "fixed-key", "seeds": [42],
                "jobs": [{"idempotency_key": "job-key", "job_id": "job-id",
                          "comfy_prompt_id": "old-prompt", "status": "ingested"}],
            })
            services = GenerateServices(
                management, comfy, state, NullNotifier(),
                lambda generation, seed, prefix: {"6": {"inputs": {"text": "x"}}},
                lambda: {"commit": "commit", "dirty": False}, lambda *_: [],
                Path(directory), lambda message: None)
            generate(path, services)
            self.assertIn(
                ("PATCH", "/api/v1/experiment-runs/run-1",
                 {"batch_id": "batch-id"}, None),
                management.calls)

    def test_generate_skips_experiment_run_patch_when_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            path.write_text(json.dumps(base_request()))
            management = ManagementFake()
            comfy = ComfyFake()
            state = StateFake({
                "idempotency_key": "fixed-key", "seeds": [42],
                "jobs": [{"idempotency_key": "job-key", "job_id": "job-id",
                          "comfy_prompt_id": "old-prompt", "status": "ingested"}],
            })
            services = GenerateServices(
                management, comfy, state, NullNotifier(),
                lambda generation, seed, prefix: {"6": {"inputs": {"text": "x"}}},
                lambda: {"commit": "commit", "dirty": False}, lambda *_: [],
                Path(directory), lambda message: None)
            generate(path, services)
            self.assertFalse(any(
                call[1].startswith("/api/v1/experiment-runs/")
                for call in management.calls))

    def test_generate_probe_stops_before_batch_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            patches = [{"target": "render.cfg", "op": "set", "value": 4.5,
                       "reason": "test"}]
            path.write_text(json.dumps(base_request(patches=patches)))
            management = ManagementFake()
            comfy = ComfyFake()
            state = StateFake(
                {"idempotency_key": "fixed-key", "seeds": [42], "jobs": []})

            def failing_builder(generation, seed, prefix):
                raise ValueError("needle absent")

            services = GenerateServices(
                management, comfy, state, NullNotifier(), failing_builder,
                lambda: {"commit": "commit", "dirty": False}, lambda *_: [],
                Path(directory), lambda message: None)
            with self.assertRaises(SystemExit):
                generate(path, services)
            self.assertFalse(
                any(call[1] == "/api/v1/batches" for call in management.calls))


if __name__ == "__main__":
    unittest.main()
