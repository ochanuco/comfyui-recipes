"""The author's hand, prompt side: face, surface, body, line, and the negative.

These blocks are the identity of the drawing -- every pose and every costume
wears all of them at once. A pose that needs a departure declares it as an
Edit in its own record (`poses.py`); this file does not change per pose, and
changing it changes every render this repo has ever approved. The delivery
half of the identity (backdrop colour, outline, palette) is
`delivery_style.py`.
"""

from __future__ import annotations

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

# Measured to do nothing to stroke width; present because fb-b carried them.
THIN = "(thin lineart:1.3), (fine lines:1.25), (delicate lines:1.2)"

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
