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

from ..domain.repair.controlnet import CONTROL_MODELS, DEFAULT_CONTROL_STRENGTH
from ..domain.repair.loras import DEFAULT_PART_LORA_WEIGHT
from ..domain.repair.models import MODELS
from ..domain.yukari.delivery_style import STROKE_LIGHTS
from ..domain.yukari.dials import DIALS as _YUKARI_DIALS
from ..domain.yukari.recipe import TOE_GUARD
from ..domain.yukari_anima.dials import DIALS as _ANIMA_DIALS
from ..domain.yukari_sketch.dials import DIALS as _SKETCH_DIALS
from ..infrastructure.imaging.backdrops import PATTERNS, is_backdrop
from .catalog import publish_catalog as publish_catalog_document
from .finalize import FinalizeServices, finalize
from .generate import GenerateServices, generate, request_file_path
from .masked_redraw import MaskedRedrawServices, masked_redraw
from .repair import RepairServices, repair

CLAIM_PATH = "/api/v1/requests/claim"
DRY_RUN_PATH = "/api/v1/requests?status=queued&limit=1"

_KNOWN_FINALIZE_OPTIONS = frozenset({
    "denoise", "repin", "recolor", "keep_legwear", "route", "finalizer",
    "size", "handdrawn", "skin", "toe_guard", "keep_scene", "transparent",
    "backdrop", "upscale", "lora_strength", "deliver_size", "stroke_light",
    "repair", "repair_regions", "repair_denoise", "repair_pad", "repair_size",
    "repair_lora",
})

_KNOWN_REPAIR_OPTIONS = frozenset({
    "parts", "regions", "denoise", "seeds", "size", "pad", "lora", "model",
    "control", "control_strength",
})

_KNOWN_MASKED_REDRAW_OPTIONS = frozenset({
    "regions", "prompt_patch", "denoise", "mask_padding", "mask_feather",
    "size", "seeds",
})

_REPAIR_PARTS = frozenset({"hands", "feet"})

_MASKED_REDRAW_PROMPT_PATCH_MAX_LENGTH = 4096
_MASKED_REDRAW_SEEDS_MAX = 16

# `generation.recipe` -> its published `dials` block (see domain/*/dials.py).
_RECIPE_DIALS = {
    "yukari": _YUKARI_DIALS,
    "yukari-anima": _ANIMA_DIALS,
    "yukari-sketch": _SKETCH_DIALS,
}

# The finalize/repair option keys a recipe may define dial words for -- kept
# in sync by hand with the resolve_dial() call sites in finalize_arguments()
# and repair_arguments(); a key resolved there and missing here is reported
# unresolved in resolved_options. Public: interfaces/cli.py reads them too,
# to resolve the same keys' words from the args it already parsed.
FINALIZE_DIAL_KEYS = ("denoise", "keep_legwear", "toe_guard", "lora_strength",
                     "repair_denoise", "repair_lora")
REPAIR_DIAL_KEYS = ("denoise", "lora")
_MASKED_REDRAW_DIAL_KEYS = ("denoise",)


def dials_scope(recipe: str, scope: str) -> Mapping[str, Mapping[str, float]]:
    return _RECIPE_DIALS.get(recipe, {}).get(scope, {})


def fetch_source(management: Management, generation_id: str) -> tuple[dict, dict, str]:
    """The requested generation's context, its batch, and that batch's recipe."""
    context = management.request(
        "GET", f"/api/v1/generations/{generation_id}/context")
    batch = management.request(
        "GET", f"/api/v1/batches/{context['batch']['id']}")
    return context, batch, batch.get("recipe") or "yukari"


def resolve_dial(key: str, value: object,
                  dials: Mapping[str, Mapping[str, float]]) -> object:
    """A string option value is looked up in `dials[key]`; every other value
    (a number, `true`, `null`) passes through for the option's own checks.
    """
    if not isinstance(value, str):
        return value
    words = dials.get(key) or {}
    if value not in words:
        raise ValueError(f"unknown {key} word: {value!r}")
    return words[value]


def _resolved_options(options: Mapping, arguments: Mapping,
                      dial_keys: tuple[str, ...]) -> dict:
    """The request's own options, with each dial-eligible key's value
    replaced by what `finalize_arguments()`/`repair_arguments()`/
    `masked_redraw_arguments()` actually resolved it to in `arguments` --
    the single source of truth for what the request ran with, rather than a
    second independent word/`true` resolution that could drift from it.
    """
    return {key: (arguments[key] if key in dial_keys else value)
           for key, value in options.items()}


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


