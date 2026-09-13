"""The interpreter: pose, costume and expression records into a prompt pair.

Anima has no second pass, so unlike `yukari.recipe` there is no pass-2
splicing here -- `render_spec` refuses `hires`/`denoise` outright rather
than silently ignoring them.
"""

from __future__ import annotations

from ..generation.models import PromptPair, RenderSpec
from ..generation.prompt_lint import tags as prompt_tags
from ..yukari.prompt_style import DOT_BAN, HAND_BAN, SHADE_BAN
from .costumes import COSTUMES, HOODED_COSTUMES, LEGWEAR
from .delivery_style import PAINT_BAN, ROUGH_BAN, ROUGH_STYLE
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
    HOOD_BAN,
    IDENTITY,
    MODEL,
    NEGATIVE_TAIL,
    PROPORTION_BAN,
    QUALITY,
    SAMPLER,
    SCHEDULER,
    SCORE_BAN,
    SHINE_BAN,
    STEPS,
    STYLE,
    THIN_BODY_BAN,
    WIDTH,
)


# The order `positive()` joins its blocks in. `patches.py` resolves
# `prompt.positive.<part>` against these names; concatenating the texts of
# `positive_parts()` in order reproduces `positive()` byte for byte.
PART_NAMES = ("quality", "identity", "pose", "mouth", "mood", "eyes",
              "gesture", "costume", "scene", "body", "background", "face",
              "style")

# The identity vocabulary this recipe can carry, at bare-tag level: hair,
# sidelock, eye colour, ornament, eye-shape, and the `standard` costume's
# cardigan/hood.
IDENTITY_TAG_NAMES = frozenset({
    "light purple hair", "short hair with long locks", "very long sidelocks",
    "purple eyes", "hair ornament", "tareme", "jitome",
    "black hooded cardigan", "rabbit hood",
})


def positive_parts(pose: str, costume: str | None = None,
                   expression: str | None = None) -> tuple[tuple[str, str], ...]:
    p = POSES[pose]
    e = EXPRESSIONS[expression if expression is not None else p.expression]
    c = costume if costume is not None else p.costume
    costume_block = COSTUMES[c] + (LEGWEAR[c] if p.legwear else "")
    values = (QUALITY, CHARACTER + IDENTITY, p.action, e.mouth, p.mood,
              e.eyes, p.gesture, costume_block, p.scene,
              p.body if p.body is not None else BODY, BACKGROUND,
              FACE, p.style if p.style is not None else STYLE)
    return tuple(zip(PART_NAMES, values))


def positive(pose: str, costume: str | None = None,
            expression: str | None = None) -> str:
    return "".join(text for _, text in positive_parts(pose, costume, expression))


def identity_tags(pose: str, costume: str | None = None) -> frozenset[str]:
    bare = set(prompt_tags(positive(pose, costume)))
    return frozenset(IDENTITY_TAG_NAMES & bare)


def negative(pose: str, costume: str | None = None,
            expression: str | None = None) -> str:
    p = POSES[pose]
    _ = EXPRESSIONS[expression if expression is not None else p.expression]
    c = costume if costume is not None else p.costume
    _ = COSTUMES[c]
    hood_ban = "" if c in HOODED_COSTUMES else HOOD_BAN
    return (DIGIT_BAN + DETAIL_BAN + COLORED_LINE_BAN + THIN_BODY_BAN
            + p.negative + SHINE_BAN + HATCH_BAN + GRADIENT_BAN
            + NEGATIVE_TAIL + hood_ban + SCORE_BAN + PROPORTION_BAN)


def refinement_prompt(base: PromptPair) -> PromptPair:
    """Build the anima-specific prompt used by the delivery redraw."""
    negative = base.negative
    for ban in (HATCH_BAN, DETAIL_BAN, GRADIENT_BAN, COLORED_LINE_BAN):
        negative = negative.replace(ban, "")
    return PromptPair(
        base.positive.replace(STYLE, ROUGH_STYLE),
        ROUGH_BAN + PAINT_BAN + HAND_BAN + SHADE_BAN + DOT_BAN + negative,
    )


def render_spec(pose: str, seed: int, prefix: str, hires: int = 0,
                denoise: float | None = None, costume: str | None = None,
                expression: str | None = None) -> RenderSpec:
    if hires:
        raise ValueError("yukari-anima has no second pass -- hires must be 0")
    if denoise is not None:
        raise ValueError(
            "yukari-anima has no second pass -- denoise must be None")
    width, height = POSES[pose].canvas or (WIDTH, HEIGHT)
    parts = positive_parts(pose, costume, expression)
    return RenderSpec(
        model_path=MODEL,
        prompts=PromptPair("".join(text for _, text in parts),
                           negative(pose, costume, expression)),
        positive_parts=parts,
        width=width, height=height, seed=seed, steps=STEPS, cfg=CFG,
        sampler_name=SAMPLER, scheduler=SCHEDULER, denoise=1.0,
        filename_prefix=prefix, hires=None, loras=POSES[pose].loras)
