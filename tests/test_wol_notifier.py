"""The sleep announcement the worker sends to the Wake-on-LAN service."""

from __future__ import annotations

import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from comfyui_recipes.infrastructure.notifications.wol import WolNotifier
from comfyui_recipes.interfaces.agent import build_rest_services


class _Handler(BaseHTTPRequestHandler):
    status = 204
    received: list = []

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        type(self).received.append(
            (self.path, dict(self.headers), json.loads(self.rfile.read(length))))
        self.send_response(type(self).status)
        self.end_headers()

    def log_message(self, *args):
        pass


class WolNotifierTest(unittest.TestCase):
    def setUp(self):
        _Handler.received = []
        _Handler.status = 204
        self.server = HTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/sleeping"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_posts_the_reason_with_the_bearer_token_from_the_file(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WOL_NOTIFY_URL", None)
            os.environ.pop("WOL_NOTIFY_TOKEN", None)
            (Path(directory) / ".local").mkdir()
            (Path(directory) / ".local/wol-notify").write_text(
                f"{self.url}\nsecret\n", encoding="utf-8")
            WolNotifier(Path(directory)).announce("idle 10m")
        path, headers, body = _Handler.received[0]
        self.assertEqual(path, "/sleeping")
        self.assertEqual(headers["Authorization"], "Bearer secret")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(body, {"reason": "idle 10m"})

    def test_environment_wins_over_the_file(self):
        with TemporaryDirectory() as directory, patch.dict(
                os.environ, {"WOL_NOTIFY_URL": self.url, "WOL_NOTIFY_TOKEN": "env"}):
            (Path(directory) / ".local").mkdir()
            (Path(directory) / ".local/wol-notify").write_text(
                "http://127.0.0.1:9/never\nfile\n", encoding="utf-8")
            WolNotifier(Path(directory)).announce("idle 10m")
        self.assertEqual(_Handler.received[0][1]["Authorization"], "Bearer env")

    def test_a_status_other_than_204_raises(self):
        _Handler.status = 200
        with TemporaryDirectory() as directory, patch.dict(
                os.environ, {"WOL_NOTIFY_URL": self.url, "WOL_NOTIFY_TOKEN": "t"}):
            with self.assertRaises(SystemExit):
                WolNotifier(Path(directory)).announce("idle 10m")

    def test_no_target_raises(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WOL_NOTIFY_URL", None)
            os.environ.pop("WOL_NOTIFY_TOKEN", None)
            with self.assertRaises(SystemExit):
                WolNotifier(Path(directory)).announce("idle 10m")


class BuildRestServicesTest(unittest.TestCase):
    def test_off_the_windows_host(self):
        with patch("comfyui_recipes.interfaces.agent.sys.platform", "darwin"):
            self.assertIsNone(build_rest_services(Path("."), object()))

    def test_zero_minutes_turns_it_off(self):
        with patch("comfyui_recipes.interfaces.agent.sys.platform", "win32"), \
                patch.dict(os.environ, {"COMFYUI_RECIPES_SLEEP_AFTER": "0"}):
            self.assertIsNone(build_rest_services(Path("."), object()))

    def test_a_malformed_threshold_is_refused(self):
        with patch("comfyui_recipes.interfaces.agent.sys.platform", "win32"), \
                patch.dict(os.environ, {"COMFYUI_RECIPES_SLEEP_AFTER": "ten"}):
            with self.assertRaises(SystemExit):
                build_rest_services(Path("."), object())


if __name__ == "__main__":
    unittest.main()
