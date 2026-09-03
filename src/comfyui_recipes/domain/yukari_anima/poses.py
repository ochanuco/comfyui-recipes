"""Every pose: its own tag blocks plus the expression/costume it defaults to."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Pose:
    action: str
    mood: str
    gesture: str
    scene: str
    expression: str
    costume: str
    negative: str = ""


POSES = {
    "brush": Pose(
        action=("(brushing teeth:1.5), (toothbrush:1.4), "
                "(holding toothbrush:1.35), (toothbrush in mouth:1.3), "),
        mood="",
        gesture="(messy hair:1.25), (bed hair:1.2), ",
        scene=("(standing:1.2), (upper body:1.3), (looking at viewer:1.1), "
               "(night:1.35), (bathroom:1.15), (sink:1.1), (indoors:1.1), "),
        expression="sleepy", costume="roomwear"),
    "coffee": Pose(
        action=("(drinking:1.3), (iced coffee:1.4), (plastic cup:1.45), "
                "(clear cup:1.2), (drinking straw:1.4), (holding cup:1.35), "
                "(straw in mouth:1.25), "),
        mood="",
        gesture="(looking at viewer:1.1), ",
        scene=("(outdoors:1.3), (street:1.15), (day:1.1), (standing:1.2), "
               "(cowboy shot:1.3), (thighs:1.2), "),
        expression="resting", costume="outing",
        negative="(mug:1.3), (paper cup:1.2), (hot coffee:1.2), (steam:1.3), "),
    "amae": Pose(
        action="",
        mood="(pleading:1.15), ",
        gesture=("(head tilt:1.2), (leaning forward:1.3), "
                 "(looking at viewer:1.3), (own hands clasped:1.25), "
                 "(hands up:1.1), "),
        scene=("(outdoors:1.3), (shopping:1.15), (street:1.1), (day:1.1), "
               "(standing:1.2), (cowboy shot:1.3), (thighs:1.2), "),
        expression="doya", costume="outing"),
}
