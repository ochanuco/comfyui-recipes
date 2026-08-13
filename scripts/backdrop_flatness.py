#!/usr/bin/env python3
"""Screen renders by how flat their backdrop is, before trying to recolour it.

scripts/recolor_bg.py repaints the flat area reachable from the border. When the
backdrop is not actually flat -- streaked, mottled, painted in bands -- it either
refuses ("only 1.6% matched") or, if the tolerance is widened to make it bite,
eats into the figure: at --tolerance 40 one render went to 45.9% repainted, which
is most of the white outline and the pale socks.

So the flatness is worth knowing before reaching for the tool. It is mostly a
property of the seed:

    seed 1886970040   std 15.2 - 19.9   across coy, yawn and both invite registers
    seed 555666777    std 34.2 - 42.9   across peace and invite both
    seed 111222333    std 26.4 - 40.7
    seed 3409564303   std 38.5 - 47.4

but not only -- 737373737 came out 19.2 on one register and 27.2 on another, so
the prompt moves it too. Screen the actual render rather than trusting the seed.

Under about 25 recolor_bg at its default tolerance does the right thing. Above
that, re-roll: there is no prompt-side fix, the backdrop has never responded to
tags. And 25 is permissive -- a render at 19 can still come out of recolor_bg
with visible patches, because the mottle that survives is the part inside the
tolerance. Look at the result.

    uv run scripts/backdrop_flatness.py out/fin-*.png

Measured on the top 4.5% of rows, full width, which is backdrop in every
composition this repo produces. A render framed differently needs a different
strip, and the number is greyscale standard deviation, so it says nothing about
which colour the backdrop is -- only whether it is one colour.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2

FLAT_ENOUGH = 25.0


def flatness(path: Path, band: float = 0.045) -> tuple[float, float]:
    image = cv2.imread(str(path))
    if image is None:
        raise SystemExit(f"cannot read {path}")
    height = image.shape[0]
    strip = cv2.cvtColor(image[: int(band * height), :], cv2.COLOR_BGR2GRAY)
    return float(strip.std()), float(strip.mean())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--band", type=float, default=0.045,
                        help="fraction of the height sampled from the top edge")
    parser.add_argument("--threshold", type=float, default=FLAT_ENOUGH)
    args = parser.parse_args()

    for path in args.images:
        std, mean = flatness(path, args.band)
        verdict = "flat" if std <= args.threshold else "MOTTLED"
        print(f"{path.name:44} std {std:6.2f}  mean {mean:6.1f}  {verdict}")


if __name__ == "__main__":
    main()
