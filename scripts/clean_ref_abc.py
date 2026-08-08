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


if __name__ == "__main__":
    main()
