"""The wardrobe: who she is, and the four sets of clothes hung on it.

A costume owns three blocks -- character, legwear, hood -- and its own staged
negative edits below. Everything else (FACE, SURFACE, BODY, THIN, every pose,
the rest of the negative) is shared: what changes between costumes is the
clothes, not her and not the drawing.
"""

from __future__ import annotations

from .models import S_BARE_LEGS, S_FABRIC, S_KNOT, S_MIDRIFF, S_SEAM, S_TINT_RELEASE, Edit

# Who she is, as against what she is wearing. Split out of CHARACTER the day a
# second costume arrived: the garments below are one of two sets now, and this
# is the half both sets keep. The split moved no text and no token order --
# `IDENTITY + <garments>` is byte-identical to the CHARACTER that shipped, and
# costume_check.py's fingerprint is the proof: it did not move when this line
# was drawn.
#
# `hair ornament` carried no weight until the nape renders, where it lost
# every time -- her clips were missing from a dozen straight. It is not that
# the tag is wrong, it is that an unweighted tag in a prompt this crowded is
# indistinguishable from an absent one: everything around it is at 1.3+.
# Same disease and same fix as `drawstring` in CHARACTER.
IDENTITY = (
    "yuzuki yukari, (light purple hair:1.25), (short hair with long locks:1.45), "
    "(very long sidelocks:1.3), sidelocks, (purple eyes:1.25), hair between eyes, "
    "(hair ornament:1.4), "
)

