#!/usr/bin/env python3
"""Stroke width inside a mask against the same picture outside it.

`scripts/analysis/stroke_width.py` measures a whole canvas, which cannot answer 「脚だけ線が太い」
-- a masked refine only redraws its own region, so the complaint is about the
difference between two halves of one image, not between two images. Same
statistic as the tool (mean dark-run length, runs over --max-run dropped as
fills), applied twice: once to the pixels the mask covers and once to the rest.

    uv run scripts/analysis/stroke_region.py <mask.png> <render.png> [more.png ...]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from stroke_width import runs

THRESHOLD, MAX_RUN = 110, 16

mask = np.asarray(Image.open(sys.argv[1]).convert("L")) > 127

print(f"{'file':<30} {'in-mask':>9} {'outside':>9} {'ratio':>7}")
for p in sys.argv[2:]:
    im = Image.open(p).convert("L")
    grey = np.asarray(im)
    line = grey < THRESHOLD
    longest = max(im.size)
    # Zeroing the other region before collecting runs, so a run never spans the
    # boundary and gets counted for the side it does not belong to.
    a = runs(line & mask, MAX_RUN)
    b = runs(line & ~mask, MAX_RUN)
    ia = a.mean() * 1000 / longest
    ob = b.mean() * 1000 / longest
    print(f"{Path(p).name:<30} {ia:>9.3f} {ob:>9.3f} {ia / ob:>7.2f}x")