def _denoise_argument(value: object, *, key: str = "denoise", max_value: float = 1) -> float:
    if not (isinstance(value, (int, float)) and not isinstance(value, bool)):
        raise ValueError(f"{key} must be a number, got {type(value).__name__}")
    if not (0 < value <= max_value):
        raise ValueError(f"{key} must be > 0 and <= {max_value}, got {value!r}")
    return float(value)


def _pixel_argument(value: object, *, key: str, max_value: float) -> float:
    if not (isinstance(value, (int, float)) and not isinstance(value, bool)):
        raise ValueError(f"{key} must be a number, got {type(value).__name__}")
    if not (0 <= value <= max_value):
        raise ValueError(f"{key} must be between 0 and {max_value}, got {value!r}")
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


# Shared by `finalize_arguments`'s `repair_lora` and `repair_arguments`'s own
# `lora` -- both select the part-LoRA weight the reroll's `LoraLoader` chain
# runs at.
def _part_lora_argument(value: object, *, key: str = "lora") -> float | None:
    if value is True:
        return DEFAULT_PART_LORA_WEIGHT
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not (0 < value <= 2):
            raise ValueError(f"{key} must be > 0 and <= 2, got {value!r}")
        return float(value)
    raise ValueError(
        f"{key} must be null, true or a number, got {type(value).__name__}")


def _model_argument(value: object, *, key: str = "model") -> str | None:
    if value is None:
        return None
    if value not in MODELS:
        valid = ", ".join(repr(word) for word in sorted(MODELS))
        raise ValueError(f"{key} must be null or one of {valid}, got {value!r}")
    return value


def _control_argument(value: object, *, key: str = "control") -> str | None:
    if value is None:
        return None
    if value not in CONTROL_MODELS:
        valid = ", ".join(repr(word) for word in sorted(CONTROL_MODELS))
        raise ValueError(f"{key} must be null or one of {valid}, got {value!r}")
    return value


def _control_strength_argument(value: object, *,
                               key: str = "control_strength") -> float:
    if not (isinstance(value, (int, float)) and not isinstance(value, bool)):
        raise ValueError(f"{key} must be a number, got {type(value).__name__}")
    if not (0 < value <= 2):
        raise ValueError(f"{key} must be > 0 and <= 2, got {value!r}")
    return float(value)


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


def finalize_arguments(options: Mapping,
                       dials: Mapping[str, Mapping[str, float]] | None = None) -> dict:
    """Validate a finalize request's `options` and map it to finalize() kwargs.

    Every key in the return value is a finalize() kwarg. Missing keys mean
    false/null; unknown keys or a wrong type raise ValueError naming the
    offending key. `dials` is the source recipe's `dials.finalize`
    vocabulary (option key -> word -> number); a dial-eligible key given a
    word absent there raises the same way.
    """
    if not isinstance(options, Mapping):
        raise ValueError(
            f"finalize options must be an object, got {type(options).__name__}")
    unknown = sorted(set(options) - _KNOWN_FINALIZE_OPTIONS)
    if unknown:
        raise ValueError(f"unknown finalize options keys: {unknown}")
    dials = dials or {}

    def boolean(key: str) -> bool:
        value = options.get(key, False)
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be a boolean, got {type(value).__name__}")
        return value

    def number(key: str) -> float | int | None:
        value = resolve_dial(key, options.get(key), dials)
        if value is None or (isinstance(value, (int, float))
                             and not isinstance(value, bool)):
            return value
        raise ValueError(f"{key} must be null or a number, got {type(value).__name__}")

    denoise = number("denoise")

    keep_legwear = resolve_dial("keep_legwear", options.get("keep_legwear"), dials)
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

    toe_guard = resolve_dial("toe_guard", options.get("toe_guard"), dials)
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

    lora_strength = resolve_dial("lora_strength", options.get("lora_strength"), dials)
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
        resolve_dial("repair_denoise", options.get("repair_denoise", 0.6), dials),
        key="repair_denoise")
    repair_pad = _pad_argument(options.get("repair_pad", 1.0), key="repair_pad")
    repair_size = _crop_size_argument(
        options.get("repair_size", 1024), key="repair_size")
    repair_lora = _part_lora_argument(
        resolve_dial("repair_lora", options.get("repair_lora"), dials),
        key="repair_lora")

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
        "repair_lora": repair_lora,
    }


