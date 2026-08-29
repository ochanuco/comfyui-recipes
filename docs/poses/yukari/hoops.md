# hoops

バスケなんてやりたくないですよぉ〜〜〜〜〜. The object grammar again, and by
now it is a form to fill in rather than a thing to work out.

```
(solo:1.5), (standing:1.45), (from front:1.3),
(holding basketball:1.5), (hugging object:1.4),
(@_@:1.0), (wavy mouth:1.4),
(flying sweatdrops:1.4), (dizzy:1.3), (full body:1.45),
(short dress:1.35)
```

`(holding basketball:1.5)` is ONE noun, and that is the correction. It was
`(holding ball:1.45), (basketball:1.5)` -- the two-noun form the grammar
prescribes -- and it drew TWO BALLS, which is precisely the hazard `ride`
records for its own second naming ("two bicycles is the first thing to look
for"). `ride` accepted that cost because a road bike is not the default
bicycle; here the fused phrase pins the type without paying it, so there is
nothing to accept.

Danbooru's tag is `basketball_(object)` at 6k, but parentheses are weight
syntax in a prompt and cannot be written. The plain word reaches the text
encoder perfectly well, which is the one place this file's tag-count
discipline has to bend to the tokenizer.

`(spread fingers:1.3)` 5.6k WAS here and is gone. It asked for open fingers
and the model obliged with too many of them; dropping it gave the cleanest
upper hand of any arm. The tag to suspect for a bad hand is not always a
guard that is missing -- sometimes it is a request that is present.

`(short dress:1.35)` 130k is the SILHOUETTE an oversized tee makes once it
reaches the thigh, named so the model draws that shape rather than a shirt
that stops at the hip. It is the tag that finally covered her, and it was
reached only after `oversized shirt` had been swept across six weights in
three rounds. The risk it carries -- that an actual dress arrives instead --
did not materialise on any of three seeds.

`(hugging object:1.4)` 32k is the grip in the reference photo: the ball at
chest height, a palm on each side, fingers open. 「両側から押し抱えてる？感
じがいいな。バスケだし」. There is no tag for holding something with both
hands -- not in `holding_*`, not under `*both_hands*`, and
`holding_to_chest` is 102 posts. So the grip is spelled as a clutch plus a
hand shape, which is the same position `side_slit` left this file in: the
picture exists in the training data and the word for it does not.

`(@_@:1.0)` is NOT re-measured here. `dizzy` owns that finding and the value
is the finding: 1.45 draws a near-black spiral on a white sclera, `spiral
eyes` and `dizzy eyes` are not danbooru tags at all, and 1.0 is the weight on
the render that was picked (`49b3aab4`). Copied at its measured value, not
re-swept.

`(dizzy:1.3)` comes with it for the reason `dizzy` records: it went in as a
floor under the symbol, in case `@_@` did not draw, and stayed because it
carries the state when the symbol is faint. Three arms were run and the one
WITH it was picked, so on this pose the floor is doing visible work.

`(wavy mouth:1.4)` 101k and `(flying sweatdrops:1.4)` 126k are the whine and
its punctuation. In `open_mouthed`: 〜〜〜 is a drawn-out complaint and FACE
closes the mouth. Removed, not replaced -- `snack`'s rule.

The joke is the costume: `fitness` is a gym kit, so she is already dressed
for the thing she does not want to do. Nothing in the block says so, which
is right -- SURFACE is a flat backdrop and a court would fight it, the same
contract `ride` keeps by putting her on a bike in front of nothing.

## Record

Canvas `(832, 1664)`, `own_eyes=True`, `open_mouth=True`.

Two hands closed around an object is `tehe`'s accident class, and that
pose's forty-render finding was about WHERE the guard goes: both passes from
the first sweep, or the 1024 sweep judges a prompt the print does not use.
Prepended -- token order. `negative_edits` prepends `HAND_BAN` at stage
`S_POSE_GUARDS`, and prepends `_LIMB_TRIO` (see `shared.md`) at stage
`S_POSE_LIMBS`.

`hires_negative` is `HAND_BAN`.
