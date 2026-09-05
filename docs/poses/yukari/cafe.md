# cafe

映画のあと、カフェで頬杖をつきながら上目遣いで「映画の感想聞かせて
ください？」と尋ねてくるゆかりさん. A `yukari-sketch` pose derived from
`date`: the same outing costume, with the walk and the cinema props
replaced by a seat at a table, and the smirk replaced by a question.

```
(sitting:1.3), (table:1.2), (head rest:1.35), (hand on own cheek:1.2),
(elbow on table:1.15), (coffee cup:1.15), cup, saucer, (from above:1.1),
(upper body:1.25)
```

```
(tareme:1.2), (jitome:1.2), (upturned eyes:1.3), (looking up:1.15),
looking at viewer, (light smile:1.1), (parted lips:1.2), (blush:1.15),
(head tilt:1.1)
```

The canvas is `1024x1280`, not the recipe's `832x1664`: a seated figure
behind a table framed at the upper body has nothing to put in the lower
half of a 1:2 frame. Against the same face and props on the tall canvas
with `(cowboy shot:1.25)` and sneakers, the bust framing rated better on
every seed but one (chimera 3gascc).

`head rest` is the tag for 頬杖; `hand on own cheek` and `elbow on table`
say where the hand and the elbow go so the rest is not read as a chin on
a fist. `(from above:1.1)` gives the upturned gaze something to look up
at; `(from below:1.2)` is already banned in `NEGATIVE`.

The face keeps `tareme` and `jitome` from `date` but drops `half-closed
eyes`, which fought `upturned eyes`. `parted lips` with a `light smile`
is what reads as asking: the `date` smirk with `closed mouth` plus the
same upturned eyes, on the same canvas, rated no good render on four
seeds.

There is no cafe in the prompt. The background stays the recipe's
`simple background, grey background`; the table and the cup are the
scene, and a location tag is what the sketch recipe's minimal prompt
exists to leave out.
