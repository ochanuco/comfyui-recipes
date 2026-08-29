# prompt_style

Yukari's prompt-side identity: face, surface, body, line and negative. These
blocks are the identity of the drawing -- every pose and every costume wears
all of them at once. A pose that needs a departure declares it as an Edit in
its own record (`poses.py`); this file does not change per pose, and
changing it changes every render this repo has ever approved. The delivery
half of the identity (backdrop colour, outline, palette) is
`delivery_style.py`.

## RESTING_EYES and FACE

The 素顔 (resting face) eyes, `(unamused:1.3), (half-closed eyes:1.3)`, were
picked as `e6d6j7` over a 28-arm sweep: shape tags (jitome / narrowed /
droopy / tsurime) all lost to what reads as ジト目 -- an expression-driven
lid at exactly this weight, with 1.15 too little and 1.45 too much, plus a
cool attitude. Swapping `unamused` out turns the same lid into the ドヤ顔
(`neki8u`) -- one lid, two moods, which is why a pose that declares its own
expression (`own_eyes=True`) strips the whole pair rather than editing it
piecemeal.

The lash weight in FACE, 「毛量は多いが長さは均一がいいかな」, is bracketed
from ABOVE: 1.45 was called ほんの少し多い and 1.25/1.15 were rendered in the
same round, so anything right on this axis is at or under 1.35. The bare
`eyelashes` tag this replaced had never been swept at all.

## SURFACE: the sticker removal

`sticker` is out. It draws literal stickers -- a rabbit decal on her cheek,
rabbit patches, loose cut-outs -- and, measured over seven seeds, it was
also the source of a second figure: with it, two of seven had a chibi clone
in frame; without it, none of seven did.

`(white outline:1.6)` and plain `outline` stay -- they are the die-cut edge;
`sticker` was the half that drew actual stickers, and the edge survives its
removal. It does NOT remove all decoration: patterned rabbits on the
garment, background streaks and one piebald coat came through anyway, so
there is at least one more source still unidentified.

## THIN

Measured to do nothing to stroke width; kept in the file only because fb-b
(the reference render) carried the tags.

## NEGATIVE

The lash-length guard, `(long eyelashes:1.35)`, is the other half of the
lash pair in FACE: `thick eyelashes` is the 毛量 and this is the 長さは均一.
It sits at the front of NEGATIVE because every guard this file kept went at
the front, and token order changes the encoding.

NOT ISOLATED: `K`/`Kn` and `qbK`/`qbKn` were rendered to measure whether
this tag does anything at all -- this recipe's own record is that a guard
deletes drawn objects and fails on properties, and lash length is nearer a
property. Those pairs were never judged; the picked render carries the
guard, so the guard stays in. Flagged as the line to delete if a later
session finds it inert -- there is no other cost to deleting it.

The skirt-guard pair, `(skirt:1.35), (pleated skirt:1.4)`, is the riskiest
thing in this negative: on its own, before the dress weight went to 1.45
(see `costumes.md`), it deleted the whole lower garment on one of two
seeds. It is here because `ns-1117511306` (prompt `7d231c4f`), the render
this recipe is aimed at, has it, and in this position.

`(opaque pantyhose:1.5)` used to live in this negative, from when the
tights were meant to be sheer. It was the direct opposite of the current
ask and had to go. So did `(thighhighs:1.4), (white legwear:1.4)`, which
forbade the socks outright -- they were added while abandoning the layered
legwear and were the reason the socks could not come back.

The sheer guard names only the dress and nothing else. A four-tag block of
`(see-through), (see-through clothes), (transparent clothing), (sheer
clothes)` went in alongside it once and the palette came back flat and
dark, the same shape as the duplicate-guard block that wrecked the colours
before. `(thighhighs:1.3)` was also tried, to stop the socks creeping back
to full length -- it removed them outright: the model does not hold
`thighhighs` and `over-kneehighs` apart, whatever the danbooru wiki
separates. Sock length has to come from the positive tag alone.

The four asymmetry guards -- `(mismatched legwear:1.5),
(asymmetrical legwear:1.45), (uneven legwear:1.4), (single thighhigh:1.5)`
-- are exactly as `gl-lounge-555666777` carried them; rebuilding the
legwear block had left only the first. Judged over four seeds, not one:
restoring the full set raised the visible tights band from a 7.7%
worst-case to 23.0%, so socks-over-tights reads correctly on every seed
tried rather than most of them. Worst case is the number that matters here
-- the mean barely moved.

They do NOT fix left/right symmetry, which is what they were originally
restored for: mean leg difference went 11.0 -> 16.5 with them in. By eye
both legs were correctly layered in all four renders regardless, so that
measure was reading pose and overlap, not sock length -- it should not be
used to judge legwear again.

