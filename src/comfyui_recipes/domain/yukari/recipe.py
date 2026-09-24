"""The interpreter: pose, costume and expression records into a prompt pair.

A hires pass's `hires` is a target longest side; the second-pass canvas is
computed proportionally from the pose's own canvas, and the first pass's
prompts carry over unchanged (`HiresSpec.positive` is `None`,
`HiresSpec.negative` is the base negative).
"""

from __future__ import annotations

from ..generation.models import HiresSpec, PromptPair, RenderSpec
from ..generation.prompt_lint import tags as prompt_tags
from .components import Component, Priority, Section, assemble, part_groups
from .costumes import (
    COSTUME_BAN,
    COSTUMES,
    HOODED_COSTUMES,
    legwear_block,
)
from .delivery_style import PAINT_BAN, ROUGH_BAN, ROUGH_STYLE
from .expressions import EXPRESSIONS
from .poses import POSES
from .prompt_style import (
    ARTIST_TAG,
    BACKGROUND,
    BODY,
    CFG,
    CHARACTER_TAG,
    COLORED_LINE_BAN,
    COUNT_TAG,
    DETAIL_BAN,
    DIGIT_BAN,
    DOT_BAN,
    FACE,
    GARMENT_BLACK_BAN,
    GARMENT_GLOSS_TAGS,
    GRADIENT_BAN,
    HAND_BAN,
    HEIGHT,
    HIRES_DENOISE,
    HOOD_BAN,
    IDENTITY,
    MODEL,
    NEGATIVE_TAIL,
    PROPORTION_BAN,
    QUALITY_TAG,
    SAMPLER,
    SCHEDULER,
    SCORE_BAN,
    SERIES_TAG,
    SHADE_BAN,
    SHEER_BAN,
    SHEER_TONE_BAN,
    SHINE_BAN,
    STEPS,
    STYLE,
    THIN_BODY_BAN,
    VIVID_BAN,
    WIDTH,
)


# The 13 legacy part names this recipe used to join `positive()` from,
# before the component model split each into its own patch target.
# `PART_GROUPS` maps each one to the component names that composed it, in
# the declaration order `_components` builds them in; `patches.py` resolves
# a `prompt.positive.<part>` patch against them for a caller that still
# names a legacy part.
PART_NAMES = ("quality", "identity", "pose", "mouth", "mood", "eyes",
              "gesture", "costume", "scene", "body", "background", "face",
              "style")
PART_GROUPS = part_groups(PART_NAMES)

# The identity vocabulary this recipe can carry, at bare-tag level: hair,
# sidelock, eye colour, ornament, eye-shape, and the `standard` costume's
# cardigan/hood.
IDENTITY_TAG_NAMES = frozenset({
    "light purple hair", "short hair with long locks", "very long sidelocks",
    "purple eyes", "hair ornament", "tareme", "jitome",
    "eggplant purple hooded cardigan", "rabbit hood",
})


def _components(pose: str, costume: str | None = None,
                expression: str | None = None,
                legwear: str | None = None) -> tuple[Component, ...]:
    p = POSES[pose]
    e = EXPRESSIONS[expression if expression is not None else p.expression]
    c = costume if costume is not None else p.costume
    lw = legwear if legwear is not None else p.legwear_kind
    legwear_text = legwear_block(c, lw) if p.legwear else ""
    G, M = Section.GENERAL, Priority.MAIN
    L, T = Priority.LEAD, Priority.TAIL
    declared = (
        Component("quality", Section.QUALITY, M, QUALITY_TAG),
        Component("count", Section.COUNT, M, COUNT_TAG),
        Component("character", Section.CHARACTER, M, CHARACTER_TAG),
        Component("series", Section.SERIES, M, SERIES_TAG),
        Component("artist", Section.ARTIST, M, ARTIST_TAG),
        Component("identity", G, L, IDENTITY),
        Component("action", G, M, p.action),
        Component("mouth", G, M, e.mouth),
        Component("mood", G, M, p.mood),
        Component("eye_base", G, L, e.eye_shape),
        Component("eye_quality", G, L, e.eyes),
        Component("gesture", G, M, p.gesture),
        Component("costume", G, M, COSTUMES[c]),
        Component("legwear", G, L, legwear_text),
        Component("place", G, M, p.scene),
        Component("framing_tags", G, L, p.framing_tags),
        Component("leg_display", G, L, p.leg_display),
        Component("body_build", G, L, p.body if p.body is not None else BODY),
        Component("cutout", G, M,
                  p.background if p.background is not None else BACKGROUND),
        Component("face", G, T, FACE),
        Component("style", G, T, p.style if p.style is not None else STYLE),
    )
    return assemble(declared)


