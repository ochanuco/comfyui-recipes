"""Every pose: its tag block, and its record.

`POSES` is the pose blocks, verbatim -- the strings the picked renders were
drawn with, byte for byte. `POSE_RECORDS` below is the rest of what a pose
owns, one record per pose: canvas, framing, its declared departures from the
shared blocks, its pass-2 contract, its settled seed. Adding a pose is one
`POSES` entry plus one record here; nothing else in the package needs to
know it exists.

Where a record departs from a shared block, the comment keeps the constraint
and the measurement that bought it; the full story is in docs/render-notes.md
under the pose's name.
"""

from __future__ import annotations

from .model import (
    Edit,
    Pose,
    S_CROWD,
    S_POSE_GUARDS,
    S_POSE_LATE,
    S_POSE_LIMBS,
    S_POSE_SCENE,
    S_POSE_SHOES,
)
from .prompt_style import HAND_BAN, HIRES_NEGATIVE_PAINT

# The one place a SCENE replaces the backdrop, and it is a deliberate break of
# the contract everything else in this file keeps. `ride` puts her on a bike in
# front of nothing and `hoops` keeps the court out, because SURFACE is flat and
# a scene fights it. `doze` was swept BOTH ways at 1152 on four seeds -- one arm
# on the grey backdrop, one with this splice -- and the picked render is
# b393e171, from this one. The contract lost a measurement rather than an
# argument, and it lost on exactly one pose.
#
# It replaces `(simple background:1.3), (grey background:1.2)` and nothing else:
# `(flat color:1.3)`, `(white outline:1.6)` and the shading pair stay, which is
# why the carriage arrives as pale line and stripe rather than as a photograph.
#
# `train_interior` 11.4k, `vehicle_interior` 1.2k, `window` 179k. The window is
# the weakest weight of the three on purpose -- it is 179k of pictures that are
# mostly NOT trains, so it is here to put light behind her and not to name the
# place.
#
# Two things this costs, both real and both paid: recolor_bg.py has nothing to
# do here (there is no flat backdrop left to set), and `headcount.py` cannot be
# pointed at this pose at all -- it takes the background colour from the border
# pixels, so seats and poles count as figure.
SCENE_TRAIN = "(train interior:1.4), (vehicle interior:1.3), (window:1.2)"

# A carriage is a room whose entire subject is other passengers, and `(solo:1.5)`
# has never had to hold against a background that implies a crowd. In front of
# NEGATIVE for the reason the rest of this file's guards are: token order changes
# the encoding, and this is the order b393e171 was drawn in.
CROWD_BAN = "(multiple girls:1.5), (2girls:1.5), (crowd:1.4), (people:1.4), "

# THE がおー, as a part rather than as a spelling. `roar` was the first pose to
# wear it and it is not going to be the last, and a family of poses that each
# write out their own copy of the same three tags is the state this file was in
# before the costume blocks existed: change one, and the others quietly do not
# change with it.
#
# Two fragments and not one, because the hands and the face do not sit next to
# each other in the order `roar` was rendered in -- `(hands up:1.35)` and
# `(leaning forward:1.3)` are between them, and token order changes the
# encoding. Splitting it here is what makes it a no-op: `roar` below is
# assembled from these and is byte-identical to the string that drew f38695b8.
GAO_HANDS = "(claw pose:1.55)"
GAO_FACE = "(open mouth:1.4), (fang:1.3)"

