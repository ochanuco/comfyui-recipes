"""Named words for yukari-sketch's finalize/repair/patch options, published
in the catalog.
"""

from __future__ import annotations

from ..repair.loras import DEFAULT_PART_LORA_WEIGHT
from ..yukari.recipe import TOE_GUARD
from .delivery_style import FINALIZE_DENOISE
from .prompt_style import LORA as SKETCH_LORA

# 0.65 redraws the line only; 0.8 also redraws held props and the
# expression on a full-body base (delivery_style.FINALIZE_DENOISE), which
# is why it is a named word rather than the default.
_REDRAW_DENOISE = 0.8
_TIDY_DENOISE = 0.65
_RAW_LORA_STRENGTH = 1.5
_REPAIR_DENOISE_KEEP = 0.6
_KEEP_LEGWEAR_CUT = 0.62

DIALS = {
    "finalize": {
        "denoise": {"keep": FINALIZE_DENOISE, "tidy": _TIDY_DENOISE,
                    "redraw": _REDRAW_DENOISE},
        "keep_legwear": {"on": _KEEP_LEGWEAR_CUT},
        "toe_guard": {"on": TOE_GUARD},
        "lora_strength": {"recipe": SKETCH_LORA[1], "raw": _RAW_LORA_STRENGTH},
        "repair_lora": {"on": DEFAULT_PART_LORA_WEIGHT},
        "repair_denoise": {"keep": _REPAIR_DENOISE_KEEP},
    },
    "repair": {
        "denoise": {"keep": _REPAIR_DENOISE_KEEP},
        "lora": {"on": DEFAULT_PART_LORA_WEIGHT},
    },
    "patches": {
        "render.lora_strength": {"recipe": SKETCH_LORA[1], "raw": _RAW_LORA_STRENGTH},
    },
}
