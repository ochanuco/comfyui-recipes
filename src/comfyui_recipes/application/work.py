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

from ..domain.yukari.delivery_style import STROKE_LIGHTS
from ..domain.yukari.recipe import TOE_GUARD
from ..infrastructure.imaging.backdrops import PATTERNS, is_backdrop
from .catalog import publish_catalog as publish_catalog_document
from .finalize import FinalizeServices, finalize
from .generate import GenerateServices, generate, request_file_path
from .repair import RepairServices, repair

CLAIM_PATH = "/api/v1/requests/claim"
DRY_RUN_PATH = "/api/v1/requests?status=queued&limit=1"

_KNOWN_FINALIZE_OPTIONS = frozenset({
    "denoise", "repin", "recolor", "keep_legwear", "route", "finalizer",
    "size", "handdrawn", "skin", "toe_guard", "keep_scene", "transparent",
    "backdrop", "upscale", "lora_strength", "deliver_size", "stroke_light",
    "repair", "repair_regions", "repair_denoise", "repair_pad", "repair_size",
})

_KNOWN_REPAIR_OPTIONS = frozenset({
    "parts", "regions", "denoise", "seeds", "size", "pad",
})

_REPAIR_PARTS = frozenset({"hands", "feet"})


# Shared by `finalize_arguments`' `repair`/`repair_*` options and
# `repair_arguments`' own -- both validate the same reroll geometry, just
# under different option names and defaults.
def _parts_argument(value: object, *, key: str = "parts") -> list[str]:
    if (not isinstance(value, list)
            or any(not isinstance(part, str) for part in value)):
        raise ValueError(f"{key} must be a list of strings, got {value!r}")
    invalid = sorted(set(value) - _REPAIR_PARTS)
    if invalid:
        raise ValueError(f"unknown {key}: {invalid}")
    return value


def _regions_argument(value: object, *, key: str = "regions") -> list[list[float]]:
    if not isinstance(value, list):
        raise ValueError(f"{key} must be an array, got {type(value).__name__}")
    parsed = []
    for region in value:
        if (not isinstance(region, list) or len(region) != 4
                or any(not isinstance(v, (int, float)) or isinstance(v, bool)
                       for v in region)):
            raise ValueError(
                f"each region must be [x0, y0, x1, y1] numbers, got {region!r}")
        if any(not (0 <= v <= 1) for v in region):
            raise ValueError(f"region values must be within 0..1, got {region!r}")
        parsed.append([float(v) for v in region])
    return parsed


def _denoise_argument(value: object, *, key: str = "denoise") -> float:
    if not (isinstance(value, (int, float)) and not isinstance(value, bool)):
        raise ValueError(f"{key} must be a number, got {type(value).__name__}")
    if not (0 < value <= 1):
        raise ValueError(f"{key} must be > 0 and <= 1, got {value!r}")
    return float(value)


def _pad_argument(value: object, *, key: str = "pad") -> float:
    if not (isinstance(value, (int, float)) and not isinstance(value, bool)):
        raise ValueError(f"{key} must be a number, got {type(value).__name__}")
    if not (0.5 <= value <= 3):
        raise ValueError(f"{key} must be between 0.5 and 3, got {value!r}")
    return float(value)


