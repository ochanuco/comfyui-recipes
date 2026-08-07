# DQ3 sage — where the recipe stands

Everything below is already the default in `scripts/queue_dq3.py`. The bare
command reproduces it:

```bash
uv run scripts/queue_dq3.py --job sage --pose sitting --width 1024 --height 1536
```

## Accepted results

| prompt id | file | seed | why it was kept |
|-----------|------|------|-----------------|
| `a962cf99` | `ln-A-mid_00001_` | 2557902837 | the line/border balance that settled it |
| `557b4ff9` | `qs-sit_00002_` | 2557902837 | best overall before the line change |
| `372207ef` | `mash-sit_00001_` | 3992482423 | colour and linework mashup |
| `9d6f4d27` | `sel-sitting_00003_` | 3931122703 | thigh volume |
| `53c5e9f6` | `sel-reaching_00002_` | 3062102535 | white border |
| `79168c71` | `sel-sitting_00002_` | 3992482423 | pose |

All six poses work: **sitting, kneesup, reaching, lookback, standing, bootoff**.
standing and bootoff were broken for a long time and the cause was the face
preset, not the poses — see below.

## Settings that took a while to find

- **Checkpoint moved the art style further than any prompt work.** novaAnimeXL →
  Amanatsu was the single biggest change of the session. NoobAI XL was tried and
  rejected: flat and saturated, and it lost the legwear quality.
- **`quarterstaff`, never `staff`.** Danbooru's `staff` is overwhelmingly the
  ornate magical kind; thin/simple/plain and negating `ornate staff` all failed
  against it. Renaming the object worked first try.
- **Eye size tops out around 1.65.** At 1.75 the scarf disappears; at 1.9 a spare
  eye gets drawn in the background. Past that, raise the eye LoRA instead — LoRA
  weight costs no prompt attention.
- **Hair is dark blue over black, shading to black.** Blue in the shadows *and*
  in the base came out light all over.
- **Legwear is opaque black.** `sheer legwear` had been held in check by the old
  bulky negative; once that was pruned it took over and the legs went grey.

## Failure modes and what actually fixed them

- **IPAdapter** was abandoned after ~40 images. On Amanatsu it duplicates the
  figure and blows out the saturation. `--ref-*` still works but is not in the
  recipe.
- **The prompt is saturated.** Adding weighted tags visibly costs the existing
  ones: two thigh tags flattened the shading, seven sleeve tags rewrote the
  outfit, and maxing the eye tags pushed out the style and the scarf. Prefer
  replacing a tag over adding one.
- **The negative prompt grows and nothing prunes it.** It reached 255 tags
  against 100 positive, which flattened and brightened everything: mean luminance
  drifted 140 → 228. It is 125 now. Re-check it whenever the goal changes.
- **A negative that describes a legitimate shape deletes that shape.**
  `ragged`/`tattered` shrank the cape, which genuinely has a pointed hem.
- **Listing a thing's parts in the negative summons them.** `staff head, orb,
  crystal, spikes` produced a more elaborate staff, not a plainer one. Name the
  symptom instead.
- **CLIP has no negation.** `no ornament` in the positive prompt asks for an
  ornament.
- **Every negative eventually fights a later request.** `latex`/`wet` blocked the
  legwear gloss; `cel shading`/`flat shading` blocked anime shading; `hood`
  blocked a hooded character; `white outline` blocked the border that was later
  wanted; the anti-thick-line block blocked the bold lines that were wanted last.

## Per-character structure

Characters own their legwear, franchise tag, face preset, and negative removals,
because the sage's tuned prompt turned out to be actively hostile to another
character — the `moe` face melted Yukari into noise. Poses can drop both class
tags and negative terms (`POSE_TAG_DROP`, `POSE_NEG_DROP`).

Never drop a whole negative block by name: doing that for a hooded character took
the distortion terms with it and the render melted.

## Eye size — measured, and why tags cannot get there

Measured off `ref-eye4`/`ref-pose-headrest` against a grid:

| | reference | what we produce |
|---|---|---|
| eye height / face height | **31%** | 15-18% |
| iris / eye opening | **90%+** | 60-70% |

Tags cap out well below this. `(large eyes:1.75)` loses the scarf, `1.9` draws a
spare eye in the background, and even `1.85` plus `(huge eyes:1.3)` lands at
about half the reference ratio. The eye LoRA does not help either -- ramping it
0.7 / 1.0 / 1.4 / 2.1 changes the iris *quality* (brightness, highlights) and
leaves the *size* untouched; 2.1 breaks the image outright. 1.0 is prettier than
the 0.7 default and costs nothing.

A ratio is a property of the art style, not something a prompt can state. The
next thing to try is a 2000s moe style LoRA, which should bring the proportion
with it and let the eye tags come back down:

| model | id | trigger |
|-------|----|---------|
| moe style | 2297509 | `2000s_moe_style` |
| moe style 2000s | 2299478 | `2000s anime, 2000s artstyle` |
| Mozudoll-style | 2784868 | `moe (mozudoll)` |

Downloading them needs the Civitai token; `op://Personal/jv36itf5rqh5sneynlgpbk47k4/credential`
stopped resolving at the end of the session.

## Checkpoint swap: reverted (see the correction below)

**The default is amanatsu-il-v11 again.** What follows describes the moe
experiment, kept because the measurements are real, but the conclusion it
reached was wrong.

### The measurement that led there

`moe is all you need` (NoobAI/Illustrious v-pred v2) reaches the proportion that
tags and LoRAs could not:

| | eye height / face height |
|---|---|
| Amanatsu | ~20% |
| **moe-vpred-v2** | **~31%** |
| target | 25% |
| reference | 31% |

