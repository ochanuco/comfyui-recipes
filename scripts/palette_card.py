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
    FIGURE_MIDTONE_V, FIGURE_SAT_MEAN_MAX, FIGURE_SAT_P90_MAX,
    PALETTE_WINDOWS, SAT_BAND, STROKE,
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
         f"(V>={FIGURE_LIGHT_V}; drift indicator)", "light"),
        (f"midtone gate mean<={FIGURE_SAT_MEAN_MAX:.0f} p90<={FIGURE_SAT_P90_MAX:.0f}  "
         f"(V>={FIGURE_MIDTONE_V})", "mid"),
        (f"frame mean {SAT_BAND[0]:.0f}-{SAT_BAND[1]:.0f}   "
         f"backdrop sat<={BG_SAT_MAX:.0f}", None),
        ("material windows (repin targets; chips: hue at light/mid sat)", None),
    ]
    for w in PALETTE_WINDOWS:
        hue = w["hue_target"] if w["hue_target"] is not None else sum(w["hue"]) / 2
        rows.append((f"{w['name']}  H {w['hue'][0]:.0f}-{w['hue'][1]:.0f}"
                     + (f" ->{w['hue_target']:.0f}" if w["hue_target"] else "")
                     + f"  S light {w['sat_light']:.0f} / mid {w['sat_mid']:.0f}",
                     ("window", hue, w["sat_light"], w["sat_mid"])))
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
        elif isinstance(spec, tuple) and spec[0] == "window":
            _, hue, s_light, s_mid = spec
            d.rectangle([PAD, y, PAD + CHIP, y + CHIP // 2],
                        fill=hsv_chip(int(s_light), 200, int(hue)),
                        outline="#222222")
            d.rectangle([PAD + CHIP + 8, y, PAD + 2 * CHIP + 8, y + CHIP // 2],
                        fill=hsv_chip(int(s_mid), 115, int(hue)),
                        outline="#222222")
            d.text((PAD + 2 * CHIP + 22, y + CHIP // 4 - 6), label,
                   fill="#222222")
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
