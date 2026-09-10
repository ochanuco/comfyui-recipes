"""Pure generation values shared by recipes and graph adapters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptPair:
    positive: str
    negative: str


@dataclass(frozen=True)
class HiresSpec:
    width: int
    height: int
    denoise: float
    negative: str
    positive: str | None = None


@dataclass(frozen=True)
class RenderSpec:
    model_path: str
    prompts: PromptPair
    width: int
    height: int
    seed: int
    steps: int
    cfg: float
    sampler_name: str
    scheduler: str
    denoise: float
    filename_prefix: str
    hires: HiresSpec | None = None
    loras: tuple[tuple[str, float], ...] = ()
    layerdiffuse: bool = False
    layerdiffuse_weight: float = 1.0
    layerdiffuse_config: str = "SDXL, Conv Injection"
    # The ordered (name, text) breakdown of `prompts.positive` -- joining the
    # texts in order reproduces it byte for byte. Empty for a recipe (yukari)
    # that has no named parts; `patches.py` reads this to resolve
    # `prompt.positive.<part>` targets.
    positive_parts: tuple[tuple[str, str], ...] = ()
