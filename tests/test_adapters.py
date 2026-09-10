from __future__ import annotations

import io
import json
import os
import stat
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from comfyui_recipes.domain.yukari_sketch.recipe import render_spec as sketch_render_spec
from comfyui_recipes.infrastructure.chimera.client import ChimeraClient
from comfyui_recipes.infrastructure.comfyui.client import ComfyUIClient
from comfyui_recipes.infrastructure.comfyui.refinement_graph import (
    DELIVERED_SUFFIX, MATTE_SUFFIX, chain_pass,
)
from comfyui_recipes.infrastructure.comfyui.yukari_graph import build_graph
from comfyui_recipes.infrastructure.notifications.discord import DiscordNotifier
from comfyui_recipes.infrastructure.persistence.run_state import JsonRunState


class AdapterTest(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "POSIX permission bits")
    def test_chimera_cache_permissions_are_restricted(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            cache_directory = repository / ".local"
            cache_directory.mkdir(mode=0o755)
            client = ChimeraClient(repository)
            fields = [SimpleNamespace(stdout="client\n"),
                      SimpleNamespace(stdout="secret\n")]
            with patch("subprocess.run", side_effect=fields):
                client.credentials()
            self.assertEqual(stat.S_IMODE(cache_directory.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(client.token_cache.stat().st_mode), 0o600)

    def test_chimera_retry_does_not_sleep_after_final_attempt(self):
        client = ChimeraClient(Path("."), base_url="https://example.invalid")
        client._credentials = {}
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("offline")) as urlopen, \
                patch("time.sleep") as sleep, self.assertRaises(SystemExit):
            client.request("GET", "/test")
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(sleep.call_args_list, [call(2), call(4)])

    def test_chimera_request_returns_none_on_204(self):
        client = ChimeraClient(Path("."), base_url="https://example.invalid")
        client._credentials = {}
        response = MagicMock()
        response.read.return_value = b""
        response.status = 204
        response.headers = {}
        response.__enter__.return_value = response
        with patch("urllib.request.urlopen", return_value=response):
            self.assertIsNone(client.request("POST", "/api/v1/requests/claim"))

    def test_chimera_request_returns_none_on_empty_body(self):
        client = ChimeraClient(Path("."), base_url="https://example.invalid")
        client._credentials = {}
        response = MagicMock()
        response.read.return_value = b""
        response.status = 200
        response.headers = {}
        response.__enter__.return_value = response
        with patch("urllib.request.urlopen", return_value=response):
            self.assertIsNone(client.request("GET", "/api/v1/requests/claim"))

    def test_chimera_put_catalog_puts_to_the_recipe_refs_catalog_path(self):
        client = ChimeraClient(Path("."), base_url="https://example.invalid")
        client._credentials = {}
        response = MagicMock()
        response.read.return_value = json.dumps({"ok": True}).encode()
        response.status = 200
        response.headers = {"Content-Type": "application/json"}
        response.__enter__.return_value = response
        with patch("urllib.request.urlopen", return_value=response) as urlopen:
            result = client.put_catalog(
                "dev/catalog-publish", {"schema_version": 1})
        self.assertEqual(result, {"ok": True})
        request = urlopen.call_args[0][0]
        self.assertEqual(
            request.full_url,
            "https://example.invalid/api/v1/catalogs/dev/catalog-publish")
        self.assertEqual(request.get_method(), "PUT")
        self.assertEqual(json.loads(request.data), {"schema_version": 1})

    def test_chimera_put_catalog_escapes_the_recipe_ref(self):
        client = ChimeraClient(Path("."), base_url="https://example.invalid")
        client._credentials = {}
        response = MagicMock()
        response.read.return_value = b"{}"
        response.status = 200
        response.headers = {"Content-Type": "application/json"}
        response.__enter__.return_value = response
        with patch("urllib.request.urlopen", return_value=response) as urlopen:
            client.put_catalog("dev/catalog#v1", {"schema_version": 1})
        self.assertEqual(
            urlopen.call_args[0][0].full_url,
            "https://example.invalid/api/v1/catalogs/dev/catalog%23v1")

    def test_chimera_record_publication_posts_only_the_given_fields(self):
        client = ChimeraClient(Path("."), base_url="https://example.invalid")
        client._credentials = {}
        response = MagicMock()
        response.read.return_value = json.dumps({"id": "pub-1"}).encode()
        response.status = 201
        response.headers = {"Content-Type": "application/json"}
        response.__enter__.return_value = response
        with patch("urllib.request.urlopen", return_value=response) as urlopen:
            result = client.record_publication("gen-1", url="https://x.com/post/1")
        self.assertEqual(result, {"id": "pub-1"})
        request = urlopen.call_args[0][0]
        self.assertEqual(
            request.full_url,
            "https://example.invalid/api/v1/generations/gen-1/publications")
        self.assertEqual(request.get_method(), "POST")
        body = json.loads(request.data)
        self.assertEqual(body.pop("url"), "https://x.com/post/1")
        self.assertEqual(set(body), {"idempotency_key"})

    def test_chimera_record_publication_omits_unset_fields(self):
        client = ChimeraClient(Path("."), base_url="https://example.invalid")
        client._credentials = {}
        response = MagicMock()
        response.read.return_value = json.dumps({"id": "pub-2"}).encode()
        response.status = 201
        response.headers = {"Content-Type": "application/json"}
        response.__enter__.return_value = response
        with patch("urllib.request.urlopen", return_value=response) as urlopen:
            client.record_publication("gen-1", idempotency_key="pub-key")
        request = urlopen.call_args[0][0]
        self.assertEqual(json.loads(request.data), {"idempotency_key": "pub-key"})

    def test_chimera_record_publication_resends_one_generated_key(self):
        client = ChimeraClient(Path("."), base_url="https://example.invalid")
        client._credentials = {}
        response = MagicMock()
        response.read.return_value = json.dumps({"id": "pub-3"}).encode()
        response.status = 200
        response.headers = {"Content-Type": "application/json"}
        response.__enter__.return_value = response
        lost = urllib.error.URLError("connection reset")
        with patch("urllib.request.urlopen", side_effect=[lost, response]) as urlopen, \
                patch("time.sleep"):
            client.record_publication("gen-1")
        keys = [json.loads(sent[0][0].data)["idempotency_key"]
                for sent in urlopen.call_args_list]
        self.assertEqual(len(keys), 2)
        self.assertEqual(keys[0], keys[1])

    def test_comfyui_wait_retries_transport_error_and_returns_empty_success(self):
        client = ComfyUIClient(
            "http://example.invalid", poll_interval=0, poll_timeout=1)
        client.request = MagicMock(side_effect=[
            urllib.error.URLError("temporary"),
            {"prompt": {"status": {"status_str": "success"}, "outputs": {}}},
        ])
        self.assertEqual(client.wait_for("prompt"), [])

    def test_comfyui_knows_true_via_history(self):
        client = ComfyUIClient("http://example.invalid")
        client.request = MagicMock(return_value={"prompt": {"status": {}}})
        self.assertTrue(client.knows("prompt"))

    def test_comfyui_knows_true_via_queue_pending(self):
        client = ComfyUIClient("http://example.invalid")
        client.request = MagicMock(side_effect=[
            {},
            {"queue_running": [], "queue_pending": [[0, "prompt", {}, {}, []]]},
        ])
        self.assertTrue(client.knows("prompt"))

    def test_comfyui_knows_false_when_both_empty(self):
        client = ComfyUIClient("http://example.invalid")
        client.request = MagicMock(side_effect=[
            {},
            {"queue_running": [], "queue_pending": []},
        ])
        self.assertFalse(client.knows("prompt"))

    def test_comfyui_knows_true_on_url_error(self):
        client = ComfyUIClient("http://example.invalid")
        client.request = MagicMock(side_effect=urllib.error.URLError("offline"))
        self.assertTrue(client.knows("prompt"))

    def test_comfyui_upload_image_posts_multipart_and_returns_the_stored_name(self):
        client = ComfyUIClient("http://example.invalid")
        response = MagicMock()
        response.read.return_value = json.dumps(
            {"name": "fin-source.png", "type": "input"}).encode()
        response.__enter__.return_value = response
        with patch("urllib.request.urlopen", return_value=response) as urlopen:
            name = client.upload_image("fin-source.png", b"png-bytes")
        self.assertEqual(name, "fin-source.png")
        request = urlopen.call_args[0][0]
        self.assertEqual(request.full_url, "http://example.invalid/upload/image")
        self.assertIn(b"png-bytes", request.data)
        self.assertIn(b'name="image"', request.data)
        self.assertIn(b'name="overwrite"', request.data)
        self.assertIn(b"true", request.data)
        self.assertTrue(
            request.headers["Content-type"].startswith("multipart/form-data"))

    def test_chain_pass_rejects_a_base_with_no_vaedecode_and_non_numeric_ids(self):
        base = {
            "3": {"class_type": "KSampler",
                  "inputs": {"positive": ["6", 0], "negative": ["7", 0]}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "p"}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "n"}},
        }
        with self.assertRaises(ValueError):
            chain_pass(base, 2048, 0.2, "test", canvas=(832, 1664))
        with self.assertRaisesRegex(ValueError, "non-numeric node IDs"):
            chain_pass({**base, "output": {}}, 2048, 0.2, "test", canvas=(832, 1664))

    def test_chain_pass_upscales_the_decoded_image_in_pixel_space(self):
        base = {
            "3": {"class_type": "KSampler",
                  "inputs": {"seed": 7, "positive": ["6", 0], "negative": ["7", 0]}},
            "4": {"class_type": "DiffusersLoader", "inputs": {}},
            "5": {"class_type": "EmptyLatentImage",
                  "inputs": {"width": 832, "height": 1664}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "p"}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "n"}},
            "8": {"class_type": "VAEDecode",
                  "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage",
                  "inputs": {"images": ["8", 0], "filename_prefix": "base"}},
        }
        graph = chain_pass(base, 2048, 0.45, "fin", canvas=(832, 1664))
        scale = graph["10"]
        self.assertEqual(scale["class_type"], "ImageScale")
        self.assertEqual(scale["inputs"]["upscale_method"], "bicubic")
        self.assertEqual(scale["inputs"]["image"], ["8", 0])
        self.assertEqual(
            (scale["inputs"]["width"], scale["inputs"]["height"]), (1024, 2048))
        encode = graph["11"]
        self.assertEqual(encode["class_type"], "VAEEncode")
        self.assertEqual(encode["inputs"]["pixels"], ["10", 0])
        self.assertEqual(graph["12"]["inputs"]["latent_image"], ["11", 0])
        self.assertEqual(graph["9"]["inputs"]["images"], ["13", 0])

    def test_chain_pass_pixel_route_honours_the_upscale_method(self):
        base = {
            "3": {"class_type": "KSampler",
                  "inputs": {"seed": 7, "positive": ["6", 0], "negative": ["7", 0]}},
            "4": {"class_type": "DiffusersLoader", "inputs": {}},
            "5": {"class_type": "EmptyLatentImage",
                  "inputs": {"width": 832, "height": 1664}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "p"}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "n"}},
            "8": {"class_type": "VAEDecode",
                  "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage",
                  "inputs": {"images": ["8", 0], "filename_prefix": "base"}},
        }
        graph = chain_pass(base, 2048, 0.45, "fin", canvas=(832, 1664), upscale="nearest-exact")
        scale = graph["10"]
        self.assertEqual(scale["class_type"], "ImageScale")
        self.assertEqual(scale["inputs"]["upscale_method"], "nearest-exact")

    def test_chain_pass_rejects_an_unknown_upscale_method(self):
        base = {
            "3": {"class_type": "KSampler",
                  "inputs": {"seed": 7, "positive": ["6", 0], "negative": ["7", 0]}},
            "4": {"class_type": "DiffusersLoader", "inputs": {}},
            "5": {"class_type": "EmptyLatentImage",
                  "inputs": {"width": 832, "height": 1664}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "p"}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "n"}},
            "8": {"class_type": "VAEDecode",
                  "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage",
                  "inputs": {"images": ["8", 0], "filename_prefix": "base"}},
        }
        with self.assertRaisesRegex(ValueError, "unsupported upscale method"):
            chain_pass(base, 2048, 0.45, "fin", canvas=(832, 1664), upscale="mitchell")

    def test_chain_pass_sampler_override_keeps_steps_cfg_and_seed(self):
        base = {
            "3": {"class_type": "KSampler",
                  "inputs": {"seed": 7, "steps": 30, "cfg": 5.0,
                             "sampler_name": "dpmpp_2m", "scheduler": "karras",
                             "positive": ["6", 0], "negative": ["7", 0]}},
            "4": {"class_type": "DiffusersLoader", "inputs": {}},
            "5": {"class_type": "EmptyLatentImage",
                  "inputs": {"width": 832, "height": 1664}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "p"}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "n"}},
            "8": {"class_type": "VAEDecode",
                  "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage",
                  "inputs": {"images": ["8", 0], "filename_prefix": "base"}},
        }
        graph = chain_pass(base, 2048, 0.45, "fin", canvas=(832, 1664), sampler=("euler", "normal"))
        sample = graph["12"]
        self.assertEqual(sample["inputs"]["sampler_name"], "euler")
        self.assertEqual(sample["inputs"]["scheduler"], "normal")
        self.assertEqual(sample["inputs"]["steps"], 30)
        self.assertEqual(sample["inputs"]["cfg"], 5.0)
        self.assertEqual(sample["inputs"]["seed"], 7)

    def test_chain_pass_loader_adds_a_diffusers_loader_and_reroutes(self):
        base = {
            "3": {"class_type": "KSampler",
                  "inputs": {"model": ["1", 0], "seed": 7, "steps": 25,
                             "cfg": 3.5, "positive": ["6", 0], "negative": ["7", 0]}},
            "4": {"class_type": "VAELoader", "inputs": {}},
            "5": {"class_type": "EmptyLatentImage",
                  "inputs": {"width": 832, "height": 1664}},
            "6": {"class_type": "CLIPTextEncode",
                  "inputs": {"clip": ["2", 0], "text": "p"}},
            "7": {"class_type": "CLIPTextEncode",
                  "inputs": {"clip": ["2", 0], "text": "n"}},
            "8": {"class_type": "VAEDecode",
                  "inputs": {"samples": ["3", 0], "vae": ["4", 0]}},
            "9": {"class_type": "SaveImage",
                  "inputs": {"images": ["8", 0], "filename_prefix": "base"}},
        }
        original = json.loads(json.dumps(base))
        graph = chain_pass(base, 2048, 0.75, "fin", loader="hassaku-il-v22",
                           canvas=(832, 1664))
        loader_id = "20"
        self.assertEqual(graph[loader_id],
                         {"class_type": "DiffusersLoader",
                          "inputs": {"model_path": "hassaku-il-v22"}})
        self.assertEqual(graph["12"]["inputs"]["model"], [loader_id, 0])
        self.assertEqual(graph["14"]["inputs"]["clip"], [loader_id, 1])
        self.assertEqual(graph["15"]["inputs"]["clip"], [loader_id, 1])
        self.assertEqual(graph["11"]["inputs"]["vae"], [loader_id, 2])
        self.assertEqual(graph["13"]["inputs"]["vae"], [loader_id, 2])
        for key in ("3", "4", "5", "6", "7"):
            self.assertEqual(graph[key], original[key])

    def test_chain_pass_sampling_override_sets_steps_and_cfg(self):
        base = {
            "3": {"class_type": "KSampler",
                  "inputs": {"seed": 7, "steps": 25, "cfg": 3.5,
                             "sampler_name": "er_sde", "scheduler": "normal",
                             "positive": ["6", 0], "negative": ["7", 0]}},
            "4": {"class_type": "DiffusersLoader", "inputs": {}},
            "5": {"class_type": "EmptyLatentImage",
                  "inputs": {"width": 832, "height": 1664}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "p"}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "n"}},
            "8": {"class_type": "VAEDecode",
                  "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage",
                  "inputs": {"images": ["8", 0], "filename_prefix": "base"}},
        }
        original_node_3 = json.loads(json.dumps(base["3"]))
        graph = chain_pass(base, 2048, 0.75, "fin",
                           sampler=("dpmpp_2m", "karras"),
                           sampling=(30, 5.0), canvas=(832, 1664))
        sample = graph["12"]
        self.assertEqual(sample["inputs"]["steps"], 30)
        self.assertEqual(sample["inputs"]["cfg"], 5.0)
        self.assertEqual(graph["3"], original_node_3)

    def test_chain_pass_rejects_a_saved_image_that_is_not_decoded(self):
        base = {
            "3": {"class_type": "KSampler",
                  "inputs": {"seed": 7, "positive": ["6", 0], "negative": ["7", 0]}},
            "4": {"class_type": "DiffusersLoader", "inputs": {}},
            "5": {"class_type": "EmptyLatentImage",
                  "inputs": {"width": 832, "height": 1664}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "p"}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "n"}},
            "8": {"class_type": "ImageScale", "inputs": {}},
            "9": {"class_type": "SaveImage",
                  "inputs": {"images": ["8", 0], "filename_prefix": "base"}},
        }
        with self.assertRaisesRegex(ValueError, "must be fed by a VAEDecode"):
            chain_pass(base, 2048, 0.45, "fin", canvas=(832, 1664))

    def _deliver_base(self):
        return {
            "3": {"class_type": "KSampler",
                  "inputs": {"seed": 7, "positive": ["6", 0], "negative": ["7", 0]}},
            "4": {"class_type": "DiffusersLoader", "inputs": {}},
            "5": {"class_type": "EmptyLatentImage",
                  "inputs": {"width": 832, "height": 1664}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "p"}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "n"}},
            "8": {"class_type": "VAEDecode",
                  "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage",
                  "inputs": {"images": ["8", 0], "filename_prefix": "base"}},
        }

    def test_chain_pass_deliver_requires_matte_model(self):
        with self.assertRaisesRegex(ValueError, "deliver requires matte_model"):
            chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664), deliver=True)

    def test_chain_pass_skin_requires_source_image(self):
        with self.assertRaisesRegex(ValueError, "skin requires source_image"):
            chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664),
                      matte_model="birefnet", deliver=True, skin=True)

    def test_chain_pass_deliver_wires_deliver_onto_the_matte_branch(self):
        graph = chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664),
                           matte_model="birefnet", deliver=True)
        remove = graph["17"]
        self.assertEqual(remove["class_type"], "RemoveBackground")
        deliver_node = graph["20"]
        self.assertEqual(deliver_node["class_type"], "YukariDeliver")
        self.assertEqual(deliver_node["inputs"]["image"], ["13", 0])
        self.assertEqual(deliver_node["inputs"]["matte"], ["17", 0])
        self.assertIs(deliver_node["inputs"]["keep_scene"], False)
        self.assertIs(deliver_node["inputs"]["transparent"], False)
        save = graph["21"]
        self.assertEqual(save["class_type"], "SaveImage")
        self.assertEqual(save["inputs"]["images"], ["20", 0])
        self.assertEqual(save["inputs"]["filename_prefix"], "fin" + DELIVERED_SUFFIX)
        # The raw pass and the matte are untouched by the delivery addition.
        self.assertEqual(graph["9"]["inputs"]["filename_prefix"], "fin")
        self.assertEqual(graph["19"]["inputs"]["filename_prefix"],
                         "fin" + MATTE_SUFFIX)

    def test_chain_pass_deliver_keep_scene_is_passed_through(self):
        graph = chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664),
                           matte_model="birefnet", deliver=True, keep_scene=True)
        self.assertIs(graph["20"]["inputs"]["keep_scene"], True)

    def test_chain_pass_deliver_transparent_is_passed_through(self):
        graph = chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664),
                           matte_model="birefnet", deliver=True, transparent=True)
        self.assertIs(graph["20"]["inputs"]["transparent"], True)

    def test_chain_pass_stroke_light_is_passed_onto_the_deliver_node(self):
        graph = chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664),
                           matte_model="birefnet", deliver=True, stroke_light="sw")
        self.assertEqual(graph["20"]["inputs"]["stroke_light"], "sw")

    def test_chain_pass_stroke_light_defaults_to_an_empty_string(self):
        graph = chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664),
                           matte_model="birefnet", deliver=True)
        self.assertEqual(graph["20"]["inputs"]["stroke_light"], "")

    def test_chain_pass_bad_stroke_light_raises(self):
        with self.assertRaisesRegex(ValueError, "stroke_light"):
            chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664),
                      matte_model="birefnet", deliver=True, stroke_light="north")

    def test_chain_pass_backdrop_is_passed_onto_the_deliver_node(self):
        graph = chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664),
                           matte_model="birefnet", deliver=True, backdrop="stripes")
        self.assertEqual(graph["20"]["inputs"]["backdrop"], "stripes")

    def test_chain_pass_backdrop_defaults_to_an_empty_string(self):
        graph = chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664),
                           matte_model="birefnet", deliver=True)
        self.assertEqual(graph["20"]["inputs"]["backdrop"], "")

    def test_chain_pass_bad_backdrop_raises(self):
        with self.assertRaisesRegex(ValueError, "backdrop"):
            chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664),
                      matte_model="birefnet", deliver=True, backdrop="plaid")

    def test_chain_pass_deliver_with_skin_chains_repin_skin_before_delivery(self):
        graph = chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664),
                           matte_model="birefnet", deliver=True,
                           skin=True, source_image="fin-source.png")
        load_source = graph["20"]
        self.assertEqual(load_source, {"class_type": "LoadImage",
                                       "inputs": {"image": "fin-source.png"}})
        repin_skin = graph["21"]
        self.assertEqual(repin_skin["class_type"], "YukariRepinSkin")
        self.assertEqual(repin_skin["inputs"]["image"], ["13", 0])
        self.assertEqual(repin_skin["inputs"]["source"], ["20", 0])
        deliver_node = graph["22"]
        self.assertEqual(deliver_node["class_type"], "YukariDeliver")
        self.assertEqual(deliver_node["inputs"]["image"], ["21", 0])
        save = graph["23"]
        self.assertEqual(save["inputs"]["images"], ["22", 0])

    def test_chain_pass_deliver_with_repin_chains_repin_before_delivery(self):
        graph = chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664),
                           matte_model="birefnet", deliver=True,
                           repin=True, keep_legwear=0.4)
        repin_node = graph["20"]
        self.assertEqual(repin_node["class_type"], "YukariRepin")
        self.assertEqual(repin_node["inputs"]["image"], ["13", 0])
        self.assertIs(repin_node["inputs"]["keep_legwear"], True)
        self.assertEqual(repin_node["inputs"]["keep_legwear_cut"], 0.4)
        deliver_node = graph["21"]
        self.assertEqual(deliver_node["inputs"]["image"], ["20", 0])

    def test_chain_pass_deliver_repin_without_keep_legwear_defaults_the_cut(self):
        graph = chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664),
                           matte_model="birefnet", deliver=True, repin=True)
        repin_node = graph["20"]
        self.assertIs(repin_node["inputs"]["keep_legwear"], False)
        self.assertEqual(repin_node["inputs"]["keep_legwear_cut"], 0.62)

    def test_chain_pass_deliver_recolor_wins_over_repin(self):
        graph = chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664),
                           matte_model="birefnet", deliver=True,
                           repin=True, recolor=True)
        recolor_node = graph["20"]
        self.assertEqual(recolor_node["class_type"], "YukariRecolor")
        self.assertFalse(any(node.get("class_type") == "YukariRepin"
                             for node in graph.values()))
        deliver_node = graph["21"]
        self.assertEqual(deliver_node["class_type"], "YukariDeliver")
        self.assertEqual(deliver_node["inputs"]["image"], ["20", 0])

    def _layerdiffuse_sketch_base(self):
        spec = sketch_render_spec("cinema", 7, "ab11", layerdiffuse=True)
        return build_graph(spec)

    def _single(self, graph, class_type):
        matches = [node for node in graph.values()
                  if node.get("class_type") == class_type]
        self.assertEqual(len(matches), 1, class_type)
        return matches[0]

    def _id_of(self, graph, node):
        return next(key for key, candidate in graph.items() if candidate is node)

    def _redraw_decode_id(self, graph):
        """The redraw's own VAEDecode, not the layerdiffuse base pass's."""
        matches = [key for key in graph if key.isdecimal() and int(key) > 15
                  and graph[key].get("class_type") == "VAEDecode"]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_chain_pass_compose_wires_compose_into_the_pixel_route(self):
        base = self._layerdiffuse_sketch_base()
        graph = chain_pass(base, 2048, 0.55, "fin", prompt=("p", "n"),
                           canvas=(832, 1664), latent_route=False, compose=True)
        compose_node = self._single(graph, "YukariCompose")
        self.assertEqual(compose_node["inputs"]["image"], ["15", 0])
        self.assertEqual(compose_node["inputs"]["backdrop"], "")
        self.assertEqual(compose_node["inputs"]["stroke_light"], "")
        compose_id = self._id_of(graph, compose_node)

        scale = self._single(graph, "ImageScale")
        self.assertEqual(scale["inputs"]["image"], [compose_id, 0])
        scale_id = self._id_of(graph, scale)

        encode = self._single(graph, "VAEEncode")
        self.assertEqual(encode["inputs"]["pixels"], [scale_id, 0])
        encode_id = self._id_of(graph, encode)

        redraw_ids = [key for key in graph if key.isdecimal() and int(key) > 15
                     and graph[key].get("class_type") == "KSampler"]
        self.assertEqual(len(redraw_ids), 1)
        sampler = graph[redraw_ids[0]]
        self.assertEqual(sampler["inputs"]["latent_image"], [encode_id, 0])
        # Sees through node 12 (LayeredDiffusionApply) to the LoRA it samples.
        self.assertEqual(sampler["inputs"]["model"], ["10", 0])

    def test_chain_pass_compose_stroke_light_is_passed_onto_the_compose_node(self):
        base = self._layerdiffuse_sketch_base()
        graph = chain_pass(base, 2048, 0.55, "fin", prompt=("p", "n"),
                           canvas=(832, 1664), latent_route=False, compose=True, stroke_light="ne")
        compose_node = self._single(graph, "YukariCompose")
        self.assertEqual(compose_node["inputs"]["stroke_light"], "ne")

    def test_chain_pass_compose_latent_route_wires_compose_into_latent_space(self):
        base = self._layerdiffuse_sketch_base()
        graph = chain_pass(base, 2048, 0.55, "fin", prompt=("p", "n"),
                           canvas=(832, 1664), latent_route=True, compose=True)
        compose_node = self._single(graph, "YukariCompose")
        self.assertEqual(compose_node["inputs"]["image"], ["15", 0])
        compose_id = self._id_of(graph, compose_node)

        self.assertFalse(any(node.get("class_type") == "ImageScale"
                             for node in graph.values()))

        encode = self._single(graph, "VAEEncode")
        self.assertEqual(encode["inputs"]["pixels"], [compose_id, 0])
        encode_id = self._id_of(graph, encode)

        upscale = self._single(graph, "LatentUpscale")
        self.assertEqual(upscale["inputs"]["samples"], [encode_id, 0])
        self.assertEqual(upscale["inputs"]["upscale_method"], "bicubic")
        self.assertEqual(upscale["inputs"]["crop"], "disabled")
        upscale_id = self._id_of(graph, upscale)

        redraw_ids = [key for key in graph if key.isdecimal() and int(key) > 15
                     and graph[key].get("class_type") == "KSampler"]
        self.assertEqual(len(redraw_ids), 1)
        sampler = graph[redraw_ids[0]]
        self.assertEqual(sampler["inputs"]["latent_image"], [upscale_id, 0])
        self.assertEqual(sampler["inputs"]["model"], ["10", 0])

    def test_chain_pass_redraw_lora_adds_a_loraloader_feeding_the_redraw(self):
        base = self._layerdiffuse_sketch_base()
        graph = chain_pass(
            base, 2048, 0.55, "fin", prompt=("p", "n"), latent_route=True,
            compose=True, redraw_lora=("some-lora.safetensors", 0.8, 0.7),
            canvas=(832, 1664))
        new_lora_ids = [key for key, node in graph.items()
                        if node.get("class_type") == "LoraLoader" and key != "10"]
        self.assertEqual(len(new_lora_ids), 1)
        lora_node = graph[new_lora_ids[0]]
        self.assertEqual(lora_node["inputs"]["model"], ["4", 0])
        self.assertEqual(lora_node["inputs"]["clip"], ["4", 1])
        self.assertEqual(lora_node["inputs"]["lora_name"], "some-lora.safetensors")
        self.assertEqual(lora_node["inputs"]["strength_model"], 0.8)
        self.assertEqual(lora_node["inputs"]["strength_clip"], 0.7)

        redraw_ids = [key for key in graph if key.isdecimal() and int(key) > 15
                     and graph[key].get("class_type") == "KSampler"]
        sampler = graph[redraw_ids[0]]
        self.assertEqual(sampler["inputs"]["model"], [new_lora_ids[0], 0])

        prompt_nodes = [node for node in graph.values()
                        if node.get("class_type") == "CLIPTextEncode"
                        and node["inputs"]["clip"] == [new_lora_ids[0], 1]]
        self.assertEqual(len(prompt_nodes), 2)

    def test_chain_pass_deliver_size_scales_the_delivered_save_image(self):
        base = self._deliver_base()
        base["5"]["inputs"]["width"] = 1024
        base["5"]["inputs"]["height"] = 1280
        graph = chain_pass(base, 2560, 0.45, "fin", canvas=(1024, 1280),
                           matte_model="birefnet", deliver=True,
                           deliver_size=1536)
        deliver_node = self._single(graph, "YukariDeliver")
        deliver_id = self._id_of(graph, deliver_node)
        scale = next(node for node in graph.values()
                    if node.get("class_type") == "ImageScale"
                    and node["inputs"]["image"] == [deliver_id, 0])
        self.assertEqual(scale["inputs"]["upscale_method"], "lanczos")
        self.assertEqual(
            (scale["inputs"]["width"], scale["inputs"]["height"]), (1229, 1536))
        self.assertEqual(scale["inputs"]["crop"], "disabled")
        scale_id = self._id_of(graph, scale)
        matches = [node for node in graph.values()
                  if node.get("class_type") == "SaveImage"
                  and node["inputs"]["filename_prefix"] == "fin" + DELIVERED_SUFFIX]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["inputs"]["images"], [scale_id, 0])
        # The raw pass and the matte are untouched by the downscale.
        self.assertEqual(graph["9"]["inputs"]["filename_prefix"], "fin")
        matte_save = next(node for node in graph.values()
                          if node.get("class_type") == "SaveImage"
                          and node["inputs"]["filename_prefix"] == "fin" + MATTE_SUFFIX)
        self.assertNotEqual(matte_save["inputs"]["images"], [scale_id, 0])

    def test_chain_pass_deliver_size_at_or_above_the_redraw_adds_no_scale(self):
        base = self._deliver_base()
        base["5"]["inputs"]["width"] = 1024
        base["5"]["inputs"]["height"] = 1280
        graph = chain_pass(base, 2560, 0.45, "fin", canvas=(1024, 1280),
                           matte_model="birefnet", deliver=True,
                           latent_route=True, deliver_size=2560)
        self.assertFalse(any(node.get("class_type") == "ImageScale"
                             for node in graph.values()))

    def test_chain_pass_deliver_size_none_adds_no_scale(self):
        graph = chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664),
                           matte_model="birefnet", deliver=True,
                           latent_route=True)
        self.assertFalse(any(node.get("class_type") == "ImageScale"
                             for node in graph.values()))

    def test_chain_pass_compose_deliver_size_scales_node_9s_input(self):
        base = self._layerdiffuse_sketch_base()
        base["5"]["inputs"]["width"] = 1024
        base["5"]["inputs"]["height"] = 1280
        graph = chain_pass(base, 2560, 0.55, "fin", prompt=("p", "n"),
                           canvas=(1024, 1280), latent_route=False, compose=True,
                           deliver_size=1536)
        # Two ImageScale nodes exist on this route (the pixel-route upscale
        # feeding the redraw, and the delivery downscale); the delivery one
        # is the one feeding node "9".
        scales = [node for node in graph.values()
                 if node.get("class_type") == "ImageScale"]
        self.assertEqual(len(scales), 2)
        deliver_scale = next(
            node for node in scales if node["inputs"]["upscale_method"] == "lanczos")
        deliver_scale_id = self._id_of(graph, deliver_scale)
        self.assertEqual(graph["9"]["inputs"]["images"], [deliver_scale_id, 0])
        self.assertEqual(
            (deliver_scale["inputs"]["width"], deliver_scale["inputs"]["height"]),
            (1229, 1536))

    def test_chain_pass_compose_with_matte_model_raises(self):
        base = self._layerdiffuse_sketch_base()
        with self.assertRaisesRegex(ValueError, "compose cannot be combined"):
            chain_pass(base, 2048, 0.55, "fin", canvas=(832, 1664),
                      compose=True, matte_model="birefnet")

    def test_chain_pass_compose_deliver_without_transparent_raises(self):
        base = self._layerdiffuse_sketch_base()
        with self.assertRaisesRegex(ValueError, "compose deliver requires transparent"):
            chain_pass(base, 2048, 0.55, "fin", canvas=(832, 1664),
                      compose=True, deliver=True)

    def test_chain_pass_compose_on_a_non_rgba_base_raises(self):
        with self.assertRaisesRegex(ValueError, "JoinImageWithAlpha"):
            chain_pass(self._deliver_base(), 2048, 0.45, "fin", canvas=(832, 1664), compose=True)

    def test_chain_pass_compose_transparent_wires_bands_true_onto_the_compose_node(self):
        base = self._layerdiffuse_sketch_base()
        graph = chain_pass(base, 2048, 0.55, "fin", prompt=("p", "n"),
                           canvas=(832, 1664), latent_route=False, compose=True,
                           transparent=True, deliver=True)
        compose_node = self._single(graph, "YukariCompose")
        self.assertIs(compose_node["inputs"]["bands"], True)

    def test_chain_pass_compose_without_transparent_wires_bands_true(self):
        base = self._layerdiffuse_sketch_base()
        graph = chain_pass(base, 2048, 0.55, "fin", prompt=("p", "n"),
                           canvas=(832, 1664), latent_route=False, compose=True)
        compose_node = self._single(graph, "YukariCompose")
        self.assertIs(compose_node["inputs"]["bands"], True)

    def test_chain_pass_compose_transparent_appends_the_cut_backdrop_tail(self):
        base = self._layerdiffuse_sketch_base()
        graph = chain_pass(base, 2048, 0.55, "fin", prompt=("p", "n"),
                           canvas=(832, 1664), latent_route=False, compose=True,
                           transparent=True, deliver=True, backdrop="#112233")
        decode_id = self._redraw_decode_id(graph)
        self.assertFalse(any(node.get("class_type") in
                             ("RemoveBackground", "LoadBackgroundRemovalModel", "YukariDeliver")
                             for node in graph.values()))
        cut_node = self._single(graph, "YukariCutBackdrop")
        self.assertEqual(cut_node["inputs"]["image"], [decode_id, 0])
        self.assertEqual(cut_node["inputs"]["backdrop"], "#112233")
        cut_id = self._id_of(graph, cut_node)
        to_image = self._single(graph, "MaskToImage")
        self.assertEqual(to_image["inputs"]["mask"], [cut_id, 1])
        to_image_id = self._id_of(graph, to_image)
        matte_save = next(node for node in graph.values()
                          if node.get("class_type") == "SaveImage"
                          and node["inputs"]["filename_prefix"] == "fin" + MATTE_SUFFIX)
        self.assertEqual(matte_save["inputs"]["images"], [to_image_id, 0])
        delivered_save = next(node for node in graph.values()
                              if node.get("class_type") == "SaveImage"
                              and node["inputs"]["filename_prefix"] == "fin" + DELIVERED_SUFFIX)
        self.assertEqual(delivered_save["inputs"]["images"], [cut_id, 0])
        # The raw redraw itself is untouched -- no deliver_target scaling,
        # since that is the cut tail's own job.
        self.assertEqual(graph["9"]["inputs"]["images"], [decode_id, 0])

    def test_chain_pass_compose_transparent_deliver_size_scales_only_the_delivered_save(self):
        base = self._layerdiffuse_sketch_base()
        base["5"]["inputs"]["width"] = 1024
        base["5"]["inputs"]["height"] = 1280
        graph = chain_pass(base, 2560, 0.55, "fin", prompt=("p", "n"),
                           canvas=(1024, 1280), latent_route=False, compose=True,
                           transparent=True, deliver=True,
                           deliver_size=1536)
        decode_id = self._redraw_decode_id(graph)
        cut_node = self._single(graph, "YukariCutBackdrop")
        cut_id = self._id_of(graph, cut_node)
        scale = next(node for node in graph.values()
                    if node.get("class_type") == "ImageScale"
                    and node["inputs"]["image"] == [cut_id, 0])
        self.assertEqual(scale["inputs"]["upscale_method"], "lanczos")
        scale_id = self._id_of(graph, scale)
        delivered_save = next(node for node in graph.values()
                              if node.get("class_type") == "SaveImage"
                              and node["inputs"]["filename_prefix"] == "fin" + DELIVERED_SUFFIX)
        self.assertEqual(delivered_save["inputs"]["images"], [scale_id, 0])
        # node 9 (the raw redraw) is the compose-then-redraw pass's own
        # output, not the delivered picture, so deliver_size never touches it.
        self.assertEqual(graph["9"]["inputs"]["images"], [decode_id, 0])

    def test_chain_pass_canvas_drives_sizes_not_the_bases_empty_latent_image(self):
        base = self._deliver_base()
        # The base's own EmptyLatentImage stays 832x1664; a caller-given
        # canvas of a different shape is what the redraw is sized from.
        graph = chain_pass(base, 2048, 0.45, "fin", canvas=(1000, 1000))
        scale = graph["10"]
        self.assertEqual(
            (scale["inputs"]["width"], scale["inputs"]["height"]), (2048, 2048))

    def test_discord_closes_response_and_swallows_transport_errors(self):
        notifier = DiscordNotifier(Path("."))
        response = MagicMock()
        with patch.object(notifier, "_webhook", return_value="https://example"), \
                patch("urllib.request.urlopen", return_value=response):
            notifier.send("content", "image.png", b"image")
        response.__enter__.assert_called_once_with()
        response.__exit__.assert_called_once()

        output = io.StringIO()
        with patch.object(notifier, "_webhook", return_value="https://example"), \
                patch("urllib.request.urlopen",
                      side_effect=urllib.error.URLError("offline")), \
                redirect_stdout(output):
            notifier.send("content", "image.png", b"image")
        self.assertIn("Discord", output.getvalue())

    def test_run_state_save_is_atomic_and_cleans_up_on_failure(self):
        state = JsonRunState()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "state.json"
            state.save(path, {"value": 1})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"value": 1})
            self.assertEqual(list(root.iterdir()), [path])

            failed = root / "failed.json"
            with patch(
                    "comfyui_recipes.infrastructure.persistence.run_state.os.replace",
                    side_effect=OSError("no replace")), self.assertRaises(OSError):
                state.save(failed, {"value": 2})
            self.assertEqual(sorted(item.name for item in root.iterdir()),
                             ["state.json"])


if __name__ == "__main__":
    unittest.main()
