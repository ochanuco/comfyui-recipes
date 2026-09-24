"""Expression overlays: mouth and eyes, layered onto a pose's own face."""

from __future__ import annotations

from dataclasses import dataclass

from .prompt_style import EYE_SHAPE, EYE_SHAPE_FLAT


@dataclass(frozen=True)
class Expression:
    mouth: str
    eyes: str
    eye_shape: str = EYE_SHAPE


EXPRESSIONS = {
    "resting": Expression(
        mouth="", eyes="(unamused:1.3), (half-closed eyes:1.3), "),
    "sleepy": Expression(
        mouth="",
        eyes="(sleepy:1.4), (drowsy:1.3), (half-closed eyes:1.4), "),
    "doya": Expression(
        mouth="(smug:1.35), (doyagao:1.25), ",
        eyes="(half-closed eyes:1.3), (unamused:1.15), "),
    "v": Expression(
        mouth="(:v:1.5), ",
        eyes="(half-closed eyes:1.3), (unamused:1.15), "),
    "smile": Expression(
        mouth="(closed mouth:1.2), (light smile:1.25), ",
        eyes="(confident:1.18), ", eye_shape=EYE_SHAPE_FLAT),
    "gao": Expression(
        mouth="(open mouth:1.35), (fang:1.3), ",
        eyes="(confident:1.18), ", eye_shape=EYE_SHAPE_FLAT),
}
