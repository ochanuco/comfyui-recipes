"""Adapter-level tests for the finalize use case.

All collaborators below are fakes: this suite never opens a network socket.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from comfyui_recipes.application.finalize import FinalizeServices, finalize
from comfyui_recipes.domain.yukari import delivery_style
from comfyui_recipes.domain.yukari_anima import delivery_style as anima_delivery_style
from comfyui_recipes.domain.yukari_anima.recipe import render_spec
from comfyui_recipes.infrastructure.comfyui import anima_graph
from comfyui_recipes.infrastructure.comfyui.refinement_graph import chain_pass

GRAPH = {"3": {"inputs": {"seed": 1}},
         "6": {"inputs": {"text": "p"}},
         "7": {"inputs": {"text": "n"}}}

ANIMA_GRAPH = {"1": {"class_type": "UNETLoader", "inputs": {}},
              "3": {"inputs": {"seed": 1}},
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
            finalize("gen-id", services, apply_repin=True)
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
            finalize("gen-id", services, apply_repin=True)
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

    def test_repin_and_skin_default_off_and_sampler_passed_to_chain_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            chain_pass_calls = []

            def chain_pass(base, size, denoise, prefix, **kwargs):
                chain_pass_calls.append(kwargs)
                return {}

            repin_calls = []

            def repin(data):
                repin_calls.append(data)
                return data, []

            skin_calls = []

            def repin_skin(picked, data):
                skin_calls.append((picked, data))
                return data, []

            services = base_services(
                directory, chain_pass=chain_pass, repin=repin,
                repin_skin=repin_skin)

            finalize("gen-id", services)
            self.assertEqual(repin_calls, [])
            self.assertEqual(skin_calls, [])
            self.assertEqual(
                chain_pass_calls[-1]["sampler"], delivery_style.FINALIZE_SAMPLER)

            finalize("gen-id", services, apply_repin=True, apply_skin=True)
            self.assertEqual(repin_calls, [b"raw-bytes"])
            self.assertEqual(skin_calls, [(b"picked", b"raw-bytes")])
            self.assertEqual(
                chain_pass_calls[-1]["sampler"], delivery_style.FINALIZE_SAMPLER)

    def test_default_denoise_and_size_pick_the_base_graphs_own_recipe(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append((size, denoise))
                return {}

            yukari_services = base_services(
                directory, chain_pass=chain_pass,
                graph_from_png=lambda data: GRAPH,
                repin=lambda data: (data, []))
            finalize("gen-id", yukari_services)

            anima_services = base_services(
                directory, chain_pass=chain_pass,
                graph_from_png=lambda data: ANIMA_GRAPH,
                repin=lambda data: (data, []))
            finalize("gen-id", anima_services)

            self.assertEqual(
                calls, [(2560, delivery_style.FINALIZE_DENOISE),
                       (anima_delivery_style.FINALIZE_SIZE,
                        anima_delivery_style.FINALIZE_DENOISE)])

    def test_anima_base_submitted_graph_carries_the_il_redraw(self):
        with tempfile.TemporaryDirectory() as directory:
            spec = render_spec("stand", 42, "fin-nare8p-il-rough")
            anima_base = anima_graph.build_graph(spec)
            submitted = []

            class RealComfyFake(ComfyFake):
                def submit(self, graph):
                    submitted.append(graph)
                    return "prompt-id"

            services = base_services(
                directory, chain_pass=chain_pass, comfyui=RealComfyFake(),
                graph_from_png=lambda data: anima_base,
                repin=lambda data: (data, []))
            finalize("gen-id", services)

            graph = submitted[0]
            loaders = [node for node in graph.values()
                      if node.get("class_type") == "DiffusersLoader"]
            self.assertTrue(any(
                loader["inputs"]["model_path"] == "hassaku-il-v22"
                for loader in loaders))
            redraw_sampler = graph["12"]["inputs"]
            self.assertEqual(redraw_sampler["denoise"], anima_delivery_style.FINALIZE_DENOISE)
            self.assertEqual(redraw_sampler["steps"], 30)
            self.assertEqual(redraw_sampler["cfg"], 5.0)
            self.assertEqual(redraw_sampler["sampler_name"], "dpmpp_2m")
            self.assertEqual(redraw_sampler["scheduler"], "karras")

    def test_anima_base_redraws_with_the_il_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            chain_pass_calls = []

            def chain_pass(base, size, denoise, prefix, **kwargs):
                chain_pass_calls.append((size, denoise, kwargs))
                return {}

            services = base_services(
                directory, chain_pass=chain_pass,
                graph_from_png=lambda data: ANIMA_GRAPH,
                repin=lambda data: (data, []))
            finalize("gen-id", services)

            size, denoise, kwargs = chain_pass_calls[-1]
            self.assertEqual(size, anima_delivery_style.FINALIZE_SIZE)
            self.assertEqual(denoise, anima_delivery_style.FINALIZE_DENOISE)
            self.assertEqual(kwargs["loader"], anima_delivery_style.FINALIZE_MODEL)
            self.assertEqual(kwargs["sampler"], anima_delivery_style.FINALIZE_SAMPLER)
            self.assertEqual(
                kwargs["sampling"],
                (anima_delivery_style.FINALIZE_STEPS,
                 anima_delivery_style.FINALIZE_CFG))

            batch_call = next(
                call for call in services.management.calls
                if call[0] == "POST" and call[1] == "/api/v1/batches")
            self.assertEqual(batch_call[2]["parameters"]["finalizer"],
                             anima_delivery_style.FINALIZE_MODEL)

    def test_anima_base_honors_an_explicit_finalizer(self):
        with tempfile.TemporaryDirectory() as directory:
            chain_pass_calls = []

            def chain_pass(base, size, denoise, prefix, **kwargs):
                chain_pass_calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=chain_pass,
                graph_from_png=lambda data: ANIMA_GRAPH,
                repin=lambda data: (data, []))
            finalize("gen-id", services, finalizer="other-checkpoint")

            self.assertEqual(chain_pass_calls[-1]["loader"], "other-checkpoint")
            batch_call = next(
                call for call in services.management.calls
                if call[0] == "POST" and call[1] == "/api/v1/batches")
            self.assertEqual(
                batch_call[2]["parameters"]["finalizer"], "other-checkpoint")

    def test_yukari_base_keeps_no_loader_and_no_sampling_override(self):
        with tempfile.TemporaryDirectory() as directory:
            chain_pass_calls = []

            def chain_pass(base, size, denoise, prefix, **kwargs):
                chain_pass_calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=chain_pass,
                graph_from_png=lambda data: GRAPH,
                repin=lambda data: (data, []))
            finalize("gen-id", services)

            self.assertIsNone(chain_pass_calls[-1]["loader"])
            self.assertIsNone(chain_pass_calls[-1]["sampling"])
            batch_call = next(
                call for call in services.management.calls
                if call[0] == "POST" and call[1] == "/api/v1/batches")
            self.assertNotIn("finalizer", batch_call[2]["parameters"])

    def test_returns_batch_id_and_generation_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory, repin=lambda data: (data, []))
            result = finalize("gen-id", services)
            self.assertEqual(result["batch_id"], "batch-id")
            self.assertEqual(result["generation_ids"], ["generation", "generation"])

    def test_key_prefix_derives_batch_and_job_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory, repin=lambda data: (data, []))
            finalize("gen-id", services, key_prefix="request:r1")
            posts = {call[1]: call[2] for call in services.management.calls
                     if call[0] == "POST" and call[2]}
            self.assertEqual(posts["/api/v1/batches"]["idempotency_key"], "request:r1")
            self.assertEqual(posts["/api/v1/batches/batch-id/jobs"]["idempotency_key"],
                             "request:r1:job:0")


if __name__ == "__main__":
    unittest.main()
