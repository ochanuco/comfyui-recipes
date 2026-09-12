"""Adapter-level tests for the finalize use case.

All collaborators below are fakes: this suite never opens a network socket,
and never talks to a real ComfyUI -- the redraw, matte and delivery are all
a single graph now, so these tests check what finalize() asks that graph to
do (deliver=True, the skin/repin/recolor/keep_* flags, an uploaded source
image) and how it classifies the three outputs, not any local pixel work.
"""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from comfyui_recipes.application.finalize import FinalizeServices, finalize
from comfyui_recipes.domain.generation.models import PromptPair
from comfyui_recipes.domain.repair.prompt import PART_TAGS
from comfyui_recipes.domain.yukari import delivery_style
from comfyui_recipes.domain.yukari.recipe import refinement_prompt
from comfyui_recipes.domain.yukari_anima import delivery_style as anima_delivery_style
from comfyui_recipes.domain.yukari_anima.recipe import render_spec
from comfyui_recipes.domain.yukari_sketch import delivery_style as sketch_delivery_style
from comfyui_recipes.domain.yukari_sketch.prompt_style import LORA as SKETCH_LORA
from comfyui_recipes.infrastructure.comfyui import anima_graph
from comfyui_recipes.infrastructure.comfyui.refinement_graph import chain_pass

# base_roles resolves each fixture's sampler/decode/save/prompt roles by
# structure, so every fixture needs a real KSampler <- decode <- save chain
# plus positive/negative refs, not just the fields finalize() reads directly.
_DECODE_SAVE = {
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
    "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "base"}},
}

GRAPH = {"3": {"class_type": "KSampler",
              "inputs": {"seed": 1, "positive": ["6", 0], "negative": ["7", 0]}},
         "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "p"}},
         "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "n"}},
         **_DECODE_SAVE}

ANIMA_GRAPH = {"1": {"class_type": "UNETLoader", "inputs": {}},
              "3": {"class_type": "KSampler",
                   "inputs": {"seed": 1, "positive": ["6", 0], "negative": ["7", 0]}},
              "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "p"}},
              "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "n"}},
              **_DECODE_SAVE}

SKETCH_GRAPH = {"2": {"class_type": "LoraLoader", "inputs": {}},
                "3": {"class_type": "KSampler",
                     "inputs": {"seed": 1, "positive": ["6", 0], "negative": ["7", 0]}},
                "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "p"}},
                "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "n"}},
                **_DECODE_SAVE}

LAYERDIFFUSE_SKETCH_GRAPH = {"2": {"class_type": "LoraLoader", "inputs": {}},
                            "3": {"class_type": "KSampler",
                                 "inputs": {"seed": 1, "positive": ["6", 0],
                                           "negative": ["7", 0]}},
                            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "p"}},
                            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "n"}},
                            "12": {"class_type": "LayeredDiffusionApply",
                                  "inputs": {}},
                            **_DECODE_SAVE}

# A real yukari-sketch masked_redraw base: its KSampler is "19" (not "3"),
# its prompts are "15"/"16" (not "6"/"7"), it has no EmptyLatentImage, and
# its SaveImage is reached through an InpaintStitchImproved -- the shape
# that broke finalize() before base_roles resolved these structurally.
MASKED_REDRAW_GRAPH = {
    "4": {"class_type": "DiffusersLoader", "inputs": {"model_path": "hassaku-il-v22"}},
    "9": {"class_type": "SaveImage", "inputs": {"images": ["21", 0], "filename_prefix": "mrd-src-s3141592653"}},
    "10": {"class_type": "LoraLoader", "inputs": {"model": ["4", 0], "clip": ["4", 1], "lora_name": "sketch-style-xl-linaqruf.safetensors", "strength_model": 0.8, "strength_clip": 0.8}},
    "11": {"class_type": "LoadImage", "inputs": {"image": "mrd-source.png"}},
    "12": {"class_type": "LoadImage", "inputs": {"image": "mrd-mask.png"}},
    "13": {"class_type": "ImageToMask", "inputs": {"image": ["12", 0], "channel": "red"}},
    "14": {"class_type": "InpaintCropImproved", "inputs": {"image": ["11", 0], "mask": ["13", 0], "output_target_width": 2048, "output_target_height": 2048}},
    "15": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["10", 1], "text": "positive"}},
    "16": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["10", 1], "text": "negative"}},
    "17": {"class_type": "VAEEncode", "inputs": {"pixels": ["14", 1], "vae": ["4", 2]}},
    "18": {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["17", 0], "mask": ["14", 2]}},
    "19": {"class_type": "KSampler", "inputs": {"model": ["10", 0], "positive": ["15", 0], "negative": ["16", 0], "latent_image": ["18", 0], "seed": 3141592653, "steps": 30, "cfg": 5, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 0.55}},
    "20": {"class_type": "VAEDecode", "inputs": {"samples": ["19", 0], "vae": ["4", 2]}},
    "21": {"class_type": "InpaintStitchImproved", "inputs": {"stitcher": ["14", 0], "inpainted_image": ["20", 0]}},
}


