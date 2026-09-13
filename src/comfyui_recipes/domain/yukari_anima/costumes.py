"""The wardrobe: garment tags layered between a pose's gesture and scene."""

from __future__ import annotations

COSTUMES = {
    "roomwear": ("(oversized shirt:1.35), (sleeves past wrists:1.3), "
                 "(bare shoulders:1.1), "),
    "outing": ("(oversized sweatshirt:1.35), (white sweatshirt:1.2), "
               "(sleeves past wrists:1.25), (denim shorts:1.3), "),
    "standard": ("(black hooded cardigan:1.25), open cardigan, "
                 "(rabbit hood:1.3), long sleeves, drawstring, "
                 "(purple dress:1.25), frills, (sleeves past wrists:1.15), "
                 "hood down, "),
}

LEGWEAR = {
    "roomwear": "",
    "outing": "(black pantyhose:1.5), (opaque pantyhose:1.4), ",
    "standard": ("(black pantyhose:1.3), (pale purple pantyhose:1.15), "
                 "(gradient legwear:1.2), "),
}

# Costumes whose garments include a hood or cardigan; `recipe.negative`
# skips HOOD_BAN for them.
HOODED_COSTUMES = frozenset({"standard"})
