"""Named words for yukari's finalize options, published in the catalog."""

from __future__ import annotations

from .delivery_style import FINALIZE_DENOISE

DIALS = {
    "finalize": {
        "denoise": {"keep": FINALIZE_DENOISE},
    },
    "patches": {
        "render.width": {"draft": 1024, "full": 1280},
        "render.height": {"draft": 1640, "full": 2048},
    },
}
