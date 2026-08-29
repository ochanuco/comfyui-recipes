# allnighter

徹夜明け -- the eyes are dead.

```
(solo:1.5), (portrait:1.5), (head and shoulders:1.4), (close-up:1.2),
(face focus:1.3), (empty eyes:1.45), (eyebags:1.4),
(half-closed eyes:1.35), (open mouth:1.35)
```

Built on `portrait`'s framing rather than on a body pose, because the
request is about the eyes and at 1024x1536 the face is a hundred pixels
tall. `slouching`, `desk`, `computer` were all considered and left out: the
backdrop is `(simple background:1.3), (grey background:1.2)` in SURFACE, and
a scene fights that contract.

`(empty eyes:1.45)` is the tag that does the work -- no highlight, and it is
what the danbooru vocabulary calls dead eyes; `dead eyes` is not a tag.
`(eyebags:1.4)` is what makes it an all-nighter rather than a mood, and
`(half-closed eyes)` is already portrait's, raised 1.3 -> 1.35 for the droop.

NOT `(closed eyes)`: `yawn` measured that at 1.35 and it drew a second figure
on four seeds of four. Half-closed is also the only version of this that can
show an empty eye at all.

「ちょっと口がキレてるね・・・放心状態感で口が空いてる方が良さそう」.
`(open mouth:1.35)`, and the teeth are gone entirely.

THE TEETH WERE THE ANGER. Both attempts at a 「イー」 mouth put teeth in the
frame -- `(clenched teeth:1.45)` first, then `(teeth:1.45), (parted
lips:1.3)` -- and the second read as cross too. `clenched teeth` was blamed
for it when it went, on the grounds that the tag lives on rage and strain;
that was half right. Bared teeth carry the strain on their own, whichever tag
asks for them, and no weight on the tag beside them undoes it.

`parted lips` goes with it rather than staying as the gap. It is one
description of the mouth and `open mouth` is another, and this pose has now
been through two rounds of two tags arguing over the same feature.

1.35 and not `fall`'s 1.30: both precedents for an open mouth in this file
have something driving it -- `(yawning:1.4)` there, `(surprised:1.35)` there
-- and nothing here does. 放心 is the absence of an expression, so it has no
engine, and the weight is the whole engine. Too wide is a visible, fixable
failure; a mouth that never opens loses the request.

`(expressionless:1.3)` is deliberately NOT restored, even though 放心 is what
it names. On danbooru it sits on closed neutral mouths, so against `open
mouth` it is a third description of the same feature. The vacancy is carried
by `(empty eyes:1.45)` and by there being no smile or anger tag at all --
which is what went wrong when there WAS one.

Back to nine tags, and back to removing only `closed mouth` from FACE -- the
same one-tag departure `yawn` and `fall` make. `small mouth` returns: it was
taken out for the 「イー」 width, and a 放心 mouth is a small ぽかん one, so
the shared block is left alone.

## Record

Canvas `(1024, 1024)`, `own_eyes=True`, `framing="head"`, `open_mouth=True`.

No further edits are recorded on this pose's record entry beyond those
parameters.
