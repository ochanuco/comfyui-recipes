#!/usr/bin/env python3
"""Yukari's settled recipe, and a seed sweep to check it stays settled.

This is `fb-b` (prompt id 4c012937), chosen after the design was restored from
gl-lounge-555666777 / job 38918ed3. Everything here is the reference's own
vocabulary; the port onto the Hamakaze graph is not part of it.

    uv run scripts/yukari_recipe.py --seeds 6          # sweep fresh seeds
    uv run scripts/yukari_recipe.py --seed 555666777   # the settled render
    uv run scripts/yukari_recipe.py --pose portrait    # head and shoulders
    uv run scripts/yukari_recipe.py --pose peace       # double v, v over eye
    uv run scripts/yukari_recipe.py --pose invite      # patting her lap, one girl

**There are two costumes now, and `default` is still the settled one.** The
second is `sporty` -- grey oversized tee, denim shorts, plain black tights,
white high tops -- and it was added the way it was so that the first one is one
flag away and unchanged: both hang on the same `IDENTITY`, and `--costume
default` builds the same prompt and the same graph, tag for tag, as the commit
before it existed. That was checked across every pose rather than assumed.

    uv run scripts/yukari_recipe.py --pose hype --costume sporty --seeds 6

What a costume owns is three blocks -- character, legwear, hood -- and nothing
else. FACE, SURFACE, BODY, THIN, every pose and the whole negative are shared,
which is the claim: what changes is the clothes, not her and not the drawing.
Two things follow, and both are in the code rather than in this paragraph:

- The garment splices in `positive()` (`open cardigan`, `(drawstring:1.4)`,
  `(oversized shirt:1.3)`) name tags only the settled costume has, so they are
  gated on the costume and go through `_splice`, which ASSERTS. A splice that
  matches nothing does nothing and says nothing; with two costumes in the file
  that stopped being a hypothetical.
- Three guards are released under `sporty` and only there: `situp`'s
  `(sportswear:1.45), (gym uniform:1.4)` (that costume IS a gym kit -- the
  arched-back guard beside it is about her back and stays), `stand`'s
  `(white footwear:1.45), (red footwear:1.4)` (its shoes are white), and
  `(blue tint:1.4)` (denim is blue). `(blue background:1.5)` is NOT released:
  the backdrop is set afterwards by recolor_bg.py and a blue one in the render
  is still a defect.

Sweep cheap, then print big. The first pass does not change when `--hires` is
added -- same seed, same latent, same picture -- so a seed picked at the sweep
size comes back as the same drawing, only with detail the small render had no
room for:

    uv run scripts/yukari_recipe.py --pose sip --seeds 8              # find one
    uv run scripts/yukari_recipe.py --pose sip --seed 999999999 \
        --hires 2048                                                  # keep it

Which also means a render the sweep did not produce is not waiting at 2048.
The arc that 1029384756 refuses to draw at 1024 is refused there too: the
second pass redraws what the first one decided, it does not reconsider it.

**The leg is ONE garment, and that is deliberate across every pose.** A single
pantyhose, purple at the thigh running to black at the ankle, with the second
garment banned by name in the negative. Pale socks over grey tights was this
repo's own design and it is retired -- `LEGWEAR_LAYERED` keeps its text and its
measurements, and the note above `LEGWEAR` says what broke it. So `--pose peace`
no longer reproduces 9d24700e pixel-for-pixel, and neither does anything else
from the layered lineage; the `pick/yk-recipe` tag still points at the commit
that does.

Settled on the prone pose and then kept global rather than split per pose,
because it is the costume and not a framing: the palette is one palette. If a
future pose wants the layering back, name `LEGWEAR_LAYERED` in a splice and take
`LEGWEAR_BAN` back out of that pose's negative -- both halves, or the guards
will delete the garment the splice just asked for.

Then set the backdrop, which the prompt does not control -- it landed on
#d0d0c0, #a0a0a0 and #909090 across three renders whose only difference was two
leg-tag weights:

    uv run scripts/recolor_bg.py out/yk-peace-555666777_00001_.png --color '#d0d0c0'

Three findings are baked into the constants and should not be quietly undone:

- **`(realistic:1.1)` belongs in the NEGATIVE.** The Hamakaze pipeline had it
  positive at 1.3, and that single flip did more damage to her look than any
  other change. Same for shading: flat colour with soft shading, and
  (heavy shading), (detailed shading) held out.
- **The rabbit hood stays on her and goes down.** (rabbit hood:1.55) with
  (hood down:1.5), (hood behind head:1.3) and (hood up:1.5) negative. Deleting
  the hood to uncover the hair costs more identity than it buys.
- **1024x1536 is the ceiling for full body.** 1280x1920 improves the stroke-to-
  figure ratio from 1.91 to 1.53 (in 1536-equivalent pixels) but drew a second
  figure in both renders that tried it, with (solo:1.5) already in the prompt.

And one non-finding, recorded so it is not retried: **the line width does not
respond to tags.** Median stroke is 1.91px in the 1024x1024 portrait, at
1024x1280, at 1024x1536, and with (thin lineart:1.3), (fine lines:1.25),
(delicate lines:1.2) added. Full-body line reads heavier only because the head is
smaller, not because the stroke changed.

Those thin-line tags are kept anyway, because `fb-b` is the render that was
accepted and they are in it. They do change the image -- just not the thing they
are named for. Dropping them on the grounds that the measurement came back null
would quietly ship a different picture than the one that was chosen.
"""

from __future__ import annotations

import argparse
import json
import urllib.request

from comfy_host import DEFAULT_HOST, DEFAULT_PORT

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

FACE = (
    # 「毛量は多いが長さは均一がいいかな」, and the weight is bracketed from
    # ABOVE: 1.45 was called ほんの少し多い and 1.25/1.15 were rendered in the
    # same round, so anything right on this axis is at or under 1.35. The bare
    # `eyelashes` this replaces had never been swept at all.
    "(tareme:1.3), (large eyes:1.3), 2000s (style), "
    "(eyelashes:1.3), (thick eyelashes:1.35), "
    "(large iris:1.25), thin eyebrows, closed mouth, small mouth, "
    "looking at viewer"
)

SURFACE = (
    # `sticker` is out. It draws literal stickers -- a rabbit decal on her cheek,
    # rabbit patches, loose cut-outs -- and, measured over seven seeds, it was
    # also the source of the second figure: with it, two of seven had a chibi
    # clone in frame; without it, none of seven did.
    #
    # (white outline:1.6), outline stay. They are the die-cut edge; `sticker`
    # was the half that drew actual stickers. The edge survives its removal.
    #
    # It does NOT remove all decoration. Patterned rabbits on the garment,
    # background streaks and one piebald coat came through anyway, so there is
    # at least one more source.
    "(flat color:1.3), (simple background:1.3), (grey background:1.2), "
    "(white outline:1.6), outline, (soft shading:1.3), smooth shading"
)

BODY = (
    "(toned legs:1.2), (wide hips:1.3), (thick thighs:1.35), (narrow waist:1.25), "
    "(petite:1.2), (pale skin:1.25)"
)

# Reset to b1258b0c: hood down at 1.25, not pinned behind her head.
#
# The alternative -- (hood down:1.5), (hood behind head:1.3) -- was measured and
# is not better: unpinning changed neither the colour count nor the clutter, and
# pinning it back did not recover anything. This is the picked render's value.
HOOD = "(hood down:1.25), (visible hair:1.2), (purple eyes:1.2)"

# Measured to do nothing to stroke width; present because fb-b carried them.
THIN = "(thin lineart:1.3), (fine lines:1.25), (delicate lines:1.2)"

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
}


def _splice(text: str, old: str, new: str, when: bool = True) -> str:
    """`str.replace`, except that a needle which is not there is an error.

    Every splice in `positive()` is a string replacement against a block, and a
    replacement that matches nothing does nothing AND SAYS NOTHING. This file
    has a rule about that failure because it has paid for it twice. With two
    costumes in the file the odds of a needle going missing went up, so the
    quiet version is gone.

    `when=False` skips the splice outright, which is the honest way to say "this
    costume has no such garment" -- as against letting the replacement run and
    match nothing, which looks identical in the output and means the opposite.
    """
    if not when:
        return text
    assert old in text, f"splice needle absent: {old!r}"
    return text.replace(old, new)


def pose_block(pose: str, costume: str = "default") -> str:
    """The pose's own tags, after the costume has had its say about them.

    The poses were all written for the settled costume and one of them names its
    shoes. `build()` goes through here too: the second pass is spliced in by
    matching the pose block inside the finished prompt, so both callers have to
    be looking at the same text or that splice matches nothing.
    """
    text = POSES[pose]
    if pose == "stand" and costume in SHOD:
        # The only pose that names footwear, and it names the settled costume's
        # black high tops. SPORTY brings white sneakers; both in one prompt is
        # asking for two pairs of shoes.
        text = _splice(text, "(black footwear:1.35), (high tops:1.35), ", "")
    return text


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
        "(solo:1.5), (sitting:1.45), (soles:1.4), (foot focus:1.35), "
        "(foreshortening:1.3), (knee up:1.25), (leaning back:1.25), (couch:1.2), "
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
    # `(>_<:1.0)` at `dizzy`'s weight and not a digit higher. Two priors, both
    # about weight rather than the symbol: `(@_@:1.45)` drew literal black
    # spirals on the whites and 1.0 is what was picked, and `swelter` swept
    # `(>_<:1.4)` head to head against `(closed eyes:1.4)` and the symbol LOST.
    # 93.7k posts, more than `@_@`, so the tag is real -- it is 1.4 that is not.
    # Swept here at 1.0 and 1.3, and 1.0 is the pick.
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
        "(open mouth:1.5), (>_<:1.0), (wavy mouth:1.4), (looking up:1.35), "
        "(heavy breathing:1.45), "
        "(flying sweatdrops:1.35), (sweat:1.3), "
        "(full body:1.45), (short dress:1.35)"
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
}

