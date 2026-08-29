# snack

菓子パン, sitting down. `straw`'s vessel grammar one size smaller, and every
slot does the same job it does there:

```
(solo:1.5), (sitting on chair:1.45), (front view:1.35),
facing viewer, (holding food:1.45), (melon bread:1.5),
(eating:1.4), (full body:1.45)
```

- `(holding food:1.45)` is `holding cup`. It puts the thing in her hand and
  says nothing at all about where the hand then goes.
- `(eating:1.4)` is `drinking`: the tag that lifts it to the mouth.
- `(melon bread:1.5)` is the second naming, and this is the case `ride` paid
  for rather than the one `straw` got free. Bare `bread` draws a loaf or a
  slice -- danbooru has `bread` at 21k and `bread_slice` at 5.5k -- and
  neither is a 菓子パン. `melon_bread` at 1.5k is the archetype, and the
  only sweet roll there with a count worth spending a slot on (`cream_bread`
  143, `curry_bread` 66).

The chair is NOT named twice, and that is the same judgement seen from the
other side: a plain chair is what the model reaches for unaided, like
`straw`'s paper cup. `chair` spends `gaming chair, swivel chair, backrest`
because a gaming chair is not the default one. That is `ride`'s road bike,
and it is not this.

Seated because standing could not keep its shoes on. 「パンを食べてるとき
に靴は触っちゃダメよw 椅子に座って食べるのもOK」. The other arm of the
first sweep was a `cowboy shot`, which crops at the thigh -- and the sporty
costume's `(white footwear:1.4), (sneakers:1.45), (high tops:1.3)` then had
no referent, while `holding food` was sitting there as an open slot for an
object. She was drawn holding a sneaker in 2 of 4 seeds and standing over a
loose one in a third. Deleting the three tags fixed it 4 of 4, which is the
`HEAD_FRAMINGS` rule one crop shallower: naming what is out of frame is what
invites it back in. This pose needs no such deletion, because the feet are
in frame -- it is the framing that makes the costume honest again, not a
guard.

In `open_mouthed`, against `straw`'s reading of the same question: lips
close around a straw and a bite does not. FACE's `closed mouth` is removed
rather than replaced -- nothing here asks for `(open mouth)` -- so a bite is
permitted and a shout is not commanded.

## Record

Canvas `(1024, 1536)`, `open_mouth=True`, `paint_finish=True`,
`hires_negative=HIRES_NEGATIVE_PAINT`.

No further edits are recorded on this pose's record entry beyond those
parameters.
