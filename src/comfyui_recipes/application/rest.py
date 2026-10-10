"""When an idle worker puts its host to sleep, and how it holds the host awake."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass


@dataclass(frozen=True)
class RestServices:
    after: float
    input_idle: Callable[[], float]
    comfyui_busy: Callable[[], bool]
    announce: Callable[[str], None]
    suspend: Callable[[], None]
    keep_awake: Callable[[], AbstractContextManager]

    def reason(self) -> str:
        return f"idle {round(self.after / 60)}m"


def rest_due(rest: RestServices, idle_for: float,
             emit: Callable[[str], None]) -> bool:
    """Both the queue and the console have been idle for `rest.after`.

    `idle_for` counts from the last finished job, so empty polls never
    extend it. A check that cannot be read keeps the host awake.
    """
    if idle_for < rest.after:
        return False
    try:
        if rest.input_idle() < rest.after:
            return False
        if rest.comfyui_busy():
            return False
    except (SystemExit, Exception) as error:
        emit(f"! idle check failed: {error}")
        return False
    return True
