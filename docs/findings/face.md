# Eyes and face

Tags and `a<n> §` pointers: see [`docs/README.md`](../README.md).

## Holds

- The identity is たれ目 + ジト目. What makes ジト目 is an expression tag that
  lowers the lid (`half-closed eyes`) plus an attitude word; direct shape tags
  (`jitome`, `narrowed eyes`, `tsurime`, `droopy`) lost every blind round on
  IL. `[IL]` (a5 §第3弾ピック; a5 §目の種類シート)
- On Anima, `jitome` works only at the head of the eyes part, where its weight
  counts; `half-closed eyes` is what removes the round eye. smile/gao take
  1.8 without half-closed, other expressions 1.4 (1.8 kills the doya smile).
  `[Anima]` (PR #217)
- Bust eye size does not move with `large eyes` / `big eyes` weight or
  position on Anima; dropping `half-closed eyes` opens them a little. `[Anima]`
- Two settled states on IL: resting = `unamused` + `half-closed eyes` (1.3
  each); smug = `tareme` + `half-closed eyes`. 1.15 too little, 1.45 too much.
  `[IL]` (a5 §目の役割割当)
- Eye tags decide more than the face: swapping only the eye tag at a fixed
  seed moved the figure's skin-hue share from 81% to 2% (skin painted purple).
  `[all]` (a5 §2026-08-31 表情差分シート)
- Eye identity is not local. Crop-and-stitch on the eye region failed at every
  denoise up to a full repaint; change eyes by regenerating the face. `[all]` (a5 §目は局所プロパティ)
- Any path that repaints the face outside the prompt builder carries the face
  part and its eye bans (`EYE_BAN` in the IL recipe), or it falls back to the
  checkpoint's own eyes. `[all]` (a5 §目のアイデンティティ)
- Grimace comes from visible teeth, not from the tag that asked for them; use
  `open mouth` alone. A weight cannot rescue a tag that means the opposite;
  delete it. `[IL]` (a3 §The teeth; a3 §The gap is a different tag)
- When an expression will not land, compare with the reference render's
  actual prompt (`get_generation`) before re-weighting: two rounds went to
  `smug` while a shared `closed mouth` default silenced `open mouth`. `[all]` (a3 §The answer was in `/history`)
- An eye-lid guard banning half-closed and closed as a pair contradicts a
  wanted half-closed; ban only fully closed. `[IL]` (a3 §The answer was in)
- Expression and body/camera tags were independent axes: a 4-tag expression
  cluster swapped four times never moved body or canvas. `[all]` (a3 §2026-08-19 — `flop` takes 1.45)
- Lowering an expression tag's weight keeps the posture it drives (chin,
  spine) and drops only excess emotion; a synonym swap cost unrelated details.
  `[IL]` (a2 §Dialling the smirk down)
- Symbol tags draw literally and need low weight: `(@_@:1.0)`; `@_@` at 1.45
  overdraws. An additive symbol is not a drop-in for a subtractive tag at the
  same weight. `[IL]` (a4 §`dizzy` settles)
- Texture features (dark eyebags) need two different tags (`eyebags` 1.55 +
  `tired` 1.3), not one heavier tag. `[IL]` (a4 §`(eyebags:1.55)`)
- Below ~250 px face width the eyes stop matching and late expression edits
  stop reading. `[IL]` (a3 §Verbatim, and still)
- `portrait` means head and shoulders; it defeats a head-only crop whatever
  the negative bans. `[all]` (a4 §Dropped: a head-only)
- On IL, eye tags scale the face the checkpoint already draws; the checkpoint
  sets the face. Eye weights do not transfer across checkpoints or framings.
  `[IL]` (a1 §The base draws the face; a1 §A weight is only right)
- Face shape and eye choice are compared against the bust pick; a style probe
  is always shown next to bust. `[Anima]`

## Does not work

- Pixel-counting irises or eye ratios on small crops — contaminated by crop
  edges and hair; the eye decided in one look. `[all]` (a3 §2026-08-19 — `flop` takes 1.15)
- Optimising eye-to-face ratio as the quality target; everything unmeasured
  drifted. `[all]` (a1 §Correction: eye ratio)
- `smirk` on Anima bust: it draws a duck mouth. `light smile` 1.25 +
  `jitome` 1.4 is the bust look. `[Anima]`
