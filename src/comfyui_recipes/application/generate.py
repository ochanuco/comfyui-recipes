"""Generate-and-record use case.

The application layer owns the workflow and depends on small adapter
interfaces.  HTTP, files, credentials and graph node details stay outside it.
"""

from __future__ import annotations

import json
import secrets
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol


class Management(Protocol):
    def request(self, method: str, path: str, payload: dict | None = None,
                multipart: tuple[dict, str, str, bytes, str] | None = None) -> dict: ...

    def resolve_character(self, name: str) -> str: ...

    def put_semantic(self, generation_id: str, semantic: dict) -> dict: ...


class ComfyUI(Protocol):
    def submit(self, graph: dict) -> str: ...

    def wait_for(self, prompt_id: str) -> list[dict]: ...

    def fetch(self, image: dict) -> bytes: ...


class RunState(Protocol):
    def load(self, path: Path) -> dict: ...

    def save(self, path: Path, state: dict) -> None: ...


class Notifier(Protocol):
    def send(self, content: str, filename: str, image: bytes) -> None: ...


GraphBuilder = Callable[[dict, int, str], dict]
ConflictFinder = Callable[[str, str], list[tuple[str, str, str]]]


@dataclass(frozen=True)
class GenerateServices:
    management: Management
    comfyui: ComfyUI
    state: RunState
    notifier: Notifier
    graph_builder: GraphBuilder
    git_metadata: Callable[[], dict]
    conflicts: ConflictFinder
    output_root: Path
    emit: Callable[[str], None] = print


def validate_request(req: dict) -> None:
    if req.get("schema_version") != 1:
        raise SystemExit("schema_version must be 1")
    count = req.get("request", {}).get("count")
    if not isinstance(count, int) or count < 1:
        raise SystemExit("request.count must be an integer >= 1")
    seeds = req.get("request", {}).get("seeds")
    if seeds is not None and len(seeds) != count:
        raise SystemExit(f"len(seeds)={len(seeds)} but count={count}")
    generation = req.get("generation", {})
    if generation.get("graph"):
        if not isinstance(generation["graph"], dict) or not generation["graph"]:
            raise SystemExit("generation.graph must be a non-empty graph dict")
        if not generation.get("recipe"):
            raise SystemExit("generation.recipe must name what this graph is")
    elif generation.get("recipe") != "yukari":
        raise SystemExit(f"recipe {generation.get('recipe')!r} not supported yet")
    elif not generation.get("parameters", {}).get("pose"):
        raise SystemExit("generation.parameters.pose is required for yukari")
    if not req.get("semantic", {}).get("summary"):
        raise SystemExit(
            "request.semantic.summary is required: state this arm's intent "
            "(what it tries, what it varies from the base) -- it is written "
            "to every generation at ingest"
        )


def request_graph(generation: dict, seed: int, prefix: str,
                  yukari_builder: Callable[..., dict]) -> dict:
    """Build a job graph while preserving explicit graphs verbatim.

    Seed inputs and SaveImage prefixes are job properties, so those are the
    only fields rewritten in explicit graph mode.
    """
    if generation.get("graph"):
        graph = json.loads(json.dumps(generation["graph"]))
        for node in graph.values():
            inputs = node.get("inputs", {})
            if "seed" in inputs:
                inputs["seed"] = seed
            if node.get("class_type") == "SaveImage":
                inputs["filename_prefix"] = prefix
        return graph
    params = generation.get("parameters", {})
    graph = yukari_builder(
        params["pose"], seed, prefix,
        hires=params.get("hires", 0),
        denoise=params.get("denoise"),
        costume=params.get("costume", "default"),
    )
    if generation.get("prompt"):
        graph["6"]["inputs"]["text"] = generation["prompt"]
    if generation.get("negative_prompt"):
        graph["7"]["inputs"]["text"] = generation["negative_prompt"]
    return graph


def batch_payload(req: dict, git: dict, idempotency_key: str) -> dict:
    generation = req["generation"]
    payload = {
        "idempotency_key": idempotency_key,
        "raw_instruction": req["request"]["instruction"],
        "recipe": generation["recipe"],
        "parameters": generation.get("parameters", {}),
        "git_commit": git["commit"],
        "git_dirty": git["dirty"],
    }
    for key in ("prompt", "negative_prompt"):
        if generation.get(key):
            payload[key] = generation[key]
    if req.get("references"):
        payload["references"] = [
            {**{key: value for key, value in reference.items()
                if key != "generation_id"},
             "source_generation_id": reference["generation_id"]}
            for reference in req["references"]
        ]
    for key in ("refinement", "story"):
        if req.get(key):
            payload[key] = req[key]
    return payload


def _seeds(req: dict) -> list[int]:
    return (req["request"].get("seeds")
            or [secrets.randbelow(2 ** 32)
                for _ in range(req["request"]["count"])])


