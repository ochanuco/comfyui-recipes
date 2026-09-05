"""Adapter-level tests for the finalize use case.

All collaborators below are fakes: this suite never opens a network socket,
and never talks to a real ComfyUI -- the redraw, matte and delivery are all
a single graph now, so these tests check what finalize() asks that graph to
do (deliver=True, the skin/repin/recolor/keep_* flags, an uploaded source
image) and how it classifies the three outputs, not any local pixel work.
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
    def __init__(self):
        self.uploaded = []

    def upload_image(self, name, data):
        self.uploaded.append((name, data))
        return f"uploaded-{name}"

    def submit(self, graph):
        return "prompt-id"

    def wait_for(self, prompt_id):
        return [{"filename": "out.png"}, {"filename": "out-matte.png"},
                {"filename": "out-delivered.png"}]

    def fetch(self, image):
        name = image["filename"]
        if "-matte" in name:
            return b"matte-bytes"
        if "-delivered" in name:
            return b"delivered-bytes"
        return b"raw-bytes"


class RecordingNotifier:
    def __init__(self):
        self.calls = []

    def send(self, *args):
        self.calls.append(args)


def base_services(directory, **overrides):
    kwargs = dict(
        management=ManagementFake(),
        comfyui=ComfyFake(),
        graph_from_png=lambda data: GRAPH,
        chain_pass=lambda *args, **kwargs: {},
        git_metadata=lambda: {"commit": "commit", "dirty": False},
        notifier=RecordingNotifier(),
        output_root=Path(directory),
        emit=lambda message: None,
    )
    kwargs.update(overrides)
    return FinalizeServices(**kwargs)


def batch_call(services):
    return next(
        call for call in services.management.calls
        if call[0] == "POST" and call[1] == "/api/v1/batches")


class FinalizeApplicationTest(unittest.TestCase):
    def test_deliver_is_requested_with_the_matte_model(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(directory, chain_pass=recording_chain_pass)
            finalize("gen-id", services)
            self.assertIs(calls[-1]["deliver"], True)
            self.assertEqual(calls[-1]["matte_model"], delivery_style.MATTE_MODEL)
            self.assertIs(calls[-1]["keep_scene"], False)
            self.assertIs(calls[-1]["skin"], False)
            self.assertIs(calls[-1]["repin"], False)
            self.assertIs(calls[-1]["recolor"], False)

    def test_the_matte_is_stored_as_a_mask_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
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

    def test_the_delivered_output_is_recorded_as_the_second_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            result = finalize("gen-id", services)
            generation_calls = [
                call for call in services.management.calls
                if call[0] == "POST" and call[1].endswith("/generations")]
            self.assertEqual(generation_calls[1][3][1], "image")
            self.assertEqual(generation_calls[1][3][2], "out-delivered.png")
            self.assertEqual(generation_calls[1][3][3], b"delivered-bytes")
            self.assertEqual(result["generation_ids"], ["generation", "generation"])

    def test_a_missing_output_aborts(self):
        class NoMatte(ComfyFake):
            def wait_for(self, prompt_id):
                return [{"filename": "out.png"}, {"filename": "out-delivered.png"}]

        class NoDelivered(ComfyFake):
            def wait_for(self, prompt_id):
                return [{"filename": "out.png"}, {"filename": "out-matte.png"}]

        class NoRaw(ComfyFake):
            def wait_for(self, prompt_id):
                return [{"filename": "out-matte.png"},
                        {"filename": "out-delivered.png"}]

        for fake in (NoMatte(), NoDelivered(), NoRaw()):
            with tempfile.TemporaryDirectory() as directory:
                services = base_services(directory, comfyui=fake)
                with self.assertRaises(SystemExit):
                    finalize("gen-id", services)

    def test_batch_parameters_record_repin_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            finalize("gen-id", services, apply_repin=True)
            self.assertIs(batch_call(services)[2]["parameters"]["repin"], True)

    def test_batch_parameters_repin_false_when_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            finalize("gen-id", services, apply_repin=False)
            self.assertIs(batch_call(services)[2]["parameters"]["repin"], False)

    def test_recolor_wins_over_repin(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(directory, chain_pass=recording_chain_pass)
            finalize("gen-id", services, apply_repin=True, apply_recolor=True)
            self.assertIs(calls[-1]["repin"], False)
            self.assertIs(calls[-1]["recolor"], True)
            parameters = batch_call(services)[2]["parameters"]
            self.assertIs(parameters["repin"], False)
            self.assertIs(parameters["recolor"], True)

    def test_skin_uploads_the_picked_source_and_passes_its_name(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            comfy = ComfyFake()
            services = base_services(
                directory, chain_pass=recording_chain_pass, comfyui=comfy)
            finalize("gen-id", services, apply_skin=True)
            self.assertEqual(comfy.uploaded, [("fin-gen-id-source.png", b"picked")])
            self.assertIs(calls[-1]["skin"], True)
            self.assertEqual(
                calls[-1]["source_image"], "uploaded-fin-gen-id-source.png")

    def test_skin_off_does_not_upload_a_source(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = ComfyFake()
            services = base_services(directory, comfyui=comfy)
            finalize("gen-id", services)
            self.assertEqual(comfy.uploaded, [])

    def test_keep_legwear_and_keep_scene_reach_chain_pass_and_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(directory, chain_pass=recording_chain_pass)
            finalize("gen-id", services, keep_legwear=0.4, keep_scene=True)
            self.assertEqual(calls[-1]["keep_legwear"], 0.4)
            self.assertIs(calls[-1]["keep_scene"], True)
            parameters = batch_call(services)[2]["parameters"]
            self.assertEqual(parameters["keep_legwear"], 0.4)
            self.assertIs(parameters["keep_scene"], True)

    def test_keep_scene_omitted_from_parameters_when_false(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            finalize("gen-id", services)
            self.assertNotIn("keep_scene", batch_call(services)[2]["parameters"])

    def test_repin_and_skin_default_off_and_sampler_passed_to_chain_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            chain_pass_calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                chain_pass_calls.append(kwargs)
                return {}

            services = base_services(directory, chain_pass=recording_chain_pass)

            finalize("gen-id", services)
            self.assertIs(chain_pass_calls[-1]["repin"], False)
            self.assertIs(chain_pass_calls[-1]["skin"], False)
            self.assertEqual(
                chain_pass_calls[-1]["sampler"], delivery_style.FINALIZE_SAMPLER)

            finalize("gen-id", services, apply_repin=True, apply_skin=True)
            self.assertIs(chain_pass_calls[-1]["repin"], True)
            self.assertIs(chain_pass_calls[-1]["skin"], True)
            self.assertEqual(
                chain_pass_calls[-1]["sampler"], delivery_style.FINALIZE_SAMPLER)

    def test_default_denoise_and_size_pick_the_base_graphs_own_recipe(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append((size, denoise))
                return {}

            yukari_services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: GRAPH)
            finalize("gen-id", yukari_services)

            anima_services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: ANIMA_GRAPH)
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
                graph_from_png=lambda data: anima_base)
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

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                chain_pass_calls.append((size, denoise, kwargs))
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: ANIMA_GRAPH)
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

            self.assertEqual(
                batch_call(services)[2]["parameters"]["finalizer"],
                anima_delivery_style.FINALIZE_MODEL)

    def test_anima_base_honors_an_explicit_finalizer(self):
        with tempfile.TemporaryDirectory() as directory:
            chain_pass_calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                chain_pass_calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: ANIMA_GRAPH)
            finalize("gen-id", services, finalizer="other-checkpoint")

            self.assertEqual(chain_pass_calls[-1]["loader"], "other-checkpoint")
            self.assertEqual(
                batch_call(services)[2]["parameters"]["finalizer"],
                "other-checkpoint")

    def test_yukari_base_keeps_no_loader_and_no_sampling_override(self):
        with tempfile.TemporaryDirectory() as directory:
            chain_pass_calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                chain_pass_calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: GRAPH)
            finalize("gen-id", services)

            self.assertIsNone(chain_pass_calls[-1]["loader"])
            self.assertIsNone(chain_pass_calls[-1]["sampling"])
            self.assertNotIn("finalizer", batch_call(services)[2]["parameters"])

    def test_returns_batch_id_and_generation_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            result = finalize("gen-id", services)
            self.assertEqual(result["batch_id"], "batch-id")
            self.assertEqual(result["generation_ids"], ["generation", "generation"])

    def test_key_prefix_derives_batch_and_job_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            finalize("gen-id", services, key_prefix="request:r1")
            posts = {call[1]: call[2] for call in services.management.calls
                     if call[0] == "POST" and call[2]}
            self.assertEqual(posts["/api/v1/batches"]["idempotency_key"], "request:r1")
            self.assertEqual(posts["/api/v1/batches/batch-id/jobs"]["idempotency_key"],
                             "request:r1:job:0")


if __name__ == "__main__":
    unittest.main()