# The portrait needs a square-ish frame: (portrait:1.5) alone lost to the canvas
# at 1024x1280 and drew down to the thighs. 1024x1024 held it.
SIZES = {"lounge": (1024, 1536), "portrait": (1024, 1024),
         # Portrait's framing, so portrait's canvas.
         "allnighter": (1024, 1024),
         # `allnighter`'s crop, so `allnighter`'s square.
         "dizzy": (1024, 1024),
         # Every seated full body in this file is 1024x1536 and none of them
         # has argued with it. NOT in HEAD_FRAMINGS: this one wears the legwear.
         "allnighter_full": (1024, 1536),
         "peace": (1024, 1536),
         "chair": (1024, 1024),
         # Same square as the render it is built on.
         "boss": (1024, 1024),
         "yawn": (1024, 1536), "fall": (1024, 1536),
         "coy": (1024, 1536),
         "lap": (1024, 1536),
         "invite": (1024, 1536),
         "hunt": (1024, 1536), "crouch": (1024, 1536),
         # A side-on squat is about as wide as it is tall. At 1024x1536 the same
         # block drew her small in a tall empty frame; the square fills.
         "sip": (1024, 1024),
         # Seated and seen from above: head, back and folded legs fill a square.
         "nape": (1024, 1024),
         # The first landscape canvas here, and a body on the floor is what
         # earns it. Measured against the other two on 555666777:
         #
         #   1024x1024  cropped her at the frame edges, broke the die-cut
         #              outline, and doubled the relative stroke to 3.92 per
         #              1000px -- the figure is drawn big, so the line is heavy
         #              against her rather than against the canvas.
         #   1024x1536  drew her diagonally with the hips raised toward the top
         #              of the frame. That is the rear-forward composition this
         #              project has thrown work away over, arriving from the
         #              canvas rather than from any tag.
         #   1536x1024  whole figure, outline intact, 1.94 per 1000px.
         #
         # It does not violate the docstring's "1024x1536 is the ceiling for
         # full body". That ceiling is a pixel count -- 1536x1024 is the same
         # 1.57M pixels turned on its side, not the 2.46M that drew a second
         # figure -- and none of six seeds here drew one.
         "prone": (1536, 1024),
         # `prone`'s canvas, for `prone`'s reason: a horizontal body, and a
         # couch is horizontal furniture. The measurements that chose 1536x1024
         # over the two portrait canvases are in the note above.
         "flop": (1536, 1024),
         # 768 wide, and the width is the whole point.
         #
         # `(wide shot:1.3)` is what pulls the camera back far enough to fit the
         # figure and the shoes -- and at 1024 it also buys a SECOND FIGURE,
         # every time. Two guard sets that this file already relies on elsewhere
         # (`lap`'s, naming the person; `nape`'s, naming the layout) did not move
         # it at the weights they carry there. Narrowing the frame did, on four
         # seeds of four: give the model room beside her and it puts someone in
         # it.
         #
         # 1024x1536 is not the fallback it looks like. Its render was better --
         # the shoes were the approved pair and the narrower canvas redraws them
         # -- but keeping it meant cutting one figure out of two, and a crop
         # while the prompt is still being tuned is banned (see CLAUDE.md). A
         # picture that needs a crop is a prompt that has not solved the problem.
         # 832x1664, chosen over 768x1536 and 896x1792 by eye. 1.38M pixels,
         # under the ceiling, and still narrow enough that nobody else fits
         # beside her -- which is the constraint the width is really carrying.
         #
         # It is NOT the same picture at a bigger size. Each of these three
         # canvases frames her differently: the first pass is where the
         # composition is decided, so its size is a composition choice and the
         # pose has to be re-picked when it changes.
         # Every seated whole figure in this file is 1024x1536 and this one has
         # no reason to argue with it yet: the extended leg goes into depth
         # rather than across the frame, so it buys no extra width. Untested.
         "kick": (1024, 1536),
         # A body on the floor, which is what earned `prone` and `flop` the
         # landscape canvas; the measurements are in the note above `prone`.
         # She is longer here than in either of them -- knees up, elbows out --
         # so the width is doing the same job for the same reason.
         "situp": (1536, 1024),
         "stand": (832, 1664),
         # `stand`'s canvas, and reached the same way `stand` reached it.
         #
         # It was 1024x1536 for one sweep, on the reasoning that arms out to the
         # sides need width. They do not need it from the frame: at 1024 wide
         # three of six seeds came back with a second figure, and at 832 with
         # nothing else changed it was one of six. Same six seeds, headcount.py
         # both times.
         #
         # Not a clean result and it should not be read as one -- 3/6 against
         # 5/6 is not a difference six seeds can settle, and the one render the
         # narrow canvas lost (555666777) is one the wide canvas had. What
         # decided it is that this is the SAME lever `stand` was fixed with, for
         # the same defect: width beside her is room for someone else to stand.
         # The picked render (28e243ec, seed 1886970040) is drawn at this size.
         "hype": (832, 1664),
         # `hype`'s frame, and taken rather than re-derived: this pose has its
         # arms UP, not out, so it wants width even less than that one did, and
         # the second-figure lesson behind 832 applies to any standing full body
         # in this file until something shows otherwise.
         "roar": (832, 1664),
         # A squat is wide and short where a standing figure is narrow and tall,
         # and `sip` already squats at this square. The second-figure argument
         # for 832 is about width BESIDE her; this pose fills the width itself.
         "pounce": (1024, 1024),
         # `roar` reaching upward, so `roar`'s frame -- and this is the pose that
         # needs the height of it most.
         "loom": (832, 1664),
         # `portrait`'s crop, so `portrait`'s square. (portrait:1.5) alone lost
         # to the canvas at 1024x1280 and drew down to the thighs.
         "snarl": (1024, 1024),
         # A standing full body, so `stand`'s frame and `stand`'s reason. The
         # cost is that the cup is small in it; if the vessel is what fails, a
         # square crop is the arm to try before the tags are touched.
         "straw": (832, 1664),
         # A seated full body, so the frame every seated full body in this
         # file uses. The roll is small in it and that was accepted: the arm
         # that made the roll bigger is the one that lost its shoes.
         "snack": (1024, 1536),
         # A standing full body, so `stand`'s frame -- and `straw`'s, which is
         # the closer sibling: one figure, arms down, an object in her hands.
         "hoops": (832, 1664),
         # Square, and the only square full body in the file. Legs forward and
         # arms back put the figure's long axis on the DIAGONAL, so neither the
         # portrait frames nor the landscape ones fit it: `snack`'s 1024x1536
         # runs the feet into the edge and `flop`'s 1536x1024 leaves half the
         # frame empty beside a seated girl. The reference is square too.
         "winded": (1152, 1152),
         # Landscape, and the only pose here that is wide for the sake of an
         # OBJECT rather than a body: a road bike seen from the side is longer
         # than she is tall. `flop`, `prone` and `situp` already use this frame.
         #
         # It spends the second-figure protection that 832 buys the standing
         # poses. That is knowingly spent -- there is no way to photograph a
         # bicycle side-on in a narrow frame -- and it is the other thing to
         # watch for in the sweep.
         "ride": (1536, 1024),
         # `flop` and `prone`'s frame: a body lying down is wide and short, and
         # from directly above that is the shape of the whole picture.
         "swelter": (1536, 1024),
         # `portrait`'s square, like `snarl`. The crop inside it is wider --
         # `upper body` rather than `close-up` -- and that is a tag decision,
         # not a canvas one; the frame is the settled one for a head.
         "tehe": (1024, 1024)}

# Framings that crop above the legs. They drop LEGWEAR, BODY (bar `pale skin`)
# and THIN from the positive and the legwear ban from the negative -- naming a
# garment that is out of frame is what invites it back into the frame.
HEAD_FRAMINGS = ("portrait", "allnighter", "dizzy", "snarl", "tehe")

NEGATIVE = (
    # The other half of the lash pair above: `thick eyelashes` is the 毛量 and
    # this is the 長さは均一. In front, because every guard this file kept went
    # at the front and token order changes the encoding.
    #
    # NOT ISOLATED. K/Kn and qbK/qbKn were rendered to measure whether this tag
    # does anything at all -- the recipe's own record is that a guard deletes
    # drawn objects and fails on properties, and lash length is nearer a
    # property. Those pairs were never judged; the picked render carries the
    # guard, so the guard is in. If a later session finds it inert, this is the
    # line to delete and there is no other cost to deleting it.
    "(long eyelashes:1.35), "
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text, (disembodied eye:1.4), "
    "(brown legwear:1.5), brown thighhighs, brown pantyhose, (fishnet:1.4), "
    "(latex:1.45), (rubber:1.45), (leather legwear:1.45), "
    "(upskirt:1.4), panties, (from below:1.35), "
    "(blue legwear:1.5), (blue background:1.5), (blue tint:1.4), "
    # (opaque pantyhose:1.5) used to live here, from when the tights were meant
    # to be sheer. It is the direct opposite of the current ask and had to go.
    #
    # So did (thighhighs:1.4), (white legwear:1.4), which forbade the socks
    # outright -- they were added while abandoning the layering and are the
    # reason it could not come back.
    #
    # The sheer guard names the dress and nothing else. A four-tag block of
    # (see-through), (see-through clothes), (transparent clothing),
    # (sheer clothes) went in with it and the palette came back flat and dark,
    # which is the same shape as the duplicate-guard block that wrecked the
    # colours once before.
    # (thighhighs:1.3) was tried here to stop the socks creeping back to full
    # length. It removed them outright: the model does not hold thighhighs and
    # over-kneehighs apart, whatever the danbooru wiki separates. Length has to
    # come from the positive tag alone.
    # All four asymmetry guards, as gl-lounge-555666777 carried them. Rebuilding
    # the legwear block had left only the first.
    #
    # Judged over four seeds, not one: restoring them raised the visible tights
    # band from a 7.7% worst case to 23.0%, so socks-over-tights now reads on
    # every seed tried rather than most of them. Worst case is the number that
    # matters here -- the mean barely moved.
    #
    # They do NOT fix left/right symmetry, which is what they were restored for:
    # mean leg difference went 11.0 -> 16.5. By eye both legs are correctly
    # layered in all four, so that measure is reading pose and overlap, not
    # sock length. It should not be used to judge legwear again.
    #
    # Dropping (over-kneehighs:1.4) alongside was tried and is much worse --
    # worst-case leg difference 73.9, with one sock nearly gone at 737373737.
    # Two competing length tags are apparently holding each other in place.
    # The skirt pair stops the one-piece being drawn as a skirt with a frill
    # under it. It is the riskiest thing in this negative: on its own, before
    # the dress weight went to 1.45, it deleted the whole lower garment on one
    # seed of two. It is here because ns-1117511306 (prompt 7d231c4f), the
    # render this recipe is aimed at, has it -- and in this position.
    "(mismatched legwear:1.5), (skirt:1.35), (pleated skirt:1.4), "
    "(single thighhigh:1.5), "
    "(asymmetrical legwear:1.45), (uneven legwear:1.4), "
    "(petticoat:1.35), (layered skirt:1.25), "
    "(see-through dress:1.45), (transparent clothing:1.3), "
    "(hood up:1.5), (hood over head:1.4), "
    "(impasto:1.25), (painterly:1.25), (oil painting (medium):1.2), "
    "(heavy shading:1.2), (detailed shading:1.2), (realistic:1.1), "
    "(huge breasts:1.4), (large breasts:1.25), cleavage"
    # Tail, and the target render's own order. These three measured nothing --
    # the hem did not move with them in or out -- and are kept for identity with
    # 7d231c4f rather than for effect.
    ", (cropped jacket:1.45), (midriff:1.35), (navel:1.3)"
)

