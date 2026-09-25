# Legwear and costume

Tags and `a<n> §` pointers: see [`docs/README.md`](../README.md).

## Current decisions

- One garment on the leg. The official design draws one; two layers (tights
  under knee-highs / thighhighs) are retired after long failure. `[all]` (a2 §Two garments on one leg)
- Canonical legwear is black sheer-gloss for every pose (`LEGWEAR` in
  `yukari/costumes.py`); axes opaque / sheer-gloss / sheer (PR #230, #239).
  `[Anima]`
- `thin translucent legwear` draws vertical stripes on the leg and no negative
  removes them; the block uses `skin visible through legwear` (PR #253). `[Anima]`
- Gloss: `shiny pantyhose` 1.3 is the ceiling, and an IL redraw evens the
  gloss out. `[Anima]` On IL, unwanted gloss was held down by four shiny
  words in the negative; removing body-mass tags did nothing. `[IL]`
- Costume is the official one by default; garment colours move by the black
  ban in the negative, and delivery repins them back to black. `[Anima]`

## Holds

- Sheerness cannot be added afterwards: masked refine at 0.55–0.95 stayed
  opaque; img2img cannot recolour a garment (black → white reached L 39 of
  145). Ask for it at generation, or paint numerically then redraw low. `[all]` (a1 §Where a colour change belongs; a5 §根本原因)
- Colour inside a hue family (white → cream) ignores weight and belongs after
  the sampler; across categories (white → black, opaque → sheer) it lands in
  the prompt. `[all]` (a1 §Where a colour change belongs)
- Translucent tags leak colour with a fixed direction: `skin visible through
  pantyhose` pink, `sheer legwear` green. A strong colour anchor stops it.
  `[IL]` (a5 §膝枕: 透けタグの色漏れ地図)
- Unspecified garment colour randomises across seeds; presence is stable.
  Pin colours with a tag. `[all]` (a5 §roomwear costume 初回)
- Symmetry answers only to the negative guard (`mismatched legwear`,
  `single thighhigh`); asking for matching legwear made it worse. `[all]` (a1 §Mashing two renders)
- A layer boundary is read as a garment edge: a hem above a second colour
  reads as bike shorts whatever the colours. `[all]` (a2 §「タイツになってないな)
- Coverage answers to the noun, not the weight: swap the garment word. `[IL]` (a1 §Garment length)
- A garment-recruiting tag (`oversized shirt`) pulls a button-front
  shirt-dress; remove it and ban `buttons` / placket too. `[all]` (a5 §2026-08-29 `cackle`)
- Swapping a garment onto a pose is two edits: the positive block and the
  pose's opposing negative ban. `[all]` (a5 §2026-08-28 新ポーズ `recover`)
- Gate costume behaviour on set membership (`costume in SHOD`), never on
  equality with the one costume that existed then. `[all]` (a4 §`fitness`)
- A guard may exist for a costume reason, not a pose reason; ask why before
  releasing it. `[all]` (a4 §`fitness`)
- A full-body pose with feet in frame needs a footwear tag or the legs end in
  stumps. `[IL]` (a3 §The legs were never)
- A structure tag (straps, halter) applied globally brought intruders; keep it
  as a per-pose splice. `[IL]` (a3 §The ears were already off)
- A splice goes silently no-op when the shared default rises to its value; the
  costume contract checks declared exceptions exist. `[all]` (a3 §The ears were already off)
- A costume change silently breaks per-pose splices of every pose not
  re-rendered right after. `[all]` (a5 §`stand` が銀紙ノイズ)

## Does not work

- Directional gradient legwear (purple thigh → black ankle): 11 arms, the
  model puts the dark end where contrast is needed. Gradient words also turn
  brown on Anima. `[all]` (a3 §The gradient direction is ABANDONED)
- Naming a second colour to place it: it appears, but not where asked. `[IL]` (a3 §Naming the colour)
- `muted color` / `limited palette` to calm legwear: desaturates the backdrop
  too. `[IL]` (a5 §膝枕深掘り)
- Post-hoc painting of tights colour or sheerness: rejected as degradation. `[all]`
- Pale-purple pantyhose: reads as bare white skin. `[Anima]`
