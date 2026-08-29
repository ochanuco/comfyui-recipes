# hige

自分の髪でヒゲを作って遊ぶ（「ヒゲ〜〜〜」）. `tehe`'s framing verbatim, for
`brush`'s reason: it is the one crop built for a hand at the face.

```
(solo:1.5), (portrait:1.5), (head and shoulders:1.4),
(upper body:1.35), (face focus:1.3), (holding own hair:1.5),
(smelling hair:1.45), (playing with own hair:1.3), (smile:1.2)
```

`sip`/`brush`'s two-slot rule: `holding own hair` is the action that brings
the hair to the face and takes the heavier weight; `fake mustache` is the
object slot that says what the held hair is posing as. The hope is the two
read together as hair-held-under-nose rather than a separate costume prop --
that is the thing the sweep judges. `playing with own hair` beside them is
the mood: this is play, not a hairstyle.

「ヒゲのパーツを書くのではなくて、毛先を口元に持ってきてヒゲを表現する」.
`fake mustache` at any weight names the drawn part, not the gesture -- arms
a-c all reached for the part -- so the mustache words are out of the
positive entirely and banned by name in the negative instead.

What is left is pure composition, on the two-slot rule: `holding own hair`
is the action that fills the hand, and `smelling hair` is the placement --
the sniffing gesture is the one vocabulary that pins held TIPS to the NOSE
(arm p, `74gn3v`: 「毛先っていう意味ではこれが正しい」). The mouth pair that
preceded it (`covering own mouth` + `hair in own mouth`, arms h) sent
everything to the mouth instead and lost once 毛先 was the ask. What
`smelling hair` drags in -- narrowed, smug eyes -- is named and banned in
the negative, and the picked render (`kts2c3`, seed `3409564303`) was drawn
through that ban.

## Record

Canvas `(1024, 1024)`, `own_eyes=True`, `framing="head"`, `settled_seed=3409564303`.

`(frills:1.25)` names a dress collar that is out of frame here, and the tag
was landing on the cardigan instead. Gated on the costume whose CHARACTER
carries it. `tail_edits` removes `(frills:1.25), ` (gated `dressed`).

`kts2c3`'s three end-appends, AFTER everything -- the token order it was
drawn in; a mid-prompt insertion re-rolls every token after it. `tail_edits`
appends `, (covered mouth:1.35), (tareme:1.5), (large eyes:1.4)`.

Two prices of the pose's own tags: the lace trio removes what the model
draws out of habit once the `(frills:1.25)` ask is gone (`dm5e2v`), and the
eye trio returns FACE's tareme -- `smelling hair` narrows the eyes into a
smirk (`74gn3v`). Then `tehe`'s hand guard (a hand closed at the face), then
the mustache words, moved here from the positive: asked for, they drew the
part instead of the gesture. The hair at the lip has no name in this
prompt, so the ban cannot delete it. All in `kts2c3`'s order. `negative_edits`
prepends `(lace trim:1.5), (frilled jacket:1.45), (lace:1.4), (half-closed
eyes:1.5), (narrowed eyes:1.5), (smug:1.4), ` + `HAND_BAN` + `(mustache:1.5),
(fake mustache:1.5), (facial hair:1.4), (beard:1.4), ` at stage
`S_POSE_GUARDS`.

Pass 2 redraws the hand at the face; the mustache ban rides along because
pass 2 could paint the part back in. `hires_negative=HAND_BAN + "(mustache:1.5),
(fake mustache:1.5), "`.

`kts2c3`, picked over six fresh seeds on the identical prompt (batch
`wekzha`) -- the seed is carrying something the words do not.