CHARACTER = IDENTITY + (
        # hooded coat, not hoodie. The hem is the one thing that answered to nothing
    # else: raising (black hoodie) to 1.55 did nothing, (cropped jacket) in the
    # negative did nothing, (oversized clothes) destroyed the costume, and
    # deleting the body block did nothing. Swapping the noun moved it, because
    # these are different garments to the model rather than one with a length:
    # dark pixels 13.6-18.4% on hoodie against 16.6-25.1% on hooded coat.
    #
    # `hooded cardigan` measures longest of all (17.9-26.1%) and is the one to
    # try if this wants to go further. The coat is here because ns-1117511306 --
    # prompt 7d231c4f, the render this is aimed at -- is a coat.
    # hooded cardigan, and sleeves that say "too big" without naming the garment.
    #
    # Length first: nothing but swapping the noun ever moved the hem. Raising
    # (black hoodie) to 1.55 did nothing, (cropped jacket) in the negative did
    # nothing, deleting the body block did nothing. Measured dark pixels by
    # garment: hoodie 13.6-18.4%, hooded jacket 16.6-25.1%, hooded cardigan
    # 17.9-26.1%. The cardigan is longest, and against the coat it took the
    # lower back from 46.6% to 58.0% covered.
    #
    # Then the silhouette. The target is an oversized hoodie -- boxy body, big
    # soft hood on the shoulders, hem at the hip. Every tag that names the
    # garment's fit failed: (oversized clothes) destroyed the costume at 1.35
    # AND at 1.15 (stroke 1.91 -> 3.82 both times), (loose clothes) loosened the
    # drawing rather than the cloth (stroke to 7.64), (coattails) drew narrow
    # jointed straps, (wind) summoned floating white shapes.
    #
    # Tags naming a PART's state pass where tags naming the garment's fit do not.
    # (sleeves past wrists) + (wide sleeves) took the lower back from 54.6% to
    # 78.5% covered, boxed out the body and dropped the hem, at 1.91px.
    "(black hooded cardigan:1.45), open cardigan, (rabbit hood:1.55), "
    # The hem does not respond to length tags. Asked to cover the buttocks, three
    # renders moved bare skin in the upper-leg band 37.4% -> 40.1% -> 38.3%:
    # (medium dress:1.3), then (medium dress:1.45) with (short dress:1.4),
    # (microdress:1.4) opposing it in the negative. All noise. `short dress` per
    # its wiki already spans "the middle of the thighs at the lowest to just
    # below the crotch and ass at the highest" and this sits at the top of that
    # range and stays there.
    #
    # The likely reason -- untested -- is that the costume comes from
    # `yuzuki yukari` itself rather than from these garment tags, so a length tag
    # is arguing with the character prior and losing. Lengthening it will need
    # something with more authority than a tag: a different garment noun, or
    # inpainting the hem.
        # 1.2 -> 1.45. At 1.2 the purple was being drawn as a pleated skirt with a
    # separate white frill under it -- a two-piece where the design is one.
    #
    # Naming the wrong reading in the negative instead, (skirt:1.35),
    # (pleated skirt:1.4), deleted the lower half of the garment outright on one
    # of two seeds: hoodie and tights, no dress. Third time a guard tag has cost
    # more than it bought here, after the duplicate guards that wrecked the
    # palette and the (thighhighs:1.3) that removed the socks.
    # `drawstring` -- the coat's cord, with the pink bead on the end -- was
    # unweighted and therefore not drawn. Weighted, it comes back.
    #
    # The dress's own fastening is NOT here, deliberately. It ties at the back
    # of the neck in black straps, and `positive` adds those for the one pose
    # that can see them. Globally they are destructive: measured on `sip`,
    # (halterneck:1.45) + (black straps:1.35) pulled the coat off her shoulders
    # and bared her back, and lowering them to 1.15/1.1 still bared a shoulder.
    # Naming a halter is apparently read as naming a garment that leaves the
    # shoulders out, and the coat gets out of its way.
    "animal hood, long sleeves, (drawstring:1.4), (purple dress:1.45), short dress, "
    # 0.85 -> 1.25 (2026-08-18). "Weighted down rather than deleted" was the
    # intent and 0.85 did not deliver it: below 1 in a prompt where everything
    # else is 1.3+ has meant ABSENT three times in this file, and this was the
    # fourth. `boss` had spliced it to 1.25 for a session already and got the
    # frilled collar, the ribbon ties and the beaded cords back for nothing
    # measurable -- so the value was proven and simply never promoted.
    #
    # 「ワンピースを正しく見直す」. Measured here on 555666777 and 1886970040:
    # the frilled hem returns, the coat's cord shows its pink bead, the backdrop
    # stays clean. It is a COSTUME change and therefore every pose.
    "(frills:1.25), vocaloid, voiceroid, "
    # The oversized silhouette: boxy body, big soft hood, hem at the hip.
    #
    # Neither of these works alone. (oversized shirt:1.35) on its own broke the
    # stroke to 3.82 and 13.69px; (sleeves past fingers:1.4) on its own to 4.65
    # and 7.64. Together at 1.3 each, the stroke holds at 1.91 on both seeds and
    # lower-back coverage goes 54.6% -> 79.8% and 96.2%.
    #
    # That is the same shape as the sock lengths, where dropping one of two
    # competing tags made things worse: they hold each other in place. It is NOT
    # the "nouns and part-states pass, fit words fail" rule written here earlier
    # -- `oversized shirt` is a noun and `sleeves past fingers` is a part state,
    # and both destroy the drawing on their own. That rule was generalised from
    # two tags that happened to work and does not hold.
        # `past wrists`, not `past fingers`. Fingers-length sleeves cover the hands
    # entirely and they get drawn as shapeless lumps; five of five renders had
    # them buried. Letting the hands out puts real fingers on the coins in four
    # of five, and drops the colour count from 26-50 to 16-22 as a bonus.
    #
    # Weighting the hand guards already in the negative -- (bad hands:1.4),
    # (extra fingers:1.4) -- did nothing: all five still had the hands inside
    # the sleeves. The fix was removing what hid them, not forbidding the
    # failure.
    #
    # Swapping this same tag once left her back bare, in a block without
    # (coin:1.3) in the pose. It does not here. The same substitution is not the
    # same change in a different block.
    "(oversized shirt:1.3), (sleeves past wrists:1.3)"
)

# rabbit print is deliberately absent: paired with `sticker` it drew a rabbit
# decal on her cheek in the 1024x1024 portrait. `sticker` earns its place --
# it is half of the white-outline idiom -- so the print is the one that goes.

# Reset to b1258b0c: hood down at 1.25, not pinned behind her head.
#
# The alternative -- (hood down:1.5), (hood behind head:1.3) -- was measured and
# is not better: unpinning changed neither the colour count nor the clutter, and
# pinning it back did not recover anything. This is the picked render's value.
HOOD = "(hood down:1.25), (visible hair:1.2), (purple eyes:1.2)"

