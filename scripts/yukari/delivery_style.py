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
#
# The upper bound was 70 until 2026-08-28, when it failed a render the user
# had picked (tx4oxl raw 76.5, its delivered composite 90.8): the frame mean
# moves with the figure's share of the canvas, so a bound calibrated on lap
# framings misreads a lounge. 95 keeps it as the explosion detector (the lap
# disasters measured 108-188); the composition-independent guard is the
# FIGURE_SAT pair below.
SAT_BAND = (30.0, 95.0)
BG_SAT_MAX = 60.0

# The figure's own saturation, measured where colour is actually visible:
# non-backdrop pixels at V >= FIGURE_MIDTONE_V. The V floor is the 「タイツを
# 除く」 rule made mechanical -- the black tights and coat sit below it, so
# deep black stays exempt while the midtones carry the 高彩度・多彩 guard.
# Calibrated 2026-08-28 on the lounge contrast verdicts: the picked grad-free
# arms (jcjwb6/64d41q) measure mean 59.9-66.5, top-decile 123-191; the
# rejected gradient renders measure mean 108-137, top-decile 255. The bands
# split those with margin on the picked side.
FIGURE_MIDTONE_V = 80
FIGURE_SAT_MEAN_MAX = 95.0
FIGURE_SAT_P90_MAX = 230.0

# Saturation normalization, applied to the raw render (scripts/desat.py, HSV
# S alone) before the layered delivery. Poses drift by different amounts --
# lounge paints the whole picture 3x stand's saturation on every seed (8/8),
# lap about half that -- and no prompt lever moves it (six attempts, muted
# color, limited palette, all on record). So the delivery normalizes instead
# of holding a per-pose factor table: measure the figure's LIGHT band (the
# pale dress and hair, V >= FIGURE_LIGHT_V), scale saturation by
# target/measured, clamped to at most 1.0 so a pale render is never pushed
# up. The light band is the anchor because it reproduced both settled
# verdicts from one rule: lounge 28/98 -> 0.29 (the user's picked 0.30,
# 「明らかに yjsswf だ！！」) and lap 28/51 -> 0.55 (the computed proposal).
# The target is stand's own measured light band (26-30 across the delivered
# pair) -- stand IS the palette reference, per 「立ちの方が正」.
FIGURE_LIGHT_V = 150
FIGURE_LIGHT_SAT_TARGET = 28.0

# finalize's masked refine, the denoise a 2048 print's touch-up runs at.
FINALIZE_DENOISE = 0.45
