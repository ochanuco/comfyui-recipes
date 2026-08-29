"""Yukari's delivery policy: what happens to a render after the model.

The prompt cannot hold these values -- the backdrop is not prompt-stable and
the purple marker is a post-process -- but they are identity all the same,
applied by the delivery tools instead of the graph. Every tool reads its
default from here, so the value a delivered picture actually wears has one
source. Changing a value here changes every picture delivered after it --
`costume_check.py` fingerprints this file alongside the prompt blocks for
that reason.

The calibration measurements behind each number are in
docs/yukari/delivery_style.md.
"""

# The backdrop every delivered picture is set to. The render's own backdrop
# is unstable under any perturbation, so the delivered colour is set after
# the fact by recolor_bg.repaint, always to this. recolor_bg itself stays
# general (its --color is required, not defaulted): the identity belongs to
# the delivery, not to the tool.
BACKDROP = "#c7e5e9"

# The purple marker drawn outside the figure's own white band. The white
# band itself is the model's (`(white outline:1.6)` in SURFACE); this is the
# second edge outside it, deliberately darker than the hair accent.
STROKE = "#6a3494"
# Width as a share of the white band it sits against, which is what it was
# actually chosen as (see outline_stroke.band_thickness).
STROKE_WIDTH_BAND = 0.80
# The share-of-canvas rule the band rule replaced, kept as a FLOOR under it:
# both rules only ever failed by drawing too thin, so the larger of the two
# is the one that is never the failure.
STROKE_WIDTH_PCT = 0.3

# The acceptance band, from measured approved work. A pass is not approval
# -- the human still judges -- but a FAIL never goes forward. The frame mean
# moves with the figure's share of the canvas, so the upper bound is only an
# explosion detector; the composition-independent guard is the FIGURE_SAT
# pair below.
SAT_BAND = (30.0, 95.0)
BG_SAT_MAX = 60.0

# The figure's own saturation, measured where colour is actually visible:
# non-backdrop pixels at V >= FIGURE_MIDTONE_V. The V floor is the
# tights-exempt rule made mechanical -- the black tights and coat sit below
# it, so deep black stays exempt while the midtones carry the
# high-saturation guard. The bands split the picked arms from the rejected
# gradient renders with margin on the picked side.
FIGURE_MIDTONE_V = 80
FIGURE_SAT_MEAN_MAX = 95.0
FIGURE_SAT_P90_MAX = 230.0

# Saturation normalization, applied to the raw render (scripts/desat.py, HSV
# S alone) before the layered delivery. Poses drift by different amounts and
# no prompt lever moves it, so the delivery normalizes instead of holding a
# per-pose factor table: measure the figure's LIGHT band (the pale dress and
# hair, V >= FIGURE_LIGHT_V), scale saturation by target/measured, clamped
# to at most 1.0 so a pale render is never pushed up. The target is stand's
# own measured light band -- stand IS the palette reference.
FIGURE_LIGHT_V = 150
FIGURE_LIGHT_SAT_TARGET = 28.0

# The palette proper: per-material colour targets, applied by scripts/repin.py
# (V untouched -- the brushwork is the render's own; hue and saturation are
# the delivery's). Values are stand's measurement frozen as numbers, and each
# window's saturation target is per V band (light >= FIGURE_LIGHT_V / mid
# below), blended continuously so no band boundary shows. Chosen over the
# uniform S scale because the materials drift by different amounts, which one
# global factor can only average.
PALETTE_WINDOWS = (
    {"name": "purple", "hue": (170.0, 225.0), "hue_target": 191.0,
     "sat_light": 50.4, "sat_mid": 45.1},
    {"name": "skin", "hue": (0.0, 48.0), "hue_target": None,
     "sat_light": 24.7, "sat_mid": 58.5},
)

# The backdrop flatness screen, on the RAW render's corner brightness spread.
# A gradient backdrop starves the flood mask, and then every downstream
# number -- the figure bands, the normalization factor, the repaint -- is
# measured against a backdrop leak. Measured flat renders sit under 10 and
# gradient failures at 40+, so the bound splits them mid-gap.
BACKDROP_SPREAD_MAX = 25.0

# finalize's masked refine, the denoise a 2048 print's touch-up runs at.
FINALIZE_DENOISE = 0.45
