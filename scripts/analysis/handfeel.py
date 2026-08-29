#!/usr/bin/env python3
"""Is the hand in the line a number? One candidate, tested against known cases.

Four statistics failed at this today. Stroke-width spread could not separate
drawn from vector (0.87-0.98 across renders anyone can tell apart). Runs per
megapixel INVERTED, because a smaller canvas spends fewer pixels per line and so
counts more of them. Ink fraction is dominated by whatever garment happens to be
black. A fixed sampling box measures whatever the composition has moved under it.

What those failures agree on: the measure has to be scale-free, pinned to the
figure rather than to a box, and about the INSIDE of shapes -- the drawn quality
showed up as strokes within flat areas (hair strands, fold hatching), not as
contours, which both kinds of render have.

So: count the marks that lie in the interior, and normalise by the figure's
size rather than the canvas's.

**It does not survive a change of canvas.** Same seed, same prompt, 1024 reads
36.9 and 2048 reads 127.9 -- normalising by the figure's height does not absorb
it, because a line's width in pixels does not scale with the figure. Compare
renders at one size only.

    uv run scripts/analysis/handfeel.py <render.png> ...
"""
import sys

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage

print(f"{'render':<26} {'interior marks':>14} {'per 1k fig-h':>13} {'fig h':>7}")
for path in sys.argv[1:]:
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(int)
    bg = np.median(a[:24, :24].reshape(-1, 3), axis=0)

    fig = np.abs(a - bg).max(axis=2) > 18
    fig = ndimage.binary_closing(fig, np.ones((9, 9)))
    fig = ndimage.binary_fill_holes(fig)
    lab, n = ndimage.label(fig)
    if n:
        sizes = ndimage.sum(fig, lab, range(1, n + 1))
        fig = lab == (1 + int(np.argmax(sizes)))

    # Everything within 12px of the silhouette is contour, which a vector-clean
    # render has just as much of. What separates the two is what is drawn inside.
    inner = cv2.erode(fig.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool)

    line = (np.asarray(im.convert("L")).astype(int) < 110) & inner
    # Count marks, not pixels: a long contour and a hundred short hatches differ
    # in number, and it is the number the eye reads as "drawn".
    mlab, marks = ndimage.label(line, structure=np.ones((3, 3)))
    if marks:
        sz = ndimage.sum(line, mlab, range(1, marks + 1))
        marks = int((sz >= 8).sum())          # drop single-pixel speckle

    ys = np.nonzero(fig.any(axis=1))[0]
    height = (ys.max() - ys.min()) if len(ys) else 1
    print(f"{path.split('/')[-1][:26]:<26} {marks:>14} "
          f"{marks * 1000 / height:>13.1f} {height:>7}")
