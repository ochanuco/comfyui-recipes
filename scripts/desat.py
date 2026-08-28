#!/usr/bin/env python3
"""Take saturation out, without touching the gradient.

Six prompt attempts could not lower the purple end of the tights -- (muted
colors)+(desaturated) doubled it, (dusty purple) raised it, a vividness guard
left the mean flat and pushed the peak up. That is the shape the notes name:
when the tag that describes the defect does nothing at any weight, the defect is
implied by something else. Here it is the palette itself -- the dress and hair
are pale purple and the tights' upper end is being pulled toward them.

So do it in HSV afterwards, where it is exact. Saturation is scaled and nothing
else: value and hue are untouched, so the purple-to-black run down the leg keeps
its shape, and the lineart keeps its weight.

The factor is not this tool's to choose (recolor_bg's --color rule): the
delivered identity's per-pose factors live in
`yukari.delivery_style.POSE_DESAT`.

    uv run scripts/desat.py <in.png> <out.png> <factor>
"""
import sys

import numpy as np
from PIL import Image

im = Image.open(sys.argv[1]).convert("RGB")
f = float(sys.argv[3])
hsv = np.asarray(im.convert("HSV")).astype(np.float32)
hsv[..., 1] *= f
out = Image.fromarray(hsv.clip(0, 255).astype(np.uint8), "HSV").convert("RGB")
out.save(sys.argv[2])

a = np.asarray(im).astype(int)
bg = np.median(a[:24, :24].reshape(-1, 3), axis=0)
fig = np.abs(a - bg).max(axis=2) > 18
for lab, img in (("before", im), ("after", out)):
    s = np.asarray(img.convert("HSV")).astype(int)[..., 1][fig]
    print(f"{lab:>6}: figure sat mean {s.mean():5.1f}  p90 {np.percentile(s,90):5.0f}"
          f"  >60 {(s>60).mean():5.2%}")