# Fixed list rather than random: a sweep that cannot be repeated cannot be used
# to show that a later change did or did not break something.
SWEEP_SEEDS = [555666777, 111222333, 1886970040, 737373737, 2557902837, 3409564303]


def negative(pose: str, costume: str = "default") -> str:
    """The negative, plus the legwear ban every full-figure pose now carries."""
    text = _negative_base(pose)
    if costume in ("sporty", "fitness"):
        # One guard released. `(blue tint:1.4)` was aimed at a cast over the
        # whole picture; `sporty` is asking for denim, which is blue, so the
        # guard would be arguing with the clothes.
        #
        # **`fitness` is here on inheritance, not on that reason.** Nothing in
        # that costume is blue -- black leggings, a light purple tee, white
        # shoes -- so by the argument above it should keep the guard. It is
        # released because the renders that were picked (d218afdc, e8dacf7e)
        # were swept under `sporty` and drawn without it, and one guard is
        # exactly the size of difference this file has watched change an
        # output. Same shape as `straw` carrying `swelter`'s paint guard:
        # carried rather than earned, and written down as such so that the day
        # a blue cast turns up there is a line to take back.
        #
        # `(blue background:1.5)` STAYS. The backdrop is not prompt-stable here
        # and is set afterwards with recolor_bg.py, so a blue one in the render
        # is a defect even when the delivered picture is going to be cyan.
        text = _splice(text, "(blue tint:1.4), ", "")
    # The head framings crop above the legs, and a guard against a garment that
    # is out of frame is tokens spent on nothing.
    if pose == "swelter":
        # 「シャツも少しお腹が見えてしまってる感じで」, and this guard is the thing
        # in the way. Released at a cost this file already put at zero: the
        # note on that tail reads "These three measured nothing -- the hem did
        # not move with them in or out -- and are kept for identity with
        # 7d231c4f rather than for effect."
        #
        # `(cropped jacket:1.45)` STAYS, and is the reason this is a splice of
        # two tags rather than of the tail. That one names a different garment,
        # and the garment is a contract. `(upskirt:1.4), panties` stay too --
        # the undignified part of this pose is the posture, and it is not this
        # recipe's job to help it anywhere else.
        text = _splice(text, ", (midriff:1.35), (navel:1.3)", "")
        # 「効果線は削除して」. **There is no tag in the positive that asks for
        # them.** The 微動 round already took `(motion lines:1.45)` out of the
        # pose block, and the lines came back anyway: `flailing` and `screaming`
        # are drawn with them by default, so the model is supplying the
        # convention on its own.
        #
        # That makes this the OPPOSITE of the cases this file keeps losing on.
        # `(long torso:1.4)` in the negative moved a proportion by nothing, and
        # the two-layer leg had no tag to outvote -- both times the negative was
        # being asked about something that is not a drawn object. Speed lines
        # are a drawn object with a name, which is the kind of thing a guard
        # has always been able to take out of this backdrop.
        #
        # Three names because the model does not treat them as one: `motion
        # lines` is the general tag, `speed lines` the dense parallel kind, and
        # `emphasis lines` the burst behind a face -- and it is the burst that
        # was in the picture.
        text += ", (motion lines:1.5), (speed lines:1.5), (emphasis lines:1.45)"
    if pose == "tehe":
        # And the tongue, which nothing in the positive asks for any more. The
        # emoticon that drew it is gone; this is here because a wink and a small
        # mouth are what the model was drawing one FROM. A tongue is a drawn
        # object with a name, which is the case where a guard works -- same
        # reasoning as `swelter`'s speed lines.
        text = "(tongue:1.5), (tongue out:1.5), " + text
        # ...and the hands go in FRONT of the tongue, because that is the order
        # the sweep ran in. Two prepends in the other order reproduced every
        # node but this one.
        # **A hand guard, in PASS 1, and that placement is the point.** It lived
        # in `HIRES_NEGATIVE` first, which is invisible at 1024 -- and 1024 is
        # where forty renders of this hand were judged, so a sweep would have
        # been looking at a prompt the print does not use. It is in both passes
        # now: this one, and the pass-2 copy below.
        #
        # 「指の形がおかしいのと、数（手の甲の指の根元の突起の数）がおかしい」.
        # `extra digits` is the one that names the second half -- four knuckles
        # drawn for a fist showing two folded fingers -- and it is the term the
        # weight is on.
        #
        # PREPENDED, not appended, and that is not cosmetic. The sweep these
        # were judged on put them at the front of the negative, and this file
        # has already recorded that token order changes the encoding -- the
        # がおー parts are split into two fragments for exactly that reason.
        # Appending reproduced every other node of d2106e99 and differed here,
        # which is the whole check catching a one-line drift.
        text = HAND_BAN + text
    if pose == "hoops":
        # `tehe`'s guard on `tehe`'s reasoning, taken up front rather than
        # after the fact: two hands closed around an object is the same
        # accident, and that pose's finding was that a pass-2-only guard leaves
        # the 1024 sweep judging a prompt the print will not use.
        #
        # PREPENDED, for the reason recorded above -- the sweep this reproduces
        # put it at the front, and token order changes the encoding here.
        text = HAND_BAN + text
    if costume == "fitness":
        # **The tee knots itself, and a knotted tee rides up at the back.** This
        # is the guard that ended three rounds of sweeping the hem: the hem was
        # being pulled up by a knot, so no weight on `oversized shirt` could
        # win. 「服で隠す」 was unreachable until the knot was named.
        #
        # `tied_shirt` 21k, `front-tie_top` 52k. A knot is a DRAWN OBJECT, which
        # is why this works in the second pass as well -- see the entry in the
        # notes: it removed a knot pass 1 had already drawn, without moving the
        # composition, which is the sharpest reading this file has of where the
        # late pass's reach ends.
        text = "(tied shirt:1.5), (front-tie top:1.5), " + text
    if pose == "hoops":
        # Arms AND legs by name. `extra limbs` is in NEGATIVE unweighted and did
        # not stop either: a third arm crossing her torso at 2048, and a fourth
        # leg on a print. The weighted names are what worked, the same way
        # `(extra arms:1.5)` had to be spelled out beside it.
        text = "(extra arms:1.5), (extra legs:1.5), (extra limbs:1.5), " + text
    if costume == "fitness":
        # 「股を出さずに」. `(skin tight:1.45)` draws the seam it implies, and
        # `cameltoe` 125k is that seam's name. A drawn thing, so a guard reaches
        # it; the SHIRT covering her is the other half and lives in the hem.
        #
        # Prepended last so the three land in the order the picked render was
        # drawn in -- seam, limbs, knot. Token order changes the encoding here
        # and this file has caught a one-line drift by checking it before.
        text = "(cameltoe:1.6), " + text
    if pose == "winded":
        # The bend to delete, and the limbs that a girl propped on both arms
        # grows. `knees_up` 81k is how the legs get straight: nothing in the
        # positive says "extended" in a count that moves a picture, so the
        # lever is subtraction. The limb trio is `hoops`'s, and it is here for
        # a sharper reason than there -- two arms angled back behind the torso
        # is the arrangement that invites a third.
        #
        # Prepended AFTER the seam guard, which means they land in front of it.
        # That is the order the picked render was drawn in and this file has
        # caught a one-line drift by checking it; `hoops`'s comment above claims
        # the last word for the seam and no longer has it on this pose.
        text = "(knees up:1.5), " + text
        text = "(extra arms:1.5), (extra legs:1.5), (extra limbs:1.5), " + text
    if costume == "fitness" and ", (midriff:1.35), (navel:1.3)" in text:
        # 「お腹が見えてるのも not for me」. The tail this replaces carries its own
        # confession -- "these three measured nothing... kept for identity with
        # 7d231c4f rather than for effect" -- and 1.35/1.30 is what that looks
        # like from the other side: weights placed for provenance, asked to do
        # work for the first time and unable to. `(crop top:1.5)` 282k is the
        # garment name that was missing; the other two are the same tags with
        # weights that mean it.
        #
        # Costume-gated, because it is this costume's shirt that rides up: a
        # plain tee over high-waist leggings has a hem with nothing to sit on.
        #
        # The `in text` test is not defensive coding, it is `swelter`: that pose
        # RELEASES these two tags a few lines above, deliberately, and a fitness
        # `swelter` must keep that release rather than have it silently undone
        # here. `_splice` would assert instead, which would be the wrong answer
        # to a legitimate combination.
        text = text.replace(", (midriff:1.35), (navel:1.3)",
                            ", (midriff:1.5), (navel:1.45), (crop top:1.5)")
    if pose in HEAD_FRAMINGS:
        return text
    text = text + ", " + LEGWEAR_BAN
    if costume == "fitness":
        # **The stripe tag names CLOTHES, not trousers.** `vertical-striped
        # clothes` is 64k and does not know which garment was meant, so the tee
        # this costume spent three tags keeping plain comes back striped. Same
        # shape as `snack`'s watermelon: a pattern tag with no garment attached
        # goes wherever there is fabric.
        #
        # Gated on the COSTUME, which is the correction this one forced.
        # `(logo:1.4), (print:1.35)` sit in `_negative_base` under `stand` and
        # nowhere else, so every other pose is unguarded against a print -- the
        # guard was put where a pose needed it instead of where the wardrobe
        # does. This is the same mistake not repeated.
        #
        # AFTER the legwear ban, because that is where the sweep put it. The
        # arm this reproduces appended to a finished negative, and this file has
        # already recorded that token order changes the encoding.
        text = text + ", (striped shirt:1.5)"
        # 「シャツが股間で凹むのも望んでいない」 -- the hem pulling into a V between
        # her legs. `(skin tight:1.45)` is in this costume's LEGWEAR slot and
        # that slot does not contain it: it is a property tag with no garment
        # attached, so it goes wherever there is fabric. **Third time in one
        # costume**, after `vertical-striped clothes` striping the tee and
        # `snack`'s watermelon, which stops it being a surprise and makes it the
        # rule: a tag that names how cloth behaves needs a guard on every
        # garment it was not meant for.
        #
        # `taut_clothes` 21k and `taut_shirt` 8.5k, after the stripe guard,
        # which is the order the picked renders were drawn in.
        text = text + ", (taut clothes:1.45), (taut shirt:1.5)"
    if pose == "situp":
        # The exercise brings its own wardrobe and its own room. Three tags,
        # kept short on purpose: this file has twice watched a long guard stack
        # flatten the palette, and the costume only needs the gym kept out of
        # it, not argued with.
        # `(yoga mat:1.3)` was here and is deliberately gone. The guard was
        # written against the wardrobe -- an exercise scene is the strongest
        # pull off this costume anything here has asked for -- but a mat is
        # FLOOR, not clothing, and it was the one thing in the picture saying
        # the scene is exercise. Banning it helped take 腹筋要素 to zero. The
        # two clothing tags stay; they are what the guard was actually for.
        # Released under `sporty`: that costume IS a casual gym kit, and a
        # guard against the wardrobe would be a guard against the clothes. The
        # posture guard below is about her back, not her clothes, and stays.
        if costume == "default":
            text += ", (sportswear:1.45), (gym uniform:1.4)"
        # 猫背's opposite, and the posture this model volunteers for a girl on
        # her back. `stand` pays a positive tag to GET this arch; here it is
        # the whole defect. Naming the shape in the positive without forbidding
        # its opposite is half a lever.
        text += ", (arched back:1.4), (bridge (pose):1.3)"
    if pose == "stand" and costume == "default":
        # Gated on the costume: `sporty`'s shoes ARE white, so this line would
        # forbid the footwear that costume names.
        #
        # After the ban, not before it: this is the tail of the negative that
        # a5c494ef was drawn with, verified against its own history rather than
        # rebuilt from memory.
        text += ", (white footwear:1.45), (red footwear:1.4)"
    return text


