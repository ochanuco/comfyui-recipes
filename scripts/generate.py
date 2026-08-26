"""Run one generation batch from a request.json, recorded in chimera.

Claude Code interprets the human's intent and writes the request; this script
only validates, executes and records (chimera/docs/architecture.md). Usage:

    uv run scripts/generate.py --request request.json [--dry-run]

Everything that must survive a crash -- idempotency keys, batch/job ids, the
seeds -- lives in <request>.state.json next to the request file, so re-running
the same command resumes instead of duplicating records.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comfy_host
import post_renders

BASE = os.environ.get("CHIMERA_BASE_URL", "https://chimera.chanu.co").rstrip("/")
REPO = Path(__file__).resolve().parent.parent
WORKDIR = REPO / ".local/_nogit/chimera"
OP_ITEM = "yml6r5qgx3zt57pryokgi3xdqy"
TOKEN_CACHE = REPO / ".local/chimera-token"
POLL_INTERVAL = 10
POLL_TIMEOUT = 20 * 60


def credentials() -> dict[str, str]:
    cid = os.environ.get("CHIMERA_CF_CLIENT_ID", "").strip()
    sec = os.environ.get("CHIMERA_CF_CLIENT_SECRET", "").strip()
    if not (cid and sec) and TOKEN_CACHE.exists():
        # Untracked cache, same standing as .local/discord-webhook: `op`
        # prompts Touch ID on every fetch, which makes unattended runs stall.
        cid, sec, *_ = TOKEN_CACHE.read_text().splitlines() + ["", ""]
        cid, sec = cid.strip(), sec.strip()
    if not (cid and sec):
        def field(label: str) -> str:
            return subprocess.run(
                ["op", "item", "get", OP_ITEM, "--fields", f"label={label}",
                 "--reveal"],
                check=True, capture_output=True, text=True).stdout.strip()
        cid, sec = field("CF-Access-Client-Id"), field("CF-Access-Client-Secret")
        TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE.touch(mode=0o600)
        TOKEN_CACHE.write_text(f"{cid}\n{sec}\n")
    return {"CF-Access-Client-Id": cid, "CF-Access-Client-Secret": sec}


def api(method: str, path: str, payload: dict | None = None,
        multipart: tuple[dict, str, bytes] | None = None) -> dict:
    """One Management API call. Retries transport errors and 5xx; a non-JSON
    response is Cloudflare Access bouncing us to login, not data."""
    url = BASE + path
    # Cloudflare answers urllib's default User-Agent with 403 / error 1010,
    # exactly as it does for the Discord webhook in post_renders.py.
    headers = {**_CREDS, "User-Agent": post_renders.USER_AGENT}
    if multipart:
        meta, filename, image = multipart
        boundary = uuid.uuid4().hex
        body = b"".join([
            f'--{boundary}\r\nContent-Disposition: form-data; name="metadata"\r\n'
            f"Content-Type: application/json\r\n\r\n{json.dumps(meta)}\r\n".encode(),
            f'--{boundary}\r\nContent-Disposition: form-data; name="image"; '
            f'filename="{filename}"\r\nContent-Type: image/png\r\n\r\n'.encode(),
            image,
            f"\r\n--{boundary}--\r\n".encode(),
        ])
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    else:
        body = None
    for attempt in range(3):
        request = urllib.request.Request(url, data=body, headers=headers,
                                         method=method)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                text = response.read()
                if "json" not in (response.headers.get("Content-Type") or ""):
                    raise SystemExit(
                        f"{method} {path}: non-JSON response -- Cloudflare "
                        "Access rejected the service token")
                return json.loads(text)
        except urllib.error.HTTPError as err:
            detail = err.read()[:300]
            if err.code < 500:
                raise SystemExit(f"{method} {path}: HTTP {err.code} {detail!r}")
            last = f"HTTP {err.code} {detail!r}"
        except urllib.error.URLError as err:
            last = str(err)
        time.sleep(2 ** (attempt + 1))
    raise SystemExit(f"{method} {path}: giving up after retries ({last})")


def git_metadata() -> dict:
    def out(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=REPO, check=True,
                              capture_output=True, text=True).stdout.strip()
    return {
        "commit": out("rev-parse", "HEAD"),
        "branch": out("branch", "--show-current"),
        "dirty": bool(out("status", "--porcelain")),
    }


def validate(req: dict) -> None:
    if req.get("schema_version") != 1:
        raise SystemExit("schema_version must be 1")
    count = req.get("request", {}).get("count")
    if not isinstance(count, int) or count < 1:
        raise SystemExit("request.count must be an integer >= 1")
    seeds = req.get("request", {}).get("seeds")
    if seeds is not None and len(seeds) != count:
        raise SystemExit(f"len(seeds)={len(seeds)} but count={count}")
    gen = req.get("generation", {})
    if gen.get("recipe") != "yukari":
        raise SystemExit(f"recipe {gen.get('recipe')!r} not supported yet")
    if not gen.get("parameters", {}).get("pose"):
        raise SystemExit("generation.parameters.pose is required for yukari")


def check_references(req: dict) -> None:
    for ref in req.get("references") or []:
        api("GET", f"/api/v1/generations/{ref['generation_id']}/context")


def build_graph(gen: dict, seed: int, prefix: str) -> dict:
    import yukari_recipe
    params = gen.get("parameters", {})
    graph = yukari_recipe.build(
        params["pose"], seed, prefix,
        hires=params.get("hires", 0),
        denoise=params.get("denoise"),
        costume=params.get("costume", "default"),
    )
    # The recipe is the default; an explicit prompt in the request replaces the
    # node text wholesale rather than splicing, so what was sent is what ran.
    if gen.get("prompt"):
        graph["6"]["inputs"]["text"] = gen["prompt"]
    if gen.get("negative_prompt"):
        graph["7"]["inputs"]["text"] = gen["negative_prompt"]
    return graph


def comfy(path: str, payload: dict | None = None) -> dict:
    request = urllib.request.Request(
        comfy_host.base_url() + path,
        data=json.dumps(payload).encode() if payload else None,
        headers={"Content-Type": "application/json"} if payload else {},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def wait_for(prompt_id: str) -> list[dict]:
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        entry = comfy(f"/history/{prompt_id}").get(prompt_id)
        if entry:
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                raise RuntimeError(f"comfy job {prompt_id} failed")
            images = post_renders.images_of(entry)
            if images:
                return images
        time.sleep(POLL_INTERVAL)
    raise RuntimeError(f"comfy job {prompt_id} timed out")


def fetch(image: dict) -> bytes:
    query = urllib.parse.urlencode({
        "filename": image["filename"],
        "subfolder": image.get("subfolder", ""),
        "type": image.get("type", "output"),
    })
    with urllib.request.urlopen(comfy_host.base_url() + "/view?" + query,
                                timeout=120) as response:
        return response.read()


def notify(content: str, filename: str, image: bytes) -> None:
    try:
        url = post_renders.webhook()
    except SystemExit:
        print("  ! no Discord webhook configured, skipping notification")
        return
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    body = b"".join([
        f'--{boundary}\r\nContent-Disposition: form-data; name="payload_json"\r\n'
        f"Content-Type: application/json\r\n\r\n"
        f"{json.dumps({'content': content})}\r\n".encode(),
        f'--{boundary}\r\nContent-Disposition: form-data; name="files[0]"; '
        f'filename="{filename}"\r\nContent-Type: {ctype}\r\n\r\n'.encode(),
        image,
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    request = urllib.request.Request(url, data=body, headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": post_renders.USER_AGENT,
    })
    try:
        urllib.request.urlopen(request, timeout=120)
    except urllib.error.HTTPError as err:
        print(f"  ! Discord: HTTP {err.code} {err.read()[:200]!r}")


def resolve_character(name: str) -> str:
    """Name to UUID; the ingest metadata wants the id, not the name."""
    listing = api("GET", "/api/v1/characters")
    for item in listing.get("items", listing if isinstance(listing, list) else []):
        if item.get("name") == name or name in (item.get("aliases") or []):
            return item["id"]
    created = api("POST", "/api/v1/characters", {"name": name, "aliases": []})
    return created["id"]


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"idempotency_key": str(uuid.uuid4()), "jobs": []}


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2))


def batch_payload(req: dict, git: dict, idempotency_key: str) -> dict:
    """The batch row is the provenance record: the API takes these flat,
    treats them all as optional, and stores NULL for whatever is not sent --
    this mapping is what decides whether a picture can be traced later."""
    gen = req["generation"]
    payload = {
        "idempotency_key": idempotency_key,
        "raw_instruction": req["request"]["instruction"],
        "recipe": gen["recipe"],
        "parameters": gen.get("parameters", {}),
        "git_commit": git["commit"],
        "git_dirty": git["dirty"],
    }
    # Optional blocks want absent keys, not explicit nulls.
    for key in ("prompt", "negative_prompt"):
        if gen.get(key):
            payload[key] = gen[key]
    if req.get("references"):
        # The request contract says generation_id; the API's reference rows
        # say source_generation_id. Map at the boundary, keep the contract.
        payload["references"] = [
            {**{k: v for k, v in ref.items() if k != "generation_id"},
             "source_generation_id": ref["generation_id"]}
            for ref in req["references"]]
    for key in ("refinement", "story"):
        if req.get(key):
            payload[key] = req[key]
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    req = json.loads(args.request.read_text())
    validate(req)
    git = git_metadata()

    if args.dry_run:
        seeds = (req["request"].get("seeds")
                 or [secrets.randbelow(2 ** 32)
                     for _ in range(req["request"]["count"])])
        graph = build_graph(req["generation"], seeds[0], "chimera-dryrun-0")
        print("batch payload:")
        print(json.dumps(batch_payload(req, git, "<uuid4>"),
                         indent=2, ensure_ascii=False))
        print(f"seeds: {seeds}")
        print(f"graph nodes: {sorted(graph, key=int)}")
        print(f"positive: {graph['6']['inputs']['text'][:120]}...")
        return

    global _CREDS
    _CREDS = credentials()

    state_path = args.request.with_suffix(args.request.suffix + ".state.json")
    state = load_state(state_path)
    check_references(req)

    batch = api("POST", "/api/v1/batches",
                batch_payload(req, git, state["idempotency_key"]))
    state["batch_id"] = batch["id"]
    if "seeds" not in state:
        state["seeds"] = (req["request"].get("seeds")
                          or [secrets.randbelow(2 ** 32)
                              for _ in range(req["request"]["count"])])
    save_state(state_path, state)
    short = batch.get("short_id", batch["id"][:8])
    print(f"batch {batch['id']} ({short})")
    api("PATCH", f"/api/v1/batches/{state['batch_id']}", {"status": "running"})

    outdir = WORKDIR / short
    outdir.mkdir(parents=True, exist_ok=True)
    params = req["generation"].get("parameters", {})
    character_id = params.get("character_id")
    if not character_id and params.get("character"):
        character_id = resolve_character(params["character"])

    for index, seed in enumerate(state["seeds"]):
        while len(state["jobs"]) <= index:
            state["jobs"].append({"idempotency_key": str(uuid.uuid4())})
        job = state["jobs"][index]
        if job.get("status") == "ingested":
            continue
        try:
            if "job_id" not in job:
                created = api("POST",
                              f"/api/v1/batches/{state['batch_id']}/jobs",
                              {"idempotency_key": job["idempotency_key"],
                               "seed": seed, "index": index})
                job["job_id"] = created["id"]
                save_state(state_path, state)
            if "comfy_prompt_id" not in job:
                graph = build_graph(req["generation"], seed,
                                    f"chimera-{short}-{index}")
                job["comfy_prompt_id"] = comfy("/prompt",
                                               {"prompt": graph})["prompt_id"]
                save_state(state_path, state)
                api("PATCH", f"/api/v1/jobs/{job['job_id']}",
                    {"status": "queued",
                     "comfy_prompt_id": job["comfy_prompt_id"]})
            api("PATCH", f"/api/v1/jobs/{job['job_id']}", {"status": "running"})
            images = wait_for(job["comfy_prompt_id"])
            api("PATCH", f"/api/v1/jobs/{job['job_id']}",
                {"status": "completed"})

            job.setdefault("generations", [])
            for output_index, image in enumerate(images):
                data = fetch(image)
                (outdir / image["filename"]).write_bytes(data)
                meta = {"seed": seed, "original_filename": image["filename"],
                        "comfy_output_index": output_index}
                if character_id:
                    meta["character_id"] = character_id
                generation = api(
                    "POST", f"/api/v1/jobs/{job['job_id']}/generations",
                    multipart=(meta, image["filename"], data))
                job["generations"].append(
                    {k: generation[k]
                     for k in ("id", "short_id", "canonical_url")})
                save_state(state_path, state)
                notify(f"**JOB ID** `{job['comfy_prompt_id']}`\n"
                       f"**file** `{image['filename']}`\n"
                       f"**chimera** {generation['canonical_url']}",
                       image["filename"], data)
            api("PATCH", f"/api/v1/jobs/{job['job_id']}",
                {"status": "ingested"})
            job["status"] = "ingested"
        except (RuntimeError, urllib.error.URLError, OSError) as err:
            print(f"  ! job {index} (seed {seed}): {err}")
            job["status"] = "failed"
            if "job_id" in job:
                api("PATCH", f"/api/v1/jobs/{job['job_id']}",
                    {"status": "failed"})
        save_state(state_path, state)

    done = sum(1 for j in state["jobs"] if j.get("status") == "ingested")
    status = ("completed" if done == len(state["seeds"])
              else "partial" if done else "failed")
    api("PATCH", f"/api/v1/batches/{state['batch_id']}", {"status": status})
    print(f"batch {status}: {done}/{len(state['seeds'])} jobs ingested")


if __name__ == "__main__":
    main()
