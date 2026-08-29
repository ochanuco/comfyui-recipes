# dizzy

「寝不足ゆかりさん。目にクマがあってぐるぐる目」 -- `allnighter`'s crop and
`allnighter`'s クマ, with the dead eye swapped for a spinning one.

```
(solo:1.5), (portrait:1.5), (head and shoulders:1.4), (close-up:1.2),
(face focus:1.3), (@_@:1.0), (eyebags:1.55), (tired:1.3),
(dizzy:1.3), (open mouth:1.35)
```

It is a SUBSTITUTION and not an addition, which is this file's cheapest kind
of change: the framing five are untouched, `eyebags` stays at the 1.4 it
holds in every exhausted pose here, and the two tags that describe how the
eye is drawn are the two that leave.

- `(@_@:1.0)` is the tag, and 1.0 is the whole finding. ぐるぐる目 is `@_@`
  on danbooru; `spiral eyes` and `dizzy eyes` are not tags there, and it
  draws -- at 1.45 it draws a near-black spiral on a white sclera that takes
  the entire face (「強調されすぎて視線誘導されてしまう」). That 1.45 was
  inherited from `empty eyes`, which is SUBTRACTIVE -- it removes the
  highlight -- while `@_@` is additive, so the weights were never
  like-for-like. Walked down 1.45 -> 1.3 -> 1.15 -> 1.0 on one seed, and 1.0
  is the render that was picked (`49b3aab4`). At 1.0 the spiral is no longer
  drawn as a stroke: what is left is the wide flat eye it comes with, under
  the クマ. Kept in the block anyway, because it is in the accepted render
  and this file does not delete tags on a null measurement -- see the
  thin-line tags.
- `half-closed eyes` has to go. A lid at 1.35 covers the thing the request is
  about. `allnighter` raised it for the droop; here the droop is carried by
  `eyebags` and the mouth, and the eye has to be open to show anything at
  all.
- `(eyebags:1.55), (tired:1.3)` is the クマ, and it took two words. `eyebags`
  at the 1.4 every other exhausted pose here uses drew two faint strokes;
  1.55 and 1.7 alone did no better. Adding `tired` beside it at 1.55 drew
  the shadow as a dark mass under both eyes on the first try. More weight was
  the wrong lever and a second word was the right one, which is the reverse
  of what the クマ was expected to need.
- `(dizzy:1.3)` outlived the swirl it was hired to support. It went in as a
  floor under `@_@` -- a real tag for the state, in case the symbol was
  punctuation the model never learned. The symbol turned out to be real and
  had to be walked back instead, and `dizzy` is what now carries ぐるぐる as
  a state rather than as a drawn line.
- `(open mouth:1.35)` is kept, unweighted from `allnighter`. A ぽかん mouth
  is what 寝不足 looks like from the front, and it is the one departure from
  FACE that all three exhausted poses here already make.

Ten tags, one over `allnighter`'s nine, and the extra one is `tired` -- the
tag that turned out to be doing the work. No desk, no night, no motion
lines: SURFACE is a grey background and the state is on her face.

Settled on seed `737373737` (`49b3aab4`), picked for its art style first and
then tuned twice on that one seed without re-rolling.

## Record

Canvas `(1024, 1024)`, `own_eyes=True`, `framing="head"`, `open_mouth=True`.

No further edits are recorded on this pose's record entry beyond those
parameters.