# Pale thighhighs over opaque black tights. The layering failed before with
# (sheer black pantyhose:1.5) underneath -- the sheer tights vanished and left
# the socks alone. Solid black is a much stronger thing to ask for, so the pair
# gets another go rather than being abandoned.
#
# (lavender tint:1.3) and the pale sock colours are not only leg tags: dropping
# them took the whole palette darker and flatter, because they were where the
# pale cast came from.
#
# What did have to go is the see-through set -- (see-through pantyhose:1.45),
# (skin visible through pantyhose:1.4) never stayed on the legs and left the
# dress sheer over her stomach.
# RETIRED, kept whole. Everything below was measured and none of it was wrong;
# the design it serves is the one that changed. Read it before proposing two
# garments again -- it is the record of what the layering costs and of the four
# things that do not move the sock colour.
LEGWEAR_LAYERED = (
    # grey, not black. `grey pantyhose` is the canonical spelling (`gray_` has no
    # page) and its wiki warns of "considerable overlap" with black and brown --
    # brown is guarded in the negative already.
    #
    # Chosen over red: the hoodie lining measures #bc616a, and (red pantyhose)
    # landed at hue 338 / saturation 152 against the lining's 313 / 126. Close
    # enough to read as the same intent, far enough to read as a second red.
    # Grey sits inside a range the palette already has.
    #
    # The cost is the layering: the dark band at the top of the thigh went from
    # 28.7-41.6% of the measured strip on black to 10.2-28.6% on grey, because
    # the socks are pale and the contrast under them shrank.
    #
    # Nothing found makes it darker, and two things make it lighter. Band value,
    # lower being darker, over three seeds:
    #
    #     (grey pantyhose:1.45) alone            52.9 / 73.1 / 76.3
    #     + (black pantyhose:1.1)                80.1 / 81.4 / 84.9
    #     + (black pantyhose:1.25)               85.8 / 92.2 / 83.8
    #     (charcoal pantyhose:1.35) alongside    57.5 / 73.1 / 84.9
    #
    # Mixing in the darker colour name lightens it, and more of it lightens it
    # further: two colour words land on neither, somewhere between. Competing
    # tags held each other in place for sock *length* -- dropping one there made
    # things worse -- and that does not carry over to colour. Grey alone is the
    # darkest of everything tried.
    "(grey pantyhose:1.45), pantyhose, (opaque pantyhose:1.3), "
    # over-kneehighs ends just above the knee and, per its danbooru wiki, exists
    # to "leave a larger gap between the stocking and the skirt or dress" --
    # which is the shortening that was wanted. It is ADDED, not substituted:
    # swapping the whole block to over-kneehighs removed the socks entirely,
    # because `thighhighs over pantyhose` is a real tag carrying the layering
    # and `over-kneehighs over pantyhose` is a phrase that is not.
    # 1.2/1.5 measured sock saturation 22.9 against fb-b's 12.2, and 1.45/1.25
    # overshot to 8.7. Left at the first, because the second cost dress hue
    # (306 -> 280 against a 300 target) and whiteness is the cheaper of the two
    # to fix afterwards.
    #
    # The background moved too -- #d0d0c0, #a0a0a0, #909090 across 1.2/1.5,
    # 1.45/1.25 and 1.35/1.35 -- and the middle setting was the darkest of the
    # three. That is not these tags controlling it, it is the backdrop being
    # unstable under any small perturbation, which is already written down:
    # generate against whatever flat value turns up and set the real one with
    # scripts/recolor_bg.py --color. fb-b's is #d0d0c0.
    "(very pale purple thighhighs:1.5), (white thighhighs:1.2), "
    # over-kneehighs is OUT. This is lyC-555666777 (prompt 9d24700e), checked
    # afterwards across seven seeds: all seven put pale socks over black tights
    # on both legs, with the tights showing as a band at the top of the thigh.
    #
    # It was written up as the least consistent arm on the strength of a
    # left/right brightness difference that peaked at 73.9. That measure reads
    # pose and overlap, not sock length -- 737373737, reported here as having
    # lost a sock, has both -- and it had already been found unfit for judging
    # legwear one arm earlier. The number was wrong, not the recipe. Judge this
    # block by looking at it.
    "(lavender tint:1.3), "
    "(thighhighs over pantyhose:1.55)"
)

