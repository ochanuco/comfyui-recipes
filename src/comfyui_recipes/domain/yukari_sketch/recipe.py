"""The interpreter: pose and costume records into a prompt pair.

Sketch has no second pass of its own -- like `yukari_anima.recipe`,
`render_spec` refuses `hires`/`denoise` outright rather than silently
ignoring them. The delivery redraw reuses the base prompt verbatim; the
LoRA that gives the base pass its look rides into the redraw through the
graph (see `infrastructure/comfyui/yukari_graph.py`), not through the
prompt.
"""

from __future__ import annotations

from ..generation.models import PromptPair, RenderSpec
from ..generation.prompt_lint import tags as prompt_tags
from .costumes import COSTUMES, LEGWEAR_BY_COSTUME, NEGATIVE_BY_COSTUME
from .poses import POSES
from .prompt_style import (
    BACKGROUND,
    BODY,
    CFG,
    CHARACTER,
    FACE,
    FINISH,
    GLOSS_BAN,
    HEIGHT,
    IDENTITY,
    LEGWEAR,
    LORA,
    MODEL,
    NEGATIVE,
    PROPORTION,
    QUALITY,
    SAMPLER,
    SCHEDULER,
    STEPS,
    TRIGGER,
    WIDTH,
)


# The order `positive()` joins its blocks in. `patches.py` resolves
# `prompt.positive.<part>` against these names; concatenating the texts of
# `positive_parts()` in order reproduces `positive()` byte for byte.
PART_NAMES = ("quality", "identity", "costume", "pose", "proportion",
              "background", "legwear", "face", "body", "finish")

# The identity vocabulary this recipe can carry, at bare-tag level: hair
# colour/length, sidelocks, eye colour, hair ornament, eye-shape identity and
# the costume's cardigan/hood. `identity_tags()` intersects this with what a
# given pose/costume actually renders, so a costume without a hood (none,
# here) or a pose without `jitome` simply contributes nothing for that slot.
IDENTITY_TAG_NAMES = frozenset({
    "light purple hair", "short hair with long locks", "very long sidelocks",
    "purple eyes", "hair ornament", "tareme", "jitome",
    "black hooded cardigan", "rabbit hood",
})


def positive_parts(pose: str, costume: str | None = None) -> tuple[tuple[str, str], ...]:
    p = POSES[pose]
    name = costume if costume is not None else p.costume
    costume_block = COSTUMES[name]
    legwear = LEGWEAR_BY_COSTUME.get(name, LEGWEAR)
    face = p.face if p.face is not None else FACE
    values = (QUALITY + TRIGGER, CHARACTER + IDENTITY, costume_block,
              p.action, PROPORTION, BACKGROUND, legwear, face, BODY, FINISH)
    return tuple(zip(PART_NAMES, values))


def positive(pose: str, costume: str | None = None) -> str:
    return "".join(text for _, text in positive_parts(pose, costume))


def identity_tags(pose: str, costume: str | None = None) -> frozenset[str]:
    bare = set(prompt_tags(positive(pose, costume)))
    return frozenset(IDENTITY_TAG_NAMES & bare)


def negative(pose: str, costume: str | None = None) -> str:
    p = POSES[pose]
    name = costume if costume is not None else p.costume
    _ = COSTUMES[name]
    return NEGATIVE + NEGATIVE_BY_COSTUME.get(name, "") + GLOSS_BAN


def refinement_prompt(base: PromptPair) -> PromptPair:
    """The redraw uses the same prompt as the base pass."""
    return base


def render_spec(pose: str, seed: int, prefix: str, hires: int = 0,
                denoise: float | None = None,
                costume: str | None = None,
                layerdiffuse: bool = False) -> RenderSpec:
    if hires:
        raise ValueError("yukari-sketch has no second pass -- hires must be 0")
    if denoise is not None:
        raise ValueError(
            "yukari-sketch has no second pass -- denoise must be None")
    width, height = POSES[pose].canvas or (WIDTH, HEIGHT)
    parts = positive_parts(pose, costume)
    return RenderSpec(
        model_path=MODEL,
        prompts=PromptPair("".join(text for _, text in parts),
                           negative(pose, costume)),
        positive_parts=parts,
        width=width, height=height, seed=seed, steps=STEPS, cfg=CFG,
        sampler_name=SAMPLER, scheduler=SCHEDULER, denoise=1.0,
        filename_prefix=prefix, hires=None, loras=(LORA,),
        layerdiffuse=layerdiffuse)