def _negative_base(pose: str) -> str:
    """The negative, with the poses that need a different one handled here."""
    if pose == "nape":
        # Two guards, both earned by this pose specifically.
        #
        # `from behind` invites a turnaround sheet, and while the composition
        # words alone did not save `close-up`, the pose no longer uses it and
        # they cost nothing here.
        #
        # The exposure guard is the load-bearing one. `nape of neck` reads to
        # the model as skin to uncover rather than a place to look, and it took
        # the coat off entirely in three renders of four. What it must NOT
        # forbid is the coat slipping -- (off-shoulder) and (bare shoulders)
        # were in this list first and banned the exact look the pose is for.
        #
        # In front of NEGATIVE, not appended: that is the order the approved
        # render was drawn in, and token order changes the encoding.
        return (
            "(character sheet:1.4), (multiple views:1.4), reference sheet, "
            "turnaround, (undressing:1.4), topless, (bare back:1.3), "
        ) + NEGATIVE
    if pose == "boss":
        # `(mature female:1.35)` brings a fuller chest with it, the same way it
        # brought a longer dress -- one tag, two costs, and both of them found
        # by looking upstream rather than at the thing that changed.
        #
        # The guard for it is already in NEGATIVE at 1.25 and was simply being
        # outvoted, so it gets the weight instead of a neighbour: this recipe
        # has wrecked its palette twice by stacking duplicate guards, once with
        # five of them and once with four. Raising the one that is already
        # there costs nothing and no tag is added.
        #
        # Measured against two alternatives, both of which also worked and both
        # of which cost more: easing `mature female` to 1.15 gives back some of
        # the adult read this pose exists for, and `(small breasts:1.35)` in the
        # positive grows the block by a tag and lands flatter than asked.
        #
        # And no buttons. Her dress has none -- ribbed front, ribbon and beads,
        # and that is all -- but nothing in the prompt asks for them either;
        # they arrive from the cardigan, or from the garment being read as a
        # shirt dress. Nothing to substitute, so this is a guard, and it is one
        # guard on purpose.
        #
        # Measured at one, two and four. All three remove the buttons. Two and
        # four also drew a rabbit silhouette onto the chair back on 979797979 --
        # the same backdrop intruder this pose's ancestors fought, arriving with
        # the stack rather than with the tag. Third time guard-stacking has cost
        # something here, and the first time the cost was an intruder rather
        # than the palette.
        #
        # In front of NEGATIVE, which is where `nape` puts its own and the order
        # the approved render was drawn in.
        return "(buttons:1.4), " + NEGATIVE.replace(
            "(large breasts:1.25)", "(large breasts:1.5)")
    if pose == "stand":
        # 「靴に柄はいらない」. Naming a shoe drew one and it arrived with a pink
        # butterfly decal on the outer side. Three tags, and they are three
        # rather than one because `(logo)` and `(print)` are the generic pair
        # and the motif itself needed naming to go: with only the generic two
        # the decal went but the sole came back magenta.
        #
        # The ear-like high collar is the part that is WANTED and it survives
        # all three.
        #
        # The pale sole is the second thing the shoe arrives with, and it is
        # guarded rather than described because describing it did not work:
        # `(black sole:1.35)` in the positive left a white midsole and added a
        # red flash. Two guards, and the shoe that came out is black to the
        # ground.
        #
        # Five stand-only guards is more than this file likes, and the rule they
        # look like they are breaking is a real one -- stacking guards at ONE
        # defect has wrecked the palette here twice. These point at three
        # separate things: a decal, a logo, and a colour. Measured together on
        # 1886970040 with the whole list present.
        # `(buttons:1.4)` in front, which is where `boss` puts its own copy and
        # the order this was measured in. Her dress has no buttons -- ribbed
        # front, ribbon and beads, and that is all -- and nothing in the prompt
        # asks for any; they arrive from the cardigan being read as a shirt.
        # There is nothing to substitute, so it is a guard, and `boss` already
        # established that one guard is the whole fix.
        #
        # The sole guards are NOT here. They go after the legwear ban -- see
        # `negative()` -- because that is the order the picked render was drawn
        # in, and this file has already found that token order changes what
        # comes out.
        return ("(buttons:1.4), " + NEGATIVE
                + ", (butterfly:1.5), (logo:1.4), (print:1.35)")
    if pose != "lap":
        return NEGATIVE
    # A head resting in her lap looks up at her, so the guard against low angles
    # is fighting the shot rather than protecting it. (upskirt:1.4) and panties
    # stay -- those are about what the camera sees, not where it sits.
    text = NEGATIVE.replace("(from below:1.35), ", "")
    assert "from below" not in text
    # And the second person has to be named to be kept out, since the pose is
    # about someone who is not in frame.
    return text + ", (2girls:1.6), (multiple girls:1.6), (duplicate:1.55), (another person:1.5)"


# The poses whose finish is 174ce1dc's. It is TWO things -- the pass-2 paint
# guard in HIRES_NEGATIVE, and the removal of THIN -- and a pose that got one
# half without the other is precisely the failure the `straw` entry down there
# warns about. Named here so that adding a third pose to the finish is one edit
# in one place rather than two edits five hundred lines apart.
PAINT_FINISH = ("straw", "snack")


