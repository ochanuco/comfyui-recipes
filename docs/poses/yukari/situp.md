# situp

「腹筋が全くできないゆかりさん」. The joke is a NEGATIVE result -- the
picture has to show the sit-up not happening -- and nothing in this file has
drawn a failed action before. Every other pose here is a state she is in;
this one is an attempt that does not come off, and the whole block is built
around which half of it the model must not complete.

```
(solo:1.5), (sit-up:1.5), (from side:1.35), (lying:1.45),
(on back:1.4), (knees up:1.4), (hands behind head:1.35),
(slouching:1.35), (clenched teeth:1.35), full body
```

Four tags set the apparatus and they are the ones `flop` already proved:
`(lying:1.45), (on back:1.5)` put her down, `(knees up:1.4)` bends the legs
the exercise needs, `(hands behind head:1.35)` is the sit-up's own arm
position and is a 200k-post tag, unlike anything naming the exercise.

`(sit-up:1.3)` is deliberately the WEAKEST of them. It names the feature --
without it the four above read as lying down comfortably -- but raised it is
the tag most likely to draw the successful rep, which is the one picture
this pose must not produce. If she comes up off the floor, this is the
weight to lower before touching anything else.

The strain is `(clenched teeth:1.35)`, and it costs `closed mouth` out of
FACE (declared in `costume_check`, `open_mouthed` in `positive()`). A smug
半目 is this character's default and it is exactly wrong here: composure
reads as a rest, not as a failure. `(sweatdrop:1.3)` over `sweat` on purpose
-- the anime bead is a comic marker, where `sweat` buys wet shine and this
recipe is flat colour.

Untested, and the two things to watch on the first sweep are the costume and
the camera. A sit-up recruits a gym: the negative carries a sportswear guard
for this pose, because the costume is a contract and an exercise scene is
the strongest pull away from it this file has tried. No angle tag is spent
yet -- `flop` holds a body on the floor at this canvas without one -- but a
side view is what reads "shoulders still down", so `(from side:1.3)` is the
first lever if the camera looks straight down and flattens the failure out
of the picture.

## 「筋肉がなさすぎて猫背になってしまう」

The punchline moved. The first block's failure was "she does not come up";
this one's is "she comes up WRONG" -- no core to lift with, so the spine
rounds and the neck does the work. That is a shape, and a shape is drawable
in a way that an absence is not.

`(slouching:1.4)` took `(sweatdrop:1.3)`'s slot rather than being added to
it. Nine tags is where this file's blocks start losing things, and the bead
was the one tag in here that decorates rather than describes -- the strain
still has `(clenched teeth:1.35)` carrying it.

ONE tag for the feature. `(hunched over:1.4)` names the same thing and the
pair of them is exactly the shape that cost the toe work its accents; it is
the B arm in `.local/situp_arms.py`, not a second guard here.

The negative gains `(arched back:1.4)` for this pose, and it is the
load-bearing half of the change: 猫背 has a direct opposite, this model
reaches for it unprompted on anything lying down, and `stand` spends a
positive tag on that arch on purpose. Naming the shape without forbidding
its opposite is half a lever.

## 「腹筋要素が0になった」

And this file has the note that predicted it. The toe work ends with "a
guard is a deletion, and what it deleted was the feature rather than the
surplus. Zero is not five." The same mistake, arrived at from the positive
side: `(sit-up:1.3)` was pinned at the BOTTOM of the block on the argument
that raising it would draw a successful rep -- and the failure mode that
actually turned up is the one where the exercise is not in the picture at
all. A rep drawn too well is a note to write; no rep is no picture. Do not
spend a weight defending against a feature's excess before the feature has
been shown to appear.

Three changes, all the same change -- move weight off the state and onto the
action:

- `(sit-up:1.5)` raised, and moved to the slot straight after `(solo:1.5)`.
  It is the subject; at position six behind two tags that say she is lying
  down it was a footnote.
- `(on back:1.4)` lowered from 1.5. A crunch is not flat, and this tag was
  saying "resting" louder than anything was saying "exercising".
- `(slouching:1.35)` eased a notch, for the same budget reason: it won the
  last round outright and that is the problem.

`(yoga mat:1.3)` came OUT of this pose's negative. It was aimed at the
wardrobe and took the scene with it.

## Picked: a61a67a8, seed 1886970040, the F arm

`(from side:1.35)` is IN the block, and it is what the pose was missing for
three rounds. It was named as the first lever the day the pose was written
and then not taken, twice, while three rounds of weights argued about words
instead. A sit-up is a silhouette before it is a tag: bent knees and a torso
at an angle read as the exercise from the side and as a girl lying on the
floor from anywhere else. No weight on `sit-up` buys that geometry, because
it is the camera and not the subject.

NINE tags after `(solo:1.5)`, against the eight this file keeps quoting.
`kick` held thirteen and this held nine; the budget is a smell, not a rule,
and the tag that pushed it over is the one doing the work.

## Record

Canvas `(1536, 1024)`, `open_mouth=True`.

The exercise brings its own wardrobe; keep the gym out without arguing with
it. Released for the shod costumes -- `sporty` IS a gym kit -- but a tee and
dolphin shorts is loungewear, so `roomwear` keeps the guard. `(yoga mat:1.3)`
is deliberately gone: a mat is FLOOR, and banning it helped 腹筋要素 to zero.
`negative_edits` appends `, (sportswear:1.45), (gym uniform:1.4)` gated
`default_or_roomwear` at stage `S_POSE_SCENE`.

猫背's opposite, the posture this model volunteers for a girl on her back.
`stand` pays a tag to GET this arch; here it is the whole defect.
`negative_edits` appends `, (arched back:1.4), (bridge (pose):1.3)` at stage
`S_POSE_SCENE`.
