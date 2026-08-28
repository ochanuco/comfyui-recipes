#!/usr/bin/env python3
"""Render the delivered palette as one swatch card PNG.

The palette lives in `yukari/delivery_style.py` as numbers; this draws those
numbers so the eye and the tools judge against the same reference. Nothing
here is a value of its own -- edit delivery_style, re-render the card.

    uv run scripts/palette_card.py [out.png]
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

from yukari.delivery_style import (  # noqa: E402
    BACKDROP, BG_SAT_MAX, FIGURE_LIGHT_SAT_TARGET, FIGURE_LIGHT_V,
    FIGURE_MIDTONE_V, FIGURE_SAT_MEAN_MAX, FIGURE_SAT_P90_MAX, SAT_BAND,
    STROKE,
)

W, PAD, CHIP = 860, 24, 96


def hsv_chip(s: int, v: int = 200, h: int = 190) -> tuple[int, int, int]:
    return Image.new("HSV", (1, 1), (h, s, v)).convert("RGB").getpixel((0, 0))


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("palette-card.png")
    rows = [
        ("identity", None),
        (f"backdrop  {BACKDROP}", BACKDROP),
        (f"stroke    {STROKE}", STROKE),
        ("figure saturation (hue: the dress purple, for scale only)", None),
        (f"light band target {FIGURE_LIGHT_SAT_TARGET:.0f}  "
         f"(V>={FIGURE_LIGHT_V}; desat normalizes here)", "light"),
        (f"midtone gate mean<={FIGURE_SAT_MEAN_MAX:.0f} p90<={FIGURE_SAT_P90_MAX:.0f}  "
         f"(V>={FIGURE_MIDTONE_V})", "mid"),
        (f"frame mean {SAT_BAND[0]:.0f}-{SAT_BAND[1]:.0f}   "
         f"backdrop sat<={BG_SAT_MAX:.0f}", None),
    ]
    H = PAD + len(rows) * (CHIP // 2 + 18) + PAD
    im = Image.new("RGB", (W, H), "#ffffff")
    d = ImageDraw.Draw(im)
    y = PAD
    for label, spec in rows:
        if spec is None:
            d.text((PAD, y), label, fill="#222222")
            y += 26
            continue
        if isinstance(spec, str) and spec.startswith("#"):
            d.rectangle([PAD, y, PAD + CHIP, y + CHIP // 2], fill=spec,
                        outline="#222222")
            d.text((PAD + CHIP + 14, y + CHIP // 4 - 6), label, fill="#222222")
        else:
            # A saturation ruler 0..255 in the dress hue, with the markers
            # that delivery actually uses drawn on it.
            x0, x1 = PAD, W - PAD
            for x in range(x0, x1):
                s = int((x - x0) / (x1 - x0) * 255)
                d.line([x, y, x, y + CHIP // 2], fill=hsv_chip(s))
            marks = ([(FIGURE_LIGHT_SAT_TARGET, "#ffffff")] if spec == "light"
                     else [(FIGURE_SAT_MEAN_MAX, "#ffffff"),
                           (FIGURE_SAT_P90_MAX, "#222222")])
            for val, col in marks:
                x = int(x0 + val / 255 * (x1 - x0))
                d.line([x, y - 4, x, y + CHIP // 2 + 4], fill=col, width=3)
            d.rectangle([x0, y, x1, y + CHIP // 2], outline="#222222")
            d.text((x0, y + CHIP // 2 + 4), label, fill="#222222")
        y += CHIP // 2 + 18
    im.save(out)
    print(out)


if __name__ == "__main__":
    main()
