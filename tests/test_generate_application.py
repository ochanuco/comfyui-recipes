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
    generate,
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

    def test_output_paths_must_remain_inside_configured_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
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
        graph = request_graph({"recipe": "probe", "graph": original}, 99, "new", lambda *_: None)
        self.assertEqual(graph["a"]["inputs"]["seed"], 99)
        self.assertEqual(graph["b"]["inputs"]["filename_prefix"], "new")
        self.assertEqual(original["a"]["inputs"]["seed"], 1)

    def test_request_graph_builds_yukari_and_applies_overrides(self):
        seen = {}

        def builder(*args, **kwargs):
            seen["args"] = args
            seen["kwargs"] = kwargs
            return {"6": {"inputs": {"text": "built"}}, "7": {"inputs": {"text": "built-neg"}}}

        generation = base_request(prompt="override", negative_prompt="override-neg")["generation"]
        graph = request_graph(generation, 42, "prefix", builder)
        self.assertEqual(seen["args"], ("lounge", 42, "prefix"))
        self.assertEqual(seen["kwargs"]["costume"], "default")
        self.assertEqual(graph["6"]["inputs"]["text"], "override")
        self.assertEqual(graph["7"]["inputs"]["text"], "override-neg")

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


if __name__ == "__main__":
    unittest.main()