def positive(pose: str, costume: str = "default") -> str:
    # The legwear, body and thin-line blocks belong to whole-figure framings;
    # the portrait crops above them and naming what is out of frame is what
    # invites it back in.
    full_figure = pose not in HEAD_FRAMINGS
    blocks = COSTUMES[costume]
    # The garment splices further down name tags that only the settled costume
    # has -- `open cardigan`, `(drawstring:1.4)`, `(oversized shirt:1.3)`. Under
    # any other costume the needle is absent, and a splice that matches nothing
    # does nothing and reports nothing. So they are gated on the costume here
    # and asserted in `_splice`, rather than left to miss quietly.
    dressed = costume == "default"
    # A yawn, a shout and a vacant stare all need the mouth open; FACE closes it
    # by default. `allnighter` briefly took `small mouth` out too, for the width
    # of an 「イー」 mouth; that mouth is gone and so is the departure.
    # `kick` is here because its expression moved to pass 1. While the
    # expression lived in `HIRES_POSITIVE`, `build()` stripped `closed mouth`
    # from the second pass only and this list was deliberately not touched --
    # membership here would have opened the mouth in the pass that picks the
    # composition too. That pass now carries the expression, so the departure is
    # real and belongs where the other four are.
    # `situp` joins them for `(clenched teeth:1.35)`: gritted teeth are drawn
    # with the mouth open, and FACE's `closed mouth` is the tag that turns the
    # strain back into composure.
    # `hype` is here for `(grin:1.4)`: a grin is drawn with the teeth showing
    # and FACE's `closed mouth` is what turns it back into a smirk. Same
    # mechanism as `kick`'s ドヤ顔 and `situp`'s clenched teeth.
    # `snack` is here for a bite. `straw` is deliberately NOT, and the pair is
    # the whole rule: lips close around a straw and they do not close around a
    # melon bread.
    open_mouthed = pose in ("yawn", "fall", "allnighter", "allnighter_full",
                            "dizzy", "kick", "situp", "hype", "roar",
                            "pounce", "loom", "snarl", "swelter", "snack",
                            "hoops", "winded")
    face = FACE.replace("closed mouth, ", "") if open_mouthed else FACE
    # Turned away from the camera, an instruction to face it has no referent;
    # it either argues with the pose or spins her back around.
    # `flop` was in this list while its face was in the ground, for `nape`'s
    # reason. Its face is up, so the instruction has a referent and FACE keeps
    # it; putting `flop` back here is one part of that pose's FACE DOWN state
    # and belongs with the rest of it rather than on its own.
    if pose == "nape":
        face = face.replace(", looking at viewer", "")
    if pose == "swelter":
        # FACE was settled on a composed girl and two of its tags are the
        # opposite of a tantrum.
        #
        # `small mouth` first: the reference's mouth is the biggest thing in
        # the face. `allnighter` removed this once for the same reason and the
        # notes record it going back when that mouth stopped being wanted; it
        # is wanted again.
        face = _splice(face, "small mouth, ", "")
        # And `looking at viewer` for `nape`'s reason rather than its own: with
        # the eyes clamped shut the instruction has no referent, so it either
        # argues with the pose or opens her eyes.
        face = _splice(face, ", looking at viewer", "")
    if pose == "winded":
        # Both of `swelter`'s removals, each for the reason `swelter` gives.
        #
        # `small mouth` because あ゛〜〜〜 makes the mouth the largest thing in
        # the face, which is the sentence `swelter` wrote about its own
        # reference.
        #
        # `looking at viewer` for `nape`'s reason: shot from the side with her
        # head back, the instruction has no referent, so it either argues with
        # the camera or turns her around. FACE's `(tareme:1.3), (large eyes:1.3),
        # (large iris:1.25)` STAY, and they are instructions about eyes that are
        # now shut -- `swelter` noted that cost and did not pay it either.
        face = _splice(face, "small mouth, ", "")
        face = _splice(face, ", looking at viewer", "")
    body = BODY
    if pose == "prone":
        # 「めちゃ下半身太ってしまった…」. BODY's `(wide hips:1.3)` and
        # `(thick thighs:1.35)` were settled on poses that see her from the front
        # or the side, where they read as proportion. This pose looks straight at
        # the rear, foreshortened, so the same two tags land on the largest thing
        # in the frame and read as bulk.
        #
        # Eased rather than deleted, which keeps the framing -- and rather than
        # pushed further: at 0.6/0.6 with `(petite:1.4)` and
        # `(narrow waist:1.4)` the figure is slimmer still and a rabbit
        # silhouette appeared in the backdrop, the same intruder `boss` bought
        # with its guard stack. Two tags eased is the change that costs nothing.
        #
        # `petite` is deliberately not raised. It is the tag `boss` swaps out to
        # grow her up, so leaning on it here would trade one wrong proportion
        # for another.
        #
        # `flop` briefly had this too, transferred on the argument that it saw
        # her from above and from behind exactly as `prone` does. **It has been
        # taken back out**, because the tag that argument rested on --
        # (from above:1.35) -- left `flop` when the dive was asked for. A splice
        # justified by a geometry is not justified once the geometry goes, and
        # keeping it would have left an unexplained deviation from BODY that the
        # next session would have had to reconstruct.
        body = (body.replace("(wide hips:1.3)", "(wide hips:1.0)")
                    .replace("(thick thighs:1.35)", "(thick thighs:1.05)"))
    if pose == "stand":
        # 「身長はそれで良い、だが上半身が少し長い。脚の長さに比重をかけてほしい」.
        #
        # Measured as the share of figure height below the hem, on 1886970040:
        # the accepted render is 40.1%, this is 55.7%. Two caveats on that
        # number -- it is "below the hem" and not an anatomical hip, so a dress
        # that rides up inflates it, and it moved for both reasons here.
        #
        # ADDED as a seventh tag rather than substituted into `(petite:1.2)`,
        # which is the slot arguing against it and which `boss` swaps out for
        # exactly that reason. The substitution measured 55.1%, within noise of
        # this, and was not the one picked.
        #
        # The negative route does not work and this is the second time: naming
        # `(long torso:1.4)` there moved 40.1% to 38.9%, i.e. nothing, and
        # `prone` had already found `(long legs:1.4)` in the negative did
        # nothing to thighs that read too long. **One side of this axis is
        # addressable and it is the positive one.**
        #
        # Spliced, not global. Every other pose was settled against this BODY
        # and would move under it -- the same reason `boss` and `prone` splice
        # it rather than editing the block.
        body = body.replace("(pale skin:1.25)",
                            "(long legs:1.35), (pale skin:1.25)")
    if pose == "flop":
        # 「ちょっと胴体が長い」 on 2ab57f7b, which is the same axis `stand`
        # settled as 「上半身が少し長い。脚の長さに比重をかけてほしい」 and is
        # answered with the same tag at the same weight, in the same slot.
        #
        # Not re-measured, deliberately. `.local/proportion.py` is the metric
        # that separated `stand`'s arms, and it reads rows: head at the top,
        # soles at the bottom, hem where the figure narrows into two legs.
        # She is lying across a landscape frame with her arms thrown out, so
        # every one of those three assumptions is false here, and a transposed
        # version would be a new metric wearing a trusted one's name. The
        # lever is what transfers; the number is not.
        #
        # What transfers with it is the negative-side finding, and it is worth
        # repeating because it is the cheap thing to reach for: naming
        # `(long torso:1.4)` in the NEGATIVE moved 40.1% to 38.9%, i.e.
        # nothing, and `prone` found the same for `(long legs:1.4)` there.
        # One side of this axis is addressable. Ask for the leg.
        # **This weight is bracketed from both sides and that is the useful
        # thing here.** No tag at all drew 「ちょっと胴体が長い」; 1.45 drew
        # 「ちょっと脚が長すぎる」. Whatever is right is strictly inside that,
        # so a future session does not get to go back to either end.
        #
        # 1.40 is the midpoint and it is a guess, not a measurement. 1.35 was
        # rendered against 1.45 once and lost -- but that was against the
        # torso complaint, where too little and too much fail differently, and
        # it was seen on the 徹夜 face at one pass. It is being rendered again
        # beside this rather than ruled out by that.
        #
        # `stand` sits at 1.35 and is not evidence for this pose. It measures
        # a vertical figure whose legs already run the full height of the
        # frame; this one is lying across a landscape one.
        #
        # Leg length is decided in the FIRST pass. There is no second-pass
        # version of this fix the way there was for the eyes -- 0.60 redraws
        # the picture, it does not re-proportion the figure -- so every move
        # on this axis costs the picked composition and has to be re-picked.
        body = body.replace("(pale skin:1.25)",
                            "(long legs:1.40), (pale skin:1.25)")
    if pose == "swelter":
        # `prone`'s argument, pointed at length instead of bulk. That pose eased
        # hips and thighs because a from-above camera foreshortens them into
        # reading as mass; here the same camera was making the legs read long,
        # and `petite` is the tag in BODY that answers proportion as a whole.
        # 1.2 -> 1.4, swept against removing the camera tag alone -- both were
        # needed, and d35a67f8 is the render that carries them.
        body = _splice(body, "(petite:1.2)", "(petite:1.4)")
    character = blocks["character"]
    if pose in HEAD_FRAMINGS:
        # The head framings already drop LEGWEAR, BODY and THIN for one reason:
        # naming what is out of frame is what invites it back into the frame.
        # The shoes are the same reason and were being missed, because they are
        # not in one of those blocks -- `sporty` carries them in the CHARACTER
        # block, which no crop touches.
        #
        # What that cost, and it is the cleanest demonstration of the rule this
        # file has: c08034a0 drew a white high-top sneaker floating in the
        # backdrop beside her head, correctly rendered and attached to nothing.
        # Not a defect of the pose -- the costume asked for a shoe and the frame
        # had no foot to put it on.
        #
        # Removed, not substituted. `swelter` swaps in `(no shoes:1.35)` because
        # its feet are IN the picture and something has to be on them; here
        # there is no foot, and `no shoes` would be naming the crop's own
        # contents back into it.
        character = _splice(
            character,
            ", (white footwear:1.4), (sneakers:1.45), (high tops:1.3)", "",
            costume in SHOD)
    if pose == "swelter":
        # 「部屋でジタバタしているので」. She is on the floor of a room, and
        # SPORTY's white high tops are outdoor shoes; nothing else in the
        # picture says outside, so the shoes were the one tag arguing with the
        # setting.
        #
        # A SUBSTITUTION IN THE SAME SLOT, not a removal. `no shoes` is a real
        # tag and it means what is wanted here exactly -- a foot with no shoe on
        # it, still wearing something -- which is right for a leg in opaque
        # pantyhose; `barefoot` would ask for the tights to come off too. It
        # goes where the three footwear tags were because that is the slot the
        # rest of the costume reads for what is on her feet, and because leaving
        # the slot empty is what this file means by an unaddressed axis: the
        # model has drawn sneakers on this pose on every seed so far and has
        # never been told not to.
        #
        # Gated on the costume that HAS shoes. The settled costume never names
        # footwear on any pose but `stand`, so under `default` there is no
        # needle and `_splice` would fail loudly rather than quietly -- which is
        # the point of the gate. That also means a `default` swelter gets no
        # `no shoes` at all; it has never been rendered, and inventing a slot
        # for it here would be a guess wearing a measurement's clothes.
        character = _splice(
            character,
            "(white footwear:1.4), (sneakers:1.45), (high tops:1.3)",
            "(no shoes:1.35)",
            costume in SHOD)
    if pose == "boss":
        # Grown up, and it is one substitution now, not the two it started as.
        #
        # `petite` -> `mature female`. Direct opposite in the same slot. The
        # rest of BODY -- wide hips, thick thighs, narrow waist -- is already
        # adult proportion and was only ever being held down by that one tag.
        #
        # The face is NOT touched, and why is worth keeping. It was
        # `tareme` -> `tsurime`, on the reasoning that drooping eyes are most
        # of what reads young and that upturned ones would carry the smirk as
        # well -- one swap for both asks. Both halves turned out to be somebody
        # else's work. Reverting the eyes alone leaves the adult read intact,
        # so the body swap was doing that; and the smirk went to (smug:1.15)
        # in the meantime, which retired the other job. What was left was a tag
        # with nothing to do and a sharpness nobody had asked for.
        #
        # `(tsurime:1.1)` is the middle if a trace of it is ever wanted.
        # Dropping the eye tag outright is not the neutral option it looks
        # like: it drew a second empty chair into the backdrop.
        #
        # Spliced per-pose, not changed globally: every other pose was settled
        # against this BODY and would move under it.
        body = body.replace("(petite:1.2)", "(mature female:1.35)")
        # And then say the chest outright, because `mature female` brings one
        # and the negative could not finish the job alone. `(large breasts)` in
        # NEGATIVE went 1.25 -> 1.5 -> 1.75 and was still leaving more than
        # Yukari has; naming `small breasts` positively lands it in one step and
        # holds on 979797979, 343434343 and 2557902837 alike.
        #
        # An addition, and the second block found to tolerate one after the
        # legwear. Guards were the alternative and this recipe has twice been
        # punished for stacking those -- the weight route was tried first here
        # for exactly that reason and simply did not reach.
        body = body.replace("(narrow waist:1.25)",
                            "(narrow waist:1.25), (small breasts:1.35)")
        # And `(oversized shirt:1.3)` comes out, which the adult body made
        # necessary. `mature female` pulls the costume toward a long pale
        # button-front shirt dress -- reverting the body swap alone brought the
        # purple bodice straight back, which is how the cause was found. Since
        # the adult read is the point of this pose, the competing garment goes
        # instead: `oversized shirt` is what `mature female` was recruiting, and
        # dropping it restores the dress on the seeds that had lost it while
        # keeping the proportions.
        #
        # `sleeves past wrists` stays. It is the tag CHARACTER measured as
        # boxing the coat out, and it was not part of this.
        character = _splice(character, "(oversized shirt:1.3), ", "", dressed)
        # The frills splice that used to be here is GONE, and not because it
        # stopped being wanted: CHARACTER carries 1.25 globally now, so the
        # replacement matched nothing and did nothing. A splice against a block
        # that no longer contains its needle fails silently, which is the exact
        # failure this file has a rule about -- so it is deleted rather than
        # left lying as documentation of a value that moved.
        # The coat off her shoulders. This is the render that was approved for
        # the pose, and it costs the rabbit hood -- which the module docstring
        # rules out in general and which is a deliberate exception here, not an
        # oversight. Drop this line to get the hood and the ears back.
        character = _splice(character, "open cardigan",
                            "open cardigan, (off shoulder:1.3)", dressed)
        # The straps. Her dress is a halter that crosses at the chest, goes over
        # the shoulders and ties in a bow behind the neck -- it is in the
        # official design and the recipe had never drawn it outside `nape`,
        # which splices (halterneck:1.45), (black straps:1.35) for the same
        # garment seen from behind.
        #
        # `nape`'s pair is documented as costing every other pose its coat.
        # That is why this is spliced and not global -- but it is also why this
        # pose can afford it: the coat is already off the shoulders one line up.
        #
        # `(criss-cross halter:1.45)` alone is what shipped. One tag against
        # nape's two or all three together, and it names the cross specifically,
        # which is the part the reference is explicit about. The three-tag form
        # drew the straps most clearly and pulled the camera in off the body;
        # the single tag draws them and leaves the composition where it was.
        character = _splice(
            character,
            "(drawstring:1.4), ", "(drawstring:1.4), (criss-cross halter:1.45), ",
            dressed)
    if pose == "stand" and dressed:
        # The dress's own straps: they cross at the chest, go over the shoulders
        # and tie behind the neck. Official design, and until now only `boss`
        # and `nape` drew them -- `boss` because its coat is already off the
        # shoulders, `nape` because it is looking at the knot.
        #
        # This pose has neither excuse and the tag was measured as costing
        # something: backdrop intruders on both seeds it was tried on, which is
        # the same shape `sip` recorded a session ago when the halter pair was
        # tried globally. It was dropped on that basis and then chosen anyway --
        # 355f91cf, picked over the arm without it. The straps are the design and
        # the backdrop is fixable afterwards; `recolor_bg.py` exists for exactly
        # that and the backdrop here has never been prompt-stable.
        #
        # One tag, not `nape`'s two. `(criss-cross halter:1.45)` names the cross
        # specifically, which is the part the reference is explicit about, and
        # `boss` already found the three-tag form pulls the camera in.
        character = _splice(
            character,
            "(drawstring:1.4), ", "(drawstring:1.4), (criss-cross halter:1.45), ",
            dressed)
    if pose == "portrait" and dressed:
        # 「肩紐がないね」. The halter is the official design and this is a
        # head-and-shoulders framing, so the straps are in frame and were not
        # being drawn -- the pose simply never had the splice.
        #
        # `boss` could afford this because its coat is already off the
        # shoulders, and this pose cannot make that argument. It did not need
        # to: the one-tag form drew the straps here with the cardigan up.
        # e4ff4f8a is the picked render, against nape's pair and against the
        # `(off shoulder:1.3)` configuration boss uses.
        #
        # The backdrop cost recorded when this tag was tried GLOBALLY applies
        # here too and is accepted for the same reason `stand` accepted it: the
        # backdrop of a head framing is repainted by `recolor_bg.py` at
        # delivery, so it is a cost this pose had already paid.
        character = _splice(
            character,
            "(drawstring:1.4), ", "(drawstring:1.4), (criss-cross halter:1.45), ",
            dressed)
    if pose == "nape" and dressed:
        # The dress ties in a bow at the nape, which only this pose is looking
        # at, and which costs every other pose its coat -- see CHARACTER.
        # Spliced in beside the coat's cord rather than appended, because that
        # is where they sat in the render this was settled on.
        character = _splice(
            character,
            "(drawstring:1.4), ",
            "(drawstring:1.4), (halterneck:1.45), (black straps:1.35), ",
            dressed)
    legwear = blocks["legwear"]
    if pose == "boss" and dressed:
        # The rib is not decoration -- it is what her thighhighs are, and the
        # block draws it only on some seeds unaided. `(ribbed legwear:1.35)` is
        # ADDED here rather than substituted, which is against this file's usual
        # rule and is the point of the note below.
        #
        # It was substituted first, for `(opaque pantyhose:1.3)`, on one seed
        # where that restored the lines. Shipped, it removed the tights on every
        # seed: `opaque pantyhose` is one of only three tags holding the grey
        # side up against three pale ones, and breaking that tie hands the pale
        # side the whole leg. Substituting from the pale side instead
        # (`white thighhighs`) keeps the tights and costs the pale colour --
        # the legs come out mid-purple.
        #
        # Adding it leaves both sides intact. Measured on 979797979, 343434343
        # and 2557902837: ribbing, pale colour, welt band and the grey above it,
        # all three seeds, and nothing pushed out of the block. The legwear is
        # documented as the first thing this pose spends, so if a later change
        # starts losing thighhighs, this extra tag is the first suspect.
        #
        # The tag it used to be appended to is gone with the second garment --
        # the rib was her thighhighs' rib. It is kept because the surface it
        # names survived the garment: one opaque pantyhose can be ribbed too,
        # and this pose is the one that asks for the texture by name. Appended
        # to `opaque pantyhose` now, which is the slot in the new block that
        # describes the fabric rather than its colour.
        legwear = legwear.replace(
            "(opaque pantyhose:1.4)",
            "(opaque pantyhose:1.4), (ribbed legwear:1.35)")
    # ---- and then the block itself became one garment ----
    #
    # This is where prone spliced its legwear, and the splice is gone: LEGWEAR
    # is a single pantyhose for every pose now, so there is no second garment
    # left to shorten, recolour or ease. The fight is kept in the record because
    # its results are about the MODEL, not about this pose:
    #
    #   Two layers seen from behind read as bike shorts, and nothing lexical
    #   fixes it. Measured on 1886970040, all unchanged: `(bike shorts:1.4)` in
    #   the negative, that plus `(shorts:1.35)`, `pantyhose` from bare to 1.4,
    #   `(very pale purple thighhighs)` eased to 1.15, and a masked in-place
    #   refine of the hip at 0.50 and 0.65 -- the route that fixed this same
    #   render's hand an hour earlier. Nothing in the prompt says shorts, which
    #   is why the lexical route did nothing: there was no tag to outvote.
    #
    #   Easing the grey pair to 0.6 only recoloured the problem -- a smooth plum
    #   rear with the frilled hem above and the welt band below, the same
    #   garment in the dress's colour. The boundary is the defect, so the fix
    #   has to remove one layer, not move it.
    #
    #   Tights to the toes with knee-highs over them, which was the ask for a
    #   while: THIS MODEL WILL NOT DRAW IT IN ONE PASS.
    #     socks at 1.45/1.25   boundary at the knee, correctly, and the thigh
    #                          comes back at 254,240,230 -- her cheek. It is skin.
    #     tights at 1.6/1.7    the socks disappear; one garment again
    #     `kneehighs over pantyhose`, `socks over pantyhose`,
    #     `pantyhose under kneehighs`          thigh still bare, all three
    #     `(bare legs:1.5), (bare thighs:1.45)` negative    thigh still bare
    #     masked refine of the calves, 0.55 / 0.65          no boundary drawn
    #     black socks against pale tights      socks crisp, thigh still bare
    #   The only two-layer construction it knows is `thighhighs over pantyhose`,
    #   a real tag, and that one puts the boundary on the THIGH.
    #
    #   `pale purple pantyhose` gets DRAWN on the thigh and `grey pantyhose`
    #   does not. That is why the colours were inverted here for so long without
    #   anyone noticing: the wrong colour was buying thigh coverage.
    #
    # Obsolete with it: the two-step finish (`recolor_skin.py --tolerance 14`
    # then a masked 0.3 refine) that painted the bare thigh into tights. One
    # garment covers the leg, so there is no bare thigh to repair.
    parts = ["best quality, absurdres, 1girl, solo", character,
             pose_block(pose, costume)]
    if full_figure:
        parts.append(legwear)
    parts += [face, SURFACE]
    parts.append(body if full_figure else "(pale skin:1.25)")
    # The coat pulled off the shoulders, which is what uncovers the nape. It
    # rides with the hood rather than joining the pose block: that block is at
    # eight tags and a ninth is where the hair clips broke last time.
    hood = blocks["hood"]
    parts.append(f"{hood}, (off shoulder:1.25)" if pose == "nape" else hood)
    if full_figure and pose not in PAINT_FINISH:
        # `PAINT_FINISH` drops THIN, and it is a PALETTE decision rather than a
        # line one. Measured on `portrait`: THIN alone took the figure from 150
        # distinct flats to 190, the pass-2 paint guard alone to 168, and the
        # two together to 225 -- superadditive, and neither half predicts it.
        # This pose carries the guard (see HIRES_NEGATIVE), so it cannot also
        # carry THIN without rebuilding the arm that drew 「色がおかしい」.
        #
        # THIN's own comment says it was "measured to do nothing to stroke
        # width". That still holds. Doing nothing to stroke width is not the
        # same as doing nothing, and this is where the difference showed up.
        parts.append(THIN)
    return ", ".join(parts)


