#!/usr/bin/env python3
"""Take a render from the worker to the picture the user sees: repaint, stroke, post.

The three steps at the end of every round were three separate commands and a
download in between, which is how a sweep gets judged on raw renders that are
missing half of what the delivered picture has. 「紫線がなくなった」 is what that
looks like from the other side: the purple marker is a post-process, so a
prompt_id posted by `post_renders.py` has never had one.

    uv run scripts/deliver.py <prompt_id> [<prompt_id> ...]     # fetch, finish, post
    uv run scripts/deliver.py out/*.png --no-post               # local files, no webhook

Order is fixed and it matters: the backdrop is set FIRST, because the stroke
finds the figure by flooding from a corner and has to be looking at the colour
that is staying. Both steps are import-level calls into the scripts that own
them -- `recolor_bg.repaint` and `outline_stroke.stroke` -- so the delivered
file is what those two CLIs would have produced, defaults and all.

Everything this writes goes to .local/_nogit/deliver/. It is a derived picture:
the render is on the worker and the recipe is in git, so nothing here is worth
keeping.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import comfy_host
import post_renders
import recolor_bg
import outline_stroke
from comfy_host import DEFAULT_HOST, DEFAULT_PORT

REPO = Path(__file__).resolve().parent.parent
OUTDIR = REPO / ".local/_nogit/deliver"
# The backdrop this project delivers on. Set here rather than defaulted in
# recolor_bg, which is a general tool and gets pointed at other colours.
BACKDROP = "#c7e5e9"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="+", help="prompt ids, or local PNG paths")
    parser.add_argument("--color", default=BACKDROP, help="backdrop to repaint to")
    parser.add_argument(
        "--stroke",
        default=outline_stroke.DEFAULT_COLOR,
        help="marker drawn outside the figure's white band; '' to skip it",
    )
    parser.add_argument("--stroke-width-pct", type=float)
    parser.add_argument("--no-post", action="store_true")
    parser.add_argument("--outdir", type=Path, default=OUTDIR)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def sources(targets: list[str], host: str, port: int) -> list[tuple[str, Path]]:
    """(label, local path) for each target, pulling prompt ids off the worker.

    A prompt id can have produced more than one image; all of them come back,
    labelled with the id so the user can name one the same way they named it in
    the channel.
    """
    found: list[tuple[str, Path]] = []
    history = None
    for target in targets:
        path = Path(target)
        if path.exists():
            found.append((path.stem, path))
            continue
        if history is None:
            history = post_renders.history(host, port, max_items=200)
        entry = history.get(target)
        if entry is None:
            print(f"{target}: not in history -- the worker may have dropped it")
            continue
        for image in post_renders.images_of(entry):
            found.append((target, comfy_host.ensure_local(
                image["filename"], post_renders.OUTPUT_DIR,
                image.get("subfolder", ""), image.get("type", "output"),
                host=host, port=port)))
    return found


def main() -> int:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    url = None if args.no_post else post_renders.webhook()

    for label, path in sources(args.targets, args.host, args.port):
        pixels = np.array(Image.open(path).convert("RGB")).astype(int)
        pixels, share = recolor_bg.repaint(pixels, recolor_bg.parse_color(args.color))
        if share < 5:
            print(f"{path.name}: {share:.1f}% backdrop, not flat enough -- skipped")
            continue
        width = None
        if args.stroke:
            pixels, width, _ = outline_stroke.stroke(
                pixels.astype(float), args.stroke, width_pct=args.stroke_width_pct)
        out = args.outdir / f"{path.stem}-delivered.png"
        Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8)).save(out)
        edge = "" if width is None else f", {args.stroke} at {width:.1f}px"
        print(f"{path.name}: {share:.1f}% repainted{edge} -> {out.name}", flush=True)
        if url:
            post_renders.post(url, label, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
