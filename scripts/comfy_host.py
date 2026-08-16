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
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_HOST = os.environ.get("COMFYUI_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("COMFYUI_PORT", "8188"))

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def base_url(host: str | None = None, port: int | None = None) -> str:
    """http://host:port with no trailing slash."""
    return f"http://{host or DEFAULT_HOST}:{port or DEFAULT_PORT}"


def is_remote(host: str | None = None) -> bool:
    """True when ComfyUI runs on another machine, so files are not shared."""
    return (host or DEFAULT_HOST) not in _LOCAL_HOSTS


def ensure_local(
    filename: str,
    output_dir,
    subfolder: str = "",
    type_: str = "output",
    host: str | None = None,
    port: int | None = None,
) -> Path:
    """Path to the rendered image on this disk, pulling it over HTTP if needed.

    Local runs already share the filesystem with ComfyUI, so this just points
    at the file. Remote runs fetch it through /view into the same place, which
    keeps every downstream script working on a plain local path.
    """
    output_dir = Path(output_dir)
    path = output_dir / subfolder / filename if subfolder else output_dir / filename

    if not is_remote(host):
        return path

    if path.exists() and path.stat().st_size > 0:
        return path

    query = urllib.parse.urlencode(
        {"filename": filename, "subfolder": subfolder, "type": type_}
    )
    url = f"{base_url(host, port)}/view?{query}"
    path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()
    if not data:
        raise RuntimeError(f"empty response fetching {url}")
    path.write_bytes(data)
    return path
