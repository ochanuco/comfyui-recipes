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

from ..domain.yukari.recipe import TOE_GUARD
from .finalize import FinalizeServices, finalize
from .generate import GenerateServices, generate, request_file_path

CLAIM_PATH = "/api/v1/requests/claim"
DRY_RUN_PATH = "/api/v1/requests?status=queued&limit=1"

_KNOWN_FINALIZE_OPTIONS = frozenset({
    "denoise", "repin", "recolor", "keep_legwear", "route", "finalizer",
    "size", "handdrawn", "skin", "toe_guard", "keep_scene",
})


class Management(Protocol):
    def request(self, method: str, path: str, payload: dict | None = None,
                multipart: tuple[dict, str, str, bytes, str] | None = None) -> dict | None: ...


class Connection(Protocol):
    """What HubListener/ProgressRelay need from an open socket -- already open."""

    def send(self, message: dict) -> None: ...
    def recv(self, timeout: float) -> dict | None: ...
    def close(self) -> None: ...


class Heartbeat:
    """PATCHes {"status": "running"} every `interval` seconds until stopped."""

    def __init__(self, management: Management, row_id: str, worker_id: str, *,
                 interval: float = 30, emit: Callable[[str], None] = print) -> None:
        self.management = management
        self.row_id = row_id
        self.worker_id = worker_id
        self.interval = interval
        self.emit = emit
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self.management.request(
                    "PATCH", f"/api/v1/requests/{self.row_id}",
                    {"status": "running", "worker_id": self.worker_id})
            except (SystemExit, Exception) as error:
                self.emit(f"heartbeat failed for {self.row_id}: {error}")

    def start(self) -> "Heartbeat":
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()

    def __enter__(self) -> "Heartbeat":
        return self.start()

    def __exit__(self, *exc_info: object) -> None:
        self.stop()


@dataclass(frozen=True)
class WorkServices:
    management: Management
    generate_services: GenerateServices
    finalize_services: FinalizeServices
    git_metadata: Callable[[], dict]
    worker_id: str
    generate: Callable[..., dict | None] = generate
    finalize: Callable[..., dict] = finalize
    emit: Callable[[str], None] = print
    sleep: Callable[[float], None] = time.sleep
    heartbeat_interval: float = 30
    kinds: tuple[str, ...] = ("generate", "finalize")
    heartbeat: Callable[..., Heartbeat] = Heartbeat
    hub: Callable[[], Connection] | None = None
    progress_feed: Callable[[], Connection] | None = None
    backoff_max: float = 60
    ping_interval: float = 30
    clock: Callable[[], float] = time.monotonic


class HubListener:
    """Keeps one WorkerHub socket open: hello, ping, wake on `queued`.

    Reconnects with exponential backoff (1s doubling to `backoff_max`); the
    backoff resets once the hub has sent a frame, so a hub that accepts the
    Upgrade and drops the socket at once does not get hammered. send_progress()
    is a silent no-op while no socket is open.
    """

    def __init__(self, services: WorkServices, wake: threading.Event) -> None:
        self.services = services
        self.wake = wake
        self._stop = threading.Event()
        self._connection: Connection | None = None
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def start(self) -> "HubListener":
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            connection, self._connection = self._connection, None
        if connection is not None:
            try:
                connection.close()
            except (SystemExit, Exception):
                pass
        if self._thread is not None:
            self._thread.join()

    def send_progress(self, request_id: str, phase: str, **fields: object) -> None:
        with self._lock:
            connection = self._connection
        if connection is None:
            return
        message = {"type": "progress", "request_id": request_id, "phase": phase}
        message.update({key: value for key, value in fields.items() if value is not None})
        try:
            connection.send(message)
        except (SystemExit, Exception):
            pass

    def _run(self) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            connection: Connection | None = None
            try:
                connection = self.services.hub()
                with self._lock:
                    self._connection = connection
                connection.send({
                    "type": "hello", "worker_id": self.services.worker_id,
                    "kinds": list(self.services.kinds),
                })
                self.wake.set()
                next_ping = self.services.clock() + self.services.ping_interval
                while not self._stop.is_set():
                    timeout = max(0.0, next_ping - self.services.clock())
                    message = connection.recv(timeout)
                    if message is None:
                        connection.send({"type": "ping"})
                        next_ping = self.services.clock() + self.services.ping_interval
                        continue
                    backoff = 1.0
                    if message.get("type") == "queued":
                        self.wake.set()
            except (SystemExit, Exception) as error:
                self.services.emit(f"hub connection lost: {error}")
            finally:
                with self._lock:
                    if self._connection is connection:
                        self._connection = None
                if connection is not None:
                    try:
                        connection.close()
                    except (SystemExit, Exception):
                        pass
            if self._stop.is_set():
                return
            self.services.sleep(backoff)
            backoff = min(backoff * 2, self.services.backoff_max)


