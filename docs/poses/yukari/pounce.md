# pounce

がおー crouched, a beat before it goes off.

```
(solo:1.5), (kneeling:1.4), (one knee:1.45), (from front:1.3), (claw pose:1.55), 
(arms up:1.3), (leaning forward:1.45), (open mouth:1.4), (fang:1.3), 
(full body:1.45)
```

(`(claw pose:1.55)` and `(open mouth:1.4), (fang:1.3)` are the shared
`GAO_HANDS` / `GAO_FACE` fragments -- see `shared.md`.)

`roar` is the shape at rest -- standing, hands beside her head; this is the
same hands and the same face with the body loaded. `(leaning forward:1.45)`
is the highest weight that tag carries in this file and it is doing the work
`roar` gives to `(standing:1.45)`.

`(arms up:1.3)` rather than `roar`'s `(hands up:1.35)`: from a squat the
hands come up from below and the whole arm is in it. Eased, because a crouch
already puts the shoulders where the tag was pushing them.

No low camera, and this is not an oversight: `(from below:1.35)` is in
NEGATIVE for every pose but `lap`, and the one place this file took it out
it had to be taken out by name. A pounce shot from below is the obvious
framing and it is not available without paying for it.

THE STANCE IS A KNEE, NOT A SQUAT. `978fb1f1` was picked off the squat and
then asked for 「片膝は着くくらい」, which is not something a render can be
adjusted into -- the prompt change redraws the picture and a low-denoise
refine cannot build a limb into a new position. So the squat's render was
spent, deliberately, and two arms were swept in the one slot that decides
the stance:

- ka: `(one knee:1.45)` -- one substitution, one slot
- kb: `(kneeling:1.4), (one knee:1.45)` -- the pair

kb won on `9b2dfdf6` (seed `1886970040`), and it is the arm this file's
usual rule argues against: two tags at one defect is how the palette has
been wrecked here before. It is not that rule's case. Those failures were
GUARDS stacked in the negative, outvoting each other's neighbours; this is a
stance named twice in the positive, where `kneeling` is the posture and `one
knee` is which knee. `ka` alone drew the knee on some seeds and a deeper
squat on others, which is the disease this file describes as an unweighted
tag being indistinguishable from an absent one.

`(leaning forward:1.45)` and both paws stay up. A knee down invites the
three-point stance -- one hand to the ground -- and that costs half the
がおー, which is the thing this pose is a member of.

## Record

Canvas `(1024, 1024)`, `own_eyes=True`, `open_mouth=True`.

A squat fills its own width; the 832 argument is about width BESIDE her.
