# flop

「ソファーにダイブしてる姿の方がいいな」 -- the all-nighter face, face-planted.

```
(solo:1.5), (lying:1.45), (on back:1.5), (outstretched arms:1.3),
(smug:1.15), full body
```

Built on `prone`, which is this file's only tested lying pose and supplies
`(lying:1.45)`, `(on stomach:1.5)`, `(from above:1.35)` and its landscape
canvas unchanged. What comes out of it is `chin rest` and `feet up`: both
prop her up and arrange her, and this pose is someone who stopped. `smug`
goes for the obvious reason.

「顔見えなくていいよ。床に埋まってて」 put the face down; 「寝転んでるゆかり
さん（寝不足放心状態）」 brought it back up; 「いつもの表情に戻して」 has
taken the exhaustion off it. Three states have been live on this pose, so all
three are written out and not just whichever one is current.

## The three states

**DEFAULT (now)**: no eye or mouth tags in the block at all, and `flop` in
neither `open_mouthed` nor the `nape` list, so FACE arrives whole -- closed
mouth, tareme, looking at viewer. This is the state with the fewest moving
parts rather than a third variant of two: it is what the pose looks like
when it stops arguing with the shared block at all.

**徹夜 (exhausted)**: `(empty eyes:1.45), (eyebags:1.4), (half-closed
eyes:1.35), (open mouth:1.35)` in the block, and `flop` added to
`open_mouthed` so FACE gives up `closed mouth`. The mouth belongs with the
eyes -- it was never rejected on its own, and 放心状態で口が空いてる was
approved on the way in. Those four tags are the WHOLE of what 徹夜 was on
this pose; no body tag ever carried any of it, which is why the expression
could be lifted off without the pose moving.

**FACE DOWN**: `(face down:1.5)` in the block, no eye or mouth tags, `flop`
back in the `nape` list so `looking at viewer` leaves -- an instruction to
face a camera she is turned away from -- AND `(on back:1.5)` back to `(on
stomach:1.5)`, because there is no face-down on her back.

In NONE of the three: `(from above:1.35)` or `chin rest`. They are how
`prone` keeps a face legible on her stomach, and reaching for one to move the
head would hand back a different composition than whichever render was
picked. The face has now moved four times and the camera none.

「床に埋まって」 needs no floor tag. She is already on the ground with the
couch gone, and `floor` or a room would import a scene that argues with
SURFACE's `(simple background:1.3), (grey background:1.2)` -- which is the
tension the couch carried, now resolved. The burial is `(face down:1.5)`, at
`on stomach`'s weight.

## No dive tag

「ズサーッとダイブしている感じ」, and NO DIVE TAG. This is the trap `fall`
already paid for: tripping + falling + fallen down together drew two figures
on three seeds of three, one still upright and one already on the ground,
because they are three MOMENTS and the model resolved that by giving each
moment a body. `diving` or `falling` on top of `(lying:1.45), (on
stomach:1.5)` is the same construction -- mid-air and landed at once.

So one moment is chosen and it is the skid, not the leap: 「ズサーッ」 is the
part where she is already down and still moving. The motion is carried the
way `fall` carries it, by comic convention rather than by a second moment --
`(motion lines:1.3)`, which that pose records as surviving flat colour -- and
by `(outstretched arms:1.3)`, the arms thrown ahead of her, which is the same
tag at the same weight `fall` uses.

`(from above:1.35)` came out to make room and because it works against the
request: a top-down camera is the one view that flattens horizontal momentum.
It was borrowed from `prone` for legibility, not chosen here.

「寝転んでる」 is not the skid, and `(motion lines:1.3)` came out with it.
Motion lines are the tag that says she is still moving, and 放心状態 is the
opposite of that -- already stopped, and not getting up. They were bought
for 「ズサーッ」 and 「ズサーッ」 is not what is being asked for now. This
paragraph is kept rather than deleted because the dive is one request away,
and the trap it records is still true if it comes back: a dive or falling
tag over `(lying:1.45), (on stomach:1.5)` is two moments, and the model
settles two moments by drawing two bodies.

`(outstretched arms:1.3)` stayed. It arrived as the skid's arms, but arms
thrown out is also simply what 寝転ぶ looks like, and it is the tag holding
the difference between flopped and posed. Second job, not the same job, so
it is not a leftover of the dive.

「寝転んでる」 was rendered both ways on shared seeds and `2ab57f7b` -- on
her BACK -- is the one picked, so `(on stomach:1.5)` became `(on back:1.5)`
here and `.local/_onback.py` is spent. The reason it was worth a render
rather than an argument: on her stomach the face is only legible if the head
is lifted, and the two tags that lift it are the two this pose is on record
as not reaching for. On her back it points at the camera for nothing, and
the four exhaustion tags get a face to land on.

This COUPLED the face switch to the body tag, which it had not been before
-- FACE DOWN carries `(on stomach:1.5)` with it now, and that is folded into
the switch above. Face and body are not independent axes on this pose any
more; do not flip half of one.

## The smug/half-closed weight

「ちょっとドヤ顔（自信ありげな顔）」. The house pair `(smug:1.35),
(half-closed eyes:1.3)` -- what `portrait`, `lounge`, `stand`, `peace` and
`prone` all wear -- was rendered against `boss`'s dialled-down `(smug:1.15)`
alone, and `4b7d646c` is the LOW one. So this pose follows `boss` rather
than its neighbour `prone`, which is worth a line: the request glossed ドヤ顔
as 自信ありげ, and 1.15 is the weight `boss` describes as composed where 1.4
was gloating.

`half-closed eyes` left WITH the weight, not as a separate choice. `boss` F3
measured it indistinguishable at 1.15 and dropped it, and `boss` then found
the tag is not gradual at all -- easing it to 1.1 was still lidded, so
present-or-absent is its whole range. It is one lever, not two.

`smug` is NOT only an expression on this file and that matters for a figure
on her back. `sip` measured it holding her chin up so that head, spine and
hip land on one arc, and `boss` found that easing the weight keeps that lift
while swapping the tag out loses it -- `light smile` at the same count
reached the same face and took a stocking off her foot. Move the weight; do
not substitute the word.

Six tags. It has been nine and it has been five, and every tag that has come
or gone in those swings was expression -- the body, the camera and the
framing have not moved since the on-back pick, whatever the count says.

## Record

Canvas `(1536, 1024)`, `own_eyes=True`.

「ちょっと胴体が長い」, `stand`'s axis and `stand`'s lever. Bracketed from
both sides: no tag drew a long torso, 1.45 drew 「脚が長すぎる」. The negative
route does nothing on this axis -- ask for the leg. Fix applied via
`body_edits`: `(pale skin:1.25)` -> `(long legs:1.40), (pale skin:1.25)`.

「目も修正してほしい」 (`4b7d646c`): `smug` narrows the lids on its own, and
a 250px face is where eyes stop matching. Pass 2 only -- `hires_negative`
carries `(half-closed eyes:1.4), (closed eyes:1.4), `.
