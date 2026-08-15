#!/usr/bin/env python3
"""Composite a denoise-1.0 inpaint back over its source without a visible seam.

For removing an object a render baked in (the mirror-ghost and plush on
sm2-crouch-111222333 were the first case): mask the region, redraw it with
VAEEncodeForInpaint, then run this to keep the redraw only inside the mask.

Everything here exists because the naive versions failed on that first case:

- VAEEncodeForInpaint needs denoise 1.0. It blanks the latent under the mask,
  so at 0.55/0.70/0.85 the masked region came back as a flat grey rectangle --
  there is nothing under the noise to denoise toward.
- The redraw cannot simply be pasted. Its backdrop lands on its own tone (~30
  levels darker here), and the original's backdrop is not one colour either
  (warm beige toward left and bottom, neutral at the top), so a constant shift
  cannot match both edges. The fix: extend the original's just-outside-the-mask
  backdrop across the masked region by Laplace diffusion (target T), take the
  low-frequency of the redraw's own backdrop (L), and add T - L to backdrop
  pixels only. Figure pixels inside the mask are left exactly as drawn.
- The band feeding T accepts darker-than-reference backdrop (the beige) but not
  brighter (the figure's white outline). A symmetric threshold excluded the
  beige and mismatched two edges.
- The sampler draws a faint seam line along the mask boundary. Edge strips
  where both sides read as backdrop are replaced by T.
- The blend feathers OUTWARD past the mask, never inward: inward feathering
  mixes the removed object's own pixels back in.
- Outside the feather ring the output is byte-identical to the original.
  (VAEEncodeForInpaint's round-trip nudges every pixel, so returning the
  sampler's output unmasked region is not equivalent.)

Prompt-side removal was tried first and is not available: adding the object
("stuffed animal, reflection") to the negative, weighted or not, rebuilt the
whole composition and in one case summoned a bigger plush. Seed-baked clutter
does not answer to the negative; it answers to redrawing.

    uv run scripts/inpaint_composite.py original.png inpainted.png mask.png \
        --out fixed.png

The mask is expected to be an axis-aligned rectangle (white = redraw); the
seam-line pass runs along its bounding box edges.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def dominant(pixels: np.ndarray) -> np.ndarray:
    """Modal colour of an Nx3 float array, at 16-level resolution."""
    coarse = (pixels.astype(np.uint8) >> 4) << 4
    buckets, counts = np.unique(coarse, axis=0, return_counts=True)
    top = buckets[counts.argmax()]
    hit = (np.abs(pixels - top) < 24).all(axis=1)
    return pixels[hit].mean(axis=0)


def laplace_extend(known: np.ndarray, values: np.ndarray, shape, scale=8, iters=4000):
    """Harmonic interpolation of `values` (defined where `known`) over the frame.

    Solved on a 1/`scale` grid. The interior must be initialised at the known
    mean: from zero, 4000 Jacobi sweeps do not converge and the field comes out
    dark (measured: interior stuck at ~108 of ~229).
    """
    h, w = shape
    hs, ws = h // scale, w // scale

    def down(x):
        return cv2.resize(x.astype(np.float32), (ws, hs), interpolation=cv2.INTER_AREA)

    kw = down(known.astype(np.float32))
    vals = np.dstack([down(values[..., c] * known) for c in range(3)])
    kd = kw > 0.15
    vals = vals / np.where(kw < 0.15, 1, kw)[..., None]
    field = np.full((hs, ws, 3), vals[kd].mean(0), np.float32)
    for _ in range(iters):
        field = np.where(kd[..., None], vals, cv2.blur(field, (3, 3)))
    return cv2.GaussianBlur(cv2.resize(field, (w, h)), (0, 0), 8)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("inpainted", type=Path)
    parser.add_argument("mask", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    orig = cv2.imread(str(args.original)).astype(np.float32)
    new = cv2.imread(str(args.inpainted)).astype(np.float32)
    rect = cv2.imread(str(args.mask), 0) > 127
    r8 = rect.astype(np.uint8)
    h, w = orig.shape[:2]

    border = np.zeros((h, w), bool)
    border[:40] = border[-40:] = True
    border[:, :40] = border[:, -40:] = True
    bg_ref = dominant(orig[border & ~rect].reshape(-1, 3))
    interior = cv2.erode(r8, np.ones((41, 41), np.uint8)) > 0
    inside_bg = dominant(new[interior].reshape(-1, 3))
    bgdist_new = np.abs(new - inside_bg).max(axis=2)

    # original backdrop just outside the mask: darker-than-reference is still
    # backdrop (shading drift), brighter is the figure's white outline
    brighter = (orig - bg_ref).max(axis=2)
    darker = (bg_ref - orig).max(axis=2)
    band_out = (
        (cv2.dilate(r8, np.ones((41, 41), np.uint8)) > 0)
        & ~rect & (brighter <= 10) & (darker <= 45)
    )
    T = laplace_extend(band_out, orig, (h, w))

    bgmask = ((bgdist_new < 25) & rect).astype(np.float32)
    L = np.dstack([cv2.GaussianBlur(new[..., c] * bgmask, (0, 0), 35) for c in range(3)])
    L = L / np.maximum(cv2.GaussianBlur(bgmask, (0, 0), 35), 1e-3)[..., None]

    wgt = np.clip((28 - bgdist_new) / 16, 0, 1) * rect
    corrected = np.clip(new + (T - L) * wgt[..., None], 0, 255)

    # seam lines along the mask bbox edges, where both sides read as backdrop
    ys, xs = np.where(rect)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    strip = np.zeros((h, w), np.float32)

    def bgish(img, sl):
        return (np.abs(img[sl] - T[sl]).max(axis=2) < 25).mean(axis=0 if img[sl].shape[0] < img[sl].shape[1] else 1) > 0.7

    for edge, coord in (("l", x0), ("r", x1), ("t", y0), ("b", y1)):
        vertical = edge in "lr"
        if vertical and (coord < 20 or coord > w - 20):
            continue
        if not vertical and (coord < 20 or coord > h - 20):
            continue
        if vertical:
            out_sl = np.s_[:, max(coord - 28, 0):max(coord - 14, 1)] if edge == "l" \
                else np.s_[:, coord + 14:coord + 28]
            in_sl = np.s_[:, coord + 16:coord + 30] if edge == "l" \
                else np.s_[:, coord - 30:coord - 16]
            ok = bgish(orig, out_sl) & bgish(corrected, in_sl)
            strip[ok, max(coord - 8, 0):coord + 8] = 1
        else:
            out_sl = np.s_[max(coord - 28, 0):max(coord - 14, 1), :] if edge == "t" \
                else np.s_[coord + 14:coord + 28, :]
            in_sl = np.s_[coord + 16:coord + 30, :] if edge == "t" \
                else np.s_[coord - 30:coord - 16, :]
            ok = bgish(orig, out_sl) & bgish(corrected, in_sl)
            strip[max(coord - 8, 0):coord + 8, ok] = 1
    strip = cv2.GaussianBlur(strip, (0, 0), 3)[..., None]
    corrected = corrected * (1 - strip) + T * strip

    feather = cv2.GaussianBlur(
        cv2.dilate(r8, np.ones((15, 15), np.uint8)).astype(np.float32), (0, 0), 5
    )[..., None]
    out = (corrected * feather + orig * (1 - feather)).clip(0, 255).astype(np.uint8)
    cv2.imwrite(str(args.out), out)

    inner = cv2.erode(r8, np.ones((17, 17), np.uint8)) > 0
    band_in = rect & ~inner & (bgdist_new < 20)
    ring = (cv2.dilate(r8, np.ones((25, 25), np.uint8)) > 0) & ~rect & (darker <= 45) & (brighter <= 10)
    gi = out.astype(np.float32)[band_in].mean(0)
    go = out.astype(np.float32)[ring].mean(0)
    print(f"{args.out.name}: seam gap {np.abs(gi - go).max():.1f} "
          f"(in {gi.round(1)} out {go.round(1)})")


if __name__ == "__main__":
    main()