# What the second pass redraws at, whatever size it is redrawing into. This is
# the number cc65b02d was drawn at (hr-deep, 1024 -> 1536) and it holds at 2048
# too, so it is a property of the look rather than of the stretch.
#
# It was briefly derived from the upscale instead -- 0.3 + 0.2 * scale, which
# asks 0.70 at 2x -- and separately the climb was split into 1.5x steps so no
# single stretch would need that much. Both are wrong, in the same direction
# and for the same reason: denoise is how much of the final size actually gets
# drawn. 30 steps at 0.45 is thirteen steps of drawing at 2048 and it arrives
# soft; at 0.60 it is eighteen and the linework holds. Splitting the climb
# lowers the number and therefore lowers the drawing, which is the opposite of
# what a bigger print wants.
#
# Keep it a float literal. ComfyUI sizes the schedule with
# int(steps / denoise), so 30 / 0.6 is 50 steps where a computed
# 0.6000000000000001 truncates to 49 -- and one step is a visibly different
# picture. Anything that computes this value must round it.
HIRES_DENOISE = 0.60

# Guards that only run on the SECOND pass, prepended to that pass's negative.
# The first pass keeps the negative it was picked with, byte for byte.
#
# This exists because of one measured asymmetry. `boss` found that removing
# `half-closed eyes` opens the eyes some, and that removal PLUS
# `(half-closed eyes:1.4), (closed eyes:1.4)` in the negative opens them the
# rest of the way -- 「open, iris visible」 -- and in the same breath found that
# the pair is safe chained onto a settled picture and unsafe from scratch: run
# from the recipe it stacked with that pose's buttons guard and grew a second
# chair with a rabbit face on it, the fourth intruder this file has bought by
# stacking guards.
#
# The reason the split works is the pass-depth finding: a late pass only gets
# to delete, and a guard IS a deletion. A first pass gets to rearrange the
# composition around the same guard, and it does.
#
# So a guard whose job is subtraction belongs here rather than in
# `_negative_base`, where it would be handed to the pass that can act on it.
# The five names for a hand drawn wrong, used by `tehe` in both passes.
HAND_BAN = ("(bad hands:1.5), (mutated hands:1.5), (extra digits:1.5), "
            "(fused fingers:1.45), (long fingers:1.4), ")

