# Hands, feet and repair

Tags and `a<n> §` pointers: see [`docs/README.md`](../README.md).

## Holds

- Digit count is a repair problem. Positive toe tags shift the palette,
  negative toe bans melt the separation, a redraw reproduces pass 1. The fix
  is request kind `repair`: DWPose circle mask, crop-and-stitch at a size the
  model draws hands at, d≈0.6. `[all]` (a6 §Toes are a repair)
- Mask from the structural root: an ankle-centred circle (~0.3 shin radius),
  not the toes. A hair/sleeve order defect is fixed from where the lock meets
  the head. `[all]` (a6 §Toes are a repair; a5 §膝枕 最終確定)
- The repair prompt is region-local. Whole-picture tags with no referent in
  the mask get spent inside it (breath puff by a foot, hood tags on a leg);
  full-prompt replacement, not append. `[all]` (a6 §Toes; a2 §The lower body on; a2 §The bare back)
- Editing `prompt.positive` wholesale drops identity tags; patch
  `prompt.positive.<part>`, the identity guard checks it. `[all]`
- `VAEEncode` + `SetLatentNoiseMask` keeps the old drawing as context. Never
  `VAEEncodeForInpaint` below denoise 1.0 (grey; deleted the hand 6/6). `[all]` (a2 §Hands: refine in place)
- Hands under ~120 px are blobs: crop, upscale ×2, fix, paste back. A region
  whose content depends on body layout needs full-frame context. `[all]` (a2 §Hands; a2 §Context size decides)
- Denoise ladder in a masked hand: 0.45 sloppy, 0.65 restructures, style-only
  polish below 0.55. Unmasked, stay ≤0.25–0.3. `[all]` (a2 §Hands; a1 §Masked refine)
- Region parts on Feet XL / Hands XL LoRA in the crop only (`lora: true`) got
  toes 4/4. Frontal soles need rectangular `regions`, and start from a plain
  finalize delivery. `[all]`
- A visible hand failure is an occlusion problem first: a sleeve tag hiding
  the hand, not anatomy. `[all]` (a1 §The hands were hidden)
- A naming-the-feature lever beats naming the count (`toe scrunch` curled toes
  read as correct); stay below the weight where it melts separations. `[IL]` (a3 §`(toe scrunch:1.35)`)
- Opaque tights need no countable toes: judge against the garment. Frontal
  soles are avoided by default; not facing the sole fixes most toes. `[all]` (a3 §The palette breaks)
- Rebuild beats erase: carving out a defect gets refilled with a new one (4/4);
  mask the whole zone. `[all]` (a2 §Rebuild beats erase)
- A negative cannot remove a seed-baked object; masked redraw + composite
  can. Baked buttons survive even a 0.6 masked reroll; shape-detected fill +
  soft mask at 0.35 removes them. `[all]` (a2 §Removing baked-in; a5 §部屋着 glo2s4)
- A cheap pass deletes, it does not add: 0.35 removes a placket, drawing straps
  onto skin needs 0.6. `[all]` (a2 §A cheap pass deletes)
- Unpainted regions (pink sketch outline, no flat) are reachable at 0.6 if the
  refine negative names the state (`sketch, lineart, unfinished`). `[all]` (a4 §The arm that was never painted)
- Stray dots after a refine: connected-component detect + fill, not another
  pass. Restore a damaged contour by linear interpolation between anchors. `[all]` (a5 §腰リボン上端)
- Recolour a well-shaped, wrong-coloured mass before re-rolling it. `[all]` (a2 §Rebuild beats erase)
- Masks go stale when the figure moves; re-cut from the current render and
  exclude backdrop. `[all]` (a2 §The socks' own design)
- A masked refine thickens and darkens the line inside the mask; compare
  against an untouched region of the same picture. `[all]` (a2 §The lower body on)
- A handshape tag draws its own construction (`clenched hand` → fist, not V).
  `[IL]` (a4 §指が正常化)
- A second pass draws a new hand rather than enlarging the old one; Lanczos
  keeps it pixel-identical. `[all]` (a4 §It is not the resolution)

## Does not work

- Prompt guards for toes and fingers (count words, negative bans). `[all]`
- Seed stacking to chase toe repair; it lands about half the time. `[all]`
- Anatomy negatives (`bad hands`, `extra fingers`) when the hand is hidden. `[all]` (a1 §The hands were hidden)
- Geometric warps to add a missing joint: the complaint moves. `[all]` (a2 §The prone legs)
- Masked refine on a region a pose estimator cannot read as a limb; it needs a
  new pose, not polish. `[all]` (a2 §The prone legs)
