# chair

Sitting on a gaming chair with her legs crossed, facing front.

```
(solo:1.5), (sitting on chair:1.4), (crossed legs:1.2), (front view:1.35),
facing viewer, (gaming chair:1.4), swivel chair, backrest, full body
```

This block is not new here. It is the one kept as `pick/yk-chair-151`,
`pick/yk-chair-111` and `pick/yk-chair-555` -- three seeds, settled on the
older `queue_dq3` recipe against this same base, and passed as `--pose-text`
rather than ever being written down as a pose. Porting it in is the whole
change; every weight below was measured there and none of it was re-run.

What it replaces was `peace` moved off the floor and onto a chair (`sitting`
+ `on chair` + the double-V hands). That went one clean seed in four --
rabbit plushies, a low camera on the thighs, the dress swapped for a hoodie,
and three chibi clones -- and nothing was ever picked from it. The floor
version is still there as `peace`, seven seeds of seven.

Four measurements this block carries, all of them costly:

- `(crossed legs:1.2)`, NOT 1.35. At 1.35 the model draws the crossing
  rather than the legs and a third leg appears. Banning it -- `(extra
  legs:1.6), (three legs:1.5)` -- did not help, because the weight was the
  problem and not the absence of a ban.
- The chair is one word. Asked for as a five-tag block -- `(gaming
  chair:1.45), racing seat, (high backrest:1.3), headrest, armrest` -- it
  returned a full-frame noise field, and so did this block plus `leaning
  back, hand on own knee`. Substituting `(office chair:1.35)` for `(gaming
  chair:1.4)` at the same tag count drew a proper racing seat instead, and
  threw in a controller nothing had asked for.
- Nine tags, and the ninth is load-bearing in both directions. At twelve the
  pale thighhighs are pushed out and one dark tights is drawn instead -- the
  legwear is the first thing this block spends.
- Bare `full body`, NOT `(full body:1.4)`. render-notes recommends the
  raised form off three seeds, and `pick/yk-chair-gradient` records the same
  substitution alone collapsing the two legwear layers into one stocking.
  Ported with the raised form first and the collapse reproduced on
  `151515151`; reverting it brought the layers back on that seed. Two picks
  disagreed about one substitution and the unfavourable one was right.

One tag had to go to make room for `(solo:1.5)`, which leads every entry
here and is worth its slot -- it took clones from five of eight to none.
`looking at viewer` is the one dropped, because FACE already supplies it;
`lap` omits it for the same reason. Nine tags in, nine tags out.

1024x1024, where the picks were 2:3. The look was drifting flat next to
`sip` -- no highlights, no modelling -- and that is a framing property, not
a style one. Stroke is a constant 1.91px at every canvas this recipe uses
(see the module docstring), so a figure drawn small carries a line that is
heavy relative to her head and has no pixels left to shade in. The square
puts her back at `sip`'s scale and the shading returns with her.

NOT SETTLED, one clean seed in three. `111222333` holds the front view with
the chair whole; `151515151` keeps everything but swings to three-quarter;
`555666777` brings the camera in on the legs and loses the composition. The
framing tags are what the square is spending, and `full body` at any weight
does not anchor them -- it was tried both ways here.

Unmeasured here: the picks ran `--face moe-far-noeye`, and this recipe has
one fixed FACE block. The backdrop intruder that owned an earlier chair
pose answered only to the face lever, so if it comes back, that is where it
lives -- but none of the twelve renders here had one.

## Record

Canvas `(1024, 1024)`.

No further edits are recorded on this pose's record entry beyond that
parameter.
