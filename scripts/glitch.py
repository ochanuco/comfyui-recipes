#!/usr/bin/env python3
"""Datamosh-style digital noise over a bust render, in a purple palette.

The backdrop and the figure get different treatment. The flat backdrop is
replaced outright by a macroblock texture -- rows of wide rectangles in blue,
violet, magenta, black and white, shifted row by row and striped -- because a
glitch laid over a plain grey field just reads as dirt. The figure keeps its
drawing: a few horizontal tear bands with an R/B channel offset, and sparse
wide blocks copied sideways or stretched from one line, thinning out toward the
face so the eyes stay legible at every strength.

The backdrop is found by colour distance from the corners, so this only works on
a render with a flat background (the `bust` / `smug` poses). `--noise-sat`
scales the noise palette toward its luminance and shrinks the channel offset
with it; the figure's own colours are never touched. The X icon is the `smug`
pin at `--strength 0.3 --seed 11 --noise-sat 0.25`.

    uv run scripts/glitch.py in.png --out out.png --strength 0.3 --noise-sat 0.25
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

LUMA = np.array([0.299, 0.587, 0.114], dtype=np.float32)

PALETTE = np.array([
    [0x12, 0x0C, 0x8C],
    [0x1E, 0x3C, 0xFF],
    [0x2B, 0x6C, 0xFF],
    [0x5A, 0x10, 0xD8],
    [0x9C, 0x2A, 0xFF],
    [0xE0, 0x2C, 0xE8],
    [0xFF, 0x48, 0xC8],
    [0x06, 0x04, 0x22],
    [0x06, 0x04, 0x22],
    [0xF4, 0xEE, 0xFF],
    [0x1C, 0xD8, 0xF0],
    [0x40, 0xFF, 0x90],
    [0xFF, 0xE0, 0x40],
], dtype=np.float32)
PALETTE_WEIGHT = np.array([4, 4, 2, 3, 3, 3, 2, 3, 2, 1.5, 1, 0.35, 0.25])
PALETTE_WEIGHT = PALETTE_WEIGHT / PALETTE_WEIGHT.sum()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--strength", type=float, default=0.3,
                        help="0 leaves the figure alone, 1 tears it apart")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--noise-sat", type=float, default=0.25,
                        help="saturation of the noise palette, 1 = full")
    return parser.parse_args()


class Noise:
    def __init__(self, seed: int, saturation: float) -> None:
        self.rng = np.random.default_rng(seed)
        self.saturation = saturation
        lum = (PALETTE @ LUMA)[..., None]
        self.palette = lum + (PALETTE - lum) * saturation

    def pick(self, n: int = 1) -> np.ndarray:
        return self.palette[self.rng.choice(len(self.palette), size=n, p=PALETTE_WEIGHT)]

    def texture(self, h: int, w: int) -> np.ndarray:
        rng = self.rng
        out = np.zeros((h, w, 3), np.float32)
        y = 0
        while y < h:
            bh = int(rng.choice([8, 12, 16, 24, 32, 48], p=[.2, .2, .25, .15, .12, .08]))
            x = 0
            while x < w:
                bw = int(rng.choice([8, 16, 32, 48, 64, 96, 128, 192],
                                    p=[.08, .15, .2, .15, .15, .12, .1, .05]))
                out[y:y + bh, x:x + bw] = self.pick()[0]
                x += bw
            y += bh
        for _ in range(int(h * w / 20000)):
            bh, bw = int(rng.integers(8, 96)), int(rng.integers(32, 256))
            y0, x0 = int(rng.integers(0, h - bh)), int(rng.integers(0, w - bw))
            y1, x1 = int(rng.integers(0, h - bh)), int(rng.integers(0, w - bw))
            out[y1:y1 + bh, x1:x1 + bw] = out[y0:y0 + bh, x0:x0 + bw]
        fine = rng.random((h // 4, w // 4)) < 0.06
        colors = self.pick(int(fine.sum()))
        up = np.repeat(np.repeat(fine, 4, 0), 4, 1)
        out[up] = np.repeat(colors, 16, axis=0)
        y = 0
        while y < h:
            bh = int(rng.integers(4, 40))
            if rng.random() < 0.4:
                period = int(rng.choice([2, 3, 4, 8]))
                out[y:y + bh, (np.arange(w) // period) % 2 == 0] *= 0.55
            y += bh
        y = 0
        while y < h:
            bh = int(rng.integers(2, 32))
            if rng.random() < 0.5:
                out[y:y + bh] = np.roll(out[y:y + bh], int(rng.integers(-w // 3, w // 3)), axis=1)
            y += bh
        return out

    def tear_bands(self, img: np.ndarray, count: int, weight: np.ndarray) -> np.ndarray:
        rng = self.rng
        out = img.copy()
        h = img.shape[0]
        shift = round(10 * self.saturation)
        for _ in range(count):
            bh = int(rng.integers(3, 28))
            y = int(rng.integers(0, h - bh))
            keep = max(float(weight[y:y + bh].mean()), 0.25)
            dx = int(rng.integers(6, 70) * (1 if rng.random() < 0.5 else -1) * keep)
            seg = np.roll(img[y:y + bh], dx, axis=1).copy()
            seg[..., 0] = np.roll(seg[..., 0], int(rng.integers(-shift, shift + 1)), axis=1)
            seg[..., 2] = np.roll(seg[..., 2], int(rng.integers(-shift, shift + 1)), axis=1)
            if rng.random() < 0.3:
                seg = np.repeat(seg[:1], bh, axis=0)
            out[y:y + bh] = seg
        return out

    def figure_blocks(self, img: np.ndarray, density: float, weight: np.ndarray) -> np.ndarray:
        rng = self.rng
        out = img.copy()
        h, w, _ = img.shape
        for bh, bw in ((8, 48), (8, 96), (12, 64), (16, 128), (24, 96), (32, 32)):
            for by in range(h // bh):
                for bx in range(w // bw):
                    y0, x0 = by * bh, bx * bw
                    if rng.random() > density * 0.5 * weight[y0:y0 + bh, x0:x0 + bw].mean():
                        continue
                    sl = (slice(y0, y0 + bh), slice(x0, x0 + bw))
                    r = rng.random()
                    if r < 0.55:
                        sx = int(np.clip(x0 + rng.integers(-w // 6, w // 6), 0, w - bw))
                        out[sl] = img[y0:y0 + bh, sx:sx + bw]
                    elif r < 0.7:
                        out[sl] = out[sl] * 0.35 + self.pick()[0] * 0.65
                    elif r < 0.9:
                        out[sl] = np.repeat(out[y0:y0 + 1, x0:x0 + bw], bh, axis=0)
                    else:
                        out[sl] = out[sl][..., [2, 0, 1]]
        return out


def backdrop_mask(img: np.ndarray) -> np.ndarray:
    corners = np.concatenate([img[:24, :24].reshape(-1, 3), img[:24, -24:].reshape(-1, 3),
                              img[-24:, :24].reshape(-1, 3), img[-24:, -24:].reshape(-1, 3)])
    dist = np.abs(img - np.median(corners, axis=0)).sum(axis=2)
    flat = Image.fromarray(((dist < 60) * 255).astype(np.uint8))
    flat = flat.filter(ImageFilter.MinFilter(7)).filter(ImageFilter.GaussianBlur(2))
    return np.asarray(flat, np.float32) / 255.0


def face_weight(h: int, w: int) -> np.ndarray:
    yy, xx = np.mgrid[:h, :w]
    d = ((yy - h * 0.40) / (h * 0.26)) ** 2 + ((xx - w * 0.5) / (w * 0.26)) ** 2
    return np.clip((d - 0.7) / 0.8, 0, 1).astype(np.float32)


def saturate(img: np.ndarray, amount: float) -> np.ndarray:
    lum = (img @ LUMA)[..., None]
    return lum + (img - lum) * (1 + amount)


def glitch(img: np.ndarray, strength: float, seed: int, noise_sat: float) -> np.ndarray:
    noise = Noise(seed, noise_sat)
    h, w, _ = img.shape
    backdrop = backdrop_mask(img)
    away = face_weight(h, w)
    weight = away * (0.35 + 0.65 * strength) + (1 - away) * max(0.0, (strength - 0.5) * 1.2)
    figure = noise.figure_blocks(saturate(img, 0.25 * strength), 0.05 + 0.25 * strength, weight)
    out = figure * (1 - backdrop[..., None]) + noise.texture(h, w) * backdrop[..., None]
    out = noise.tear_bands(out, int(4 + 14 * strength), np.maximum(weight, backdrop))
    out[1::2] *= 1 - 0.12 * strength
    return np.clip(out, 0, 255)


def main() -> None:
    args = parse_args()
    img = np.asarray(Image.open(args.image).convert("RGB"), dtype=np.float32)
    out = glitch(img, args.strength, args.seed, args.noise_sat)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out.astype(np.uint8)).save(args.out)
    print(args.out)


if __name__ == "__main__":
    main()
