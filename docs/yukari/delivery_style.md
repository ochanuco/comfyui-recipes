# delivery_style

Yukari's delivery policy: what happens to a render after the model. The
prompt cannot hold these values -- the backdrop is not prompt-stable and the
purple marker is a post-process -- but they are identity all the same,
applied by the delivery tools instead of the graph. Every tool reads its
default from here, so the value a delivered picture actually wears has one
source; before this file, `#c7e5e9` lived in two scripts and `#6a3494` in
two others, and only the session that set them knew which copy was current.

## BACKDROP

The render's own backdrop is unstable under any perturbation: three renders
whose only difference was two leg-tag weights landed on `#d0d0c0`,
`#a0a0a0` and `#909090`. So the delivered colour, `#c7e5e9`, is set after
the fact by `recolor_bg.repaint`, always to this value. `recolor_bg` itself
stays general (its `--color` is required, not defaulted): the identity
belongs to the delivery, not to the tool.

## STROKE

The purple marker drawn outside the figure's own white band (the white band
itself is the model's `(white outline:1.6)` from `SURFACE`). Re-picked
2026-08-26 on the colW kick sweep: `#6a3494`, darker than the hair-accent
`#9256b8` it replaced, judged against a lighter `#b591d6` at the same
width.

## STROKE_WIDTH_BAND / STROKE_WIDTH_PCT

Width is set as a share of the white band it sits against (`0.80`), which
is what it was actually chosen as: 12.5px on the render whose 0.32 stroke
setting drew 6.1px, picked from a 0.32 / 0.50 / 0.80 / 1.2 ladder (see
`outline_stroke.band_thickness`).

The old share-of-canvas rule, `0.3`, is kept as a FLOOR under the band rule:
both rules only ever failed by drawing too thin, so the larger of the two
values is the one that is never the failure.

## SAT_BAND / BG_SAT_MAX

The acceptance band, from measured approved work: `kfuthu` 54.5, `lx2mjb`
41.6, `uk1jfi` 41.5. (The y-arms' 68-86 pink drift already read as
「寄っている」 by eye, independent of this band.) A pass is not approval --
the human still judges -- but a FAIL never goes forward.

The upper bound was 70 until 2026-08-28, when it failed a render the user
had already picked (`tx4oxl`, raw saturation 76.5, delivered composite
90.8): the frame mean moves with the figure's share of the canvas, so a
bound calibrated on lap framings misreads a lounge framing. The bound was
raised to 95, which keeps it as an explosion detector (the lap disasters
measured 108-188); the composition-independent guard is the `FIGURE_SAT`
pair below.

## FIGURE_MIDTONE_V / FIGURE_SAT_MEAN_MAX / FIGURE_SAT_P90_MAX

The figure's own saturation, measured where colour is actually visible:
non-backdrop pixels at V >= `FIGURE_MIDTONE_V` (80). The V floor is the
「タイツを除く」 rule made mechanical -- the black tights and coat sit below
it, so deep black stays exempt while the midtones carry the 高彩度・多彩
guard.

Calibrated 2026-08-28 on the lounge contrast verdicts: the picked
grad-free arms (`jcjwb6`/`64d41q`) measure mean 59.9-66.5, top-decile
123-191; the rejected gradient renders measure mean 108-137, top-decile
255. The bands (`FIGURE_SAT_MEAN_MAX = 95.0`, `FIGURE_SAT_P90_MAX = 230.0`)
split those two populations with margin on the picked side.

## FIGURE_LIGHT_V / FIGURE_LIGHT_SAT_TARGET

Saturation normalization is applied to the raw render (`scripts/desat.py`,
HSV S alone) before the layered delivery. Poses drift by different amounts
-- `lounge` paints the whole picture at 3x `stand`'s saturation on every
seed (8/8), `lap` at about half that -- and no prompt lever moves it (six
attempts on record: muted colour, limited palette, and others). So the
delivery normalizes instead of holding a per-pose factor table: measure the
figure's LIGHT band (the pale dress and hair, V >= `FIGURE_LIGHT_V` = 150),
scale saturation by target/measured, clamped to at most 1.0 so a pale
render is never pushed up.

The light band is the anchor because it reproduced both settled verdicts
from one rule: `lounge` 28/98 -> 0.29 (the user's picked value was 0.30,
「明らかに yjsswf だ！」) and `lap` 28/51 -> 0.55 (the computed proposal).
The target, `FIGURE_LIGHT_SAT_TARGET = 28.0`, is `stand`'s own measured
light band (26-30 across the delivered pair) -- `stand` IS the palette
reference, per 「立ちの方が正」.

## PALETTE_WINDOWS

The palette proper, applied by `scripts/repin.py` (V untouched -- the
brushwork is the render's own; hue and saturation are the delivery's).
Values are `stand` `4eqpdv`'s measurement frozen as numbers -- `stand` IS
the reference, per 「立ちの方が正」 -- and each window's saturation target is
per V band (light >= `FIGURE_LIGHT_V` / mid below), blended continuously so
no band boundary shows.

Chosen over a uniform S scale by eye across `stand`/`lounge`/`lap`
(「安定してそう」, 2026-08-28): the materials drift by different amounts --
purple mid drift 0.18 against skin mid drift 0.37 on the same render --
which one global factor can only average.

## BACKDROP_SPREAD_MAX

The backdrop flatness screen, on the RAW render's corner brightness spread.
A gradient backdrop starves the flood mask (23.7% coverage on `cmfpby`'s
`stand` against ~40%+ when flat), and then every downstream number -- the
figure bands, the normalization factor, the repaint -- is measured against
a backdrop leak.

Measured flat renders sit under 10, gradient failures at 40+ (2026-08-28
white-outline sweep; confirmed by `cmfpby` at 41.1), so the bound (`25.0`)
splits them mid-gap.

## FINALIZE_DENOISE

`0.45`, the denoise `finalize`'s masked refine runs at for a 2048 print's
touch-up.