POSES = {
    "lounge": (
        "(solo:1.5), (yokozuwari:1.35), sitting on floor, legs to the side, "
        "(arms behind head:1.3), (smug:1.35), (half-closed eyes:1.3), full body"
    ),
    "portrait": (
        "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), (close-up:1.2), "
        "(face focus:1.3), (smug:1.35), (half-closed eyes:1.3)"
    ),
    # 徹夜明け -- the eyes are dead. Built on `portrait`'s framing rather than on
    # a body pose, because the request is about the eyes and at 1024x1536 the
    # face is a hundred pixels tall. `slouching`, `desk`, `computer` were all
    # considered and left out: the backdrop is (simple background:1.3),
    # (grey background:1.2) in SURFACE, and a scene fights that contract.
    #
    # (empty eyes:1.45) is the tag that does the work -- no highlight, and it is
    # what the danbooru vocabulary calls dead eyes; `dead eyes` is not a tag.
    # (eyebags:1.4) is what makes it an all-nighter rather than a mood, and
    # (half-closed eyes) is already portrait's, raised 1.3 -> 1.35 for the droop.
    #
    # NOT (closed eyes): `yawn` measured that at 1.35 and it drew a second
    # figure on four seeds of four. Half-closed is also the only version of this
    # that can show an empty eye at all.
    #
    # 「ちょっと口がキレてるね・・・放心状態感で口が空いてる方が良さそう」.
    # (open mouth:1.35), and the teeth are gone entirely.
    #
    # THE TEETH WERE THE ANGER. Both attempts at a 「イー」 mouth put teeth in the
    # frame -- (clenched teeth:1.45) first, then (teeth:1.45), (parted lips:1.3)
    # -- and the second read as cross too. `clenched teeth` was blamed for it
    # when it went, on the grounds that the tag lives on rage and strain; that
    # was half right. Bared teeth carry the strain on their own, whichever tag
    # asks for them, and no weight on the tag beside them undoes it.
    #
    # `parted lips` goes with it rather than staying as the gap. It is one
    # description of the mouth and `open mouth` is another, and this pose has
    # now been through two rounds of two tags arguing over the same feature.
    #
    # 1.35 and not `fall`'s 1.30: both precedents for an open mouth in this file
    # have something driving it -- (yawning:1.4) there, (surprised:1.35) there
    # -- and nothing here does. 放心 is the absence of an expression, so it has
    # no engine, and the weight is the whole engine. Too wide is a visible,
    # fixable failure; a mouth that never opens loses the request.
    #
    # (expressionless:1.3) is deliberately NOT restored, even though 放心 is what
    # it names. On danbooru it sits on closed neutral mouths, so against
    # `open mouth` it is a third description of the same feature. The vacancy is
    # carried by (empty eyes:1.45) and by there being no smile or anger tag at
    # all -- which is what went wrong when there WAS one.
    #
    # Back to nine tags, and back to removing only `closed mouth` from FACE --
    # the same one-tag departure `yawn` and `fall` make. `small mouth` returns:
    # it was taken out for the 「イー」 width, and a 放心 mouth is a small
    # ぽかん one, so the shared block is left alone.
    "allnighter": (
        "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), (close-up:1.2), "
        "(face focus:1.3), (empty eyes:1.45), (eyebags:1.4), "
        "(half-closed eyes:1.35), (open mouth:1.35)"
    ),
    # 「寝不足ゆかりさん。目にクマがあってぐるぐる目」. `allnighter`'s crop and
    # `allnighter`'s クマ, with the dead eye swapped for a spinning one.
    #
    # It is a SUBSTITUTION and not an addition, which is this file's cheapest
    # kind of change: the framing five are untouched, `eyebags` stays at the
    # 1.4 it holds in every exhausted pose here, and the two tags that describe
    # how the eye is drawn are the two that leave.
    #
    # - **`(@_@:1.0)` is the tag, and 1.0 is the whole finding.** ぐるぐる目 is
    #   `@_@` on danbooru; `spiral eyes` and `dizzy eyes` are not tags there, and
    #   it draws -- at 1.45 it draws a near-black spiral on a white sclera that
    #   takes the entire face (「強調されすぎて視線誘導されてしまう」). That 1.45 was
    #   inherited from `empty eyes`, which is SUBTRACTIVE -- it removes the
    #   highlight -- while `@_@` is additive, so the weights were never
    #   like-for-like. Walked down 1.45 -> 1.3 -> 1.15 -> 1.0 on one seed, and
    #   **1.0 is the render that was picked** (49b3aab4). At 1.0 the spiral is
    #   no longer drawn as a stroke: what is left is the wide flat eye it comes
    #   with, under the クマ. Kept in the block anyway, because it is in the
    #   accepted render and this file does not delete tags on a null
    #   measurement -- see the thin-line tags.
    # - **`half-closed eyes` has to go.** A lid at 1.35 covers the thing the
    #   request is about. `allnighter` raised it for the droop; here the droop
    #   is carried by `eyebags` and the mouth, and the eye has to be open to
    #   show anything at all.
    # - **`(eyebags:1.55), (tired:1.3)` is the クマ, and it took two words.**
    #   `eyebags` at the 1.4 every other exhausted pose here uses drew two faint
    #   strokes; 1.55 and 1.7 alone did no better. Adding `tired` beside it at
    #   1.55 drew the shadow as a dark mass under both eyes on the first try.
    #   **More weight was the wrong lever and a second word was the right one**,
    #   which is the reverse of what the クマ was expected to need.
    # - **`(dizzy:1.3)` outlived the swirl it was hired to support.** It went in
    #   as a floor under `@_@` -- a real tag for the state, in case the symbol
    #   was punctuation the model never learned. The symbol turned out to be
    #   real and had to be walked back instead, and `dizzy` is what now carries
    #   ぐるぐる as a state rather than as a drawn line.
    # - **`(open mouth:1.35)` is kept**, unweighted from `allnighter`. A ぽかん
    #   mouth is what 寝不足 looks like from the front, and it is the one
    #   departure from FACE that all three exhausted poses here already make.
    #
    # Ten tags, one over `allnighter`'s nine, and the extra one is `tired` --
    # the tag that turned out to be doing the work. No desk, no night, no
    # motion lines: SURFACE is a grey background and the state is on her face.
    #
    # Settled on seed 737373737 (49b3aab4), picked for its art style first and
    # then tuned twice on that one seed without re-rolling.
    "dizzy": (
        "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), (close-up:1.2), "
        "(face focus:1.3), (@_@:1.0), (eyebags:1.55), (tired:1.3), "
        "(dizzy:1.3), (open mouth:1.35)"
    ),
    # 「c575fc46 全身、正座」. The same face, knelt, at full length.
    #
    # It is a NEW POSE and not a size on the old one. `allnighter` is a
    # 1024x1024 head framing; a full body is a different first pass, and this
    # file already records that the first-pass canvas is a composition variable
    # rather than a resolution knob. The render that was picked cannot be
    # "made bigger" into this -- it has to be re-picked here.
    #
    # `seiza` was asked for by name, and this file convicts it twice over: the
    # 「One tag, `seiza`, was behind the drifting art style」 entry has it taking
    # the line, the backdrop flatness and the headcount together, and `invite`'s
    # comment says to keep it out. **Most of that conviction was withdrawn on
    # 2026-08-19** -- swapping only the seat in `lap` moved nothing, and the
    # stroke number that convicted it had been read off the wrong statistic.
    #
    # What was NOT withdrawn is the headcount: one seed of that swap drew two of
    # her, and no measurement since has addressed it. So the seat is used, and
    # the sweep is counted rather than trusted. `(solo:1.5)` leads, as everywhere
    # else here.
    #
    # The face block is carried over unchanged and unweighted-down, even though
    # a full body spends far fewer pixels on it than the close-up did. Easing
    # tags that are already fighting for a small feature is how the eyes would
    # quietly stop reading; if they do not survive at 1024x1536, the answer is
    # the second pass, not a heavier tag.
    "allnighter_full": (
        "(solo:1.5), (seiza:1.35), (empty eyes:1.45), (eyebags:1.4), "
        "(half-closed eyes:1.35), (open mouth:1.35), full body"
    ),
    # 「ソファーにダイブしてる姿の方がいいな」. The all-nighter face, face-planted.
    #
    # Built on `prone`, which is this file's only tested lying pose and supplies
    # (lying:1.45), (on stomach:1.5), (from above:1.35) and its landscape canvas
    # unchanged. What comes out of it is `chin rest` and `feet up`: both prop
    # her up and arrange her, and this pose is someone who stopped. `smug` goes
    # for the obvious reason.
    #
    # 「顔見えなくていいよ。床に埋まってて」 put the face down; 「寝転んでるゆかり
    # さん（寝不足放心状態）」 brought it back up; 「いつもの表情に戻して」 has
    # taken the exhaustion off it. Three states have been live on this pose, so
    # all three are written out and not just whichever one is current.
    #
    # DEFAULT (now): no eye or mouth tags in the block at all, and `flop` in
    # neither `open_mouthed` nor the `nape` list, so FACE arrives whole --
    # closed mouth, tareme, looking at viewer. This is the state with the
    # fewest moving parts rather than a third variant of two: it is what the
    # pose looks like when it stops arguing with the shared block at all.
    #
    # 徹夜 (exhausted): (empty eyes:1.45), (eyebags:1.4), (half-closed
    # eyes:1.35), (open mouth:1.35) in the block, and `flop` added to
    # `open_mouthed` so FACE gives up `closed mouth`. The mouth belongs with
    # the eyes -- it was never rejected on its own, and 放心状態で口が空いてる
    # was approved on the way in. Those four tags are the WHOLE of what 徹夜
    # was on this pose; no body tag ever carried any of it, which is why the
    # expression could be lifted off without the pose moving.
    #
    # FACE DOWN: (face down:1.5) in the block, no eye or mouth tags, `flop`
    # back in the `nape` list so `looking at viewer` leaves -- an instruction
    # to face a camera she is turned away from -- AND `(on back:1.5)` back to
    # `(on stomach:1.5)`, because there is no face-down on her back.
    #
    # In NONE of the three: `(from above:1.35)` or `chin rest`. They are how
    # `prone` keeps a face legible on her stomach, and reaching for one to move
    # the head would hand back a different composition than whichever render
    # was picked. The face has now moved four times and the camera none.
    #
    # 「床に埋まって」 needs no floor tag. She is already on the ground with the
    # couch gone, and `floor` or a room would import a scene that argues with
    # SURFACE's (simple background:1.3), (grey background:1.2) -- which is the
    # tension the couch carried, now resolved. The burial is (face down:1.5),
    # at `on stomach`'s weight.
    #
    # 「ズサーッとダイブしている感じ」, and NO DIVE TAG. This is the trap `fall`
    # already paid for: tripping + falling + fallen down together drew two
    # figures on three seeds of three, one still upright and one already on the
    # ground, because they are three MOMENTS and the model resolved that by
    # giving each moment a body. `diving` or `falling` on top of (lying:1.45),
    # (on stomach:1.5) is the same construction -- mid-air and landed at once.
    #
    # So one moment is chosen and it is the skid, not the leap: 「ズサーッ」 is
    # the part where she is already down and still moving. The motion is carried
    # the way `fall` carries it, by comic convention rather than by a second
    # moment -- (motion lines:1.3), which that pose records as surviving flat
    # colour -- and by (outstretched arms:1.3), the arms thrown ahead of her,
    # which is the same tag at the same weight `fall` uses.
    #
    # (from above:1.35) came out to make room and because it works against the
    # request: a top-down camera is the one view that flattens horizontal
    # momentum. It was borrowed from `prone` for legibility, not chosen here.
    #
    # 「寝転んでる」 is not the skid, and (motion lines:1.3) came out with it.
    # Motion lines are the tag that says she is still moving, and 放心状態 is
    # the opposite of that -- already stopped, and not getting up. They were
    # bought for 「ズサーッ」 and 「ズサーッ」 is not what is being asked for now.
    # The paragraph above is kept rather than deleted because the dive is one
    # request away, and the trap it records is still true if it comes back: a
    # dive or falling tag over (lying:1.45), (on stomach:1.5) is two moments,
    # and the model settles two moments by drawing two bodies.
    #
    # (outstretched arms:1.3) stayed. It arrived as the skid's arms, but arms
    # thrown out is also simply what 寝転ぶ looks like, and it is the tag
    # holding the difference between flopped and posed. Second job, not the
    # same job, so it is not a leftover of the dive.
    #
    # 「寝転んでる」 was rendered both ways on shared seeds and 2ab57f7b -- on
    # her BACK -- is the one picked, so `(on stomach:1.5)` became
    # `(on back:1.5)` here and `.local/_onback.py` is spent. The reason it was
    # worth a render rather than an argument: on her stomach the face is only
    # legible if the head is lifted, and the two tags that lift it are the two
    # this pose is on record as not reaching for. On her back it points at the
    # camera for nothing, and the four exhaustion tags get a face to land on.
    #
    # This COUPLED the face switch to the body tag, which it had not been
    # before -- FACE DOWN carries `(on stomach:1.5)` with it now, and that is
    # folded into the switch above. Face and body are not independent axes on
    # this pose any more; do not flip half of one.
    #
    # 「ちょっとドヤ顔（自信ありげな顔）」. The house pair `(smug:1.35),
    # (half-closed eyes:1.3)` -- what `portrait`, `lounge`, `stand`, `peace`
    # and `prone` all wear -- was rendered against `boss`'s dialled-down
    # `(smug:1.15)` alone, and 4b7d646c is the LOW one. So this pose follows
    # `boss` rather than its neighbour `prone`, which is worth a line: the
    # request glossed ドヤ顔 as 自信ありげ, and 1.15 is the weight `boss`
    # describes as composed where 1.4 was gloating.
    #
    # `half-closed eyes` left WITH the weight, not as a separate choice.
    # `boss` F3 measured it indistinguishable at 1.15 and dropped it, and
    # `boss` then found the tag is not gradual at all -- easing it to 1.1 was
    # still lidded, so present-or-absent is its whole range. It is one lever,
    # not two.
    #
    # `smug` is NOT only an expression on this file and that matters for a
    # figure on her back. `sip` measured it holding her chin up so that head,
    # spine and hip land on one arc, and `boss` found that easing the weight
    # keeps that lift while swapping the tag out loses it -- `light smile` at
    # the same count reached the same face and took a stocking off her foot.
    # Move the weight; do not substitute the word.
    #
    # Six tags. It has been nine and it has been five, and every tag that has
    # come or gone in those swings was expression -- the body, the camera and
    # the framing have not moved since the on-back pick, whatever the count
    # says.
    "flop": (
        "(solo:1.5), (lying:1.45), (on back:1.5), (outstretched arms:1.3), "
        "(smug:1.15), full body"
    ),
    # Both hands making a V, one held over the eye and one arm thrown out
    # towards the camera. `double v` (42k posts) and `v over eye` (10k, "with
    # the eye between the fingers") are both real tags; the gesture is not
    # something a description of fingers would get.
    #
    # This is pv1 (prompt 37ac6c0d) exactly, reverted to on request. Nine tags.
    #
    # Trimming it was tried three ways and none of them held together. At eight
    # -- (outstretched arm:1.3) dropped -- the dress palette recovered (value
    # 116 -> 196) but the socks split left from right. At seven without
    # `legs to the side` the legwear came right and the colour count went 20 ->
    # 52, but rabbit cut-outs and a small second figure appeared. At seven
    # without `full body` instead, the leg mismatch went to its worst and the
    # frame cropped at the shins.
    #
    # So the count was never the variable, whatever the earlier notes here said:
    # two seven-tag blocks went opposite ways. What each individual tag holds is
    # the variable, and the nine together are what was actually wanted.
    #
    # (solo:1.5) stays at the head at exactly this weight -- measured, took
    # clones from 5-of-8 to 0-of-8.
    "peace": (
        "(solo:1.5), (yokozuwari:1.35), legs to the side, (double v:1.45), "
        "(v over eye:1.4), (outstretched arm:1.3), (smug:1.35), "
        "(half-closed eyes:1.3), full body"
    ),
    # Stretching and yawning, looked down on. The pose text comes from
    # pick/yk-yawn-full, which was settled on the older queue_dq3 recipe against
    # the same base and sampler, and carries two measured constraints:
    #
    #   the block must stay at eight tags after (solo:1.5) -- a ninth pushes the
    #   pale thighhighs out;
    #   (closed eyes:1.35) drew a second figure on four seeds of four, so the
    #   eyes stay open even though a yawn would close them.
    #
    # `closed mouth` comes out of FACE for this pose; it is the direct opposite
    # of what a yawn needs.
    "yawn": (
        "(solo:1.5), (stretching:1.4), (arms up:1.35), (yawning:1.4), "
        "(open mouth:1.35), (from above:1.4), sitting, looking at viewer, "
        "full body"
    ),
    # Going over spectacularly. ONE fall tag.
    #
    # tripping + falling + fallen down together drew two figures on three seeds
    # of three -- one still upright, one already on the ground. They are three
    # moments, not three descriptions of one moment, and the model resolved that
    # by giving each moment a body. Competing tags did hold each other in place
    # for the socks, but that was two lengths of one garment at one instant;
    # carrying the idea over to a sequence was a bad generalisation.
    #
    # `falling` is the one kept: mid-air is what reads as spectacular, and both
    # of the others describe ground contact. `flailing` supplies the drama and
    # `motion lines` is a comic convention that survives flat colour. Eight tags
    # after (solo:1.5), and `closed mouth` comes out of FACE for the shout.
    "fall": (
        "(solo:1.5), (falling:1.5), (flailing:1.35), (surprised:1.35), "
        # No (spread legs) here. Paired with (from above) that is exactly the
        # crotch-forward low-angle framing this project already threw a whole
        # composition away over.
        "(open mouth:1.3), (motion lines:1.25), (outstretched arms:1.3), "
        "(from above:1.25), full body"
    ),
    # Knowingly cute -- the pose is aware of being looked at. Head tilted,
    # finger to the cheek, one eye shut, blushing, with a heart floating.
    # `head tilt`, `finger to cheek` and `one eye closed` are all real tags
    # (`wink` has no wiki page of its own and appears to fold into the last).
    #
    # It sits on yokozuwari, which is the seat this recipe has seven clean seeds
    # on, so only the face and the hand are new. Building an untested gesture on
    # an untested seat is how the fall pose ended up with two of her.
    "coy": (
        "(solo:1.5), (yokozuwari:1.3), (head tilt:1.4), (finger to cheek:1.45), "
        "(one eye closed:1.35), (blush:1.35), (heart:1.25), (smile:1.25), "
        "full body"
    ),
    # Giving a lap pillow, and pleased with herself about it. The person whose
    # head is on her lap is the camera -- this is the composition recorded in
    # pick/momiji-lap, which is the only lap pillow in this repo that came out
    # with one girl in it.
    #
    # (head on lap) and (hand on another's head) are deliberately absent. They
    # name a second person literally and drew her twice; (solo:1.5) cannot
    # outvote a tag that says two people are present.
    #
    # `lap pillow` is the right tag over `lap pillow invitation` -- per its wiki
    # the latter is for merely offering, and she is doing it.
    #
    # `looking at viewer` already comes from FACE, so it is not repeated here.
    #
    # yokozuwari, and it was PICKED, not deduced. The seat was swapped on the
    # theory that `seiza` was breaking the line here the way it broke it in
    # `invite` -- see the null in the notes, which says plainly that it was not:
    # `seiza`, `yokozuwari` and no seat tag at all measured the same. What is
    # true is only that ls-yz-lap-555666777 (8b51610f) is the render that was
    # chosen, and yokozuwari is what drew it. Do not restore `seiza` on the
    # grounds that the line argument fell over; there is no argument for it
    # either, and this seat has the picked image under it.
    "lap": (
        "(solo:1.5), (lap pillow:1.35), (pov:1.45), sitting, (yokozuwari:1.25), "
        "(looking down:1.4), (smug:1.4), (hand up:1.25), cowboy shot"
    ),
    # Patting her own thigh, inviting you to put your head on it. One girl.
    #
    # There is no lap-pillow tag here on purpose. `lap pillow` is for a head
    # already resting on someone, and `lap pillow invitation` -- which its wiki
    # describes as exactly this gesture -- still drew a second Yukari lying on
    # her lap on every seed tried, guarded or not, and with (solo:1.7). It names
    # the relationship, and so names the other party; the same way (head on lap)
    # and (hand on another's head) did in pick/momiji-lap. Weight does not beat
    # that, deletion does.
    #
    # So the invitation is assembled only from things that describe her alone:
    # kneeling, a hand on her own thigh, beckoning, looking down at someone who
    # is not drawn.
    #
    # Do NOT add duplicate guards to the negative for this. Four of them at
    # 1.5-1.6 left the headcount unchanged and took mean saturation from ~25 to
    # 105-163 -- neon backdrop, orange skin. Same as the five-guard block that
    # wrecked the palette once before.
    # yokozuwari, NOT seiza. `seiza` on its own moved stroke width from this
    # recipe's fixed 1.91px to 6.56 and 8.47, mottled the backdrop, and drew a
    # second Yukari on one of two seeds -- swapped one at a time into `peace`,
    # it was the only element that did anything. (come hither), (looking down)
    # and the hand pair all measured 1.91px, and `cowboy shot` only breaks the
    # die-cut outline, not the line.
    "invite": (
        "(solo:1.5), (yokozuwari:1.35), legs to the side, "
        "(hand on own thigh:1.45), (beckoning:1.35), (looking down:1.4), "
        "(smug:1.4), (come hither:1.25), full body"
    ),
    # On all fours, patting the floor for the glasses she has just dropped, looking
    # back over her shoulder. `all fours`, `searching`, `hands on ground`,
    # `top-down bottom-up` and `glasses` are all real tags; `crouching` and
    # `reaching out` have no wiki pages and are not used.
    #
    # The dropped thing is named. An unnamed one renders as nothing at all --
    # the same finding as Hamakaze's meal, which stayed an unreadable dark blob
    # until it was given (onigiri).
    #
    # Kept from gl-fours-737373737 (prompt 3394c4bb), and NOT SETTLED: that seed
    # is the one it works on. Three further seeds all rode the hoodie up and bared
    # her midriff, one of them drew two of her, and none of them read as searching
    # -- she is still wearing the glasses she is supposed to be looking for.
    # Stroke stayed 1.91px throughout, so this is a content failure, not the
    # style break `seiza` caused.
    "hunt": (
        "(solo:1.5), (all fours:1.45), (searching:1.4), (hands on ground:1.35), "
        "(from behind:1.3), (glasses:1.3), (looking down:1.25), full body"
    ),
    # The same search, squatting rather than down on her hands, seen from behind
    # and slightly above.
    #
    # SETTLED HERE. `--pose crouch --seed 1117511306` reproduces ns-1117511306
    # (prompt 7d231c4f) pixel for pixel -- verified, max channel difference 0 --
    # and that render is the target: the design and the pose that carry the
    # wide-hipped read this character is meant to have.
    #
    # Three attempts to push it further were run and none are in here:
    #
    #   (coattails:1.4)        the coat became narrow straps rather than a
    #                          spreading garment, several of them on some seeds,
    #                          reading as jointed legs; two seeds drew a second
    #                          figure. It is confusable with the hood's own black
    #                          red-striped ears.
    #   (loose clothes:1.4)    stroke width went 1.91 -> 3.82 and 7.64, the paint
    #                          thickened, the dress fell to 5-6% of the frame.
    #                          It loosens the drawing, not the garment.
    #   (from above:1.2) out   this one worked -- pale legwear went 47% to 55-75%
    #                          and the legs come back. Left out only because it
    #                          changes the picked composition; re-add it if the
    #                          legs are wanted over the overhead angle.
    #
    # Originally from bk-squat-1886970040 (prompt 3d7376f2), before the sticker
    # removal and the coat.
    #
    # Eleven seeds, all eleven at exactly 1.91px, all one girl, no clothing
    # failures. `hunt` on the same recipe rode the hoodie up on three seeds of
    # three and doubled her on one, so the difference is the pose, not luck.
    #
    # What is NOT stable is the posture inside the pose: some seeds hug the knees,
    # some pitch the torso much further forward, and the hood's pompom sometimes
    # lands where the silhouette needs to read. And (searching:1.2) does no work
    # at that weight -- none of the eleven look like they are looking for
    # anything. It is a settled drawing style around an unsettled action.
    "crouch": (
        "(solo:1.5), (squatting:1.4), (from behind:1.45), (looking down:1.4), "
        # (smug:1.2) stays. It was swapped for (expressionless:1.2) on a reading
        # of "not showing it off" as "no expression at all", and that took her
        # character with it -- she is written as confident and hapless, and a
        # blank face carries neither. The staging is carried by the action and
        # the angle, not by the face.
        #
        # (coin:1.3) is gone and (from above:1.2) is back in its slot. The coins
        # gave `picking up` something to act on, but cost the overhead angle,
        # which is also what keeps the hips out of centre frame.
        #
        # For the record, since it looks like it should be tried: `light smile`
        # and `looking back` measured 42-48 and 38-44 colours in an earlier
        # block and were rejected. Re-measured here they come in at 16-23. The
        # rejection was true of that block, not of the tags.
        "(picking up:1.3), (from above:1.2), (smug:1.2), full body"
    ),
    # Sitting on a gaming chair with her legs crossed, facing front.
    #
    # This block is not new here. It is the one kept as pick/yk-chair-151,
    # pick/yk-chair-111 and pick/yk-chair-555 -- three seeds, settled on the
    # older queue_dq3 recipe against this same base, and passed as --pose-text
    # rather than ever being written down as a pose. Porting it in is the whole
    # change; every weight below was measured there and none of it was re-run.
    #
    # What it replaces was `peace` moved off the floor and onto a chair
    # (`sitting` + `on chair` + the double-V hands). That went one clean seed in
    # four -- rabbit plushies, a low camera on the thighs, the dress swapped for
    # a hoodie, and three chibi clones -- and nothing was ever picked from it.
    # The floor version is still there as `peace`, seven seeds of seven.
    #
    # Four measurements this block carries, all of them costly:
    #
    #   `(crossed legs:1.2)`, NOT 1.35. At 1.35 the model draws the crossing
    #   rather than the legs and a third leg appears. Banning it -- (extra
    #   legs:1.6), (three legs:1.5) -- did not help, because the weight was the
    #   problem and not the absence of a ban.
    #
    #   The chair is one word. Asked for as a five-tag block -- (gaming
    #   chair:1.45), racing seat, (high backrest:1.3), headrest, armrest -- it
    #   returned a full-frame noise field, and so did this block plus `leaning
    #   back, hand on own knee`. Substituting (office chair:1.35) for (gaming
    #   chair:1.4) at the same tag count drew a proper racing seat instead, and
    #   threw in a controller nothing had asked for.
    #
    #   Nine tags, and the ninth is load-bearing in both directions. At twelve
    #   the pale thighhighs are pushed out and one dark tights is drawn instead
    #   -- the legwear is the first thing this block spends.
    #
    #   Bare `full body`, NOT `(full body:1.4)`. render-notes recommends the
    #   raised form off three seeds, and pick/yk-chair-gradient records the same
    #   substitution alone collapsing the two legwear layers into one stocking.
    #   Ported with the raised form first and the collapse reproduced on
    #   151515151; reverting it brought the layers back on that seed. Two picks
    #   disagreed about one substitution and the unfavourable one was right.
    #
    # One tag had to go to make room for (solo:1.5), which leads every entry
    # here and is worth its slot -- it took clones from five of eight to none.
    # `looking at viewer` is the one dropped, because FACE already supplies it;
    # `lap` omits it for the same reason. Nine tags in, nine tags out.
    #
    # 1024x1024, where the picks were 2:3. The look was drifting flat next to
    # `sip` -- no highlights, no modelling -- and that is a framing property, not
    # a style one. Stroke is a constant 1.91px at every canvas this recipe uses
    # (see the module docstring), so a figure drawn small carries a line that is
    # heavy relative to her head and has no pixels left to shade in. The square
    # puts her back at `sip`'s scale and the shading returns with her.
    #
    # NOT SETTLED, one clean seed in three. 111222333 holds the front view with
    # the chair whole; 151515151 keeps everything but swings to three-quarter;
    # 555666777 brings the camera in on the legs and loses the composition. The
    # framing tags are what the square is spending, and `full body` at any
    # weight does not anchor them -- it was tried both ways here.
    #
    # Unmeasured here: the picks ran --face moe-far-noeye, and this recipe has
    # one fixed FACE block. The backdrop intruder that owned an earlier chair
    # pose answered only to the face lever, so if it comes back, that is where
    # it lives -- but none of the twelve renders here had one.
    "chair": (
        "(solo:1.5), (sitting on chair:1.4), (crossed legs:1.2), (front view:1.35), "
        "facing viewer, (gaming chair:1.4), swivel chair, backrest, full body"
    ),
    # `chair` with the smirk on, and grown up. Built on ykchairD-chair-555666777
    # (prompt c1629d37), the square render that lost the front view and sank her
    # into the seat instead -- which is the wrong result for `chair` and the
    # right starting point for this. Same canvas, same seed family.
    #
    # `(front view:1.35), facing viewer` are what pay for the smirk. That seed
    # never delivered them anyway, so the two tags were being bought and not
    # collected; the pair that replaces them is the one `lounge`, `peace` and
    # `invite` all already carry, at the weights they carry it at. Nine in,
    # nine out.
    # `(smug:1.15)`, not 1.4. At 1.4 it is gloating; at 1.15 it is composed, and
    # the chin lift and the head-spine-hip arc that `sip` measured `smug` doing
    # both survive the drop. The weight is the lever and the tag is not: swapped
    # for `(light smile:1.3)` the face arrives in roughly the same place and
    # takes a stocking off her foot on the way, and easing
    # `half-closed eyes` to 1.15 alongside it changed nothing visible at all.
    # SEED MATTERS MORE THAN THE BLOCK HERE. On 555666777 -- the render this
    # pose was built on -- her feet come up to head height, which no chair
    # supports. That is a property of the composition and not of any tag:
    # `feet on floor` was tried in two donor slots and both weighted and bare,
    # `crossed legs` was deleted outright and the knees stayed up regardless,
    # the sitting was raised to 1.6 against the crossing at 1.05, and
    # (feet up:1.45), (legs up:1.4), (knees up:1.35) went into the negative
    # alone and alongside the positive. Twelve renders, nothing moved.
    #
    # 1886970040 and 2557902837 seat her properly with the same block, so use
    # those. The nape session's rule applies: when a defect survives that many
    # prompt levers, stop diagnosing and change tools -- and the tool here is
    # the seed.
    #
    # Ground contact is not available at all on this canvas. The square crops
    # at the shins, so the floor is never in frame; the best the pose can do is
    # send the feet downward out of it. Showing a foot planted needs the floor,
    # which needs the camera back, which is the tall canvas this pose gave up
    # to get its shading.
    # `half-closed eyes` is gone and the block is eight. It was half of the
    # smirk pair every other pose carries, and once `smug` came down to 1.15 the
    # lids were the only thing still reading as attitude rather than composure.
    # F3 measured easing it from 1.3 to 1.15 as changing nothing, which was
    # true and beside the point: the tag is not gradual, it is present or not.
    #
    # To open them further on a picture that is already settled, chain a pass
    # with `(half-closed eyes:1.4), (closed eyes:1.4)` in the negative --
    # measured, and it opens them fully. Do NOT put that pair in the negative
    # here: from scratch it stacks with the buttons guard and 979797979 grows a
    # second chair with a rabbit on it. Guards are cheap in a late pass, which
    # only gets to delete, and expensive in a first pass, which gets to
    # rearrange the picture around them.
    "boss": (
        "(solo:1.5), (sitting on chair:1.4), (crossed legs:1.2), (smug:1.15), "
        "(gaming chair:1.4), swivel chair, backrest, full body"
    ),
    # A full squat seen from the side, curled forward over her knees with a mug
    # held in both hands at her mouth. Built by substituting into `crouch`'s
    # eight slots one at a time, and every slot here was paid for:
    #
    #   `drinking` is what lifts the cup to her mouth. Dropped in favour of
    #   `leaning forward`, on the theory that `holding cup` plus the mouth would
    #   carry it, the cup fell to her feet on all four renders. It stays.
    #
    #   The mug needs two slots, not one. `coffee mug` alone put a mug in the
    #   frame but not reliably in her hands; `holding cup` alone drew a paper
    #   cup or a can. Together they draw a china mug, and on some seeds steam
    #   off it -- which is the whole "ホッとしている" read, at no extra tag.
    #
    #   `leaning forward` is not how she rounds. It bends her at the hips, so
    #   the back stays straight and folds, and `hunched over` is what curves
    #   the spine instead. `slouching` does the same job and was tried in the
    #   same slot; `hunched over` won on all three seeds.
    #
    #   `smug` was spared at first, on the reasoning that she is warming up
    #   rather than showing off. That was wrong, and not about the mood: it is
    #   what holds her head up. `hunched over` alone rounds the back but pushes
    #   her neck out ahead of it, so the silhouette reads as a bend rather than
    #   a curve. The smirk lifts her chin, and head, spine and hip land on one
    #   arc. Two things asked for -- the smirk, and a rounder shape -- and one
    #   tag answered both.
    #
    #   `full body` is what pays for it; the square canvas frames her anyway.
    #   `knees to chest` is still spared, since `squatting` holds the tuck.
    #
    #   A ninth slot is where this block breaks, and both candidates for one
    #   were measured: `curled up` and `knees to chest` each stretched her
    #   sideways instead of curling her, and the cost came out of tags that
    #   were working -- the mug sank out of frame under one, and under the
    #   other her hair clips slid down to her ears. The saturation is not only
    #   a pose budget. It reaches the character.
    #
    # Seed-sensitive, and the sensitivity belongs to the block rather than the
    # seed: this block puts the cup at her mouth on 111222333, while the
    # tighter-curl variant put it on the ground on that same seed three times
    # and needed 3409564303 instead. The smirk carries across seeds where the
    # arc does not: three of three drew it, two of three closed the curve, and
    # 1029384756 sat up straight with the mug steaming anyway.
    "sip": (
        "(solo:1.5), (squatting:1.4), (from side:1.45), (hunched over:1.45), "
        "(smug:1.3), (holding cup:1.3), (drinking:1.2), (coffee mug:1.3)"
    ),
    # The back of her neck, seen by someone standing behind her while she sits.
    #
    # Framing was the whole problem and the answer was not to move the camera
    # closer. `(upper body:1.35)` lost to `from behind` every time, and the
    # obvious fix -- `close-up` and `head and shoulders`, which the portrait
    # uses -- draws a character reference sheet instead: two figures side by
    # side, front view and back view, the back one in a strapless dress. A
    # composition guard in the negative does not stop it. Neither tag is usable
    # in a shot that is already looking at her from behind.
    #
    # Seating her is what solved it. She is below the camera, so the nape is
    # what faces it, and `(upper body:1.3)` is enough. `from above` tilted a
    # standing figure diagonally and behaves against a seated one, which has
    # somewhere for the angle to land.
    #
    # `(nape of neck:1.45)` does not come down. Dropped to 1.25 it does not
    # merely soften -- the pose collapses and she turns to face the camera.
    # The exposure it brings has to be answered in the negative instead; see
    # `negative`.
    # `yokozuwari`, not `sitting on floor`. The thighs read too long under the
    # latter and no amount of describing them fixed it: `thick thighs` down to
    # 1.15, `(long legs:1.4)` in the negative, `(petite:1.35)`, and the camera
    # angle eased to 1.3 all changed nothing. They could not, because the
    # length was never asserted -- `sitting on floor` extends the legs, and a
    # leg extended away from a camera looking down runs the frame. Naming the
    # sitting folds them, and the knee lands where the eye expects it.
    "nape": (
        "(solo:1.55), (from behind:1.45), (from above:1.45), (yokozuwari:1.4), "
        "(nape of neck:1.45), (hair over shoulder:1.35), (head down:1.25), (back focus:1.3)"
    ),
    # Face down on the floor, chin in her hands, feet swinging up behind her.
    #
    # `lying` and `on stomach` are one unit -- the second is a qualifier for the
    # first and is not used alone -- so the posture costs two slots before
    # anything else is asked for. `chin rest` props her up on her elbows and
    # `feet up` lifts the shins; together they are what separates this from a
    # body face down on the ground. Eight tags after (solo:1.5), which is the
    # budget every block here is held to.
    #
    # The steadiest pose in this file on first measurement. Six seeds, six with
    # one girl, six lying face down with the chin on the hands and the feet up,
    # no clothing failures and no bare skin. `crouch` needed eleven seeds to
    # earn that sentence and `hunt` never did.
    #
    # Stroke per 1000px over the six: 1.72 and 1.75 at the fine end, 1.94 and
    # 1.99 in the middle, 2.18 and 2.20 at the heavy -- straddling the recipe's
    # 1.91, so nothing here breaks the line. (Median is 2.00 on all six and says
    # nothing; a median over small integers is a vote, not a measure.)
    #
    # 737373737 is the loosest of the six and worth knowing about: the hem rides
    # up over the hip and the grey tights carry the whole lower half of the
    # frame. Covered, but it is the seed closest to the rear-forward framing
    # this project has thrown compositions away over. 555666777, 111222333 and
    # 2557902837 are the clean ones.
    #
    # `from above` is at 1.35 rather than the 1.45 `nape` uses. She is already
    # horizontal, so the angle only has to look down at her -- raised, it is the
    # tag most likely to buy the overhead rear view that the portrait canvas
    # drew on its own (see SIZES).
    #
    # `--hires 2048` at the default denoise, and that is a correction. The
    # measurements are unchanged -- the second pass takes the stroke from 1.941
    # per 1000px to 1.274 and redraws the die-cut edge as a stroke rather than a
    # cut -- but "this canvas already lands on 1.91, so the pass has nothing to
    # give" was a conclusion drawn from a number, and the thinner, looser line
    # is the one that was picked. 1.91 is what `fb-b` measured, not a target the
    # recipe is aiming at.
    #
    # 0.45 is not the same thing softened; it scribbles the outline instead of
    # drawing it, and 3072 blurs it to a halo. The line that was wanted is 2048
    # at 0.60 specifically.
    #
    # The six-seed sweep above predates the legwear splice in `positive()`, so
    # its "no clothing failures" is about the pose block and not about what the
    # grey layer was doing behind it.
    "prone": (
        "(solo:1.5), (lying:1.45), (on stomach:1.5), (from above:1.35), "
        "(chin rest:1.35), (feet up:1.3), (smug:1.35), (half-closed eyes:1.3), "
        "full body"
    ),
    # Standing, facing the camera, hands behind her back -- the plain 立ち絵
    # this file never had. Every other pose here sits, lies or squats, so this
    # is the first block whose figure is vertical in a vertical frame, and the
    # thing to watch on the first sweep is the crop: a standing body at
    # 1024x1536 is the case `full body` exists for, and the poses that lost
    # their shins lost them to a canvas rather than to a tag.
    #
    # `(from front:1.3)` is here for the same reason `nape` spends a tag on its
    # angle: standing is the posture the model has the most other ideas about
    # (three-quarter turns, walking, from below), and this is the one that says
    # which of them. `(from below:1.35)` is already in NEGATIVE and does half
    # the job from the other side.
    #
    # Hands in front at the chest, and nothing held: a prop is a second thing to
    # get right and the point of a standing reference is the costume. It started
    # as `(arms behind back:1.3)` -- 「ては出して欲しい。胸あたりに出す感じ」 --
    # and `own hands together` is the tag for the gesture. `(hands up:1.25)` is
    # what puts them at the chest rather than at the waist; measured against the
    # same seed without it, which lands them low. That is the ninth tag this
    # file keeps warning about and it is spent here on purpose.
    #
    # `(arched back:1.2)` took `head tilt`'s slot rather than being added to it.
    # It is here because two renders of the same seed differed only in LEGWEAR's
    # TOKEN ORDER and one of them stood slightly chest-out -- the posture came
    # from the encoding, not from any tag, so it is not repeatable and had to be
    # named to be kept. Measured at 1.2 in this slot, at 1.2 alongside `head
    # tilt` (nine tags) and at 1.35 in this slot; the first is what was picked.
    # It is a tag that leans pin-up when raised, which is why the range was
    # swept downward rather than up.
    #
    # ---- and then it turned out the legs were not in the frame ----
    #
    # `full body` did not hold a standing figure. Measured rather than looked
    # at: the figure mask ran to the last row of the canvas on every arm, and
    # the crop was at mid-calf. Two changes, and they are coupled:
    #
    #   `(full body:1.45)`        the bare tag was the only thing arguing for
    #                             the whole figure and it lost to the canvas.
    #   `(black footwear:1.35)`   at a canvas that DID fit the leg, the model
    #                             ended it in a rounded stump. Nothing in this
    #                             prompt had ever named a shoe, so there was no
    #                             foot to draw. Naming one draws it -- and it is
    #                             black, which is where the leg is supposed to
    #                             end anyway.
    #
    # Ten tags after (solo:1.5), against the eight this file keeps quoting. The
    # budget was measured on a seated pose in a frame that fit; a standing
    # figure spends two tags just staying inside the picture.
    #
    # The footwear is an ADDITION TO THE COSTUME, not a framing tag, and it has
    # not been checked against the official design. If her shoes are wrong, this
    # is the tag to argue with -- but removing it brings the stumps back, so it
    # has to be replaced rather than deleted.
    "stand": (
        "(solo:1.5), (standing:1.5), (from front:1.3), (own hands together:1.35), "
        "(hands up:1.25), (arched back:1.2), (smug:1.35), (half-closed eyes:1.3), "
        "(full body:1.45), (black footwear:1.35), (high tops:1.35), "
        "(wide shot:1.3)"
    ),
    # Seated with one leg thrust at the camera, sole first. Built from a
    # reference the user supplied rather than from a render of this recipe, so
    # nearly everything below is a first guess and is labelled as one.
    #
    # THE FOOT GETS TWO SLOTS, not one. `sip` established that the thing a
    # composition is built around does not fit in a single tag -- its mug needed
    # `coffee mug` and `holding cup` together, and either alone drew the wrong
    # object or put it in the wrong place. The same split applies here: `soles`
    # names what faces the camera, `foot focus` names where the camera looks.
    # Neither is the picture on its own.
    #
    # `foreshortening` is bought rather than left to the seed, and it is doing
    # two jobs. A leg pointed at the lens either compresses or reads as a long
    # leg lying across the frame -- and reading too long is the failure this
    # recipe has spent the most on. `nape` found that `sitting on floor` extends
    # the legs and that a leg extended away from the camera runs the frame;
    # `flop` had to have its `long legs` weight bracketed from both sides. What
    # was the defect in both of those is the subject here, so the tag that
    # governs it does not get spared.
    #
    # `knee up` is SINGULAR on purpose: one leg folded, one out is the whole
    # asymmetry. `knees up` raises both and is a different picture.
    #
    # `couch` is the cheapest thing that makes `leaning back` mean something --
    # leaning back against nothing is falling. It is not what was asked for (the
    # leg was), and it is the first slot to spend if the block needs one.
    #
    # NO FOOTWEAR GUARD, and that is a decision rather than an oversight.
    # `stand` is the only pose in this file that names a shoe, so nothing here
    # asks for one -- but nothing forbids one either, and a shoe sole is a
    # different picture from a pantyhose sole. Guarding it means naming a shoe
    # in the negative, and `stand`'s own note says that naming a shoe drew one.
    # Find out whether the guard is needed before paying for it.
    #
    # `full body` is NOT in the block, and its absence is what the first round
    # is measuring against. `foot focus` can walk the camera down to the foot
    # and leave the head out of frame, which is this pose's likeliest failure,
    # and `full body` is the counterweight every other whole-figure block here
    # carries. Eight slots is the house size, so the ninth goes in only if the
    # first round loses the face.
    # THE EXPRESSION IS IN PASS 1, and it took four rounds and a losing arm to
    # earn that sentence. It was in `HIRES_POSITIVE` first, on the reasoning
    # that a late pass buys the face without the posture -- which is true, and
    # was not the constraint. Copied verbatim from 10915a12, guard tail and all,
    # a 0.60 pass could not overwrite a face the base image had already drawn
    # calm and closed-mouthed. Moved here, the same words work. **A late pass
    # refines a decision; it does not reverse one, and an expression is a
    # decision pass 1 makes.**
    #
    # It costs the composition, which is exactly what this pose spent four
    # rounds refusing to pay. It was paid because the expression had been asked
    # for four times and had not arrived once.
    #
    # NO TOE TAG IN THIS BLOCK, and the reason is not the toes -- it is the
    # palette. Measured across the series at seed 111222333, mean saturation of
    # the figure against the costume's own colours:
    #
    #   13 tags, no toe tag                 sat  52.5   coat 37.7%  hair 5.0%
    #   + (toes:1.4)                        sat 113.5   coat 20.7%
    #   + (five toes:1.6)                   sat 187.8   coat  0.2%
    #   + (toe scrunch:1.35 / 1.55)         sat 196.9 / 198.9   coat 0.1% / 0.0%
    #
    # The costume colours do not merely shift, they LEAVE. And it is not the
    # slot count: dropping back to thirteen and to twelve with the toe tag still
    # in measured 196.0 and 142.3, so the count was a coincidence of the toe tag
    # always having been the one added last.
    #
    # NEGATIVE toe guards cost nothing at all -- 40.3, 51.0, 47.7, all at or
    # better than the clean block. So the axis is not "toes"; it is that a
    # POSITIVE toe tag pulls this prompt somewhere with a different palette,
    # and subtraction does not.
    #
    # DO NOT GUARD THE TOES. 「指が6本あるねえ」 on the sole that is the nearest
    # thing to the lens, and both sides of the tag axis were spent on it:
    #
    #   positive  `(five toes:1.3)` rode four consecutive renders. Six toes.
    #             Naming a number does not count; it failed while the count was
    #             wrong in the direction it named.
    #   negative  `(extra toes:1.45)` and `(extra digits:1.45)`, in PASS 1 where
    #             the topology is decided. Neither corrected the count -- both
    #             DISSOLVED THE TOES, leaving a smooth sole with no separation
    #             at all. A guard is a deletion, and what it deleted was the
    #             feature rather than the surplus. Zero is not five.
    #
    # So the tag axis is exhausted, and `nape`'s rule applies: when a defect
    # survives that many prompt levers, stop diagnosing and change tools. The
    # tool is the seed -- toe topology is a first-pass structural fact, and
    # raising the first-pass canvas to give the foot more room is the one
    # escape this file has already measured shut (a second figure at 1280x1920).
    #
    # `(full body:1.4)` was written OUT of this block on the first round, as the
    # B arm, with the note that `foot focus` can walk the camera down to the foot
    # and leave the head out. Four seeds then did exactly that, four times out of
    # four -- and both renders picked before that were on 2557902837, which had
    # been carrying the framing on its own. It is in now, on fa504c93.
    #
    # THIRTEEN TAGS, and this file's own note says a pose block breaks around
    # nine -- `sip` lost its mug and its hair clips to a ninth. It held here.
    # That is a data point and not a licence: the next tag added to this block
    # is on thinner ice than the count suggests, because the four that pushed it
    # past the line were all expression and none of them touched the pose.
    "kick": (
        # `(couch:1.2)` is gone (2026-08-26): the sticker delivery wants the
        # white band and the marker on HER alone, and the model draws the band
        # around subject-plus-couch as one thing. No tag un-outlines a couch,
        # so the couch is what goes. She still gets seated -- the model invents
        # a ledge or sits her on the frame edge -- and the picked render
        # (0db8e020, seed 737373737) is this form.
        "(solo:1.5), (sitting:1.45), (soles:1.4), (foot focus:1.35), "
        "(foreshortening:1.3), (knee up:1.25), (leaning back:1.25), "
        "(smug:1.3), (confident:1.25), (half-closed eyes:1.25), (open mouth:1.35), "
        "(full body:1.4)"
    ),
    # 「腹筋が全くできないゆかりさん」. The joke is a NEGATIVE result -- the
    # picture has to show the sit-up not happening -- and nothing in this file
    # has drawn a failed action before. Every other pose here is a state she is
    # in; this one is an attempt that does not come off, and the whole block is
    # built around which half of it the model must not complete.
    #
    # Four tags set the apparatus and they are the ones flop already proved:
    # `(lying:1.45), (on back:1.5)` put her down, `(knees up:1.4)` bends the
    # legs the exercise needs, `(hands behind head:1.35)` is the sit-up's own
    # arm position and is a 200k-post tag, unlike anything naming the exercise.
    #
    # `(sit-up:1.3)` is deliberately the WEAKEST of them. It names the feature
    # -- without it the four above read as lying down comfortably -- but raised
    # it is the tag most likely to draw the successful rep, which is the one
    # picture this pose must not produce. If she comes up off the floor, this
    # is the weight to lower before touching anything else.
    #
    # The strain is `(clenched teeth:1.35)`, and it costs `closed mouth` out of
    # FACE (declared in costume_check, `open_mouthed` in positive()). A smug
    # 半目 is this character's default and it is exactly wrong here: composure
    # reads as a rest, not as a failure. `(sweatdrop:1.3)` over `sweat` on
    # purpose -- the anime bead is a comic marker, where `sweat` buys wet
    # shine and this recipe is flat colour.
    #
    # Untested, and the two things to watch on the first sweep are the costume
    # and the camera. A sit-up recruits a gym: the negative carries a
    # sportswear guard for this pose (see `negative()`), because the costume is
    # a contract and an exercise scene is the strongest pull away from it this
    # file has tried. No angle tag is spent yet -- flop holds a body on the
    # floor at this canvas without one -- but a side view is what reads
    # "shoulders still down", so `(from side:1.3)` is the first lever if the
    # camera looks straight down and flattens the failure out of the picture.
    # ---- 「筋肉がなさすぎて猫背になってしまう」 ----
    #
    # The punchline moved. The first block's failure was "she does not come up";
    # this one's is "she comes up WRONG" -- no core to lift with, so the spine
    # rounds and the neck does the work. That is a shape, and a shape is
    # drawable in a way that an absence is not.
    #
    # `(slouching:1.4)` took `(sweatdrop:1.3)`'s slot rather than being added to
    # it. Nine tags is where this file's blocks start losing things, and the
    # bead was the one tag in here that decorates rather than describes -- the
    # strain still has `(clenched teeth:1.35)` carrying it.
    #
    # ONE tag for the feature. `(hunched over:1.4)` names the same thing and the
    # pair of them is exactly the shape that cost the toe work its accents; it
    # is the B arm in `.local/situp_arms.py`, not a second guard here.
    #
    # The negative gains `(arched back:1.4)` for this pose, and it is the
    # load-bearing half of the change: 猫背 has a direct opposite, this model
    # reaches for it unprompted on anything lying down, and `stand` spends a
    # positive tag on that arch on purpose. Naming the shape without forbidding
    # its opposite is half a lever.
    # ---- 「腹筋要素が0になった」 ----
    #
    # And this file has the note that predicted it. The toe work ends with **"a
    # guard is a deletion, and what it deleted was the feature rather than the
    # surplus. Zero is not five."** The same mistake, arrived at from the
    # positive side: `(sit-up:1.3)` was pinned at the BOTTOM of the block on the
    # argument that raising it would draw a successful rep -- and the failure
    # mode that actually turned up is the one where the exercise is not in the
    # picture at all. A rep drawn too well is a note to write; no rep is no
    # picture. **Do not spend a weight defending against a feature's excess
    # before the feature has been shown to appear.**
    #
    # Three changes, all the same change -- move weight off the state and onto
    # the action:
    #
    #   `(sit-up:1.5)` raised, and moved to the slot straight after (solo:1.5).
    #                  It is the subject; at position six behind two tags that
    #                  say she is lying down it was a footnote.
    #   `(on back:1.4)` lowered from 1.5. A crunch is not flat, and this tag
    #                  was saying "resting" louder than anything was saying
    #                  "exercising".
    #   `(slouching:1.35)` eased a notch, for the same budget reason: it won the
    #                  last round outright and that is the problem.
    #
    # `(yoga mat:1.3)` came OUT of this pose's negative -- see `negative()`. It
    # was aimed at the wardrobe and took the scene with it.
    # ---- picked: a61a67a8, seed 1886970040, the F arm ----
    #
    # `(from side:1.35)` is IN the block, and it is what the pose was missing
    # for three rounds. It was named as the first lever the day the pose was
    # written and then not taken, twice, while three rounds of weights argued
    # about words instead. **A sit-up is a silhouette before it is a tag**:
    # bent knees and a torso at an angle read as the exercise from the side and
    # as a girl lying on the floor from anywhere else. No weight on `sit-up`
    # buys that geometry, because it is the camera and not the subject.
    #
    # NINE tags after (solo:1.5), against the eight this file keeps quoting.
    # `kick` held thirteen and this held nine; the budget is a smell, not a
    # rule, and the tag that pushed it over is the one doing the work.
    "situp": (
        "(solo:1.5), (sit-up:1.5), (from side:1.35), (lying:1.45), "
        "(on back:1.4), (knees up:1.4), (hands behind head:1.35), "
        "(slouching:1.35), (clenched teeth:1.35), full body"
    ),
    # Both arms thrown out and down, a V in each hand, weight forward, grinning
    # with her teeth showing. `peace` is the other double-V pose in this file
    # and it is a still one -- hands up by the face, one V over an eye. The
    # difference this pose is for is the body: the arms are away from her and
    # the shoulders are ahead of the hips.
    #
    # Nine tags. `(arms out:1.3)` is what keeps the Vs off her face -- without
    # it `double v` is drawn at the chin, which is `peace` again. `(grin:1.4)`
    # is the expression and it is why `hype` joins `open_mouthed` below: FACE
    # nails the mouth shut and a grin with a shut mouth is a smirk.
    "hype": (
        "(solo:1.5), (standing:1.45), (from front:1.3), (leaning forward:1.35), "
        "(legs apart:1.3), (double v:1.45), (arms out:1.3), (grin:1.4), "
        "(full body:1.45)"
    ),
    # 「がおーッ」. Both hands up as paws beside her face, mouth open, leaning in
    # at the camera. `(claw pose:1.55)` is the tag that draws the hands and it
    # carries the whole pose -- everything else here is what keeps it playful
    # rather than monstrous, which is the axis this one can fall off.
    #
    # `(fang:1.3)` and not `(sharp teeth)`: the second draws a mouthful and the
    # joke is one tooth. `(open mouth:1.4)` puts the pose in `open_mouthed`, so
    # FACE gives up `closed mouth` -- a がおー with a shut mouth is a shrug.
    #
    # `(leaning forward:1.3)` is `hype`'s tag at a lower weight. It is what
    # makes the hands read as coming AT the viewer instead of resting beside
    # her head, and it is eased because this pose already has the arms up and
    # `hype` at 1.35 was fighting nothing.
    "roar": (
        "(solo:1.5), (standing:1.45), (from front:1.3), " + GAO_HANDS + ", "
        "(hands up:1.35), (leaning forward:1.3), " + GAO_FACE + ", "
        "(full body:1.45)"
    ),
    # がおー crouched, a beat before it goes off. `roar` is the shape at rest --
    # standing, hands beside her head; this is the same hands and the same face
    # with the body loaded. `(leaning forward:1.45)` is the highest weight that
    # tag carries in this file and it is doing the work `roar` gives to
    # `(standing:1.45)`.
    #
    # `(arms up:1.3)` rather than `roar`'s `(hands up:1.35)`: from a squat the
    # hands come up from below and the whole arm is in it. Eased, because a
    # crouch already puts the shoulders where the tag was pushing them.
    #
    # No low camera, and this is not an oversight: `(from below:1.35)` is in
    # NEGATIVE for every pose but `lap`, and the one place this file took it out
    # it had to be taken out by name. A pounce shot from below is the obvious
    # framing and it is not available without paying for it.
    # THE STANCE IS A KNEE, NOT A SQUAT. 978fb1f1 was picked off the squat and
    # then asked for 「片膝は着くくらい」, which is not something a render can be
    # adjusted into -- the prompt change redraws the picture and a low-denoise
    # refine cannot build a limb into a new position. So the squat's render was
    # spent, deliberately, and two arms were swept in the one slot that decides
    # the stance:
    #
    #   ka   (one knee:1.45)                    one substitution, one slot
    #   kb   (kneeling:1.4), (one knee:1.45)    the pair
    #
    # kb won on 9b2dfdf6 (seed 1886970040), and it is the arm this file's usual
    # rule argues against: two tags at one defect is how the palette has been
    # wrecked here before. It is not that rule's case. Those failures were
    # GUARDS stacked in the negative, outvoting each other's neighbours; this is
    # a stance named twice in the positive, where `kneeling` is the posture and
    # `one knee` is which knee. `ka` alone drew the knee on some seeds and a
    # deeper squat on others, which is the disease this file describes as an
    # unweighted tag being indistinguishable from an absent one.
    #
    # `(leaning forward:1.45)` and both paws stay up. A knee down invites the
    # three-point stance -- one hand to the ground -- and that costs half the
    # がおー, which is the thing this pose is a member of.
    "pounce": (
        "(solo:1.5), (kneeling:1.4), (one knee:1.45), (from front:1.3), " + GAO_HANDS + ", "
        "(arms up:1.3), (leaning forward:1.45), " + GAO_FACE + ", "
        "(full body:1.45)"
    ),
    # がおー at full stretch: up on her toes, arms above her head, as big as she
    # can make herself. The opposite end of the same gesture from `pounce`, and
    # the reason the family is worth having -- one motif, three amplitudes.
    #
    # `(standing on tiptoes:1.35)` is the tag that buys the last of the height
    # and it is the risky one: this recipe's toe work (see the `kick` sections)
    # is a record of how badly this model draws feet when asked to look at them.
    # It is here at 1.35 and not higher for that reason, and the shoes help --
    # `sporty` has sneakers on, which is a foot the model does not have to draw.
    "loom": (
        "(solo:1.5), (standing:1.45), (from front:1.3), " + GAO_HANDS + ", "
        "(arms up:1.45), (standing on tiptoes:1.35), " + GAO_FACE + ", "
        "(full body:1.45)"
    ),
    # ストローで紙コップのドリンク. Built on `sip`'s measurements rather than on
    # `sip` -- that pose is a side-on squat with a china mug and shares nothing
    # with this but the fact that something is being drunk.
    #
    # Three findings from that pose are load-bearing here:
    #   `drinking` is what LIFTS the vessel to the mouth. Without it `holding
    #   cup` puts the cup in her hand and the hand stays down; on one sweep the
    #   can ended up at her feet in four of four.
    #   `holding cup` alone draws a paper cup or a can, which is the vessel this
    #   pose wants -- so the noun is nearly free here where `sip` had to spend a
    #   slot on `coffee mug` to get china.
    #   Naming the vessel twice is what pins the type, and is also what drew two
    #   of them on 1117511306. It was tried here -- `(disposable cup:1.5)`
    #   beside `holding cup`, four seeds against four without it -- and 9082bedc
    #   was picked off the arm WITHOUT it. The second noun bought nothing this
    #   pose needed, so it is gone. `sip` had to spend that slot to get china;
    #   a paper cup is what this model reaches for unaided.
    #
    # This block used to claim that `(logo:1.4), (print:1.35)` are in NEGATIVE
    # and that they are why the cup comes out plain. **They are not in
    # NEGATIVE.** They are appended by `_negative_base` for `stand` and for no
    # other pose, so `straw`'s plain cup is the model's own doing and has no
    # guard behind it. The claim cost a real render to disprove: the sporty tee
    # arrived with a watermelon print on `snack`'s sweep, on a pose that has no
    # such guard, which is what a costume relying on this would look like.
    #
    # NOT in `open_mouthed`: FACE's `closed mouth` is correct with a straw --
    # lips around it, not a shout.
    "straw": (
        "(solo:1.5), (standing:1.45), (from front:1.3), (holding cup:1.45), "
        "(drinking straw:1.55), (drinking:1.3), (full body:1.45)"
    ),
    # 菓子パン, sitting down. `straw`'s vessel grammar one size smaller, and
    # every slot does the same job it does there:
    #
    #   `(holding food:1.45)` is `holding cup`. It puts the thing in her hand
    #   and says nothing at all about where the hand then goes.
    #   `(eating:1.4)` is `drinking`: the tag that lifts it to the mouth.
    #   `(melon bread:1.5)` is the second naming, and this is the case `ride`
    #   paid for rather than the one `straw` got free. Bare `bread` draws a loaf
    #   or a slice -- danbooru has `bread` at 21k and `bread_slice` at 5.5k --
    #   and neither is a 菓子パン. `melon_bread` at 1.5k is the archetype, and
    #   the only sweet roll there with a count worth spending a slot on
    #   (`cream_bread` 143, `curry_bread` 66).
    #
    # The chair is NOT named twice, and that is the same judgement seen from the
    # other side: a plain chair is what the model reaches for unaided, like
    # `straw`'s paper cup. `chair` spends `gaming chair, swivel chair, backrest`
    # because a gaming chair is not the default one. That is `ride`'s road bike,
    # and it is not this.
    #
    # **Seated because standing could not keep its shoes on.** 「パンを食べてる
    # ときに靴は触っちゃダメよw 椅子に座って食べるのもOK」. The other arm of the
    # first sweep was a `cowboy shot`, which crops at the thigh -- and the
    # sporty costume's `(white footwear:1.4), (sneakers:1.45), (high tops:1.3)`
    # then had no referent, while `holding food` was sitting there as an open
    # slot for an object. She was drawn holding a sneaker in 2 of 4 seeds and
    # standing over a loose one in a third. Deleting the three tags fixed it 4
    # of 4, which is the HEAD_FRAMINGS rule one crop shallower: naming what is
    # out of frame is what invites it back in. This pose needs no such deletion,
    # because the feet are in frame -- it is the framing that makes the costume
    # honest again, not a guard.
    #
    # In `open_mouthed`, against `straw`'s reading of the same question: lips
    # close around a straw and a bite does not. FACE's `closed mouth` is removed
    # rather than replaced -- nothing here asks for `(open mouth)` -- so a bite
    # is permitted and a shout is not commanded.
    "snack": (
        "(solo:1.5), (sitting on chair:1.45), (front view:1.35), "
        "facing viewer, (holding food:1.45), (melon bread:1.5), "
        "(eating:1.4), (full body:1.45)"
    ),
    # バスケなんてやりたくないですよぉ〜〜〜〜〜. The object grammar again, and by
    # now it is a form to fill in rather than a thing to work out:
    #
    #   `(holding basketball:1.5)` is ONE noun, and that is the correction.
    #   It was `(holding ball:1.45), (basketball:1.5)` -- the two-noun form the
    #   grammar prescribes -- and it drew TWO BALLS, which is precisely the
    #   hazard `ride` records for its own second naming ("two bicycles is the
    #   first thing to look for"). `ride` accepted that cost because a road bike
    #   is not the default bicycle; here the fused phrase pins the type without
    #   paying it, so there is nothing to accept.
    #
    #   Danbooru's tag is `basketball_(object)` at 6k, but parentheses are
    #   weight syntax in a prompt and cannot be written. The plain word reaches
    #   the text encoder perfectly well, which is the one place this file's
    #   tag-count discipline has to bend to the tokenizer.
    #
    #   `(spread fingers:1.3)` 5.6k WAS here and is gone. It asked for open
    #   fingers and the model obliged with too many of them; dropping it gave
    #   the cleanest upper hand of any arm. The tag to suspect for a bad hand is
    #   not always a guard that is missing -- sometimes it is a request that is
    #   present.
    #
    #   `(short dress:1.35)` 130k is the SILHOUETTE an oversized tee makes once
    #   it reaches the thigh, named so the model draws that shape rather than a
    #   shirt that stops at the hip. It is the tag that finally covered her, and
    #   it was reached only after `oversized shirt` had been swept across six
    #   weights in three rounds. The risk it carries -- that an actual dress
    #   arrives instead -- did not materialise on any of three seeds.
    #
    #   `(hugging object:1.4)` 32k is the grip
    #   in the reference photo: the ball at chest height, a palm on each side,
    #   fingers open. 「両側から押し抱えてる？感じがいいな。バスケだし」. **There is
    #   no tag for holding something with both hands** -- not in `holding_*`,
    #   not under `*both_hands*`, and `holding_to_chest` is 102 posts. So the
    #   grip is spelled as a clutch plus a hand shape, which is the same
    #   position `side_slit` left this file in: the picture exists in the
    #   training data and the word for it does not.
    #
    # **`(@_@:1.0)` is NOT re-measured here.** `dizzy` owns that finding and the
    # value is the finding: 1.45 draws a near-black spiral on a white sclera,
    # `spiral eyes` and `dizzy eyes` are not danbooru tags at all, and 1.0 is
    # the weight on the render that was picked (49b3aab4). Copied at its
    # measured value, not re-swept.
    #
    # `(dizzy:1.3)` comes with it for the reason `dizzy` records: it went in as
    # a floor under the symbol, in case `@_@` did not draw, and stayed because
    # it carries the state when the symbol is faint. Three arms were run and the
    # one WITH it was picked, so on this pose the floor is doing visible work.
    #
    # `(wavy mouth:1.4)` 101k and `(flying sweatdrops:1.4)` 126k are the whine
    # and its punctuation. In `open_mouthed`: 〜〜〜 is a drawn-out complaint and
    # FACE closes the mouth. Removed, not replaced -- `snack`'s rule.
    #
    # The joke is the costume: `fitness` is a gym kit, so she is already dressed
    # for the thing she does not want to do. Nothing in the block says so, which
    # is right -- SURFACE is a flat backdrop and a court would fight it, the
    # same contract `ride` keeps by putting her on a bike in front of nothing.
    "hoops": (
        "(solo:1.5), (standing:1.45), (from front:1.3), "
        "(holding basketball:1.5), (hugging object:1.4), "
        "(@_@:1.0), (wavy mouth:1.4), "
        "(flying sweatdrops:1.4), (dizzy:1.3), (full body:1.45), "
        "(short dress:1.35)"
    ),
    # 運動不足で息も絶え絶えで床に座り込む. `hoops` の続き -- she is still in the
    # gym kit, now on the floor. The reference is a stick figure: legs stretched
    # out in front, both hands planted on the floor BEHIND her, head back, mouth
    # open, sweatdrops flying.
    #
    # **Half the words for this state are not tags.** Counted before use:
    # `panting` 0, `tired` 0, `fatigue` 0, `sitting_on_floor` 0,
    # `outstretched_legs` 956, `hands_on_floor` 985. What carries the state is
    # `heavy_breathing` 51k, and what carries the hands-behind shape is
    # `arm_support` 118k -- the tag is already exactly this gesture, so the
    # 985-count literal naming of it is not needed.
    #
    # `(from side:1.35)` 333k is load-bearing, not framing taste. Legs thrown
    # forward are foreshortened into nothing by a front camera; the first sweep
    # of this pose was nine renders all shot `from front` and that is what was
    # wrong with them. It costs the face its three-quarter turn, which is why
    # `looking at viewer` comes out below.
    #
    # **The legs are straightened by a DELETION.** No tag says "legs extended"
    # in a count that moves a picture, but `knees_up` 81k is exactly the bend to
    # remove, and it goes in the negative -- the same shape as the knot and the
    # third arm, where naming the thing to delete beat every attempt to draw the
    # thing wanted. `legs_together` 37k keeps them closed, which the costume's
    # standing 「股を出さずに」 requires.
    #
    # `(>_<:1.45)`, and the road to that number is the useful part. 93.7k posts,
    # more than `@_@` at 55.7k, so the tag is real. Two priors said to keep the
    # weight LOW -- `(@_@:1.45)` drew literal black spirals on the whites and
    # `dizzy` picked 1.0; `swelter` swept `(>_<:1.4)` against `(closed eyes:1.4)`
    # and the symbol lost -- and 1.0 was duly swept against 1.3 and picked.
    #
    # **Then the seed changed and 1.0 stopped drawing anything at all.** On
    # 111222333 the eyes came out open, and 1.3 and 1.45 both brought the symbol
    # back without drawing a glyph on the whites. So the window is real and it
    # MOVES WITH THE SEED: the same weight that was correct on one pass 1 is
    # invisible on another. A face symbol has to be re-checked on any seed it is
    # carried to, and re-checked in both directions -- too low is as wrong as
    # too high, and this file only had the too-high failure written down.
    #
    # `(feet out of frame:1.4)` 236k, and it is here because the ankles could
    # not be drawn. 「足首から靴の向きが骨折しているとしか見えない」 on the
    # settled render: one shoe sole-on, one shoe not joined to a leg, and a
    # third lace-covered lump between them.
    #
    # **Three second-pass guards were tried first and none of them touched it.**
    # `shoe_soles` 18.4k for the sole-on view, `single_shoe` 10.8k for the odd
    # count, and dropping the costume's own `(high tops:1.3)` -- ink coverage
    # over the lower half moved 44.9 to 44.3, i.e. nothing. A late pass can
    # delete a drawn object; it cannot re-articulate a joint. That is
    # `refine-cannot-rebuild-structure` measured on a fourth pose.
    #
    # Which left re-rolling pass 1, and the cheap exit was to re-roll it with
    # the broken region outside the frame. Note what this tag is NOT: it is a
    # framing decision, so it only works in the pass that decides framing.
    # Putting it in the second pass would be the same mistake as the guards.
    #
    # It does not land the same way on every seed. On 111222333 -- the seed this
    # pose was settled on for COLOUR -- the figure still reached the bottom edge
    # in full, so the cheapest exit was closed on exactly the seed that had the
    # flattest paint. Four seeds were run with and without; 737373737 is the
    # pick, at some cost in saturation (31.4 against 22.4).
    #
    # `(sweat:1.3)` is deliberately the lowest weight in the block. 763k and
    # strong, but it is drawn as SHEEN, which is the same axis as the pass-2
    # gloss this round was spent removing. The state is carried by the symbol
    # side instead -- `flying_sweatdrops` 126k, `hoops`'s tag. `steaming_body`
    # 42k is left out for `hoops`'s reason: steam is scenery and SURFACE is a
    # flat backdrop.
    "winded": (
        "(solo:1.5), (sitting:1.5), (on floor:1.45), (from side:1.35), "
        "(arm support:1.5), (leaning back:1.4), "
        "(outstretched legs:1.5), (legs together:1.4), "
        "(open mouth:1.5), (>_<:1.45), (wavy mouth:1.4), (looking up:1.35), "
        "(heavy breathing:1.45), "
        "(flying sweatdrops:1.35), (sweat:1.3), "
        "(feet out of frame:1.4), (full body:1.45), (short dress:1.35)"
    ),
    # バスケ帰りの電車で寝落ち. `hoops` と `winded` の続き -- the same gym kit one
    # train ride later, and the state has gone from gasping to spent.
    #
    # Counted before use: `sleeping` 100k, `sleeping_upright` 4.3k,
    # `head_tilt` 173k, `zzz` 15.8k, `towel_around_neck` 9.4k, `messy_hair`
    # 91k, `bench` 21.7k, `arms_at_sides` 38.8k. Two words the scene wants are
    # not tags at all -- `dozing` 0 and `nodding_off`, which has no page -- and
    # `tired` is 0 here for the third time in this file. `exhausted` IS real at
    # 3.7k and is still left out: at that count it is a word, and the state is
    # carried by the posture and the symbol the way `winded` carries panting
    # with `heavy_breathing` and sweatdrops rather than with a word for being
    # tired.
    #
    # `(sleeping upright:1.45)` is the pose, and it is the whole reason this is
    # not `flop` with the camera moved. 4.3k is thin for a load-bearing tag, so
    # it is weighted ABOVE the 100k `sleeping` under it rather than left to be
    # outvoted: `sleeping` alone at 100k is a girl in a bed, which is the one
    # picture this pose must not be.
    #
    # `(head tilt:1.4)` 173k is the lolled head. It is the tag doing what
    # `slouching` 1.0k and `head_down` 3.7k are too thin to do -- the same
    # choice `winded` made when it spelled hands-behind as `arm_support` 118k
    # instead of the literal 985-post naming.
    #
    # `(zzz:1.35)` is on the file's idiom rather than on its count: `@_@`,
    # `>_<` and `flying_sweatdrops` each carry a state the drawing has no other
    # way to say, and this is the sleep one. `dizzy`'s finding applies to it
    # unmeasured -- a face symbol has a weight window and THE WINDOW MOVES WITH
    # THE SEED -- so a glyph drawn on the cheek, or no symbol at all, is the
    # first dial to turn and not a fault in the rest of the block.
    #
    # **The carriage is not in the picture, and that is `ride`'s contract kept
    # rather than an oversight.** SURFACE is a flat grey backdrop; a train
    # interior is a scene, and a scene whose whole point is a row of other
    # passengers is also the second figure this file spends canvas width to
    # keep out. So 帰り is said with what she is WEARING: a towel round the neck
    # cannot fall out of the composition the way a loose bag can, which is
    # `sip`'s finding -- an object tag puts the object in frame and says
    # nothing whatever about where it ends up. `(bench:1.3)` is the seat under
    # her, named as an object in front of nothing, exactly as the bicycle is.
    #
    # `(sweat:1.2)` is the lowest weight in the block for `winded`'s reason:
    # 763k and strong, but drawn as SHEEN, which is the axis this recipe keeps
    # having to take gloss off. First tag to cut if the skin comes back shiny.
    #
    # NOT SWEPT. Three things to look at first: a `bench` that arrives as a
    # park bench, the camera -- no framing tag is spent here, and `chair`
    # records a square not anchoring one on its own -- and the eyes, since
    # FACE's `looking at viewer` is spliced out in `positive` for `nape`'s
    # reason and it is the one instruction that would undo the pose.
    "doze": (
        "(solo:1.5), (sitting:1.5), (sleeping:1.5), (sleeping upright:1.45), "
        "(closed eyes:1.45), (head tilt:1.4), (zzz:1.35), "
        "(bench:1.3), (arms at sides:1.3), "
        "(towel around neck:1.4), (messy hair:1.3), (sweat:1.2), "
        "(full body:1.45)"
    ),
    # ロードバイク. Written against the vessel grammar `sip` and `straw` worked
    # out, because a bicycle is the same problem one size up: an object that has
    # to be BOTH in the picture and under her, and whose type has to be pinned.
    #
    #   `(bicycle:1.4)` puts one in frame. On its own that is all it does --
    #   `holding cup` put the cup in her hand and left the hand down, and the
    #   sweep that trusted an object tag to imply the action found the can at
    #   her feet in four of four.
    #   `(riding bicycle:1.5)` is this pose's `drinking`: the tag that says
    #   where she is in relation to it. It is the load-bearing one and it is
    #   weighted above the noun for that reason.
    #   `(road bicycle:1.45)` is the second naming. `straw` dropped its second
    #   noun because a paper cup is what the model reaches for unaided; a ROAD
    #   bike is not -- the default bicycle is a city bike with flat bars. So
    #   this is the case `sip` paid for and `straw` did not, and the cost is
    #   the same one: a second vessel on some seeds. Two bicycles is the first
    #   thing to look for in the sweep.
    #
    # Nothing here asks for a road, and that is deliberate: SURFACE is a flat
    # grey backdrop and a scene fights that contract. She will be riding in
    # front of nothing, like everything else in this file.
    "ride": (
        "(solo:1.5), (riding bicycle:1.5), (road bicycle:1.45), (bicycle:1.4), "
        "(from side:1.4), (leaning forward:1.3), (full body:1.45)"
    ),
    # 暑くて床でジタバタ, straight down. `flop` is this body position at rest and
    # `prone` is the from-above camera that works; what is new here is motion
    # and a reason.
    #
    # `(flailing:1.4)` is borrowed from `fall`, which is the only other pose in
    # this file whose subject is a body not in control of itself, and it is
    # paired with `(motion lines:1.3)` for the same reason it is there: motion
    # lines are a comic convention, drawn as separate marks BY DEFINITION, and
    # this is the tag that says the limbs are moving rather than posed. Note for
    # a later sweep -- `headcount.py` counts marks, and its own docstring says
    # a pose carrying motion lines could not be counted by the tool it replaced.
    #
    # THE HEAT IS NOT ON HER FACE ANY MORE, and that is a correction rather
    # than a drift. The first sweep had `(sweat:1.35)` and `(full body:1.45)`
    # and read as a girl lying down being warm; the reference the user then
    # posted is a TANTRUM -- both fists and both knees in the air, eyes clamped,
    # mouth wide -- where the heat is carried by how hard she is thrashing.
    # Both slots were spent on that: `legs up` for the knees, `closed eyes` for
    # the clamp. `full body` goes free (a landscape canvas with a lying figure
    # frames her anyway; `sip` measured the same slot spare at its square) and
    # the sweat goes knowingly.
    #
    # `(closed eyes:1.4)` over `(>_<:1.4)`, swept head to head. `dizzy` proved
    # this model reads face symbols as tags -- `@_@` is real to it -- so the
    # symbol was the favourite and it lost. b2370dcc is the picked render.
    #
    # Note what closing her eyes costs: FACE's `(tareme:1.3), (large eyes:1.3),
    # (large iris:1.25)` are all instructions about eyes that are now shut.
    #
    # This is also the one framing in the file where the flat grey backdrop is
    # not a compromise. Shot straight down, SURFACE's `(simple background:1.3)`
    # IS the floor she is lying on, so the pose gets a real setting for free
    # where every other pose is standing in front of nothing.
    # EIGHTEEN TAGS, the longest block in this file, and it got there one
    # reference image at a time. The order it was built in is the order the
    # asks arrived, and each step is a measured arm rather than a guess:
    #
    #   closed eyes over `(>_<:1.4)`      b2370dcc, swept head to head. `dizzy`
    #                                     proved face symbols are real tags to
    #                                     this model, so the symbol was the
    #                                     favourite and it lost.
    #   EVERY LIMB TAG IS SINGULAR        the reference is asymmetric in all
    #                                     three: one fist and one open hand,
    #                                     one knee high and one low, one arm up
    #                                     and one down. This file already
    #                                     carries both forms -- `kick` has
    #                                     `knee up`, `situp` has `knees up`;
    #                                     `peace` has `outstretched arm`, `flop`
    #                                     has `outstretched arms` -- so naming
    #                                     one of a pair is an established lever
    #                                     here, not a hopeful one.
    #   kicking AND foreshortening        the limb argument and the camera
    #                                     argument. Shot from above, a leg
    #                                     thrown up is a leg thrown AT the
    #                                     viewer; `kick` uses this tag at 1.3
    #                                     for the same geometry.
    #   screaming + furrowed brow         `fall` names its emotion beside its
    #                                     open mouth rather than trusting the
    #                                     mouth; this does the same.
    #
    # `thin eyebrows` is deliberately still in FACE. `(furrowed brow:1.35)` is
    # about the SHAPE the brows make and not their weight, and pulling both at
    # once is how a face gets changed without anyone knowing which lever did it.
    #
    # IT WAS EIGHTEEN TAGS AND IT IS FIFTEEN, because the subject was misread
    # and the two reference images are what misread it. They are tantrum
    # illustrations; 「暑いので大暴れはしていないです。微動」 is the actual pose.
    # `(motion lines:1.45)` and `(kicking:1.4)` came out and `flailing` went
    # 1.55 -> 1.25 on that -- the whole violence axis, turned down.
    #
    # `(foreshortening:1.3)` came out for a different and more interesting
    # reason. It was added while the leg was being SNAPPED up, to draw a limb
    # thrown at the camera, and it was correct then. When the knee eased to
    # 1.35 nothing removed it, so a camera distortion was being applied to a
    # leg that is barely raised, and 「足の長さが不自然」 was the result. Swept
    # against a negative `(long legs:1.4)` and against easing BODY, and taking
    # the tag out is what fixed it. **A camera tag left behind after the pose
    # it was for has gone is worse than no camera tag at all** -- this file has
    # plenty of notes about tags that are wrong and this is its first about a
    # tag whose supporting setting was removed from under it.
    #
    # The length is a real risk and is not the same risk as the tag count. There
    # is no ceiling -- `kick` runs 13 and is fine -- but a longer block dilutes
    # every tag in it. If the face or the arms go weak later, suspect the length
    # before suspecting whatever was added last.
    "swelter": (
        "(solo:1.5), (lying:1.45), (on back:1.5), (from above:1.45), "
        # `(flailing:1.25)` was here and is gone with the effect lines. It is
        # the one word left in the block that a speed line is the standard
        # drawing of, and the negative guard alone did not finish the job.
        # What it cost is recorded rather than guessed at: on 555666777 the
        # backdrop stopped being flat at all -- 0.1% floods, against 29.3% with
        # the tag -- so this tag was holding the plain background up on at
        # least one seed, and `deliver.py` cannot repaint what it cannot flood.
        # The pose survives it because `knee up`, `spread legs` and `arm up`
        # are the shape, and 微動 is the ask.
        "(knee up:1.35), (spread legs:1.35), (arm up:1.4), "
        "(clenched hand:1.35), (closed eyes:1.4), (open mouth:1.35), "
        "(screaming:1.4), (furrowed brow:1.35), (midriff:1.35), (navel:1.3)"
    ),
    # The がおー with the body cropped off it: head and shoulders, both paws up
    # beside her face. `portrait`'s framing exactly, because that framing is
    # settled and this pose has no argument with it.
    #
    # In HEAD_FRAMINGS, so it drops the legwear, most of BODY and the thin-line
    # block from the positive and the legwear ban from the negative. That is not
    # a decision this pose gets to make differently: naming a garment that is out
    # of frame is what invites it back into the frame.
    "snarl": (
        "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), (close-up:1.2), "
        "(face focus:1.3), " + GAO_HANDS + ", (hands up:1.4), " + GAO_FACE
    ),
    # テヘペロ minus the ペロ, with a peace sign at the cheek.
    #
    # **`;p` was here and it worked exactly as advertised, which is why it had
    # to go.** Danbooru's emoticon tags name a complete expression -- that one
    # is a wink WITH the tongue out -- and it drew both halves from one token
    # on the first sweep, beating an arm that spelled the same face out. Then
    # 「舌出し止めて」, and an emoticon whose whole content is a wink and a
    # tongue has nothing left to be once the tongue goes. So the face is spelled
    # out after all: `(one eye closed:1.45), (wink:1.35), (smile:1.35)`, shut,
    # which is the sly version rather than the cheerful one. `(open mouth:1.25),
    # (smile:1.3)` is the cheerful arm and `(smile:1.35)` alone dropped is the
    # flat one; both were rendered on this seed and both work.
    #
    # The pose leaves `open_mouthed` with the tongue. It was only ever in that
    # list to let a tongue through FACE's `closed mouth`.
    #
    # `(v:1.45)` against `(hand on own cheek:1.05)`, and the weights are the
    # whole finding. At 1.45/1.4 the cheek tag won outright and drew an open
    # palm with splayed fingers -- `hand on own cheek` DESCRIBES an open palm,
    # so the two tags are naming different handshapes for the same hand and
    # whichever is heavier gets it. Inverted, the V is the shape and the cheek
    # is only the place.
    #
    # **The exact weights past that inversion do not matter and forty renders
    # say so.** 1.6/1.15 and 1.45/1.05 were run against the same nine seeds:
    # the same two draws are good in both and the same seven are bad in both.
    # Two other levers died on the way -- `(clenched hand:1.2)` fixes the
    # knuckle count by removing the V, and dropping the cheek tag draws the
    # best hands in the sweep and puts them on her chest. **At this point the
    # hand is the seed**, and the guard below is what makes a good seed hold.
    #
    # `(upper body:1.35)` where the other head framings have `(close-up:1.2)`.
    # This is the one crop in the file with a hand ON the face rather than
    # beside it, and at `close-up` the top of her head was outside the frame.
    # The backdrop share is the other half of it: 30-41% here against 7-30% at
    # the tighter crop, which is what the delivery step needs to flood.
    "tehe": (
        "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), "
        "(upper body:1.35), (face focus:1.3), (one eye closed:1.45), "
        "(wink:1.35), (smile:1.35), (v:1.45), (hand on own cheek:1.05)"
    ),
    # 疲れ顔で歯磨き、チェストアップ. `tehe`'s framing verbatim -- it is the one
    # crop in the file built for a hand at the face, and its `(upper body:1.35)`
    # is already the chest-up that was asked for.
    #
    # `brushing teeth` + `toothbrush` is `sip`'s two-slot rule: the action tag
    # is what puts the object at the mouth (`drinking` held the cup up after
    # `holding cup` alone dropped it to her feet), and the object tag is what
    # decides which object it is. The action carries the pose, so it takes the
    # heavier weight.
    #
    # The exhaustion is `allnighter`'s pair at `allnighter`'s weights --
    # (eyebags:1.4) is the fixed price of tired in this file, and the droop is
    # the raised 1.35 form of `half-closed eyes`. No expression tag beside
    # them, for `allnighter`'s reason: tiredness is the absence of one, and the
    # last time a slot was spent naming it anyway the face came back angry.
    "brush": (
        "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), "
        "(upper body:1.35), (face focus:1.3), (brushing teeth:1.45), "
        "(toothbrush:1.3), (eyebags:1.4), (half-closed eyes:1.35)"
    ),
    # 自分の髪でヒゲを作って遊ぶ（「ヒゲ〜〜〜」）. `tehe`'s framing verbatim,
    # for `brush`'s reason: it is the one crop built for a hand at the face.
    #
    # `sip`/`brush`'s two-slot rule: `holding own hair` is the action that
    # brings the hair to the face and takes the heavier weight; `fake mustache`
    # is the object slot that says what the held hair is posing as. The hope is
    # the two read together as hair-held-under-nose rather than a separate
    # costume prop -- that is the thing the sweep judges.
    # `playing with own hair` beside them is the mood: this is play, not a
    # hairstyle.
    # 「ヒゲのパーツを書くのではなくて、毛先を口元に持ってきてヒゲを表現する」.
    # `fake mustache` at any weight names the drawn part, not the gesture --
    # arms a-c all reached for the part -- so the mustache words are out of the
    # positive entirely and banned by name in the negative instead.
    #
    # What is left is pure composition, on the two-slot rule: `holding own
    # hair` is the action that fills the hand, and `smelling hair` is the
    # placement -- the sniffing gesture is the one vocabulary that pins held
    # TIPS to the NOSE (arm p, 74gn3v: 「毛先っていう意味ではこれが正しい」).
    # The mouth pair that preceded it (`covering own mouth` + `hair in own
    # mouth`, arms h) sent everything to the mouth instead and lost once 毛先
    # was the ask. What `smelling hair` drags in -- narrowed, smug eyes -- is
    # named and banned in `negative()`, and the picked render (kts2c3, seed
    # 3409564303) was drawn through that ban.
    "hige": (
        "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), "
        "(upper body:1.35), (face focus:1.3), (holding own hair:1.5), "
        "(smelling hair:1.45), (playing with own hair:1.3), (smile:1.2)"
    ),
}


