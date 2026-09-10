"""Tests pinning repair_graph's transformation on the two reference graphs.

`repair-graph-raw.json` is a plain generation (one SaveImage). `repair-graph-
finalize.json` is a finalize output graph: redraw + birefnet matte + purple-
stroke delivery, all downstream of the redraw's own VAEDecode. Both were
captured from a real worker submission; see AGENTS.md for how to regenerate
fixtures like these if the node packs' contracts ever change.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from comfyui_recipes.domain.generation.models import PromptPair, RenderSpec
from comfyui_recipes.infrastructure.comfyui.base_graph import base_roles
from comfyui_recipes.infrastructure.comfyui.repair_graph import (
    DELIVERED_SUFFIX,
    MATTE_SUFFIX,
    masked_redraw_graph,
    redraw_canvas,
    repair_graph,
    source_prompts,
    splice_repair,
)
from comfyui_recipes.infrastructure.comfyui.yukari_graph import build_graph

FIXTURES = Path(__file__).parent / "fixtures"
RAW = json.loads((FIXTURES / "repair-graph-raw.json").read_text())
FINALIZE = json.loads((FIXTURES / "repair-graph-finalize.json").read_text())

# A layerdiffuse raw: node 12 LayeredDiffusionApply wraps the model, 13
# LayeredDiffusionDecode/14 InvertMask/15 JoinImageWithAlpha compute the RGBA
# picture from VAEDecode 8, and SaveImage 9 reads the Join.
LAYERDIFFUSE = build_graph(RenderSpec(
    model_path="hassaku-il-v22", prompts=PromptPair("p", "n"),
    width=832, height=1664, seed=7, steps=30, cfg=5.0,
    sampler_name="dpmpp_2m", scheduler="karras", denoise=1.0,
    filename_prefix="ld-src", layerdiffuse=True))


class SourcePromptsTest(unittest.TestCase):
    def test_raw_graph_reads_the_only_prompt_pair(self):
        positive, negative = source_prompts(RAW)
        self.assertEqual(positive, RAW["6"]["inputs"]["text"])
        self.assertEqual(negative, RAW["7"]["inputs"]["text"])

    def test_finalize_graph_reads_the_redraw_prompt_pair_not_pass1(self):
        # The fixture's pass-1 and redraw prompts happen to carry the same
        # text; what matters is which node source_prompts reads them from.
        positive, negative = source_prompts(FINALIZE)
        self.assertEqual(positive, FINALIZE["15"]["inputs"]["text"])
        self.assertEqual(negative, FINALIZE["16"]["inputs"]["text"])


class RepairGraphRawTest(unittest.TestCase):
    def setUp(self):
        self.graph = repair_graph(
            RAW, image_name="src.png", mask_name="mask.png",
            positive="p", negative="n", seed=99, denoise=0.6, size=1024,
            prefix="rep-abc-s99")

    def test_keeps_only_the_shared_loaders(self):
        kept_original = {key for key in self.graph if key in RAW}
        self.assertEqual(kept_original, {"4", "10", "9"})

    def test_kept_loader_nodes_are_untouched(self):
        self.assertEqual(self.graph["4"], RAW["4"])
        self.assertEqual(self.graph["10"], RAW["10"])

    def test_the_only_saveimage_is_rewired_to_the_stitch_output_and_prefixed(self):
        save = self.graph["9"]
        self.assertEqual(save["class_type"], "SaveImage")
        self.assertEqual(save["inputs"]["filename_prefix"], "rep-abc-s99")
        stitch_id = save["inputs"]["images"][0]
        self.assertEqual(self.graph[stitch_id]["class_type"], "InpaintStitchImproved")

    def test_no_extra_saveimage_is_added_when_one_directly_consumes_the_stitch(self):
        saves = [node for node in self.graph.values()
                if node["class_type"] == "SaveImage"]
        self.assertEqual(len(saves), 1)

    def test_new_subgraph_wires_crop_encode_sample_decode_stitch(self):
        crop_id, crop = next(
            (key, node) for key, node in self.graph.items()
            if node["class_type"] == "InpaintCropImproved")
        self.assertEqual(crop["inputs"]["output_target_width"], 1024)
        self.assertEqual(crop["inputs"]["output_target_height"], 1024)
        self.assertEqual(crop["inputs"]["output_padding"], "32")
        self.assertIs(crop["inputs"]["preresize"], False)
        self.assertIs(crop["inputs"]["mask_fill_holes"], True)

        load_image = self.graph[crop["inputs"]["image"][0]]
        self.assertEqual(load_image["class_type"], "LoadImage")
        self.assertEqual(load_image["inputs"]["image"], "src.png")

        to_mask = self.graph[crop["inputs"]["mask"][0]]
        self.assertEqual(to_mask["class_type"], "ImageToMask")
        self.assertEqual(to_mask["inputs"]["channel"], "red")
        load_mask = self.graph[to_mask["inputs"]["image"][0]]
        self.assertEqual(load_mask["inputs"]["image"], "mask.png")

        encode_id, encode = next(
            (key, node) for key, node in self.graph.items()
            if node["class_type"] == "VAEEncode")
        self.assertEqual(encode["inputs"]["vae"], ["4", 2])
        self.assertEqual(encode["inputs"]["pixels"], [crop_id, 1])

        noise_mask_id, noise_mask = next(
            (key, node) for key, node in self.graph.items()
            if node["class_type"] == "SetLatentNoiseMask")
        self.assertEqual(noise_mask["inputs"]["samples"], [encode_id, 0])
        self.assertEqual(noise_mask["inputs"]["mask"], [crop_id, 2])

        sample_id, sample = next(
            (key, node) for key, node in self.graph.items()
            if node["class_type"] == "KSampler")
        self.assertEqual(sample["inputs"]["model"], ["10", 0])
        self.assertEqual(sample["inputs"]["latent_image"], [noise_mask_id, 0])
        self.assertEqual(sample["inputs"]["seed"], 99)
        self.assertEqual(sample["inputs"]["denoise"], 0.6)
        self.assertEqual(sample["inputs"]["steps"], RAW["3"]["inputs"]["steps"])
        self.assertEqual(sample["inputs"]["cfg"], RAW["3"]["inputs"]["cfg"])
        self.assertEqual(sample["inputs"]["sampler_name"],
                         RAW["3"]["inputs"]["sampler_name"])
        self.assertEqual(sample["inputs"]["scheduler"],
                         RAW["3"]["inputs"]["scheduler"])

        positive_node = self.graph[sample["inputs"]["positive"][0]]
        negative_node = self.graph[sample["inputs"]["negative"][0]]
        self.assertEqual(positive_node["inputs"]["text"], "p")
        self.assertEqual(positive_node["inputs"]["clip"], ["10", 1])
        self.assertEqual(negative_node["inputs"]["text"], "n")

        # The raw fixture's own VAEDecode ("8") is dropped along with its
        # sampler, so the repair's own decode is the only one left.
        decode_id, decode = next(
            (key, node) for key, node in self.graph.items()
            if node["class_type"] == "VAEDecode")
        self.assertEqual(decode["inputs"]["samples"], [sample_id, 0])
        self.assertEqual(decode["inputs"]["vae"], ["4", 2])

        stitch_id = self.graph["9"]["inputs"]["images"][0]
        stitch_node = self.graph[stitch_id]
        self.assertEqual(stitch_node["class_type"], "InpaintStitchImproved")
        self.assertEqual(stitch_node["inputs"]["stitcher"], [crop_id, 0])
        self.assertEqual(stitch_node["inputs"]["inpainted_image"], [decode_id, 0])

    def test_does_not_mutate_the_source_graph(self):
        before = json.dumps(RAW, sort_keys=True)
        repair_graph(RAW, image_name="x.png", mask_name="m.png",
                    positive="p", negative="n", seed=1, denoise=0.5,
                    size=512, prefix="rep")
        self.assertEqual(json.dumps(RAW, sort_keys=True), before)


class RepairGraphFinalizeTest(unittest.TestCase):
    def setUp(self):
        self.graph = repair_graph(
            FINALIZE, image_name="src.png", mask_name="mask.png",
            positive="p", negative="n", seed=42, denoise=0.6, size=1024,
            prefix="rep-xyz-s42")

    def test_keeps_only_the_shared_loaders_plus_the_whole_tail(self):
        kept_original = {key for key in self.graph if key in FINALIZE}
        self.assertEqual(
            kept_original,
            {"4", "10", "9", "17", "18", "19", "20", "21", "22", "23", "24"})

    def test_pass1_and_old_redraw_sampling_nodes_are_dropped(self):
        dropped = {"3", "5", "6", "7", "8", "11", "13", "15", "16"}
        self.assertFalse(dropped & set(self.graph))

    def test_raw_saveimage_is_rewired_to_the_stitch_and_gets_the_bare_prefix(self):
        save = self.graph["9"]
        self.assertEqual(save["inputs"]["filename_prefix"], "rep-xyz-s42")
        stitch_id = save["inputs"]["images"][0]
        self.assertEqual(self.graph[stitch_id]["class_type"], "InpaintStitchImproved")

    def test_matte_saveimage_keeps_its_own_suffix(self):
        save = self.graph["20"]
        self.assertEqual(save["inputs"]["filename_prefix"],
                         "rep-xyz-s42" + MATTE_SUFFIX)
        # unchanged wiring -- it reads the birefnet matte-to-image node, not
        # the redraw's own decode.
        self.assertEqual(save["inputs"]["images"], ["19", 0])

    def test_delivered_saveimage_keeps_its_own_suffix(self):
        save = self.graph["24"]
        self.assertEqual(save["inputs"]["filename_prefix"],
                         "rep-xyz-s42" + DELIVERED_SUFFIX)

    def test_only_three_saveimage_nodes_survive(self):
        saves = [node for node in self.graph.values()
                if node["class_type"] == "SaveImage"]
        self.assertEqual(len(saves), 3)

    def test_bg_removal_loader_is_pulled_in_though_not_downstream_of_the_decode(self):
        self.assertIn("17", self.graph)
        self.assertEqual(self.graph["17"], FINALIZE["17"])
        remove_background = self.graph["18"]
        self.assertEqual(remove_background["inputs"]["bg_removal_model"], ["17", 0])

    def test_tail_refs_to_the_old_decode_are_rewired_to_the_stitch(self):
        stitch_id = self.graph["9"]["inputs"]["images"][0]
        remove_background = self.graph["18"]
        self.assertEqual(remove_background["inputs"]["image"], [stitch_id, 0])
        repin = self.graph["21"]
        self.assertEqual(repin["inputs"]["image"], [stitch_id, 0])

    def test_tail_refs_not_pointing_at_the_old_decode_are_untouched(self):
        deliver = self.graph["22"]
        self.assertEqual(deliver["inputs"]["image"], ["21", 0])
        self.assertEqual(deliver["inputs"]["matte"], ["18", 0])

    def test_sampler_settings_come_from_the_redraw_pass_not_pass1(self):
        sample = next(node for node in self.graph.values()
                     if node["class_type"] == "KSampler")
        self.assertEqual(sample["inputs"]["sampler_name"],
                         FINALIZE["13"]["inputs"]["sampler_name"])
        self.assertEqual(sample["inputs"]["scheduler"],
                         FINALIZE["13"]["inputs"]["scheduler"])
        self.assertEqual(sample["inputs"]["steps"], FINALIZE["13"]["inputs"]["steps"])
        self.assertEqual(sample["inputs"]["cfg"], FINALIZE["13"]["inputs"]["cfg"])
        self.assertNotEqual(sample["inputs"]["sampler_name"],
                            FINALIZE["3"]["inputs"]["sampler_name"])

    def test_vae_ref_matches_the_redraw_decode(self):
        encode = next(node for node in self.graph.values()
                     if node["class_type"] == "VAEEncode")
        self.assertEqual(encode["inputs"]["vae"], FINALIZE["14"]["inputs"]["vae"])


class RepairGraphLayerDiffuseTest(unittest.TestCase):
    def setUp(self):
        self.graph = repair_graph(
            LAYERDIFFUSE, image_name="src.png", mask_name="mask.png",
            positive="p", negative="n", seed=11, denoise=0.6, size=1024,
            prefix="rep-ld-s11")

    def test_ld_decode_and_invert_mask_are_dropped(self):
        self.assertNotIn("13", self.graph)
        self.assertNotIn("14", self.graph)

    def test_pass1_and_apply_nodes_are_not_pulled_back_in(self):
        dropped = {"3", "5", "6", "7", "8", "12"}
        self.assertFalse(dropped & set(self.graph))

    def test_join_is_rewired_to_the_stitch_and_the_staged_masks_alpha(self):
        join = self.graph["15"]
        self.assertEqual(join["class_type"], "JoinImageWithAlpha")
        stitch_id = join["inputs"]["image"][0]
        self.assertEqual(self.graph[stitch_id]["class_type"], "InpaintStitchImproved")
        alpha_ref = join["inputs"]["alpha"]
        self.assertEqual(alpha_ref[1], 1)
        load_image = self.graph[alpha_ref[0]]
        self.assertEqual(load_image["class_type"], "LoadImage")
        self.assertEqual(load_image["inputs"]["image"], "src.png")

    def test_exactly_one_saveimage_fed_by_the_join_with_the_prefix(self):
        saves = [(key, node) for key, node in self.graph.items()
                if node["class_type"] == "SaveImage"]
        self.assertEqual(len(saves), 1)
        save_id, save = saves[0]
        self.assertEqual(save_id, "9")
        self.assertEqual(save["inputs"]["filename_prefix"], "rep-ld-s11")
        self.assertEqual(save["inputs"]["images"], ["15", 0])

    def test_base_roles_resolves_the_single_save_as_stitched(self):
        roles = base_roles(self.graph)
        self.assertEqual(roles.save_id, "9")
        self.assertTrue(roles.stitched)

    def test_reroll_model_is_not_the_layereddiffusionapply_node(self):
        sample = next(node for node in self.graph.values()
                     if node["class_type"] == "KSampler")
        self.assertEqual(sample["inputs"]["model"], ["4", 0])

    def test_does_not_mutate_the_source_graph(self):
        before = json.dumps(LAYERDIFFUSE, sort_keys=True)
        repair_graph(LAYERDIFFUSE, image_name="x.png", mask_name="m.png",
                    positive="p", negative="n", seed=1, denoise=0.5,
                    size=512, prefix="rep-ld")
        self.assertEqual(json.dumps(LAYERDIFFUSE, sort_keys=True), before)


class SpliceRepairLayerDiffuseTest(unittest.TestCase):
    def test_reroll_model_unwraps_the_layereddiffusionapply_node(self):
        graph = splice_repair(
            LAYERDIFFUSE, mask_name="mask.png", positive="p", negative="n",
            denoise=0.6, size=1024)
        sample = next(node for node in graph.values()
                     if node["class_type"] == "KSampler"
                     and node["inputs"]["denoise"] == 0.6)
        self.assertEqual(sample["inputs"]["model"], ["4", 0])


class MaskedRedrawGraphTest(unittest.TestCase):
    def test_repair_graph_keeps_the_inpaint_crop_defaults(self):
        graph = repair_graph(
            RAW, image_name="src.png", mask_name="mask.png",
            positive="p", negative="n", seed=99, denoise=0.6, size=1024,
            prefix="rep-abc-s99")
        crop = next(node for node in graph.values()
                   if node["class_type"] == "InpaintCropImproved")
        self.assertEqual(crop["inputs"]["mask_expand_pixels"], 0)
        self.assertEqual(crop["inputs"]["mask_blend_pixels"], 32)

    def test_mask_padding_and_feather_reach_the_inpaint_crop(self):
        graph = masked_redraw_graph(
            RAW, image_name="src.png", mask_name="mask.png",
            positive="p", negative="n", seed=99, denoise=0.48,
            mask_padding=24, mask_feather=8, size=768, prefix="mrd-abc-s99")
        crop = next(node for node in graph.values()
                   if node["class_type"] == "InpaintCropImproved")
        self.assertEqual(crop["inputs"]["mask_expand_pixels"], 24)
        self.assertEqual(crop["inputs"]["mask_blend_pixels"], 8)
        self.assertEqual(crop["inputs"]["output_target_width"], 768)
        self.assertEqual(crop["inputs"]["output_target_height"], 768)

    def test_otherwise_shaped_like_repair_graph(self):
        graph = masked_redraw_graph(
            RAW, image_name="src.png", mask_name="mask.png",
            positive="p", negative="n", seed=99, denoise=0.6,
            mask_padding=0, mask_feather=32, size=1024, prefix="mrd-abc-s99")
        save = graph["9"]
        self.assertEqual(save["class_type"], "SaveImage")
        self.assertEqual(save["inputs"]["filename_prefix"], "mrd-abc-s99")
        sample = next(node for node in graph.values()
                     if node["class_type"] == "KSampler")
        self.assertEqual(sample["inputs"]["seed"], 99)
        self.assertEqual(sample["inputs"]["denoise"], 0.6)

    def test_does_not_mutate_the_source_graph(self):
        before = json.dumps(RAW, sort_keys=True)
        masked_redraw_graph(
            RAW, image_name="x.png", mask_name="m.png", positive="p",
            negative="n", seed=1, denoise=0.5, mask_padding=10,
            mask_feather=20, size=512, prefix="mrd")
        self.assertEqual(json.dumps(RAW, sort_keys=True), before)


class RepairGraphErrorsTest(unittest.TestCase):
    def test_a_graph_with_no_final_decode_raises(self):
        broken = {"3": {"class_type": "KSampler", "inputs": {
            "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["5", 0], "seed": 1, "steps": 1, "cfg": 1,
            "sampler_name": "euler", "scheduler": "normal", "denoise": 1}}}
        with self.assertRaises(ValueError):
            repair_graph(broken, image_name="i", mask_name="m",
                        positive="p", negative="n", seed=1, denoise=0.5,
                        size=512, prefix="rep")

    def test_a_graph_with_two_final_decodes_raises(self):
        broken = {
            "4": {"class_type": "DiffusersLoader", "inputs": {"model_path": "m"}},
            "8a": {"class_type": "VAEDecode", "inputs": {
                "samples": ["3a", 0], "vae": ["4", 2]}},
            "8b": {"class_type": "VAEDecode", "inputs": {
                "samples": ["3b", 0], "vae": ["4", 2]}},
            "3a": {"class_type": "KSampler", "inputs": {
                "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
                "latent_image": ["5", 0], "seed": 1, "steps": 1, "cfg": 1,
                "sampler_name": "euler", "scheduler": "normal", "denoise": 1}},
            "3b": {"class_type": "KSampler", "inputs": {
                "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
                "latent_image": ["5", 0], "seed": 1, "steps": 1, "cfg": 1,
                "sampler_name": "euler", "scheduler": "normal", "denoise": 1}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": "p"}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": "n"}},
            "5": {"class_type": "EmptyLatentImage", "inputs": {}},
            "9a": {"class_type": "SaveImage", "inputs": {
                "images": ["8a", 0], "filename_prefix": "a"}},
            "9b": {"class_type": "SaveImage", "inputs": {
                "images": ["8b", 0], "filename_prefix": "b"}},
        }
        with self.assertRaises(ValueError):
            repair_graph(broken, image_name="i", mask_name="m",
                        positive="p", negative="n", seed=1, denoise=0.5,
                        size=512, prefix="rep")


class RedrawCanvasTest(unittest.TestCase):
    def test_finalize_graph_reads_the_latent_upscale_size(self):
        self.assertEqual(redraw_canvas(FINALIZE), (1280, 2560))

    def test_raw_graph_falls_back_to_the_empty_latent_size(self):
        self.assertEqual(redraw_canvas(RAW), (832, 1664))


class SpliceRepairFinalizeTest(unittest.TestCase):
    def setUp(self):
        self.graph = splice_repair(
            FINALIZE, mask_name="mask.png", positive="p", negative="n",
            denoise=0.6, size=1024)

    def test_nothing_is_pruned(self):
        self.assertTrue(set(FINALIZE) <= set(self.graph))

    def test_the_crops_image_is_the_redraws_own_decode(self):
        crop = next(node for node in self.graph.values()
                   if node["class_type"] == "InpaintCropImproved")
        self.assertEqual(crop["inputs"]["image"], ["14", 0])
        self.assertEqual(crop["inputs"]["output_target_width"], 1024)
        self.assertEqual(crop["inputs"]["output_target_height"], 1024)

    def test_no_loadimage_is_added_for_a_staged_source(self):
        load_images = [node for node in self.graph.values()
                       if node["class_type"] == "LoadImage"]
        self.assertEqual(len(load_images), 1)
        self.assertEqual(load_images[0]["inputs"]["image"], "mask.png")

    def test_tail_consumers_of_the_old_decode_are_rewired_to_the_stitch(self):
        stitch_id = next(
            key for key, node in self.graph.items()
            if node["class_type"] == "InpaintStitchImproved")
        self.assertEqual(self.graph["18"]["inputs"]["image"], [stitch_id, 0])
        self.assertEqual(self.graph["21"]["inputs"]["image"], [stitch_id, 0])
        self.assertEqual(self.graph["9"]["inputs"]["images"], [stitch_id, 0])

    def test_saveimage_prefixes_are_left_untouched(self):
        self.assertEqual(self.graph["9"]["inputs"]["filename_prefix"], "fin-g76ufg")
        self.assertEqual(
            self.graph["20"]["inputs"]["filename_prefix"], "fin-g76ufg-matte")
        self.assertEqual(
            self.graph["24"]["inputs"]["filename_prefix"], "fin-g76ufg-delivered")

    def test_sampler_settings_come_from_the_redraw_pass(self):
        sample = next(
            node for node in self.graph.values()
            if node["class_type"] == "KSampler" and node["inputs"]["denoise"] == 0.6)
        self.assertEqual(sample["inputs"]["seed"], 8)
        self.assertEqual(sample["inputs"]["sampler_name"], "euler")
        self.assertEqual(sample["inputs"]["scheduler"], "normal")
        self.assertEqual(sample["inputs"]["cfg"], 5)
        self.assertEqual(sample["inputs"]["steps"], 30)

    def test_explicit_seed_overrides_the_redraw_passs_own(self):
        graph = splice_repair(
            FINALIZE, mask_name="mask.png", positive="p", negative="n",
            denoise=0.6, size=1024, seed=99)
        sample = next(
            node for node in graph.values()
            if node["class_type"] == "KSampler" and node["inputs"]["denoise"] == 0.6)
        self.assertEqual(sample["inputs"]["seed"], 99)

    def test_does_not_mutate_the_source_graph(self):
        before = json.dumps(FINALIZE, sort_keys=True)
        splice_repair(FINALIZE, mask_name="m.png", positive="p", negative="n",
                      denoise=0.5, size=512)
        self.assertEqual(json.dumps(FINALIZE, sort_keys=True), before)


class SpliceRepairRawTest(unittest.TestCase):
    def test_the_only_saveimage_is_rewired_to_the_stitch(self):
        graph = splice_repair(
            RAW, mask_name="mask.png", positive="p", negative="n",
            denoise=0.6, size=1024)
        stitch_id = next(
            key for key, node in graph.items()
            if node["class_type"] == "InpaintStitchImproved")
        self.assertEqual(graph["9"]["inputs"]["images"], [stitch_id, 0])
        crop = next(node for node in graph.values()
                   if node["class_type"] == "InpaintCropImproved")
        self.assertEqual(crop["inputs"]["image"], ["8", 0])


if __name__ == "__main__":
    unittest.main()
