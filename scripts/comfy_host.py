#!/usr/bin/env python3
"""Where the ComfyUI server lives. Defaults local, overridable per shell.

Every queue/post-processing script talks to a single ComfyUI instance. This
module centralizes that address so `COMFYUI_HOST` / `COMFYUI_PORT` can point
the whole toolchain at a remote box without touching each script -- CLI flags
still win when a script also exposes `--host` / `--port`, since argparse
defaults are read from here but explicit flags override them.
"""

from __future__ import annotations

import json
import mimetypes
import os
import shutil
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

DEFAULT_HOST = os.environ.get("COMFYUI_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("COMFYUI_PORT", "8188"))

# ComfyUI's /features reports max_upload_size: 104857600 (100 MiB).
MAX_UPLOAD_BYTES = 100 * 1024 * 1024

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


def stage_input(
    src,
    input_dir,
    subfolder: str = "",
    host: str | None = None,
    port: int | None = None,
) -> str:
    """Put an image where LoadImage can see it, and return the name to use.

    Local runs only need the copy into ComfyUI's own input directory. Remote
    runs also push it through /upload/image, since that directory lives on
    the other machine. The returned string is what a LoadImage node's
    `image` input expects -- "name" or "subfolder/name".
    """
    src = Path(src)
    input_dir = Path(input_dir)
    dest_dir = input_dir / subfolder if subfolder else input_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name

    # Skip the copy when src already is the staged file -- shutil.copyfile
    # would otherwise raise SameFileError.
    if not (dest.exists() and os.path.samefile(src, dest)):
        shutil.copyfile(src, dest)

    if not is_remote(host):
        return f"{subfolder}/{src.name}" if subfolder else src.name

    data = dest.read_bytes()
    if len(data) > MAX_UPLOAD_BYTES:
        raise RuntimeError(
            f"{dest} is {len(data)} bytes, over the /upload/image "
            f"{MAX_UPLOAD_BYTES}-byte limit"
        )

    # A boundary that cannot appear inside the file's own bytes.
    boundary = uuid.uuid4().hex
    while boundary.encode() in data:
        boundary = uuid.uuid4().hex

    fields = {"subfolder": subfolder, "type": "input", "overwrite": "true"}
    parts = []
    for name, value in fields.items():
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode()
        )
    content_type = mimetypes.guess_type(src.name)[0] or "application/octet-stream"
    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="{src.name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode()
    )
    parts.append(data)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)

    url = f"{base_url(host, port)}/upload/image"
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"upload of {dest} to {url} failed: "
            f"{exc.code} {exc.read().decode(errors='replace')}"
        ) from exc

    remote_name = result["name"]
    remote_subfolder = result.get("subfolder", "")
    return f"{remote_subfolder}/{remote_name}" if remote_subfolder else remote_name