# ONE garment on the leg, and it is the pantyhose. This is the live block: it is
# what `positive()` splices into every full-figure pose, and it is a change to
# the COSTUME rather than to any one pose, which is why it lives here and not in
# a splice.
#
# The official V6 sheet draws one pantyhose. The layered pair above is this
# repo's own invention, and it held up for a while -- lyC-555666777 put pale
# socks over grey tights on seven seeds out of seven. What broke it was the
# prone pose: seen from behind, whichever layer covers the buttock ends in a
# hem, and a fitted shape bounded by a hem above legs of another colour is a
# pair of bike shorts. 「スパッツになってる」. Six lexical attempts, a regional
# conditioning pass and a hand-drawn hem later, the answer was that the model
# only knows `thighhighs over pantyhose` -- which puts the boundary on the
# THIGH, the exact geometry the pose threw out.
#
# 「タイツ1本にするか」. Abandoned, not deferred. Dropping the second garment
# removes the boundary, so there is nothing left to hold: no hem to draw, no
# region to condition, no two greys to keep apart.
#
# The gradient is the sheet's own reading and it runs the other way from the
# tights it replaces -- purple at the thigh, black at the ankle, one surface the
# whole way. I called that inverted once and dropped `(gradient legwear)` on the
# strength of it; the purple end is what was wanted.
#
# Three tags, which is the count a garment block tolerates here before the coat
# starts sprawling. Six attempts could not lower the purple end from the prompt
# -- `(muted colors)`+`(desaturated)` DOUBLED the leg's saturation, 37.7 to
# 75.6, `(dusty purple)` raised it, and a vividness guard left the mean flat and
# pushed the peak up. That is the shape the notes name: when the tag describing
# the defect does nothing at any weight, the defect is implied by something
# else -- here the pale purple dress and hair, pulling the top of the leg toward
# them. Take it off afterwards instead, with `.local/desat.py` (HSV S alone, so
# the gradient and the line survive); x0.55 matches the older palette.
# ---- and then the direction had to be said out loud (2026-08-18) ----
#
# 「グラデーションの向きが逆ですね。足先を黒に。これは固定化」. The three-tag
# block above describes the garment and says nothing about which end is which,
# and left to itself the model put the black at the THIGH and faded it pale at
# the ankle -- the exact reverse of the design this comment has asserted since
# the layering was retired. Six seeds of `stand` all drew it that way, so it was
# never a seed.
#
# There is no directional tag. `gradient legwear` is the only gradient word the
# model has and it carries no orientation, so the direction has to be bought by
# naming the colour that goes at the top and letting the black fall to what is
# left. `pale purple pantyhose` is the tag for that job and it was already
# measured, one design ago, for exactly this property: it gets DRAWN on the
# thigh where `grey pantyhose` does not. That finding was recorded as an
# explanation of an accident -- the wrong colour was buying thigh coverage --
# and it is now what the block is built on.
#
# Measured on 1886970040, three wordings, one seed, `stand`:
#
#   black, gradient, opaque                   black thigh, pale ankle (reversed)
#   black, PALE PURPLE, gradient, opaque      purple thigh, black ankle  <- kept
#   PALE PURPLE, black, gradient, opaque      also right-way-up, and the whole
#                                             composition moved -- see `stand`
#
# The last two both fix the direction, so order is not what carries it; the
# colour being named at all is. Black stays first and at 1.5, which keeps it the
# garment's stated colour with the purple as the thing done to one end of it.
#
# FOUR tags, and the comment above says three is what a garment block tolerates
# here before the coat starts sprawling. The fourth is spent knowingly and this
# is the note that says so: if the coat starts growing or the dress loses its
# frills, this tag is the first suspect, ahead of anything a later session adds.
LEGWEAR = ("(black pantyhose:1.5), (pale purple pantyhose:1.35), "
           "(gradient legwear:1.4), (opaque pantyhose:1.4)")

