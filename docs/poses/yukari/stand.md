# stand

Standing, facing the camera, hands behind her back -- the plain 立ち絵 this
file never had.

```
(solo:1.5), (standing:1.5), (from front:1.3), (own hands together:1.35),
(hands up:1.25), (arched back:1.2), (smug:1.35), (half-closed eyes:1.3),
(full body:1.45), (black footwear:1.35), (high tops:1.35),
(wide shot:1.3)
```

Every other pose here sits, lies or squats, so this is the first block whose
figure is vertical in a vertical frame, and the thing to watch on the first
sweep is the crop: a standing body at 1024x1536 is the case `full body`
exists for, and the poses that lost their shins lost them to a canvas rather
than to a tag.

`(from front:1.3)` is here for the same reason `nape` spends a tag on its
angle: standing is the posture the model has the most other ideas about
(three-quarter turns, walking, from below), and this is the one that says
which of them. `(from below:1.35)` is already in NEGATIVE and does half the
job from the other side.

Hands in front at the chest, and nothing held: a prop is a second thing to
get right and the point of a standing reference is the costume. It started
as `(arms behind back:1.3)` -- 「ては出して欲しい。胸あたりに出す感じ」 --
and `own hands together` is the tag for the gesture. `(hands up:1.25)` is
what puts them at the chest rather than at the waist; measured against the
same seed without it, which lands them low. That is the ninth tag this file
keeps warning about and it is spent here on purpose.

`(arched back:1.2)` took `head tilt`'s slot rather than being added to it.
It is here because two renders of the same seed differed only in LEGWEAR's
TOKEN ORDER and one of them stood slightly chest-out -- the posture came
from the encoding, not from any tag, so it is not repeatable and had to be
named to be kept. Measured at 1.2 in this slot, at 1.2 alongside `head tilt`
(nine tags) and at 1.35 in this slot; the first is what was picked. It is a
tag that leans pin-up when raised, which is why the range was swept downward
rather than up.

## ...and then it turned out the legs were not in the frame

`full body` did not hold a standing figure. Measured rather than looked at:
the figure mask ran to the last row of the canvas on every arm, and the crop
was at mid-calf. Two changes, and they are coupled:

- `(full body:1.45)` -- the bare tag was the only thing arguing for the
  whole figure and it lost to the canvas.
- `(black footwear:1.35)` -- at a canvas that DID fit the leg, the model
  ended it in a rounded stump. Nothing in this prompt had ever named a shoe,
  so there was no foot to draw. Naming one draws it -- and it is black,
  which is where the leg is supposed to end anyway.

Ten tags after `(solo:1.5)`, against the eight this file keeps quoting. The
budget was measured on a seated pose in a frame that fit; a standing figure
spends two tags just staying inside the picture.

The footwear is an ADDITION TO THE COSTUME, not a framing tag, and it has
not been checked against the official design. If her shoes are wrong, this
is the tag to argue with -- but removing it brings the stumps back, so it
has to be replaced rather than deleted.

## Record

Canvas `(832, 1664)`, `own_eyes=True`.

832 wide: width beside her is room for someone else to stand. At 1024 three
of six seeds drew a second figure; at 832, one.

The 2026-08-24 lash pair melts THIS pose into foil noise -- full prompt,
every seed, weight-independent; `portrait` and `brush` carry the same pair
and are fine. The negative's `(long eyelashes:1.35)` was isolated and
acquitted. `face_edits` replaces `(eyelashes:1.3), (thick eyelashes:1.35)`
with plain `eyelashes`.

「脚の長さに比重をかけてほしい」. ADDED beside `petite`, not substituted into
it (measured within noise and not picked). The negative route moved nothing
on this axis, twice. `body_edits` replaces `(pale skin:1.25)` with `(long
legs:1.35), (pale skin:1.25)`.

`355f91cf`: straps are the design; the backdrop cost is repaid by
`recolor_bg.py` at delivery. `character_edits` carries the shared
`_CRISS_CROSS` edit (see `shared.md`).

The one pose that names footwear, and it names the settled costume's black
high tops; a shod costume brings its own pair, and both in one prompt is
asking for two pairs of shoes. `pose_block_edits` removes `(black
footwear:1.35), (high tops:1.35), ` gated `shod`.

`negative_base` carries `boss`'s button guard, in `boss`'s slot: prepends
`(buttons:1.4), `.

「靴に柄はいらない」: decal, logo, colour -- three separate defects, so
three guards, measured together on `1886970040`. The ear-like high collar is
WANTED and survives all three. `negative_base` appends `, (butterfly:1.5),
(logo:1.4), (print:1.35)`.

The pale sole: describing `(black sole:1.35)` positively left a white
midsole and added a red flash; guarding the colours works. `sporty`'s shoes
ARE white, `roomwear`'s feet are bare -- gated. `negative_edits` appends `,
(white footwear:1.45), (red footwear:1.4)` gated `default_or_roomwear`.
