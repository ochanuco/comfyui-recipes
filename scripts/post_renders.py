#!/usr/bin/env python3
"""Post finished renders to a Discord webhook: job id, filename, image.

Watches ComfyUI's history rather than hooking any one queueing script. Those
scripts return as soon as the prompt is accepted, so none of them is in a
position to post the result; and there are several of them. Polling the history
catches whatever produced the image, including work queued from the web UI.

The webhook is a credential -- anyone holding it can post to the channel -- so it
is never written into this file or into the repo. It comes from
$DISCORD_WEBHOOK, or from .local/discord-webhook, which .gitignore covers.

    uv run scripts/post_renders.py                 # watch, posting new renders
    uv run scripts/post_renders.py --once          # drain and exit
    uv run scripts/post_renders.py --backfill 5    # also post the last 5 already done

First run posts nothing from the backlog: it records what history already holds
and starts from there. A session can easily leave fifty comparison renders
behind, and dumping those into a channel is not what "post the renders" means.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from comfy_host import DEFAULT_HOST, DEFAULT_PORT

REPO = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO / ".local/ComfyUI/output"
STATE = REPO / ".local/posted-prompts.json"
WEBHOOK_FILE = REPO / ".local/discord-webhook"
USER_AGENT = "ai-comfyui-env-post-renders/1.0 (+local)"


def webhook() -> str:
    url = os.environ.get("DISCORD_WEBHOOK", "").strip()
    if url:
        return url
    if WEBHOOK_FILE.exists():
        return WEBHOOK_FILE.read_text().strip()
    raise SystemExit(
        f"no webhook: set $DISCORD_WEBHOOK or write one to {WEBHOOK_FILE}"
    )


def load_state() -> set[str]:
    if not STATE.exists():
        return set()
    return set(json.loads(STATE.read_text()))


def save_state(seen: set[str]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(sorted(seen)))


def history(host: str, port: int, max_items: int = 60) -> dict:
    url = f"http://{host}:{port}/history?max_items={max_items}"
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read())


def images_of(entry: dict) -> list[str]:
    """Output filenames of a finished prompt, in the order the graph saved them."""
    names = []
    for node_output in entry.get("outputs", {}).values():
        for image in node_output.get("images", []):
            if image.get("type") == "output":
                names.append(image["filename"])
    return names


def post(url: str, job: str, path: Path) -> int:
    """Multipart POST of one image. Returns the HTTP status."""
    boundary = uuid.uuid4().hex
    payload = json.dumps(
        {"content": f"**JOB ID** `{job}`\n**file** `{path.name}`"}
    )
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="payload_json"\r\n'
        f"Content-Type: application/json\r\n\r\n{payload}\r\n".encode(),
        f'--{boundary}\r\nContent-Disposition: form-data; name="files[0]"; '
        f'filename="{path.name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode(),
        path.read_bytes(),
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    request = urllib.request.Request(
        url,
        data=b"".join(parts),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            # Cloudflare fronts the webhook endpoint and answers urllib's default
            # User-Agent with 403 / error code 1010. curl gets through, urllib
            # does not, and the body is the only thing that says why.
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status
    except urllib.error.HTTPError as err:
        # 413 is the channel's upload limit; everything else is worth seeing too.
        print(f"  ! {path.name}: HTTP {err.code} {err.read()[:200]!r}", flush=True)
        return err.code


def drain(url: str, seen: set[str], host: str, port: int) -> int:
    """Post every finished prompt not yet seen. Returns how many images went out."""
    sent = 0
    for job, entry in history(host, port).items():
        if job in seen:
            continue
        if entry.get("status", {}).get("status_str") != "success":
            # Errored prompts are marked seen too: they will never produce an
            # image, and leaving them out means re-checking them forever.
            seen.add(job)
            continue
        for name in images_of(entry):
            path = OUTPUT_DIR / name
            if not path.exists():
                print(f"  ! {name}: missing on disk", flush=True)
                continue
            status = post(url, job, path)
            print(f"  {status} {job[:8]} {name}", flush=True)
            if status < 300:
                sent += 1
        seen.add(job)
    if sent or seen:
        save_state(seen)
    return sent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--interval", type=float, default=20.0)
    parser.add_argument("--once", action="store_true", help="drain and exit")
    parser.add_argument(
        "--backfill",
        type=int,
        default=0,
        help="on a first run, post this many of the most recent finished prompts "
        "instead of silently adopting the whole backlog",
    )
    args = parser.parse_args()

    url = webhook()
    first_run = not STATE.exists()
    seen = load_state()

    if first_run:
        done = [
            job
            for job, entry in history(args.host, args.port).items()
            if entry.get("status", {}).get("status_str") == "success"
        ]
        keep = done[-args.backfill :] if args.backfill else []
        seen = set(done) - set(keep)
        save_state(seen)
        print(
            f"first run: adopted {len(seen)} finished prompts without posting"
            + (f", backfilling {len(keep)}" if keep else ""),
            flush=True,
        )

    if args.once:
        print(f"sent {drain(url, seen, args.host, args.port)}", flush=True)
        return

    print(f"watching {args.host}:{args.port} every {args.interval}s", flush=True)
    while True:
        try:
            drain(url, seen, args.host, args.port)
        except urllib.error.URLError as err:
            # ComfyUI restarts and MPS crashes are routine here; a watcher that
            # dies with them would have to be restarted by hand every time.
            print(f"  . comfyui unreachable ({err.reason}), retrying", flush=True)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
