"""The author's hand, delivery side: what happens to a render after the model.

The prompt cannot hold these values -- the backdrop is not prompt-stable and
the purple marker is a post-process -- but they are identity all the same,
applied by the delivery tools instead of the graph. Every tool reads its
default from here, so the value a delivered picture actually wears has one
source; before this file, `#c7e5e9` lived in two scripts and `#6a3494` in
two others, and only the session that set them knew which copy was current.

Changing a value here changes every picture delivered after it --
`costume_check.py` fingerprints this file alongside the prompt blocks for
that reason.
"""

# The backdrop every delivered picture is set to. The render's own backdrop
# is unstable under any perturbation -- three renders whose only difference
# was two leg-tag weights landed on #d0d0c0, #a0a0a0 and #909090 -- so the
# delivered colour is set after the fact by recolor_bg.repaint, always to
# this. recolor_bg itself stays general (its --color is required, not
# defaulted): the identity belongs to the delivery, not to the tool.
BACKDROP = "#c7e5e9"

# The purple marker drawn outside the figure's own white band. The white
# band itself is the model's (`(white outline:1.6)` in SURFACE); this is the
# second edge outside it. Re-picked 2026-08-26 on the colW kick sweep:
# darker than the hair-accent #9256b8 it replaced, judged against a lighter
# #b591d6 at the same width.
STROKE = "#6a3494"
# Width as a share of the white band it sits against, which is what it was
# actually chosen as: 12.5px on the render whose 0.32 stroke drew 6.1px,
# from a 0.32 / 0.50 / 0.80 / 1.2 ladder (see outline_stroke.band_thickness).
STROKE_WIDTH_BAND = 0.80
# The share-of-canvas rule the band rule replaced, kept as a FLOOR under it:
# both rules only ever failed by drawing too thin, so the larger of the two
# is the one that is never the failure.
STROKE_WIDTH_PCT = 0.3

# The acceptance band, from measured approved work (kfuthu 54.5, lx2mjb
# 41.6, uk1jfi 41.5; the y-arms' 68-86 pink drift already read as
# 「寄っている」). A pass is not approval -- the human still judges -- but a
# FAIL never goes forward.
SAT_BAND = (30.0, 70.0)
BG_SAT_MAX = 60.0

# finalize's masked refine, the denoise a 2048 print's touch-up runs at.
FINALIZE_DENOISE = 0.45
