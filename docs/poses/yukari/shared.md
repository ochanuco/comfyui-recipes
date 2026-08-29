# shared

The module-level constants shared across multiple poses, extracted from
`src/comfyui_recipes/domain/yukari/poses.py`, plus the experiment history
attached to them.

## SCENE_TRAIN and CROWD_BAN

```python
SCENE_TRAIN = "(train interior:1.4), (vehicle interior:1.3), (window:1.2)"
CROWD_BAN = "(multiple girls:1.5), (2girls:1.5), (crowd:1.4), (people:1.4), "
```

`doze` is the one place a SCENE replaces the backdrop, and it is a deliberate
break of the contract everything else in this file keeps. `ride` puts her on a
bike in front of nothing and `hoops` keeps the court out, because SURFACE is
flat and a scene fights it. `doze` was swept BOTH ways at 1152 on four seeds
-- one arm on the grey backdrop, one with this splice -- and the picked
render is `b393e171`, from this one. The contract lost a measurement rather
than an argument, and it lost on exactly one pose.

It replaces `(simple background:1.3), (grey background:1.2)` and nothing
else: `(flat color:1.3)`, `(white outline:1.6)` and the shading pair stay,
which is why the carriage arrives as pale line and stripe rather than as a
photograph.

`train_interior` 11.4k, `vehicle_interior` 1.2k, `window` 179k. The window is
the weakest weight of the three on purpose -- it is 179k of pictures that are
mostly NOT trains, so it is here to put light behind her and not to name the
place.

Two things this costs, both real and both paid: `recolor_bg.py` has nothing
to do here (there is no flat backdrop left to set), and `headcount.py` cannot
be pointed at this pose at all -- it takes the background colour from the
border pixels, so seats and poles count as figure.

A carriage is a room whose entire subject is other passengers, and
`(solo:1.5)` has never had to hold against a background that implies a
crowd. `CROWD_BAN` goes in front of NEGATIVE for the reason the rest of this
file's guards do: token order changes the encoding, and this is the order
`b393e171` was drawn in.

For the pose-level side of this story (why `doze` earns the swap, the square
canvas, the settled seed), see `doze.md`.

## GAO_HANDS / GAO_FACE

```python
GAO_HANDS = "(claw pose:1.55)"
GAO_FACE = "(open mouth:1.4), (fang:1.3)"
```

THE がおー, as a part rather than as a spelling. `roar` was the first pose to
wear it and it is not going to be the last, and a family of poses that each
write out their own copy of the same three tags is the state this file was
in before the costume blocks existed: change one, and the others quietly do
not change with it.

Two fragments and not one, because the hands and the face do not sit next to
each other in the order `roar` was rendered in -- `(hands up:1.35)` and
`(leaning forward:1.3)` are between them, and token order changes the
encoding. Splitting it here is what makes it a no-op: `roar` is assembled
from these and is byte-identical to the string that drew `f38695b8`.

## _LIMB_TRIO

```python
_LIMB_TRIO = "(extra arms:1.5), (extra legs:1.5), (extra limbs:1.5), "
```

The extra-limb trio: `extra limbs` unweighted in NEGATIVE stopped neither a
third arm at 2048 nor a fourth leg on a print; the weighted names are what
worked (`hoops`, then `winded`).

## _CRISS_CROSS

```python
_CRISS_CROSS = Edit("replace", "(drawstring:1.4), ",
                    "(drawstring:1.4), (criss-cross halter:1.45), ",
                    gate="dressed")
```

The dress's straps: a halter that crosses at the chest and ties behind the
neck, official design. Globally the tag costs the coat its shoulders, so it
is per-pose; one tag, not `nape`'s two -- the three-tag form pulls the
camera in (`boss`), and the backdrop intruders it invites are repainted at
delivery anyway (`recolor_bg.py`).
