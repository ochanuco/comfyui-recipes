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
    canvas: tuple[int, int] | None = None


POSES = {
    "brush": Pose(
        action=("(brushing teeth:1.5), (toothbrush:1.4), "
                "(holding toothbrush:1.35), (toothbrush in mouth:1.3), "),
        mood="",
        gesture="(messy hair:1.25), (bed hair:1.2), ",
        scene=("(standing:1.2), (upper body:1.3), (looking at viewer:1.1), "
               "(night:1.35), (bathroom:1.15), (sink:1.1), (indoors:1.1), "),
        expression="sleepy", costume="roomwear"),
    "sofa": Pose(
        action=("(lying:1.45), (on side:1.35), (on couch:1.45), "
                "(couch:1.3), (knees up:1.1), (hand on own cheek:1.1), "),
        mood="(relaxed:1.2), (cozy:1.1), ",
        gesture=("(messy hair:1.2), (wet hair:1.3), (damp hair:1.2), "
                 "(after bath:1.3), (towel around neck:1.15), (blush:1.1), "
                 "(looking at viewer:1.0), (thighhighs:1.45), "
                 "(purple thighhighs:1.35), (loose thighhighs:1.3), "
                 "(slouch socks:1.2), (baggy:1.15), (wrinkled legwear:1.1), "),
        scene=("(indoors:1.2), (living room:1.15), (from side:1.25), "
               "(full body:1.3), (thighs:1.15), (evening:1.1), "),
        expression="sleepy", costume="roomwear",
        negative=("(sitting:1.3), (standing:1.4), (bed:1.25), "
                  "(pillow:1.1), (blanket:1.1), (socks:1.3), "
                  "(loose socks:1.3), (kneehighs:1.2), "),
        canvas=(2048, 1280)),
    "cinema": Pose(
        action=("(walking:1.2), (holding popcorn:1.45), (popcorn:1.4), "
                "(popcorn bucket:1.3), (holding cup:1.35), "
                "(disposable cup:1.3), (drinking straw:1.25), (cola:1.15), "
                "(holding food:1.1), (holding with both hands:1.1), "),
        mood="(excited:1.1), ",
        gesture=("(looking at viewer:1.2), (sneakers:1.3), "
                 "(white sneakers:1.2), "),
        scene=("(movie theater:1.4), (theater lobby:1.2), (indoors:1.2), "
               "(dim lighting:1.1), (carpet:1.1), (cowboy shot:1.3), "
               "(thighs:1.15), "),
        expression="doya", costume="outing",
        negative=("(sitting:1.3), (eating:1.3), (theater seat:1.1), "
                  "(mug:1.2), (glass:1.2), (bottle:1.2), (bag:1.1), "
                  "(multiple girls:1.3), "),
        ),
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
    "step": Pose(
        action=("(walking:1.3), (stepping:1.3), (big step:1.35), "
                "(wide stride:1.3), (one leg forward:1.3), "
                "(straight leg:1.2), (leg lift:1.15), (arms spread:1.4), "
                "(outstretched arms:1.35), (balancing:1.35), (playful:1.15), "),
        mood="",
        gesture="(looking at viewer:1.1), (sneakers:1.3), (white sneakers:1.2), ",
        scene=("(outdoors:1.3), (cobblestone:1.4), (stone floor:1.25), "
               "(street:1.15), (day:1.1), (full body:1.35), (from side:1.1), "
               "(thighs:1.1), "),
        expression="resting", costume="outing",
        negative="(running:1.3), (jumping:1.25), (sitting:1.2), "),
    "stand": Pose(
        action=("(standing:1.5), (own hands together:1.3), (hands up:1.2), "
                "(arched back:1.15), "),
        mood="",
        gesture=("(looking at viewer:1.2), (sneakers:1.3), "
                 "(white sneakers:1.2), "),
        scene=("(from front:1.3), (full body:1.45), (wide shot:1.3), "
               "(thighs:1.1), "),
        expression="doya", costume="outing",
        negative="(sitting:1.3), (cowboy shot:1.2), (upper body:1.2), "),
}
