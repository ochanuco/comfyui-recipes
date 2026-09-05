"""Every pose: its own gesture block plus the costume it defaults to."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Pose:
    action: str
    costume: str = "default"


POSES = {
    "cinema": Pose(
        action=("(walking:1.2), (holding popcorn:1.3), popcorn, (holding "
                "cup:1.25), disposable cup, (drinking straw:1.3), (full "
                "body:1.3), ")),
    "stand": Pose(
        action=("(standing:1.5), (own hands together:1.3), (hands "
                "up:1.2), (arched back:1.15), (from front:1.3), (full "
                "body:1.45), (wide shot:1.3), ")),
}
