# Delivery: finalize, palette, matte, stroke

The delivery identity (backdrop `#c7e5e9`, purple stroke, acceptance band)
lives in `domain/yukari/delivery_style.py`, fingerprinted by
`scripts/delivery_check.py`. When `--accept` records a change, rewrite
"The look now" below. Tags and `a<n> §` pointers: see
[`docs/README.md`](../README.md).

## The look now

- Finalize delivers the raw Anima pick: matte, repin, backdrop and purple
  stroke, no redraw. An IL redraw (hassaku-il-v22 at 2560, d0.4) is opt-in
  per request. Defaults: `FINALIZE_DEFAULTS` in `delivery_style.py`. `[Anima]`
- Finalize defaults: repin on, backdrop `dots`, stroke light from `n`. The
  diagonal stripes + faint focus lines backdrop is `backdrop=stripes`. `[Anima]`
- Rim is `#885b80`, polygonised (Douglas–Peucker, eps 0.5%) for a hand-cut
  look; eps stays well under the white band or the outline cuts inside it.
  Light-direction shading on the purple rim, 8 directions. `[all]` (a6 §Hand-cut sticker rim)
- Matte: RMBG BiRefNet-general + 1 px key alpha + projected despill. Anima
  bust renders on green; hair-enclosed green gets `enclosed_cut`. Cast
  shadows: `soft_clamped` + `shadow_cut` (#183). `[Anima]`
- Detail density follows the redraw canvas: draw at 2560, shrink to 1536. `[IL]`

## Holds

- Cut the delivery silhouette with a matte model on the raw, pre-correction
  image, never from colour: repin can cut into pale hair. `[all]` (a5 §納品のシルエット)
- A computed stroke replaces model-drawn outlines: two concentric model rims
  do not survive seeds, and a band has no tag vocabulary. `[all]` (a5 §縁の出し方比較; a4 §A second marker outline)
- `white outline` in the prompt also bought a flat background; without it,
  background flatness fell to 3 of 6 seeds, so a flatness screen is required.
  `[IL]` (a5 §追試)
- Straight-alpha layers (backdrop, purple, white, figure) let rim width and
  colour change without re-running the repaint. `[all]` (a5 §レイヤー分離)
- Crop first, then stroke: a stroke drawn before a crop has no rim at the cut.
  `[all]` (a5 §2026-08-28 部屋着のピンク)
- Transparent finalize composites the bands first and cuts the backdrop after;
  the colour test is bounded by the compose's own band geometry or it holes
  pale hair. `[all]` (a6 §`cut_backdrop`)
- Stroke width is a share of the figure's own white band, not the canvas; a
  median band estimate is "not found" past ~50% contour without outline. `[all]` (a4 §肩紐; a4 §The purple stroke's automatic width)
- Backdrop recolour fringe: shift pixels by their backdrop share inside a 1 px
  feather; tolerance cannot separate fringe from skin. `[all]` (a4 §「じゃぎってる」; a4 §「輪郭の雰囲気)
- The enclosed-pocket repaint cannot tell a gap from a pale detail inside the
  figure; per-render tolerance, not a new default. `[all]` (a4 §`deliver.py --enclosed-tolerance`)
- Seat layered delivery: backdrop → seat → frame → figure, re-running
  `clean_background` with the seat pasted into the backdrop. `[Anima]`

## Palette (repin)

- Repin per hue window, not one saturation scale; a light-band normalisation
  computes the factor per render. Fixed per-pose factors did not generalise
  (×0.30 vs ×0.55). `[all]` (a5 §2026-08-28 パレットを明示化; a5 §repin 採用)
- Every accent family needs its own window: pink in the purple window (170–225)
  goes lavender; cyan inner hair has 115–140, exempt from the dark-band grey.
  `[all]` (a5 §部屋着のピンク; a6 §repin's cyan)
- A correction built to subtract damages an in-band render (crushed irises,
  pink blotches); skip it, do not shrink it. `[all]` (a5 §補正は)
- Hue interpolation goes the short way round, or purple → skin crosses green at
  every feather. Skin restoration fires only where skin was painted. `[all]` (a5 §肌ピン自体)
- Despill on a yellow-green key pinks the skin at the excess-24 edge; limit it
  to the edge band. `[Anima]`
- `recolor` is for the lap palette; a sketch delivery uses repin or nothing. `[all]`

## Redraw passes (IL opt-in)

- A redraw is not a magnification: it adds saturation bumps and fringing to a
  flat style. Lanczos keeps an approved look. `[all]` (a5 §hige の印刷経路)
- The route decides the surface, denoise the invention: image-space Lanczos at
  0.45 beats latent bicubic at 0.60. Latent upscale leaves banding in flats.
  `[all]` (a2 §Refining a chair render; a2 §Image-space upscaling)
- A refine only thins the line; do not add one the first pass does not need.
  `[all]` (a2 §`prone`)
- Apply corrections in one pass from the last approved render; stacked passes
  drift the palette. `[all]` (a2 §Corrections go on in one pass)
- Rough look needs both halves: drop the finish tags and ban clean-line tags.
  Hand-drawn line on IL came from removing the style block and texture bans.
  `[IL]` (a5 §2026-08-29 ラフ化; a6 §On IL the style block)
- Pass-2 gloss regression: ban `detailed shading, heavy shading, impasto,
  painterly` in the pass-2 negative only. `[IL]` (a4 §「線画の絵柄)

## Does not work

- Post-process that removes part of the picture to make it acceptable. `[all]`
- Handdrawn tag on finalize; d0.55 plain is the loose hand-drawn dial. `[IL]`
- A greyscale init for colourising a rough: no colour comes out. `[all]` (a5 §ラフに色を乗せる)
- See-through part decomposition off-front: drops legs and legwear, and its
  output is a redraw. `[all]` (a5 §See-through)
- Chaining two same-size image-space passes to rough then colour. `[IL]` (a5 §2026-08-29 再考)
