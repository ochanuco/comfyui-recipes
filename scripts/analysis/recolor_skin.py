#!/usr/bin/env python3
"""Turn a bare region of skin into legwear, keeping the drawing that is on it.

`prone` needs tights under knee-highs and the model will not draw both (see the
splice in yukari_recipe.py). It will draw the socks, and it draws the thigh
above them as bare skin -- correctly shaped, correctly shaded, wrong garment.
That is the case render-notes already settled once, on a thigh that came out
warm-taupe: **recolour a wrong-coloured but well-shaped mass before re-rolling
it.** This is that operation, as a tool.

    uv run scripts/analysis/recolor_skin.py in.png --box 1400 500 1900 950 \
        --color '#d8c8ee' --out out.png

Method, and why each half is there:

- The skin is selected by colour, not by a hand-drawn mask, so the sock edge,
  the hem and the outline cut the selection exactly where they cut the drawing.
  The reference tone is the modal colour inside the box, which on a flat-colour
  render is the skin fill itself.
- Shading is kept as an offset from that tone: `(p - ref) * contrast + target`.
  Pasting the target flat would delete the modelling, and this render has very
  little of it to spare.
- Line art is protected by luminance. Anything darker than `--line-max` is left
  exactly as it was, so contours, creases and the sock's own edge survive a
  recolour that runs underneath them.
- The selection is feathered by one pixel before compositing. Without it the
  boundary against the outline aliases, which on a die-cut style reads as a
  second, thinner line.

The result is a paste, and it looks like one under a loupe. Send it back through
`queue_refine.py --mask` at 0.3 to have it drawn.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def modal(pixels: np.ndarray) -> np.ndarray:
    """Modal colour of an Nx3 array at 16-level resolution, then refined."""
    coarse = (pixels.astype(np.uint8) >> 4) << 4
    buckets, counts = np.unique(coarse, axis=0, return_counts=True)
    top = buckets[counts.argmax()]
    hit = (np.abs(pixels.astype(np.int16) - top) < 24).all(axis=1)
    return pixels[hit].mean(axis=0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", type=Path)
    ap.add_argument("--box", type=int, nargs=4, required=True,
                    metavar=("X0", "Y0", "X1", "Y1"))
    ap.add_argument("--color", required=True, help="target fill, #rrggbb")
    ap.add_argument("--from-color", help="reference tone, #rrggbb; default is the "
                                         "modal colour inside the box")
    ap.add_argument("--tolerance", type=float, default=28.0,
                    help="max per-channel distance from the reference tone")
    ap.add_argument("--contrast", type=float, default=1.0,
                    help="scale on the shading kept from the original")
    ap.add_argument("--line-max", type=int, default=150,
                    help="pixels darker than this are line art and are untouched")
    ap.add_argument("--out", type=Path, required=True)
    # The refine that follows has to be told where the paste is, and only this
    # step knows: the selection is by colour, so its shape is not a rectangle
    # anyone could type. Written full-frame so it lines up with --out.
    ap.add_argument("--mask-out", type=Path,
                    help="white where pixels were repainted, for queue_refine --mask")
    args = ap.parse_args()

    img = cv2.imread(str(args.image)).astype(np.float32)
    x0, y0, x1, y1 = args.box
    region = img[y0:y1, x0:x1]

    def rgb(text: str) -> np.ndarray:
        text = text.lstrip("#")
        return np.array([int(text[i:i + 2], 16) for i in (4, 2, 0)], np.float32)

    target = rgb(args.color)
    ref = rgb(args.from_color) if args.from_color else modal(region.reshape(-1, 3))

    dist = np.abs(region - ref).max(axis=2)
    luma = region.mean(axis=2)
    hit = ((dist < args.tolerance) & (luma > args.line_max)).astype(np.uint8)
    # Opened before it is used. The die-cut white outline is 2/15/24 away from
    # skin -- outside the tolerance -- but the antialiased pixels along its edge
    # pass through every value in between, so a raw selection speckles the
    # outline with repainted dots. One 3x3 opening removes every speck and takes
    # a pixel off nothing that is a garment.
    hit = cv2.morphologyEx(hit, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    sel = cv2.GaussianBlur(hit.astype(np.float32), (0, 0), 1.0)[..., None]

    painted = (region - ref) * args.contrast + target
    img[y0:y1, x0:x1] = region * (1 - sel) + painted * sel
    cv2.imwrite(str(args.out), img.clip(0, 255).astype(np.uint8))

    if args.mask_out:
        mask = np.zeros(img.shape[:2], np.float32)
        mask[y0:y1, x0:x1] = sel[..., 0]
        # Dilated, because the refine has to be allowed to work across the edge
        # of the paste -- that edge is the seam it exists to remove.
        mask = cv2.dilate((mask > 0.5).astype(np.uint8) * 255,
                          np.ones((9, 9), np.uint8))
        cv2.imwrite(str(args.mask_out), cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR))

    covered = float(sel.mean())
    print(f"{args.out.name}: ref {ref[::-1].round(0)} -> {target[::-1].round(0)}, "
          f"{covered:.1%} of the box repainted")


if __name__ == "__main__":
    main()