def _crop_size_argument(value: object, *, key: str = "size") -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer, got {type(value).__name__}")
    if value < 256 or value % 8 != 0:
        raise ValueError(f"{key} must be a multiple of 8, at least 256, got {value!r}")
    return value


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
    repair_services: RepairServices
    git_metadata: Callable[[], dict]
    worker_id: str
    generate: Callable[..., dict | None] = generate
    finalize: Callable[..., dict] = finalize
    repair: Callable[..., dict] = repair
    emit: Callable[[str], None] = print
    sleep: Callable[[float], None] = time.sleep
    heartbeat_interval: float = 30
    kinds: tuple[str, ...] = ("generate", "finalize", "repair")
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

    deliver_size = options.get("deliver_size")
    if deliver_size is not None and not (
            isinstance(deliver_size, int) and not isinstance(deliver_size, bool)):
        raise ValueError(
            f"deliver_size must be null or an integer, got {type(deliver_size).__name__}")
    if deliver_size is not None and deliver_size < 1:
        raise ValueError(f"deliver_size must be at least 1, got {deliver_size!r}")

    toe_guard = options.get("toe_guard")
    if toe_guard is True:
        toe_guard = TOE_GUARD
    elif toe_guard is not None and not (
            isinstance(toe_guard, (int, float)) and not isinstance(toe_guard, bool)):
        raise ValueError(
            "toe_guard must be null, true or a number, got "
            f"{type(toe_guard).__name__}")

    transparent = options.get("transparent")
    if transparent is not None and not isinstance(transparent, bool):
        raise ValueError(
            f"transparent must be null or a boolean, got {type(transparent).__name__}")

    backdrop = options.get("backdrop")
    if backdrop is not None:
        if not isinstance(backdrop, str):
            raise ValueError(
                f"backdrop must be null or a string, got {type(backdrop).__name__}")
        if not is_backdrop(backdrop):
            names = ", ".join(repr(key) for key in sorted(PATTERNS))
            raise ValueError(
                f"backdrop must be null, a #RRGGBB colour or one of {names}, got {backdrop!r}")

    upscale = options.get("upscale")
    if upscale is not None and upscale not in (
            "bicubic", "nearest-exact", "bilinear", "lanczos"):
        raise ValueError(
            "upscale must be null, 'bicubic', 'nearest-exact', 'bilinear' or "
            f"'lanczos', got {upscale!r}")

    lora_strength = options.get("lora_strength")
    if lora_strength is not None and not (
            isinstance(lora_strength, (int, float)) and not isinstance(lora_strength, bool)):
        raise ValueError(
            f"lora_strength must be null or a number, got {type(lora_strength).__name__}")
    if lora_strength is not None and not (0 <= lora_strength <= 2):
        raise ValueError(f"lora_strength must be between 0 and 2, got {lora_strength!r}")

    stroke_light = options.get("stroke_light")
    if stroke_light is not None and stroke_light not in STROKE_LIGHTS:
        valid = ", ".join(repr(key) for key in sorted(STROKE_LIGHTS))
        raise ValueError(f"stroke_light must be null or one of {valid}, got {stroke_light!r}")

    repair_raw = options.get("repair")
    repair = (None if repair_raw is None
             else _parts_argument(repair_raw, key="repair"))
    repair_regions = _regions_argument(
        options.get("repair_regions", []), key="repair_regions")
    repair_denoise = _denoise_argument(
        options.get("repair_denoise", 0.6), key="repair_denoise")
    repair_pad = _pad_argument(options.get("repair_pad", 1.0), key="repair_pad")
    repair_size = _crop_size_argument(
        options.get("repair_size", 1024), key="repair_size")

    return {
        "denoise": float(denoise) if denoise is not None else None,
        "handdrawn": boolean("handdrawn"),
        "apply_repin": boolean("repin"),
        "apply_skin": boolean("skin"),
        "apply_recolor": boolean("recolor"),
        "keep_legwear": float(keep_legwear) if keep_legwear is not None else None,
        "toe_guard": float(toe_guard) if toe_guard is not None else None,
        "size": size,
        "deliver_size": deliver_size,
        "latent_route": latent_route,
        "finalizer": finalizer,
        "keep_scene": boolean("keep_scene"),
        "transparent": transparent,
        "backdrop": backdrop,
        "upscale": upscale,
        "lora_strength": float(lora_strength) if lora_strength is not None else None,
        "stroke_light": stroke_light,
        "repair": repair,
        "repair_regions": repair_regions,
        "repair_denoise": repair_denoise,
        "repair_pad": repair_pad,
        "repair_size": repair_size,
    }


def repair_arguments(options: Mapping) -> dict:
    """Validate a repair request's `options` and map it to repair() kwargs.

    Every key in the return value is a repair() kwarg; unknown keys or a
    wrong type raise ValueError naming the offending key.
    """
    if not isinstance(options, Mapping):
        raise ValueError(
            f"repair options must be an object, got {type(options).__name__}")
    unknown = sorted(set(options) - _KNOWN_REPAIR_OPTIONS)
    if unknown:
        raise ValueError(f"unknown repair options keys: {unknown}")

    parts = _parts_argument(options.get("parts", ["hands", "feet"]))
    parsed_regions = _regions_argument(options.get("regions", []))

    if not parts and not parsed_regions:
        raise ValueError("repair needs at least one of parts or regions")

    denoise = _denoise_argument(options.get("denoise", 0.6))

    seeds = options.get("seeds", [1, 2, 3, 4])
    if (not isinstance(seeds, list) or not seeds
            or any(not isinstance(seed, int) or isinstance(seed, bool)
                   for seed in seeds)):
        raise ValueError(f"seeds must be a non-empty array of integers, got {seeds!r}")

    size = _crop_size_argument(options.get("size", 1024))
    pad = _pad_argument(options.get("pad", 1.0))

    return {
        "parts": parts, "regions": parsed_regions, "denoise": denoise,
        "seeds": seeds, "size": size, "pad": pad,
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


def _execute_repair(services: WorkServices, row: Mapping) -> dict:
    payload = row.get("payload") or {}
    generation_id = payload.get("generation_id")
    if not generation_id:
        raise SystemExit("repair payload.generation_id is required")
    try:
        arguments = repair_arguments(payload.get("options") or {})
    except ValueError as error:
        raise SystemExit(str(error)) from error
    return services.repair(generation_id, services.repair_services,
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
    if kind == "repair":
        return _execute_repair(services, row)
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
         dry_run: bool = False, publish_catalog: bool = True) -> None:
    listener: HubListener | None = None
    relay: ProgressRelay | None = None
    wake = threading.Event()
    if publish_catalog:
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
