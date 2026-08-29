# doze

バスケ帰りの電車で寝落ち. `hoops` と `winded` の続き -- the same gym kit one
train ride later, and the state has gone from gasping to spent.

```
(solo:1.5), (sitting:1.5), (sleeping:1.5), (sleeping upright:1.45),
(closed eyes:1.45), (head tilt:1.4), (zzz:1.35),
(bench:1.3), (arms at sides:1.3),
(towel around neck:1.4), (messy hair:1.3), (sweat:1.2),
(full body:1.45)
```

Counted before use: `sleeping` 100k, `sleeping_upright` 4.3k, `head_tilt`
173k, `zzz` 15.8k, `towel_around_neck` 9.4k, `messy_hair` 91k, `bench` 21.7k,
`arms_at_sides` 38.8k. Two words the scene wants are not tags at all --
`dozing` 0 and `nodding_off`, which has no page -- and `tired` is 0 here for
the third time in this file. `exhausted` IS real at 3.7k and is still left
out: at that count it is a word, and the state is carried by the posture and
the symbol the way `winded` carries panting with `heavy_breathing` and
sweatdrops rather than with a word for being tired.

`(sleeping upright:1.45)` is the pose, and it is the whole reason this is
not `flop` with the camera moved. 4.3k is thin for a load-bearing tag, so it
is weighted ABOVE the 100k `sleeping` under it rather than left to be
outvoted: `sleeping` alone at 100k is a girl in a bed, which is the one
picture this pose must not be.

`(head tilt:1.4)` 173k is the lolled head. It is the tag doing what
`slouching` 1.0k and `head_down` 3.7k are too thin to do -- the same choice
`winded` made when it spelled hands-behind as `arm_support` 118k instead of
the literal 985-post naming.

`(zzz:1.35)` is on the file's idiom rather than on its count: `@_@`, `>_<`
and `flying_sweatdrops` each carry a state the drawing has no other way to
say, and this is the sleep one. `dizzy`'s finding applies to it unmeasured
-- a face symbol has a weight window and THE WINDOW MOVES WITH THE SEED --
so a glyph drawn on the cheek, or no symbol at all, is the first dial to
turn and not a fault in the rest of the block.

The carriage is not in the picture, and that is `ride`'s contract kept
rather than an oversight. SURFACE is a flat grey backdrop; a train interior
is a scene, and a scene whose whole point is a row of other passengers is
also the second figure this file spends canvas width to keep out. So 帰り is
said with what she is WEARING: a towel round the neck cannot fall out of the
composition the way a loose bag can, which is `sip`'s finding -- an object
tag puts the object in frame and says nothing whatever about where it ends
up. `(bench:1.3)` is the seat under her, named as an object in front of
nothing, exactly as the bicycle is.

`(sweat:1.2)` is the lowest weight in the block for `winded`'s reason: 763k
and strong, but drawn as SHEEN, which is the axis this recipe keeps having
to take gloss off. First tag to cut if the skin comes back shiny.

NOT SWEPT. Three things to look at first: a `bench` that arrives as a park
bench, the camera -- no framing tag is spent here, and `chair` records a
square not anchoring one on its own -- and the eyes, since FACE's `looking
at viewer` is spliced out in `positive` for `nape`'s reason and it is the
one instruction that would undo the pose.

For the background splice that this pose actually uses (`SCENE_TRAIN` /
`CROWD_BAN`), see `shared.md`.

## Record

Canvas `(1152, 1152)`, `own_eyes=True`, `settled_seed=737373737`.

The only square doze earns: asleep she is compact, and the empty half of a
wider canvas is where a second figure gets drawn.

Eyes shut: `looking at viewer` has no referent and either argues or opens
them. `small mouth` STAYS -- asleep it is the smallest thing in the face,
the expression rather than something in the way. `face_edits` removes `,
looking at viewer`.

The one SCENE in the file, and a measured break of the flat-backdrop
contract: swept both ways at 1152 on four seeds, and the picked render
(`b393e171`) is from this arm. Only the background pair is replaced -- flat
color, white outline and the shading pair stay, which is why the carriage
arrives as pale line rather than as a photograph. Costs `recolor_bg.py` and
`headcount.py` their jobs on this pose. `surface_edits` replaces `(simple
background:1.3), (grey background:1.2)` with `SCENE_TRAIN` (see
`shared.md`).

A carriage is a room whose subject is other passengers, and `(solo:1.5)`
has never had to hold against a background that implies a crowd. In front --
the order `b393e171` was drawn in. `negative_edits` prepends `CROWD_BAN`
(see `shared.md`) at stage `S_CROWD`.
