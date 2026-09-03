"""Yukari-anima's delivery policy: what the finalize redraw runs at."""

from __future__ import annotations

FINALIZE_SIZE = 2560
FINALIZE_DENOISE = 0.55
FINALIZE_MODEL = "hassaku-il-v22"
FINALIZE_SAMPLER = ("dpmpp_2m", "karras")
FINALIZE_STEPS = 30
FINALIZE_CFG = 5.0

# Replaces `STYLE`, the tail of the positive, for the redraw. `STYLE` is
# hassakuAnima's own flat/cel-shaded finish; the redraw is a different
# checkpoint aiming at a rough, unfinished line instead.
ROUGH_STYLE = ("(sketch:1.45), (rough sketch:1.4), rough lines, sketchy "
              "lines, pencil sketch, (unfinished:1.2), construction lines, "
              "(colored pencil (medium):1.2), (soft shading:1.1)")

ROUGH_BAN = ("(clean lineart:1.3), (smooth lines:1.2), (cel shading:1.2), "
            "(flat color:1.2), ")
PAINT_BAN = ("(brown legwear:1.5), (brown pantyhose:1.4), "
            "(detailed shading:1.5), (heavy shading:1.5), (impasto:1.45), "
            "(painterly:1.45), ")
