"""Every pose: its tag block, and its record.

`POSES` is the pose blocks, verbatim -- the strings the picked renders were
drawn with, byte for byte. `POSE_RECORDS` below is the rest of what a pose
owns, one record per pose: canvas, framing, its declared departures from the
shared blocks, its pass-2 contract, its settled seed. Adding a pose is one
`POSES` entry plus one record here; nothing else in the package needs to
know it exists.

Comments here keep only the constraints that guard the current blocks. The
observations that bought them -- sweeps, weights tried, seeds, render IDs --
are experiment records under experiments/yukari/<pose>.jsonl; the per-pose
reasoning lives in docs/poses/yukari/<pose>.md, and cross-pose lessons in
docs/render-notes.md.
"""

from __future__ import annotations

from .models import (
    Edit,
    Pose,
    S_CROWD,
    S_POSE_GUARDS,
    S_POSE_LATE,
    S_POSE_LIMBS,
    S_POSE_SCENE,
    S_POSE_SHOES,
)
from .prompt_style import (
    HAND_BAN,
    HANDDRAWN_FINISH,
    HIRES_NEGATIVE_PAINT,
)

# The one place a SCENE replaces the backdrop -- a deliberate, measured break
# of the flat-backdrop contract, on exactly one pose (`doze`). It replaces
# `(simple background:1.3), (grey background:1.2)` and nothing else: flat
# color, white outline and the shading pair stay, which is why the carriage
# arrives as pale line rather than as a photograph. `window` is the weakest
# weight on purpose -- it is there to put light behind her, not to name the
# place. Costs recolor_bg.py and headcount.py their jobs on this pose.
SCENE_TRAIN = "(train interior:1.4), (vehicle interior:1.3), (window:1.2)"

# A carriage implies a crowd that `(solo:1.5)` alone has never had to hold
# against. Goes in FRONT of NEGATIVE: token order changes the encoding, and
# this is the order the picked render was drawn in.
CROWD_BAN = "(multiple girls:1.5), (2girls:1.5), (crowd:1.4), (people:1.4), "

