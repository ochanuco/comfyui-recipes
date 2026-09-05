"""Crash-resumable JSON state for a generation request."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path


class JsonRunState:
    def load(self, path: Path) -> dict:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"idempotency_key": str(uuid.uuid4()), "jobs": []}

    def save(self, path: Path, state: dict) -> None:
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=path.parent,
                    prefix=f".{path.name}.", delete=False) as temporary:
                temporary_path = Path(temporary.name)
                json.dump(state, temporary, indent=2)
                temporary.flush()
            os.replace(temporary_path, path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
