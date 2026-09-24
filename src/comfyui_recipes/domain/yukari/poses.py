"""Every pose: its own tag blocks plus the expression/costume it defaults to."""

from __future__ import annotations

from dataclasses import dataclass

from .components import Framing
from .costumes import DEFAULT_LEGWEAR


@dataclass(frozen=True)
class Pose:
    action: str
    mood: str
    gesture: str
    scene: str
    framing: Framing
    leg_display: str
    expression: str
    costume: str
    negative: str = ""
    canvas: tuple[int, int] | None = None
    legwear: bool = True
    legwear_kind: str = DEFAULT_LEGWEAR
    body: str | None = None
    style: str | None = None
    background: str | None = None
    loras: tuple[tuple[str, float], ...] = ()
    angle: str = ""


POSES = {
    "cinema": Pose(
        action=("(walking:1.2), (holding popcorn:1.45), (popcorn:1.4), "
                "(popcorn bucket:1.3), (holding cup:1.35), "
                "(disposable cup:1.3), (drinking straw:1.25), (cola:1.15), "
                "(holding food:1.1), (holding with both hands:1.1), "),
        mood="(excited:1.1), ",
        gesture=("(looking at viewer:1.2), (sneakers:1.3), "
                 "(white sneakers:1.2), "),
        scene=("(movie theater:1.4), (theater lobby:1.2), (indoors:1.2), "
               "(dim lighting:1.1), (carpet:1.1), "),
        framing=Framing.COWBOY,
        leg_display="(thighs:1.15), ",
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
        scene="(outdoors:1.3), (street:1.15), (day:1.1), (standing:1.2), ",
        framing=Framing.COWBOY,
        leg_display="(thighs:1.2), ",
        expression="resting", costume="outing",
        negative="(mug:1.3), (paper cup:1.2), (hot coffee:1.2), (steam:1.3), "),
    "amae": Pose(
        action="",
        mood="(pleading:1.15), ",
        gesture=("(head tilt:1.2), (leaning forward:1.3), "
                 "(looking at viewer:1.3), (own hands clasped:1.25), "
                 "(hands up:1.1), "),
        scene=("(outdoors:1.3), (shopping:1.15), (street:1.1), (day:1.1), "
               "(standing:1.2), "),
        framing=Framing.COWBOY,
        leg_display="(thighs:1.2), ",
        expression="doya", costume="outing"),
    "step": Pose(
        action=("(walking:1.3), (stepping:1.3), (big step:1.35), "
                "(wide stride:1.3), (one leg forward:1.3), "
                "(straight leg:1.2), (leg lift:1.15), (arms spread:1.4), "
                "(outstretched arms:1.35), (balancing:1.35), (playful:1.15), "),
        mood="",
        gesture="(looking at viewer:1.1), (sneakers:1.3), (white sneakers:1.2), ",
        scene=("(outdoors:1.3), (cobblestone:1.4), (stone floor:1.25), "
               "(street:1.15), (day:1.1), "),
        framing=Framing.FULL,
        angle="(from side:1.1), ",
        leg_display="(thighs:1.1), ",
        expression="resting", costume="outing",
        negative="(running:1.3), (jumping:1.25), (sitting:1.2), "),
    "stand": Pose(
        action=("(standing:1.5), (own hands together:1.3), (hands up:1.2), "
                "(arched back:1.15), "),
        mood="",
        gesture=("(looking at viewer:1.2), (sneakers:1.3), "
                 "(white sneakers:1.2), "),
        scene="",
        framing=Framing.FULL,
        angle="(from front:1.3), ",
        leg_display="(thighs:1.1), ",
        expression="doya", costume="outing",
        negative="(sitting:1.3), (cowboy shot:1.2), (upper body:1.2), "),
    "dance": Pose(
        action=("(standing:1.4), (dancing:1.4), (knock-kneed:1.3), "
                "(one arm up:1.2), (clenched hand:1.1), "),
        mood="",
        gesture=("(looking at viewer:1.2), (sneakers:1.3), "
                 "(white sneakers:1.2), "),
        scene="",
        framing=Framing.FULL,
        angle="(from front:1.3), ",
        leg_display="(thighs:1.1), ",
        expression="v", costume="standard",
        negative="(sitting:1.3), (cowboy shot:1.2), (upper body:1.2), ",
        legwear_kind="sheer-gloss"),
    "bust": Pose(
        action="",
        mood="",
        gesture="(looking at viewer:1.2), ",
        scene="",
        framing=Framing.BUST,
        angle="(from front:1.3), ",
        leg_display="",
        expression="smile", costume="standard",
        negative=("(sitting:1.3), (wavy mouth:1.4), (:3:1.3), (pout:1.3), "
                  "(pursed lips:1.3), (puckered lips:1.2), "),
        legwear=False,
        body="(mature female:1.3), (adult:1.2), adult proportions, "),
    "gao": Pose(
        action=("(claw pose:1.45), (gao:1.2), (hands up:1.25), "
                "(standing:1.3), (leaning forward:1.15), "),
        mood="",
        gesture="(looking at viewer:1.2), ",
        scene="",
        framing=Framing.COWBOY,
        angle="(from front:1.3), ",
        leg_display="(thighs:1.2), ",
        expression="gao", costume="standard",
        negative=("(sitting:1.3), (upper body:1.2), "
                  "(ribbed legwear:1.3), (vertical-striped legwear:1.3), ")),
}