# And the second garment banned by name. Not decoration: these are exactly the
# words the layered recipe spent its weight on, and the model reaches for them
# on its own -- `thighhighs` alone came back on seeds that asked for none.
#
# Six tags is more guards than this file usually allows itself, and the rule it
# looks like it is breaking is a different one: the palette damage came from
# stacking guards that all pointed at ONE defect, outvoting each other's
# neighbours. These six each name a distinct garment. Measured across the
# one-tights arms with the whole list present -- palette intact, hair violet,
# backdrop grey, no colour drift.
LEGWEAR_BAN = (
    "(thighhighs:1.5), (kneehighs:1.5), (socks:1.45), (over-kneehighs:1.45), "
    "(two-tone legwear:1.4), (legwear hem:1.3)"
)

# THE SECOND COSTUME. Everything above this line is the settled one and it does
# not move: this is another set of garments hung on the same IDENTITY, reached
# with `--costume sporty`, and the point of building it this way is that the
# original is one flag away and stays reproducible. Nothing here replaces
# anything.
#
# The reference is a grey oversized tee, denim shorts, plain black tights and
# white high-top sneakers. Three things it keeps from the settled costume on
# purpose: IDENTITY whole, ONE garment on the leg, and its shoes named in the
# costume rather than in a pose -- `stand` is the only pose that names footwear
# and it has that pair spliced out under this costume; see `pose_block`.
SPORTY = IDENTITY + (
    "(grey shirt:1.45), (t-shirt:1.45), (oversized shirt:1.4), short sleeves, "
    "(denim shorts:1.45), (short shorts:1.25), "
    "vocaloid, voiceroid, "
    "(white footwear:1.4), (sneakers:1.45), (high tops:1.3)"
)

# One garment on the leg, exactly as LEGWEAR is -- the gradient pair is what
# makes that one purple, and this one is plain. LEGWEAR_BAN still applies: the
# reference has tights running straight into the shoe with no sock at the
# ankle, so the six guards that keep a second garment off are as load-bearing
# here as they are there.
SPORTY_LEGWEAR = "(black pantyhose:1.5), (opaque pantyhose:1.4)"

# HOOD minus the hood. `(hood down:1.25)` is an instruction about a garment this
# costume does not have, and naming an absent garment is how it gets drawn.
SPORTY_HOOD = "(visible hair:1.2), (purple eyes:1.2)"

# The third costume, and it was arrived at by subtraction from the second over
# one session: the tee lost its print and its colour, the denim and the tights
# came off as 夏っぽくない, a skirt was tried in six shapes and abandoned
# (「スカート案をやめた方が良さそう」), and what was left is a gym kit.
#
# 「無地でリブ生地がいいな。夏っぽさを出すなら少し薄めの紫」 is the top, tag for
# tag: `light purple` is IDENTITY's own spelling for the shade, borrowed rather
# than invented, and one colour tag in one slot -- `purple shirt` is NOT stacked
# beside it. `ribbed_shirt` is 8.3k.
#
# `(high-waist pants:1.4)` is here and not in the legwear block on purpose. It
# is the waistband, which is a thing the SHIRT sits on: without it the oversized
# tee hangs to mid-thigh and swallows whatever is under it, which is how two
# rounds of skirt-length measurement got thrown away before anyone noticed the
# hem was not the variable.
FITNESS = IDENTITY + (
    # **`(ribbed shirt:1.35)` was here and is gone**, and the removal is the
    # more interesting half of this line. 「リブ柄を指定したがスポーツ着としては
    # 合ってないから」 -- but the rib was also the reason the hem could not be
    # settled. A ribbed knit falls against the body, so it read as a sweater
    # dress when long and as a shirt tucked in when short, and 1.4 drew
    # 「少し服が長すぎる」 while 1.3 drew 「服を中に入れるのは違う」. There was no
    # window between them because the dial was the wrong one.
    #
    # Plain jersey has neither failure, and the hem then went the OTHER way from
    # where two rounds of weight-sweeping were pushing it: 1.45, longer than the
    # 1.4 that had already been called too long. That is what a wrong dial looks
    # like from the far side.
    "(light purple shirt:1.45), (t-shirt:1.45), "
    # 1.45 -> 1.55. 「股を出さずに服で隠すこと」. Third value on this dial and
    # the last: it is the tag that decides where the hem lands, the hem is what
    # covers her, and this is the weight at which it clears the crotch.
    "(oversized shirt:1.55), short sleeves, "
    "(high-waist pants:1.4), (sportswear:1.35), "
    "vocaloid, voiceroid, "
    "(white footwear:1.4), (sneakers:1.45), (high tops:1.3)"
)

