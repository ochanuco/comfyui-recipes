"""Yukari-anima domain, graph and dispatch tests."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from comfyui_recipes.application.generate import validate_request
from comfyui_recipes.domain.generation.models import PromptPair
from comfyui_recipes.domain.yukari_anima import prompt_style as ps
from comfyui_recipes.domain.yukari_anima.costumes import COSTUMES
from comfyui_recipes.domain.yukari_anima.poses import POSES
from comfyui_recipes.domain.yukari_anima.recipe import (
    negative, positive, refinement_prompt, render_spec,
)
from comfyui_recipes.infrastructure.comfyui import anima_graph
from comfyui_recipes.infrastructure.comfyui.refinement_graph import chain_pass
from comfyui_recipes.interfaces import cli

COFFEE_POSITIVE = (
    "masterpiece, best quality, score_7, 1girl, solo, yuzuki yukari, "
    "vocaloid, voiceroid, (@ixy:0.7), light purple hair, short hair with long "
    "locks, very long sidelocks, purple eyes, hair ornament, (drinking:1.3), "
    "(iced coffee:1.4), (plastic cup:1.45), (clear cup:1.2), (drinking "
    "straw:1.4), (holding cup:1.35), (straw in mouth:1.25), (unamused:1.3), "
    "(half-closed eyes:1.3), (looking at viewer:1.1), (oversized "
    "sweatshirt:1.35), (white sweatshirt:1.2), (sleeves past wrists:1.25), "
    "(denim shorts:1.3), (black pantyhose:1.5), (opaque pantyhose:1.4), "
    "(outdoors:1.3), (street:1.15), (day:1.1), (standing:1.2), (cowboy "
    "shot:1.3), (thighs:1.2), (mature female:1.3), (adult:1.2), (wide "
    "hips:1.2), (thick thighs:1.2), (soft thighs:1.3), (long legs:1.35), "
    "(narrow waist:1.25), adult proportions, long torso, seven heads tall, "
    "simple background, grey background, (large eyes:1.4), (round face:1.3), "
    "(tareme:1.2), (thick eyelashes:1.3), (flat color:1.7), (anime "
    "coloring:1.4), (cel shading:1.2), (limited palette:1.6), (few "
    "colors:1.3), (matte:1.5), (minimal shading:1.2), (flat shadow:1.2), "
    "(thin lineart:1.3), (simple lines:1.3), (minimal lines:1.2), (black "
    "lineart:1.35), (black outline:1.2)"
)

COFFEE_NEGATIVE = (
    "(extra digits:1.5), bad anatomy, bad hands, (detailed:1.3), "
    "(intricate:1.3), (highly detailed:1.3), (fine details:1.2), (colored "
    "lineart:1.4), (colored outline:1.3), (purple lineart:1.2), (skinny:1.3), "
    "(thin legs:1.3), (slender legs:1.2), (slender:1.1), (mug:1.3), (paper "
    "cup:1.2), (hot coffee:1.2), (steam:1.3), (shiny:1.4), (glossy:1.3), "
    "(shiny hair:1.4), (shiny clothes:1.3), (specular highlights:1.3), "
    "(reflection:1.2), (hair highlights:1.2), (watercolor:1.3), (ink "
    "wash:1.3), (painterly:1.3), (hatching:1.5), (crosshatching:1.4), (pencil "
    "shading:1.3), (sketch shading:1.2), (gradient:1.5), (soft shading:1.5), "
    "(sparkling eyes:1.4), (glitter:1.3), (multiple highlights:1.3), "
    "(gradient eyes:1.2), (speed lines:1.45), (motion lines:1.4), (emphasis "
    "lines:1.4), (hood:1.3), (cardigan:1.3), score_1, score_2, score_3, "
    "(fat:1.35), (chubby:1.35), (short legs:1.35), (muscular:1.3), "
    "(toned:1.2), (child:1.3), (loli:1.3), (chibi:1.3), (aged down:1.2)"
)

AMAE_POSITIVE = (
    "masterpiece, best quality, score_7, 1girl, solo, yuzuki yukari, "
    "vocaloid, voiceroid, (@ixy:0.7), light purple hair, short hair with long "
    "locks, very long sidelocks, purple eyes, hair ornament, (smug:1.35), "
    "(doyagao:1.25), (pleading:1.15), (tareme:1.3), (half-closed eyes:1.3), "
    "(unamused:1.15), (head tilt:1.2), (leaning forward:1.3), (looking at "
    "viewer:1.3), (own hands clasped:1.25), (hands up:1.1), (oversized "
    "sweatshirt:1.35), (white sweatshirt:1.2), (sleeves past wrists:1.25), "
    "(denim shorts:1.3), (black pantyhose:1.5), (opaque pantyhose:1.4), "
    "(outdoors:1.3), (shopping:1.15), (street:1.1), (day:1.1), "
    "(standing:1.2), (cowboy shot:1.3), (thighs:1.2), (mature female:1.3), "
    "(adult:1.2), (wide hips:1.2), (thick thighs:1.2), (soft thighs:1.3), "
    "(long legs:1.35), (narrow waist:1.25), adult proportions, long torso, "
    "seven heads tall, simple background, grey background, (large eyes:1.4), "
    "(round face:1.3), (tareme:1.2), (thick eyelashes:1.3), (flat color:1.7), "
    "(anime coloring:1.4), (cel shading:1.2), (limited palette:1.6), (few "
    "colors:1.3), (matte:1.5), (minimal shading:1.2), (flat shadow:1.2), "
    "(thin lineart:1.3), (simple lines:1.3), (minimal lines:1.2), (black "
    "lineart:1.35), (black outline:1.2)"
)

AMAE_NEGATIVE = COFFEE_NEGATIVE.replace(
    "(mug:1.3), (paper cup:1.2), (hot coffee:1.2), (steam:1.3), ", "")

STAND_POSITIVE = (
    "masterpiece, best quality, score_7, 1girl, solo, yuzuki yukari, "
    "vocaloid, voiceroid, (@ixy:0.7), light purple hair, short hair with long "
    "locks, very long sidelocks, purple eyes, hair ornament, (standing:1.5), "
    "(own hands together:1.3), (hands up:1.2), (arched back:1.15), "
    "(smug:1.35), (doyagao:1.25), (tareme:1.3), (half-closed eyes:1.3), "
    "(unamused:1.15), (looking at viewer:1.2), (sneakers:1.3), (white "
    "sneakers:1.2), (oversized sweatshirt:1.35), (white sweatshirt:1.2), "
    "(sleeves past wrists:1.25), (denim shorts:1.3), (black pantyhose:1.5), "
    "(opaque pantyhose:1.4), (from front:1.3), (full body:1.45), (wide "
    "shot:1.3), (thighs:1.1), (mature female:1.3), (adult:1.2), (wide "
    "hips:1.2), (thick thighs:1.2), (soft thighs:1.3), (long legs:1.35), "
    "(narrow waist:1.25), adult proportions, long torso, seven heads tall, "
    "simple background, grey background, (large eyes:1.4), (round face:1.3), "
    "(tareme:1.2), (thick eyelashes:1.3), (flat color:1.7), (anime "
    "coloring:1.4), (cel shading:1.2), (limited palette:1.6), (few "
    "colors:1.3), (matte:1.5), (minimal shading:1.2), (flat shadow:1.2), "
    "(thin lineart:1.3), (simple lines:1.3), (minimal lines:1.2), (black "
    "lineart:1.35), (black outline:1.2)"
)

STAND_NEGATIVE = (
    "(extra digits:1.5), bad anatomy, bad hands, (detailed:1.3), "
    "(intricate:1.3), (highly detailed:1.3), (fine details:1.2), (colored "
    "lineart:1.4), (colored outline:1.3), (purple lineart:1.2), (skinny:1.3), "
    "(thin legs:1.3), (slender legs:1.2), (slender:1.1), (sitting:1.3), "
    "(cowboy shot:1.2), (upper body:1.2), (shiny:1.4), (glossy:1.3), (shiny "
    "hair:1.4), (shiny clothes:1.3), (specular highlights:1.3), "
    "(reflection:1.2), (hair highlights:1.2), (watercolor:1.3), (ink "
    "wash:1.3), (painterly:1.3), (hatching:1.5), (crosshatching:1.4), (pencil "
    "shading:1.3), (sketch shading:1.2), (gradient:1.5), (soft shading:1.5), "
    "(sparkling eyes:1.4), (glitter:1.3), (multiple highlights:1.3), "
    "(gradient eyes:1.2), (speed lines:1.45), (motion lines:1.4), (emphasis "
    "lines:1.4), (hood:1.3), (cardigan:1.3), score_1, score_2, score_3, "
    "(fat:1.35), (chubby:1.35), (short legs:1.35), (muscular:1.3), "
    "(toned:1.2), (child:1.3), (loli:1.3), (chibi:1.3), (aged down:1.2)"
)

REDRAW_STAND_POSITIVE = (
    "masterpiece, best quality, score_7, 1girl, solo, yuzuki yukari, "
    "vocaloid, voiceroid, (@ixy:0.7), light purple hair, short hair with long "
    "locks, very long sidelocks, purple eyes, hair ornament, (standing:1.5), "
    "(own hands together:1.3), (hands up:1.2), (arched back:1.15), "
    "(smug:1.35), (doyagao:1.25), (tareme:1.3), (half-closed eyes:1.3), "
    "(unamused:1.15), (looking at viewer:1.2), (sneakers:1.3), (white "
    "sneakers:1.2), (oversized sweatshirt:1.35), (white sweatshirt:1.2), "
    "(sleeves past wrists:1.25), (denim shorts:1.3), (black pantyhose:1.5), "
    "(opaque pantyhose:1.4), (from front:1.3), (full body:1.45), (wide "
    "shot:1.3), (thighs:1.1), (mature female:1.3), (adult:1.2), (wide "
    "hips:1.2), (thick thighs:1.2), (soft thighs:1.3), (long legs:1.35), "
    "(narrow waist:1.25), adult proportions, long torso, seven heads tall, "
    "simple background, grey background, (large eyes:1.4), (round face:1.3), "
    "(tareme:1.2), (thick eyelashes:1.3), (sketch:1.45), (rough sketch:1.4), "
    "rough lines, sketchy lines, pencil sketch, (unfinished:1.2), "
    "construction lines, (colored pencil (medium):1.2), (soft shading:1.1)"
)

REDRAW_STAND_NEGATIVE = (
    "(clean lineart:1.3), (smooth lines:1.2), (cel shading:1.2), (flat "
    "color:1.2), (brown legwear:1.5), (brown pantyhose:1.4), (detailed "
    "shading:1.5), (heavy shading:1.5), (impasto:1.45), (painterly:1.45), "
    "(bad hands:1.5), (mutated hands:1.5), (extra digits:1.5), (fused "
    "fingers:1.45), (long fingers:1.4), (detailed shading:1.5), (heavy "
    "shading:1.5), (impasto:1.45), (painterly:1.45), (dotted line:1.3), "
    "(dashed line:1.3), (stipple:1.3), (halftone:1.2), (extra digits:1.5), "
    "bad anatomy, bad hands, (skinny:1.3), (thin legs:1.3), (slender "
    "legs:1.2), (slender:1.1), (sitting:1.3), (cowboy shot:1.2), (upper "
    "body:1.2), (shiny:1.4), (glossy:1.3), (shiny hair:1.4), (shiny "
    "clothes:1.3), (specular highlights:1.3), (reflection:1.2), (hair "
    "highlights:1.2), (watercolor:1.3), (ink wash:1.3), (painterly:1.3), "
    "(sparkling eyes:1.4), (glitter:1.3), (multiple highlights:1.3), "
    "(gradient eyes:1.2), (speed lines:1.45), (motion lines:1.4), (emphasis "
    "lines:1.4), (hood:1.3), (cardigan:1.3), score_1, score_2, score_3, "
    "(fat:1.35), (chubby:1.35), (short legs:1.35), (muscular:1.3), "
    "(toned:1.2), (child:1.3), (loli:1.3), (chibi:1.3), (aged down:1.2)"
)


class PromptTest(unittest.TestCase):
    def test_coffee_positive_matches_the_confirmed_render(self):
        self.assertEqual(positive("coffee"), COFFEE_POSITIVE)

    def test_coffee_negative_matches_the_confirmed_render(self):
        self.assertEqual(negative("coffee"), COFFEE_NEGATIVE)

    def test_amae_positive_matches_the_confirmed_render(self):
        self.assertEqual(positive("amae"), AMAE_POSITIVE)

    def test_amae_negative_drops_the_coffee_vessel_ban(self):
        self.assertEqual(negative("amae"), AMAE_NEGATIVE)

    def test_stand_positive_matches_the_confirmed_render(self):
        self.assertEqual(positive("stand"), STAND_POSITIVE)

    def test_stand_negative_matches_the_confirmed_render(self):
        self.assertEqual(negative("stand"), STAND_NEGATIVE)

    def test_brush_carries_its_own_expression_and_costume(self):
        text = positive("brush")
        self.assertTrue(text.startswith(ps.QUALITY + ps.CHARACTER + ps.IDENTITY))
        self.assertIn("(sleepy:1.4)", text)
        self.assertIn(COSTUMES["roomwear"], text)

    def test_expression_override_swaps_the_eyes_block(self):
        default_text = positive("coffee")
        overridden = positive("coffee", expression="doya")
        self.assertNotEqual(default_text, overridden)
        self.assertIn("(tareme:1.3), (half-closed eyes:1.3), (unamused:1.15), ",
                      overridden)
        self.assertNotIn("(unamused:1.3), (half-closed eyes:1.3), ", overridden)


class RefinementPromptTest(unittest.TestCase):
    def test_stand_refinement_prompt_matches_the_confirmed_redraw(self):
        result = refinement_prompt(PromptPair(STAND_POSITIVE, STAND_NEGATIVE))
        self.assertEqual(result.positive, REDRAW_STAND_POSITIVE)
        self.assertEqual(result.negative, REDRAW_STAND_NEGATIVE)


class PoseTableTest(unittest.TestCase):
    def test_step_pose_defaults(self):
        self.assertIn("step", POSES)
        self.assertEqual(POSES["step"].expression, "resting")
        self.assertEqual(POSES["step"].costume, "outing")

    def test_stand_pose_defaults(self):
        self.assertIn("stand", POSES)
        self.assertEqual(POSES["stand"].expression, "doya")
        self.assertEqual(POSES["stand"].costume, "outing")

    def test_sofa_pose_defaults(self):
        self.assertIn("sofa", POSES)
        self.assertEqual(POSES["sofa"].expression, "sleepy")
        self.assertEqual(POSES["sofa"].costume, "roomwear")
        self.assertEqual(POSES["sofa"].canvas, (2048, 1280))


class RenderSpecTest(unittest.TestCase):
    def test_render_spec_fields(self):
        spec = render_spec("coffee", 42, "p")
        self.assertEqual(spec.model_path, ps.MODEL)
        self.assertEqual((spec.width, spec.height), (1280, 2048))
        self.assertEqual(spec.steps, 25)

    def test_pose_canvas_overrides_the_default(self):
        spec = render_spec("sofa", 7, "p")
        self.assertEqual((spec.width, spec.height), (2048, 1280))

    def test_render_spec_default_canvas(self):
        spec = render_spec("stand", 42, "p")
        self.assertEqual(spec.cfg, 3.5)
        self.assertEqual(spec.sampler_name, "er_sde")
        self.assertEqual(spec.scheduler, "normal")
        self.assertIsNone(spec.hires)

    def test_hires_is_rejected(self):
        with self.assertRaises(ValueError):
            render_spec("coffee", 42, "p", hires=2048)

    def test_denoise_override_is_rejected(self):
        with self.assertRaises(ValueError):
            render_spec("coffee", 42, "p", denoise=0.5)


class GraphTest(unittest.TestCase):
    def test_build_graph_node_shape(self):
        spec = render_spec("coffee", 42, "p")
        graph = anima_graph.build_graph(spec)
        self.assertEqual(graph["1"]["class_type"], "UNETLoader")
        self.assertEqual(graph["1"]["inputs"]["unet_name"], ps.MODEL)
        self.assertEqual(graph["2"]["class_type"], "CLIPLoader")
        self.assertEqual(graph["4"]["class_type"], "VAELoader")
        self.assertEqual(graph["5"]["class_type"], "EmptyLatentImage")
        self.assertEqual(graph["6"]["class_type"], "CLIPTextEncode")
        self.assertEqual(graph["6"]["inputs"]["clip"], ["2", 0])
        self.assertEqual(graph["6"]["inputs"]["text"], spec.prompts.positive)
        self.assertEqual(graph["7"]["inputs"]["text"], spec.prompts.negative)
        self.assertEqual(graph["3"]["class_type"], "KSampler")
        self.assertEqual(graph["3"]["inputs"]["model"], ["1", 0])
        self.assertEqual(graph["3"]["inputs"]["positive"], ["6", 0])
        self.assertEqual(graph["3"]["inputs"]["negative"], ["7", 0])
        self.assertEqual(graph["3"]["inputs"]["latent_image"], ["5", 0])
        self.assertEqual(graph["8"]["class_type"], "VAEDecode")
        self.assertEqual(graph["8"]["inputs"]["samples"], ["3", 0])
        self.assertEqual(graph["8"]["inputs"]["vae"], ["4", 0])
        self.assertEqual(graph["9"]["class_type"], "SaveImage")
        self.assertEqual(graph["9"]["inputs"]["images"], ["8", 0])
        self.assertEqual(graph["9"]["inputs"]["filename_prefix"], "p")

    def test_chain_pass_accepts_the_built_graph(self):
        spec = render_spec("coffee", 42, "p")
        base = anima_graph.build_graph(spec)
        out = chain_pass(
            base, 2560, 0.20, "fin-prefix",
            prompt=(spec.prompts.positive, spec.prompts.negative),
            matte_model="birefnet.safetensors", latent_route=False,
            sampler=("euler", "normal"))
        self.assertIsInstance(out, dict)


class ValidateRequestTest(unittest.TestCase):
    def _request(self, **generation):
        return {
            "schema_version": 1,
            "request": {"count": 1, "instruction": "test", "seeds": [42]},
            "generation": {"recipe": "yukari-anima",
                          "parameters": {"pose": "coffee"}, **generation},
            "semantic": {"summary": "test arm"},
        }

    def test_yukari_anima_is_accepted(self):
        validate_request(self._request())

    def test_hires_is_rejected_for_yukari_anima(self):
        request = self._request()
        request["generation"]["parameters"]["hires"] = 2048
        with self.assertRaises(SystemExit):
            validate_request(request)

    def test_denoise_is_rejected_for_yukari_anima(self):
        request = self._request()
        request["generation"]["parameters"]["denoise"] = 0.5
        with self.assertRaises(SystemExit):
            validate_request(request)

    def test_expression_is_rejected_for_yukari(self):
        request = {
            "schema_version": 1,
            "request": {"count": 1, "instruction": "test", "seeds": [42]},
            "generation": {"recipe": "yukari",
                          "parameters": {"pose": "lounge", "expression": "doya"}},
            "semantic": {"summary": "test arm"},
        }
        with self.assertRaises(SystemExit):
            validate_request(request)


class CliTest(unittest.TestCase):
    def test_anima_prompt_json_needs_no_clients(self):
        output = io.StringIO()
        with patch.object(cli, "ChimeraClient") as chimera_class, \
                redirect_stdout(output):
            cli.main(["anima", "prompt", "--pose", "amae", "--json"])
        chimera_class.assert_not_called()
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["positive"], AMAE_POSITIVE)
        self.assertEqual(payload["negative"], AMAE_NEGATIVE)


if __name__ == "__main__":
    unittest.main()
