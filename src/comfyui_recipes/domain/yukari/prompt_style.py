"""Yukari's prompt-side identity: face, surface, body, line and negative.

These blocks are the identity of the drawing -- every pose and every costume
wears all of them at once. A pose that needs a departure declares it as an
Edit in its own record (`poses.py`); this file does not change per pose, and
changing it changes every render this repo has ever approved. The delivery
half of the identity (backdrop colour, outline, palette) is
`delivery_style.py`.
"""

from __future__ import annotations

# The 素顔 (resting face) lids. Eye-shape tags all lost the sweep; what reads
# as ジト目 is an expression-driven lid at exactly this weight plus a cool
# attitude. Swapping `unamused` out turns the same lid into the ドヤ顔 -- one
# lid, two moods. A pose that declares its own expression sets
# `own_eyes=True`, which strips this pair the way `open_mouth` strips
# `closed mouth`; both halves must stay one string or the strip breaks.
RESTING_EYES = "(unamused:1.3), (half-closed eyes:1.3), "

FACE = (
    # The lash pair is bracketed from ABOVE: 1.45 is already slightly too
    # much, so anything right on this axis is at or under 1.35.
    "(tareme:1.3), " + RESTING_EYES + "(large eyes:1.3), 2000s (style), "
    "(eyelashes:1.3), (thick eyelashes:1.35), "
    "(large iris:1.25), thin eyebrows, closed mouth, small mouth, "
    "looking at viewer"
)

SURFACE = (
    # `sticker` is out: it draws literal stickers (a decal on her cheek,
    # loose cut-outs) and was the measured source of the second figure.
    # The die-cut edge is drawn by the delivery now, not this block --
    # which does NOT remove all decoration; there is at least one more
    # source.
    "(flat color:1.3), (simple background:1.3), (grey background:1.2), "
    "(soft shading:1.3), smooth shading"
)

BODY = (
    "(toned legs:1.2), (wide hips:1.3), (thick thighs:1.35), (narrow waist:1.25), "
    "(petite:1.2), (pale skin:1.25)"
)

# Measured to do nothing to stroke width; present because the reference
# render carried them.
THIN = "(thin lineart:1.3), (fine lines:1.25), (delicate lines:1.2)"

NEGATIVE = (
    # The other half of FACE's lash pair (the 長さ side). In front, because
    # every guard this file kept went at the front and token order changes
    # the encoding. Never isolated: the picked render carries it, so it is
    # in; if a later session finds it inert, deleting it costs nothing else.
    "(long eyelashes:1.35), "
    "worst quality, low quality, score_1, score_2, score_3, blurry, "
    "jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text, (disembodied eye:1.4), "
    "(brown legwear:1.5), brown thighhighs, brown pantyhose, (fishnet:1.4), "
    "(latex:1.45), (rubber:1.45), (leather legwear:1.45), "
    "(upskirt:1.4), panties, (from below:1.35), "
    "(blue legwear:1.5), (blue background:1.5), (blue tint:1.4), "
    # No thighhighs guard here: the model does not hold sock lengths apart,
    # and a length guard removes the garment outright. The sheer guard names
    # the dress ALONE -- a broad see-through block flattened the palette the
    # way stacked duplicate guards always have. The skirt pair stops the
    # one-piece being drawn as a skirt with a frill under it; it is the
    # riskiest guard in this negative (without the dress weighted it once
    # deleted the whole lower garment) and it sits in the target render's
    # own position.
    "(mismatched legwear:1.5), (skirt:1.35), (pleated skirt:1.4), "
    "(single thighhigh:1.5), "
    "(asymmetrical legwear:1.45), (uneven legwear:1.4), "
    "(petticoat:1.35), (layered skirt:1.25), "
    "(see-through dress:1.45), (transparent clothing:1.3), "
    "(hood up:1.5), (hood over head:1.4), "
    "(impasto:1.25), (painterly:1.25), (oil painting (medium):1.2), "
    "(heavy shading:1.2), (detailed shading:1.2), (realistic:1.1), "
    "(huge breasts:1.4), (large breasts:1.25), cleavage"
    # Tail, in the target render's own order. The three measured nothing and
    # are kept for identity with that render rather than for effect.
    ", (cropped jacket:1.45), (midriff:1.35), (navel:1.3)"
)

