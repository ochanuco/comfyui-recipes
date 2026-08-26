"""Measure a render against the look spec before a human sees it.

    uv run scripts/palette_check.py <short_id> [<short_id> ...]
    uv run scripts/palette_check.py --file <png> [...]

The lap deep-dive's failures -- a neon backdrop, a saturation explosion, a
pink cast -- were all numbers before they were opinions: background hue and
saturation, and frame-wide mean saturation, all sat far outside the band
every approved render lives in. Nothing measured them until the human had
already seen the damage. This is the acceptance gate: run it on every arm
the moment it is ingested, and do not present a FAIL as a candidate.

The band is from measured approved work (kfuthu 54.5, lx2mjb 41.6,
uk1jfi 41.5, and the y-arms' 68-86 pink drift already read as "寄っている"):
mean saturation 30-70, background saturation under 60. A pass is not
approval -- the human still judges -- but a FAIL never goes forward.
"""
from __future__ import annotations

import argparse
import io
import sys
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

SAT_BAND = (30.0, 70.0)
BG_SAT_MAX = 60.0


def measure(data: bytes) -> dict:
    im = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    hsv = np.array(Image.fromarray(im).convert("HSV")).astype(float)
    edge = np.concatenate([im[:30].reshape(-1, 3), im[-30:].reshape(-1, 3),
                           im[:, :30].reshape(-1, 3), im[:, -30:].reshape(-1, 3)])
    bg = np.median(edge, axis=0).astype(int)
    bg_hsv = np.array(Image.fromarray(bg[None, None].astype(np.uint8))
                      .convert("HSV")).astype(float)[0, 0]
    return {"bg": tuple(bg), "bg_sat": float(bg_hsv[1]),
            "sat": float(hsv[..., 1].mean())}


def verdict(m: dict) -> list[str]:
    fails = []
    if not SAT_BAND[0] <= m["sat"] <= SAT_BAND[1]:
        fails.append(f"mean saturation {m['sat']:.1f} outside {SAT_BAND}")
    if m["bg_sat"] > BG_SAT_MAX:
        fails.append(f"background saturation {m['bg_sat']:.1f} > {BG_SAT_MAX}")
    return fails


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ids", nargs="*", help="chimera short ids")
    parser.add_argument("--file", action="append", type=Path, default=[])
    args = parser.parse_args()
    failed = False
    sources: list[tuple[str, bytes]] = []
    if args.ids:
        import generate
        import post_renders
        generate._CREDS = generate.credentials()
        for sid in args.ids:
            req = urllib.request.Request(
                f"{generate.BASE}/g/{sid}/image",
                headers={**generate._CREDS,
                         "User-Agent": post_renders.USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                sources.append((sid, r.read()))
    for path in args.file:
        sources.append((str(path), path.read_bytes()))
    for name, data in sources:
        m = measure(data)
        fails = verdict(m)
        status = "FAIL" if fails else "pass"
        failed |= bool(fails)
        print(f"{name}: {status} | bg #%02x%02x%02x sat {m['bg_sat']:.0f} "
              f"| mean sat {m['sat']:.1f}" % m["bg"]
              + ("".join(f"\n  - {f}" for f in fails)))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
