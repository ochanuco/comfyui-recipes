# tehe

テヘペロ minus the ペロ, with a peace sign at the cheek.

```
(solo:1.5), (portrait:1.5), (head and shoulders:1.4),
(upper body:1.35), (face focus:1.3), (one eye closed:1.45),
(wink:1.35), (smile:1.35), (v:1.45), (hand on own cheek:1.05)
```

`;p` was here and it worked exactly as advertised, which is why it had to
go. Danbooru's emoticon tags name a complete expression -- that one is a
wink WITH the tongue out -- and it drew both halves from one token on the
first sweep, beating an arm that spelled the same face out. Then 「舌出し
止めて」, and an emoticon whose whole content is a wink and a tongue has
nothing left to be once the tongue goes. So the face is spelled out after
all: `(one eye closed:1.45), (wink:1.35), (smile:1.35)`, shut, which is the
sly version rather than the cheerful one. `(open mouth:1.25), (smile:1.3)`
is the cheerful arm and `(smile:1.35)` alone dropped is the flat one; both
were rendered on this seed and both work.

The pose leaves `open_mouthed` with the tongue. It was only ever in that
list to let a tongue through FACE's `closed mouth`.

`(v:1.45)` against `(hand on own cheek:1.05)`, and the weights are the whole
finding. At 1.45/1.4 the cheek tag won outright and drew an open palm with
splayed fingers -- `hand on own cheek` DESCRIBES an open palm, so the two
tags are naming different handshapes for the same hand and whichever is
heavier gets it. Inverted, the V is the shape and the cheek is only the
place.

The exact weights past that inversion do not matter and forty renders say
so. 1.6/1.15 and 1.45/1.05 were run against the same nine seeds: the same
two draws are good in both and the same seven are bad in both. Two other
levers died on the way -- `(clenched hand:1.2)` fixes the knuckle count by
removing the V, and dropping the cheek tag draws the best hands in the sweep
and puts them on her chest. At this point the hand is the seed, and the
guard below is what makes a good seed hold.

`(upper body:1.35)` where the other head framings have `(close-up:1.2)`.
This is the one crop in the file with a hand ON the face rather than beside
it, and at `close-up` the top of her head was outside the frame. The
backdrop share is the other half of it: 30-41% here against 7-30% at the
tighter crop, which is what the delivery step needs to flood.

## Record

Canvas `(1024, 1024)`, `own_eyes=True`, `framing="head"`.

The emoticon that drew the tongue is gone; a wink and a small mouth are what
the model draws one FROM. A tongue is a drawn object with a name.
`negative_edits` prepends `(tongue:1.5), (tongue out:1.5), ` at stage
`S_POSE_GUARDS`.

The hand guard in PASS 1, hands in front of the tongue -- the order the
sweep ran in; the other order reproduced every node but this one. Forty
renders judged at 1024 were judging a prompt the print did not use while
this lived in pass 2 only. `negative_edits` prepends `HAND_BAN` at stage
`S_POSE_GUARDS`.

...and the pass-2 copy: 0.70 redraws the hand, and a guard that only ran on
the pass being redrawn is not a guard. `hires_negative=HAND_BAN`.
