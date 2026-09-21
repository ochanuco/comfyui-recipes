"""Claim, execute and report on chimera's `requests` queue.

The wire contract is chimera's docs/worker-protocol.md.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

from .catalog import publish_catalog as publish_catalog_document
from .finalize import FinalizeServices, finalize
from .generate import GenerateServices, generate, request_file_path
from .masked_redraw import MaskedRedrawServices, masked_redraw
from .repair import RepairServices, repair
from .request_options import (
    FINALIZE_DIAL_KEYS,
    REPAIR_DIAL_KEYS,
    _MASKED_REDRAW_DIAL_KEYS,
    _resolved_options,
    dials_scope,
    finalize_arguments,
    masked_redraw_arguments,
    repair_arguments,
)
from .worker_channels import Connection, Heartbeat, HubListener, Management, ProgressRelay

CLAIM_PATH = "/api/v1/requests/claim"
DRY_RUN_PATH = "/api/v1/requests?status=queued&limit=1"


def fetch_source(management: Management, generation_id: str) -> tuple[dict, dict, str]:
    """The requested generation's context, its batch, and that batch's recipe."""
    context = management.request(
        "GET", f"/api/v1/generations/{generation_id}/context")
    batch = management.request(
        "GET", f"/api/v1/batches/{context['batch']['id']}")
    return context, batch, batch.get("recipe") or ""


@dataclass(frozen=True)
class WorkServices:
    management: Management
    generate_services: GenerateServices
    finalize_services: FinalizeServices
    repair_services: RepairServices
    masked_redraw_services: MaskedRedrawServices
    git_metadata: Callable[[], dict]
    worker_id: str
    generate: Callable[..., dict | None] = generate
    finalize: Callable[..., dict] = finalize
    repair: Callable[..., dict] = repair
    masked_redraw: Callable[..., dict] = masked_redraw
    emit: Callable[[str], None] = print
    sleep: Callable[[float], None] = time.sleep
    heartbeat_interval: float = 30
    kinds: tuple[str, ...] = ("generate", "finalize", "repair", "masked_redraw")
    heartbeat: Callable[..., Heartbeat] = Heartbeat
    hub: Callable[[], Connection] | None = None
    draining: Callable[[], bool] | None = None
    drained: Callable[[], None] | None = None
    progress_feed: Callable[[], Connection] | None = None
    backoff_max: float = 60
    ping_interval: float = 30
    clock: Callable[[], float] = time.monotonic


def _request_path(output_root: Path, request_id: object) -> Path:
    return request_file_path(output_root, "requests", request_id)


def _execute_generate(services: WorkServices, row: Mapping) -> dict:
    request_id = row["id"]
    path = _request_path(services.generate_services.output_root, request_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(row.get("payload") or {}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    result = services.generate(
        path, services.generate_services, key_prefix=f"request:{request_id}")
    return result or {"batch_id": None, "generation_ids": []}


def _execute_finalize(services: WorkServices, row: Mapping) -> dict:
    payload = row.get("payload") or {}
    generation_id = payload.get("generation_id")
    if not generation_id:
        raise SystemExit("finalize payload.generation_id is required")
    context, _batch, recipe = fetch_source(services.management, generation_id)
    dials = dials_scope(recipe, "finalize")
    options = payload.get("options") or {}
    try:
        arguments = finalize_arguments(options, dials)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    result = services.finalize(generation_id, services.finalize_services,
                               key_prefix=f"request:{row['id']}", context=context,
                               **arguments)
    result["resolved_options"] = _resolved_options(options, arguments, FINALIZE_DIAL_KEYS)
    return result


def _execute_repair(services: WorkServices, row: Mapping) -> dict:
    payload = row.get("payload") or {}
    generation_id = payload.get("generation_id")
    if not generation_id:
        raise SystemExit("repair payload.generation_id is required")
    context, batch, recipe = fetch_source(services.management, generation_id)
    dials = dials_scope(recipe, "repair")
    options = payload.get("options") or {}
    try:
        arguments = repair_arguments(options, dials)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    result = services.repair(generation_id, services.repair_services,
                             key_prefix=f"request:{row['id']}", context=context,
                             batch=batch, **arguments)
    result["resolved_options"] = _resolved_options(options, arguments, REPAIR_DIAL_KEYS)
    return result


def _execute_masked_redraw(services: WorkServices, row: Mapping) -> dict:
    payload = row.get("payload") or {}
    generation_id = payload.get("generation_id")
    if not generation_id:
        raise SystemExit("masked_redraw payload.generation_id is required")
    context, batch, recipe = fetch_source(services.management, generation_id)
    dials = dials_scope(recipe, "repair")
    options = payload.get("options") or {}
    try:
        arguments = masked_redraw_arguments(options, dials)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    result = services.masked_redraw(generation_id, services.masked_redraw_services,
                                    key_prefix=f"request:{row['id']}", context=context,
                                    batch=batch, **arguments)
    result["resolved_options"] = _resolved_options(
        options, arguments, _MASKED_REDRAW_DIAL_KEYS)
    return result


def execute(services: WorkServices, row: Mapping) -> dict:
    ref = row.get("recipe_ref")
    if ref != services.git_metadata().get("branch"):
        raise SystemExit(f"recipe_ref not served: {ref}")
    kind = row.get("kind")
    if kind == "generate":
        return _execute_generate(services, row)
    if kind == "finalize":
        return _execute_finalize(services, row)
    if kind == "repair":
        return _execute_repair(services, row)
    if kind == "masked_redraw":
        return _execute_masked_redraw(services, row)
    raise SystemExit(f"unsupported request kind: {kind!r}")


def _report(services: WorkServices, row_id: str, payload: dict) -> None:
    try:
        services.management.request(
            "PATCH", f"/api/v1/requests/{row_id}",
            {**payload, "worker_id": services.worker_id})
    except SystemExit as error:
        services.emit(f"report failed for {row_id} (worker moved on?): {error}")


def work_once(services: WorkServices, *, dry_run: bool = False,
             listener: HubListener | None = None,
             relay: ProgressRelay | None = None) -> bool:
    if dry_run:
        response = services.management.request("GET", DRY_RUN_PATH)
        items = (response or {}).get("items", [])
        if not items:
            services.emit("no queued requests")
        else:
            services.emit("would execute:")
            services.emit(json.dumps(items[0], indent=2, ensure_ascii=False))
        return False
    try:
        row = services.management.request(
            "POST", CLAIM_PATH,
            {"worker_id": services.worker_id, "kinds": list(services.kinds)})
    except SystemExit as error:
        services.emit(f"claim failed: {error}")
        return False
    if row is None:
        return False
    if listener is not None:
        phase = "finalize" if row.get("kind") == "finalize" else "submit"
        listener.send_progress(row["id"], phase)
    failure: BaseException | None = None
    with services.heartbeat(services.management, row["id"], services.worker_id,
                            interval=services.heartbeat_interval, emit=services.emit):
        if relay is not None:
            relay.current = row["id"]
        try:
            result = execute(services, row)
        except (SystemExit, Exception) as error:
            failure = error
        finally:
            if relay is not None:
                relay.current = None
    if failure is not None:
        _report(services, row["id"], {"status": "failed", "error": str(failure)})
        services.emit(f"request {row['id']} failed: {failure}")
        return True
    _report(services, row["id"], {"status": "done", "result": result})
    services.emit(f"request {row['id']} done")
    return True


def release_claims(services: WorkServices) -> None:
    """Hand back the rows this worker still holds from a killed process.

    Otherwise they sit running until the heartbeat goes stale, and a worker
    that came back in seconds waits minutes for its own queue.
    """
    worker = quote(services.worker_id, safe="")
    try:
        response = services.management.request(
            "GET", f"/api/v1/requests?status=running&worker_id={worker}")
    except (SystemExit, Exception) as error:
        services.emit(f"! release query failed: {error}")
        return
    for row in (response or {}).get("items", []):
        if not row.get("id"):
            continue
        try:
            released = services.management.request(
                "PATCH", f"/api/v1/requests/{row['id']}",
                {"status": "queued", "worker_id": services.worker_id})
        except (SystemExit, Exception) as error:
            services.emit(f"! release failed for {row['id']}: {error}")
            continue
        status = (released or {}).get("status", "queued")
        services.emit(f"released {row['id']}: {status}")


def _draining(services: WorkServices) -> bool:
    """Never let a stop signal that cannot be read stop the worker."""
    if services.draining is None:
        return False
    try:
        return bool(services.draining())
    except (SystemExit, Exception) as error:
        services.emit(f"! drain check failed: {error}")
        return False


def _idle(services: WorkServices, wake: threading.Event | None,
          interval: float) -> None:
    """Sleep out the idle interval, cut short once a drain is asked for.

    Sliced rather than waited whole: deploy waits on this worker leaving, so
    an idle worker must not hold the deploy for the length of a poll. With no
    drain wired there is nothing to notice, so the wait stays whole.
    """
    if services.draining is None:
        if wake is not None:
            wake.wait(interval)
        else:
            services.sleep(interval)
        return
    remaining = interval
    while remaining > 0:
        slice_ = min(1.0, remaining)
        if wake is not None:
            if wake.wait(slice_):
                return
        else:
            services.sleep(slice_)
        if _draining(services):
            return
        remaining -= slice_


def work(services: WorkServices, *, interval: float = 30, once: bool = False,
         dry_run: bool = False, publish_catalog: bool = True) -> None:
    listener: HubListener | None = None
    relay: ProgressRelay | None = None
    wake = threading.Event()
    if not dry_run:
        release_claims(services)
    if publish_catalog and not dry_run:
        try:
            publish_catalog_document(services.management, services.git_metadata())
        except (SystemExit, Exception) as error:
            services.emit(f"! catalog publish failed: {error}")
    try:
        if services.hub is not None:
            listener = HubListener(services, wake).start()
            if services.progress_feed is not None:
                relay = ProgressRelay(services, listener).start()
        while True:
            if _draining(services):
                services.emit("draining: no new work claimed")
                break
            if listener is not None:
                wake.clear()
            did_something = work_once(services, dry_run=dry_run,
                                      listener=listener, relay=relay)
            if once:
                return
            if not did_something:
                _idle(services, wake if listener is not None else None, interval)
    except KeyboardInterrupt:
        services.emit("work stopped")
    finally:
        if relay is not None:
            relay.stop()
        if listener is not None:
            listener.stop()
        if services.drained is not None and _draining(services):
            # The deploy waits on this acknowledgement rather than on a clock.
            try:
                services.drained()
            except (SystemExit, Exception) as error:
                services.emit(f"! drain acknowledgement failed: {error}")
