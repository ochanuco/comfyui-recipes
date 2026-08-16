#!/usr/bin/env python3
"""Where the ComfyUI server lives. Defaults local, overridable per shell.

Every queue/post-processing script talks to a single ComfyUI instance. This
module centralizes that address so `COMFYUI_HOST` / `COMFYUI_PORT` can point
the whole toolchain at a remote box without touching each script -- CLI flags
still win when a script also exposes `--host` / `--port`, since argparse
defaults are read from here but explicit flags override them.
"""

from __future__ import annotations

import os

DEFAULT_HOST = os.environ.get("COMFYUI_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("COMFYUI_PORT", "8188"))


def base_url(host: str | None = None, port: int | None = None) -> str:
    """http://host:port with no trailing slash."""
    return f"http://{host or DEFAULT_HOST}:{port or DEFAULT_PORT}"
