#!/usr/bin/env python3
"""Put a refined crop back into the print it was cut from.

The route the notes settle on for any local defect -- a hand, a thigh -- is:
crop a square at print resolution, Lanczos it up so the model draws that region
at a size it can draw, refine in place with `queue_refine.py --mask`, then paste
back. This is the paste.

    uv run scripts/analysis/paste_refined.py print.png refined-1024.png \\
        --box 1280 450 768 --mask recolour-mask.png --out fixed.png

`inpaint_composite.py` is NOT this tool and the difference is worth knowing.
That one exists for a masked region that contains BACKDROP: it extends the
surrounding backdrop across the mask by Laplace diffusion, because a denoise-1.0
redraw lands its own backdrop tone and no constant can match both edges. A
`SetLatentNoiseMask` refine keeps the old drawing under the noise, so its region
comes back on the original's own tones and all that is left is the VAE round
trip's nudge -- a constant, measured here on the ring just outside the mask and
subtracted. Regions that hold only figure (skin, cloth, sock) have no backdrop
for the other tool to act on at all.

Everything outside the box is byte-identical to the input, and inside the box
only the mask (feathered by 2px) is touched.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base", type=Path, help="the full-size print")
    ap.add_argument("refined", type=Path, help="what the refine returned, any size")
    ap.add_argument("--box", type=int, nargs=3, required=True, metavar=("X0", "Y0", "SIZE"),
                    help="the square that was cropped out of the print")
    ap.add_argument("--mask", type=Path,
                    help="full-frame, white where the refine may land. Without one "
                         "the whole box is pasted with a feathered border")
    ap.add_argument("--feather", type=float, default=2.0)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    x0, y0, size = args.box
    base = np.asarray(Image.open(args.base).convert("RGB"), np.float32)
    new = np.asarray(Image.open(args.refined).convert("RGB").resize(
        (size, size), Image.LANCZOS), np.float32)
    patch = base[y0:y0 + size, x0:x0 + size]

    if args.mask:
        mask = Image.open(args.mask).convert("L").crop((x0, y0, x0 + size, y0 + size))
    else:
        mask = Image.new("L", (size, size), 0)
        mask.paste(255, (8, 8, size - 8, size - 8))
    hard = np.asarray(mask, np.float32) > 127
    soft = np.asarray(mask.filter(ImageFilter.GaussianBlur(args.feather)),
                      np.float32)[..., None] / 255.0

    # The ring just outside the mask is the same drawing in both images, so what
    # differs there is the round trip and nothing else.
    ring = np.asarray(mask.filter(ImageFilter.MaxFilter(9)), np.float32) > 127
    ring &= ~hard
    offset = (np.median(patch[ring], 0) - np.median(new[ring], 0)) if ring.any() else 0.0
    print(f"ring offset {np.round(offset, 2)}")

    out = base.copy()
    out[y0:y0 + size, x0:x0 + size] = patch * (1 - soft) + (new + offset) * soft
    Image.fromarray(out.clip(0, 255).astype(np.uint8)).save(args.out)

    outside = out.copy()
    outside[y0:y0 + size, x0:x0 + size] = patch
    print(f"{args.out.name}: max change outside the box "
          f"{np.abs(outside - base).max():.0f}")


if __name__ == "__main__":
    main()
