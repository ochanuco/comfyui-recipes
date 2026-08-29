"""Generation metadata use cases."""

from __future__ import annotations

import json
from pathlib import Path


def put_semantic(client, generation_id: str, path: Path) -> None:
    client.put_semantic(generation_id, json.loads(path.read_text()))


def add_tag(client, generation_id: str, name: str) -> None:
    client.add_tag(generation_id, name)


def upload_asset(client, generation_id: str, role: str, path: Path,
                 region: str = "") -> dict:
    return client.upload_asset(generation_id, role, path, region)


def list_assets(client, generation_id: str) -> list[dict]:
    return client.list_assets(generation_id)
