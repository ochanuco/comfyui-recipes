"""Adapter-level tests for the finalize use case.

All collaborators below are fakes: this suite never opens a network socket.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from comfyui_recipes.application.finalize import FinalizeServices, finalize

GRAPH = {"3": {"inputs": {"seed": 1}},
         "6": {"inputs": {"text": "p"}},
         "7": {"inputs": {"text": "n"}}}


class ManagementFake:
    def __init__(self):
        self.calls = []

    def request(self, method, path, payload=None, multipart=None):
        self.calls.append((method, path, payload, multipart))
        if path.endswith("/context"):
            return {"batch": {"id": "source-batch"}}
        if method == "POST" and path == "/api/v1/batches":
            return {"id": "batch-id", "short_id": "batch"}
        if method == "POST" and path.endswith("/jobs"):
            return {"id": "job-id"}
        if path.endswith("/generations"):
            return {"id": "generation", "short_id": "gen",
                     "canonical_url": "https://example/g"}
        return {}

    def fetch_generation_image(self, generation_id):
        return b"picked"


class ComfyFake:
    def submit(self, graph):
        return "prompt-id"

    def wait_for(self, prompt_id):
        return [{"filename": "out.png"}]

    def fetch(self, image):
        return b"raw-bytes"


class RecordingNotifier:
    def __init__(self):
        self.calls = []

    def send(self, *args):
        self.calls.append(args)


def deliver(data):
    return data + b"-delivered", "tag"


def base_services(directory, **overrides):
    kwargs = dict(
        management=ManagementFake(),
        comfyui=ComfyFake(),
        graph_from_png=lambda data: GRAPH,
        chain_pass=lambda *args, **kwargs: {},
        deliver=deliver,
        corner_spread=lambda data: 1.0,
        git_metadata=lambda: {"commit": "commit", "dirty": False},
        notifier=RecordingNotifier(),
        output_root=Path(directory),
        emit=lambda message: None,
    )
    kwargs.update(overrides)
    return FinalizeServices(**kwargs)


class FinalizeApplicationTest(unittest.TestCase):
    def test_repin_output_is_delivered(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def repin(data):
                calls.append(data)
                return data + b"-repinned", ["purple: measured 1/1 -> factor 1/1"]

            services = base_services(directory, repin=repin)
            finalize("gen-id", services)
            self.assertEqual(calls, [b"raw-bytes"])
            multipart_calls = [call for call in services.management.calls
                               if call[0] == "POST" and call[1].endswith("/generations")]
            delivered_call = multipart_calls[1]
            self.assertEqual(delivered_call[3][3], b"raw-bytes-repinned-delivered")

    def test_no_repin_delivers_raw(self):
        with tempfile.TemporaryDirectory() as directory:
            called = []

            def repin(data):
                called.append(data)
                return data, []

            services = base_services(directory, repin=repin)
            finalize("gen-id", services, apply_repin=False)
            self.assertEqual(called, [])
            multipart_calls = [call for call in services.management.calls
                               if call[0] == "POST" and call[1].endswith("/generations")]
            delivered_call = multipart_calls[1]
            self.assertEqual(delivered_call[3][3], b"raw-bytes-delivered")

    def test_corner_spread_over_limit_aborts(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory, corner_spread=lambda data: 999.0)
            with self.assertRaises(SystemExit):
                finalize("gen-id", services)

    def test_batch_parameters_record_repin_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(
                directory, repin=lambda data: (data, []))
            finalize("gen-id", services)
            batch_call = next(
                call for call in services.management.calls
                if call[0] == "POST" and call[1] == "/api/v1/batches")
            self.assertIs(batch_call[2]["parameters"]["repin"], True)

    def test_batch_parameters_repin_false_when_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(
                directory, repin=lambda data: (data, []))
            finalize("gen-id", services, apply_repin=False)
            batch_call = next(
                call for call in services.management.calls
                if call[0] == "POST" and call[1] == "/api/v1/batches")
            self.assertIs(batch_call[2]["parameters"]["repin"], False)


if __name__ == "__main__":
    unittest.main()