def positive_parts(pose: str, costume: str | None = None,
                   expression: str | None = None,
                   legwear: str | None = None) -> tuple[tuple[str, str], ...]:
    components = _components(pose, costume, expression, legwear)
    return tuple((c.name, c.text) for c in components)


def positive(pose: str, costume: str | None = None,
            expression: str | None = None,
            legwear: str | None = None) -> str:
    return "".join(
        text for _, text in positive_parts(pose, costume, expression, legwear))


def identity_tags(pose: str, costume: str | None = None) -> frozenset[str]:
    bare = set(prompt_tags(positive(pose, costume)))
    return frozenset(IDENTITY_TAG_NAMES & bare)


def negative(pose: str, costume: str | None = None,
            expression: str | None = None,
            legwear: str | None = None) -> str:
    p = POSES[pose]
    _ = EXPRESSIONS[expression if expression is not None else p.expression]
    c = costume if costume is not None else p.costume
    lw = legwear if legwear is not None else p.legwear_kind
    _ = COSTUMES[c]
    _ = legwear_block(c, lw)
    hood_ban = "" if c in HOODED_COSTUMES else HOOD_BAN
    garment_black_ban = GARMENT_BLACK_BAN if c == "standard" else ""
    shine_ban, sheer_ban = SHINE_BAN, ""
    if lw in ("sheer-gloss", "sheer") and p.legwear:
        for tags in GARMENT_GLOSS_TAGS:
            shine_ban = shine_ban.replace(tags, "")
        sheer_ban = SHEER_BAN + (SHEER_TONE_BAN if lw == "sheer" else "")
    return (DIGIT_BAN + DETAIL_BAN + COLORED_LINE_BAN + THIN_BODY_BAN
            + p.negative + shine_ban + GRADIENT_BAN
            + NEGATIVE_TAIL + VIVID_BAN + hood_ban + garment_black_ban
            + COSTUME_BAN.get(c, "") + sheer_ban + SCORE_BAN + PROPORTION_BAN)


def refinement_prompt(base: PromptPair) -> PromptPair:
    """Build the anima-specific prompt used by the delivery redraw."""
    negative = base.negative
    for ban in (DETAIL_BAN, GRADIENT_BAN, COLORED_LINE_BAN):
        negative = negative.replace(ban, "")
    return PromptPair(
        base.positive.replace(STYLE, ROUGH_STYLE),
        ROUGH_BAN + PAINT_BAN + HAND_BAN + SHADE_BAN + DOT_BAN + negative,
    )


def render_spec(pose: str, seed: int, prefix: str, hires: int = 0,
                denoise: float | None = None, costume: str | None = None,
                expression: str | None = None,
                legwear: str | None = None) -> RenderSpec:
    if not hires and denoise is not None:
        raise ValueError("yukari denoise needs hires")
    width, height = POSES[pose].canvas or (WIDTH, HEIGHT)
    parts = positive_parts(pose, costume, expression, legwear)
    base_negative = negative(pose, costume, expression, legwear)
    hires_spec = None
    if hires:
        longest = max(width, height)
        hires_width = round(hires * width / longest / 8) * 8
        hires_height = round(hires * height / longest / 8) * 8
        if hires_width < 8 or hires_height < 8:
            raise ValueError(
                "hires dimensions must both be at least 8 pixels, got "
                f"{hires_width}x{hires_height}")
        hires_spec = HiresSpec(
            width=hires_width,
            height=hires_height,
            denoise=HIRES_DENOISE if denoise is None else denoise,
            positive=None,
            negative=base_negative,
        )
    return RenderSpec(
        model_path=MODEL,
        prompts=PromptPair("".join(text for _, text in parts), base_negative),
        positive_parts=parts,
        part_groups=PART_GROUPS,
        width=width, height=height, seed=seed, steps=STEPS, cfg=CFG,
        sampler_name=SAMPLER, scheduler=SCHEDULER, denoise=1.0,
        filename_prefix=prefix, hires=hires_spec, loras=POSES[pose].loras)