Same seed, same prompt — only the checkpoint differs. This is the third time in
the session that changing checkpoint moved the art style further than any amount
of prompt work, and the first two were novaAnimeXL → Amanatsu and the NoobAI
rejection.

**It is v-prediction and must be told so.** `DiffusersLoader` does not read the
scheduler config, so without `--v-pred` the image comes out as coloured noise --
an unmistakable failure, at least. The flag inserts `ModelSamplingDiscrete`
(`v_prediction`, zsnr) between the loader and the LoRA stack.

It is now the default, and `--v-pred` is set automatically from `V_PRED_MODELS`
rather than by hand — the checkpoint knows, the caller should not have to.

```bash
uv run scripts/queue_dq3.py --job sage --pose sitting --width 1024 --height 1536
```

Verified across sitting / reaching / kneesup and on Yukari: eyes large in all
four, black legwear, thigh volume, straight quarterstaff, flat backdrop, and no
sign of the melting that the old face preset caused on Yukari.

**The same tag needs a different weight on a different checkpoint.** Retuned for
moe, with the Amanatsu values in brackets:

| tag | moe | (Amanatsu) |
|-----|-----|-----------|
| `white outline` | 2.4 | 1.6 |
| `thick white outline` | 1.5 | unweighted |
| `grey background` | 1.7 | 1.35 |
| `flat background` | 1.5 | absent |
| `outstretched arms` | 1.6 | 1.4 |

At the Amanatsu values the border did not draw at all and the backdrop picked up
a green or blue cast; `reaching` came out as a sitting pose. Switching back to
`--diffusers-path amanatsu-il-v11` will need those weights lowered again.

`sweet-mix-v14` was downloaded and rejected: its eye proportion matches
Amanatsu's, so it buys nothing here. It is still on disk.

The eye tags can probably come down now that the checkpoint supplies the
proportion; `(large eyes:1.65)` is fighting for something it no longer has to.
That is the first thing to try trimming.

## The iris has to scale with the eye

Switching to moe enlarged the eye but left the iris where Amanatsu wanted it, so
white showed on all four sides — the iris floating in the opening. Same class of
problem as the white border and the backdrop: a weight tuned for one checkpoint
does not carry to another.

`(large iris:1.85)` with `(large pupils:1.7)` fixes it and leaves sclera only in
the corners. `2.0` plus `huge iris` destroys the image outright — it comes back
as coloured blocks, so that is the ceiling.

## Tracing a reference with ControlNet

`--trace-image` runs a reference through Canny and applies it as structure
(`noob-canny-fp16`, chosen because the checkpoint is NoobAI-based; Canny is the
only preprocessor ComfyUI ships, so no custom node is needed).

**ControlNet moves the whole composition, not a feature.** Tracing a face
close-up produces a face close-up: at strength 1.0 the sitting pose was replaced
by the reference's bust framing, and at 0.4-0.6 the two structures simply fought
and cancelled. It is worth using when the framing already agrees with the
reference, and is the wrong tool for borrowing a face while keeping a full-body
pose — which the checkpoint change already solved anyway.

## Correction: eye ratio was the wrong thing to optimise

Rated side by side, the two best results came from **sweet-mix-v14** and
**amanatsu-il-v11** — not from moe, whose eye ratio was the reason it became the
default. moe was picked on a single measured number while the rest of the image
went unassessed, and on fresh seeds it drifts: green hair and red eyes where the
prompt says dark blue, missing forearms, stray colour on the feet.

sweet-mix was rejected for "buying nothing", which was also judged on the eye
ratio alone. It rates as well as Amanatsu and deserves a proper comparison.

Two methodology faults produced this:

- **Seeds were reused.** 2557902837 and 3992482423 got used over and over, and
  they were chosen in the first place because they had produced good results.
  Verifying on seeds already known to work says nothing about stability.
- **One metric stood in for quality.** Eye-to-face ratio was measurable, so it
  became the criterion. Everything that was not measured drifted unnoticed.

Fresh random seeds, and looking at the whole image, are the fix for both.

## A weight is only right for one framing

`standing` and `bootoff` came back as coloured blocks while the seated poses were
fine on identical settings. Dropping the face preset fixed it outright; dropping
the style did not, and Amanatsu broke differently.

`moe` asks for `(large eyes:1.65)`, `(large iris:1.85)`, `(large pupils:1.7)`.
Those are satisfiable when the head fills a good part of the canvas. In a
full-body standing shot the head is small, and a huge iris on a small face has no
solution — the sampler gives up and returns blocks. `moe-far` states the same
intent at roughly half the weight, and `FACE_BY_POSE` hands it to the framings
that need it.

This is the third axis on which a weight turns out not to transfer. The others
were the prompt being saturated (adding a tag costs an existing one) and the
checkpoint changing what a given weight is worth. Now: **the framing changes it
too.** A tag tuned on a close-up will overreach at full-body distance.

## Open, for next time

- `standing` doubles the figure; `bootoff` goes dark.
- Face contour candidates (`cf-A`..`cf-D`) were generated but never reviewed —
  the current default carries `(round face:1.2), soft jawline, small chin`.
- Yukari's `reaching` pose is implemented and unverified.
- `gen_variants.py` (ollama) inherits the full recipe now, but its scene
  vocabulary fights the flat background rule. It needs a pose/expression
  vocabulary instead of a setting one before it is useful.
- Background colour is not worth chasing in the prompt — three attempts landed on
  yellow, cream and pale blue. Generate a flat field and set the exact value with
  `scripts/recolor_bg.py --color "#C1C3C2"`.
