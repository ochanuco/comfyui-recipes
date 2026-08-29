#!/usr/bin/env python3
"""Make a render bigger without letting the model touch it.

`--hires` in yukari_recipe.py is not an upscale, it is a second pass: the latent
is stretched and then REDRAWN at denoise 0.60, which is why it can add detail
and why it can also change what is there. When a render has already been picked
and the only thing wanted is more pixels, this is the other tool -- a plain
resample, no diffusion, no model.

    uv run scripts/analysis/upscale_plain.py out/pick.png --size 2048
    uv run scripts/analysis/upscale_plain.py out/pick.png --size 3072 --filter bicubic

**It adds nothing.** There is no detail in the output that was not in the input,
and that is the point rather than a caveat: the drawing that was approved is the
drawing that comes out. What it does do, measurably, is take the aliasing off --
resampling lands the edge between pixels instead of on one, so single-pixel
stair steps stop being single-pixel stair steps. Measured going 1536 -> 2048 on
the `pounce` print:

    rows whose edge is a hard step, no partial pixel at all
        1536 source        10.9%
        2048 resampled      0.9%
        3072 resampled      0.0%
    staircase run length   2.2 both before and after, i.e. not made worse

lanczos and bicubic measured identically on that render (AA width 1.69 against
1.71, hard-step 0.9% against 0.6%); lanczos is the default because it is the
sharper of the two by construction and nothing here contradicted that.

**There is no upscale MODEL on the worker.** `UpscaleModelLoader` reports an
empty options list, the same way `LoraLoader` does, so ESRGAN-family upscalers
-- which would add plausible detail rather than none -- are not available to
this repo until something is installed there. That is why this script is a
resampler and not a graph.

Recolour AFTER this, not before: `recolor_bg.py`'s feathered edge should be
computed on the pixel grid the picture is delivered at. feather 2 was checked at
both 2048 and 3072 here (1px fringe 5.5% and 3.2% still old hue, no genuine skin
moved); feather 3 at 3072 buys no fringe and starts moving skin.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

FILTERS = {"lanczos": Image.LANCZOS, "bicubic": Image.BICUBIC,
           "nearest": Image.NEAREST}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+", type=Path)
    ap.add_argument("--size", type=int, required=True,
                    help="length of the longest side in the output")
    ap.add_argument("--filter", choices=sorted(FILTERS), default="lanczos")
    ap.add_argument("--suffix", default="-big")
    ap.add_argument("--outdir", type=Path)
    args = ap.parse_args()

    for path in args.images:
        img = Image.open(path).convert("RGB")
        longest = max(img.size)
        if args.size <= longest:
            print(f"{path.name}: already {img.size[0]}x{img.size[1]}, skipping")
            continue
        scale = args.size / longest
        # Rounded to 8, matching the latent grid every other size in this repo
        # sits on. Nothing here needs it; it keeps the numbers comparable.
        size = (round(img.size[0] * scale / 8) * 8, round(img.size[1] * scale / 8) * 8)
        out_img = img.resize(size, FILTERS[args.filter])
        outdir = args.outdir or path.parent
        outdir.mkdir(parents=True, exist_ok=True)
        out = outdir / f"{path.stem}{args.suffix}{path.suffix}"
        out_img.save(out)
        print(f"{path.name}: {img.size[0]}x{img.size[1]} -> {size[0]}x{size[1]} "
              f"({args.filter}) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