def generate(request_path: Path, services: GenerateServices, *,
             dry_run: bool = False, force: bool = False) -> None:
    req = json.loads(request_path.read_text())
    validate_request(req)
    generation = req["generation"]
    if generation.get("prompt") and generation.get("negative_prompt"):
        hits = services.conflicts(
            generation["prompt"], generation["negative_prompt"])
        if hits and not force:
            for positive, negative, why in hits:
                services.emit(
                    f"positive asks ({positive}) while negative bans "
                    f"({negative})  [{why}]"
                )
            raise SystemExit(
                "prompt contradicts its negative -- fix one side, or --force "
                "if the pair is deliberate"
            )
    git = services.git_metadata()
    if dry_run:
        seeds = _seeds(req)
        graph = services.graph_builder(generation, seeds[0], "chimera-dryrun-0")
        services.emit("batch payload:")
        services.emit(json.dumps(
            batch_payload(req, git, "<uuid4>"), indent=2, ensure_ascii=False))
        services.emit(f"seeds: {seeds}")
        services.emit(f"graph nodes: {sorted(graph, key=int)}")
        positive = graph.get("6", {}).get("inputs", {}).get("text")
        if positive:
            services.emit(f"positive: {positive[:120]}...")
        return

    state_path = request_path.with_suffix(request_path.suffix + ".state.json")
    state = services.state.load(state_path)
    for reference in req.get("references") or []:
        services.management.request(
            "GET", f"/api/v1/generations/{reference['generation_id']}/context")
    batch = services.management.request(
        "POST", "/api/v1/batches",
        batch_payload(req, git, state["idempotency_key"]),
    )
    state["batch_id"] = batch["id"]
    state.setdefault("seeds", _seeds(req))
    services.state.save(state_path, state)
    short = batch.get("short_id", batch["id"][:8])
    services.emit(f"batch {batch['id']} ({short})")
    services.management.request(
        "PATCH", f"/api/v1/batches/{state['batch_id']}", {"status": "running"})

    output_dir = services.output_root / short
    output_dir.mkdir(parents=True, exist_ok=True)
    params = generation.get("parameters", {})
    character_id = params.get("character_id")
    if not character_id and params.get("character"):
        character_id = services.management.resolve_character(params["character"])

    for index, seed in enumerate(state["seeds"]):
        while len(state["jobs"]) <= index:
            state["jobs"].append({"idempotency_key": str(uuid.uuid4())})
        job = state["jobs"][index]
        if job.get("status") == "ingested":
            continue
        try:
            if "job_id" not in job:
                created = services.management.request(
                    "POST", f"/api/v1/batches/{state['batch_id']}/jobs",
                    {"idempotency_key": job["idempotency_key"],
                     "seed": seed, "index": index},
                )
                job["job_id"] = created["id"]
                services.state.save(state_path, state)
            if "comfy_prompt_id" not in job:
                graph = services.graph_builder(
                    generation, seed, f"chimera-{short}-{index}")
                job["comfy_prompt_id"] = services.comfyui.submit(graph)
                services.state.save(state_path, state)
                services.management.request(
                    "PATCH", f"/api/v1/jobs/{job['job_id']}",
                    {"status": "queued",
                     "comfy_prompt_id": job["comfy_prompt_id"],
                     "graph": graph},
                )
            services.management.request(
                "PATCH", f"/api/v1/jobs/{job['job_id']}", {"status": "running"})
            images = services.comfyui.wait_for(job["comfy_prompt_id"])
            services.management.request(
                "PATCH", f"/api/v1/jobs/{job['job_id']}", {"status": "completed"})
            job.setdefault("generations", [])
            for output_index, image in enumerate(images):
                data = services.comfyui.fetch(image)
                (output_dir / image["filename"]).write_bytes(data)
                meta = {"seed": seed, "original_filename": image["filename"],
                        "comfy_output_index": output_index}
                if character_id:
                    meta["character_id"] = character_id
                rendered = services.management.request(
                    "POST", f"/api/v1/jobs/{job['job_id']}/generations",
                    multipart=(meta, "image", image["filename"], data, "image/png"),
                )
                job["generations"].append(
                    {key: rendered[key]
                     for key in ("id", "short_id", "canonical_url")})
                services.state.save(state_path, state)
                semantic = json.loads(json.dumps(req["semantic"]))
                semantic.setdefault("attributes", {}).update(
                    {"seed": seed, **{key: value for key, value in params.items()
                                      if key in ("arm", "pose", "costume")}})
                try:
                    services.management.put_semantic(rendered["id"], semantic)
                except SystemExit as error:
                    services.emit(f"  ! semantic PUT failed: {error}")
                services.notifier.send(
                    f"**JOB ID** `{job['comfy_prompt_id']}`\n"
                    f"**file** `{image['filename']}`\n"
                    f"**chimera** {rendered['canonical_url']}",
                    image["filename"], data,
                )
            services.management.request(
                "PATCH", f"/api/v1/jobs/{job['job_id']}", {"status": "ingested"})
            job["status"] = "ingested"
        except (RuntimeError, OSError) as error:
            services.emit(f"  ! job {index} (seed {seed}): {error}")
            job["status"] = "failed"
            if "job_id" in job:
                services.management.request(
                    "PATCH", f"/api/v1/jobs/{job['job_id']}", {"status": "failed"})
        services.state.save(state_path, state)

    done = sum(1 for job in state["jobs"] if job.get("status") == "ingested")
    status = ("completed" if done == len(state["seeds"])
              else "partial" if done else "failed")
    services.management.request(
        "PATCH", f"/api/v1/batches/{state['batch_id']}", {"status": status})
    services.emit(f"batch {status}: {done}/{len(state['seeds'])} jobs ingested")
