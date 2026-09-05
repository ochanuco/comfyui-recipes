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
from .costumes import COSTUMES
from .poses import POSES
from .prompt_style import (
    BACKGROUND,
    BODY,
    CFG,
    CHARACTER,
    FACE,
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


def positive(pose: str, costume: str | None = None) -> str:
    p = POSES[pose]
    costume_block = COSTUMES[costume if costume is not None else p.costume]
    return (QUALITY + TRIGGER + CHARACTER + IDENTITY + costume_block
            + p.action + PROPORTION + BACKGROUND + LEGWEAR + FACE + BODY)


def negative(pose: str, costume: str | None = None) -> str:
    p = POSES[pose]
    _ = COSTUMES[costume if costume is not None else p.costume]
    return NEGATIVE


def refinement_prompt(base: PromptPair) -> PromptPair:
    """The redraw uses the same prompt as the base pass."""
    return base


def render_spec(pose: str, seed: int, prefix: str, hires: int = 0,
                denoise: float | None = None,
                costume: str | None = None) -> RenderSpec:
    if hires:
        raise ValueError("yukari-sketch has no second pass -- hires must be 0")
    if denoise is not None:
        raise ValueError(
            "yukari-sketch has no second pass -- denoise must be None")
    return RenderSpec(
        model_path=MODEL,
        prompts=PromptPair(positive(pose, costume), negative(pose, costume)),
        width=WIDTH, height=HEIGHT, seed=seed, steps=STEPS, cfg=CFG,
        sampler_name=SAMPLER, scheduler=SCHEDULER, denoise=1.0,
        filename_prefix=prefix, hires=None, loras=(LORA,))