# The extra-limb trio: `extra limbs` unweighted in NEGATIVE stopped neither a
# third arm at 2048 nor a fourth leg on a print; the weighted names are what
# worked (`hoops`, then `winded`).
_LIMB_TRIO = "(extra arms:1.5), (extra legs:1.5), (extra limbs:1.5), "

# The dress's straps: a halter that crosses at the chest and ties behind the
# neck, official design. Globally the tag costs the coat its shoulders, so it
# is per-pose; one tag, not `nape`'s two -- the three-tag form pulls the
# camera in (`boss`), and the backdrop intruders it invites are repainted at
# delivery anyway (recolor_bg.py).
_CRISS_CROSS = Edit("replace", "(drawstring:1.4), ",
                    "(drawstring:1.4), (criss-cross halter:1.45), ",
                    gate="dressed")

POSE_RECORDS = {
    # The leg is the block's own gradient, like every other pose. This record
    # briefly carried a grad-removal edit (the 2026-08-28 contrast verdict,
    # jcjwb6/64d41q) -- reversed the same day when the stand/lounge delivery
    # put both legs side by side and the user called the gradient leg the
    # correct one (「立ちの方が正」). One costume, every pose.
    "lounge": Pose(POSES["lounge"], (1024, 1536), own_eyes=True),
    # Head framings sit in a square: (portrait:1.5) alone lost to a 1024x1280
    # canvas and drew down to the thighs.
    "portrait": Pose(POSES["portrait"], (1024, 1024), own_eyes=True, framing="head",
                     # 「肩紐がないね」-- in frame here and never drawn until the
                     # splice arrived. e4ff4f8a, picked with the cardigan up.
                     character_edits=(_CRISS_CROSS,)),
    "allnighter": Pose(POSES["allnighter"], (1024, 1024), own_eyes=True, framing="head",
                       open_mouth=True),
    "dizzy": Pose(POSES["dizzy"], (1024, 1024), own_eyes=True, framing="head",
                  open_mouth=True),
    # Seated full bodies are 1024x1536; this one wears the legwear, so it is
    # NOT a head framing despite the name.
    "allnighter_full": Pose(POSES["allnighter_full"], (1024, 1536), own_eyes=True,
                            open_mouth=True),
    "peace": Pose(POSES["peace"], (1024, 1536), own_eyes=True),
    "chair": Pose(POSES["chair"], (1024, 1024)),
    "boss": Pose(
        POSES["boss"], (1024, 1024), own_eyes=True,
        # Grown up by ONE substitution: the rest of BODY is already adult
        # proportion and was only held down by `petite`. Dropping the eye tag
        # instead drew a second empty chair; `(tsurime:1.1)` is the middle if
        # a trace is ever wanted.
        body_edits=(
            Edit("replace", "(petite:1.2)", "(mature female:1.35)"),
            # `mature female` brings a chest the negative could not finish
            # alone (1.25 -> 1.5 -> 1.75 all left too much); naming
            # `small breasts` positively lands it in one step.
            Edit("replace", "(narrow waist:1.25)",
                 "(narrow waist:1.25), (small breasts:1.35)"),
        ),
        character_edits=(
            # `mature female` recruits `oversized shirt` into a button-front
            # shirt dress; dropping the competing garment restores the dress
            # while keeping the proportions. `sleeves past wrists` stays.
            Edit("remove", "(oversized shirt:1.3), ", gate="dressed"),
            # The approved render's coat is off the shoulders -- a deliberate
            # exception to the docstring's hood rule. Drop this to get the
            # hood and ears back.
            Edit("replace", "open cardigan",
                 "open cardigan, (off shoulder:1.3)", gate="dressed"),
            _CRISS_CROSS,
        ),
        legwear_edits=(
            # The rib is what her legwear is, and the block draws it only on
            # some seeds unaided. ADDED, not substituted: substituting from
            # the grey side removed the tights on every seed, from the pale
            # side cost the colour. If a later change starts losing the
            # legwear, this extra tag is the first suspect.
            Edit("replace", "(opaque pantyhose:1.4)",
                 "(opaque pantyhose:1.4), (ribbed legwear:1.35)",
                 gate="dressed"),
        ),
        negative_base=(
            # The guard was already in NEGATIVE at 1.25 and was being outvoted;
            # raising it adds no tag. Guard-stacking has cost this recipe its
            # palette twice and (here) a rabbit silhouette on the chair back.
            Edit("replace", "(large breasts:1.25)", "(large breasts:1.5)"),
            # Her dress has no buttons; they arrive from the cardigan being
            # read as a shirt. One guard is the whole fix -- two and four both
            # bought the backdrop intruder.
            Edit("prepend", new="(buttons:1.4), "),
        )),
    "yawn": Pose(POSES["yawn"], (1024, 1536), own_eyes=True, open_mouth=True),
    "fall": Pose(POSES["fall"], (1024, 1536), own_eyes=True, open_mouth=True),
    "coy": Pose(POSES["coy"], (1024, 1536)),
    "lap": Pose(
        POSES["lap"], (1024, 1536), own_eyes=True,
        negative_base=(
            # A head in her lap looks up at her, so the low-angle guard fights
            # the shot. `(upskirt:1.4)`/panties stay -- those are about what
            # the camera sees, not where it sits.
            Edit("remove", "(from below:1.35), "),
            # The pose is about someone who is not in frame, so the second
            # person has to be named to be kept out.
            Edit("append", new=", (2girls:1.6), (multiple girls:1.6), "
                               "(duplicate:1.55), (another person:1.5)"),
        )),
    "invite": Pose(POSES["invite"], (1024, 1536), own_eyes=True),
    "hunt": Pose(POSES["hunt"], (1024, 1536)),
    "crouch": Pose(POSES["crouch"], (1024, 1536), own_eyes=True),
    # A side-on squat is about as wide as it is tall; at 1024x1536 she drew
    # small in a tall empty frame.
    "sip": Pose(POSES["sip"], (1024, 1024), own_eyes=True),
    "nape": Pose(
        POSES["nape"], (1024, 1024),
        # Turned away from the camera, `looking at viewer` has no referent --
        # it either argues with the pose or spins her back around.
        face_edits=(Edit("remove", ", looking at viewer"),),
        character_edits=(
            # The bow at the nape, which only this pose is looking at. The
            # pair is documented as costing every other pose its coat.
            Edit("replace", "(drawstring:1.4), ",
                 "(drawstring:1.4), (halterneck:1.45), (black straps:1.35), ",
                 gate="dressed"),
        ),
        # The coat pulled off the shoulders is what uncovers the nape. It
        # rides with the hood rather than the pose block: that block is at
        # eight tags and a ninth is where the hair clips broke last time.
        hood_suffix=", (off shoulder:1.25)",
        negative_base=(
            # `from behind` invites a turnaround sheet; and `nape of neck`
            # reads as skin to uncover -- it took the coat off in three of
            # four. What this must NOT forbid is the coat slipping:
            # (off-shoulder)/(bare shoulders) here banned the look itself.
            Edit("prepend", new=(
                "(character sheet:1.4), (multiple views:1.4), reference sheet, "
                "turnaround, (undressing:1.4), topless, (bare back:1.3), ")),
        )),
    # A body on the floor earns the landscape canvas: 1024x1024 cropped her
    # and doubled the relative stroke, 1024x1536 drew the rear-forward
    # composition from the canvas alone. Same 1.57M pixels, on its side.
    "prone": Pose(
        POSES["prone"], (1536, 1024), own_eyes=True,
        # 「めちゃ下半身太ってしまった…」: straight at the rear, foreshortened,
        # BODY's hip/thigh tags read as bulk. EASED, not deleted -- pushing
        # further (0.6/0.6 + petite/waist raises) drew the rabbit intruder.
        body_edits=(
            Edit("replace", "(wide hips:1.3)", "(wide hips:1.0)"),
            Edit("replace", "(thick thighs:1.35)", "(thick thighs:1.05)"),
        )),
    "flop": Pose(
        POSES["flop"], (1536, 1024), own_eyes=True,
        # 「ちょっと胴体が長い」, `stand`'s axis and `stand`'s lever. Bracketed
        # from both sides: no tag drew a long torso, 1.45 drew 「脚が長すぎる」.
        # The negative route does nothing on this axis -- ask for the leg.
        body_edits=(Edit("replace", "(pale skin:1.25)",
                         "(long legs:1.40), (pale skin:1.25)"),),
        # 「目も修正してほしい」 (4b7d646c): `smug` narrows the lids on its own,
        # and a 250px face is where eyes stop matching. Pass 2 only.
        hires_negative="(half-closed eyes:1.4), (closed eyes:1.4), "),
    "kick": Pose(
        POSES["kick"], (1024, 1536), own_eyes=True, open_mouth=True,
        legwear_edits=(
            # 「つま先のタイツのグラデーションを白ではなく紫に」: only this
            # framing puts the gradient's light end at the camera. Full colour
            # at reduced weight won over the pale name at higher weight.
            Edit("replace", "(pale purple pantyhose:1.35)",
                 "(purple pantyhose:1.15)", gate="dressed"),
        ),
        negative_edits=(
            # All five as the picked render (0db8e020) carried them. The line
            # trio stopped nothing measurably -- leaving the doodle seed did --
            # but the pick was drawn through them. The dress pair is
            # 「肩紐、襟無し、ボタンなし」.
            Edit("prepend", new=(
                "(speed lines:1.45), (motion lines:1.4), (emphasis lines:1.4), "
                "(buttons:1.35), (collared dress:1.35), "),
                stage=S_POSE_GUARDS),
        ),
        # ONE toe guard: she is in opaque tights, so a smooth toe box is the
        # picture -- five countable toes was the error. The second toe guard
        # flattened every accent (brightest tenth 89 -> 52); one puts it back
        # (105) and keeps the toe box. `closed eyes` banned while the positive
        # asks half-closed: 10915a12 split the pair, forbid shut / ask half.
        hires_negative="(toes:1.55), (closed eyes:1.4), ",
        settled_seed=737373737),
    "situp": Pose(
        POSES["situp"], (1536, 1024), open_mouth=True,
        negative_edits=(
            # The exercise brings its own wardrobe; keep the gym out without
            # arguing with it. Released for the shod costumes -- `sporty` IS a
            # gym kit -- but a tee and dolphin shorts is loungewear, so
            # `roomwear` keeps the guard. `(yoga mat:1.3)` is deliberately
            # gone: a mat is FLOOR, and banning it helped 腹筋要素 to zero.
            Edit("append", new=", (sportswear:1.45), (gym uniform:1.4)",
                 gate="default_or_roomwear", stage=S_POSE_SCENE),
            # 猫背's opposite, the posture this model volunteers for a girl on
            # her back. `stand` pays a tag to GET this arch; here it is the
            # whole defect.
            Edit("append", new=", (arched back:1.4), (bridge (pose):1.3)",
                 stage=S_POSE_SCENE),
        )),
    # 832 wide: width beside her is room for someone else to stand. At 1024
    # three of six seeds drew a second figure; at 832, one.
    "stand": Pose(
        POSES["stand"], (832, 1664), own_eyes=True,
        face_edits=(
            # The 2026-08-24 lash pair melts THIS pose into foil noise -- full
            # prompt, every seed, weight-independent; `portrait` and `brush`
            # carry the same pair and are fine. The negative's
            # `(long eyelashes:1.35)` was isolated and acquitted.
            Edit("replace", "(eyelashes:1.3), (thick eyelashes:1.35)",
                 "eyelashes"),
        ),
        # 「脚の長さに比重をかけてほしい」. ADDED beside `petite`, not
        # substituted into it (measured within noise and not picked). The
        # negative route moved nothing on this axis, twice.
        body_edits=(Edit("replace", "(pale skin:1.25)",
                         "(long legs:1.35), (pale skin:1.25)"),),
        # 355f91cf: straps are the design; the backdrop cost is repaid by
        # recolor_bg.py at delivery.
        character_edits=(_CRISS_CROSS,),
        pose_block_edits=(
            # The one pose that names footwear, and it names the settled
            # costume's black high tops; a shod costume brings its own pair,
            # and both in one prompt is asking for two pairs of shoes.
            Edit("remove", "(black footwear:1.35), (high tops:1.35), ",
                 gate="shod"),
        ),
        negative_base=(
            # `boss`'s button guard, in `boss`'s slot.
            Edit("prepend", new="(buttons:1.4), "),
            # 「靴に柄はいらない」: decal, logo, colour -- three separate
            # defects, so three guards, measured together on 1886970040. The
            # ear-like high collar is WANTED and survives all three.
            Edit("append", new=", (butterfly:1.5), (logo:1.4), (print:1.35)"),
        ),
        negative_edits=(
            # The pale sole: describing `(black sole:1.35)` positively left a
            # white midsole and added a red flash; guarding the colours works.
            # `sporty`'s shoes ARE white, `roomwear`'s feet are bare -- gated.
            Edit("append", new=", (white footwear:1.45), (red footwear:1.4)",
                 gate="default_or_roomwear", stage=S_POSE_SHOES),
        )),
    "hype": Pose(POSES["hype"], (832, 1664), own_eyes=True, open_mouth=True),
    "roar": Pose(POSES["roar"], (832, 1664), own_eyes=True, open_mouth=True),
    # A squat fills its own width; the 832 argument is about width BESIDE her.
    "pounce": Pose(POSES["pounce"], (1024, 1024), own_eyes=True, open_mouth=True),
    "loom": Pose(POSES["loom"], (832, 1664), own_eyes=True, open_mouth=True),
    "snarl": Pose(POSES["snarl"], (1024, 1024), own_eyes=True, framing="head",
                  open_mouth=True),
    "straw": Pose(POSES["straw"], (832, 1664),
                  # 174ce1dc's finish, carried whole -- see PAINT_FINISH in
                  # `recipe.py` for why it is one decision, not two.
                  paint_finish=True, hires_negative=HIRES_NEGATIVE_PAINT),
    "snack": Pose(POSES["snack"], (1024, 1536), open_mouth=True,
                  paint_finish=True, hires_negative=HIRES_NEGATIVE_PAINT),
    "hoops": Pose(
        POSES["hoops"], (832, 1664), own_eyes=True, open_mouth=True,
        negative_edits=(
            # Two hands closed around an object is `tehe`'s accident class,
            # and that pose's forty-render finding was about WHERE the guard
            # goes: both passes from the first sweep, or the 1024 sweep judges
            # a prompt the print does not use. Prepended -- token order.
            Edit("prepend", new=HAND_BAN, stage=S_POSE_GUARDS),
            Edit("prepend", new=_LIMB_TRIO, stage=S_POSE_LIMBS),
        ),
        hires_negative=HAND_BAN),
    # Square: legs forward and arms back put the long axis on the DIAGONAL,
    # so neither portrait nor landscape frames fit. The reference is square.
    "winded": Pose(
        POSES["winded"], (1152, 1152), own_eyes=True, open_mouth=True,
        face_edits=(
            # あ゛〜〜〜 makes the mouth the largest thing in the face
            # (`swelter`'s reason), and shot from the side with her head back
            # `looking at viewer` has no referent. FACE's eye tags STAY --
            # instructions about shut eyes, a cost noted and not paid.
            Edit("remove", "small mouth, "),
            Edit("remove", ", looking at viewer"),
        ),
        negative_edits=(
            # `knees_up` deleted is how the legs get straight: nothing in the
            # positive says "extended" in a count that moves a picture, so the
            # lever is subtraction. Applied after the limb trio so it lands in
            # FRONT of it -- the order the picked render was drawn in.
            Edit("prepend", new="(knees up:1.5), ", stage=S_POSE_LATE),
            # Two arms angled back behind the torso is the arrangement that
            # invites a third.
            Edit("prepend", new=_LIMB_TRIO, stage=S_POSE_LATE),
        ),
        # Measured, not assumed: this pose's FIRST pass has no hand guard --
        # the five names are gated to `tehe`/`hoops` there. Both hands carry
        # her weight and pass 2 redraws them, so they are named here, once.
        hires_negative=HAND_BAN,
        # 「手書き風のファイナライズ」: THIN off (pass 2 only) plus the marker
        # pair, appended at the very END -- HIRES_POSITIVE splices mid-prompt
        # instead, and token order changes the encoding; separate mechanisms
        # on purpose. `sketch` is NOT here: it means unfinished, which is the
        # state HIRES_NEGATIVE_PAINT exists to remove.
        hires_finish=", (traditional media:1.4), (marker (medium):1.35)",
        # --hires is a longest-side number, not a scale: 1416 is this pose's
        # 1.23x, the ratio every portrait pose prints at. The 1152 (1.0x)
        # conclusion before it was measured on the sweep's most saturated
        # seed and did not survive being retaken on the settled one. 0.50
        # because the face is carried by a symbol and 0.60 dissolves it.
        hires_print=(1416, 0.50),
        # The seed holds the colour (2.4x saturation spread across five seeds
        # on an identical prompt) and decides whether `feet out of frame`
        # clears the frame at all.
        settled_seed=737373737),
    # The only square doze earns: asleep she is compact, and the empty half
    # of a wider canvas is where a second figure gets drawn.
    "doze": Pose(
        POSES["doze"], (1152, 1152), own_eyes=True,
        # Eyes shut: `looking at viewer` has no referent and either argues or
        # opens them. `small mouth` STAYS -- asleep it is the smallest thing
        # in the face, the expression rather than something in the way.
        face_edits=(Edit("remove", ", looking at viewer"),),
        surface_edits=(
            # The one SCENE in the file, and a measured break of the flat-
            # backdrop contract: swept both ways at 1152 on four seeds, and
            # the picked render (b393e171) is from this arm. Only the
            # background pair is replaced -- flat color, white outline and
            # the shading pair stay, which is why the carriage arrives as
            # pale line rather than as a photograph. Costs recolor_bg.py and
            # headcount.py their jobs on this pose.
            Edit("replace", "(simple background:1.3), (grey background:1.2)",
                 SCENE_TRAIN),
        ),
        negative_edits=(
            # A carriage is a room whose subject is other passengers, and
            # (solo:1.5) has never had to hold against a background that
            # implies a crowd. In front -- the order b393e171 was drawn in.
            Edit("prepend", new=CROWD_BAN, stage=S_CROWD),
        ),
        settled_seed=737373737),
    # Wide for an OBJECT, not a body: a road bike side-on is longer than she
    # is tall. Spends the second-figure protection 832 buys, knowingly.
    "ride": Pose(POSES["ride"], (1536, 1024)),
    "swelter": Pose(
        POSES["swelter"], (1536, 1024), own_eyes=True, open_mouth=True,
        face_edits=(
            # The reference's mouth is the biggest thing in the face, and the
            # eyes are clamped shut -- FACE was settled on a composed girl and
            # these two tags are the opposite of a tantrum.
            Edit("remove", "small mouth, "),
            Edit("remove", ", looking at viewer"),
        ),
        # `prone`'s argument pointed at length: the from-above camera made the
        # legs read long, and `petite` answers proportion as a whole. Swept
        # against removing the camera tag alone -- both were needed (d35a67f8).
        body_edits=(Edit("replace", "(petite:1.2)", "(petite:1.4)"),),
        character_edits=(
            # 「部屋でジタバタしているので」: white high tops are outdoor shoes.
            # A SUBSTITUTION in the footwear slot, not a removal -- `no shoes`
            # means a foot still wearing its tights; `barefoot` would strip
            # them. Gated on the costumes that have shoes; a `default` swelter
            # has never been rendered and gets no invented slot.
            Edit("replace",
                 "(white footwear:1.4), (sneakers:1.45), (high tops:1.3)",
                 "(no shoes:1.35)", gate="shod"),
        ),
        negative_edits=(
            # 「シャツも少しお腹が見えてしまってる感じで」, and the provenance
            # tail was the thing in the way (its own note prices the release
            # at zero). `(cropped jacket:1.45)` stays -- different garment,
            # and the garment is a contract.
            Edit("remove", ", (midriff:1.35), (navel:1.3)",
                 stage=S_POSE_GUARDS),
            # 「効果線は削除して」. Nothing in the positive asks for them --
            # `flailing`/`screaming` supply the convention on their own. Speed
            # lines are a drawn object with a name, which is what a guard has
            # always been able to take out. Three names because the model
            # does not treat them as one.
            Edit("append", new=", (motion lines:1.5), (speed lines:1.5), "
                               "(emphasis lines:1.45)",
                 stage=S_POSE_GUARDS),
        ),
        # 「右腕が変な色になってる」: the flat was never laid down, and 0.60 has
        # nothing to resolve until the state is named. Four names because
        # sketch/lineart are the medium, unfinished the state, monochrome
        # what an unpainted region is. Pass 2 only -- the picked composition
        # is not re-rolled (174ce1dc).
        hires_negative=HIRES_NEGATIVE_PAINT),
    "tehe": Pose(
        POSES["tehe"], (1024, 1024), own_eyes=True, framing="head",
        negative_edits=(
            # The emoticon that drew the tongue is gone; a wink and a small
            # mouth are what the model draws one FROM. A tongue is a drawn
            # object with a name.
            Edit("prepend", new="(tongue:1.5), (tongue out:1.5), ",
                 stage=S_POSE_GUARDS),
            # The hand guard in PASS 1, hands in front of the tongue -- the
            # order the sweep ran in; the other order reproduced every node
            # but this one. Forty renders judged at 1024 were judging a
            # prompt the print did not use while this lived in pass 2 only.
            Edit("prepend", new=HAND_BAN, stage=S_POSE_GUARDS),
        ),
        # ...and the pass-2 copy: 0.70 redraws the hand, and a guard that
        # only ran on the pass being redrawn is not a guard.
        hires_negative=HAND_BAN),
    "brush": Pose(POSES["brush"], (1024, 1024), own_eyes=True, framing="head",
                  open_mouth=True,
                  # 4e56f616, from a four-seed sweep.
                  settled_seed=737373737),
    "hige": Pose(
        POSES["hige"], (1024, 1024), own_eyes=True, framing="head",
        tail_edits=(
            # `(frills:1.25)` names a dress collar that is out of frame here,
            # and the tag was landing on the cardigan instead. Gated on the
            # costume whose CHARACTER carries it.
            Edit("remove", "(frills:1.25), ", gate="dressed"),
            # kts2c3's three end-appends, AFTER everything -- the token order
            # it was drawn in; a mid-prompt insertion re-rolls every token
            # after it.
            Edit("append",
                 new=", (covered mouth:1.35), (tareme:1.5), (large eyes:1.4)"),
        ),
        negative_edits=(
            # Two prices of the pose's own tags: the lace trio removes what
            # the model draws out of habit once the `(frills:1.25)` ask is
            # gone (dm5e2v), and the eye trio returns FACE's tareme --
            # `smelling hair` narrows the eyes into a smirk (74gn3v). Then
            # `tehe`'s hand guard (a hand closed at the face), then the
            # mustache words, moved here from the positive: asked for, they
            # drew the part instead of the gesture. The hair at the lip has
            # no name in this prompt, so the ban cannot delete it. All in
            # kts2c3's order.
            Edit("prepend", new=(
                "(lace trim:1.5), (frilled jacket:1.45), (lace:1.4), "
                "(half-closed eyes:1.5), (narrowed eyes:1.5), (smug:1.4), "
                + HAND_BAN + "(mustache:1.5), (fake mustache:1.5), "
                "(facial hair:1.4), (beard:1.4), "),
                stage=S_POSE_GUARDS),
        ),
        # Pass 2 redraws the hand at the face; the mustache ban rides along
        # because pass 2 could paint the part back in.
        hires_negative=HAND_BAN + "(mustache:1.5), (fake mustache:1.5), ",
        # kts2c3, picked over six fresh seeds on the identical prompt (batch
        # wekzha) -- the seed is carrying something the words do not.
        settled_seed=3409564303),
}

assert set(POSE_RECORDS) == set(POSES), (
    set(POSE_RECORDS) ^ set(POSES))
