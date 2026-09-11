"""Yukari-sketch domain, graph, finalize and dispatch tests."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from comfyui_recipes.application.finalize import FinalizeServices, finalize
from comfyui_recipes.application.generate import validate_request
from comfyui_recipes.domain.generation.models import PromptPair, RenderSpec
from comfyui_recipes.domain.yukari_sketch import delivery_style as ds
from comfyui_recipes.domain.yukari_sketch import prompt_style as ps
from comfyui_recipes.domain.yukari_sketch.models import Edit, Pose
from comfyui_recipes.domain.yukari_sketch.poses import POSES as SKETCH_POSES
from comfyui_recipes.domain.yukari_sketch.recipe import (
    PART_NAMES, _apply, departures, identity_tags, lineage, negative,
    plain_request, positive, positive_parts, refinement_prompt, render_spec,
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
BATH = json.loads((FIXTURES / "yukari-sketch-bath.json").read_text(encoding="utf-8"))


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

    def test_bath_positive_matches_the_confirmed_render(self):
        self.assertEqual(positive("bath"), BATH["positive"])

    def test_bath_negative_matches_the_confirmed_render(self):
        self.assertEqual(negative("bath"), BATH["negative"])

    def test_bath_costume_swaps_legwear_and_bans_the_tights(self):
        self.assertNotIn(ps.LEGWEAR, positive("bath"))
        self.assertIn("(bare legs:1.3), (barefoot:1.25), ", positive("bath"))
        self.assertTrue(negative("bath").endswith("(shoes:1.4)" + ps.GLOSS_BAN))
        self.assertEqual(negative("home"), ps.NEGATIVE + ps.GLOSS_BAN)

    def test_every_pose_ends_with_the_finish_and_the_gloss_ban(self):
        for pose in ("cinema", "stand", "date", "cafe", "home", "bath"):
            self.assertTrue(positive(pose).endswith(", " + ps.FINISH), pose)
            self.assertTrue(negative(pose).endswith(ps.GLOSS_BAN), pose)

    def test_face_override_is_used_only_when_set(self):
        self.assertIn(ps.FACE, positive("cinema"))
        self.assertNotIn(ps.FACE, positive("date"))


class PartsTest(unittest.TestCase):
    def test_parts_concatenate_to_the_confirmed_render_byte_for_byte(self):
        for fixture, pose in ((CINEMA, "cinema"), (STAND, "stand"),
                              (DATE, "date"), (CAFE, "cafe"), (HOME, "home"),
                              (BATH, "bath")):
            with self.subTest(pose=pose):
                joined = "".join(text for _, text in positive_parts(pose))
                self.assertEqual(joined, fixture["positive"])

    def test_part_names_match_the_declared_order(self):
        self.assertEqual(
            [name for name, _ in positive_parts("cinema")], list(PART_NAMES))
        self.assertEqual(PART_NAMES, (
            "quality", "identity", "costume", "pose", "proportion",
            "background", "legwear", "face", "body", "finish"))


class PoseModelTest(unittest.TestCase):
    def test_face_and_face_edits_are_mutually_exclusive(self):
        with self.assertRaises(ValueError):
            Pose(action="x", face="literal face, ",
                 face_edits=(Edit("replace", "a", "b"),))

    def test_face_edit_with_absent_needle_raises_when_applied(self):
        bad = Pose(action="x", face_edits=(Edit("replace", "not present", "y"),))
        with self.assertRaises(AssertionError):
            _apply(ps.FACE, bad.face_edits)

    def test_no_pose_uses_a_full_face_override(self):
        for name, pose in SKETCH_POSES.items():
            with self.subTest(pose=name):
                self.assertIsNone(pose.face)


class DeparturesTest(unittest.TestCase):
    def test_date_departs_from_cinema_on_costume_pose_and_face(self):
        self.assertEqual(departures("date"), {
            "parent": "cinema",
            "face_override": False,
            "parts": {
                "costume": ["-short dress", "+long dress:1.15",
                           "+knee-length dress:1.1"],
                "pose": ["+sneakers:1.3", "+white sneakers:1.2"],
                "face": ["+jitome:1.25", "half-closed eyes 1.2 -> 1.15",
                        "-unamused", "+smirk:1.2", "+smug:1.15",
                        "+blush:1.1", "+head tilt:1.1"],
            },
        })

    def test_stand_has_no_parent_and_only_departs_on_pose(self):
        dep = departures("stand")
        self.assertIsNone(dep["parent"])
        self.assertFalse(dep["face_override"])
        self.assertEqual(set(dep["parts"]), {"pose"})

    def test_cafe_face_reports_a_moved_tag_instead_of_a_drop_and_re_add(self):
        self.assertEqual(departures("cafe")["parts"]["face"], [
            "jitome 1.25 -> 1.2", "-half-closed eyes", "-smirk", "-smug",
            "-closed mouth", "+upturned eyes:1.3", "+looking up:1.15",
            "looking at viewer moved", "+light smile:1.1",
            "+parted lips:1.2", "blush 1.1 -> 1.15",
        ])

    def test_lineage_covers_every_pose(self):
        self.assertEqual(set(lineage()), set(SKETCH_POSES))
        self.assertEqual(lineage()["date"], departures("date"))


class IdentityTagsTest(unittest.TestCase):
    def test_default_costume_carries_cardigan_and_hood_but_no_jitome(self):
        self.assertEqual(identity_tags("cinema"), frozenset({
            "light purple hair", "short hair with long locks",
            "very long sidelocks", "purple eyes", "hair ornament",
            "tareme", "black hooded cardigan", "rabbit hood",
        }))

    def test_date_face_override_adds_jitome(self):
        self.assertEqual(identity_tags("date"), frozenset({
            "light purple hair", "short hair with long locks",
            "very long sidelocks", "purple eyes", "hair ornament",
            "tareme", "jitome", "black hooded cardigan", "rabbit hood",
        }))

    def test_bath_costume_has_no_cardigan_or_hood(self):
        self.assertEqual(identity_tags("bath"), frozenset({
            "light purple hair", "short hair with long locks",
            "very long sidelocks", "purple eyes", "hair ornament",
            "tareme", "jitome",
        }))

    def test_costume_override_forces_the_cardigan_back_in(self):
        self.assertIn("black hooded cardigan", identity_tags("bath", "default"))
        self.assertIn("rabbit hood", identity_tags("bath", "default"))


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
            sampler=ds.FINALIZE_SAMPLER, loader=None, sampling=None,
            canvas=(spec.width, spec.height))
        redraw_ids = [key for key in out if key.isdecimal() and int(key) > 9
                     and out[key].get("class_type") == "KSampler"]
        redraw = out[redraw_ids[0]]
        self.assertEqual(redraw["inputs"]["model"], ["10", 0])


class LayerDiffuseGraphTest(unittest.TestCase):
    def test_layerdiffuse_wires_apply_and_rgba_decode(self):
        spec = render_spec("cinema", 7, "ab11", layerdiffuse=True)
        graph = build_graph(spec)
        apply_node = graph["12"]
        self.assertEqual(apply_node["class_type"], "LayeredDiffusionApply")
        self.assertEqual(apply_node["inputs"]["model"], ["10", 0])
        self.assertEqual(apply_node["inputs"]["config"],
                         "SDXL, Conv Injection")
        self.assertEqual(apply_node["inputs"]["weight"], 1.0)
        self.assertEqual(graph["3"]["inputs"]["model"], ["12", 0])
        decode_node = graph["13"]
        self.assertEqual(decode_node["class_type"], "LayeredDiffusionDecode")
        self.assertEqual(decode_node["inputs"]["samples"], ["3", 0])
        self.assertEqual(decode_node["inputs"]["images"], ["8", 0])
        self.assertEqual(decode_node["inputs"]["sd_version"], "SDXL")
        self.assertEqual(decode_node["inputs"]["sub_batch_size"], 16)
        self.assertEqual(graph["14"], {"class_type": "InvertMask",
                                       "inputs": {"mask": ["13", 1]}})
        self.assertEqual(graph["15"], {"class_type": "JoinImageWithAlpha",
                                       "inputs": {"image": ["13", 0],
                                                  "alpha": ["14", 0]}})
        self.assertEqual(graph["9"]["inputs"]["images"], ["15", 0])
        self.assertEqual(graph["8"]["class_type"], "VAEDecode")

    def test_layerdiffuse_apply_reads_weight_and_config_from_spec(self):
        spec = replace(render_spec("cinema", 7, "ab11", layerdiffuse=True),
                       layerdiffuse_weight=0.7,
                       layerdiffuse_config="SDXL, Attention Injection")
        graph = build_graph(spec)
        apply_node = graph["12"]
        self.assertEqual(apply_node["inputs"]["weight"], 0.7)
        self.assertEqual(apply_node["inputs"]["config"],
                         "SDXL, Attention Injection")

    def test_layerdiffuse_rejects_a_canvas_not_a_multiple_of_64(self):
        spec = RenderSpec(
            model_path="hassaku-il-v22", prompts=PromptPair("p", "n"),
            width=830, height=1664, seed=7, steps=30, cfg=5.0,
            sampler_name="dpmpp_2m", scheduler="karras", denoise=1.0,
            filename_prefix="ab11", layerdiffuse=True)
        with self.assertRaises(ValueError):
            build_graph(spec)

    def test_chain_pass_on_a_layerdiffuse_graph_finds_the_vae_decode(self):
        spec = render_spec("cinema", 7, "ab11", layerdiffuse=True)
        base = build_graph(spec)
        out = chain_pass(
            base, 2560, 0.55, "fin-prefix",
            prompt=(spec.prompts.positive, spec.prompts.negative),
            matte_model=None, latent_route=True,
            sampler=ds.FINALIZE_SAMPLER, loader=None, sampling=None,
            canvas=(spec.width, spec.height))
        redraw_ids = [key for key in out if key.isdecimal() and int(key) > 15
                     and out[key].get("class_type") == "VAEDecode"]
        self.assertEqual(len(redraw_ids), 1)
        self.assertEqual(out[redraw_ids[0]]["inputs"]["vae"], ["4", 2])


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
                image_size=lambda data: (832, 1664),
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

    def test_layerdiffuse_true_is_accepted_for_yukari_sketch(self):
        request = self._request()
        request["generation"]["parameters"]["layerdiffuse"] = True
        validate_request(request)

    def test_layerdiffuse_non_bool_is_rejected(self):
        request = self._request()
        request["generation"]["parameters"]["layerdiffuse"] = "true"
        with self.assertRaises(SystemExit):
            validate_request(request)


class PlainRequestTest(unittest.TestCase):
    def test_date_at_a_given_seed_and_default_costume(self):
        payload = plain_request("date", 737373737)
        self.assertEqual(payload["request"]["seeds"], [737373737])
        self.assertEqual(payload["generation"]["parameters"],
                         {"pose": "date", "costume": "outing"})
        self.assertNotIn("patches", payload["generation"])
        validate_request(payload)

    def test_stand_with_an_explicit_seed_works(self):
        payload = plain_request("stand", 5)
        self.assertEqual(payload["request"]["seeds"], [5])
        validate_request(payload)

    def test_explicit_costume_overrides_the_pose_default(self):
        payload = plain_request("date", 737373737, costume="default")
        self.assertEqual(payload["generation"]["parameters"]["costume"],
                         "default")


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

    def test_sketch_lineage_json_needs_no_clients(self):
        output = io.StringIO()
        with patch.object(cli, "ChimeraClient") as chimera_class, \
                redirect_stdout(output):
            cli.main(["sketch", "lineage", "--json"])
        chimera_class.assert_not_called()
        payload = json.loads(output.getvalue())
        self.assertEqual(set(payload), set(SKETCH_POSES))
        self.assertEqual(payload["date"], departures("date"))

    def test_sketch_lineage_single_pose_json(self):
        output = io.StringIO()
        with redirect_stdout(output):
            cli.main(["sketch", "lineage", "--pose", "date", "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(payload, {"date": departures("date")})

    def test_sketch_plain_json_needs_no_clients(self):
        output = io.StringIO()
        with patch.object(cli, "ChimeraClient") as chimera_class, \
                redirect_stdout(output):
            cli.main(["sketch", "plain", "--pose", "date", "--seed",
                     "737373737"])
        chimera_class.assert_not_called()
        payload = json.loads(output.getvalue())
        self.assertEqual(payload, plain_request("date", 737373737))

    def test_sketch_plain_without_seed_exits(self):
        output = io.StringIO()
        with redirect_stdout(output):
            with self.assertRaises(SystemExit):
                cli.main(["sketch", "plain", "--pose", "date"])


if __name__ == "__main__":
    unittest.main()
