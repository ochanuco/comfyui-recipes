"""The wardrobe: garment tags layered between the identity and the pose."""

from __future__ import annotations

COSTUMES = {
    "default": ("(black hooded cardigan:1.25), open cardigan, (rabbit "
                "hood:1.3), long sleeves, drawstring, (purple dress:1.25), "
                "short dress, frills, (sleeves past wrists:1.15), "
                "hood down, "),
    "outing": ("(black hooded cardigan:1.25), open cardigan, (rabbit "
               "hood:1.3), long sleeves, drawstring, (purple dress:1.25), "
               "(long dress:1.15), (knee-length dress:1.1), frills, "
               "(sleeves past wrists:1.15), hood down, "),
    "bath": ("(white shirt:1.3), (t-shirt:1.35), (oversized shirt:1.3), "
             "(dolphin shorts:1.3), (short shorts:1.2), (towel around "
             "neck:1.35), "),
}

# The leg block for costumes that do not wear the recipe's LEGWEAR.
LEGWEAR_BY_COSTUME = {
    "bath": "(bare legs:1.3), (barefoot:1.25), ",
}

# Appended to NEGATIVE for the costume.
NEGATIVE_BY_COSTUME = {
    "bath": ", (pantyhose:1.5), (black pantyhose:1.45), (shoes:1.4)",
}
