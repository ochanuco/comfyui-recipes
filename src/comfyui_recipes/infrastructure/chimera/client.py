"""Chimera Management API adapter."""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


USER_AGENT = "comfyui-recipes-generate/1.0 (+local)"
OP_ITEM = "yml6r5qgx3zt57pryokgi3xdqy"


class ChimeraClient:
    def __init__(self, repository: Path, base_url: str | None = None) -> None:
        self.repository = repository
        self.base_url = (base_url or os.environ.get(
            "CHIMERA_BASE_URL", "https://chimera.chanu.co")).rstrip("/")
        self.token_cache = repository / ".local/chimera-token"
        self._credentials: dict[str, str] | None = None

    def credentials(self) -> dict[str, str]:
        if self._credentials is not None:
            return self._credentials
        client_id = os.environ.get("CHIMERA_CF_CLIENT_ID", "").strip()
        secret = os.environ.get("CHIMERA_CF_CLIENT_SECRET", "").strip()
        if not (client_id and secret) and self.token_cache.exists():
            client_id, secret, *_ = (
                self.token_cache.read_text().splitlines() + ["", ""])
            client_id, secret = client_id.strip(), secret.strip()
        if not (client_id and secret):
            def field(label: str) -> str:
                return subprocess.run(
                    ["op", "item", "get", OP_ITEM, "--fields", f"label={label}",
                     "--reveal"], check=True, capture_output=True, text=True,
                ).stdout.strip()
            client_id = field("CF-Access-Client-Id")
            secret = field("CF-Access-Client-Secret")
            self.token_cache.parent.mkdir(parents=True, exist_ok=True)
            self.token_cache.touch(mode=0o600)
            self.token_cache.write_text(f"{client_id}\n{secret}\n")
        self._credentials = {
            "CF-Access-Client-Id": client_id,
            "CF-Access-Client-Secret": secret,
        }
        return self._credentials

    def request(self, method: str, path: str, payload: dict | None = None,
                multipart: tuple[dict, str, str, bytes, str] | None = None) -> dict:
        headers = {**self.credentials(), "User-Agent": USER_AGENT}
        if multipart:
            meta, field, filename, data, content_type = multipart
            boundary = uuid.uuid4().hex
            body = b"".join([
                f'--{boundary}\r\nContent-Disposition: form-data; '
                f'name="metadata"\r\nContent-Type: application/json\r\n\r\n'
                f'{json.dumps(meta)}\r\n'.encode(),
                f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; '
                f'filename="{filename}"\r\nContent-Type: {content_type}\r\n\r\n'.encode(),
                data,
                f"\r\n--{boundary}--\r\n".encode(),
            ])
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        elif payload is not None:
            body = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        else:
            body = None
        for attempt in range(3):
            request = urllib.request.Request(
                self.base_url + path, data=body, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    raw = response.read()
                    if "json" not in (response.headers.get("Content-Type") or ""):
                        raise SystemExit(
                            f"{method} {path}: non-JSON response -- Cloudflare "
                            "Access rejected the service token")
                    return json.loads(raw)
            except urllib.error.HTTPError as error:
                detail = error.read()[:300]
                if error.code < 500:
                    raise SystemExit(
                        f"{method} {path}: HTTP {error.code} {detail!r}")
                last = f"HTTP {error.code} {detail!r}"
            except urllib.error.URLError as error:
                last = str(error)
            time.sleep(2 ** (attempt + 1))
        raise SystemExit(f"{method} {path}: giving up after retries ({last})")

    def fetch_generation_image(self, generation_id: str) -> bytes:
        request = urllib.request.Request(
            f"{self.base_url}/g/{generation_id}/image",
            headers={**self.credentials(), "User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()

    def put_semantic(self, generation_id: str, semantic: dict) -> dict:
        semantic.setdefault("schema_version", 1)
        semantic.setdefault("generated_by", {
            "provider": "claude-code",
            "model": os.environ.get("CLAUDE_MODEL", "unspecified"),
        })
        return self.request(
            "PUT", f"/api/v1/generations/{generation_id}/semantic", semantic)

    def add_tag(self, generation_id: str, name: str) -> dict:
        return self.request(
            "POST", f"/api/v1/generations/{generation_id}/tags",
            {"name": name, "created_by": "claude"})

    def upload_asset(self, generation_id: str, role: str, path: Path,
                     region: str = "") -> dict:
        content_types = {
            ".png": "image/png", ".json": "application/json",
            ".psd": "image/vnd.adobe.photoshop",
        }
        metadata = {"role": role}
        if region:
            metadata["region"] = region
        return self.request(
            "POST", f"/api/v1/generations/{generation_id}/assets",
            multipart=(metadata, "file", path.name, path.read_bytes(),
                       content_types.get(path.suffix.lower(),
                                         "application/octet-stream")))

    def list_assets(self, generation_id: str) -> list[dict]:
        return self.request(
            "GET", f"/api/v1/generations/{generation_id}/assets").get("assets", [])

    def resolve_character(self, name: str) -> str:
        listing = self.request("GET", "/api/v1/characters")
        items = listing.get("items", listing if isinstance(listing, list) else [])
        for item in items:
            if item.get("name") == name or name in (item.get("aliases") or []):
                return item["id"]
        return self.request(
            "POST", "/api/v1/characters", {"name": name, "aliases": []})["id"]
