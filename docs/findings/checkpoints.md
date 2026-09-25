# Checkpoints, LoRA and reference tools

Model files and provenance are in [`docs/models.md`](../models.md); the
Anima recipe itself in [`docs/yukari/anima.md`](../yukari/anima.md). Tags and
`a<n> §` pointers: see [`docs/README.md`](../README.md).

## Holds

- Stage 1 is Anima Turbo (10 steps, CFG 2, euler, ~33 s a picture). CFG 1
  switches the negative off. `[Anima]`
- Style on Anima moves with artist tags (`@oshiki hitoshi` 0.85,
  `@yoshikawa hideaki` 0.5), not with a sketch LoRA; the sketch LoRA route is
  withdrawn. An artist the user excluded is patched out even if a default
  still carries it. `[Anima]`
- On Turbo a weight under 1.0 still registers: `oshiki` at 0.85 keeps the
  thick black line, `yoshikawa` at 0.5 stops the face lengthening and the
  eyes shrinking, and also suppresses the handwritten text `oshiki` draws
  alone. `[Anima]`
- The AI look on IL was the recipe's own style block and texture bans, not the
  checkpoint: nine checkpoint swaps under the unchanged prompt all rated
  bad/neutral; removing the block let sketch LoRAs draw. Separate the two by
  one-variable blind A/B. `[IL]` (a6 §The AI look; a6 §On IL the style block)
- A checkpoint's best face and best palette can be different checkpoints; on
  IL, the checkpoint moved style more than any prompt change. `[IL]` (a1 §The base draws the face)
- The IL redraw needs an Anima source (a `UNETLoader` in its base graph);
  other sources are delivered with `deliver_only`, LayerDiffuse bases refused. `[all]`
- `/object_info/<node>` returns 200 with `{}` for a missing node; check the
  body, or let `/prompt` report `missing_node_type`. `[all]` (a3 §「解像度を上げれば)
- No upscale model is installed on the worker; Lanczos is the only purely
  bigger route. `[all]` (a4 §Purely bigger)

## Reference tools

- ControlNet moves the whole composition: a traced framing overrides the pose.
  A partial pose skeleton is worse than none. `[IL]` (a1 §Tracing a reference)
- A pose skeleton was holding composition, not just anatomy; do not remove it
  to isolate another variable. `[IL]` (a2 §Two garments on one leg)
- A lineart ControlNet strong enough to carry a hairstyle carries unwanted
  structure too; ~0.35 kept both. Area tags pass at any strength, outline
  tags lose above it. `[IL]` (a1 §Swapping the character)
- Region prompts (`ConditioningSetMask`) beat weights for two garments: each
  region carries the whole prompt, the base region is masked out,
  `set_cond_area: default`. Debug with an absurd colour first. Colour distance
  from neighbours, not weight, wins a region. `[IL]` (a2 §Regions beat tags; a2 §Both at once)
- LayerDiffuse removes redrawn furniture that negatives cannot; the LD alpha's
  white haze is cut. `[all]`

## Does not work

- IPAdapter for costume transfer: across 4 poses, no palette gain and a 7–15%
  thicker line. Earlier "it works" came from a confounded baseline. `[IL]` (a2 §2026-08-17 -- the generation test)
- Checkpoint swaps to fix a look the recipe's own blocks were causing. `[IL]` (a6 §The AI look)
- Krea2: tag prompts draw someone else, CG paint. `[all]`
- Detail Daemon: numbers rise, the picture does not improve. `[IL]` (a1 §Detail Daemon)
