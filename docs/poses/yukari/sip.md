# sip

A full squat seen from the side, curled forward over her knees with a mug
held in both hands at her mouth.

```
(solo:1.5), (squatting:1.4), (from side:1.45), (hunched over:1.45),
(smug:1.3), (holding cup:1.3), (drinking:1.2), (coffee mug:1.3)
```

Built by substituting into `crouch`'s eight slots one at a time, and every
slot here was paid for:

- `drinking` is what lifts the cup to her mouth. Dropped in favour of
  `leaning forward`, on the theory that `holding cup` plus the mouth would
  carry it, the cup fell to her feet on all four renders. It stays.
- The mug needs two slots, not one. `coffee mug` alone put a mug in the
  frame but not reliably in her hands; `holding cup` alone drew a paper cup
  or a can. Together they draw a china mug, and on some seeds steam off it
  -- which is the whole "ホッとしている" read, at no extra tag.
- `leaning forward` is not how she rounds. It bends her at the hips, so the
  back stays straight and folds, and `hunched over` is what curves the
  spine instead. `slouching` does the same job and was tried in the same
  slot; `hunched over` won on all three seeds.
- `smug` was spared at first, on the reasoning that she is warming up rather
  than showing off. That was wrong, and not about the mood: it is what
  holds her head up. `hunched over` alone rounds the back but pushes her
  neck out ahead of it, so the silhouette reads as a bend rather than a
  curve. The smirk lifts her chin, and head, spine and hip land on one arc.
  Two things asked for -- the smirk, and a rounder shape -- and one tag
  answered both.
- `full body` is what pays for it; the square canvas frames her anyway.
  `knees to chest` is still spared, since `squatting` holds the tuck.
- A ninth slot is where this block breaks, and both candidates for one were
  measured: `curled up` and `knees to chest` each stretched her sideways
  instead of curling her, and the cost came out of tags that were working --
  the mug sank out of frame under one, and under the other her hair clips
  slid down to her ears. The saturation is not only a pose budget. It
  reaches the character.

Seed-sensitive, and the sensitivity belongs to the block rather than the
seed: this block puts the cup at her mouth on `111222333`, while the
tighter-curl variant put it on the ground on that same seed three times and
needed `3409564303` instead. The smirk carries across seeds where the arc
does not: three of three drew it, two of three closed the curve, and
`1029384756` sat up straight with the mug steaming anyway.

## Record

Canvas `(1024, 1024)`, `own_eyes=True`.

A side-on squat is about as wide as it is tall; at 1024x1536 she drew small
in a tall empty frame.