# Named once because two poses use it and a second literal is a second thing to
# keep in step. `swelter` earned it; `straw` inherited it.
HIRES_NEGATIVE_PAINT = ("(sketch:1.45), (lineart:1.45), (unfinished:1.4), "
                        "(monochrome:1.35), ")

# 「線画の絵柄が変わったね」. Every pose gets these, on the second pass only, and
# the four tags are ALREADY in NEGATIVE at 1.2/1.25 -- this is the same guard
# at a weight that survives a 2x redraw.
#
# The diagnosis, and it is worth keeping because it exonerates two suspects.
# Distinct flats over the figure ran 849 on the first `hoops` render, 643 on
# knotK2, and 1154 and 1167 on the two finalised prints -- the gloss arrived
# between them. It is not the pass-1 prompt: the same pass 1 measured 552 with
# no second pass at all. It is not `6b` either: the 1167 render has no `6b`
# node. What changed is that pass 1 handed pass 2 a different latent, and the
# redraw landed in a glossier style -- specular hair, gradient irises,
# airbrushed skin, i.e. exactly the "clean and vivid" regression this file
# exists to prevent.
#
# Raising them to 1.45/1.5 for the second pass measured 590 against 1154 on the
# same pass 1. `(short dress:1.35)` was the other suspect and it is innocent:
# dropping it from the pass-2 positive measured 1147, i.e. nothing.
#
# Pass 1 keeps 1.2/1.25, untouched. At 1024 that weight was never losing, and
# raising it there would re-roll the composition of every picked render in the
# file -- the guard belongs to the pass that redraws, which is the same rule
# `HIRES_NEGATIVE` was written on.
SHADE_BAN = ("(detailed shading:1.5), (heavy shading:1.5), (impasto:1.45), "
             "(painterly:1.45), ")

HIRES_NEGATIVE = {
    # The pass-1 hand guard again, because 0.70 redraws the hand and a guard
    # that only ran on the pass that is being redrawn is not a guard. Same five
    # tags; see `negative()` for why they are those five.
    "tehe": HAND_BAN,
    # 「右腕が変な色になってる」 on 9603280e, and it was not a colour: the arm
    # thrown over her head measured (255,243,240) against a cheek at
    # (250,230,233) and a backdrop at (238,225,230), outlined in the pink-red
    # this model roughs with instead of the near-black everything painted
    # carries. The flat was never laid down.
    #
    # **The second pass does not fix that on its own.** Same seed, 2048: plain
    # `--hires` redrew the picture with the same hole in it, and 0.70 filled it
    # by redrawing more of everything. The white region is internally coherent
    # -- it has its own linework -- so 0.60 has nothing to resolve until the
    # state is named. Naming it is this line, and it lands at 0.60 without
    # touching anything that was not asked about.
    #
    # Four names because the model does not treat them as one: `sketch` and
    # `lineart` are the medium, `unfinished` is the state, and `monochrome` is
    # what an unpainted region actually is next to a painted one.
    #
    # Pass 2 only, which is the whole point -- the composition the user picked
    # is not re-rolled. 174ce1dc is the render that carries it.
    "swelter": HIRES_NEGATIVE_PAINT,
    # The same four tags, on `straw`, and they were NOT earned the same way.
    # `swelter` had a region that was genuinely never flatted and this guard
    # named it. `straw` has no such region: 「絵柄・塗りのベースとして」 asked for
    # 174ce1dc's paint on another picture, and what transferred was this guard
    # plus THIN's removal, together, as a finish.
    #
    # Read the entry in the notes before copying this onto a third pose. A
    # finish that is the residue of a fix is not a style, and half of this one
    # is a DELETION of a block every other full-figure pose still carries.
    "straw": HIRES_NEGATIVE_PAINT,
    # The third pose to carry it, and it was carried rather than earned: this
    # one is `straw`'s sibling in the same costume, and `straw`'s configuration
    # is the last standing full body the user approved (cf978c9c). Both halves
    # came across together -- see PAINT_FINISH, which is what makes that one
    # decision instead of two.
    "snack": HIRES_NEGATIVE_PAINT,
    # Two hands closed around an object at chest height, which is `tehe`'s
    # accident class exactly. That pose spent forty renders on one hand and its
    # conclusion was about WHERE the guard goes: pass 2 only means the 1024
    # sweep is judging a prompt the print does not use. So this one carries it
    # in both passes from the first sweep, rather than earning the lesson twice.
    "hoops": HAND_BAN,
    # **Measured, not assumed: this pose's FIRST pass has no hand guard at all.**
    # The five names live in `negative()` behind `pose ==` gates, so `tehe` and
    # `hoops` get them and a new pose does not -- `(bad hands:1.5)` counted zero
    # in the picked render's negative. Both hands are flat on the floor carrying
    # her weight and pass 2 redraws them, so they are named here, once.
    "winded": HAND_BAN,
    # 「目も修正してほしい」 on 4b7d646c. `smug` narrows the lids on its own --
    # `half-closed eyes` is long gone from this pose -- and the face is roughly
    # 250px across in a 1536x1024 frame, which is where eyes stop matching each
    # other. Two things wrong, and this addresses one of them; the second pass
    # itself addresses the other by giving the face more pixels to be drawn in.
    "flop": "(half-closed eyes:1.4), (closed eyes:1.4), ",
    # `kick` HAD this guard, preemptively, on the round that gave it `smug`.
    # **It has been taken back out, and the reason is a direct contradiction.**
    # 「もうちょっといつものドヤ顔で」 was answered with the pair `stand` carries,
    # `(smug:1.35), (half-closed eyes:1.3)` -- and `half-closed eyes` is the exact
    # tag this guard deletes, in the same pass. They cannot both be in pass 2.
    #
    # So the two levers for "more smug" are mutually exclusive here, and that is
    # worth carrying forward: raising the weight is compatible with the eye
    # guard, and reaching for the pair is not. The guard was bought to undo
    # `smug`'s lid-narrowing as a side effect; once narrowed lids are the thing
    # being ASKED for, the side effect was the feature.
    #
    # HALF of it is back, and the half is the whole point. 10915a12 -- the render
    # the user pointed at for 「この頃の表情ですね」 -- bans `(closed eyes:1.4)` in
    # its negative while asking for `(half-closed eyes:1.25)` in its positive. It
    # SPLIT the two, and this guard had fused them. Forbid the lids all the way
    # shut; ask for them half. One tag banned, not a stack.
    # 「分厚いタイツってことで足の指先を書かなくてもいいのでは？」 and that
    # dissolves the whole problem, because the picture it asks for is the one
    # two guards had ALREADY DRAWN and this file had already written off.
    # `(extra toes:1.45)` and `(extra digits:1.45)` were both recorded as
    # failures for "dissolving the toes, leaving a smooth sole with no
    # separation at all" -- judged against five countable toes, **a criterion
    # the costume never asked for**. She is in `(opaque pantyhose:1.4)`. A foot
    # in thick tights has a smooth toe box, and drawing five toes through it was
    # the error the whole time.
    #
    # HERE and not in the pass-1 negative, because this is the shape a late pass
    # is best at and the argument that built this dict: a guard IS a deletion,
    # a late pass only gets to delete, and pass 1 stays byte-identical to
    # fa504c93 -- so the composition and the palette both come through
    # untouched and pass 2 smooths the toe box off the end.
    # ONE toe guard, not two, and the second one was expensive. 「あとは発色
    # かな？」 on 1ee9fbc9, which carried `(toes:1.55), (extra toes:1.55)`:
    #
    #   fa504c93  no toe guard      sat 52.0   brightest tenth  89.0
    #   1ee9fbc9  two toe guards    sat 34.4   brightest tenth  52.0
    #   f60817db  ONE toe guard     sat 60.7   brightest tenth 105.0
    #
    # The mean is the smaller half of it: the brightest tenth of the figure went
    # from 89 to 52, which is every accent in the picture flattening, and that
    # is what 発色 named. One guard puts it back above the approved render's own
    # numbers and keeps the smooth toe box, so the second guard bought nothing
    # and cost the colour.
    #
    # Fourth time guard-stacking has cost this recipe something, and the first
    # time the cost was SATURATION rather than the palette's shares or an
    # intruder in the backdrop. The rule is not about which target the guards
    # name -- these two name the same one, which is the shape the rule is about.
    #
    # The 1.55 is kept from the picked render even though its partner is gone;
    # `(toes:1.4)` alone has not been rendered and there is no reason to think
    # the weight was ever the lever.
    "kick": "(toes:1.55), (closed eyes:1.4), ",
}

