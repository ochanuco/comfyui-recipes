"""Expression overlays: mouth and eyes, layered onto a pose's own face."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Expression:
    mouth: str
    eyes: str


EXPRESSIONS = {
    "resting": Expression(
        mouth="", eyes="(unamused:1.3), (half-closed eyes:1.3), "),
    "sleepy": Expression(
        mouth="",
        eyes="(sleepy:1.4), (drowsy:1.3), (half-closed eyes:1.4), "),
    "doya": Expression(
        mouth="(smug:1.35), (doyagao:1.25), ",
        eyes="(tareme:1.3), (half-closed eyes:1.3), (unamused:1.15), "),
}