The tail of the negative -- `(cropped jacket:1.45), (midriff:1.35),
(navel:1.3)` -- is kept for identity with `7d231c4f` (the target render's
own order) rather than for effect: all three measured nothing, the hem did
not move with them in or out.

## HIRES_DENOISE

`0.60`, the value `cc65b02d` was drawn at (hr-deep, 1024 -> 1536), and it
holds at 2048 too, so it is a property of the look rather than of the
stretch.

It was briefly derived from the upscale instead -- `0.3 + 0.2 * scale`,
which asks 0.70 at 2x -- and separately the climb was split into 1.5x steps
so no single stretch would need that much denoise. Both were wrong, in the
same direction and for the same reason: denoise is how much of the final
size actually gets drawn. 30 steps at 0.45 is thirteen steps of drawing at
2048 and it arrives soft; at 0.60 it is eighteen steps and the linework
holds. Splitting the climb lowers the number and therefore lowers the
drawing, the opposite of what a bigger print wants.

The value must stay a float literal: ComfyUI sizes the schedule with
`int(steps / denoise)`, so `30 / 0.6` is 50 steps where a computed
`0.6000000000000001` truncates to 49 -- and one step is a visibly different
picture. Anything that computes this value must round it.

## HAND_BAN and the pass-depth split

This split exists because of one measured asymmetry. `boss` found that
removing `half-closed eyes` opens the eyes some, and that removal PLUS
`(half-closed eyes:1.4), (closed eyes:1.4)` in the negative opens them the
rest of the way -- 「open, iris visible」 -- and in the same breath found
that the pair is safe chained onto a settled picture and unsafe from
scratch: run from the recipe, it stacked with that pose's buttons guard and
grew a second chair with a rabbit face on it, the fourth intruder this file
has bought by stacking guards.

The reasoning kept: a late pass only gets to delete, and a guard IS a
deletion. A first pass gets to rearrange the composition around the same
guard, and it does. So a guard whose job is subtraction belongs in the
pass-2-only set (`HAND_BAN` and friends) rather than in the base negative,
where it would be handed to a pass that can still rearrange around it.

## HANDDRAWN_FINISH

「手書き風」の仕上げ、パス2の末尾に足す一対。`traditional_media` 125k と
`marker_(medium)` 18k を使い、この家族で一番大きいタグである `sketch`
(194k) はあえて入れていない -- 意味が「未完成」であり、それは
`HIRES_NEGATIVE_PAINT` が消すために書かれた状態そのものだから。`winded`
が最初に買い、`generate.py --finalize` の `--handdrawn` が同じ文字列を使う:
二か所が同じものを名乗るなら、文字列は一つにする。

末尾に足すことが仕様の一部: `HIRES_POSITIVE` はプロンプトの途中に差し込む
別機構で、途中への挿入はそれ以降のトークンを全部振り直してしまう。

## HIRES_NEGATIVE_PAINT

Named once because two poses use it, and a second literal would be a second
thing to keep in step. `swelter` earned it; `straw` inherited it.

## EYE_BAN

「目のデザインが私の作品っぽくない」(`28bgoa`). The recipe path holds the
eyes because `positive()` always carries FACE; any pass that redraws the
face WITHOUT going through `positive()` -- a rough-to-finish img2img, an
eye-region Crop&Stitch -- lets hassaku's own detailed eyes back in at high
denoise. Such a pass must put FACE in its positive and this ban in its
negative; neither half alone was enough on `28bgoa`. detailed/heavy shading
are deliberately not repeated here because `SHADE_BAN` already owns them --
the two blocks stack rather than merge.

## SHADE_BAN

「線画の絵柄が変わったね」. Every pose gets these tags on the second pass
only, at 1.45/1.5/1.45/1.45 -- the same four tags already sit in NEGATIVE at
1.2/1.25, this is the same guard at a weight that survives a 2x redraw.

The diagnosis is worth keeping because it exonerates two suspects. Distinct
flats over the figure measured 849 on the first `hoops` render, 643 on
`knotK2`, and 1154 and 1167 on the two finalised prints -- the gloss
arrived between them. It is not the pass-1 prompt: the same pass 1 measured
552 with no second pass at all. It is not `6b` either: the 1167 render has
no `6b` node. What changed is that pass 1 handed pass 2 a different latent,
and the redraw landed in a glossier style -- specular hair, gradient
irises, airbrushed skin, i.e. exactly the "clean and vivid" regression this
file exists to prevent.

Raising the guard weights to 1.45/1.5 for the second pass measured 590
against 1154 on the same pass 1. `(short dress:1.35)` was the other
suspect and it is innocent: dropping it from the pass-2 positive measured
1147, i.e. nothing.

Pass 1 keeps its weights at 1.2/1.25, untouched: at 1024 that weight was
never losing, and raising it there would re-roll the composition of every
picked render in the file. The guard belongs to the pass that redraws --
the same rule `HIRES_NEGATIVE_PAINT`/`HAND_BAN` were written on.
