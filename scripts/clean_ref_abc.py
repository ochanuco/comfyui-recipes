"""Paint the backdrop intruder out of the ab-C render so it can self-trace.

Input is a copy of `ab-C_00001_` at `.local/ComfyUI/input/ref-abC.png`; output
is `ref-abC-clean.png` next to it. The intruder sits alone in the upper-left,
so the sweep is a box, and inside it everything that is not staff, glove or
cape colour is flattened to the backdrop — the eye whites, the iris rings and
the spiky mass all fail every keep-rule. Nicks this leaves (a swallowed hair
strand) are the model's to repaint, which is the point of cleaning the
reference instead of inpainting the output.

The coordinates are specific to ab-C. For another image, re-derive the boxes;
the keep-rules travel better than the geometry.
"""

from pathlib import Path

from PIL import Image

INPUT_DIR = Path(__file__).resolve().parent.parent / ".local/ComfyUI/input"


def warm(r: int, g: int, b: int) -> bool:
    """Staff brown and glove yellow: red-led warm tones."""
    return r > 70 and r > g + 15 and g > b + 5


def teal(r: int, g: int, b: int) -> bool:
    """Cape teal: green tracks blue, both above red. The floor of 60 on green
    rejects the intruder's dark iris rings, which are blue-led."""
    return g > r + 15 and b > r + 15 and g > b - 40 and g >= 60


def main() -> None:
    im = Image.open(INPUT_DIR / "ref-abC.png").convert("RGB")
    px = im.load()

    def bg(y: int) -> tuple:
        # Sample the backdrop per-row from the clean left margin so the fill
        # follows the backdrop's own gradient instead of leaving a seam.
        return px[15, y]

    # Main sweep: keep staff/glove/cape, flatten the rest.
    for y in range(0, 520):
        row_bg = bg(y)
        for x in range(40, 550):
            r, g, b = px[x, y]
            if not (warm(r, g, b) or teal(r, g, b)):
                px[x, y] = row_bg

    # Pupil-ring leftovers pass the teal rule; this zone holds no cape, so
    # only warm survives here.
    for y in range(250, 395):
        row_bg = bg(y)
        for x in range(250, 552):
            r, g, b = px[x, y]
            if not warm(r, g, b):
                px[x, y] = row_bg

    # The sliver of intruder eye-white peeking past the hair strand.
    for y in range(350, 420):
        row_bg = bg(y)
        for x in range(540, 592):
            r, g, b = px[x, y]
            if r > 210 and g > 210 and b > 195:
                px[x, y] = row_bg

    im.save(INPUT_DIR / "ref-abC-clean.png")
    remove_shadow(im)
    im.save(INPUT_DIR / "ref-abC-clean2.png")


def remove_shadow(im) -> None:
    """Also flatten the sage's own drop shadow, in place.

    A trace that carries the shadow's outline forces every style to put
    *something* there. cel-plain draws the shadow back; galge, which does not
    want one, resolved the same outline as a boulder and then a chair. The
    shadow-free reference is what the galge render needs; for cel-plain the
    shadow-carrying one is fine and keeps the shape that was liked.

    The shadow cannot be colour-keyed: at (59, 59, 87) it is nearly the hair
    colour. What separates it is that it has no lineart — so a flood fill from
    the corners walks through its soft edge and stops at the figure's drawn
    outline. An erosion pass then eats the grainy boundary the flood leaves.
    """
    from collections import deque

    px = im.load()
    W, H = im.size

    def lum(c):
        return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]

    row_bg = []
    last = px[15, 5]
    for y in range(H):
        c = px[15, y]
        if abs(c[0] - c[1]) < 14 and abs(c[1] - c[2]) < 14 and lum(c) > 150:
            last = c
        row_bg.append(last)

    def guard(c):
        r, g, b = c
        return abs(r - g) <= 22 and (b - r) >= -6 and lum(c) >= 55

    visited = bytearray(W * H)
    q = deque()
    for sx, sy in [(2, 2), (W - 3, 2), (2, H - 3), (W - 3, H - 3),
                   (W // 2, 2), (W - 3, H // 2), (2, H // 2), (W // 2, H - 3)]:
        if guard(px[sx, sy]):
            q.append((sx, sy))
            visited[sy * W + sx] = 1
    while q:
        x, y = q.popleft()
        c = px[x, y]
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < W and 0 <= ny < H and not visited[ny * W + nx]:
                nc = px[nx, ny]
                if guard(nc) and max(abs(nc[0] - c[0]), abs(nc[1] - c[1]),
                                     abs(nc[2] - c[2])) <= 12:
                    visited[ny * W + nx] = 1
                    q.append((nx, ny))
    for y in range(H):
        for x in range(W):
            if visited[y * W + x]:
                px[x, y] = row_bg[y]

    def loose(c):
        r, g, b = c
        return abs(r - g) <= 26 and (b - r) >= -8 and 55 <= lum(c) <= 205

    flat = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            if px[x, y] == row_bg[y]:
                flat[y * W + x] = 1
    for _ in range(6):
        changed = []
        for y in range(1, H - 1):
            for x in range(1, W - 1):
                if flat[y * W + x] or not loose(px[x, y]):
                    continue
                nb = sum(flat[(y + dy) * W + (x + dx)]
                         for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)
                if nb >= 5:
                    changed.append((x, y))
        if not changed:
            break
        for x, y in changed:
            px[x, y] = row_bg[y]
            flat[y * W + x] = 1

    # A teal wisp of the intruder's tuft rides the very top edge, above the
    # main sweep's keep-rules; nothing of the figure is up there.
    for y in range(0, 45):
        for x in range(495, 615):
            px[x, y] = row_bg[y]


if __name__ == "__main__":
    main()
