"""ComfyUI HTTP adapter."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


def images_of(history_entry: dict) -> list[dict]:
    images = []
    for node_output in history_entry.get("outputs", {}).values():
        for image in node_output.get("images", []):
            if image.get("type") == "output":
                images.append(image)
    return images


class ComfyUIClient:
    def __init__(self, base_url: str | None = None, *, poll_interval: int = 10,
                 poll_timeout: int = 20 * 60) -> None:
        self.base_url = (base_url or
                         f"http://{os.environ.get('COMFYUI_HOST', '127.0.0.1')}:"
                         f"{os.environ.get('COMFYUI_PORT', '8188')}").rstrip("/")
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout

    def request(self, path: str, payload: dict | None = None) -> dict:
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode() if payload else None,
            headers={"Content-Type": "application/json"} if payload else {},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())

    def submit(self, graph: dict) -> str:
        return self.request("/prompt", {"prompt": graph})["prompt_id"]

    def wait_for(self, prompt_id: str) -> list[dict]:
        deadline = time.time() + self.poll_timeout
        while time.time() < deadline:
            try:
                entry = self.request(f"/history/{prompt_id}").get(prompt_id)
            except urllib.error.URLError:
                entry = None
            if entry:
                status = entry.get("status", {}).get("status_str")
                if status == "error":
                    raise RuntimeError(f"comfy job {prompt_id} failed")
                images = images_of(entry)
                if images or status == "success":
                    return images
            time.sleep(self.poll_interval)
        raise RuntimeError(f"comfy job {prompt_id} timed out")

    def fetch(self, image: dict) -> bytes:
        query = urllib.parse.urlencode({
            "filename": image["filename"],
            "subfolder": image.get("subfolder", ""),
            "type": image.get("type", "output"),
        })
        with urllib.request.urlopen(
                self.base_url + "/view?" + query, timeout=120) as response:
            return response.read()
