"""Starts the worker's claim loop as a thread inside ComfyUI's own process.

Off unless ``COMFYUI_RECIPES_WORKER`` is set: importing a custom node pack
must never start background work on its own, and this is the switch that
keeps a plain ComfyUI install unaffected.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable

_lock = threading.Lock()
_thread: threading.Thread | None = None


def _enabled() -> bool:
    return os.environ.get(
        "COMFYUI_RECIPES_WORKER", "").strip().lower() in {"1", "true", "yes"}


def _worker_id() -> str | None:
    return os.environ.get("COMFYUI_RECIPES_WORKER_ID") or None


def _run_guarded(run: Callable[..., None], worker_id: str | None) -> None:
    try:
        run(worker_id=worker_id)
    except Exception as error:
        print(f"[yukari_worker] worker thread failed: {error!r}")


def start(run: Callable[..., None] | None = None) -> None:
    """Start the claim-loop thread once, if enabled. Never raises."""
    try:
        if not _enabled():
            return
        if run is None:
            # Imported here, not at module scope: a disabled pack must cost
            # ComfyUI nothing but this file, and an import that fails would
            # otherwise report on every start of an install not using it.
            from comfyui_recipes.interfaces.agent import run as run
        global _thread
        with _lock:
            if _thread is not None:
                return
            thread = threading.Thread(
                target=_run_guarded, args=(run, _worker_id()),
                name="yukari-worker", daemon=True)
            thread.start()
            _thread = thread
    except Exception as error:
        print(f"[yukari_worker] failed to start worker thread: {error!r}")
