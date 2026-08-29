"""Crash-resumable JSON state for a generation request."""

from __future__ import annotations

import json
import uuid
from pathlib import Path


class JsonRunState:
    def load(self, path: Path) -> dict:
        if path.exists():
            return json.loads(path.read_text())
        return {"idempotency_key": str(uuid.uuid4()), "jobs": []}

    def save(self, path: Path, state: dict) -> None:
        path.write_text(json.dumps(state, indent=2))
