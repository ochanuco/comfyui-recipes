"""The wardrobe: garment tags layered between a pose's gesture and scene."""

from __future__ import annotations

COSTUMES = {
    "roomwear": ("(oversized shirt:1.35), (sleeves past wrists:1.3), "
                 "(bare shoulders:1.1), "),
    "outing": ("(oversized sweatshirt:1.35), (white sweatshirt:1.2), "
               "(sleeves past wrists:1.25), (denim shorts:1.3), "),
    "standard": ("(eggplant purple hooded cardigan:1.5), (dark violet hoodie:1.25), "
                 "open cardigan, "
                 "(rabbit hood:1.3), long sleeves, drawstring, "
                 "(purple dress:1.25), frills, (sleeves past wrists:1.15), "
                 "hood down, "),
}

# The `opaque` legwear: each costume's own tights.
LEGWEAR = {
    "roomwear": "",
    "outing": "(black pantyhose:1.5), (opaque pantyhose:1.4), ",
    "standard": ("(dark purple pantyhose:1.45), (opaque pantyhose:1.3), "
                 "(gradient legwear:1.2), (purple gradient:1.1), "),
}

# The `sheer-gloss` legwear: one block for every costume. `recipe.negative`
# pairs it with SHEER_BAN and drops GARMENT_GLOSS_TAGS.
SHEER_GLOSS_LEGWEAR = (
    "(sheer black pantyhose:1.5), (see-through legwear:1.4), "
    "(thin translucent legwear:1.3), (20 denier:1.1), (pantyhose:1.4), "
    "(shiny pantyhose:1.3), (subtle sheen on legwear:1.15), "
    "(anime coloring:1.2), "
    "thin sheer black pantyhose drawn in anime style: the skin shows "
    "through as a lighter greyish purple tone on the knees and shins, the "
    "legs darken to black toward their outlines, and a soft white sheen "
    "highlight runs along the shin, ")

LEGWEARS = ("opaque", "sheer-gloss")
DEFAULT_LEGWEAR = "opaque"


def legwear_block(costume: str, legwear: str) -> str:
    if legwear == "sheer-gloss":
        return SHEER_GLOSS_LEGWEAR
    if legwear != "opaque":
        raise KeyError(legwear)
    return LEGWEAR[costume]

# Costumes whose garments include a hood or cardigan; `recipe.negative`
# skips HOOD_BAN for them.
HOODED_COSTUMES = frozenset({"standard"})
