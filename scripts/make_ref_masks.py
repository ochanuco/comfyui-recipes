#!/usr/bin/env python3
"""Write the attention masks that queue_dq3.py's --ref-mask options expect.

IPAdapter applied to the whole frame repaints the outfit and the background in
the reference's colours, so the reference is confined to the head and the legs.
The masks live under .local/ComfyUI/input, which is not tracked, hence this
script: without it a fresh checkout cannot reproduce a --ref-mask run.

Bounds assume the default 832x1216 standing framing. Pass --width/--height and
the band options if you generate at another size or pose.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / ".local/ComfyUI/input",
    )
    parser.add_argument("--width", type=int, default=832)
    parser.add_argument("--height", type=int, default=1216)
    # Horizontal bounds matter as much as vertical ones: a full-width band
    # styles the background too, which came out as a pink swirl.
    parser.add_argument("--head-box", type=int, nargs=4, default=[230, 610, 0, 290],
                        metavar=("X0", "X1", "Y0", "Y1"))
    # Y1 stops above the boots so they keep the outfit's yellow.
    parser.add_argument("--legs-box", type=int, nargs=4, default=[210, 640, 640, 1000],
                        metavar=("X0", "X1", "Y0", "Y1"))
    parser.add_argument("--feather", type=int, default=90)
    return parser.parse_args()


def ramp(size: int, lo: int, hi: int, feather: int) -> np.ndarray:
    """1.0 inside [lo, hi), fading to 0 over `feather` px beyond each edge."""
    values = np.zeros(size, dtype=np.float32)
    values[max(lo, 0):min(hi, size)] = 1.0
    for offset in range(feather):
        level = 1.0 - offset / feather
        if lo - 1 - offset >= 0:
            values[lo - 1 - offset] = level
        if hi + offset < size:
            values[hi + offset] = level
    return values


def write_mask(path: Path, box: list[int], width: int, height: int, feather: int) -> None:
    x0, x1, y0, y1 = box
    field = np.outer(ramp(height, y0, y1, feather), ramp(width, x0, x1, feather))
    # ImageToMask reads a channel off an IMAGE, so save RGB rather than L.
    Image.fromarray((field * 255).astype(np.uint8), "L").convert("RGB").save(path)
    print(f"wrote {path}")


def main() -> int:
    args = parse_args()
    args.input_dir.mkdir(parents=True, exist_ok=True)
    write_mask(args.input_dir / "mask-head.png", args.head_box,
               args.width, args.height, args.feather)
    write_mask(args.input_dir / "mask-legs.png", args.legs_box,
               args.width, args.height, args.feather)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
