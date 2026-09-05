# home

映画とカフェのあと、ショッピングモールで服を買って帰宅し、ビーズソファーに
沈んで「あ゛ーーー」と息を吐くゆかりさん. A `yukari-sketch` pose derived
from `cafe`: the same outing costume and canvas, with the table and the
cheek on the hand replaced by a bean bag chair and shopping bags, and the
question replaced by a groan.

```
(sitting:1.3), (bean bag chair:1.5), (sinking:1.2), (leaning back:1.25),
(from above:1.2), (slouching:1.25), (arms at sides:1.15), (limp:1.1),
(shopping bag:1.25), (paper bag:1.15), (upper body:1.25)
```

```
(tareme:1.2), (jitome:1.15), (half-closed eyes:1.25), (head back:1.3),
(looking up:1.15), (open mouth:1.25), (exhausted:1.25), (sigh:1.15),
(blush:1.1)
```

`bean bag chair` at `1.5` with `sinking` is what keeps the seat from being
drawn as a couch: at the recipe's usual weights the tag is too weak and the
render falls back to a sofa with a backrest. `(from above:1.2)` is the
angle a bean bag is seen from, and it also gives the thrown-back head
something to look up at.

The tiredness is in the body as much as the face: `slouching`, `arms at
sides` and `limp` drop the arms onto the seat, and `head back` with `open
mouth` and `exhausted` is the groan. `looking at viewer` is deliberately
absent -- she is looking at the ceiling. `tareme` and `jitome` stay, at a
slightly lower `jitome` than `cafe`, so the half-closed eyes still read as
hers.

The shopping bags say where she has been. There is no room in the prompt:
the background stays the recipe's `simple background, grey background`, and
the bean bag and the bags are the scene.

Against the same arms on a couch (with and without `sleepy`), and the same
bean bag with a tired closed-mouth face, this is the arm the user picked on
seed 7 (chimera ptckar); the other arms were not rated.
