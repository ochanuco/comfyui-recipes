# crouch

The same search, squatting rather than down on her hands, seen from behind
and slightly above.

```
(solo:1.5), (squatting:1.4), (from behind:1.45), (looking down:1.4),
(picking up:1.3), (from above:1.2), (smug:1.2), full body
```

SETTLED HERE. `--pose crouch --seed 1117511306` reproduces `ns-1117511306`
(prompt `7d231c4f`) pixel for pixel -- verified, max channel difference 0 --
and that render is the target: the design and the pose that carry the
wide-hipped read this character is meant to have.

Three attempts to push it further were run and none are in here:

| attempt | result |
|---|---|
| `(coattails:1.4)` | the coat became narrow straps rather than a spreading garment, several of them on some seeds, reading as jointed legs; two seeds drew a second figure. It is confusable with the hood's own black red-striped ears. |
| `(loose clothes:1.4)` | stroke width went 1.91 -> 3.82 and 7.64, the paint thickened, the dress fell to 5-6% of the frame. It loosens the drawing, not the garment. |
| `(from above:1.2)` out | this one worked -- pale legwear went 47% to 55-75% and the legs come back. Left out only because it changes the picked composition; re-add it if the legs are wanted over the overhead angle. |

Originally from `bk-squat-1886970040` (prompt `3d7376f2`), before the
sticker removal and the coat.

Eleven seeds, all eleven at exactly 1.91px, all one girl, no clothing
failures. `hunt` on the same recipe rode the hoodie up on three seeds of
three and doubled her on one, so the difference is the pose, not luck.

What is NOT stable is the posture inside the pose: some seeds hug the knees,
some pitch the torso much further forward, and the hood's pompom sometimes
lands where the silhouette needs to read. And `(searching:1.2)` does no work
at that weight -- none of the eleven look like they are looking for
anything. It is a settled drawing style around an unsettled action.

## Inline notes on the pose block

`(smug:1.2)` stays. It was swapped for `(expressionless:1.2)` on a reading
of "not showing it off" as "no expression at all", and that took her
character with it -- she is written as confident and hapless, and a blank
face carries neither. The staging is carried by the action and the angle,
not by the face.

`(coin:1.3)` is gone and `(from above:1.2)` is back in its slot. The coins
gave `picking up` something to act on, but cost the overhead angle, which is
also what keeps the hips out of centre frame.

For the record, since it looks like it should be tried: `light smile` and
`looking back` measured 42-48 and 38-44 colours in an earlier block and were
rejected. Re-measured here they come in at 16-23. The rejection was true of
that block, not of the tags.

## Record

Canvas `(1024, 1536)`, `own_eyes=True`.

No further edits are recorded on this pose's record entry beyond those
parameters.
