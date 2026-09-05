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

from comfyui_recipes.infrastructure.chimera.client import ChimeraClient
from comfyui_recipes.infrastructure.comfyui.client import ComfyUIClient
from comfyui_recipes.infrastructure.comfyui.refinement_graph import chain_pass
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

    def test_comfyui_wait_retries_transport_error_and_returns_empty_success(self):
        client = ComfyUIClient(
            "http://example.invalid", poll_interval=0, poll_timeout=1)
        client.request = MagicMock(side_effect=[
            urllib.error.URLError("temporary"),
            {"prompt": {"status": {"status_str": "success"}, "outputs": {}}},
        ])
        self.assertEqual(client.wait_for("prompt"), [])

    def test_chain_pass_rejects_missing_and_non_numeric_node_ids(self):
        base = {
            "3": {}, "4": {}, "5": {}, "6": {}, "7": {}, "9": {},
        }
        with self.assertRaisesRegex(ValueError, "missing required node IDs: 9"):
            chain_pass({key: value for key, value in base.items() if key != "9"},
                       2048, 0.2, "test")
        with self.assertRaisesRegex(ValueError, "non-numeric node IDs"):
            chain_pass({**base, "output": {}}, 2048, 0.2, "test")

    def test_chain_pass_upscales_the_decoded_image_in_pixel_space(self):
        base = {
            "3": {"class_type": "KSampler", "inputs": {"seed": 7}},
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
        graph = chain_pass(base, 2048, 0.45, "fin")
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

    def test_chain_pass_sampler_override_keeps_steps_cfg_and_seed(self):
        base = {
            "3": {"class_type": "KSampler",
                  "inputs": {"seed": 7, "steps": 30, "cfg": 5.0,
                             "sampler_name": "dpmpp_2m", "scheduler": "karras"}},
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
        graph = chain_pass(base, 2048, 0.45, "fin", sampler=("euler", "normal"))
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
                             "cfg": 3.5}},
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
        graph = chain_pass(base, 2048, 0.75, "fin", loader="hassaku-il-v22")
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
                             "sampler_name": "er_sde", "scheduler": "normal"}},
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
                           sampling=(30, 5.0))
        sample = graph["12"]
        self.assertEqual(sample["inputs"]["steps"], 30)
        self.assertEqual(sample["inputs"]["cfg"], 5.0)
        self.assertEqual(graph["3"], original_node_3)

    def test_chain_pass_rejects_a_saved_image_that_is_not_decoded(self):
        base = {
            "3": {"class_type": "KSampler", "inputs": {"seed": 7}},
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
            chain_pass(base, 2048, 0.45, "fin")

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
