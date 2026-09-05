"""Yukari-sketch domain, graph, finalize and dispatch tests."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from comfyui_recipes.application.finalize import FinalizeServices, finalize
from comfyui_recipes.application.generate import validate_request
from comfyui_recipes.domain.generation.models import PromptPair, RenderSpec
from comfyui_recipes.domain.yukari_sketch import delivery_style as ds
from comfyui_recipes.domain.yukari_sketch import prompt_style as ps
from comfyui_recipes.domain.yukari_sketch.recipe import (
    negative, positive, refinement_prompt, render_spec,
)
from comfyui_recipes.infrastructure.comfyui.refinement_graph import chain_pass
from comfyui_recipes.infrastructure.comfyui.yukari_graph import build_graph
from comfyui_recipes.interfaces import cli

FIXTURES = Path(__file__).parent / "fixtures"
CINEMA = json.loads((FIXTURES / "yukari-sketch-cinema.json").read_text(encoding="utf-8"))
STAND = json.loads((FIXTURES / "yukari-sketch-stand.json").read_text(encoding="utf-8"))
DATE = json.loads((FIXTURES / "yukari-sketch-date.json").read_text(encoding="utf-8"))
CAFE = json.loads((FIXTURES / "yukari-sketch-cafe.json").read_text(encoding="utf-8"))
HOME = json.loads((FIXTURES / "yukari-sketch-home.json").read_text(encoding="utf-8"))


class PromptTest(unittest.TestCase):
    def test_cinema_positive_matches_the_confirmed_render(self):
        self.assertEqual(positive("cinema"), CINEMA["positive"])

    def test_cinema_negative_matches_the_confirmed_render(self):
        self.assertEqual(negative("cinema"), CINEMA["negative"])

    def test_stand_positive_matches_the_confirmed_render(self):
        self.assertEqual(positive("stand"), STAND["positive"])

    def test_stand_negative_matches_the_confirmed_render(self):
        self.assertEqual(negative("stand"), STAND["negative"])

    def test_date_positive_matches_the_confirmed_render(self):
        self.assertEqual(positive("date"), DATE["positive"])

    def test_date_negative_matches_the_confirmed_render(self):
        self.assertEqual(negative("date"), DATE["negative"])

    def test_cafe_positive_matches_the_confirmed_render(self):
        self.assertEqual(positive("cafe"), CAFE["positive"])

    def test_cafe_negative_matches_the_confirmed_render(self):
        self.assertEqual(negative("cafe"), CAFE["negative"])

    def test_home_positive_matches_the_confirmed_render(self):
        self.assertEqual(positive("home"), HOME["positive"])

    def test_home_negative_matches_the_confirmed_render(self):
        self.assertEqual(negative("home"), HOME["negative"])

    def test_face_override_is_used_only_when_set(self):
        self.assertIn(ps.FACE, positive("cinema"))
        self.assertNotIn(ps.FACE, positive("date"))


class RefinementPromptTest(unittest.TestCase):
    def test_refinement_prompt_is_unchanged(self):
        base = PromptPair(CINEMA["positive"], CINEMA["negative"])
        self.assertEqual(refinement_prompt(base), base)


class RenderSpecTest(unittest.TestCase):
    def test_render_spec_fields(self):
        spec = render_spec("cinema", 7, "p")
        self.assertEqual(spec.model_path, ps.MODEL)
        self.assertEqual((spec.width, spec.height), (832, 1664))
        self.assertEqual(spec.steps, 30)
        self.assertEqual(spec.cfg, 5.0)
        self.assertEqual(spec.sampler_name, "dpmpp_2m")
        self.assertEqual(spec.scheduler, "karras")
        self.assertEqual(spec.denoise, 1.0)
        self.assertIsNone(spec.hires)
        self.assertEqual(spec.loras, (ps.LORA,))

    def test_pose_canvas_overrides_the_default(self):
        spec = render_spec("cafe", 7, "p")
        self.assertEqual((spec.width, spec.height), (1024, 1280))

    def test_hires_is_rejected(self):
        with self.assertRaises(ValueError):
            render_spec("cinema", 7, "p", hires=2048)

    def test_denoise_override_is_rejected(self):
        with self.assertRaises(ValueError):
            render_spec("cinema", 7, "p", denoise=0.5)


class GraphTest(unittest.TestCase):
    def test_lora_is_wired_into_model_and_both_clips(self):
        spec = render_spec("cinema", 7, "ab11")
        graph = build_graph(spec)
        lora_name, weight = ps.LORA
        loader = graph["10"]
        self.assertEqual(loader["class_type"], "LoraLoader")
        self.assertEqual(loader["inputs"]["model"], ["4", 0])
        self.assertEqual(loader["inputs"]["clip"], ["4", 1])
        self.assertEqual(loader["inputs"]["lora_name"], lora_name)
        self.assertEqual(loader["inputs"]["strength_model"], weight)
        self.assertEqual(loader["inputs"]["strength_clip"], weight)
        self.assertEqual(graph["3"]["inputs"]["model"], ["10", 0])
        self.assertEqual(graph["6"]["inputs"]["clip"], ["10", 1])
        self.assertEqual(graph["7"]["inputs"]["clip"], ["10", 1])

    def test_empty_loras_leaves_the_pre_existing_graph_unchanged(self):
        spec = RenderSpec(
            model_path="hassaku-il-v22", prompts=PromptPair("p", "n"),
            width=832, height=1664, seed=7, steps=30, cfg=5.0,
            sampler_name="dpmpp_2m", scheduler="karras", denoise=1.0,
            filename_prefix="ab11")
        graph = build_graph(spec)
        self.assertNotIn("10", graph)
        self.assertEqual(graph["3"]["inputs"]["model"], ["4", 0])
        self.assertEqual(graph["6"]["inputs"]["clip"], ["4", 1])
        self.assertEqual(graph["7"]["inputs"]["clip"], ["4", 1])

    def test_loras_with_hires_is_rejected(self):
        from comfyui_recipes.domain.generation.models import HiresSpec
        spec = RenderSpec(
            model_path="hassaku-il-v22", prompts=PromptPair("p", "n"),
            width=832, height=1664, seed=7, steps=30, cfg=5.0,
            sampler_name="dpmpp_2m", scheduler="karras", denoise=1.0,
            filename_prefix="ab11",
            hires=HiresSpec(1664, 3328, 0.4, "n"),
            loras=(("lora.safetensors", 0.8),))
        with self.assertRaises(ValueError):
            build_graph(spec)

    def test_chain_pass_redraw_model_ref_is_the_loraloader(self):
        spec = render_spec("stand", 7, "ab11")
        base = build_graph(spec)
        out = chain_pass(
            base, 2560, 0.55, "fin-prefix",
            prompt=(spec.prompts.positive, spec.prompts.negative),
            matte_model=None, latent_route=True,
            sampler=ds.FINALIZE_SAMPLER, loader=None, sampling=None)
        redraw_ids = [key for key in out if key.isdecimal() and int(key) > 9
                     and out[key].get("class_type") == "KSampler"]
        redraw = out[redraw_ids[0]]
        self.assertEqual(redraw["inputs"]["model"], ["10", 0])


class ManagementFake:
    def __init__(self, base_graph):
        self.base_graph = base_graph
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
    def upload_image(self, name, data):
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
    def send(self, *args):
        pass


class FinalizeSketchTest(unittest.TestCase):
    def test_sketch_base_picks_its_own_delivery_constants(self):
        spec = render_spec("cinema", 7, "ab11")
        base_graph = build_graph(spec)
        chain_pass_calls = []

        def chain_pass_fake(base, size, denoise, prefix, **kwargs):
            chain_pass_calls.append((size, denoise, kwargs))
            return {}

        with tempfile.TemporaryDirectory() as directory:
            services = FinalizeServices(
                management=ManagementFake(base_graph),
                comfyui=ComfyFake(),
                graph_from_png=lambda data: base_graph,
                chain_pass=chain_pass_fake,
                git_metadata=lambda: {"commit": "commit", "dirty": False},
                notifier=RecordingNotifier(),
                output_root=Path(directory),
                emit=lambda message: None,
            )
            finalize("gen-id", services)

        size, denoise, kwargs = chain_pass_calls[-1]
        self.assertEqual(size, ds.FINALIZE_SIZE)
        self.assertEqual(denoise, ds.FINALIZE_DENOISE)
        self.assertEqual(kwargs["sampler"], ds.FINALIZE_SAMPLER)
        self.assertIsNone(kwargs["loader"])
        self.assertIsNone(kwargs["sampling"])
        self.assertTrue(kwargs["latent_route"])
        self.assertEqual(kwargs["prompt"],
                         (spec.prompts.positive, spec.prompts.negative))


class ValidateRequestTest(unittest.TestCase):
    def _request(self, **generation):
        return {
            "schema_version": 1,
            "request": {"count": 1, "instruction": "test", "seeds": [7]},
            "generation": {"recipe": "yukari-sketch",
                          "parameters": {"pose": "cinema"}, **generation},
            "semantic": {"summary": "test arm"},
        }

    def test_yukari_sketch_is_accepted(self):
        validate_request(self._request())

    def test_hires_is_rejected_for_yukari_sketch(self):
        request = self._request()
        request["generation"]["parameters"]["hires"] = 2048
        with self.assertRaises(SystemExit):
            validate_request(request)

    def test_denoise_is_rejected_for_yukari_sketch(self):
        request = self._request()
        request["generation"]["parameters"]["denoise"] = 0.5
        with self.assertRaises(SystemExit):
            validate_request(request)

    def test_expression_is_rejected_for_yukari_sketch(self):
        request = self._request()
        request["generation"]["parameters"]["expression"] = "doya"
        with self.assertRaises(SystemExit):
            validate_request(request)


class CliTest(unittest.TestCase):
    def test_sketch_prompt_json_needs_no_clients(self):
        output = io.StringIO()
        with patch.object(cli, "ChimeraClient") as chimera_class, \
                redirect_stdout(output):
            cli.main(["sketch", "prompt", "--pose", "cinema", "--json"])
        chimera_class.assert_not_called()
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["positive"], CINEMA["positive"])
        self.assertEqual(payload["negative"], CINEMA["negative"])


if __name__ == "__main__":
    unittest.main()