class ManagementFake:
    def __init__(self, *, batch_parameters=None, generation_records=None):
        self.calls = []
        self.context = {"batch": {"id": "source-batch"}}
        self.batch_parameters = batch_parameters or {}
        self.generation_records = generation_records or {}

    def request(self, method, path, payload=None, multipart=None):
        self.calls.append((method, path, payload, multipart))
        if path.endswith("/context"):
            return self.context
        if (method == "GET"
                and path == f"/api/v1/batches/{self.context['batch']['id']}"):
            return {"id": self.context["batch"]["id"],
                    "parameters": self.batch_parameters}
        if (method == "GET" and path.startswith("/api/v1/generations/")
                and path.count("/") == 4):
            generation_id = path.rsplit("/", 1)[1]
            return self.generation_records.get(generation_id, {"id": generation_id})
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
        image_size=lambda data: (832, 1664),
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

    def test_sketch_base_defaults_transparent_true(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: SKETCH_GRAPH)
            finalize("gen-id", services)
            self.assertIs(calls[-1]["transparent"], sketch_delivery_style.FINALIZE_TRANSPARENT)
            self.assertIs(batch_call(services)[2]["parameters"]["transparent"],
                         sketch_delivery_style.FINALIZE_TRANSPARENT)

    def test_recolor_is_refused_on_a_sketch_base(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(
                directory, chain_pass=lambda *args, **kwargs: {},
                graph_from_png=lambda data: SKETCH_GRAPH)
            with self.assertRaises(SystemExit) as raised:
                finalize("gen-id", services, apply_recolor=True)
            self.assertIn("recolor", str(raised.exception))
            self.assertFalse(any(call[1] == "/api/v1/batches"
                                 for call in services.management.calls))

    def test_non_sketch_base_defaults_transparent_false_and_omits_parameter(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: GRAPH)
            finalize("gen-id", services)
            self.assertIs(calls[-1]["transparent"], False)
            self.assertNotIn("transparent", batch_call(services)[2]["parameters"])

    def test_keep_scene_forces_transparent_false_on_a_sketch_base(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: SKETCH_GRAPH)
            finalize("gen-id", services, keep_scene=True)
            self.assertIs(calls[-1]["transparent"], False)

    def test_explicit_transparent_false_on_a_sketch_base_is_honored(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: SKETCH_GRAPH)
            finalize("gen-id", services, transparent=False)
            self.assertIs(calls[-1]["transparent"], False)
            self.assertNotIn("transparent", batch_call(services)[2]["parameters"])

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

    def test_a_given_context_skips_the_context_fetch(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            finalize("gen-id", services, context={"batch": {"id": "source-batch"}})
            context_calls = [call for call in services.management.calls
                             if call[0] == "GET" and call[1].endswith("/context")]
            self.assertEqual(context_calls, [])

    def test_key_prefix_derives_batch_and_job_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            finalize("gen-id", services, key_prefix="request:r1")
            posts = {call[1]: call[2] for call in services.management.calls
                     if call[0] == "POST" and call[2]}
            self.assertEqual(posts["/api/v1/batches"]["idempotency_key"], "request:r1")
            self.assertEqual(posts["/api/v1/batches/batch-id/jobs"]["idempotency_key"],
                             "request:r1:job:0")

    def test_upscale_defaults_to_bicubic_and_reaches_chain_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(directory, chain_pass=recording_chain_pass)
            finalize("gen-id", services)
            self.assertEqual(calls[-1]["upscale"], "bicubic")

    def test_upscale_override_reaches_chain_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(directory, chain_pass=recording_chain_pass)
            finalize("gen-id", services, upscale="nearest-exact")
            self.assertEqual(calls[-1]["upscale"], "nearest-exact")

    def test_batch_parameters_record_upscale_when_given(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            finalize("gen-id", services, upscale="nearest-exact")
            parameters = batch_call(services)[2]["parameters"]
            self.assertEqual(parameters["upscale"], "nearest-exact")

    def test_batch_parameters_omit_upscale_when_not_given(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            finalize("gen-id", services)
            parameters = batch_call(services)[2]["parameters"]
            self.assertNotIn("upscale", parameters)

    def test_lora_strength_adds_a_redraw_lora_and_leaves_the_base_alone(self):
        with tempfile.TemporaryDirectory() as directory:
            captured = {}

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                captured["base"] = base
                captured["redraw_lora"] = kwargs.get("redraw_lora")
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: copy.deepcopy(SKETCH_GRAPH))
            finalize("gen-id", services, lora_strength=1.4)
            self.assertEqual(captured["base"]["2"]["inputs"], {})
            self.assertEqual(captured["redraw_lora"][1:], (1.4, 1.4))

    def test_lora_strength_without_a_lora_loader_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory, graph_from_png=lambda data: GRAPH)
            with self.assertRaises(SystemExit):
                finalize("gen-id", services, lora_strength=1.0)

    def test_batch_parameters_record_lora_strength_when_given(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(
                directory, graph_from_png=lambda data: copy.deepcopy(SKETCH_GRAPH))
            finalize("gen-id", services, lora_strength=1.4)
            parameters = batch_call(services)[2]["parameters"]
            self.assertEqual(parameters["lora_strength"], 1.4)

    def test_batch_parameters_omit_lora_strength_when_not_given(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            finalize("gen-id", services)
            parameters = batch_call(services)[2]["parameters"]
            self.assertNotIn("lora_strength", parameters)

    def test_deliver_size_defaults_to_1536_for_a_sketch_base(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: copy.deepcopy(SKETCH_GRAPH))
            finalize("gen-id", services)
            self.assertEqual(calls[-1]["deliver_size"], 1536)

    def test_deliver_size_defaults_to_none_for_a_non_sketch_base(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(directory, chain_pass=recording_chain_pass)
            finalize("gen-id", services)
            self.assertIsNone(calls[-1]["deliver_size"])

    def test_deliver_size_override_is_passed_through(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: copy.deepcopy(SKETCH_GRAPH))
            finalize("gen-id", services, deliver_size=2048)
            self.assertEqual(calls[-1]["deliver_size"], 2048)

    def test_batch_parameters_record_deliver_size_for_a_sketch_base(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(
                directory, graph_from_png=lambda data: copy.deepcopy(SKETCH_GRAPH))
            finalize("gen-id", services)
            parameters = batch_call(services)[2]["parameters"]
            self.assertEqual(parameters["deliver_size"], 1536)

    def test_batch_parameters_omit_deliver_size_for_a_non_sketch_base(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            finalize("gen-id", services)
            parameters = batch_call(services)[2]["parameters"]
            self.assertNotIn("deliver_size", parameters)

    def test_stroke_light_reaches_chain_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(directory, chain_pass=recording_chain_pass)
            finalize("gen-id", services, stroke_light="ne")
            self.assertEqual(calls[-1]["stroke_light"], "ne")

    def test_stroke_light_default_is_none_in_chain_pass_kwargs(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(directory, chain_pass=recording_chain_pass)
            finalize("gen-id", services)
            self.assertIsNone(calls[-1]["stroke_light"])

    def test_batch_parameters_record_stroke_light_when_given(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            finalize("gen-id", services, stroke_light="ne")
            parameters = batch_call(services)[2]["parameters"]
            self.assertEqual(parameters["stroke_light"], "ne")

    def test_batch_parameters_omit_stroke_light_when_not_given(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            finalize("gen-id", services)
            parameters = batch_call(services)[2]["parameters"]
            self.assertNotIn("stroke_light", parameters)

    def test_backdrop_reaches_chain_pass_and_forces_transparent_false(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: SKETCH_GRAPH)
            finalize("gen-id", services, backdrop="stripes")
            self.assertEqual(calls[-1]["backdrop"], "stripes")
            self.assertIs(calls[-1]["transparent"], False)

    def test_backdrop_with_explicit_transparent_true_is_honored(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: SKETCH_GRAPH)
            finalize("gen-id", services, backdrop="stripes", transparent=True)
            self.assertIs(calls[-1]["transparent"], True)

    def test_no_backdrop_keeps_the_sketch_default_transparent_true(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: SKETCH_GRAPH)
            finalize("gen-id", services)
            self.assertIs(calls[-1]["transparent"], sketch_delivery_style.FINALIZE_TRANSPARENT)


# A minimal redraw graph `redraw_canvas` (not faked -- it is not injectable)
# can trace on its own: KSampler <- EmptyLatentImage, VAEDecode <- KSampler.
REDRAW_GRAPH = {
    "50": {"class_type": "DiffusersLoader", "inputs": {"model_path": "m"}},
    "51": {"class_type": "EmptyLatentImage", "inputs": {
        "width": 832, "height": 1664, "batch_size": 1}},
    "52": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["50", 1], "text": "p"}},
    "53": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["50", 1], "text": "n"}},
    "54": {"class_type": "KSampler", "inputs": {
        "model": ["50", 0], "positive": ["52", 0], "negative": ["53", 0],
        "latent_image": ["51", 0], "seed": 8, "steps": 30, "cfg": 5,
        "sampler_name": "euler", "scheduler": "normal", "denoise": 0.55}},
    "55": {"class_type": "VAEDecode", "inputs": {"samples": ["54", 0], "vae": ["50", 2]}},
    "56": {"class_type": "SaveImage", "inputs": {
        "images": ["55", 0], "filename_prefix": "fin-gen-id"}},
}


def _pose_outputs(found=True):
    """A minimal DWPreprocessor outputs dict; `found=False` locates nothing."""
    if not found:
        return {"2": {"openpose_json": [json.dumps([{"people": []}])]}}
    body = [0.0, 0.0, 0.0] * 18
    body[9 * 3:9 * 3 + 3] = [100.0, 300.0, 1.0]  # Rknee
    body[10 * 3:10 * 3 + 3] = [100.0, 500.0, 1.0]  # Rank
    frame = {"people": [{"pose_keypoints_2d": body,
                         "hand_left_keypoints_2d": None,
                         "hand_right_keypoints_2d": None}],
            "canvas_width": 800, "canvas_height": 1000}
    return {"2": {"openpose_json": [json.dumps([frame])]}}


class RepairComfyFake(ComfyFake):
    def __init__(self, pose_outputs=None):
        super().__init__()
        self.submitted = []
        self.pose_outputs = pose_outputs if pose_outputs is not None else _pose_outputs()

    def submit(self, graph):
        self.submitted.append(graph)
        return f"prompt-{len(self.submitted)}"

    def wait_for_outputs(self, prompt_id):
        return self.pose_outputs


class FinalizeRepairTest(unittest.TestCase):
    def _splice_recorder(self):
        calls = []

        def splice_repair(graph, **kwargs):
            calls.append(kwargs)
            return graph

        return calls, splice_repair

    def test_repair_off_by_default_stages_nothing_and_never_splices(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = RepairComfyFake()
            splice_calls, splice_repair = self._splice_recorder()
            services = base_services(
                directory, comfyui=comfy,
                chain_pass=lambda *a, **k: copy.deepcopy(REDRAW_GRAPH),
                splice_repair=splice_repair, image_size=lambda data: (800, 1000))
            finalize("gen-id", services)
            self.assertEqual(splice_calls, [])
            self.assertEqual(comfy.uploaded, [])
            self.assertEqual(len(comfy.submitted), 1)

    def test_repair_parts_submits_the_pose_pass_before_the_main_graph(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = RepairComfyFake()
            splice_calls, splice_repair = self._splice_recorder()
            services = base_services(
                directory, comfyui=comfy,
                chain_pass=lambda *a, **k: copy.deepcopy(REDRAW_GRAPH),
                splice_repair=splice_repair, image_size=lambda data: (800, 1000))
            finalize("gen-id", services, repair=["feet"])
            self.assertEqual(len(comfy.submitted), 2)
            self.assertEqual(comfy.submitted[0]["2"]["class_type"], "DWPreprocessor")
            self.assertEqual(len(splice_calls), 1)

    def test_repair_regions_only_skips_the_pose_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = RepairComfyFake()
            splice_calls, splice_repair = self._splice_recorder()
            services = base_services(
                directory, comfyui=comfy,
                chain_pass=lambda *a, **k: copy.deepcopy(REDRAW_GRAPH),
                splice_repair=splice_repair, image_size=lambda data: (800, 1000))
            finalize("gen-id", services, repair_regions=[[0.0, 0.0, 0.2, 0.2]])
            self.assertEqual(len(comfy.submitted), 1)
            self.assertEqual(len(splice_calls), 1)

    def test_no_repair_region_found_raises_system_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = RepairComfyFake(pose_outputs=_pose_outputs(found=False))
            _, splice_repair = self._splice_recorder()
            services = base_services(
                directory, comfyui=comfy,
                chain_pass=lambda *a, **k: copy.deepcopy(REDRAW_GRAPH),
                splice_repair=splice_repair, image_size=lambda data: (800, 1000))
            with self.assertRaises(SystemExit):
                finalize("gen-id", services, repair=["feet"])

    def test_splice_repair_receives_the_chain_pass_graph_and_repaired_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = RepairComfyFake()
            splice_calls, splice_repair = self._splice_recorder()
            services = base_services(
                directory, comfyui=comfy,
                chain_pass=lambda *a, **k: copy.deepcopy(REDRAW_GRAPH),
                splice_repair=splice_repair, image_size=lambda data: (800, 1000))
            finalize("gen-id", services, repair=["feet"],
                     repair_denoise=0.7, repair_size=768)
            call = splice_calls[0]
            self.assertEqual(call["denoise"], 0.7)
            self.assertEqual(call["size"], 768)
            self.assertIn(PART_TAGS["feet"], call["positive"])
            expected_negative = refinement_prompt(PromptPair("p", "n")).negative
            self.assertEqual(call["negative"], expected_negative)
            self.assertTrue(call["mask_name"].startswith("uploaded-fin-gen-id-"))
            self.assertTrue(call["mask_name"].endswith("-mask.png"))

    def test_repair_lora_reaches_splice_repair_as_part_loras(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = RepairComfyFake()
            splice_calls, splice_repair = self._splice_recorder()
            services = base_services(
                directory, comfyui=comfy,
                chain_pass=lambda *a, **k: copy.deepcopy(REDRAW_GRAPH),
                splice_repair=splice_repair, image_size=lambda data: (800, 1000))
            finalize("gen-id", services, repair=["feet"], repair_lora=0.8)
            call = splice_calls[0]
            self.assertEqual(call["loras"], (("feet-xl-ill.safetensors", 0.8),))

    def test_repair_lora_off_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = RepairComfyFake()
            splice_calls, splice_repair = self._splice_recorder()
            services = base_services(
                directory, comfyui=comfy,
                chain_pass=lambda *a, **k: copy.deepcopy(REDRAW_GRAPH),
                splice_repair=splice_repair, image_size=lambda data: (800, 1000))
            finalize("gen-id", services, repair=["feet"])
            call = splice_calls[0]
            self.assertEqual(call["loras"], ())

    def test_repair_and_skin_share_one_staged_source(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = RepairComfyFake()
            _, splice_repair = self._splice_recorder()
            services = base_services(
                directory, comfyui=comfy,
                chain_pass=lambda *a, **k: copy.deepcopy(REDRAW_GRAPH),
                splice_repair=splice_repair, image_size=lambda data: (800, 1000))
            finalize("gen-id", services, repair=["feet"], apply_skin=True)
            source_uploads = [name for name, _ in comfy.uploaded
                              if name.endswith("-source.png")]
            self.assertEqual(len(source_uploads), 1)

    def test_batch_parameters_record_repair_when_requested(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = RepairComfyFake()
            _, splice_repair = self._splice_recorder()
            services = base_services(
                directory, comfyui=comfy,
                chain_pass=lambda *a, **k: copy.deepcopy(REDRAW_GRAPH),
                splice_repair=splice_repair, image_size=lambda data: (800, 1000))
            finalize("gen-id", services, repair=["feet"], repair_pad=1.5,
                     repair_lora=0.8)
            parameters = batch_call(services)[2]["parameters"]
            self.assertEqual(parameters["repair"]["parts"], ["feet"])
            self.assertEqual(parameters["repair"]["regions"], [])
            self.assertEqual(parameters["repair"]["denoise"], 0.6)
            self.assertEqual(parameters["repair"]["pad"], 1.5)
            self.assertEqual(parameters["repair"]["size"], 1024)
            self.assertEqual(parameters["repair"]["lora"], 0.8)
            self.assertIn("mask_bbox", parameters["repair"])

    def test_batch_parameters_omit_repair_when_not_requested(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            finalize("gen-id", services)
            parameters = batch_call(services)[2]["parameters"]
            self.assertNotIn("repair", parameters)

    def test_repair_mask_uploaded_as_an_asset_on_the_raw_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = RepairComfyFake()
            _, splice_repair = self._splice_recorder()
            services = base_services(
                directory, comfyui=comfy,
                chain_pass=lambda *a, **k: copy.deepcopy(REDRAW_GRAPH),
                splice_repair=splice_repair, image_size=lambda data: (800, 1000))
            finalize("gen-id", services, repair=["feet"])
            asset_calls = [call for call in services.management.calls
                          if call[0] == "POST" and call[1].endswith("/assets")]
            repair_mask_calls = [call for call in asset_calls
                                 if call[3][0] == {"role": "repair-mask"}]
            self.assertEqual(len(repair_mask_calls), 1)
            self.assertEqual(repair_mask_calls[0][1], "/api/v1/generations/generation/assets")


class FinalizeLayerDiffuseTest(unittest.TestCase):
    def test_composes_instead_of_delivering(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services, backdrop="#112233")
            kwargs = calls[-1]
            self.assertIs(kwargs["compose"], True)
            self.assertIs(kwargs["latent_route"], False)
            self.assertIsNone(kwargs["matte_model"])
            self.assertIs(kwargs["deliver"], False)
            self.assertEqual(kwargs["backdrop"], "#112233")
            lora_name, weight = SKETCH_LORA
            self.assertEqual(kwargs["redraw_lora"], (lora_name, weight, weight))

    def test_upscale_override_reaches_the_compose_chain_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services, upscale="nearest-exact")
            self.assertEqual(calls[-1]["upscale"], "nearest-exact")

    def test_stroke_light_reaches_the_compose_chain_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services, stroke_light="sw")
            self.assertEqual(calls[-1]["stroke_light"], "sw")

    def test_batch_parameters_record_compose_and_backdrop(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(
                directory, chain_pass=lambda *a, **k: {},
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services, backdrop="#112233")
            parameters = batch_call(services)[2]["parameters"]
            self.assertIs(parameters["compose"], True)
            self.assertEqual(parameters["backdrop"], "#112233")

    def test_batch_parameters_omit_backdrop_when_not_given(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(
                directory, chain_pass=lambda *a, **k: {},
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services)
            parameters = batch_call(services)[2]["parameters"]
            self.assertNotIn("backdrop", parameters)

    def test_batch_parameters_record_cut_on_the_transparent_path(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(
                directory, chain_pass=lambda *a, **k: {},
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services)
            parameters = batch_call(services)[2]["parameters"]
            self.assertEqual(parameters["cut"], "backdrop")

    def test_batch_parameters_omit_cut_on_the_legacy_path(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(
                directory, chain_pass=lambda *a, **k: {},
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services, backdrop="#112233")
            parameters = batch_call(services)[2]["parameters"]
            self.assertNotIn("cut", parameters)

    def test_lora_strength_overrides_redraw_lora_strength(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services, lora_strength=0.9)
            lora_name, _ = SKETCH_LORA
            self.assertEqual(calls[-1]["redraw_lora"], (lora_name, 0.9, 0.9))

    def test_latent_route_opt_in_reaches_the_compose_chain_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services, latent_route=True)
            kwargs = calls[-1]
            self.assertIs(kwargs["compose"], True)
            self.assertIs(kwargs["latent_route"], True)

    def test_layerdiffuse_base_defaults_transparent_and_appends_the_deliver_tail(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services)
            kwargs = calls[-1]
            self.assertIs(kwargs["compose"], True)
            self.assertIs(kwargs["transparent"], sketch_delivery_style.FINALIZE_TRANSPARENT)
            self.assertIs(kwargs["deliver"], sketch_delivery_style.FINALIZE_TRANSPARENT)
            self.assertIsNone(kwargs["matte_model"])

    def test_layerdiffuse_keep_scene_selects_the_legacy_compose_path(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services, keep_scene=True)
            kwargs = calls[-1]
            self.assertIs(kwargs["compose"], True)
            self.assertIs(kwargs["transparent"], False)
            self.assertIs(kwargs["deliver"], False)
            self.assertIsNone(kwargs["matte_model"])

    def test_layerdiffuse_explicit_transparent_false_selects_the_legacy_compose_path(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services, transparent=False)
            kwargs = calls[-1]
            self.assertIs(kwargs["transparent"], False)
            self.assertIs(kwargs["deliver"], False)
            self.assertIsNone(kwargs["matte_model"])

    def test_layerdiffuse_backdrop_wins_over_an_explicit_transparent_true(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services, backdrop="#112233", transparent=True)
            kwargs = calls[-1]
            self.assertIs(kwargs["transparent"], False)
            self.assertIs(kwargs["deliver"], False)
            self.assertIsNone(kwargs["matte_model"])
            self.assertEqual(kwargs["backdrop"], "#112233")

    def test_layerdiffuse_transparent_path_defaults_denoise_to_the_layerdiffuse_constant(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(denoise)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services)
            self.assertEqual(calls[-1], sketch_delivery_style.FINALIZE_DENOISE_LAYERDIFFUSE)

    def test_layerdiffuse_legacy_path_defaults_denoise_to_the_layerdiffuse_constant(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(denoise)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services, backdrop="#112233")
            self.assertEqual(calls[-1], sketch_delivery_style.FINALIZE_DENOISE_LAYERDIFFUSE)

    def test_layerdiffuse_transparent_path_honors_an_explicit_denoise(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(denoise)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services, denoise=0.42)
            self.assertEqual(calls[-1], 0.42)

    def test_layerdiffuse_legacy_path_honors_an_explicit_denoise(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(denoise)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            finalize("gen-id", services, backdrop="#112233", denoise=0.42)
            self.assertEqual(calls[-1], 0.42)

    def test_non_layerdiffuse_sketch_base_still_defaults_denoise_to_the_recipe_constant(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(denoise)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: SKETCH_GRAPH)
            finalize("gen-id", services)
            self.assertEqual(calls[-1], sketch_delivery_style.FINALIZE_DENOISE)

    def test_layerdiffuse_transparent_records_a_matte_asset_and_two_generations(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(
                directory, chain_pass=lambda *a, **k: {},
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            result = finalize("gen-id", services)
            self.assertEqual(result["generation_ids"], ["generation", "generation"])
            asset_call = next(
                call for call in services.management.calls
                if call[0] == "POST" and call[1].endswith("/assets"))
            self.assertEqual(asset_call[3][0], {"role": "mask"})

    def test_layerdiffuse_legacy_path_records_one_generation_and_no_matte_asset(self):
        class SingleOutputComfyFake(ComfyFake):
            def wait_for(self, prompt_id):
                return [{"filename": "out.png"}]

        with tempfile.TemporaryDirectory() as directory:
            services = base_services(
                directory, comfyui=SingleOutputComfyFake(),
                chain_pass=lambda *a, **k: {},
                graph_from_png=lambda data: LAYERDIFFUSE_SKETCH_GRAPH)
            result = finalize("gen-id", services, backdrop="#112233")
            self.assertEqual(result["generation_ids"], ["generation"])
            self.assertFalse(any(
                call[0] == "POST" and call[1].endswith("/assets")
                for call in services.management.calls))


class MaskedRedrawBaseTest(unittest.TestCase):
    """finalize() on a base whose own base graph came from a masked_redraw:
    the reported bug (KeyError '3') and the structural roles that fix it.
    """

    def test_finalize_succeeds_over_a_masked_redraw_base(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(
                directory, chain_pass=chain_pass,
                graph_from_png=lambda data: copy.deepcopy(MASKED_REDRAW_GRAPH))
            result = finalize("gen-id", services)
            self.assertEqual(result["generation_ids"], ["generation", "generation"])

    def test_masked_redraw_sketch_base_takes_the_pixel_route(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: copy.deepcopy(MASKED_REDRAW_GRAPH))
            finalize("gen-id", services)
            self.assertIs(sketch_delivery_style.FINALIZE_LATENT_ROUTE, True)
            self.assertIs(calls[-1]["latent_route"], False)

    def test_chain_pass_over_a_masked_redraw_base_reads_seed_and_prompts(self):
        graph = chain_pass(
            copy.deepcopy(MASKED_REDRAW_GRAPH), 2560, 0.55, "fin",
            matte_model=delivery_style.MATTE_MODEL, deliver=True,
            canvas=(1024, 1024))
        redraw_ids = [key for key in graph if key.isdecimal() and int(key) > 21
                     and graph[key].get("class_type") == "KSampler"]
        self.assertEqual(len(redraw_ids), 1)
        sampler = graph[redraw_ids[0]]
        self.assertEqual(sampler["inputs"]["seed"], 3141592653)
        self.assertEqual(sampler["inputs"]["positive"], ["15", 0])
        self.assertEqual(sampler["inputs"]["negative"], ["16", 0])
        save = graph["9"]
        self.assertNotEqual(save["inputs"]["images"][0], "21")
        self.assertEqual(save["inputs"]["filename_prefix"], "fin")

    def test_chain_pass_rejects_latent_route_on_a_stitched_base(self):
        with self.assertRaisesRegex(ValueError, "stitched"):
            chain_pass(copy.deepcopy(MASKED_REDRAW_GRAPH), 2560, 0.55, "fin",
                      latent_route=True, canvas=(1024, 1024))


class RepairedRawSourceResolutionTest(unittest.TestCase):
    def test_repair_batch_resolves_base_from_the_base_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append((base, kwargs))
                return {}

            management = ManagementFake(
                batch_parameters={"kind": "repair", "base_generation": "raw-1"},
                generation_records={"raw-1": {"comfy_job": {"graph": SKETCH_GRAPH}}})
            services = base_services(
                directory, management=management, chain_pass=recording_chain_pass)
            finalize("gen-id", services)
            base, kwargs = calls[-1]
            self.assertEqual(base, SKETCH_GRAPH)
            self.assertIs(kwargs["latent_route"], True)

    def test_masked_redraw_batch_also_resolves_base_from_the_base_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append((base, kwargs))
                return {}

            management = ManagementFake(
                batch_parameters={"kind": "masked_redraw", "base_generation": "raw-2"},
                generation_records={"raw-2": {"comfy_job": {"graph": SKETCH_GRAPH}}})
            services = base_services(
                directory, management=management, chain_pass=recording_chain_pass)
            finalize("gen-id", services)
            base, _kwargs = calls[-1]
            self.assertEqual(base, SKETCH_GRAPH)

    def test_repaired_raw_uploads_the_picked_picture_as_source_image(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            management = ManagementFake(
                batch_parameters={"kind": "repair", "base_generation": "raw-1"},
                generation_records={"raw-1": {"comfy_job": {"graph": SKETCH_GRAPH}}})
            services = base_services(
                directory, management=management, chain_pass=recording_chain_pass)
            finalize("gen-id", services)
            self.assertIsNotNone(calls[-1]["source_image"])
            uploaded = dict(services.comfyui.uploaded)
            self.assertIn(calls[-1]["source_image"].removeprefix("uploaded-"), uploaded)

    def test_repaired_raw_falls_back_to_the_base_s_own_png_without_a_job_graph(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append((base, kwargs))
                return {}

            management = ManagementFake(
                batch_parameters={"kind": "repair", "base_generation": "raw-1"},
                generation_records={"raw-1": {}})
            services = base_services(
                directory, management=management, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: SKETCH_GRAPH)
            finalize("gen-id", services)
            base, _kwargs = calls[-1]
            self.assertEqual(base, SKETCH_GRAPH)

    def test_repaired_raw_on_a_non_latent_route_recipe_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(
                batch_parameters={"kind": "repair", "base_generation": "raw-3"},
                generation_records={"raw-3": {"comfy_job": {"graph": ANIMA_GRAPH}}})
            services = base_services(directory, management=management)
            with self.assertRaisesRegex(SystemExit, "latent route"):
                finalize("gen-id", services)

    def test_repaired_raw_on_a_layerdiffuse_base_is_rejected_even_with_latent_route(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(
                batch_parameters={"kind": "repair", "base_generation": "raw-4"},
                generation_records={
                    "raw-4": {"comfy_job": {"graph": LAYERDIFFUSE_SKETCH_GRAPH}}})
            services = base_services(directory, management=management)
            with self.assertRaisesRegex(SystemExit, "latent route"):
                finalize("gen-id", services, latent_route=True)

    def test_hires_chain_kind_is_not_treated_as_a_repaired_raw(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append((base, kwargs))
                return {}

            management = ManagementFake(
                batch_parameters={"kind": "hires-chain", "base_generation": "gen-id"})
            services = base_services(
                directory, management=management, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: GRAPH)
            finalize("gen-id", services)
            base, kwargs = calls[-1]
            self.assertEqual(base, GRAPH)
            self.assertIsNone(kwargs["source_image"])

    def test_a_plain_raw_batch_uses_graph_from_png_as_before(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append((base, kwargs))
                return {}

            management = ManagementFake(batch_parameters={"kind": "generate"})
            services = base_services(
                directory, management=management, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: GRAPH)
            finalize("gen-id", services)
            base, kwargs = calls[-1]
            self.assertEqual(base, GRAPH)
            self.assertIsNone(kwargs["source_image"])


class KeepRegionsTest(unittest.TestCase):
    def test_keep_regions_uploads_a_soft_mask_and_passes_it_to_chain_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(directory, chain_pass=recording_chain_pass)
            finalize("gen-id", services, keep_regions=[[0.1, 0.1, 0.4, 0.4]])
            self.assertIsNotNone(calls[-1]["keep_mask_image"])
            uploaded_names = [name for name, _data in services.comfyui.uploaded]
            self.assertTrue(any(name.endswith("-keep-mask.png") for name in uploaded_names))

    def test_keep_regions_empty_leaves_keep_mask_image_none(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(directory, chain_pass=recording_chain_pass)
            finalize("gen-id", services)
            self.assertIsNone(calls[-1]["keep_mask_image"])
            uploaded_names = [name for name, _data in services.comfyui.uploaded]
            self.assertFalse(any(name.endswith("-keep-mask.png") for name in uploaded_names))

    def test_keep_regions_and_strength_are_recorded_in_batch_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            finalize("gen-id", services, keep_regions=[[0.1, 0.1, 0.4, 0.4]],
                     keep_strength=0.4)
            parameters = batch_call(services)[2]["parameters"]
            self.assertEqual(parameters["keep_regions"], [[0.1, 0.1, 0.4, 0.4]])
            self.assertEqual(parameters["keep_strength"], 0.4)

    def test_keep_regions_default_is_not_recorded_in_batch_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            finalize("gen-id", services)
            parameters = batch_call(services)[2]["parameters"]
            self.assertNotIn("keep_regions", parameters)
            self.assertNotIn("keep_strength", parameters)

    def test_keep_regions_composes_with_a_repaired_raw_finalize(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            management = ManagementFake(
                batch_parameters={"kind": "repair", "base_generation": "raw-1"},
                generation_records={"raw-1": {"comfy_job": {"graph": SKETCH_GRAPH}}})
            services = base_services(
                directory, management=management, chain_pass=recording_chain_pass)
            finalize("gen-id", services, keep_regions=[[0.1, 0.1, 0.4, 0.4]])
            self.assertIsNotNone(calls[-1]["source_image"])
            self.assertIsNotNone(calls[-1]["keep_mask_image"])

    def test_is_layerdiffuse_branch_also_receives_the_keep_mask(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def recording_chain_pass(base, size, denoise, prefix, **kwargs):
                calls.append(kwargs)
                return {}

            services = base_services(
                directory, chain_pass=recording_chain_pass,
                graph_from_png=lambda data: copy.deepcopy(LAYERDIFFUSE_SKETCH_GRAPH))
            finalize("gen-id", services, keep_regions=[[0.1, 0.1, 0.4, 0.4]])
            self.assertIsNotNone(calls[-1]["keep_mask_image"])


if __name__ == "__main__":
    unittest.main()