# The がおー as shared parts. Two fragments, not one: other tags sit between
# them in the order the family was rendered in, and token order changes the
# encoding -- assembled blocks stay byte-identical to their picked renders.
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
    # 徹夜明け, on `portrait`'s framing. (empty eyes:1.45) is the danbooru tag
    # for no-highlight dead eyes. NOT (closed eyes) -- it draws a second
    # figure here -- and no teeth and no second mouth/expression tag: bared
    # teeth read as anger whichever tag asks for them, and competing
    # descriptions of one feature argue with `open mouth`.
    "allnighter": (
        "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), (close-up:1.2), "
        "(face focus:1.3), (empty eyes:1.45), (eyebags:1.4), "
        "(half-closed eyes:1.35), (open mouth:1.35)"
    ),
    # 寝不足でぐるぐる目, `allnighter`'s crop. `@_@` is the danbooru tag
    # (`spiral eyes`/`dizzy eyes` are not); above 1.0 the spiral dominates the
    # face, so it is intentionally weak and `(dizzy:1.3)` carries the state.
    # The クマ took a second word -- `(tired:1.3)` beside `eyebags` -- where
    # more weight on `eyebags` did nothing.
    "dizzy": (
        "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), (close-up:1.2), "
        "(face focus:1.3), (@_@:1.0), (eyebags:1.55), (tired:1.3), "
        "(dizzy:1.3), (open mouth:1.35)"
    ),
    # `allnighter`'s face at full length, kneeling. The face block is carried
    # over unweighted-down on purpose: if the eyes stop reading at 1024x1536,
    # the fix is the second pass, not a heavier tag.
    "allnighter_full": (
        "(solo:1.5), (seiza:1.35), (empty eyes:1.45), (eyebags:1.4), "
        "(half-closed eyes:1.35), (open mouth:1.35), full body"
    ),
    # 寝転んで放心, on her back -- on her stomach the face is only legible
    # with the head lifted, and the lifting tags change the composition.
    # `(smug:1.15)` is composed where 1.4 gloats; `half-closed eyes` went with
    # the drop (the tag is present-or-absent, not gradual). NO dive or motion
    # tag: a falling tag over (lying) is two moments, and the model settles
    # two moments by drawing two bodies.
    "flop": (
        "(solo:1.5), (lying:1.45), (on back:1.5), (outstretched arms:1.3), "
        "(smug:1.15), full body"
    ),
    # Both hands making a V, one over the eye. All nine tags are load-bearing:
    # every trimmed variant broke something different (split socks, palette,
    # second figure, crop). `(solo:1.5)` at the head at exactly this weight is
    # what keeps the clones out -- measured, not stylistic.
    "peace": (
        "(solo:1.5), (yokozuwari:1.35), legs to the side, (double v:1.45), "
        "(v over eye:1.4), (outstretched arm:1.3), (smug:1.35), "
        "(half-closed eyes:1.3), full body"
    ),
    # Stretching and yawning, looked down on. Two measured constraints: the
    # block stays at eight tags after (solo:1.5) -- a ninth pushes the pale
    # thighhighs out -- and the eyes stay open, because (closed eyes:1.35)
    # draws a second figure. `closed mouth` comes out of FACE for this pose.
    "yawn": (
        "(solo:1.5), (stretching:1.4), (arms up:1.35), (yawning:1.4), "
        "(open mouth:1.35), (from above:1.4), sitting, looking at viewer, "
        "full body"
    ),
    # Going over spectacularly. ONE fall tag: tripping + falling + fallen down
    # are three moments, and the model gives each moment a body. `falling` is
    # the mid-air one; `motion lines` is a comic convention that survives flat
    # colour. `closed mouth` comes out of FACE for the shout.
    "fall": (
        "(solo:1.5), (falling:1.5), (flailing:1.35), (surprised:1.35), "
        # No (spread legs) here. Paired with (from above) that is exactly the
        # crotch-forward low-angle framing this project already threw a whole
        # composition away over.
        "(open mouth:1.3), (motion lines:1.25), (outstretched arms:1.3), "
        "(from above:1.25), full body"
    ),
    # Knowingly cute: head tilt, finger to cheek, wink, blush, floating heart
    # -- all real tags. Sits on yokozuwari because that seat is proven; an
    # untested gesture on an untested seat is how `fall` grew two of her.
    "coy": (
        "(solo:1.5), (yokozuwari:1.3), (head tilt:1.4), (finger to cheek:1.45), "
        "(one eye closed:1.35), (blush:1.35), (heart:1.25), (smile:1.25), "
        "full body"
    ),
    # Giving a lap pillow to the camera (pov). (head on lap) and (hand on
    # another's head) name a second person and draw her twice; (solo:1.5)
    # cannot outvote them. `lap pillow`, not `lap pillow invitation` -- she is
    # doing it, not offering. yokozuwari was PICKED, not deduced: seat swaps
    # measured the same, and the chosen render was drawn on this one. Do not
    # restore `seiza`.
    "lap": (
        "(solo:1.5), (lap pillow:1.35), (pov:1.45), sitting, (yokozuwari:1.25), "
        "(looking down:1.4), (smug:1.4), (hand up:1.25), cowboy shot"
    ),
    # Patting her own thigh, inviting -- one girl. NO lap-pillow tag: `lap
    # pillow invitation` names the relationship, so it names the other party,
    # and drew a second Yukari on every seed; deletion beats weight. Do NOT
    # add duplicate guards to the negative -- measured leaving the headcount
    # unchanged and wrecking the palette. yokozuwari, NOT seiza: seiza alone
    # broke the line, mottled the backdrop and doubled her.
    "invite": (
        "(solo:1.5), (yokozuwari:1.35), legs to the side, "
        "(hand on own thigh:1.45), (beckoning:1.35), (looking down:1.4), "
        "(smug:1.4), (come hither:1.25), full body"
    ),
    # On all fours, looking for the glasses she dropped. The dropped thing is
    # NAMED: an unnamed object renders as nothing at all. NOT SETTLED -- the
    # block is only stable on its one known-good seed.
    "hunt": (
        "(solo:1.5), (all fours:1.45), (searching:1.4), (hands on ground:1.35), "
        "(from behind:1.3), (glasses:1.3), (looking down:1.25), full body"
    ),
    # The same search, squatting, seen from behind and above. SETTLED: `--pose
    # crouch --seed 1117511306` reproduces the picked render pixel for pixel.
    # The drawing style is stable across seeds; the posture inside the pose is
    # not, and (searching:1.2) does no visible work at that weight.
    "crouch": (
        "(solo:1.5), (squatting:1.4), (from behind:1.45), (looking down:1.4), "
        # (smug:1.2) stays: swapping it for `expressionless` took her
        # character with it. (from above:1.2) keeps the hips out of centre
        # frame.
        "(picking up:1.3), (from above:1.2), (smug:1.2), full body"
    ),
    # Gaming chair, legs crossed, facing front. Measured constraints:
    # (crossed legs:1.2), NOT 1.35 -- higher draws the crossing and a third
    # leg, and bans do not help; the chair stays ONE noun -- a five-tag chair
    # block returned noise; bare `full body`, NOT the raised form -- weighted,
    # it collapses the two legwear layers into one stocking. Nine tags: a
    # longer block pushes the pale thighhighs out. NOT SETTLED -- the square
    # canvas does not anchor the framing on every seed.
    "chair": (
        "(solo:1.5), (sitting on chair:1.4), (crossed legs:1.2), (front view:1.35), "
        "facing viewer, (gaming chair:1.4), swivel chair, backrest, full body"
    ),
    # `chair` with the smirk on, and grown up. `(smug:1.15)`: composed where
    # 1.4 gloats -- move the weight, do not substitute the word. `half-closed
    # eyes` is out with it: the tag is present-or-absent, not gradual. Seed
    # matters more than the block (some seeds refuse to seat her; pick one
    # that does). To open the eyes on a settled picture, chain a late pass
    # with the eye pair in its negative; do NOT put that pair in the
    # first-pass negative -- it stacks with the buttons guard.
    "boss": (
        "(solo:1.5), (sitting on chair:1.4), (crossed legs:1.2), (smug:1.15), "
        "(gaming chair:1.4), swivel chair, backrest, full body"
    ),
    # Side-on full squat with a mug. Every slot is measured: `drinking` is
    # what lifts the cup (without it the cup fell to her feet); the mug needs
    # BOTH `coffee mug` and `holding cup` or the wrong vessel arrives;
    # `hunched over` curves the spine where `leaning forward` folds at the
    # hips; `smug` is what holds her head up on the arc. A ninth tag breaks
    # the block -- both candidates cost tags that were working.
    "sip": (
        "(solo:1.5), (squatting:1.4), (from side:1.45), (hunched over:1.45), "
        "(smug:1.3), (holding cup:1.3), (drinking:1.2), (coffee mug:1.3)"
    ),
    # The back of her neck, from behind and above, seated. `(nape of
    # neck:1.45)` does not come down: eased, the pose collapses and she turns
    # to face the camera -- answer the exposure in the negative instead.
    # `yokozuwari`, not `sitting on floor`: the latter extends the legs and
    # they run the frame. `close-up`/`head and shoulders` are unusable from
    # behind -- they draw a character reference sheet.
    "nape": (
        "(solo:1.55), (from behind:1.45), (from above:1.45), (yokozuwari:1.4), "
        "(nape of neck:1.45), (hair over shoulder:1.35), (head down:1.25), (back focus:1.3)"
    ),
    # Face down, chin in her hands, feet swinging up. `chin rest` + `feet up`
    # are what separate this from a body face down on the ground; `lying` +
    # `on stomach` are one unit. `from above` at 1.35, not `nape`'s 1.45: she
    # is already horizontal, and raised it is the tag most likely to buy the
    # overhead rear view. Prints at `--hires 2048`, denoise 0.60 -- that exact
    # pair is the picked line; 0.45 scribbles the outline and 3072 blurs it.
    "prone": (
        "(solo:1.5), (lying:1.45), (on stomach:1.5), (from above:1.35), "
        "(chin rest:1.35), (feet up:1.3), (smug:1.35), (half-closed eyes:1.3), "
        "full body"
    ),
    # The plain 立ち絵. `(hands up:1.25)` puts the joined hands at the chest;
    # without it they land at the waist. `(arched back:1.2)` keeps a posture
    # that came from token order, not from any tag, and leans pin-up if
    # raised. `(full body:1.45)` is weighted because the bare tag lost to the
    # canvas and cropped at mid-calf; the footwear pair exists because a leg
    # with no named shoe ends in a stump -- replace it, never just delete it.
    "stand": (
        "(solo:1.5), (standing:1.5), (from front:1.3), (own hands together:1.35), "
        "(hands up:1.25), (arched back:1.2), (smug:1.35), (half-closed eyes:1.3), "
        "(full body:1.45), (black footwear:1.35), (high tops:1.35), "
        "(wide shot:1.3)"
    ),
    # One leg thrust at the camera, sole first. The foot gets two slots:
    # `soles` names what faces the camera, `foot focus` where it looks.
    # `foreshortening` is bought so the leg reads pointed, not long. `knee up`
    # SINGULAR: one folded, one out is the whole asymmetry. The expression is
    # in PASS 1 -- a late pass refines a decision, it does not reverse one.
    # NO positive toe tag (it swaps the whole palette out; measured) and NO
    # toe guard in pass 1 (guards dissolve the toes -- zero is not five): bad
    # toe topology is a seed problem.
    "kick": (
        # No couch: the sticker band outlines subject-plus-couch as one thing,
        # and no tag un-outlines a couch. The model seats her on an invented
        # ledge instead.
        "(solo:1.5), (sitting:1.45), (soles:1.4), (foot focus:1.35), "
        "(foreshortening:1.3), (knee up:1.25), (leaning back:1.25), "
        "(smug:1.3), (confident:1.25), (half-closed eyes:1.25), (open mouth:1.35), "
        "(full body:1.4)"
    ),
    # 腹筋ができない -- the sit-up must be failing, not absent. `(sit-up:1.5)`
    # leads: buried low, the exercise left the picture entirely. `(from
    # side:1.35)` is what makes the silhouette read as the exercise at all;
    # `(on back:1.4)` is eased so it stops saying "resting" louder than
    # anything says "exercising". `(clenched teeth:1.35)` is the strain and
    # costs `closed mouth` out of FACE.
    "situp": (
        "(solo:1.5), (sit-up:1.5), (from side:1.35), (lying:1.45), "
        "(on back:1.4), (knees up:1.4), (hands behind head:1.35), "
        "(slouching:1.35), (clenched teeth:1.35), full body"
    ),
    # 長座体前屈 that does not reach. `(sitting:1.5)` outranks the stretch:
    # led by `stretching`, the model draws a STANDING bend and the seat is
    # gone. `(from side:1.4)` makes the silhouette read as the exercise, the
    # fix `situp` needed for the same reason, and `(foreshortening:1.35)` is
    # what gives the near thigh its mass -- the side camera alone draws the
    # body flat. `(knees up:1.2)` is the stiffness and stays eased, or the
    # legs fold and take the long sit with them. Do NOT restore a `from
    # above` camera, which draws a top-down crouch with a hand at the lens.
    "reach": (
        "(solo:1.5), (sitting:1.5), (from side:1.4), (foreshortening:1.35), "
        "(legs together:1.35), (stretching:1.3), (leaning forward:1.35), "
        "(outstretched arms:1.3), (knees up:1.2), (thigh focus:1.4), full body"
    ),
    # Double V thrown out and down, weight forward -- `peace` is the still
    # one. `(arms out:1.3)` keeps the Vs off her face; without it `double v`
    # is drawn at the chin, which is `peace` again. `(grin:1.4)` needs
    # `open_mouthed`, or FACE nails the mouth shut and a grin becomes a smirk.
    "hype": (
        "(solo:1.5), (standing:1.45), (from front:1.3), (leaning forward:1.35), "
        "(legs apart:1.3), (double v:1.45), (arms out:1.3), (grin:1.4), "
        "(full body:1.45)"
    ),
    # がおーッ standing. `(fang:1.3)`, not `sharp teeth` -- the joke is
    # one tooth, not a mouthful. In `open_mouthed`: a がおー with a shut mouth
    # is a shrug. `leaning forward` eased to 1.3 because the arms are already
    # up and doing the work.
    "roar": (
        "(solo:1.5), (standing:1.45), (from front:1.3), " + GAO_HANDS + ", "
        "(hands up:1.35), (leaning forward:1.3), " + GAO_FACE + ", "
        "(full body:1.45)"
    ),
    # がおー crouched, loaded. The stance is a knee, not a squat, and it is
    # named TWICE on purpose: `kneeling` is the posture, `one knee` which
    # knee -- alone, `one knee` fell back to a squat on some seeds. Both paws
    # stay up: a knee down invites the three-point stance, which costs half
    # the がおー. No low camera -- `(from below:1.35)` is in NEGATIVE and a
    # pounce shot from below is not available without paying for it.
    "pounce": (
        "(solo:1.5), (kneeling:1.4), (one knee:1.45), (from front:1.3), " + GAO_HANDS + ", "
        "(arms up:1.3), (leaning forward:1.45), " + GAO_FACE + ", "
        "(full body:1.45)"
    ),
    # がおー at full stretch, on tiptoes. `(standing on tiptoes:1.35)` stays
    # low: this model draws feet badly when asked to look at them, and the
    # shod costume's sneakers are part of why this works at all.
    "loom": (
        "(solo:1.5), (standing:1.45), (from front:1.3), " + GAO_HANDS + ", "
        "(arms up:1.45), (standing on tiptoes:1.35), " + GAO_FACE + ", "
        "(full body:1.45)"
    ),
    # 紙コップにストロー. `(drinking:1.3)` is what lifts the vessel to the
    # mouth; `holding cup` alone leaves the hand down. ONE noun on purpose: a
    # paper cup is the model's unaided default, and a second naming drew two
    # of them. NOT in `open_mouthed` -- lips close around a straw.
    "straw": (
        "(solo:1.5), (standing:1.45), (from front:1.3), (holding cup:1.45), "
        "(drinking straw:1.55), (drinking:1.3), (full body:1.45)"
    ),
    # 菓子パン, seated. The vessel grammar: `holding food` fills the hand,
    # `eating` lifts it to the mouth, `(melon bread:1.5)` pins the type (bare
    # `bread` is a loaf or a slice). Seated because a thigh crop plus the
    # costume's named sneakers put a shoe in her hand -- naming what is out of
    # frame invites it back in. `closed mouth` is removed, not replaced: a
    # bite is permitted, a shout is not commanded.
    "snack": (
        "(solo:1.5), (sitting on chair:1.45), (front view:1.35), "
        "facing viewer, (holding food:1.45), (melon bread:1.5), "
        "(eating:1.4), (full body:1.45)"
    ),
    # バスケやりたくない. `(holding basketball:1.5)` is ONE fused noun -- the
    # two-noun form drew two balls. (Danbooru's `basketball_(object)` cannot
    # be written: parentheses are weight syntax.) `(hugging object:1.4)` is
    # the both-hands clutch, which has no tag of its own. `(short dress:1.35)`
    # names the silhouette an oversized tee makes at the thigh, and is what
    # covers her. No `spread fingers`: asking for open fingers bought extra
    # ones. `(@_@:1.0)` and `(dizzy:1.3)` are `dizzy`'s measured values,
    # copied, not re-swept.
    "hoops": (
        "(solo:1.5), (standing:1.45), (from front:1.3), "
        "(holding basketball:1.5), (hugging object:1.4), "
        "(@_@:1.0), (wavy mouth:1.4), "
        "(flying sweatdrops:1.4), (dizzy:1.3), (full body:1.45), "
        "(short dress:1.35)"
    ),
    # 息も絶え絶えで床に座り込む. `arm support` carries the hands-behind
    # shape; `(from side:1.35)` is load-bearing -- a front camera
    # foreshortens the thrown-out legs into nothing. The legs are straightened
    # by a DELETION: `knees up` in the negative. `(>_<:1.45)`: a face
    # symbol's weight window MOVES WITH THE SEED -- re-check both directions
    # on any new seed. `feet out of frame` is a pass-1 framing fix; `sweat`
    # stays lowest (it draws as sheen).
    "winded": (
        "(solo:1.5), (sitting:1.5), (on floor:1.45), (from side:1.35), "
        "(arm support:1.5), (leaning back:1.4), "
        "(outstretched legs:1.5), (legs together:1.4), "
        "(open mouth:1.5), (>_<:1.45), (wavy mouth:1.4), (looking up:1.35), "
        "(heavy breathing:1.45), "
        "(flying sweatdrops:1.35), (sweat:1.3), "
        "(feet out of frame:1.4), (full body:1.45), (short dress:1.35)"
    ),
    # バスケ帰りの電車で寝落ち. `(sleeping upright:1.45)` is weighted ABOVE
    # the far larger `sleeping`, or the picture is a girl in a bed. `zzz` is a
    # face symbol: its weight window moves with the seed. 帰り is said with
    # what she wears and sits on -- towel, bench, objects in front of nothing
    # -- plus the record's SCENE splice, this file's one backdrop break.
    # `sweat` lowest for `winded`'s reason: first tag to cut if skin shines.
    "doze": (
        "(solo:1.5), (sitting:1.5), (sleeping:1.5), (sleeping upright:1.45), "
        "(closed eyes:1.45), (head tilt:1.4), (zzz:1.35), "
        "(bench:1.3), (arms at sides:1.3), "
        "(towel around neck:1.4), (messy hair:1.3), (sweat:1.2), "
        "(full body:1.45)"
    ),
    # ロードバイク. `(riding bicycle:1.5)` is the load-bearing tag: the noun
    # alone puts a bike in frame and says nothing about her relation to it.
    # `road bicycle` is a paid second naming (the unaided default is a city
    # bike); two bicycles is the first thing to look for on a sweep. No road:
    # SURFACE is a flat backdrop and a scene fights that contract.
    "ride": (
        "(solo:1.5), (riding bicycle:1.5), (road bicycle:1.45), (bicycle:1.4), "
        "(from side:1.4), (leaning forward:1.3), (full body:1.45)"
    ),
    # 暑くて床で微動, shot straight down -- the one framing where the flat
    # grey backdrop IS the floor. Every limb tag is SINGULAR: the reference is
    # asymmetric in all three pairs, and this file carries both forms. NO
    # `foreshortening`: it belonged to a leg being snapped up, and a camera
    # tag left behind after its pose eased makes the leg read unnaturally
    # long. Long block -- if a tag goes weak, suspect the length before the
    # newest addition.
    "swelter": (
        "(solo:1.5), (lying:1.45), (on back:1.5), (from above:1.45), "
        # `(flailing:1.25)` is gone with the effect lines: a speed line is its
        # standard drawing, and the guard alone did not finish the job. On at
        # least one seed it was holding the backdrop flat -- a cost the
        # delivery repaint cannot cover.
        "(knee up:1.35), (spread legs:1.35), (arm up:1.4), "
        "(clenched hand:1.35), (closed eyes:1.4), (open mouth:1.35), "
        "(screaming:1.4), (furrowed brow:1.35), (midriff:1.35), (navel:1.3)"
    ),
    # The がおー cropped to head and shoulders, on `portrait`'s settled
    # framing. In HEAD_FRAMINGS: naming a garment that is out of frame is what
    # invites it back in, so the legwear and most of BODY drop out of the
    # prompt -- not a choice this pose gets to make differently.
    "snarl": (
        "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), (close-up:1.2), "
        "(face focus:1.3), " + GAO_HANDS + ", (hands up:1.4), " + GAO_FACE
    ),
    # テヘペロ minus the ペロ. NO `;p`: an emoticon names a complete
    # expression (wink WITH tongue) from one token and cannot lose half of it,
    # so the face is spelled out. `(v:1.45)` over `(hand on own cheek:1.05)`:
    # the two tags name different handshapes for the same hand and the heavier
    # one gets it -- keep the inversion; the exact values past it are noise,
    # and the hand itself is the seed. `(upper body:1.35)`, not `close-up`:
    # the one crop here with a hand ON the face, and the delivery flood needs
    # the larger backdrop share.
    "tehe": (
        "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), "
        "(upper body:1.35), (face focus:1.3), (one eye closed:1.45), "
        "(wink:1.35), (smile:1.35), (v:1.45), (hand on own cheek:1.05)"
    ),
    # 疲れ顔で歯磨き, `tehe`'s hand-at-face framing. Two-slot rule: `brushing
    # teeth` is the action that puts the object at the mouth and takes the
    # heavier weight; `toothbrush` picks the object. The exhaustion is
    # `allnighter`'s pair at its weights -- no expression tag beside it, for
    # `allnighter`'s reason: naming the mood brought the face back angry.
    "brush": (
        "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), "
        "(upper body:1.35), (face focus:1.3), (brushing teeth:1.45), "
        "(toothbrush:1.3), (eyebags:1.4), (half-closed eyes:1.35)"
    ),
    # 自分の髪でヒゲを作って遊ぶ. The mustache words are OUT of the positive
    # and banned by name in the negative: asked for, they draw the part
    # instead of the gesture. `holding own hair` fills the hand; `smelling
    # hair` is the placement -- the one vocabulary that pins held TIPS to the
    # NOSE -- and the smug narrowing it drags in is banned in `negative()`.
    "hige": (
        "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), "
        "(upper body:1.35), (face focus:1.3), (holding own hair:1.5), "
        "(smelling hair:1.45), (playing with own hair:1.3), (smile:1.2)"
    ),
    # 回復体位っぽい横寝。新しく買っているのは `(on side:1.5)` と
    # `(knee up:1.35)` の二つだけ -- 横向きで両脚が伸びればただの寝姿で、
    # 上の膝が前に折れて初めてあの形になる。`(from above:1.35)` は必須:
    # 真横からは手前の脚が折った膝を隠す。残りは flop / prone の語彙を
    # その重みのまま使う。
    "recover": (
        "(solo:1.5), (lying:1.45), (on side:1.5), (from above:1.35), "
        "(outstretched arm:1.3), (knee up:1.35), (smug:1.35), "
        "(half-closed eyes:1.3), full body"
    ),
    # おねだり、胸より上 (`tehe` の framing)。`(hands up:1.3)` がないと手が
    # 腰へ落ち、この枠では腰は枠外なので手ごと消える。上目遣いは
    # `(from above:1.35)` のカメラで作る -- 顔だけ上げさせる語彙はない。
    # 目と口は FACE のまま。`sparkling eyes` 系は EYE_BAN が禁じる側なので
    # 足さない。
    "beg": (
        "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), "
        "(upper body:1.35), (face focus:1.3), (begging:1.45), "
        "(own hands together:1.4), (hands up:1.3), (from above:1.35), "
        "(blush:1.3)"
    ),
    # したり顔で、指先だけ合わせた祈り手を口元に。`(steepled fingers:1.45)`
    # がその指先合わせを名指しする唯一のタグで、`(covered mouth:1.35)` が手の
    # 高さを口の位置に固定する。顔は neki8u 配線: FACE の tareme + own_eyes
    # + 自前の `(half-closed eyes:1.3)`。口は FACE の closed のまま -- 手で
    # 覆う構図なので開けない。ドヤが足りなければ `(open mouth:1.35)` が次の
    # ダイヤル。
    "sly": (
        "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), "
        "(upper body:1.35), (face focus:1.3), (steepled fingers:1.45), "
        "(own hands together:1.35), (hands up:1.3), (covered mouth:1.35), "
        "(smug:1.35), (half-closed eyes:1.3)"
    ),
    # 指を指してケタケタ笑う、`hype` の立ち骨格。`(hand on own hip:1.15)` は
    # 遊んだ手が顔へ行くのを止める側で、低重みは主役の指差し腕と張り合わせ
    # ないため (`tehe` の頬手 1.05 と同じ理由)。目は `sly` と同じドヤ配線。
    # 見下ろし成分は目と `(smug:1.35)` が持ち、laughing 側に冷たさは
    # 持たせない。
    "cackle": (
        "(solo:1.5), (standing:1.45), (from front:1.3), "
        "(leaning forward:1.35), (pointing at viewer:1.5), "
        "(outstretched arm:1.3), (hand on own hip:1.15), (laughing:1.45), "
        "(open mouth:1.4), (smug:1.35), (half-closed eyes:1.3), "
        "(full body:1.45)"
    ),
}