# Still ONE garment on the leg, and here the garment is the trousers: ankle-length
# compression leggings ARE the legwear, so they go in this slot rather than
# beside the shorts the way `sporty`'s denim does.
#
# **`(vertical-striped clothes:1.35)` is the side stripe, and it is the one tag
# in this costume that was bought with a hit rate rather than a look.** The line
# arrived unasked on ONE seed of four under `(sportswear:1.35)` alone -- 33f5fd9d,
# 「白のラインが良い！！！！」 -- which is this file's usual warning sign: a value
# the model has no way to hold. Naming the stripe took it to three of four. The
# COLOUR did not come along: the picked pair are purple-lined and the render that
# started it is white-lined. Presence is pinned; hue is not, and nothing here
# pretends otherwise.
#
# The cost is a guard, in `negative()`, because the tag names clothes and not
# trousers -- see there.
FITNESS_LEGWEAR = ("(leggings:1.45), (black leggings:1.4), (skin tight:1.45), "
                   "(vertical-striped clothes:1.35)")

# No hood here either, for SPORTY_HOOD's reason.
FITNESS_HOOD = "(visible hair:1.2), (purple eyes:1.2)"

# The fourth costume, and the only one that keeps the settled costume's coat:
# summer, air-conditioned room, off-duty. 寒いから羽織っている -- the cardigan is
# on her because the room is cold, not because this is a variant of the dress
# costume, so it carries CHARACTER's cardigan/hood/sleeve text VERBATIM rather
# than a respelling. That is what lets a later session widen one of the
# `dressed`-gated splices onto this costume too, if a pose ever wants to: the
# needle would be there to match. None does yet -- see the notes at those
# gates in `positive()`.
#
# Under it: a white oversized tee and dolphin shorts, same slot SPORTY's denim
# and FITNESS's high-waist pants sit in. No footwear tag, unlike either of
# those two -- this costume is barefoot, not shod.
ROOMWEAR = IDENTITY + (
    "(black hooded cardigan:1.45), open cardigan, (rabbit hood:1.55), "
    "animal hood, long sleeves, (drawstring:1.4), "
    "(white shirt:1.4), (t-shirt:1.45), (oversized shirt:1.3), "
    "(dolphin shorts:1.4), (short shorts:1.25), "
    "vocaloid, voiceroid, "
    "(sleeves past wrists:1.3)"
)

# One garment on the leg, LEGWEAR's rule -- here the garment is none.
# LEGWEAR_BAN still bans the second garment by name (socks, thighhighs), and
# `negative()` separately bans the settled costume's own pantyhose by name:
# that costume WEARS one, so the shared negative leaves the plain colour
# unbanned, and this costume does not wear it at all.
ROOMWEAR_LEGWEAR = "(bare legs:1.45), (barefoot:1.35)"

# HOOD, unchanged and reused rather than respelled: the cardigan is here and
# open, so `(hood down:1.25)` names a garment this costume actually has --
# unlike SPORTY_HOOD/FITNESS_HOOD, which drop the line because those two
# costumes have no hood to be down.
ROOMWEAR_HOOD = HOOD

# The costumes that bring shoes of their own. Three gates below are about
# footwear and NONE of them is about being `sporty` -- they were written as
# `costume == "sporty"` when that was the only shod costume, and an equality
# test is exactly the kind of gate a third costume walks past in silence. The
# failure would not have been loud: `stand` would carry two pairs of shoes, and
# the head framings would go back to drawing a sneaker floating in the backdrop.
SHOD = ("sporty", "fitness")

