# winded

運動不足で息も絶え絶えで床に座り込む. `hoops` の続き -- she is still in the
gym kit, now on the floor. The reference is a stick figure: legs stretched
out in front, both hands planted on the floor BEHIND her, head back, mouth
open, sweatdrops flying.

```
(solo:1.5), (sitting:1.5), (on floor:1.45), (from side:1.35),
(arm support:1.5), (leaning back:1.4),
(outstretched legs:1.5), (legs together:1.4),
(open mouth:1.5), (>_<:1.45), (wavy mouth:1.4), (looking up:1.35),
(heavy breathing:1.45),
(flying sweatdrops:1.35), (sweat:1.3),
(feet out of frame:1.4), (full body:1.45), (short dress:1.35)
```

Half the words for this state are not tags. Counted before use: `panting` 0,
`tired` 0, `fatigue` 0, `sitting_on_floor` 0, `outstretched_legs` 956,
`hands_on_floor` 985. What carries the state is `heavy_breathing` 51k, and
what carries the hands-behind shape is `arm_support` 118k -- the tag is
already exactly this gesture, so the 985-count literal naming of it is not
needed.

`(from side:1.35)` 333k is load-bearing, not framing taste. Legs thrown
forward are foreshortened into nothing by a front camera; the first sweep of
this pose was nine renders all shot `from front` and that is what was wrong
with them. It costs the face its three-quarter turn, which is why `looking
at viewer` comes out below.

The legs are straightened by a DELETION. No tag says "legs extended" in a
count that moves a picture, but `knees_up` 81k is exactly the bend to
remove, and it goes in the negative -- the same shape as the knot and the
third arm, where naming the thing to delete beat every attempt to draw the
thing wanted. `legs_together` 37k keeps them closed, which the costume's
standing 「股を出さずに」 requires.

`(>_<:1.45)`, and the road to that number is the useful part. 93.7k posts,
more than `@_@` at 55.7k, so the tag is real. Two priors said to keep the
weight LOW -- `(@_@:1.45)` drew literal black spirals on the whites and
`dizzy` picked 1.0; `swelter` swept `(>_<:1.4)` against `(closed eyes:1.4)`
and the symbol lost -- and 1.0 was duly swept against 1.3 and picked.

Then the seed changed and 1.0 stopped drawing anything at all. On
`111222333` the eyes came out open, and 1.3 and 1.45 both brought the symbol
back without drawing a glyph on the whites. So the window is real and it
MOVES WITH THE SEED: the same weight that was correct on one pass 1 is
invisible on another. A face symbol has to be re-checked on any seed it is
carried to, and re-checked in both directions -- too low is as wrong as too
high, and this file only had the too-high failure written down.

`(feet out of frame:1.4)` 236k, and it is here because the ankles could not
be drawn. 「足首から靴の向きが骨折しているとしか見えない」 on the settled
render: one shoe sole-on, one shoe not joined to a leg, and a third
lace-covered lump between them.

Three second-pass guards were tried first and none of them touched it.
`shoe_soles` 18.4k for the sole-on view, `single_shoe` 10.8k for the odd
count, and dropping the costume's own `(high tops:1.3)` -- ink coverage over
the lower half moved 44.9 to 44.3, i.e. nothing. A late pass can delete a
drawn object; it cannot re-articulate a joint. That is
`refine-cannot-rebuild-structure` measured on a fourth pose.

Which left re-rolling pass 1, and the cheap exit was to re-roll it with the
broken region outside the frame. Note what this tag is NOT: it is a framing
decision, so it only works in the pass that decides framing. Putting it in
the second pass would be the same mistake as the guards.

It does not land the same way on every seed. On `111222333` -- the seed
this pose was settled on for COLOUR -- the figure still reached the bottom
edge in full, so the cheapest exit was closed on exactly the seed that had
the flattest paint. Four seeds were run with and without; `737373737` is the
pick, at some cost in saturation (31.4 against 22.4).

`(sweat:1.3)` is deliberately the lowest weight in the block. 763k and
strong, but it is drawn as SHEEN, which is the same axis as the pass-2 gloss
this round was spent removing. The state is carried by the symbol side
instead -- `flying_sweatdrops` 126k, `hoops`'s tag. `steaming_body` 42k is
left out for `hoops`'s reason: steam is scenery and SURFACE is a flat
backdrop.

## Record

Canvas `(1152, 1152)`, `own_eyes=True`, `open_mouth=True`, `settled_seed=737373737`.

Square: legs forward and arms back put the long axis on the DIAGONAL, so
neither portrait nor landscape frames fit. The reference is square.

あ゛〜〜〜 makes the mouth the largest thing in the face (`swelter`'s
reason), and shot from the side with her head back `looking at viewer` has
no referent. FACE's eye tags STAY -- instructions about shut eyes, a cost
noted and not paid. `face_edits` removes `small mouth, ` and removes `,
looking at viewer`.

`knees_up` deleted is how the legs get straight: nothing in the positive
says "extended" in a count that moves a picture, so the lever is
subtraction. Applied after the limb trio so it lands in FRONT of it -- the
order the picked render was drawn in. `negative_edits` prepends `(knees
up:1.5), ` at stage `S_POSE_LATE`.

Two arms angled back behind the torso is the arrangement that invites a
third. `negative_edits` prepends `_LIMB_TRIO` (see `shared.md`) at stage
`S_POSE_LATE`.

Measured, not assumed: this pose's FIRST pass has no hand guard -- the five
names are gated to `tehe`/`hoops` there. Both hands carry her weight and
pass 2 redraws them, so they are named here, once. `hires_negative` is
`HAND_BAN`.

「手書き風のファイナライズ」: THIN off (pass 2 only) plus the marker pair,
appended at the very END -- `HIRES_POSITIVE` splices mid-prompt instead, and
token order changes the encoding; separate mechanisms on purpose. `sketch`
is NOT here: it means unfinished, which is the state `HIRES_NEGATIVE_PAINT`
exists to remove. `hires_finish=HANDDRAWN_FINISH`.

`--hires` is a longest-side number, not a scale: 1416 is this pose's 1.23x,
the ratio every portrait pose prints at. The 1152 (1.0x) conclusion before
it was measured on the sweep's most saturated seed and did not survive
being retaken on the settled one. 0.50 because the face is carried by a
symbol and 0.60 dissolves it. `hires_print=(1416, 0.50)`.

The seed holds the colour (2.4x saturation spread across five seeds on an
identical prompt) and decides whether `feet out of frame` clears the frame
at all.
