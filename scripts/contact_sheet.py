"""Tile renders into one sheet, each labelled with the prompt id that made it.

Reviewing happens by quoting a prompt id back ("this one is the good one"), but
the id is nowhere in the file: the PNG carries the graph, not the id that ran
it. ComfyUI's /history knows both, so this asks it and writes the id under each
tile. Without that the sheet is just pictures and the reply has to be "the third
one in the second row".

    uv run scripts/contact_sheet.py --glob 'fb-*' --out sheet-fb.png

Files are ordered as given; `--glob` sorts by name, which keeps a prefix family
together. Missing ids are labelled with the filename alone -- a render queued
outside this session, or one old enough to have fallen out of history.
"""

import argparse
import json
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from comfy_host import DEFAULT_HOST, DEFAULT_PORT

REPO = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO / ".local/ComfyUI/output"

LABEL_H = 34
PAD = 8
BG = (24, 24, 26)
FG = (232, 232, 236)
DIM = (150, 150, 158)


def prompt_ids(host: str, port: int) -> dict[str, str]:
    """filename -> prompt id, from the whole history."""
    url = f"http://{host}:{port}/history?max_items=2000"
    with urllib.request.urlopen(url) as response:
        history = json.loads(response.read())
    mapping = {}
    for pid, entry in history.items():
        for output in entry.get("outputs", {}).values():
            for image in output.get("images", []):
                mapping[image["filename"]] = pid
    return mapping


def font(size: int):
    # DejaVu ships with Pillow; the system fonts are not guaranteed to be there.
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def build(paths: list[Path], ids: dict[str, str], cols: int, cell: int) -> Image.Image:
    rows = (len(paths) + cols - 1) // cols
    tile_w = cell + PAD
    tile_h = cell + LABEL_H + PAD
    sheet = Image.new("RGB", (cols * tile_w + PAD, rows * tile_h + PAD), BG)
    draw = ImageDraw.Draw(sheet)
    name_font, id_font = font(15), font(13)

    for i, path in enumerate(paths):
        x = PAD + (i % cols) * tile_w
        y = PAD + (i // cols) * tile_h
        im = Image.open(path).convert("RGB")
        im.thumbnail((cell, cell), Image.LANCZOS)
        sheet.paste(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2))

        stem = path.name.replace("_00001_.png", "")
        pid = ids.get(path.name)
        draw.text((x, y + cell + 3), stem, font=name_font, fill=FG)
        draw.text((x, y + cell + 19), pid or "(no prompt id in history)",
                  font=id_font, fill=DIM)
    return sheet


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--glob", default="*_00001_.png",
                        help="pattern under the output dir")
    parser.add_argument("--out", default="contact-sheet.png",
                        help="written into the output dir")
    parser.add_argument("--cols", type=int, default=4)
    parser.add_argument("--cell", type=int, default=420)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    pattern = args.glob if args.glob.endswith(".png") else f"{args.glob}_00001_.png"
    paths = sorted(OUTPUT_DIR.glob(pattern))
    if not paths:
        raise SystemExit(f"no files match {pattern} under {OUTPUT_DIR}")

    try:
        ids = prompt_ids(args.host, args.port)
    except OSError:
        # A sheet without ids still beats no sheet; ComfyUI may not be up.
        ids = {}

    sheet = build(paths, ids, args.cols, args.cell)
    out = OUTPUT_DIR / args.out
    sheet.save(out)
    print(f"{out}  ({len(paths)} tiles)")


if __name__ == "__main__":
    main()
