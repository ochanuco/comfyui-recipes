"""Every pose: its own gesture block plus the costume it defaults to."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Pose:
    action: str
    costume: str = "default"
    face: str | None = None
    canvas: tuple[int, int] | None = None


POSES = {
    "cinema": Pose(
        action=("(walking:1.2), (holding popcorn:1.3), popcorn, (holding "
                "cup:1.25), disposable cup, (drinking straw:1.3), (full "
                "body:1.3), ")),
    "stand": Pose(
        action=("(standing:1.5), (own hands together:1.3), (hands "
                "up:1.2), (arched back:1.15), (from front:1.3), (full "
                "body:1.45), (wide shot:1.3), ")),
    "date": Pose(
        action=("(walking:1.2), (holding popcorn:1.3), popcorn, (holding "
                "cup:1.25), disposable cup, (drinking straw:1.3), (full "
                "body:1.3), (sneakers:1.3), (white sneakers:1.2), "),
        costume="outing",
        face=("(tareme:1.2), (jitome:1.25), (half-closed eyes:1.15), "
              "(smirk:1.2), (smug:1.15), closed mouth, (blush:1.1), "
              "(head tilt:1.1), looking at viewer, ")),
    "cafe": Pose(
        action=("(sitting:1.3), (table:1.2), (head rest:1.35), (hand on own "
                "cheek:1.2), (elbow on table:1.15), (coffee cup:1.15), cup, "
                "saucer, (from above:1.1), (upper body:1.25), "),
        costume="outing",
        face=("(tareme:1.2), (jitome:1.2), (upturned eyes:1.3), (looking "
              "up:1.15), looking at viewer, (light smile:1.1), (parted "
              "lips:1.2), (blush:1.15), (head tilt:1.1), "),
        canvas=(1024, 1280)),
    "home": Pose(
        action=("(sitting:1.3), (bean bag chair:1.5), (sinking:1.2), (leaning "
                "back:1.25), (from above:1.2), (slouching:1.25), (arms at "
                "sides:1.15), (limp:1.1), (shopping bag:1.25), (paper "
                "bag:1.15), (upper body:1.25), "),
        costume="outing",
        face=("(tareme:1.2), (jitome:1.15), (half-closed eyes:1.25), (head "
              "back:1.3), (looking up:1.15), (open mouth:1.25), "
              "(exhausted:1.25), (sigh:1.15), (blush:1.1), "),
        canvas=(1024, 1280)),
    "bath": Pose(
        action=("(sitting:1.3), (on floor:1.3), (knee up:1.35), (outstretched "
                "leg:1.35), (leaning forward:1.2), (hands on own leg:1.4), "
                "(both hands:1.2), (holding own leg:1.2), (massage:1.3), "
                "(from above:1.1), (cowboy shot:1.25), "),
        costume="bath",
        face=("(tareme:1.2), (jitome:1.2), (half-closed eyes:1.2), (looking "
              "down:1.25), closed mouth, (blush:1.3), (flushed:1.2), "),
        canvas=(1024, 1280)),
}