# The three blocks a costume owns. Everything else -- FACE, SURFACE, BODY, THIN,
# every pose and the whole negative -- is shared, which is the claim this split
# is making: what changes between the two is the clothes, not her and not the
# drawing.
COSTUMES = {
    "default": {"character": CHARACTER, "legwear": LEGWEAR, "hood": HOOD},
    "sporty": {"character": SPORTY, "legwear": SPORTY_LEGWEAR, "hood": SPORTY_HOOD},
    "fitness": {"character": FITNESS, "legwear": FITNESS_LEGWEAR,
                "hood": FITNESS_HOOD},
    "roomwear": {"character": ROOMWEAR, "legwear": ROOMWEAR_LEGWEAR,
                 "hood": ROOMWEAR_HOOD},
}

# What each costume does to the negative, in the slots the picked renders were
# drawn in. The rule that put most of these here: a tag that names how cloth
# behaves (skin tight, vertical stripes) goes wherever there is fabric, so it
# needs a guard on every garment it was not meant for -- and that guard
# belongs to the WARDROBE, not to whichever pose first needed it.
COSTUME_NEGATIVE_EDITS = {
    "default": (),
    "sporty": (
        # Denim is blue; the whole-picture tint guard would argue with the
        # clothes. `(blue background:1.5)` stays -- the backdrop is set
        # afterwards by recolor_bg.py and a blue one is still a defect.
        Edit("remove", "(blue tint:1.4), ", stage=S_TINT_RELEASE),
    ),
    "fitness": (
        # Carried, not earned: nothing in this costume is blue, but the picked
        # renders (d218afdc, e8dacf7e) were swept under `sporty` without the
        # guard, and one guard is the size of difference that changes an
        # output. If a blue cast turns up here, this is the line to take back.
        Edit("remove", "(blue tint:1.4), ", stage=S_TINT_RELEASE),
        # The tee knots itself and a knotted tee rides up: no weight on
        # `oversized shirt` could win until the knot was named. A knot is a
        # drawn object, so this works in pass 2 as well (see render-notes).
        Edit("prepend", new="(tied shirt:1.5), (front-tie top:1.5), ",
             stage=S_KNOT),
        # `(skin tight:1.45)` draws the seam it implies; `cameltoe` is that
        # seam's name, and a drawn thing is what a guard reaches. The shirt
        # covering her is the other half and lives in the hem weight.
        Edit("prepend", new="(cameltoe:1.6), ", stage=S_SEAM),
        # 「お腹が見えてるのも not for me」. The provenance tail's 1.35/1.30
        # never did work; `(crop top:1.5)` is the garment name that was
        # missing. `replace_if_present`, deliberately: `swelter` RELEASES
        # these two tags, and a fitness swelter must keep that release
        # rather than have it silently undone here.
        Edit("replace_if_present", ", (midriff:1.35), (navel:1.3)",
             ", (midriff:1.5), (navel:1.45), (crop top:1.5)",
             stage=S_MIDRIFF),
        # The side stripe's tag names CLOTHES, not trousers, so the tee this
        # costume spent three tags keeping plain comes back striped without
        # this. Costume-gated on purpose -- the guard belongs to the wardrobe.
        Edit("append", new=", (striped shirt:1.5)", stage=S_FABRIC),
        # 「シャツが股間で凹むのも望んでいない」 -- `skin tight` again, on the
        # shirt this time. Third property-tag leak in one costume; that is
        # the rule above, not a surprise.
        Edit("append", new=", (taut clothes:1.45), (taut shirt:1.5)",
             stage=S_FABRIC),
    ),
    "roomwear": (
        # The settled costume's own garment, banned by name: the shared
        # negative bans pantyhose DEFECTS (brown, blue...) because LEGWEAR
        # wears one, so the plain colour was never forbidden there. This
        # costume's legs are bare. `(shoes:1.4)` is a partial fix -- `stand`'s
        # positive footwear text is not spliced out for this costume (that
        # needs a matching COSTUME_ONLY declaration in costume_check.py), so
        # the guard argues with a tag it cannot reach.
        Edit("append",
             new=", (pantyhose:1.5), (black pantyhose:1.45), (shoes:1.4)",
             stage=S_BARE_LEGS),
    ),
}
