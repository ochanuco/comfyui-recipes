# recipe

The interpreter: pose records and style blocks into a render specification.
This file owns the ORDER and nothing else. Token order changes the encoding
-- a mid-prompt insertion re-rolls every token after it, and this recipe has
caught a one-line drift by checking it -- so the sequence in which blocks
are joined and edits are applied is fixed here, in the open, and the data
lives in `poses.py` / `costumes.py` / `prompt_style.py`. A new pose should
need a record and no changes to this file.

## SWEEP_SEEDS

A fixed list rather than random seeds: a sweep that cannot be repeated
cannot be used to show that a later change did or did not break something.

```python
SWEEP_SEEDS = [555666777, 111222333, 1886970040, 737373737, 2557902837,
               3409564303]
```

## `_splice`

`str.replace`, except that a needle which is not there is an error. A
replacement that matches nothing does nothing AND SAYS NOTHING; this recipe
has paid for that failure twice (see the skirt-guard and negative-tail
histories in `costumes.md` and `prompt_style.md`), so the quiet version is
gone. `when=False` skips the splice outright, which is the honest way to
say "this costume has no such garment" -- as against letting the
replacement run and match nothing, which looks identical in the output and
means the opposite.

## `positive()`: the shod-costume footwear removal

For a head framing, the shoes are not in the blocks the crop drops -- a
shod costume carries its footwear tags inside `CHARACTER` itself -- and
`c08034a0` drew a sneaker floating in the backdrop beside her head to prove
it. The fix removes the footwear text rather than substituting it: there is
no foot in frame to name anything onto.

## `positive()`: THIN and `paint_finish`

`paint_finish` drops `THIN`, and it is a PALETTE decision rather than a
line one. Measured on `portrait`: `THIN` alone took the figure from 150
distinct flats to 190, the pass-2 paint guard alone (from
`HIRES_NEGATIVE_PAINT`) to 168, and the two together to 225 --
superadditive, and neither half predicts it on its own. A finish pose
carries the paint guard in its `hires_negative`, so it cannot also carry
`THIN` without rebuilding the arm that drew 「色がおかしい」.

## `render_spec()`: canvas size is fixed at first pass

The canvas of the first pass never changes, because that is the pass that
decides the composition -- including how many people are in it. Raising the
canvas itself is what drew a second figure at 1280x1920, and no negative
guard fixes that: it is the model leaving the sizes it was trained on.
Upscaling the latent afterwards and redrawing it keeps that decision and
buys the pixels anyway.

## `render_spec()`: bicubic vs bislerp resampling

A latent pixel is an 8x8 patch of picture, so how it is resampled decides
what the edges look like -- and bislerp steps them. At 1.5x that stairstep
hid inside the linework; at 2x the diagonals came back visibly
stairstepped. Same size, same denoise, switching to bicubic instead made
them smooth. Scaling in image space through a VAE round trip fixes it too,
and was found unnecessary: the resampler was the whole problem, not the
fact that it ran on a latent.

## `render_spec()`: the pass-2 positive splice

The mechanism a pass-2 positive uses -- splicing new text after the pose
block, keyed by matching the pose block's own string inside the finished
prompt -- was proved out by the kick expression rounds, and is kept even
while no pose currently uses it: a pass-2 positive reaches anything a late
pass can DRAW (an expression, at 0.60 denoise), and does not reach anything
pass 1 has already DECIDED (a leg's pose, a toe count). `pose_block()`, not
`POSES[pose]`, because a costume may have edited the pose's tags, and the
splice needs to find the pose block as it actually appears inside the
finished prompt.

A pass cannot say `closed mouth` and `(open mouth:1.35)` at once, and FACE
says the first for every pose without `open_mouth` -- which applies to BOTH
passes, not just what a pass-2-only expression wants. The contradiction is
resolved where it arises: if `"open mouth"` is in the pose's
`hires_positive`, `"closed mouth, "` is asserted present and stripped.

`SHADE_BAN` is unconditional in the pass-2 negative: the gloss regression it
guards against is a property of the redraw itself, not of any one pose (see
`prompt_style.md`), so there is always a second negative and the pose
record only decides what goes in FRONT of it.

## Derived views

`PAINT_FINISH` collects the poses whose finish is `174ce1dc`'s. It is TWO
things together -- the pass-2 paint guard in the record's `hires_negative`,
and `paint_finish` dropping `THIN` -- and a pose that got one half without
the other would be precisely the failure the `straw` pose note warns about.
Folding both into one `paint_finish` flag makes it one decision rather than
two that can drift apart.

`SETTLED_SEED` records the seed each pose was settled on, where the pose
has one -- not a default (`--seed` is still explicit), but a number that
would otherwise only be recoverable from a filename in a worker's render
history.
