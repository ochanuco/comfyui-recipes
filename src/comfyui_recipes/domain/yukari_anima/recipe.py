"""The interpreter: pose, costume and expression records into a prompt pair.

Anima has no second pass, so unlike `yukari.recipe` there is no pass-2
splicing here -- `render_spec` refuses `hires`/`denoise` outright rather
than silently ignoring them.
"""

from __future__ import annotations

from ..generation.models import PromptPair, RenderSpec
from .costumes import COSTUMES
from .expressions import EXPRESSIONS
from .poses import POSES
from .prompt_style import (
    BACKGROUND,
    BODY,
    CFG,
    CHARACTER,
    COLORED_LINE_BAN,
    DETAIL_BAN,
    DIGIT_BAN,
    FACE,
    GRADIENT_BAN,
    HATCH_BAN,
    HEIGHT,
    IDENTITY,
    MODEL,
    NEGATIVE_TAIL,
    PROPORTION_BAN,
    QUALITY,
    SAMPLER,
    SCHEDULER,
    SHINE_BAN,
    STEPS,
    STYLE,
    THIN_BODY_BAN,
    WIDTH,
)


def positive(pose: str, costume: str | None = None,
            expression: str | None = None) -> str:
    p = POSES[pose]
    e = EXPRESSIONS[expression if expression is not None else p.expression]
    costume_block = COSTUMES[costume if costume is not None else p.costume]
    return (QUALITY + CHARACTER + IDENTITY + p.action + e.mouth + p.mood
            + e.eyes + p.gesture + costume_block + p.scene + BODY
            + BACKGROUND + FACE + STYLE)


def negative(pose: str, costume: str | None = None,
            expression: str | None = None) -> str:
    p = POSES[pose]
    _ = EXPRESSIONS[expression if expression is not None else p.expression]
    _ = COSTUMES[costume if costume is not None else p.costume]
    return (DIGIT_BAN + DETAIL_BAN + COLORED_LINE_BAN + THIN_BODY_BAN
            + p.negative + SHINE_BAN + HATCH_BAN + GRADIENT_BAN
            + NEGATIVE_TAIL + PROPORTION_BAN)


def render_spec(pose: str, seed: int, prefix: str, hires: int = 0,
                denoise: float | None = None, costume: str | None = None,
                expression: str | None = None) -> RenderSpec:
    if hires:
        raise ValueError("yukari-anima has no second pass -- hires must be 0")
    if denoise is not None:
        raise ValueError(
            "yukari-anima has no second pass -- denoise must be None")
    return RenderSpec(
        model_path=MODEL,
        prompts=PromptPair(positive(pose, costume, expression),
                           negative(pose, costume, expression)),
        width=WIDTH, height=HEIGHT, seed=seed, steps=STEPS, cfg=CFG,
        sampler_name=SAMPLER, scheduler=SCHEDULER, denoise=1.0,
        filename_prefix=prefix, hires=None)
