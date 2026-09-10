"""Declarative request-time diffs against a resolved RenderSpec."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .models import RenderSpec

TEXT_TARGETS = ("prompt.positive", "prompt.negative",
                "prompt.hires.positive", "prompt.hires.negative")
# `prompt.positive.<part>` targets one named part of `RenderSpec.positive_parts`
# instead of the whole joined string -- same ops and fields as a text target.
PART_TARGET_PREFIX = "prompt.positive."
NUMBER_TARGETS = ("render.cfg", "render.steps", "render.width",
                  "render.height", "hires.denoise",
                  "render.layerdiffuse_weight", "render.lora_strength")
STRING_TARGETS = ("render.model", "render.sampler", "render.scheduler",
                  "render.layerdiffuse_config")
LAYERDIFFUSE_CONFIGS = ("SDXL, Attention Injection", "SDXL, Conv Injection")
TEXT_OPS = ("append", "prepend", "replace", "remove")
_KNOWN_KEYS = frozenset({"target", "op", "value", "old", "reason"})

# Read by _parse_number_patch's messages and by the published catalog.
NUMBER_CONSTRAINTS = {
    "render.steps": "an int >= 1",
    "render.width": "an int >= 64, a multiple of 8",
    "render.height": "an int >= 64, a multiple of 8",
    "render.cfg": "> 0",
    "render.layerdiffuse_weight": "-1 <= value <= 3",
    "render.lora_strength": "0 <= value <= 2",
    "hires.denoise": "0 < value <= 1",
}


@dataclass(frozen=True)
class Patch:
    target: str
    op: str
    value: str | float | int | None
    old: str | None
    reason: str


def _fail(target: object, message: str) -> None:
    raise ValueError(f"patch {target!r}: {message}")


def _require_str(patch: dict, key: str, target: object) -> str:
    value = patch.get(key)
    if not isinstance(value, str) or not value:
        _fail(target, f"{key!r} must be a non-empty string")
    return value


def _parse_text_patch(patch: dict, target: str) -> Patch:
    op = patch.get("op")
    if op not in TEXT_OPS:
        _fail(target, f"op must be one of {TEXT_OPS}, got {op!r}")
    reason = _require_str(patch, "reason", target)
    if op in ("append", "prepend"):
        if "old" in patch:
            _fail(target, f"op {op!r} does not take 'old'")
        value = _require_str(patch, "value", target)
        return Patch(target, op, value, None, reason)
    if op == "replace":
        old = _require_str(patch, "old", target)
        value = _require_str(patch, "value", target)
        return Patch(target, op, value, old, reason)
    old = _require_str(patch, "old", target)
    if "value" in patch:
        _fail(target, "op 'remove' does not take 'value'")
    return Patch(target, op, None, old, reason)


def _parse_number_patch(patch: dict, target: str) -> Patch:
    op = patch.get("op")
    if op != "set":
        _fail(target, f"op must be 'set' for {target!r}, got {op!r}")
    reason = _require_str(patch, "reason", target)
    value = patch.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(target, f"value must be a number, got {value!r}")
    constraint = NUMBER_CONSTRAINTS[target]
    if target == "render.steps":
        if not isinstance(value, int) or value < 1:
            _fail(target, f"{target} value must be {constraint}")
    elif target in ("render.width", "render.height"):
        if not isinstance(value, int) or value < 64 or value % 8:
            _fail(target, f"{target} value must be {constraint}")
    elif target == "render.cfg":
        if value <= 0:
            _fail(target, f"{target} value must be {constraint}")
    elif target == "render.layerdiffuse_weight":
        if value < -1 or value > 3:
            _fail(target, f"{target} value must satisfy {constraint}")
    elif target == "render.lora_strength":
        if value < 0 or value > 2:
            _fail(target, f"{target} value must satisfy {constraint}")
    elif value <= 0 or value > 1:
        _fail(target, f"{target} value must satisfy {constraint}")
    return Patch(target, op, value, None, reason)


def _parse_string_patch(patch: dict, target: str) -> Patch:
    op = patch.get("op")
    if op != "set":
        _fail(target, f"op must be 'set' for {target!r}, got {op!r}")
    reason = _require_str(patch, "reason", target)
    value = _require_str(patch, "value", target)
    if (target == "render.layerdiffuse_config"
            and value not in LAYERDIFFUSE_CONFIGS):
        _fail(target,
              "render.layerdiffuse_config value must be one of "
              f"{LAYERDIFFUSE_CONFIGS}")
    return Patch(target, op, value, None, reason)


def parse_patches(raw: object) -> tuple[Patch, ...]:
    if not isinstance(raw, list):
        raise ValueError("generation.patches must be an array of patch objects")
    patches = []
    for patch in raw:
        if not isinstance(patch, dict):
            _fail(patch, "patch must be an object")
        unknown = set(patch) - _KNOWN_KEYS
        if unknown:
            _fail(patch.get("target"),
                  f"unknown patch keys: {sorted(unknown)}")
        target = patch.get("target")
        if not isinstance(target, str):
            _fail(target, "'target' must be a string")
        part_name = (target[len(PART_TARGET_PREFIX):]
                    if target.startswith(PART_TARGET_PREFIX) else "")
        if target in TEXT_TARGETS:
            patches.append(_parse_text_patch(patch, target))
        elif part_name and "." not in part_name:
            patches.append(_parse_text_patch(patch, target))
        elif target in NUMBER_TARGETS:
            patches.append(_parse_number_patch(patch, target))
        elif target in STRING_TARGETS:
            patches.append(_parse_string_patch(patch, target))
        else:
            allowed = (TEXT_TARGETS + (PART_TARGET_PREFIX + "<part>",)
                      + NUMBER_TARGETS + STRING_TARGETS)
            _fail(target, f"unknown target, must be one of {allowed}")
    return tuple(patches)


def _splice(text: str, target: str, old: str, new: str) -> str:
    if old not in text:
        raise ValueError(f"patch needle absent in {target}: {old!r}")
    return text.replace(old, new)


def _apply_text(text: str, patch: Patch) -> str:
    if patch.op == "append":
        return text + patch.value
    if patch.op == "prepend":
        return patch.value + text
    if patch.op == "replace":
        return _splice(text, patch.target, patch.old, patch.value)
    return _splice(text, patch.target, patch.old, "")


def _apply_part(spec: RenderSpec, patch: Patch, part_name: str) -> RenderSpec:
    if not spec.positive_parts:
        raise ValueError(
            f"patch {patch.target!r}: this recipe has no prompt parts")
    names = [name for name, _ in spec.positive_parts]
    if part_name not in names:
        raise ValueError(
            f"patch {patch.target!r}: unknown part, must be one of {names}")
    parts = list(spec.positive_parts)
    index = names.index(part_name)
    name, text = parts[index]
    parts[index] = (name, _apply_text(text, patch))
    joined = "".join(text for _, text in parts)
    prompts = replace(spec.prompts, positive=joined)
    return replace(spec, positive_parts=tuple(parts), prompts=prompts)


def _apply_one(spec: RenderSpec, patch: Patch) -> RenderSpec:
    if patch.target.startswith(PART_TARGET_PREFIX):
        return _apply_part(spec, patch, patch.target[len(PART_TARGET_PREFIX):])
    if patch.target == "prompt.positive":
        prompts = replace(spec.prompts,
                          positive=_apply_text(spec.prompts.positive, patch))
        return replace(spec, prompts=prompts)
    if patch.target == "prompt.negative":
        prompts = replace(spec.prompts,
                          negative=_apply_text(spec.prompts.negative, patch))
        return replace(spec, prompts=prompts)
    if patch.target in ("prompt.hires.positive", "prompt.hires.negative",
                        "hires.denoise"):
        if spec.hires is None:
            raise ValueError(f"{patch.target} requires request hires")
    if patch.target == "prompt.hires.positive":
        # A pose without a pass-2 positive shares pass 1's node; materializing
        # it here just spells that sharing out before the patch edits it.
        base = (spec.hires.positive if spec.hires.positive is not None
                else spec.prompts.positive)
        hires = replace(spec.hires, positive=_apply_text(base, patch))
        return replace(spec, hires=hires)
    if patch.target == "prompt.hires.negative":
        hires = replace(spec.hires,
                        negative=_apply_text(spec.hires.negative, patch))
        return replace(spec, hires=hires)
    if patch.target == "render.cfg":
        return replace(spec, cfg=float(patch.value))
    if patch.target == "render.steps":
        return replace(spec, steps=patch.value)
    if patch.target == "render.width":
        return replace(spec, width=patch.value)
    if patch.target == "render.height":
        return replace(spec, height=patch.value)
    if patch.target == "render.model":
        return replace(spec, model_path=patch.value)
    if patch.target == "render.sampler":
        return replace(spec, sampler_name=patch.value)
    if patch.target == "render.scheduler":
        return replace(spec, scheduler=patch.value)
    if patch.target == "render.layerdiffuse_weight":
        return replace(spec, layerdiffuse_weight=float(patch.value))
    if patch.target == "render.layerdiffuse_config":
        return replace(spec, layerdiffuse_config=patch.value)
    if patch.target == "render.lora_strength":
        if not spec.loras:
            raise ValueError(
                "render.lora_strength requires a recipe with loras")
        strength = float(patch.value)
        loras = tuple((name, strength) for name, _ in spec.loras)
        return replace(spec, loras=loras)
    hires = replace(spec.hires, denoise=float(patch.value))
    return replace(spec, hires=hires)


def apply_patches(spec: RenderSpec, patches: tuple[Patch, ...]) -> RenderSpec:
    for patch in patches:
        spec = _apply_one(spec, patch)
    return spec