def repair_arguments(options: Mapping,
                     dials: Mapping[str, Mapping[str, float]] | None = None) -> dict:
    """Validate a repair request's `options` and map it to repair() kwargs.

    Every key in the return value is a repair() kwarg; unknown keys or a
    wrong type raise ValueError naming the offending key. `dials` is the
    source recipe's `dials.repair` vocabulary (option key -> word -> number).
    """
    if not isinstance(options, Mapping):
        raise ValueError(
            f"repair options must be an object, got {type(options).__name__}")
    unknown = sorted(set(options) - _KNOWN_REPAIR_OPTIONS)
    if unknown:
        raise ValueError(f"unknown repair options keys: {unknown}")
    dials = dials or {}

    parts = _parts_argument(options.get("parts", ["hands", "feet"]))
    parsed_regions = _regions_argument(options.get("regions", []))

    if not parts and not parsed_regions:
        raise ValueError("repair needs at least one of parts or regions")

    denoise = _denoise_argument(
        resolve_dial("denoise", options.get("denoise", 0.6), dials))

    seeds = options.get("seeds", [1, 2, 3, 4])
    if (not isinstance(seeds, list) or not seeds
            or any(not isinstance(seed, int) or isinstance(seed, bool)
                   for seed in seeds)):
        raise ValueError(f"seeds must be a non-empty array of integers, got {seeds!r}")

    size = _crop_size_argument(options.get("size", 1024))
    pad = _pad_argument(options.get("pad", 1.0))
    lora = _part_lora_argument(resolve_dial("lora", options.get("lora"), dials))
    model = _model_argument(options.get("model"))
    control = _control_argument(options.get("control"))
    control_strength = _control_strength_argument(
        options.get("control_strength", DEFAULT_CONTROL_STRENGTH))

    return {
        "parts": parts, "regions": parsed_regions, "denoise": denoise,
        "seeds": seeds, "size": size, "pad": pad, "lora": lora, "model": model,
        "control": control, "control_strength": control_strength,
    }


def masked_redraw_arguments(options: Mapping,
                            dials: Mapping[str, Mapping[str, float]] | None = None) -> dict:
    """Validate a masked_redraw request's `options` and map it to
    masked_redraw() kwargs.

    Every key in the return value is a masked_redraw() kwarg; unknown keys or
    a wrong type raise ValueError naming the offending key. `dials` is the
    source recipe's `dials.repair` vocabulary -- masked_redraw's own
    `denoise` shares repair's, rather than defining its own.
    """
    if not isinstance(options, Mapping):
        raise ValueError(
            f"masked_redraw options must be an object, got {type(options).__name__}")
    unknown = sorted(set(options) - _KNOWN_MASKED_REDRAW_OPTIONS)
    if unknown:
        raise ValueError(f"unknown masked_redraw options keys: {unknown}")
    dials = dials or {}

    regions = _regions_argument(options.get("regions", []))
    if not regions:
        raise ValueError("masked_redraw needs at least one region")

    prompt_patch = options.get("prompt_patch")
    if not isinstance(prompt_patch, str) or not prompt_patch:
        raise ValueError(
            f"prompt_patch must be a non-empty string, got {prompt_patch!r}")
    if len(prompt_patch) > _MASKED_REDRAW_PROMPT_PATCH_MAX_LENGTH:
        raise ValueError(
            "prompt_patch must be at most "
            f"{_MASKED_REDRAW_PROMPT_PATCH_MAX_LENGTH} characters, got {len(prompt_patch)}")

    denoise = _denoise_argument(
        resolve_dial("denoise", options.get("denoise", 0.45), dials), max_value=0.75)
    mask_padding = _pixel_argument(
        options.get("mask_padding", 0), key="mask_padding", max_value=512)
    mask_feather = _pixel_argument(
        options.get("mask_feather", 32), key="mask_feather", max_value=256)
    size = _crop_size_argument(options.get("size", 1024))

    seeds = options.get("seeds", [1, 2, 3, 4])
    if (not isinstance(seeds, list) or not seeds
            or any(not isinstance(seed, int) or isinstance(seed, bool)
                   for seed in seeds)):
        raise ValueError(f"seeds must be a non-empty array of integers, got {seeds!r}")
    if len(seeds) > _MASKED_REDRAW_SEEDS_MAX:
        raise ValueError(
            f"seeds must have at most {_MASKED_REDRAW_SEEDS_MAX} entries, got {len(seeds)}")

    return {
        "regions": regions, "prompt_patch": prompt_patch, "denoise": denoise,
        "mask_padding": mask_padding, "mask_feather": mask_feather, "size": size,
        "seeds": seeds,
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