# What the second pass redraws at, whatever size it is redrawing into -- a
# property of the look, not of the stretch. Denoise is how much of the final
# size actually gets drawn: 0.45 arrives soft, 0.60 holds the linework, and
# both deriving it from the upscale and splitting the climb into smaller
# steps lower the drawing -- the opposite of what a bigger print wants.

# Keep it a float literal. ComfyUI sizes the schedule with
# int(steps / denoise), so 30 / 0.6 is 50 steps where a computed
# 0.6000000000000001 truncates to 49 -- and one step is a visibly different
# picture. Anything that computes this value must round it.
HIRES_DENOISE = 0.60

# A guard is a deletion, and a late pass only gets to delete; a FIRST pass
# rearranges the composition around the same guard, which is how stacked
# guards have bought backdrop intruders here. So a guard whose job is pure
# subtraction runs on the second pass only, prepended to that pass's
# negative; the first pass keeps the negative it was picked with, byte for
# byte.
# The five names for a hand drawn wrong, run in BOTH passes by the poses
# with a hand at the face.
HAND_BAN = ("(bad hands:1.5), (mutated hands:1.5), (extra digits:1.5), "
            "(fused fingers:1.45), (long fingers:1.4), ")

# 手書き風の仕上げ、パス2の末尾に足す一対。`sketch` はこの家族で一番大きい
# タグだが入れていない -- 意味が未完成状態そのもので、それは
# HIRES_NEGATIVE_PAINT が消すために書かれた状態だから。generate.py --finalize の --handdrawn
# も同じ文字列を使う: 二か所が同じものを名乗るなら、文字列は一つ。
#
# 末尾に足すことが仕様の一部。HIRES_POSITIVE はプロンプトの途中に差し込む別
# 機構で、途中への挿入はそれ以降のトークンを全部振り直す。
HANDDRAWN_FINISH = ", (traditional media:1.4), (marker (medium):1.35)"

# Named once because two poses use it and a second literal is a second thing
# to keep in step. `swelter` earned it; `straw` inherited it.
HIRES_NEGATIVE_PAINT = ("(sketch:1.45), (lineart:1.45), (unfinished:1.4), "
                        "(monochrome:1.35), ")

# The recipe path holds the eye design because positive() always carries
# FACE; any pass that redraws the face WITHOUT going through positive() -- a
# rough-to-finish img2img, an eye-region Crop&Stitch -- lets hassaku's own
# detailed eyes in at high denoise. Such a pass must put FACE in its positive
# AND this ban in its negative; neither half alone is enough.
# detailed/heavy shading are not here because SHADE_BAN already owns them --
# stack both blocks, do not merge.
EYE_BAN = ("(sparkling eyes:1.4), (glitter:1.3), (multiple highlights:1.3), "
           "(gradient eyes:1.2), ")

# Tags that belong to the first pass only; stripped from the redraw positive.
PASS1_ONLY_TAGS = frozenset({"sketch", "rough sketch", "rough lines"})

# The redraw's line-breaking guard.
DOT_BAN = ("(dotted line:1.3), (dashed line:1.3), (stipple:1.3), "
           "(halftone:1.2), ")

# Every pose gets these, on the second pass only. The four tags are ALREADY
# in NEGATIVE at 1.2/1.25 -- this is the same guard at a weight that survives
# a 2x redraw. The gloss is a property of the redraw, not of the pass-1
# prompt: pass 1 hands pass 2 a latent and the redraw lands in a glossier
# style (specular hair, gradient irises -- the clean-and-vivid regression
# this file exists to prevent). Pass 1 keeps 1.2/1.25 untouched: raising it
# there would re-roll the composition of every picked render in the file.
# The guard belongs to the pass that redraws, the rule HAND_BAN is also on.
SHADE_BAN = ("(detailed shading:1.5), (heavy shading:1.5), (impasto:1.45), "
             "(painterly:1.45), ")