# The extra-limb trio: `extra limbs` unweighted in NEGATIVE stopped nothing;
# the weighted names are what work.
_LIMB_TRIO = "(extra arms:1.5), (extra legs:1.5), (extra limbs:1.5), "

# The dress's halter straps, official design. Per-pose because globally the
# tag costs the coat its shoulders; ONE tag, not `nape`'s two -- the
# three-tag form pulls the camera in, and the backdrop intruders it invites
# are repainted at delivery anyway (recolor_bg.py).
_CRISS_CROSS = Edit("replace", "(drawstring:1.4), ",
                    "(drawstring:1.4), (criss-cross halter:1.45), ",
                    gate="dressed")

POSE_RECORDS = {
    # The leg keeps the block's own gradient -- ruled the correct one against
    # a grad-removed variant, side by side. One costume, every pose.
    "lounge": Pose(POSES["lounge"], (1024, 1536), own_eyes=True),
    # Head framings sit in a square: (portrait:1.5) alone lost to a 1024x1280
    # canvas and drew down to the thighs.
    "portrait": Pose(POSES["portrait"], (1024, 1024), own_eyes=True, framing="head",
                     # The straps are in frame here and were never drawn until
                     # the splice arrived.
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
            # alone; naming `small breasts` positively lands it in one step.
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
            # reads as skin to uncover -- it kept taking the coat off. What
            # this must NOT forbid is the coat slipping:
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
        # Straight at the rear, foreshortened, BODY's hip/thigh tags read as
        # bulk. EASED, not deleted -- pushing further drew the rabbit
        # intruder.
        body_edits=(
            Edit("replace", "(wide hips:1.3)", "(wide hips:1.0)"),
            Edit("replace", "(thick thighs:1.35)", "(thick thighs:1.05)"),
        )),
    "flop": Pose(
        POSES["flop"], (1536, 1024), own_eyes=True,
        # The torso reads long unless the leg is asked for; bracketed from
        # both sides -- 1.45 overshoots into too-long legs, and the negative
        # route does nothing on this axis.
        body_edits=(Edit("replace", "(pale skin:1.25)",
                         "(long legs:1.40), (pale skin:1.25)"),),
        # `smug` narrows the lids on its own, and a 250px face is where eyes
        # stop matching. Pass 2 only.
        hires_negative="(half-closed eyes:1.4), (closed eyes:1.4), "),
    "kick": Pose(
        POSES["kick"], (1024, 1536), own_eyes=True, open_mouth=True,
        legwear_edits=(
            # Only this framing puts the tights gradient's light end at the
            # camera; full colour at reduced weight beat the pale name raised.
            Edit("replace", "(pale purple pantyhose:1.35)",
                 "(purple pantyhose:1.15)", gate="dressed"),
        ),
        negative_edits=(
            # All five as the picked render carried them: the effect-line
            # trio plus the dress pair (no buttons, no collar).
            Edit("prepend", new=(
                "(speed lines:1.45), (motion lines:1.4), (emphasis lines:1.4), "
                "(buttons:1.35), (collared dress:1.35), "),
                stage=S_POSE_GUARDS),
        ),
        # ONE toe guard: she is in opaque tights, so a smooth toe box is the
        # picture -- five countable toes was the error, and a second guard
        # flattens every accent. `closed eyes` banned while the positive asks
        # half-closed: forbid shut / ask half.
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
    # Landscape: the extended legs run the long side, and the width is what
    # keeps them in frame beside her rather than cropped at the shin.
    "reach": Pose(
        POSES["reach"], (1536, 1024),
        negative_edits=(
            # `stretching` brings the gym with it exactly as `sit-up` does,
            # and the same guard answers it.
            Edit("append", new=", (sportswear:1.45), (gym uniform:1.4)",
                 gate="default_or_roomwear", stage=S_POSE_SCENE),
            # This pose's own risk: a seated stretch is one weight away from
            # a straddle, and `legs together` alone does not hold it.
            Edit("append", new=", (split:1.45), (spread legs:1.4)",
                 stage=S_POSE_SCENE),
        ),
        # The soles come at the lens, so the toe guard the delivery adds is
        # already needed a pass earlier.
        hires_negative="(toes:1.55), "),
    # 832 wide: width beside her is room for someone else to stand -- the
    # 1024 form kept drawing a second figure.
    "stand": Pose(
        POSES["stand"], (832, 1664), own_eyes=True,
        face_edits=(
            # The lash pair melts THIS pose into foil noise -- full prompt,
            # every seed, weight-independent; other poses carry the same pair
            # and are fine. The negative's `(long eyelashes:1.35)` was
            # isolated and acquitted.
            Edit("replace", "(eyelashes:1.3), (thick eyelashes:1.35)",
                 "eyelashes"),
        ),
        # ADDED beside `petite`, not substituted into it (measured within
        # noise and not picked). The negative route moved nothing on this
        # axis, twice.
        body_edits=(Edit("replace", "(pale skin:1.25)",
                         "(long legs:1.35), (pale skin:1.25)"),),
        # Straps are the design; the backdrop cost is repaid by recolor_bg.py
        # at delivery.
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
            # Shoe decal, logo and colour are three separate defects, so
            # three guards. The ear-like high collar is WANTED and survives
            # all three.
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
                  # The settled finish, carried whole -- see PAINT_FINISH in
                  # `recipe.py` for why it is one decision, not two.
                  paint_finish=True, hires_negative=HIRES_NEGATIVE_PAINT),
    "snack": Pose(POSES["snack"], (1024, 1536), open_mouth=True,
                  paint_finish=True, hires_negative=HIRES_NEGATIVE_PAINT),
    "hoops": Pose(
        POSES["hoops"], (832, 1664), own_eyes=True, open_mouth=True,
        negative_edits=(
            # Two hands closed around an object is `tehe`'s accident class,
            # and the guard must ride BOTH passes, or the sweep judges a
            # prompt the print does not use. Prepended -- token order.
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
        # Hand-drawn finalize: THIN off (pass 2 only) plus the marker pair,
        # appended at the very END -- a mid-prompt splice re-encodes every
        # token after it, so the mechanisms stay separate. `sketch` is NOT
        # here: it means unfinished, the state HIRES_NEGATIVE_PAINT removes.
        hires_finish=HANDDRAWN_FINISH,
        # --hires is a longest-side number, not a scale: 1416 is this pose's
        # 1.23x, the ratio every portrait pose prints at. 0.50 because the
        # face is carried by a symbol and 0.60 dissolves it.
        hires_print=(1416, 0.50),
        # The seed holds the colour and decides whether `feet out of frame`
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
            # The one SCENE in the file, a measured break of the flat-
            # backdrop contract. Only the background pair is replaced -- flat
            # color, white outline and the shading pair stay, which is why
            # the carriage arrives as pale line rather than as a photograph.
            # Costs recolor_bg.py and headcount.py their jobs on this pose.
            Edit("replace", "(simple background:1.3), (grey background:1.2)",
                 SCENE_TRAIN),
        ),
        negative_edits=(
            # A carriage is a room whose subject is other passengers, and
            # (solo:1.5) has never had to hold against a background that
            # implies a crowd. In front -- token order.
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
        # The from-above camera makes the legs read long, and `petite`
        # answers proportion as a whole; both this and keeping the camera fix
        # were needed.
        body_edits=(Edit("replace", "(petite:1.2)", "(petite:1.4)"),),
        character_edits=(
            # Indoors, so the shod costumes' outdoor shoes come off. A
            # SUBSTITUTION in the footwear slot, not a removal: `no shoes`
            # keeps the tights where `barefoot` would strip them. Gated on
            # the costumes that have shoes; a `default` swelter has never
            # been rendered and gets no invented slot.
            Edit("replace",
                 "(white footwear:1.4), (sneakers:1.45), (high tops:1.3)",
                 "(no shoes:1.35)", gate="shod"),
        ),
        negative_edits=(
            # The provenance tail bared the midriff, and releasing it costs
            # nothing. `(cropped jacket:1.45)` stays -- different garment,
            # and the garment is a contract.
            Edit("remove", ", (midriff:1.35), (navel:1.3)",
                 stage=S_POSE_GUARDS),
            # Speed lines are a drawn object with a name, which is what a
            # guard has always been able to take out; nothing in the positive
            # asks for them. Three names because the model does not treat
            # them as one.
            Edit("append", new=", (motion lines:1.5), (speed lines:1.5), "
                               "(emphasis lines:1.45)",
                 stage=S_POSE_GUARDS),
        ),
        # An unpainted region has to be NAMED before 0.60 can resolve it:
        # sketch/lineart are the medium, unfinished the state, monochrome
        # what an unpainted flat is. Pass 2 only -- the picked composition is
        # not re-rolled.
        hires_negative=HIRES_NEGATIVE_PAINT),
    "tehe": Pose(
        POSES["tehe"], (1024, 1024), own_eyes=True, framing="head",
        negative_edits=(
            # The emoticon that drew the tongue is gone; a wink and a small
            # mouth are what the model draws one FROM. A tongue is a drawn
            # object with a name.
            Edit("prepend", new="(tongue:1.5), (tongue out:1.5), ",
                 stage=S_POSE_GUARDS),
            # The hand guard rides PASS 1 too, hands in front of the tongue
            # -- token order. A guard that only runs on the pass being
            # redrawn is not a guard.
            Edit("prepend", new=HAND_BAN, stage=S_POSE_GUARDS),
        ),
        # ...and the pass-2 copy: 0.70 redraws the hand.
        hires_negative=HAND_BAN),
    "brush": Pose(POSES["brush"], (1024, 1024), own_eyes=True, framing="head",
                  open_mouth=True,
                  settled_seed=737373737),
    "hige": Pose(
        POSES["hige"], (1024, 1024), own_eyes=True, framing="head",
        tail_edits=(
            # `(frills:1.25)` names a dress collar that is out of frame here,
            # and the tag was landing on the cardigan instead. Gated on the
            # costume whose CHARACTER carries it.
            Edit("remove", "(frills:1.25), ", gate="dressed"),
            # End-appends, AFTER everything -- the token order the pick was
            # drawn in; a mid-prompt insertion re-rolls every token after it.
            Edit("append",
                 new=", (covered mouth:1.35), (tareme:1.5), (large eyes:1.4)"),
        ),
        negative_edits=(
            # Two prices of the pose's own tags: the lace trio removes what
            # the model draws out of habit once the `(frills:1.25)` ask is
            # gone, and the eye trio returns FACE's tareme against `smelling
            # hair`'s smirk. Then `tehe`'s hand guard (a hand closed at the
            # face), then the mustache words, moved here from the positive:
            # asked for, they drew the part instead of the gesture. The hair
            # at the lip has no name in this prompt, so the ban cannot delete
            # it.
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
        # Picked over six fresh seeds on the identical prompt -- the seed is
        # carrying something the words do not.
        settled_seed=3409564303),
    # 横になった体は横長の枠に入る -- `prone` / `flop` と同じ 1536x1024。
    # BODY の腰/腿は素のまま: `prone` がそこを緩めたのは真後ろからの短縮で
    # 嵩に読まれたからで、横向きはその面をシルエットとして見せる。最初の
    # スイープで下半身が重いなら、緩めるのはここ。
    "recover": Pose(POSES["recover"], (1536, 1024), own_eyes=True),
    # 顔の前で手を組むので、`tehe` / `hige` と同じく両パスに手ガード。頭部
    # framing は正方形 -- `portrait` が縦長で腿まで描いた記録がある。
    "beg": Pose(
        POSES["beg"], (1024, 1024), own_eyes=True, framing="head",
        negative_edits=(
            Edit("prepend", new=HAND_BAN, stage=S_POSE_GUARDS),
        ),
        hires_negative=HAND_BAN),
    # 顔の前で両手を組むので `beg` / `tehe` / `hige` と同じく両パスに手ガード。
    # 隣の `(interlocked fingers:1.5)` は指先合わせの直接の反対 -- 指を
    # 絡めた祈り手は steepled と同じ語彙圏にいて、名指しで断らないと出てくる。
    "sly": Pose(
        POSES["sly"], (1024, 1024), own_eyes=True, framing="head",
        negative_edits=(
            Edit("prepend", new=HAND_BAN + "(interlocked fingers:1.5), ",
                 stage=S_POSE_GUARDS),
        ),
        hires_negative=HAND_BAN + "(interlocked fingers:1.5), "),
    # 832 は `hype` / `roar` の立ち幅。指差しの人差し指は HAND_BAN の守備範囲。
    # `oversized shirt` はシード次第でボタン前立てシャツワンピを描くので
    # positive 側から除去し、ボタンは名指しで ban する (新規生成には効く)。
    "cackle": Pose(
        POSES["cackle"], (832, 1664), own_eyes=True, open_mouth=True,
        character_edits=(
            Edit("remove", "(oversized shirt:1.3), ", gate="dressed"),
        ),
        negative_edits=(
            Edit("prepend", new=HAND_BAN, stage=S_POSE_GUARDS),
            Edit("prepend", new="(buttons:1.5), (button placket:1.4), ",
                 stage=S_POSE_GUARDS),
        ),
        hires_negative=HAND_BAN + "(buttons:1.5), (button placket:1.4), "),
}

assert set(POSE_RECORDS) == set(POSES), (
    set(POSE_RECORDS) ^ set(POSES))
