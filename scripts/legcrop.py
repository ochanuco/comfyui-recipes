"""Crop the lower half of each render and blow it up, so the legwear can be
judged on its own instead of at contact-sheet scale."""
import sys
from pathlib import Path
from PIL import Image

OUT = Path("REPO_ROOT/.local/ComfyUI/output")

names = sys.argv[1:]
tiles = []
for n in names:
    im = Image.open(OUT / f"{n}_00001_.png").convert("RGB")
    w, h = im.size
    crop = im.crop((0, int(h * 0.45), w, h))
    crop = crop.resize((int(crop.width * 1.3), int(crop.height * 1.3)), Image.LANCZOS)
    tiles.append(crop)

W = sum(t.width for t in tiles) + 12 * (len(tiles) + 1)
H = max(t.height for t in tiles) + 24
sheet = Image.new("RGB", (W, H), (24, 24, 26))
x = 12
for t in tiles:
    sheet.paste(t, (x, 12))
    x += t.width + 12
sheet.save(OUT / "sheet-legs.png")
print(OUT / "sheet-legs.png", sheet.size)
