# prone

Face down on the floor, chin in her hands, feet swinging up behind her.

```
(solo:1.5), (lying:1.45), (on stomach:1.5), (from above:1.35),
(chin rest:1.35), (feet up:1.3), (smug:1.35), (half-closed eyes:1.3),
full body
```

`lying` and `on stomach` are one unit -- the second is a qualifier for the
first and is not used alone -- so the posture costs two slots before
anything else is asked for. `chin rest` props her up on her elbows and `feet
up` lifts the shins; together they are what separates this from a body face
down on the ground. Eight tags after `(solo:1.5)`, which is the budget every
block here is held to.

The steadiest pose in this file on first measurement. Six seeds, six with
one girl, six lying face down with the chin on the hands and the feet up, no
clothing failures and no bare skin. `crouch` needed eleven seeds to earn
that sentence and `hunt` never did.

Stroke per 1000px over the six: 1.72 and 1.75 at the fine end, 1.94 and 1.99
in the middle, 2.18 and 2.20 at the heavy -- straddling the recipe's 1.91, so
nothing here breaks the line. (Median is 2.00 on all six and says nothing; a
median over small integers is a vote, not a measure.)

`737373737` is the loosest of the six and worth knowing about: the hem rides
up over the hip and the grey tights carry the whole lower half of the frame.
Covered, but it is the seed closest to the rear-forward framing this project
has thrown compositions away over. `555666777`, `111222333` and `2557902837`
are the clean ones.

`from above` is at 1.35 rather than the 1.45 `nape` uses. She is already
horizontal, so the angle only has to look down at her -- raised, it is the
tag most likely to buy the overhead rear view that the portrait canvas drew
on its own (see SIZES).

`--hires 2048` at the default denoise, and that is a correction. The
measurements are unchanged -- the second pass takes the stroke from 1.941
per 1000px to 1.274 and redraws the die-cut edge as a stroke rather than a
cut -- but "this canvas already lands on 1.91, so the pass has nothing to
give" was a conclusion drawn from a number, and the thinner, looser line is
the one that was picked. 1.91 is what `fb-b` measured, not a target the
recipe is aiming at.

0.45 is not the same thing softened; it scribbles the outline instead of
drawing it, and 3072 blurs it to a halo. The line that was wanted is 2048 at
0.60 specifically.

The six-seed sweep above predates the legwear splice in `positive()`, so its
"no clothing failures" is about the pose block and not about what the grey
layer was doing behind it.

## Record

Canvas `(1536, 1024)`, `own_eyes=True`.

A body on the floor earns the landscape canvas: 1024x1024 cropped her and
doubled the relative stroke, 1024x1536 drew the rear-forward composition
from the canvas alone. Same 1.57M pixels, on its side.

「めちゃ下半身太ってしまった…」: straight at the rear, foreshortened, BODY's
hip/thigh tags read as bulk. EASED, not deleted -- pushing further (0.6/0.6
+ petite/waist raises) drew the rabbit intruder. `body_edits` replaces
`(wide hips:1.3)` with `(wide hips:1.0)` and `(thick thighs:1.35)` with
`(thick thighs:1.05)`.
