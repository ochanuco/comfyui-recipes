"""Generate-and-record use case.

The application layer owns the workflow and depends on small adapter
interfaces.  HTTP, files, credentials and graph node details stay outside it.
"""

from __future__ import annotations

import json
import secrets
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace as spec_replace
from pathlib import Path
from typing import Protocol

from ..domain.generation.models import PromptPair, RenderSpec
from ..domain.generation.patches import apply_patches, parse_patches


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

KNOWN_PARAMETERS = frozenset(
    {"pose", "costume", "hires", "denoise", "character", "character_id", "arm"})


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
    measure: Callable[[bytes], dict] | None = None


def validate_request(req: object) -> None:
    if not isinstance(req, Mapping):
        raise SystemExit("request root must be an object")
    if req.get("schema_version") != 1:
        raise SystemExit("schema_version must be 1")
    request = req.get("request")
    if not isinstance(request, Mapping):
        raise SystemExit("request must be an object")
    generation = req.get("generation")
    if not isinstance(generation, Mapping):
        raise SystemExit("generation must be an object")
    semantic = req.get("semantic")
    if not isinstance(semantic, Mapping):
        raise SystemExit("semantic must be an object")
    parameters = generation.get("parameters", {})
    if not isinstance(parameters, Mapping):
        raise SystemExit("generation.parameters must be an object")
    count = request.get("count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise SystemExit("request.count must be an integer >= 1")
    seeds = request.get("seeds")
    if seeds is not None:
        if (not isinstance(seeds, list)
                or any(not isinstance(seed, int) or isinstance(seed, bool)
                       for seed in seeds)):
            raise SystemExit("request.seeds must be an array of integers")
        if len(seeds) != count:
            raise SystemExit(f"len(seeds)={len(seeds)} but count={count}")
    if generation.get("graph"):
        if not isinstance(generation["graph"], dict) or not generation["graph"]:
            raise SystemExit("generation.graph must be a non-empty graph dict")
        if not generation.get("recipe"):
            raise SystemExit("generation.recipe must name what this graph is")
    elif generation.get("recipe") != "yukari":
        raise SystemExit(f"recipe {generation.get('recipe')!r} not supported yet")
    elif not parameters.get("pose"):
        raise SystemExit("generation.parameters.pose is required for yukari")
    elif set(parameters) - KNOWN_PARAMETERS:
        unknown = sorted(set(parameters) - KNOWN_PARAMETERS)
        raise SystemExit(
            f"unknown generation.parameters keys: {unknown} -- annotations "
            "belong in semantic.attributes, executable diffs in "
            "generation.patches"
        )
    if generation.get("patches") is not None:
        if generation.get("graph"):
            raise SystemExit(
                "generation.patches cannot combine with generation.graph -- "
                "the explicit graph is already the whole spec"
            )
        if generation.get("prompt") or generation.get("negative_prompt"):
            raise SystemExit(
                "generation.patches cannot combine with generation.prompt or "
                "generation.negative_prompt -- ordering between a full "
                "override and a patch would be ambiguous"
            )
        try:
            parse_patches(generation["patches"])
        except ValueError as error:
            raise SystemExit(str(error))
    if not semantic.get("summary"):
        raise SystemExit(
            "request.semantic.summary is required: state this arm's intent "
            "(what it tries, what it varies from the base) -- it is written "
            "to every generation at ingest"
        )


def request_graph(generation: dict, seed: int, prefix: str,
                  spec_builder: Callable[..., RenderSpec],
                  encode: Callable) -> dict:
    """Build a job graph while preserving explicit graphs verbatim.

    Seed inputs and SaveImage prefixes are job properties, so those are the
    only fields rewritten in explicit graph mode. Recipe mode instead builds
    a RenderSpec, applies request-level diffs to it, and only then encodes.
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
    spec = spec_builder(
        params["pose"], seed, prefix,
        hires=params.get("hires", 0),
        denoise=params.get("denoise"),
        costume=params.get("costume", "default"),
    )
    if generation.get("prompt") or generation.get("negative_prompt"):
        spec = spec_replace(spec, prompts=PromptPair(
            generation.get("prompt") or spec.prompts.positive,
            generation.get("negative_prompt") or spec.prompts.negative))
    if generation.get("patches"):
        spec = apply_patches(spec, parse_patches(generation["patches"]))
    return encode(spec)


def graph_prompts(graph: dict) -> tuple[str | None, str | None]:
    """Read the prompt pair a graph actually carries, following the sampler.

    A hires graph has more than one CLIPTextEncode pair, so the text is taken
    from whatever the first sampler is wired to rather than from fixed ids.
    """
    samplers = sorted(
        (key for key, node in graph.items()
         if "KSampler" in str(node.get("class_type"))),
        key=lambda key: (int("".join(ch for ch in key if ch.isdigit()) or 0), key),
    )
    if not samplers:
        return None, None
    inputs = graph[samplers[0]].get("inputs", {})

    def text(slot: str) -> str | None:
        link = inputs.get(slot)
        if not isinstance(link, list) or not link:
            return None
        return graph.get(link[0], {}).get("inputs", {}).get("text")

    return text("positive"), text("negative")


def batch_payload(req: dict, git: dict, idempotency_key: str,
                  prompts: tuple[str | None, str | None] = (None, None)) -> dict:
    generation = req["generation"]
    payload = {
        "idempotency_key": idempotency_key,
        "raw_instruction": req["request"]["instruction"],
        "recipe": generation["recipe"],
        "parameters": generation.get("parameters", {}),
        "git_commit": git["commit"],
        "git_dirty": git["dirty"],
    }
    for key, rendered in zip(("prompt", "negative_prompt"), prompts):
        value = generation.get(key) or rendered
        if value:
            payload[key] = value
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


def _output_directory(root: Path, identifier: object) -> Path:
    if (not isinstance(identifier, str) or not identifier
            or identifier in (".", "..")
            or "/" in identifier or "\\" in identifier):
        raise ValueError(f"invalid batch output identifier: {identifier!r}")
    resolved_root = root.resolve()
    output_dir = (root / identifier).resolve()
    if output_dir.parent != resolved_root:
        raise ValueError(f"batch output escapes output root: {identifier!r}")
    return output_dir


def _image_output_path(output_dir: Path, filename: object) -> Path:
    if not isinstance(filename, str) or not filename:
        raise ValueError(f"invalid ComfyUI output filename: {filename!r}")
    resolved_dir = output_dir.resolve()
    output_path = (output_dir / filename).resolve()
    if output_path == resolved_dir or not output_path.is_relative_to(resolved_dir):
        raise ValueError(f"ComfyUI output escapes batch directory: {filename!r}")
    return output_path


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
    if generation.get("patches"):
        try:
            services.graph_builder(generation, 0, "chimera-probe")
        except ValueError as error:
            raise SystemExit(f"patch compile failed: {error}")
    git = services.git_metadata()
    if dry_run:
        seeds = _seeds(req)
        graph = services.graph_builder(generation, seeds[0], "chimera-dryrun-0")
        services.emit("batch payload:")
        services.emit(json.dumps(
            batch_payload(req, git, "<uuid4>", graph_prompts(graph)),
            indent=2, ensure_ascii=False))
        services.emit(f"seeds: {seeds}")
        # A hires graph has suffixed node ids (6b, 7b); a plain int key dies.
        services.emit("graph nodes: " + str(sorted(
            graph, key=lambda key: (int("".join(
                ch for ch in key if ch.isdigit())), key))))
        positive = graph.get("6", {}).get("inputs", {}).get("text")
        if positive:
            services.emit(f"positive: {positive[:120]}...")
        if generation.get("patches"):
            services.emit(f"patches: {len(generation['patches'])} applied")
        return

    state_path = request_path.with_suffix(request_path.suffix + ".state.json")
    state = services.state.load(state_path)
    for reference in req.get("references") or []:
        services.management.request(
            "GET", f"/api/v1/generations/{reference['generation_id']}/context")
    batch = services.management.request(
        "POST", "/api/v1/batches",
        batch_payload(req, git, state["idempotency_key"],
                      graph_prompts(services.graph_builder(
                          generation, 0, "chimera-probe"))),
    )
    state["batch_id"] = batch["id"]
    state.setdefault("seeds", _seeds(req))
    services.state.save(state_path, state)
    short = batch.get("short_id", batch["id"][:8])
    services.emit(f"batch {batch['id']} ({short})")
    services.management.request(
        "PATCH", f"/api/v1/batches/{state['batch_id']}", {"status": "running"})

    output_dir = _output_directory(services.output_root, short)
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
                output_path = _image_output_path(output_dir, image.get("filename"))
                output = next(
                    (item for item in job["generations"]
                     if item.get("comfy_output_index") == output_index),
                    None,
                )
                if (output is None and output_index < len(job["generations"])
                        and "comfy_output_index"
                        not in job["generations"][output_index]):
                    output = job["generations"][output_index]
                if output is None:
                    output = {
                        "idempotency_key": str(uuid.uuid4()),
                        "comfy_output_index": output_index,
                    }
                    job["generations"].append(output)
                if output.get("status") == "registered" or output.get("id"):
                    continue
                if "idempotency_key" not in output:
                    output["idempotency_key"] = str(uuid.uuid4())
                output.setdefault("comfy_output_index", output_index)
                services.state.save(state_path, state)
                data = services.comfyui.fetch(image)
                output_path.write_bytes(data)
                palette = None
                if services.measure is not None:
                    try:
                        summary = services.measure(data)
                    except Exception as error:
                        services.emit(f"  ! palette measure failed: {error}")
                    else:
                        palette = {key: round(value, 1) for key, value in summary.items()
                                   if isinstance(value, (int, float))
                                   and not isinstance(value, bool)}
                        palette["verdict"] = (
                            "FAIL: " + "; ".join(summary["fails"])
                            if summary["fails"] else "pass")
                        services.emit(
                            f"  palette {'FAIL' if summary['fails'] else 'pass'}: "
                            f"fig mid {summary['fig_sat_mean']:.1f} "
                            f"light {summary['light_sat']:.1f}")
                meta = {"seed": seed, "original_filename": image["filename"],
                        "comfy_output_index": output_index,
                        "idempotency_key": output["idempotency_key"]}
                if character_id:
                    meta["character_id"] = character_id
                rendered = services.management.request(
                    "POST", f"/api/v1/jobs/{job['job_id']}/generations",
                    multipart=(meta, "image", image["filename"], data, "image/png"),
                )
                output.update(
                    {key: rendered[key]
                     for key in ("id", "short_id", "canonical_url")})
                output["status"] = "registered"
                services.state.save(state_path, state)
                semantic = json.loads(json.dumps(req["semantic"]))
                semantic.setdefault("attributes", {}).update(
                    {"seed": seed, **{key: value for key, value in params.items()
                                      if key in ("arm", "pose", "costume")}})
                if generation.get("patches"):
                    semantic["attributes"]["patches"] = generation["patches"]
                if palette:
                    semantic["attributes"]["palette"] = palette
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
