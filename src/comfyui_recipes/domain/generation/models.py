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
