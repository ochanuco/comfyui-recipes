# kick

Seated with one leg thrust at the camera, sole first. Built from a reference
the user supplied rather than from a render of this recipe, so nearly
everything below is a first guess and is labelled as one.

```
(solo:1.5), (sitting:1.45), (soles:1.4), (foot focus:1.35),
(foreshortening:1.3), (knee up:1.25), (leaning back:1.25),
(smug:1.3), (confident:1.25), (half-closed eyes:1.25), (open mouth:1.35),
(full body:1.4)
```

THE FOOT GETS TWO SLOTS, not one. `sip` established that the thing a
composition is built around does not fit in a single tag -- its mug needed
`coffee mug` and `holding cup` together, and either alone drew the wrong
object or put it in the wrong place. The same split applies here: `soles`
names what faces the camera, `foot focus` names where the camera looks.
Neither is the picture on its own.

`foreshortening` is bought rather than left to the seed, and it is doing two
jobs. A leg pointed at the lens either compresses or reads as a long leg
lying across the frame -- and reading too long is the failure this recipe
has spent the most on. `nape` found that `sitting on floor` extends the legs
and that a leg extended away from the camera runs the frame; `flop` had to
have its `long legs` weight bracketed from both sides. What was the defect
in both of those is the subject here, so the tag that governs it does not
get spared.

`knee up` is SINGULAR on purpose: one leg folded, one out is the whole
asymmetry. `knees up` raises both and is a different picture.

`couch` is the cheapest thing that makes `leaning back` mean something --
leaning back against nothing is falling. It is not what was asked for (the
leg was), and it is the first slot to spend if the block needs one.

NO FOOTWEAR GUARD, and that is a decision rather than an oversight. `stand`
is the only pose in this file that names a shoe, so nothing here asks for
one -- but nothing forbids one either, and a shoe sole is a different
picture from a pantyhose sole. Guarding it means naming a shoe in the
negative, and `stand`'s own note says that naming a shoe drew one. Find out
whether the guard is needed before paying for it.

`full body` is NOT in the block, and its absence is what the first round is
measuring against. `foot focus` can walk the camera down to the foot and
leave the head out of frame, which is this pose's likeliest failure, and
`full body` is the counterweight every other whole-figure block here
carries. Eight slots is the house size, so the ninth goes in only if the
first round loses the face.

THE EXPRESSION IS IN PASS 1, and it took four rounds and a losing arm to
earn that sentence. It was in `HIRES_POSITIVE` first, on the reasoning that
a late pass buys the face without the posture -- which is true, and was not
the constraint. Copied verbatim from `10915a12`, guard tail and all, a 0.60
pass could not overwrite a face the base image had already drawn calm and
closed-mouthed. Moved here, the same words work. A late pass refines a
decision; it does not reverse one, and an expression is a decision pass 1
makes.

It costs the composition, which is exactly what this pose spent four rounds
refusing to pay. It was paid because the expression had been asked for four
times and had not arrived once.

## The toe question

NO TOE TAG IN THIS BLOCK, and the reason is not the toes -- it is the
palette. Measured across the series at seed `111222333`, mean saturation of
the figure against the costume's own colours:

```
13 tags, no toe tag                 sat  52.5   coat 37.7%  hair 5.0%
+ (toes:1.4)                        sat 113.5   coat 20.7%
+ (five toes:1.6)                   sat 187.8   coat  0.2%
+ (toe scrunch:1.35 / 1.55)         sat 196.9 / 198.9   coat 0.1% / 0.0%
```

The costume colours do not merely shift, they LEAVE. And it is not the slot
count: dropping back to thirteen and to twelve with the toe tag still in
measured 196.0 and 142.3, so the count was a coincidence of the toe tag
always having been the one added last.

NEGATIVE toe guards cost nothing at all -- 40.3, 51.0, 47.7, all at or
better than the clean block. So the axis is not "toes"; it is that a
POSITIVE toe tag pulls this prompt somewhere with a different palette, and
subtraction does not.

DO NOT GUARD THE TOES. 「指が6本あるねえ」 on the sole that is the nearest
thing to the lens, and both sides of the tag axis were spent on it:

- positive: `(five toes:1.3)` rode four consecutive renders. Six toes.
  Naming a number does not count; it failed while the count was wrong in the
  direction it named.
- negative: `(extra toes:1.45)` and `(extra digits:1.45)`, in PASS 1 where
  the topology is decided. Neither corrected the count -- both DISSOLVED THE
  TOES, leaving a smooth sole with no separation at all. A guard is a
  deletion, and what it deleted was the feature rather than the surplus.
  Zero is not five.

So the tag axis is exhausted, and `nape`'s rule applies: when a defect
survives that many prompt levers, stop diagnosing and change tools. The tool
is the seed -- toe topology is a first-pass structural fact, and raising the
first-pass canvas to give the foot more room is the one escape this file has
already measured shut (a second figure at 1280x1920).

`(full body:1.4)` was written OUT of this block on the first round, as the B
arm, with the note that `foot focus` can walk the camera down to the foot
and leave the head out. Four seeds then did exactly that, four times out of
four -- and both renders picked before that were on `2557902837`, which had
been carrying the framing on its own. It is in now, on `fa504c93`.

THIRTEEN TAGS, and this file's own note says a pose block breaks around nine
-- `sip` lost its mug and its hair clips to a ninth. It held here. That is a
data point and not a licence: the next tag added to this block is on thinner
ice than the count suggests, because the four that pushed it past the line
were all expression and none of them touched the pose.

## Inline note on the pose block

`(couch:1.2)` is gone (2026-08-26): the sticker delivery wants the white
band and the marker on HER alone, and the model draws the band around
subject-plus-couch as one thing. No tag un-outlines a couch, so the couch is
what goes. She still gets seated -- the model invents a ledge or sits her on
the frame edge -- and the picked render (`0db8e020`, seed `737373737`) is
this form.

## Record

Canvas `(1024, 1536)`, `own_eyes=True`, `open_mouth=True`, `settled_seed=737373737`.

「つま先のタイツのグラデーションを白ではなく紫に」: only this framing puts
the gradient's light end at the camera. Full colour at reduced weight won
over the pale name at higher weight. `legwear_edits` replaces `(pale purple
pantyhose:1.35)` with `(purple pantyhose:1.15)` (gated `dressed`).

All five as the picked render (`0db8e020`) carried them. The line trio
stopped nothing measurably -- leaving the doodle seed did -- but the pick
was drawn through them. The dress pair is 「肩紐、襟無し、ボタンなし」.
`negative_edits` prepends `(speed lines:1.45), (motion lines:1.4), (emphasis
lines:1.4), (buttons:1.35), (collared dress:1.35), ` at stage
`S_POSE_GUARDS`.

ONE toe guard: she is in opaque tights, so a smooth toe box is the picture
-- five countable toes was the error. The second toe guard flattened every
accent (brightest tenth 89 -> 52); one puts it back (105) and keeps the toe
box. `closed eyes` banned while the positive asks half-closed: `10915a12`
split the pair, forbid shut / ask half. `hires_negative` is `(toes:1.55),
(closed eyes:1.4), `.