class ProgressRelay:
    """Relays ComfyUI's own /ws `progress` events to the hub for `current`.

    `current` is the request_id being executed; events outside that window
    are dropped. Never raises into the main loop.
    """

    def __init__(self, services: WorkServices, listener: HubListener) -> None:
        self.services = services
        self.listener = listener
        self.current: str | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> "ProgressRelay":
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()

    def _run(self) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            feed: Connection | None = None
            try:
                feed = self.services.progress_feed()
                backoff = 1.0
                while not self._stop.is_set():
                    event = feed.recv(self.services.ping_interval)
                    if event is None:
                        continue
                    if self.current is not None:
                        self.listener.send_progress(
                            self.current, "sampling",
                            step=event.get("step"), total=event.get("total"))
            except (SystemExit, Exception) as error:
                self.services.emit(f"progress feed lost: {error}")
            finally:
                if feed is not None:
                    try:
                        feed.close()
                    except (SystemExit, Exception):
                        pass
            if self._stop.is_set():
                return
            self.services.sleep(backoff)
            backoff = min(backoff * 2, self.services.backoff_max)


def finalize_arguments(options: Mapping) -> dict:
    """Validate a finalize request's `options` and map it to finalize() kwargs.

    Every key in the return value is a finalize() kwarg. Missing keys mean
    false/null; unknown keys or a wrong type raise ValueError naming the
    offending key.
    """
    if not isinstance(options, Mapping):
        raise ValueError(
            f"finalize options must be an object, got {type(options).__name__}")
    unknown = sorted(set(options) - _KNOWN_FINALIZE_OPTIONS)
    if unknown:
        raise ValueError(f"unknown finalize options keys: {unknown}")

    def boolean(key: str) -> bool:
        value = options.get(key, False)
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be a boolean, got {type(value).__name__}")
        return value

    def number(key: str) -> float | int | None:
        value = options.get(key)
        if value is None or (isinstance(value, (int, float))
                             and not isinstance(value, bool)):
            return value
        raise ValueError(f"{key} must be null or a number, got {type(value).__name__}")

    denoise = number("denoise")

    keep_legwear = options.get("keep_legwear")
    if keep_legwear is True:
        keep_legwear = 0.62
    elif keep_legwear is not None and not (
            isinstance(keep_legwear, (int, float)) and not isinstance(keep_legwear, bool)):
        raise ValueError(
            "keep_legwear must be null, true or a number, got "
            f"{type(keep_legwear).__name__}")

    route = options.get("route")
    if route is None:
        latent_route = None
    elif route == "latent":
        latent_route = True
    elif route == "pixel":
        latent_route = False
    else:
        raise ValueError(f"route must be null, 'latent' or 'pixel', got {route!r}")

    finalizer = options.get("finalizer")
    if finalizer is not None and not isinstance(finalizer, str):
        raise ValueError(f"finalizer must be null or a string, got {type(finalizer).__name__}")

    size = options.get("size")
    if size is not None and not (isinstance(size, int) and not isinstance(size, bool)):
        raise ValueError(f"size must be null or an integer, got {type(size).__name__}")

    toe_guard = options.get("toe_guard")
    if toe_guard is True:
        toe_guard = TOE_GUARD
    elif toe_guard is not None and not (
            isinstance(toe_guard, (int, float)) and not isinstance(toe_guard, bool)):
        raise ValueError(
            "toe_guard must be null, true or a number, got "
            f"{type(toe_guard).__name__}")

    return {
        "denoise": float(denoise) if denoise is not None else None,
        "handdrawn": boolean("handdrawn"),
        "apply_repin": boolean("repin"),
        "apply_skin": boolean("skin"),
        "apply_recolor": boolean("recolor"),
        "keep_legwear": float(keep_legwear) if keep_legwear is not None else None,
        "toe_guard": float(toe_guard) if toe_guard is not None else None,
        "size": size,
        "latent_route": latent_route,
        "finalizer": finalizer,
        "keep_scene": boolean("keep_scene"),
    }


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
    try:
        arguments = finalize_arguments(payload.get("options") or {})
    except ValueError as error:
        raise SystemExit(str(error)) from error
    return services.finalize(generation_id, services.finalize_services,
                             key_prefix=f"request:{row['id']}", **arguments)


def execute(services: WorkServices, row: Mapping) -> dict:
    ref = row.get("recipe_ref")
    if ref != services.git_metadata().get("branch"):
        raise SystemExit(f"recipe_ref not served: {ref}")
    kind = row.get("kind")
    if kind == "generate":
        return _execute_generate(services, row)
    if kind == "finalize":
        return _execute_finalize(services, row)
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


def work(services: WorkServices, *, interval: float = 30, once: bool = False,
         dry_run: bool = False) -> None:
    listener: HubListener | None = None
    relay: ProgressRelay | None = None
    wake = threading.Event()
    try:
        if services.hub is not None:
            listener = HubListener(services, wake).start()
            if services.progress_feed is not None:
                relay = ProgressRelay(services, listener).start()
        while True:
            if listener is not None:
                wake.clear()
            did_something = work_once(services, dry_run=dry_run,
                                      listener=listener, relay=relay)
            if once:
                return
            if not did_something:
                if listener is not None:
                    wake.wait(interval)
                else:
                    services.sleep(interval)
    except KeyboardInterrupt:
        services.emit("work stopped")
    finally:
        if relay is not None:
            relay.stop()
        if listener is not None:
            listener.stop()
