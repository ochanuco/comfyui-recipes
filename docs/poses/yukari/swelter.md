# swelter

暑くて床でジタバタ, straight down. `flop` is this body position at rest and
`prone` is the from-above camera that works; what is new here is motion and
a reason.

```
(solo:1.5), (lying:1.45), (on back:1.5), (from above:1.45),
(knee up:1.35), (spread legs:1.35), (arm up:1.4),
(clenched hand:1.35), (closed eyes:1.4), (open mouth:1.35),
(screaming:1.4), (furrowed brow:1.35), (midriff:1.35), (navel:1.3)
```

`(flailing:1.4)` is borrowed from `fall`, which is the only other pose in
this file whose subject is a body not in control of itself, and it is
paired with `(motion lines:1.3)` for the same reason it is there: motion
lines are a comic convention, drawn as separate marks BY DEFINITION, and
this is the tag that says the limbs are moving rather than posed. Note for a
later sweep -- `headcount.py` counts marks, and its own docstring says a
pose carrying motion lines could not be counted by the tool it replaced.

THE HEAT IS NOT ON HER FACE ANY MORE, and that is a correction rather than a
drift. The first sweep had `(sweat:1.35)` and `(full body:1.45)` and read as
a girl lying down being warm; the reference the user then posted is a
TANTRUM -- both fists and both knees in the air, eyes clamped, mouth wide --
where the heat is carried by how hard she is thrashing. Both slots were
spent on that: `legs up` for the knees, `closed eyes` for the clamp. `full
body` goes free (a landscape canvas with a lying figure frames her anyway;
`sip` measured the same slot spare at its square) and the sweat goes
knowingly.

`(closed eyes:1.4)` over `(>_<:1.4)`, swept head to head. `dizzy` proved
this model reads face symbols as tags -- `@_@` is real to it -- so the
symbol was the favourite and it lost. `b2370dcc` is the picked render.

Note what closing her eyes costs: FACE's `(tareme:1.3), (large eyes:1.3),
(large iris:1.25)` are all instructions about eyes that are now shut.

This is also the one framing in the file where the flat grey backdrop is not
a compromise. Shot straight down, SURFACE's `(simple background:1.3)` IS the
floor she is lying on, so the pose gets a real setting for free where every
other pose is standing in front of nothing.

## Eighteen tags, then fifteen

EIGHTEEN TAGS, the longest block in this file, and it got there one
reference image at a time. The order it was built in is the order the asks
arrived, and each step is a measured arm rather than a guess:

- closed eyes over `(>_<:1.4)`: `b2370dcc`, swept head to head. `dizzy`
  proved face symbols are real tags to this model, so the symbol was the
  favourite and it lost.
- EVERY LIMB TAG IS SINGULAR: the reference is asymmetric in all three: one
  fist and one open hand, one knee high and one low, one arm up and one
  down. This file already carries both forms -- `kick` has `knee up`,
  `situp` has `knees up`; `peace` has `outstretched arm`, `flop` has
  `outstretched arms` -- so naming one of a pair is an established lever
  here, not a hopeful one.
- kicking AND foreshortening: the limb argument and the camera argument.
  Shot from above, a leg thrown up is a leg thrown AT the viewer; `kick`
  uses this tag at 1.3 for the same geometry.
- screaming + furrowed brow: `fall` names its emotion beside its open mouth
  rather than trusting the mouth; this does the same.

`thin eyebrows` is deliberately still in FACE. `(furrowed brow:1.35)` is
about the SHAPE the brows make and not their weight, and pulling both at
once is how a face gets changed without anyone knowing which lever did it.

IT WAS EIGHTEEN TAGS AND IT IS FIFTEEN, because the subject was misread and
the two reference images are what misread it. They are tantrum
illustrations; 「暑いので大暴れはしていないです。微動」 is the actual pose.
`(motion lines:1.45)` and `(kicking:1.4)` came out and `flailing` went 1.55
-> 1.25 on that -- the whole violence axis, turned down.

`(foreshortening:1.3)` came out for a different and more interesting reason.
It was added while the leg was being SNAPPED up, to draw a limb thrown at
the camera, and it was correct then. When the knee eased to 1.35 nothing
removed it, so a camera distortion was being applied to a leg that is barely
raised, and 「足の長さが不自然」 was the result. Swept against a negative
`(long legs:1.4)` and against easing BODY, and taking the tag out is what
fixed it. A camera tag left behind after the pose it was for has gone is
worse than no camera tag at all -- this file has plenty of notes about tags
that are wrong and this is its first about a tag whose supporting setting
was removed from under it.

The length is a real risk and is not the same risk as the tag count. There
is no ceiling -- `kick` runs 13 and is fine -- but a longer block dilutes
every tag in it. If the face or the arms go weak later, suspect the length
before suspecting whatever was added last.

## Inline note on the pose block

`(flailing:1.25)` was here and is gone with the effect lines. It is the one
word left in the block that a speed line is the standard drawing of, and the
negative guard alone did not finish the job. What it cost is recorded rather
than guessed at: on `555666777` the backdrop stopped being flat at all --
0.1% floods, against 29.3% with the tag -- so this tag was holding the plain
background up on at least one seed, and the delivery repaint cannot fix what
it cannot flood. The pose survives it because `knee up`, `spread legs` and
`arm up` are the shape, and 微動 is the ask.

## Record

Canvas `(1536, 1024)`, `own_eyes=True`, `open_mouth=True`.

The reference's mouth is the biggest thing in the face, and the eyes are
clamped shut -- FACE was settled on a composed girl and these two tags are
the opposite of a tantrum. `face_edits` removes `small mouth, ` and removes
`, looking at viewer`.

`prone`'s argument pointed at length: the from-above camera made the legs
read long, and `petite` answers proportion as a whole. Swept against
removing the camera tag alone -- both were needed (`d35a67f8`). `body_edits`
replaces `(petite:1.2)` with `(petite:1.4)`.

「部屋でジタバタしているので」: white high tops are outdoor shoes. A
SUBSTITUTION in the footwear slot, not a removal -- `no shoes` means a foot
still wearing its tights; `barefoot` would strip them. Gated on the costumes
that have shoes; a `default` swelter has never been rendered and gets no
invented slot. `character_edits` replaces `(white footwear:1.4), (sneakers:1.45),
(high tops:1.3)` with `(no shoes:1.35)` (gated `shod`).

「シャツも少しお腹が見えてしまってる感じで」, and the provenance tail was the
thing in the way (its own note prices the release at zero). `(cropped
jacket:1.45)` stays -- different garment, and the garment is a contract.
`negative_edits` removes `, (midriff:1.35), (navel:1.3)` at stage
`S_POSE_GUARDS`.

「効果線は削除して」. Nothing in the positive asks for them -- `flailing`/
`screaming` supply the convention on their own. Speed lines are a drawn
object with a name, which is what a guard has always been able to take out.
Three names because the model does not treat them as one. `negative_edits`
appends `, (motion lines:1.5), (speed lines:1.5), (emphasis lines:1.45)` at
stage `S_POSE_GUARDS`.

「右腕が変な色になってる」: the flat was never laid down, and 0.60 has
nothing to resolve until the state is named. Four names because
sketch/lineart are the medium, unfinished the state, monochrome what an
unpainted region is. Pass 2 only -- the picked composition is not re-rolled
(`174ce1dc`). `hires_negative=HIRES_NEGATIVE_PAINT`.
