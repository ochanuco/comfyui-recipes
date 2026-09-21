"""Turn a `requests` row's JSON `options` into a use-case's kwargs.

The wire contract is chimera's docs/worker-protocol.md.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..domain.repair.controlnet import CONTROL_MODELS, DEFAULT_CONTROL_STRENGTH
from ..domain.repair.loras import DEFAULT_PART_LORA_WEIGHT
from ..domain.repair.models import MODELS
from ..domain.yukari.delivery_style import STROKE_LIGHTS
from ..domain.yukari.dials import DIALS
from ..infrastructure.imaging.backdrops import PATTERNS, is_backdrop
from .finalize import RECIPE_DEFAULT

_KNOWN_FINALIZE_OPTIONS = frozenset({
    "denoise", "repin", "recolor", "keep_legwear", "route", "finalizer",
    "size", "skin", "keep_scene", "transparent",
    "backdrop", "upscale", "deliver_size", "stroke_light",
    "repair", "repair_regions", "repair_denoise", "repair_pad", "repair_size",
    "repair_lora", "repair_seeds", "keep_regions", "keep_strength",
    "deliver_only",
})

_KNOWN_REPAIR_OPTIONS = frozenset({
    "parts", "regions", "denoise", "seeds", "size", "pad", "lora", "model",
    "control", "control_strength",
})

_KNOWN_MASKED_REDRAW_OPTIONS = frozenset({
    "regions", "prompt_patch", "denoise", "mask_padding", "mask_feather",
    "size", "seeds",
})

_REPAIR_PARTS = frozenset({"hands", "feet"})

_MASKED_REDRAW_PROMPT_PATCH_MAX_LENGTH = 4096
_MASKED_REDRAW_SEEDS_MAX = 16

# `generation.recipe` -> its published `dials` block (see domain/*/dials.py).
_RECIPE_DIALS = {
    "yukari": DIALS,
}

# The finalize/repair option keys a recipe may define dial words for -- kept
# in sync by hand with the resolve_dial() call sites in finalize_arguments()
# and repair_arguments(); a key resolved there and missing here is reported
# unresolved in resolved_options. Public: interfaces/cli.py reads them too,
# to resolve the same keys' words from the args it already parsed.
FINALIZE_DIAL_KEYS = ("denoise", "keep_legwear", "repair_denoise", "repair_lora")
REPAIR_DIAL_KEYS = ("denoise", "lora")
_MASKED_REDRAW_DIAL_KEYS = ("denoise",)


def dials_scope(recipe: str, scope: str) -> Mapping[str, Mapping[str, float]]:
    return _RECIPE_DIALS.get(recipe, {}).get(scope, {})


def resolve_dial(key: str, value: object,
                  dials: Mapping[str, Mapping[str, float]]) -> object:
    """A string option value is looked up in `dials[key]`; every other value
    (a number, `true`, `null`) passes through for the option's own checks.
    """
    if not isinstance(value, str):
        return value
    words = dials.get(key) or {}
    if value not in words:
        raise ValueError(f"unknown {key} word: {value!r}")
    return words[value]


def _resolved_options(options: Mapping, arguments: Mapping,
                      dial_keys: tuple[str, ...]) -> dict:
    """The request's own options, with each dial-eligible key's value
    replaced by what `finalize_arguments()`/`repair_arguments()`/
    `masked_redraw_arguments()` actually resolved it to in `arguments` --
    the single source of truth for what the request ran with, rather than a
    second independent word/`true` resolution that could drift from it.
    """
    return {key: (arguments[key] if key in dial_keys else value)
           for key, value in options.items()}


# Shared by `finalize_arguments`' `repair`/`repair_*` options and
# `repair_arguments`' own -- both validate the same reroll geometry, just
# under different option names and defaults.
def _parts_argument(value: object, *, key: str = "parts") -> list[str]:
    if (not isinstance(value, list)
            or any(not isinstance(part, str) for part in value)):
        raise ValueError(f"{key} must be a list of strings, got {value!r}")
    invalid = sorted(set(value) - _REPAIR_PARTS)
    if invalid:
        raise ValueError(f"unknown {key}: {invalid}")
    return value


def _regions_argument(value: object, *, key: str = "regions") -> list[list[float]]:
    if not isinstance(value, list):
        raise ValueError(f"{key} must be an array, got {type(value).__name__}")
    parsed = []
    for region in value:
        if (not isinstance(region, list) or len(region) != 4
                or any(not isinstance(v, (int, float)) or isinstance(v, bool)
                       for v in region)):
            raise ValueError(
                f"each region must be [x0, y0, x1, y1] numbers, got {region!r}")
        if any(not (0 <= v <= 1) for v in region):
            raise ValueError(f"region values must be within 0..1, got {region!r}")
        parsed.append([float(v) for v in region])
    return parsed


def _denoise_argument(value: object, *, key: str = "denoise", max_value: float = 1) -> float:
    if not (isinstance(value, (int, float)) and not isinstance(value, bool)):
        raise ValueError(f"{key} must be a number, got {type(value).__name__}")
    if not (0 < value <= max_value):
        raise ValueError(f"{key} must be > 0 and <= {max_value}, got {value!r}")
    return float(value)


def _pixel_argument(value: object, *, key: str, max_value: float) -> float:
    if not (isinstance(value, (int, float)) and not isinstance(value, bool)):
        raise ValueError(f"{key} must be a number, got {type(value).__name__}")
    if not (0 <= value <= max_value):
        raise ValueError(f"{key} must be between 0 and {max_value}, got {value!r}")
    return float(value)


def _pad_argument(value: object, *, key: str = "pad") -> float:
    if not (isinstance(value, (int, float)) and not isinstance(value, bool)):
        raise ValueError(f"{key} must be a number, got {type(value).__name__}")
    if not (0.5 <= value <= 3):
        raise ValueError(f"{key} must be between 0.5 and 3, got {value!r}")
    return float(value)


def _keep_strength_argument(value: object, *, key: str = "keep_strength") -> float:
    if not (isinstance(value, (int, float)) and not isinstance(value, bool)):
        raise ValueError(f"{key} must be a number, got {type(value).__name__}")
    if not (0 < value < 1):
        raise ValueError(f"{key} must be > 0 and < 1, got {value!r}")
    return float(value)


def _crop_size_argument(value: object, *, key: str = "size") -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer, got {type(value).__name__}")
    if value < 256 or value % 8 != 0:
        raise ValueError(f"{key} must be a multiple of 8, at least 256, got {value!r}")
    return value


def _repair_seeds_argument(value: object, *, key: str = "repair_seeds") -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer, got {type(value).__name__}")
    if not (1 <= value <= 8):
        raise ValueError(f"{key} must be between 1 and 8, got {value!r}")
    return value


# Shared by `finalize_arguments`'s `repair_lora` and `repair_arguments`'s own
# `lora` -- both select the part-LoRA weight the reroll's `LoraLoader` chain
# runs at.
def _part_lora_argument(value: object, *, key: str = "lora") -> float | None:
    if value is True:
        return DEFAULT_PART_LORA_WEIGHT
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not (0 < value <= 2):
            raise ValueError(f"{key} must be > 0 and <= 2, got {value!r}")
        return float(value)
    raise ValueError(
        f"{key} must be null, true or a number, got {type(value).__name__}")


def _model_argument(value: object, *, key: str = "model") -> str | None:
    if value is None:
        return None
    if value not in MODELS:
        valid = ", ".join(repr(word) for word in sorted(MODELS))
        raise ValueError(f"{key} must be null or one of {valid}, got {value!r}")
    return value


def _control_argument(value: object, *, key: str = "control") -> str | None:
    if value is None:
        return None
    if value not in CONTROL_MODELS:
        valid = ", ".join(repr(word) for word in sorted(CONTROL_MODELS))
        raise ValueError(f"{key} must be null or one of {valid}, got {value!r}")
    return value


def _control_strength_argument(value: object, *,
                               key: str = "control_strength") -> float:
    if not (isinstance(value, (int, float)) and not isinstance(value, bool)):
        raise ValueError(f"{key} must be a number, got {type(value).__name__}")
    if not (0 < value <= 2):
        raise ValueError(f"{key} must be > 0 and <= 2, got {value!r}")
    return float(value)


def finalize_arguments(options: Mapping,
                       dials: Mapping[str, Mapping[str, float]] | None = None) -> dict:
    """Validate a finalize request's `options` and map it to finalize() kwargs.

    Every key in the return value is a finalize() kwarg. Missing keys mean
    false/null; unknown keys or a wrong type raise ValueError naming the
    offending key. `dials` is the source recipe's `dials.finalize`
    vocabulary (option key -> word -> number); a dial-eligible key given a
    word absent there raises the same way.
    """
    if not isinstance(options, Mapping):
        raise ValueError(
            f"finalize options must be an object, got {type(options).__name__}")
    unknown = sorted(set(options) - _KNOWN_FINALIZE_OPTIONS)
    if unknown:
        raise ValueError(f"finalize が受け付けない option です: {', '.join(unknown)}")
    dials = dials or {}

    def boolean(key: str) -> bool:
        value = options.get(key, False)
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be a boolean, got {type(value).__name__}")
        return value

    def defaultable_boolean(key: str) -> bool | object:
        if key not in options:
            return RECIPE_DEFAULT
        value = options[key]
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be a boolean, got {type(value).__name__}")
        return value

    def number(key: str) -> float | int | None:
        value = resolve_dial(key, options.get(key), dials)
        if value is None or (isinstance(value, (int, float))
                             and not isinstance(value, bool)):
            return value
        raise ValueError(f"{key} must be null or a number, got {type(value).__name__}")

    denoise = number("denoise")

    keep_legwear = resolve_dial("keep_legwear", options.get("keep_legwear"), dials)
    if keep_legwear is True:
        keep_legwear = 0.62
    elif keep_legwear is not None and not (
            isinstance(keep_legwear, (int, float)) and not isinstance(keep_legwear, bool)):
        raise ValueError(
            "keep_legwear must be null, true or a number, got "
            f"{type(keep_legwear).__name__}")

    route = options.get("route")
    if route is None:
        latent_route = None
    elif route == "latent":
        latent_route = True
    elif route == "pixel":
        latent_route = False
    else:
        raise ValueError(f"route must be null, 'latent' or 'pixel', got {route!r}")

    finalizer = options.get("finalizer")
    if finalizer is not None and not isinstance(finalizer, str):
        raise ValueError(f"finalizer must be null or a string, got {type(finalizer).__name__}")

    size = options.get("size")
    if size is not None and not (isinstance(size, int) and not isinstance(size, bool)):
        raise ValueError(f"size must be null or an integer, got {type(size).__name__}")

    deliver_size = options.get("deliver_size")
    if deliver_size is not None and not (
            isinstance(deliver_size, int) and not isinstance(deliver_size, bool)):
        raise ValueError(
            f"deliver_size must be null or an integer, got {type(deliver_size).__name__}")
    if deliver_size is not None and deliver_size < 1:
        raise ValueError(f"deliver_size must be at least 1, got {deliver_size!r}")

    transparent = options.get("transparent")
    if transparent is not None and not isinstance(transparent, bool):
        raise ValueError(
            f"transparent must be null or a boolean, got {type(transparent).__name__}")

    if "backdrop" not in options:
        backdrop = RECIPE_DEFAULT
    else:
        backdrop = options["backdrop"]
        if backdrop is not None:
            if not isinstance(backdrop, str):
                raise ValueError(
                    f"backdrop must be null or a string, got {type(backdrop).__name__}")
            if not is_backdrop(backdrop):
                names = ", ".join(repr(key) for key in sorted(PATTERNS))
                raise ValueError(
                    f"backdrop must be null, a #RRGGBB colour or one of {names}, "
                    f"got {backdrop!r}")

    upscale = options.get("upscale")
    if upscale is not None and upscale not in (
            "bicubic", "nearest-exact", "bilinear", "lanczos"):
        raise ValueError(
            "upscale must be null, 'bicubic', 'nearest-exact', 'bilinear' or "
            f"'lanczos', got {upscale!r}")

    if "stroke_light" not in options:
        stroke_light = RECIPE_DEFAULT
    else:
        stroke_light = options["stroke_light"]
        if stroke_light is not None and stroke_light not in STROKE_LIGHTS:
            valid = ", ".join(repr(key) for key in sorted(STROKE_LIGHTS))
            raise ValueError(
                f"stroke_light must be null or one of {valid}, got {stroke_light!r}")

    repair_raw = options.get("repair")
    repair = (None if repair_raw is None
             else _parts_argument(repair_raw, key="repair"))
    repair_regions = _regions_argument(
        options.get("repair_regions", []), key="repair_regions")
    repair_denoise = _denoise_argument(
        resolve_dial("repair_denoise", options.get("repair_denoise", 0.6), dials),
        key="repair_denoise")
    repair_pad = _pad_argument(options.get("repair_pad", 1.0), key="repair_pad")
    # `None` (an absent key) reaches finalize() as its own "caller omitted
    # this" sentinel, which on the deliver_only + repair_seeds path resolves
    # to 1536/1024 by the picked picture's own size rather than a fixed 1024.
    repair_size = (_crop_size_argument(options["repair_size"], key="repair_size")
                  if "repair_size" in options else None)
    repair_lora = _part_lora_argument(
        resolve_dial("repair_lora", options.get("repair_lora"), dials),
        key="repair_lora")
    repair_seeds = (_repair_seeds_argument(options["repair_seeds"], key="repair_seeds")
                    if "repair_seeds" in options else None)
    keep_regions = _regions_argument(
        options.get("keep_regions", []), key="keep_regions")
    keep_strength = _keep_strength_argument(options.get("keep_strength", 0.25))

    return {
        "denoise": float(denoise) if denoise is not None else None,
        "apply_repin": defaultable_boolean("repin"),
        "apply_skin": boolean("skin"),
        "apply_recolor": boolean("recolor"),
        "keep_legwear": float(keep_legwear) if keep_legwear is not None else None,
        "size": size,
        "deliver_size": deliver_size,
        "latent_route": latent_route,
        "finalizer": finalizer,
        "keep_scene": boolean("keep_scene"),
        "transparent": transparent,
        "backdrop": backdrop,
        "upscale": upscale,
        "stroke_light": stroke_light,
        "repair": repair,
        "repair_regions": repair_regions,
        "repair_denoise": repair_denoise,
        "repair_pad": repair_pad,
        "repair_size": repair_size,
        "repair_lora": repair_lora,
        "repair_seeds": repair_seeds,
        "keep_regions": keep_regions,
        "keep_strength": keep_strength,
        "deliver_only": defaultable_boolean("deliver_only"),
    }


def repair_arguments(options: Mapping,
                     dials: Mapping[str, Mapping[str, float]] | None = None) -> dict:
    """Validate a repair request's `options` and map it to repair() kwargs.

    Every key in the return value is a repair() kwarg; unknown keys or a
    wrong type raise ValueError naming the offending key. `dials` is the
    source recipe's `dials.repair` vocabulary (option key -> word -> number).
    """
    if not isinstance(options, Mapping):
        raise ValueError(
            f"repair options must be an object, got {type(options).__name__}")
    unknown = sorted(set(options) - _KNOWN_REPAIR_OPTIONS)
    if unknown:
        raise ValueError(f"unknown repair options keys: {unknown}")
    dials = dials or {}

    parts = _parts_argument(options.get("parts", ["hands", "feet"]))
    parsed_regions = _regions_argument(options.get("regions", []))

    if not parts and not parsed_regions:
        raise ValueError("repair needs at least one of parts or regions")

    denoise = _denoise_argument(
        resolve_dial("denoise", options.get("denoise", 0.6), dials))

    seeds = options.get("seeds", [1, 2, 3, 4])
    if (not isinstance(seeds, list) or not seeds
            or any(not isinstance(seed, int) or isinstance(seed, bool)
                   for seed in seeds)):
        raise ValueError(f"seeds must be a non-empty array of integers, got {seeds!r}")

    size = _crop_size_argument(options.get("size", 1024))
    pad = _pad_argument(options.get("pad", 1.0))
    lora = _part_lora_argument(resolve_dial("lora", options.get("lora"), dials))
    model = _model_argument(options.get("model"))
    control = _control_argument(options.get("control"))
    control_strength = _control_strength_argument(
        options.get("control_strength", DEFAULT_CONTROL_STRENGTH))

    return {
        "parts": parts, "regions": parsed_regions, "denoise": denoise,
        "seeds": seeds, "size": size, "pad": pad, "lora": lora, "model": model,
        "control": control, "control_strength": control_strength,
    }


def masked_redraw_arguments(options: Mapping,
                            dials: Mapping[str, Mapping[str, float]] | None = None) -> dict:
    """Validate a masked_redraw request's `options` and map it to
    masked_redraw() kwargs.

    Every key in the return value is a masked_redraw() kwarg; unknown keys or
    a wrong type raise ValueError naming the offending key. `dials` is the
    source recipe's `dials.repair` vocabulary -- masked_redraw's own
    `denoise` shares repair's, rather than defining its own.
    """
    if not isinstance(options, Mapping):
        raise ValueError(
            f"masked_redraw options must be an object, got {type(options).__name__}")
    unknown = sorted(set(options) - _KNOWN_MASKED_REDRAW_OPTIONS)
    if unknown:
        raise ValueError(f"unknown masked_redraw options keys: {unknown}")
    dials = dials or {}

    regions = _regions_argument(options.get("regions", []))
    if not regions:
        raise ValueError("masked_redraw needs at least one region")

    prompt_patch = options.get("prompt_patch")
    if not isinstance(prompt_patch, str) or not prompt_patch:
        raise ValueError(
            f"prompt_patch must be a non-empty string, got {prompt_patch!r}")
    if len(prompt_patch) > _MASKED_REDRAW_PROMPT_PATCH_MAX_LENGTH:
        raise ValueError(
            "prompt_patch must be at most "
            f"{_MASKED_REDRAW_PROMPT_PATCH_MAX_LENGTH} characters, got {len(prompt_patch)}")

    denoise = _denoise_argument(
        resolve_dial("denoise", options.get("denoise", 0.45), dials), max_value=0.75)
    mask_padding = _pixel_argument(
        options.get("mask_padding", 0), key="mask_padding", max_value=512)
    mask_feather = _pixel_argument(
        options.get("mask_feather", 32), key="mask_feather", max_value=256)
    size = _crop_size_argument(options.get("size", 1024))

    seeds = options.get("seeds", [1, 2, 3, 4])
    if (not isinstance(seeds, list) or not seeds
            or any(not isinstance(seed, int) or isinstance(seed, bool)
                   for seed in seeds)):
        raise ValueError(f"seeds must be a non-empty array of integers, got {seeds!r}")
    if len(seeds) > _MASKED_REDRAW_SEEDS_MAX:
        raise ValueError(
            f"seeds must have at most {_MASKED_REDRAW_SEEDS_MAX} entries, got {len(seeds)}")

    return {
        "regions": regions, "prompt_patch": prompt_patch, "denoise": denoise,
        "mask_padding": mask_padding, "mask_feather": mask_feather, "size": size,
        "seeds": seeds,
    }
