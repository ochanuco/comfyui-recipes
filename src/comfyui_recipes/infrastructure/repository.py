"""Repository provenance adapter."""

from __future__ import annotations

import subprocess
from pathlib import Path


def git_metadata(repository: Path) -> dict:
    def output(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=repository, check=True,
            capture_output=True, text=True,
        ).stdout.strip()

    return {
        "commit": output("rev-parse", "HEAD"),
        "branch": output("branch", "--show-current"),
        "dirty": bool(output("status", "--porcelain")),
    }
