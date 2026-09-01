"""Turn chimera's pending ExperimentRuns into generations.

This is the bridge between a Cloudflare-hosted Agent (which cannot reach the
render host) and a local `comfy-recipes generate`. A pending Run carries
`overrides` and `base_parameters`, and finishing one means a `batch_id` gets
attached to it -- that PATCH already happens inside `generate()`. Nothing
about evaluation, decision, promotion, or the rest of the Experiment
lifecycle belongs in this module.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .generate import GenerateServices, generate, validate_request

PENDING_RUNS_PATH = "/api/v1/experiment-runs?pending=true"


class Management(Protocol):
    def request(self, method: str, path: str, payload: dict | None = None,
                multipart: tuple[dict, str, str, bytes, str] | None = None) -> dict: ...


class SkipRun(ValueError):
    """A pending ExperimentRun cannot be turned into a request."""


@dataclass(frozen=True)
class WatchServices:
    management: Management
    generate_services: GenerateServices
    generate: Callable[..., None] = generate
    emit: Callable[[str], None] = print
    sleep: Callable[[float], None] = time.sleep


def _fallback_summary(item: Mapping) -> str:
    experiment = item.get("experiment") or {}
    name = experiment.get("name") or experiment.get("id") or "experiment"
    run_index = item.get("run_index")
    suffix = "" if run_index is None else f" run #{run_index}"
    return f"{name}{suffix}"


def build_request(item: Mapping) -> dict:
    """Build a comfy-recipes request.json body from one pending Run item.

    Raises SkipRun when the item's experiment names no base_recipe -- there
    is nothing to generate from. Callers should also run the result through
    validate_request, since a base_recipe alone does not guarantee the rest
    of the shape (e.g. a required pose) is present.
    """
    experiment = item.get("experiment") or {}
    base_recipe = experiment.get("base_recipe")
    if not base_recipe:
        raise SkipRun(f"run {item.get('id')}: experiment has no base_recipe")
    base_parameters = experiment.get("base_parameters")
    if base_parameters is not None and not isinstance(base_parameters, Mapping):
        raise SkipRun(
            f"run {item.get('id')}: base_parameters must be a mapping, got "
            f"{type(base_parameters).__name__}")
    parameters = dict(base_parameters or {})
    count = parameters.pop("count", 1)
    summary = item.get("objective") or _fallback_summary(item)
    return {
        "schema_version": 1,
        "request": {"instruction": summary, "count": count},
        "generation": {"recipe": base_recipe, "parameters": parameters},
        "semantic": {"summary": summary},
        "experiment": {
            "experiment_id": item.get("experiment_id"),
            "run_id": item.get("id"),
            "overrides": item.get("overrides"),
        },
    }


def _request_path(output_root: Path, run_id: object) -> Path:
    # A stable path per Run (not a fresh temp file each poll) is what makes
    # the CLI's <request>.state.json idempotency-key cache work on a resend.
    # The id names a file, so it gets the same containment check generate()
    # applies to batch output identifiers.
    if (not isinstance(run_id, str) or not run_id or run_id in (".", "..")
            or "/" in run_id or "\\" in run_id):
        raise SkipRun(f"invalid run id: {run_id!r}")
    return output_root / "experiment-runs" / f"{run_id}.json"


def poll_once(services: WatchServices, *, dry_run: bool = False) -> None:
    # A single Run's build/validate/write/generate is isolated here so one
    # malformed or failing Run cannot stop the rest of the batch from
    # running. KeyboardInterrupt is a BaseException, not an Exception, so it
    # is deliberately left uncaught and keeps propagating to watch()'s loop.
    response = services.management.request("GET", PENDING_RUNS_PATH)
    for item in response.get("items", []):
        run_id = item.get("id")
        try:
            request = build_request(item)
            validate_request(request)
            request_path = _request_path(
                services.generate_services.output_root, run_id)
            request_path.parent.mkdir(parents=True, exist_ok=True)
            request_path.write_text(
                json.dumps(request, indent=2, ensure_ascii=False))
            services.generate(
                request_path, services.generate_services, dry_run=dry_run)
        except (SystemExit, Exception) as error:
            services.emit(f"skip run {run_id}: {error}")


def watch(services: WatchServices, *, interval: float = 30, once: bool = False,
          dry_run: bool = False) -> None:
    try:
        while True:
            poll_once(services, dry_run=dry_run)
            if once:
                return
            services.sleep(interval)
    except KeyboardInterrupt:
        services.emit("watch stopped")