# The positive-side sibling, and it exists for a request the negative one cannot
# serve: 「リファイン。いつもの強気な表情で」 on 202e6fc0 -- a finish AND an
# expression, on a composition that had just been picked.
#
# The first pass is the pass that decides the composition, so putting `smug`
# there would have cost the picked render, exactly as the leg weight did the
# round before. Putting it here does not, and the reason it still works is the
# other half of the pass-depth finding: a late pass at 0.60 DOES draw things the
# base does not contain -- `refine_from_history`'s own note measured 0.35
# leaving new straps a faint suggestion and 0.60 drawing them properly. Addition
# is not free in a late pass the way deletion is; it is affordable at 0.60.
#
# And the thing this loses is the thing that makes it safe. `sip` measured that
# `smug` does posture as well as face -- it lifts the chin and puts head, spine
# and hip on one arc -- and a late pass cannot re-pose a figure. So this buys
# the half of `smug` that was asked for and cannot spend the half that would
# have moved the leg. **The pass boundary is what splits the tag.**
#
# Spliced into the pose block rather than appended to the whole string: that is
# where every other pose carries the smirk, and this file has already recorded
# that token order changes the encoding.
HIRES_POSITIVE = {
    # 「もうちょっといつものドヤ顔で」 after 1.15 and 1.35 both landed short.
    # The pair, not a third weight -- this is the lever the previous round named
    # as next, and it is the one `stand` runs. `boss` dropped the lids only
    # because at `(smug:1.15)` they were the last thing reading as attitude
    # rather than composure, which is an argument for keeping them when attitude
    # is what was asked for. See HIRES_NEGATIVE above: this is why `kick` no
    # longer carries the eye guard.
    # 「この頃の表情ですね」 with 10915a12 attached -- pl-b-2331520658, an
    # upper-body portrait from the hoodie era, on a different SURFACE and a
    # different negative. Its expression cluster is copied here verbatim, and it
    # says plainly that TWO ROUNDS OF WEIGHT-HUNTING WERE THE WRONG SEARCH:
    #
    #   (smug:1.3)              between the 1.15 and 1.35 that both landed short
    #   (half-closed eyes:1.25) the pair, confirmed, and just under 1.3
    #   (confident:1.25)        NEVER USED IN THIS RECIPE, and it is literally
    #                           the word the request was made with (自信ありげ)
    #   (open mouth:1.35)       the mouth is OPEN, and FACE nails it shut
    #
    # The last one is most of the difference. A smirk with a closed mouth is
    # composure; the same smirk with the mouth open is the ドヤ顔 that had been
    # asked for three times. No weight on `smug` was ever going to reach it,
    # because the mouth is a different tag -- and the search stayed on `smug`
    # for two rounds because that was the tag that had moved last.
    # ...and 「表情は2枚目が正しい」 emptied it again. The cluster is in
    # `POSES["kick"]` now; see the note there. The mechanism stays, because the
    # finding it proved is worth having in code: `HIRES_POSITIVE` reaches
    # anything a late pass can DRAW, and does not reach anything pass 1 has
    # already DECIDED. A face is the second kind. So is a toe count.
}


def build(pose: str, seed: int, prefix: str, hires: int = 0,
          denoise: float | None = None, costume: str = "default") -> dict:
    """The settled graph. `hires` adds a second pass at that square size.

    The canvas of the first pass never changes, because that is the pass that
    decides the composition -- including how many people are in it. Raising the
    canvas itself is what drew a second figure at 1280x1920, and no card fixes
    that: it is the model leaving the sizes it was trained on. Upscaling the
    latent afterwards and redrawing it keeps that decision and buys the pixels
    anyway.
    """
    width, height = SIZES[pose]
    graph = {
        "4": {"class_type": "DiffusersLoader",
              "inputs": {"model_path": "hassaku-il-v22"}},
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"batch_size": 1, "width": width, "height": height}},
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["4", 1], "text": positive(pose, costume)}},
        "7": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["4", 1], "text": negative(pose, costume)}},
        "3": {"class_type": "KSampler", "inputs": {
            "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["5", 0], "seed": seed, "steps": 30, "cfg": 5.0,
            # dpmpp_2m, reset to b1258b0c. euler_ancestral took clean renders from
            # 4-of-7 to 7-of-7 and is the better sampler for clutter -- but it
            # re-injects noise each step, so every seed draws something else and
            # the picked render cannot be reproduced under it. Switch back if
            # clutter matters more than this particular image.
            "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode",
              "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0],
                         "filename_prefix": f"{prefix}-{pose}-{seed}"}},
    }

    if hires:
        longest = max(width, height)
        # bicubic, not bislerp. A latent pixel is an 8x8 patch of picture, so
        # how it is resampled decides what the edges look like -- and bislerp
        # steps them. At 1.5x that hid inside the linework; at 2x the diagonals
        # came back visibly stairstepped. Same size, same denoise, bicubic
        # instead, and they are smooth. Scaling in image space through a VAE
        # round trip fixes it too, and is not needed: the resampler was the
        # whole problem, not the fact that it ran on a latent.
        graph["10"] = {"class_type": "LatentUpscale", "inputs": {
            "samples": ["3", 0], "upscale_method": "bicubic",
            "width": round(hires * width / longest / 8) * 8,
            "height": round(hires * height / longest / 8) * 8,
            "crop": "disabled"}}
        graph["11"] = {"class_type": "KSampler", "inputs": {
            "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["10", 0], "seed": seed, "steps": 30, "cfg": 5.0,
            "sampler_name": "dpmpp_2m", "scheduler": "karras",
            "denoise": HIRES_DENOISE if denoise is None else denoise}}
        if pose in HIRES_POSITIVE:
            # `pose_block`, not `POSES[pose]`: a costume may have edited the
            # pose's tags, and this splice finds the pose block inside the
            # finished prompt by matching it.
            block = pose_block(pose, costume)
            text = positive(pose, costume).replace(
                block, block + ", " + HIRES_POSITIVE[pose])
            # A pass cannot say `closed mouth` and `(open mouth:1.35)` at once,
            # and FACE says the first for every pose outside `open_mouthed`.
            # That list is read by `positive()`, so it applies to BOTH passes --
            # which is not what a pass-2-only expression wants. Resolved where
            # the contradiction arises, rather than by adding the pose to a list
            # that would also open its mouth in the pass that picks the
            # composition. Asserted, because this file has been bitten by a
            # `.replace` against a string that no longer contained the target.
            if "open mouth" in HIRES_POSITIVE[pose]:
                assert "closed mouth, " in text, pose
                text = text.replace("closed mouth, ", "")
            graph["6b"] = {"class_type": "CLIPTextEncode",
                           "inputs": {"clip": ["4", 1], "text": text}}
            graph["11"]["inputs"]["positive"] = ["6b", 0]
        # Unconditional, where this used to be `if pose in HIRES_NEGATIVE`.
        # SHADE_BAN applies to every pose -- the gloss is a property of the
        # redraw, not of any one pose -- so there is always a second negative
        # now, and the dict only decides what goes in FRONT of it.
        graph["7b"] = {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["4", 1],
            "text": (SHADE_BAN + HIRES_NEGATIVE.get(pose, "")
                     + negative(pose, costume))}}
        graph["11"]["inputs"]["negative"] = ["7b", 0]
        graph["8"]["inputs"]["samples"] = ["11", 0]

    return graph


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pose", choices=sorted(POSES), default="lounge")
    parser.add_argument("--costume", choices=sorted(COSTUMES), default="default",
                        help="which set of clothes; the settled one is `default`")
    parser.add_argument("--seed", type=int, action="append", default=[])
    parser.add_argument("--seeds", type=int, default=0,
                        help="take this many from the fixed sweep list")
    parser.add_argument("--prefix", default="yk")
    parser.add_argument(
        "--hires",
        type=int,
        default=0,
        help="redraw at this size on a second pass (1536 and 2048 are measured)",
    )
    parser.add_argument(
        "--hires-denoise",
        type=float,
        help="override the second pass denoise; the default follows the upscale",
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--print-prompt", action="store_true")
    args = parser.parse_args()

    if args.print_prompt:
        print(positive(args.pose, args.costume), "\n\n---\n\n",
              negative(args.pose, args.costume))
        return

    # The costume goes in the filename. Two sets of clothes through one pose at
    # one seed are otherwise two files a letter apart in the output directory,
    # and the second one is the one nobody can name afterwards.
    prefix = (args.prefix if args.costume == "default"
              else f"{args.prefix}-{args.costume}")
    seeds = args.seed or SWEEP_SEEDS[:args.seeds] or [SWEEP_SEEDS[0]]
    for seed in seeds:
        req = urllib.request.Request(
            f"http://{args.host}:{args.port}/prompt",
            data=json.dumps({"prompt": build(args.pose, seed, prefix,
                                             args.hires, args.hires_denoise,
                                             args.costume)}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(seed, json.load(resp)["prompt_id"], flush=True)


if __name__ == "__main__":
    main()
