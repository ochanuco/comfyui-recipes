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
        self.context = {"batch": {"id": "source-batch"}}

    def request(self, method, path, payload=None, multipart=None):
        self.calls.append((method, path, payload, multipart))
        if path.endswith("/context"):
            return self.context
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
        return [{"filename": "out.png"}, {"filename": "out-matte.png"}]

    def fetch(self, image):
        return b"matte-bytes" if "-matte" in image["filename"] else b"raw-bytes"


class RecordingNotifier:
    def __init__(self):
        self.calls = []

    def send(self, *args):
        self.calls.append(args)


def deliver(data, matte):
    return data + b"-delivered", "tag"


def base_services(directory, **overrides):
    kwargs = dict(
        management=ManagementFake(),
        comfyui=ComfyFake(),
        graph_from_png=lambda data: GRAPH,
        chain_pass=lambda *args, **kwargs: {},
        deliver=deliver,
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

    def test_matte_reaches_the_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            seen = []

            def deliver_recording(data, matte):
                seen.append((data, matte))
                return data + b"-delivered", "tag"

            services = base_services(directory, deliver=deliver_recording,
                                     repin=lambda data: (data, []))
            finalize("gen-id", services)
            self.assertEqual(seen, [(b"raw-bytes", b"matte-bytes")])

    def test_the_matte_is_stored_as_a_mask_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory, repin=lambda data: (data, []))
            finalize("gen-id", services)
            asset_call = next(
                call for call in services.management.calls
                if call[0] == "POST" and call[1].endswith("/assets"))
            self.assertEqual(asset_call[1], "/api/v1/generations/generation/assets")
            metadata, field, filename, data, content_type = asset_call[3]
            self.assertEqual(metadata, {"role": "mask"})
            self.assertEqual(field, "file")
            self.assertEqual(filename, "out-matte.png")
            self.assertEqual(data, b"matte-bytes")
            self.assertEqual(content_type, "image/png")

    def test_a_missing_matte_aborts(self):
        class NoMatte(ComfyFake):
            def wait_for(self, prompt_id):
                return [{"filename": "out.png"}]

        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory, comfyui=NoMatte())
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
