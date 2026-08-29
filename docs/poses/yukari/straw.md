# straw

ストローで紙コップのドリンク. Built on `sip`'s measurements rather than on
`sip` -- that pose is a side-on squat with a china mug and shares nothing
with this but the fact that something is being drunk.

```
(solo:1.5), (standing:1.45), (from front:1.3), (holding cup:1.45),
(drinking straw:1.55), (drinking:1.3), (full body:1.45)
```

Three findings from that pose are load-bearing here:

- `drinking` is what LIFTS the vessel to the mouth. Without it `holding cup`
  puts the cup in her hand and the hand stays down; on one sweep the can
  ended up at her feet in four of four.
- `holding cup` alone draws a paper cup or a can, which is the vessel this
  pose wants -- so the noun is nearly free here where `sip` had to spend a
  slot on `coffee mug` to get china.
- Naming the vessel twice is what pins the type, and is also what drew two
  of them on `1117511306`. It was tried here -- `(disposable cup:1.5)`
  beside `holding cup`, four seeds against four without it -- and `9082bedc`
  was picked off the arm WITHOUT it. The second noun bought nothing this
  pose needed, so it is gone. `sip` had to spend that slot to get china; a
  paper cup is what this model reaches for unaided.

This block used to claim that `(logo:1.4), (print:1.35)` are in NEGATIVE and
that they are why the cup comes out plain. They are NOT in NEGATIVE. They
are appended by `_negative_base` for `stand` and for no other pose, so
`straw`'s plain cup is the model's own doing and has no guard behind it. The
claim cost a real render to disprove: the sporty tee arrived with a
watermelon print on `snack`'s sweep, on a pose that has no such guard, which
is what a costume relying on this would look like.

NOT in `open_mouthed`: FACE's `closed mouth` is correct with a straw -- lips
around it, not a shout.

## Record

Canvas `(832, 1664)`, `paint_finish=True`, `hires_negative=HIRES_NEGATIVE_PAINT`.

`174ce1dc`'s finish, carried whole -- see `PAINT_FINISH` in `recipe.py` for
why it is one decision, not two.
