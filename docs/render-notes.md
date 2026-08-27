# Render notes — what has been measured, per character

> The characters described here belong to their original works — see
> [Derivative work](../README.md#derivative-work) in the README. Rights in
> them rest with their creators, not with this repository.

Renamed from `docs/dq3-sage-notes.md`. Eleven tag messages still cite the old
path; they are records of where the file was at the commit they point to, and
they stay correct there. Nothing else in the repo referenced it, which is why
the rename was cheap. `scripts/queue_dq3.py` keeps its name for now — that one
is named by four files and five tags, so it is a separate decision.

The file started as the sage's recipe and is no longer only that: Yukari,
Momiji and Takao all have sections below, and the later findings — the surface
block, the pose-block ceiling, the volume tags — apply to whichever character
is being drawn.

The sage's own defaults are still the defaults in `scripts/queue_dq3.py`, and
the bare command reproduces the state this file opened in:

```bash
uv run scripts/queue_dq3.py --job sage --pose sitting --width 1024 --height 1536
```

That command predates the rough-sketch work. For the sage as he stands now, see
`pick/sage-parts` and the surface-block section near the end.

## Accepted results

| prompt id | file | seed | why it was kept |
|-----------|------|------|-----------------|
| `a962cf99` | `ln-A-mid_00001_` | 2557902837 | the line/border balance that settled it |
| `557b4ff9` | `qs-sit_00002_` | 2557902837 | best overall before the line change |
| `372207ef` | `mash-sit_00001_` | 3992482423 | colour and linework mashup |
| `9d6f4d27` | `sel-sitting_00003_` | 3931122703 | thigh volume |
| `53c5e9f6` | `sel-reaching_00002_` | 3062102535 | white border |
| `79168c71` | `sel-sitting_00002_` | 3992482423 | pose |
| `f066dccc` | `abc-F-softline_00001_` | 4051776310 | ab-C rescued by self-trace: same composition, no intruder (tag `pick/abc-F`) |
| `23e7f00f` | `mn-h-grey_00001_` | 1117511306 | the colouring. `--minimal` on Hassaku: flat field, thin tinted line, no cast shadow, no gloss (tag `pick/mn-h-grey`). Reproduced by bare `--job takao --pose lookback --width 1024 --height 1536 --minimal --diffusers-path hassaku-il-v22` **at commit `6312637`** — `LEGWEAR_BY_JOB` landed afterwards and puts thighhighs on her, so the bare command no longer rebuilds it. The graph is kept in `mn-h-grey-63126379.json` and in the PNG |
| `a8e9bebb` | `gl-sg-1117511306_00001_` | 1117511306 | the sage in black glossy tights, no brown, no fibre, no vinyl (tag `pick/gl-sg`) |
| `ab7a84cd` | `yk-3409564303_00001_` | 3409564303 | Yukari on the same recipe, single figure (tag `pick/yk-min`) |
| `2f06db87` | `yk-bd-3409564303_00001_` | 3409564303 | the same with `--border`. The white sticker outline is clean; note it also encloses a backdrop eye at top left, which was accepted rather than fixed (tag `pick/yk-border`) |

The last three all rebuild from the same shape, with no base named — `BASE_BY_JOB`
now points every character at Hassaku:

```bash
uv run scripts/queue_dq3.py --job <sage|takao|yukari> --pose <sitting|lookback> \
  --width 1024 --height 1536 --minimal --face moe-mid-noeye [--border] --seed <N>
```
| `cac2cf43` | `bm-moevpred_00001_` | 1117511306 | the face. `moe-vpred-v2` draws the small round face with large round irises that the identical tags do not produce on any other base — see the base sweep below. Now needs the base named: `--job takao --pose lookback --width 1024 --height 1536 --style cel-plain --flat-paint mild --diffusers-path moe-vpred-v2` (verified byte-identical) |
| `1126385e` | `takao-canon_00001_` | 618823993 | Takao in the sage's art style, canon colours, her shadow on the wall (tag `pick/takao-canon`). Reproduced by bare `--job takao --pose standing --width 1024 --height 1536 --diffusers-path hassaku-il-v22 --style cel-plain` — prompt verified byte-identical against the PNG |

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

`--trace-image` applies a reference as structure. `--trace-mode` picks what gets
extracted from it, and each mode needs a ControlNet trained on that signal —
`TRACE_MODES` holds the pairing, so `--controlnet-name` is now only an override.

**ControlNet moves the whole composition, not a feature.** Tracing a face
close-up produces a face close-up: at strength 1.0 the sitting pose was replaced
by the reference's bust framing, and at 0.4-0.6 the two structures simply fought
and cancelled. It is worth using when the framing already agrees with the
reference, and is the wrong tool for borrowing a face while keeping a full-body
pose — which the checkpoint change already solved anyway.

**That was Canny's property, not ControlNet's.** Canny reproduces every outline,
so the reference's costume, proportions and framing come along with its pose. It
was the only mode because it is the only preprocessor ComfyUI ships, not because
it was the right signal.

### `--trace-mode openpose`

The weights are `noob-openpose-fp16`, the same r3gm fp16 mirror the Canny model
came from; ComfyUI reads the bare diffusers `diffusion_pytorch_model.fp16.safetensors`
once it is renamed, and the two files differ by 32 bytes in size, which is how
the mirror was identified.

**Everything here depends on the skeleton actually being found, and mostly it is
not.** Pass `--save-trace` and look at it before believing any result. An empty
skeleton is a black frame, and a ControlNet conditioned on a black frame fails
silently -- the render still comes out, still varies with the seed, and looks
like an ordinary result. A whole session was spent comparing images that had no
skeleton behind them at all.

**DWPose finds nothing in this material.** Its yolox person detector returned
zero boxes on every reference tried, under both its torchscript and its onnx
weights. The log gives it away: `DWPose: Bbox NNNms` appears, and no `Pose` line
ever follows. `--trace-backend openpose` (the default) uses the older estimator,
which does not go through yolox and does find bodies here. `dwpose` is kept only
to retest it.

**Coverage varies enormously by reference, and it is the thing that decides the
render.** Non-black fraction of the skeleton image, measured on the same five
references:

| reference | skeleton | render |
|---|---|---|
| `ref-pose-bootoff` | 1.887% | clean, 7-8 heads tall |
| `ref-pose-kneesup` | 0.517% | **two figures, 3 heads tall** |
| `ref-pose-abovestand` | 0.291% | — |
| `ref-eye3-purple-gradient` | 0.000% | — |
| `ref-yukari-rabbit-hoodie` | 0.000% | — |

**A partial skeleton is worse than none.** The 0.5% one produced a doubled
figure; the empty ones never did. Half a body is a contradictory instruction and
the sampler resolves it by drawing another person. Treat anything under roughly
1.5% as unusable rather than weak.

**A complete skeleton fixes the proportions.** The 1.887% render came out 7-8
heads tall where every previous `standing` attempt had squashed to 2-4.

**And it suppresses the backdrop intruder, without eliminating it.** Five seeds,
`ref-pose-bootoff` as the reference, the trace the only difference:

| seed | trace off | trace on |
|---|---|---|
| 3584446990 | **intruder** | clean |
| 812365471 | clean | clean |
| 1947558203 | **intruder** | clean |
| 4051776310 | **intruder** | silhouette only, no face |
| 1730948821 | **intruder** | **intruder**, smaller |

Four of five produce it untraced; three of those five come back clean with the
trace, one keeps a faceless shadow, and 1730948821 keeps the intruder outright.
So this is the first thing that has moved it at all — the nine prompt-side
attempts recorded above moved it none — but it is not a fix. It fits the reading
there: the model fills empty backdrop with another character, and a skeleton
occupies some of that space. Where the skeleton does not reach, the intruder
still fits.

Do not conclude from three seeds. At three this looked like a clean two-for-two
removal; the counterexample was in the next two.

**The skeleton takes the framing with it.** On two of three seeds the trace
pulled the camera in to knee height despite `full body` in the prompt — the
skeleton's bounding box wins.

**Camera distance is the skeleton's share of the frame, and it trades directly
against the intruder.** Padding the reference (`sips --padToHeightWidth`) shrinks
the skeleton inside the canvas and pulls the camera back:

| padding | skeleton | 812365471 | 1947558203 |
|---|---|---|---|
| none | 1.887% | knees up, clean | knees up, clean |
| 35% | 1.250% | **full body, intruder swarm** | **full body, clean** |

Both seeds gained the full body. One of them gained six extra eyes with it —
and that seed had been clean untraced.

These are one mechanism seen from two sides. The skeleton suppresses the
intruder by occupying the space it would be drawn in, so any empty margin
deliberately created for framing is margin handed back. Framing and a clean
backdrop are bought from the same budget; there may be no setting that gets
both on every seed.

Detection fails on strong perspective, on hair that covers the silhouette, and
on anything cropped above the legs. Both detectors are trained on photographs.

- **Hands and face are off by default** (`--trace-hands`, `--trace-face`). Both
  pin something the prompt already owns: hand keypoints hand the sage a grip
  copied from whatever the reference was holding, which fights the quarterstaff,
  and face keypoints override the face preset and the `CHECKPOINT_TUNING` behind
  it.
- **`--trace-strength 0.6` / `--trace-end 0.5` are Canny's numbers.** They let go
  of the structure halfway, which is right for outlines and too weak for a pose.
  1.0 / 0.85 is what the working render used.
- The reference is centre-cropped to the render's aspect ratio by an `ImageScale`
  node, so it can be dropped into `input/` at any size. The skeleton is stretched
  to the canvas rather than letterboxed, so without that the proportions arrive
  squashed.

### `--pose-text`, which is independent of all the above

**Let the prompt frame and the skeleton pose.** Dropping `standing` and keeping
`full body` is what stopped `standing` shredding the costume into ruffles:

```bash
uv run scripts/queue_dq3.py --job sage --pose standing --width 1024 --height 1536 \
  --diffusers-path hassaku-il-v22 --style cel-plain --pose-text "full body"
```

This was found with a trace attached but the skeleton empty, so it is a
prompt-side result and owes nothing to ControlNet. Whether the pose word is
harmful on its own, or only when a real skeleton disagrees with it, is untested.

**Do not drop the pose text entirely.** `--pose-text ""` removes `full body`
along with `standing`, and the render collapses into mosaic tiles under both the
full and light negatives. The prompt has to keep saying how far away the camera
is; the skeleton never states that.

On macOS, `comfyui_controlnet_aux` is registered with `install_requirements`
off: its pinned `onnxruntime-gpu` has no macOS wheel and would abort
`install-custom-nodes.sh` under `set -e`. See README for the manual dependency
list.

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

## Second correction: the checkpoint was not the problem, the face weight was

Two more moe images were then rated good — `standing` and `bootoff`, the two
poses recorded above as broken. Both used the halved `moe-far` face. Lining every
rating up:

| rating | checkpoint | face | pose |
|--------|-----------|------|------|
| ◎ | sweet-mix-v14 | `moe` (1.65) | sitting |
| ◎ | amanatsu-il-v11 | `moe` (1.65) | sitting |
| ◯ ×2 | moe-vpred-v2 | `moe-far` (1.3) | — |
| good ×2 | moe-vpred-v2 | `moe-far` (1.3) | standing, bootoff |
| △ | moe-vpred-v2 | `moe-far` / none | — |

Every acceptable moe result carries `moe-far`. The full-weight face is what
produced the coloured blocks, not the checkpoint — so the fix was never to
abandon moe, only to stop asking it for an eye it cannot draw.

**Tuning now belongs to the checkpoint.** `CHECKPOINT_TUNING` maps a checkpoint
to its face preset and to weight substitutions applied to the finished positive
prompt. Amanatsu's numbers stay inline as the defaults; moe's overrides live in
the table, so one flag switches everything at once:

```bash
uv run scripts/queue_dq3.py --job sage --pose standing --diffusers-path moe-vpred-v2
```

Verified tag-for-tag against the prompts ComfyUI recorded for the two liked
images, and the Amanatsu prompt is byte-identical across all six poses and both
characters.

## Hassaku, and the figure it draws in the backdrop

`hassaku-il-v22` (Hassaku XL Illustrious v2.2, John6666's diffusers mirror)
reaches a larger eye than either Amanatsu or moe and keeps the white border and
the straight quarterstaff. Two things needed tuning and one could not be tuned
at all.

- **The scarf disappears under the cape.** `(teal scarf:1.35)` brings it back in
  every frame.
- **`black tinted shadows` is load-bearing.** It was dropped along with the other
  shadow tags, and on its own that one removal washes the entire image out: mean
  luminance 115 -> 220 at a stddev of 13, a nearly uniform white field. Trimming
  `(dark shadows:1.3), deep shadow tone` down to `dark shadows` is harmless.
- **A second figure appears in empty backdrop** -- a flat black silhouette with
  eyes drawn into it, beside the sage. Seed-dependent: 2903118455 never shows it,
  4051776310 and 1730948821 always do.

**Nine prompt-side attempts failed to remove that figure.** Recorded so they are
not tried again:

| attempt | result |
|---------|--------|
| raise `cast shadow` / `shadow on ground` | worse |
| raise `dark figure` / `dark shape` / `disembodied eye` / `monster` | worse -- the eye grew |
| cut the positive shadow tags | no effect |
| drop `sticker` | no effect |
| drop `outline, sticker` | no effect |
| drop the whole white-border block | worse -- the figure grew |
| add `silhouette` / `shadow person` to the negative | no effect |
| raise the background weights | no effect |
| add `2girls` / `duplicate` to the negative | worse |
| add `(solo focus:1.35)` | no effect |
| all three of the last kind together | smaller, still there, composition changed |

### Correction: it is a shadow, and that is how to remove it

The claim above that it is not a shadow was wrong. A softedge render put the two
side by side unmistakably: a cast shadow of the sage, offset to the empty right
half, keeping her hair and body outline — with two eyes drawn into its head. The
eyes really are in her own eye style, which is what the earlier reading was
based on, but they sit *on* a shadow rather than replacing one.

The order is **empty space → a shadow is placed there → eyes get drawn into
it**. That also explains the trace results below: a hint that occupies the frame
leaves nowhere to put the shadow, and margin added back for framing hands the
space over again.

**With a trace attached, the shadow negatives work.** Adding
`(cast shadow:1.6), (shadow on ground:1.5), (silhouette:1.4), (dark figure:1.4)`
to the negative removed both the shadow and the intruder on 4051776310, leaving
a small contact shadow at the boots and no damage anywhere else.

This is the same move the table above records as *worse* and *no effect*. It
failed then because there was no trace: the backdrop was open, so pushing the
shadow out of one place left it others. Every entry in that table was measured
without a hint occupying the frame, and none of them transfers.

**`black tinted shadows` still cannot be dropped.** Removing it under these
settings does not wash the image out as recorded — it destroys it outright,
returning a field of pink noise. Negate the shadow; do not stop asking for it.

**Removing it afterwards was tried and reverted.** Repainting the backdrop
cannot reach it: the sticker outline encloses subject and intruder together, so
a border flood stops at the intruder and a connected-component pass returns one
blob covering 75% of the frame. Masking it by chroma and inpainting does work --
the intruder is flat black and white where the staff, cape and gloves are
coloured -- but the result reads as retouched, and building the mask is
delicate: an automatic second pass put the mask over the sage's own hair and the
left tip of her headband, which are as black as the intruder. Choosing a seed
that does not produce it is the cheaper answer.

### Self-trace: regenerating an accepted image without its intruder

The inpainting dead end above has a working replacement: feed the image back to
itself. Copy the output into `input/`, paint the intruder out of the *copy*, and
rerun the original prompt with the cleaned copy as a softedge reference plus the
shadow negatives. The trace pins the composition the seed is loved for, the
cleaned reference no longer asks for the intruder, and the negatives keep the
regenerated backdrop from growing a new one. The release point sets how much
of the original survives: `abc-D` (end 0.4) keeps the composition and lets the
model redraw the rest, `abc-F` (end 0.8) is the accepted balance, `abc-E`
(strength 0.75, end 1.0) is a faithful recolouring of the line art. Held past
~0.8 the trace also carries the reference's *own drop shadow outline*, so the
shadow shape is inherited rather than reinvented — a feature for a rescue,
where the shadow was part of what was liked.

`abc-F-softline_00001_` (tag `pick/abc-F`) is ab-C rescued this way — same
crouch, staff, cape and framing, backdrop holding only her own drop shadow:

```bash
.venv/bin/python scripts/clean_ref_abc.py   # ref-abC.png -> ref-abC-clean.png
uv run scripts/queue_dq3.py --job sage --pose sitting --width 1024 --height 1536 \
  --diffusers-path hassaku-il-v22 --style cel-plain --seed 4051776310 \
  --trace-image ref-abC-clean.png --trace-mode softedge \
  --trace-strength 0.6 --trace-end 0.8 --trace-resolution 1024 --trace-margin 0 \
  --negative-extra "(cast shadow:1.6), (shadow on ground:1.5), (silhouette:1.4), (dark figure:1.4)"
```

`ref-abC.png` is `ab-C_00001_` copied into `input/`. The reproduced negative is
byte-identical to the one `abc-F` embeds (checked against its PNG metadata).

### The cute ones never came from a reference

Looking back across everything accepted so far: the results worth keeping came
from the prompt alone — a pose named in words, the checkpoint free to solve it
with its own proportions, framing and face. The trace pipeline works as
machinery (reference → line art → render, verified on four references), but
its output has not been *cute*. Softedge imports the reference's silhouette
wholesale: body ratios, hairstyle, costume outlines. The tuned look lives in
an equilibrium of checkpoint + prompt weights, and a foreign silhouette drags
the render off it.

The exception proves the rule: `abc-F` is a trace result and it is the
high-water mark — but it is a *self*-trace, so the silhouette it pins is the
checkpoint's own. Tracing works when the outline is already native; it costs
cuteness in proportion to how foreign the reference's proportions are.

Paths that respect this, if pose-from-reference is still wanted:
- **Skeleton, not outline.** Openpose carries joints and nothing else — the
  silhouette stays the model's. Its blocker is detection on illustrations
  (yolox finds nothing), not the concept; `--trace-render-kps` plus edited
  keypoints is the surviving route.
- **Reference as vocabulary.** Use the reference to *name* the pose, then
  drop the image and generate prompt-only — the division that produced every
  accepted result.
- **Loosen the grip.** Lower strength / earlier end is a dial between pose
  fidelity and native proportions, but both ends give up something.

### Skeleton first, outline as a whisper

Tested on `bootoff` (the one reference legacy openpose detects): openpose at
1.0/0.85 owns the pose, plus a second softedge net over the same reference at
low strength (`--trace2-mode softedge`). The native cuteness comes back in
all three, and the whisper earns its keep:

- skeleton only (`wf-op-only`): pose lands, but joints carry no *props* — the
  boot she should be holding rendered as an unreadable dark object.
- `--trace2-strength 0.25 --trace2-end 0.3` (`wf-mix25`): **the sweet spot.**
  The boot in her hand, the belt, the boots by her feet all resolve; face and
  proportions stay fully native. The outline clarifies gesture and props
  without taking the silhouette.
- 0.4/0.4 (`wf-mix40`): proportions still hold, but it starts picking up the
  reference's cast shadow — the takeover begins with the backdrop, not the
  body.

Division of labour: the skeleton protects pose and cuteness, the faint
outline contributes context. The dial's answer is ~0.25/0.3.

### A traced shadow the style refuses to draw becomes an object

Restyling the rescue exposed a failure mode. The trace carries the drop
shadow's outline, and the sampler must put *something* inside it. cel-plain
draws the shadow back (`abc-H`). galge — which has no appetite for hard
shadows, with the shadow negatives pushing the same way — resolved the exact
same outline as a boulder, and on the next try as a wooden chair. Releasing
the trace at 0.4 did not help: the shape is laid down in the first steps.

The fix is the same principle one level deeper: **the drop shadow is also not
the figure, so it leaves the reference too.** It cannot be colour-keyed — at
(59, 59, 87) it is nearly the hair colour — but it has no lineart, so a flood
fill from the corners walks through its soft edge and stops at the figure's
drawn outline (`clean_ref_abc.py` writes this as `ref-abC-clean2.png`). This
is the inverse of the old finding that a border flood *stops* at the intruder:
hard outlines block the flood, soft ones feed it.

- `--negative-preset light` (the galge pairing the style comment suggests) is
  not safe here: it drops the monster/intruder protections and the backdrop
  grew a boulder. Keep `full`; the glow it costs is the lesser loss.
- Restyled renders from the shadow-free reference: the galge pick is `abc-I1`
  and the anime one is `abc-H` (cel-plain with `(dark shadows:1.3)` and
  `deep shadow tone` dropped, `(anime coloring:1.2)` added) — the anime one
  keeps the inherited shadow, the galge one has a bare backdrop.
- galge came out 厚塗り (`abc-G4`) until the paint itself was negated. The
  anti-impasto bundle `(impasto:1.4), (painterly:1.4), (oil painting
  (medium):1.3), (heavy shading:1.3), (detailed shading:1.3), (realistic:1.2)`
  flattened it to the preferred `abc-I1`. Flattening the positive as well
  (drop `detailed skin`/`smooth shading`, add `flat color`/`anime coloring`)
  overshot into plainer fields than the galge look wants (`abc-I2`).
- The backdrop's *brightness* is not pinned by the BACKGROUND block, so some
  seeds come back dark — deep grey-navy field, deeper uniform blues. Both
  sides of the fix work on the same seed; the negative one is preferred
  since it costs no positive attention:
  `--negative-extra "(dark background:1.4), (dark:1.2), dim lighting, underexposed"`.
  But use the narrow `(dark background:1.35)` alone if anything: the full
  bundle's `dim lighting`/`underexposed` also erase the wall-shadow staging
  that makes these read as illustrations rather than design roughs.
- **Where a tag sits changes more than what it says.** Takao's flesh dose
  baked into the middle of the LEGS block darkened the entire palette and
  dropped the shadow staging; the identical tags at the tail of the prompt
  left both alone (verified on one seed both ways, then 4/4 bright on
  random seeds). Body-shape adjustments belong at the end — that is what
  `EXTRA_BY_JOB` is for. This also retro-explains the darkening that was
  first blamed on seed luck above.
- The bundle transfers to cel-plain and is now the `--flat-paint` flag
  (`mild`/`full`, byte-verified against the pt6/pt1 runs). Explored on
  Takao's tagged seed: full kills the legwear gloss outright, mild lands at
  the accepted sage level, which keeps some shine — the sage LEGS block
  asks for it. Positive-side flattening (`anime coloring`) again came third.
  Composition quirks (the wall silhouette, the sporadic duplicate) are
  seed-bound and move with neither bundle. A luminance-variance metric was
  tried as an objective 厚塗り gauge and does not discriminate — palette
  contrast dominates it; the eye stays the judge.

```bash
uv run scripts/queue_dq3.py --job sage --pose sitting --width 1024 --height 1536 \
  --diffusers-path hassaku-il-v22 --style galge --seed 4051776310 \
  --trace-image ref-abC-clean2.png --trace-mode softedge \
  --trace-strength 0.6 --trace-end 0.8 --trace-resolution 1024 --trace-margin 0 \
  --negative-extra "(cast shadow:1.6), (shadow on ground:1.5), (silhouette:1.4), (dark figure:1.4)" \
  --negative-extra "(impasto:1.4), (painterly:1.4), (oil painting (medium):1.3), (heavy shading:1.3), (detailed shading:1.3), (realistic:1.2)"
```

Two things the attempt established on the way:

- **Cleaning the copy is not optional.** Self-tracing ab-C as-is (`abc-B`)
  reproduced the intruder faithfully — softedge hands over every outline in the
  reference, including the one being exorcised. Same lesson as the flowerbed,
  applied to a defect instead of scenery. The paint-out is easy where the manual
  inpaint mask was delicate, because it happens in the *reference*: colour-keyed
  keep-rules for staff/glove/cape with everything else flattened to the backdrop
  grey, and any nick it leaves (a swallowed hair strand) is repainted by the
  model rather than shipped.
- **Set `--trace-margin 0` when self-tracing.** The output already contains
  its own framing, so the usual padding is pure surplus. (It used to be worse
  than surplus: the pad's edge survived HED as four straight lines and got
  rendered as a picture frame, `abc-C`. The margin has since been moved to
  the other side of the preprocessor — the trace is composited onto a black
  canvas, which adds no edge — so the frame is gone at any margin, and
  `ImagePadForOutpaint` is out of the graph. Its `feathering` was tried
  first and does nothing here: it feathers the mask output, not the image.)

Shadow negatives alone, without a trace (`abc-A`), still fail exactly as the
failure table predicts: the backdrop stays open and the shadow keeps its seat.

## The sticker border is optional, and Hassaku is better without it

`--style cel-plain` is `cel` with `(white outline:1.6), outline, sticker`
removed. It was found by accident, as the ablation testing whether the border
block was summoning the intruder -- it was not, and the image was preferred
anyway.

Dropping the border changes more than the outline: the cape spreads wider, the
legwear gloss comes up, and the result reads as an illustration rather than a
die-cut sticker.

```bash
uv run scripts/queue_dq3.py --job sage --pose sitting --width 1024 --height 1536 \
  --diffusers-path hassaku-il-v22 --style cel-plain --seed 4051776310
```

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

Controlled on one collapsing seed (4268811745, Hassaku, prompt-only standing —
the collapse there is duplicated figures, giant eyes drawn straight onto the
backdrop, and machinery noise, not blocks):

- face `default`: clean, but the eye colour drifts (it lives in the preset).
- face `moe-far`: clean, eye colour kept. Dose–response confirmed.
- face `moe` with `cowboy shot` instead of `full body`: **still collapses.**
  The face itself resolves — the surplus moves to the backdrop.

That last one corrects the small-face story: giving the face more canvas does
not absorb the weights. Seated framings tolerate full `moe`; everything else
overflows regardless of crop, so the dose is what has to move — which is what
`FACE_BY_POSE` now does (it was described here before it was actually wired
into the code; as of today it is).

The dose does not have to drop all the way to `moe-far`. The cliff sits
between 1.45 and 1.65: `moe-mid` (eyes 1.45, iris 1.4) held on the collapsing
seed and on three random seeds, and its face is visibly closer to `moe`'s
than `moe-far`'s is — so `FACE_BY_POSE` hands standing to `moe-mid`. Raising
the eye LoRA (0.7 → 0.95) is a further identity dial that costs no prompt
attention and composes with either preset.

Standing also shows the whole leg, so `(thick thighs:1.6)` reads heavier than
it does seated. `--extra 'tall, (long legs:1.3)'` rebalances it by height
alone and keeps the tuned leg weights; dropping the thigh weight to 1.2 as
well gives a distinctly slimmer silhouette at the cost of the series' soft
legs (`tall-A` / `tall-B`, seed 1210136864). Not baked into POSES because
`tall` would leak into every job's standing — Yukari is small on purpose.

How the same dial landed on the other jobs:

- **Takao**: height alone was not enough — the sage block's 1.6 thigh weight
  compounds with her own build. Her `LEGS_BY_JOB` entry states the height
  (canon for her, in the class tags) and thighs at 1.2; baked in.
- **Yukari**: `tall` on her surfaced Hassaku's second-figure habit — two of
  three standing renders duplicated her outright, the third grew a
  rabbit-eared silhouette on the backdrop. Appending
  `(cast shadow:1.6), (shadow on ground:1.5), (silhouette:1.4),
  (dark figure:1.4), (2girls:1.5), (duplicate:1.3), (clone:1.3)` to the
  negative cleared it 3/3 (`yukari-tall2`). Not baked in: whether Yukari is
  tall at all is a taste call, and her petiteness is the default identity.

The overflow also explains the *shape* of the collapse: the over-weighted eye
tokens claim pixels wherever they can — as spare eyes on the backdrop, or as a
second, larger-faced figure that can carry them.

This is the third axis on which a weight turns out not to transfer. The others
were the prompt being saturated (adding a tag costs an existing one) and the
checkpoint changing what a given weight is worth. Now: **the framing changes it
too.** A tag tuned on a close-up will overreach at full-body distance.

## The goal this is aimed at

`ab-C_00001_` is the current high-water mark. It predates any trace and any
commit — it came out of the ablation that later became `cel-plain`, 34 minutes
before that was committed — but the prompt it used is reproduced byte-for-byte
by the current code:

```bash
uv run scripts/queue_dq3.py --job sage --pose sitting --width 1024 --height 1536 \
  --diffusers-path hassaku-il-v22 --style cel-plain --seed 4051776310
```

It carries a backdrop intruder, which is the one thing to fix in it.

**The goal: change the pose by swapping the reference image, with ab-C's
quality as the floor.** The staff can go (`--drop`) — the reference's hands are
always doing something else, and the grip is the tag most likely to fight.

`--trace-mode openpose` cannot deliver this. It needs a body detector that finds
almost nothing in illustrations: six references were tried and one worked, and
neither background contrast nor resolution rescued the others.

**`--trace-mode softedge` does deliver it.** An edge filter has nothing to fail
at, so every reference produces a hint. Three references, everything else
identical, three different poses:

| reference | pose that came out |
|---|---|
| Alice bending | bent forward, holding the skirt, looking back |
| `ref-pose-bootoff` | seated, legs forward, one hand raised |
| `ref-pose-abovestand` | high angle, hand raised to the head |

The sage stays the sage in all three — headband, white dress, yellow gloves,
teal cape, black legwear, yellow boots. This is the working command:

```bash
uv run scripts/queue_dq3.py --job sage --pose sitting --width 1024 --height 1536 \
  --diffusers-path hassaku-il-v22 --style cel-plain --seed 4051776310 \
  --trace-image <ref>.png --trace-mode softedge \
  --trace-strength 0.6 --trace-end 0.4 --trace-resolution 1024 \
  --drop '(quarterstaff:1.35)' --drop 'plain wooden pole' --drop 'holding pole'
```

**0.6 / 0.4 is enough, and more is worse.** Swept against 0.8/0.5 and 1.0/0.7:
the pose transferred at all three, and the only thing the higher settings added
was the reference's own decoration — a ribbon at 0.8, the reference's black
ribbon verbatim at 1.0.

**Whatever else is in the reference arrives as outline too.** The flowerbed at
Alice's feet came out as a creature with eyes standing next to the sage; it went
away when the flowerbed was painted out of the reference. The bedsheet behind
`bootoff` came through as a blue backdrop. Clear the reference of anything that
is not the figure.

**Hair length does not survive, and cannot be argued back.** `(medium hair:1.3)`
loses to a long-haired reference every time. Adding `(short hair:1.3)` to the
positive and `(long hair:1.4)` to the negative both changed nothing — same seed,
same reference, hair still long in each. Hair is silhouette, and silhouette is
what softedge hands over, so the prompt is not in the argument at all. Pick a
short-haired reference if the length matters.

**Add the shadow negatives.** The intruder is a shadow with eyes drawn into it,
and with a trace occupying the frame it can finally be negated away -- see the
correction in the Hassaku section. Append to the negative:

    (cast shadow:1.6), (shadow on ground:1.5), (silhouette:1.4), (dark figure:1.4)

## Simplicity is not a style block — it is the absence of one

The look this recipe was eventually judged against comes from the ~100-checkpoint
comparison sheets, which render every model on six tokens:

    masterpiece, best quality, 1girl, flat color, cowboy shot

Rendered bare on two seeds, Amanatsu and Hassaku land in the same place: a flat
single-hue field, low-chroma cream skin, a thin *tinted* line, no cast shadow.
Corner colour and mean saturation, 256px:

| base | field | sat |
|------|-------|-----|
| amanatsu | `(244,201,201)` / `(109,190,219)` | 0.50 / 0.56 |
| hassaku | `(222,137,144)` / `(137,192,196)` | 0.43 / 0.48 |
| moe-vpred | `(242,242,242)` both | 0.17 / 0.29 |

So the palette everyone credits to Amanatsu is Hassaku's too — they are the same
family, and `moe-vpred-v2` is the outlier that wants a white ground and a heavy
black line. Which sets up the standing conflict: **the base with the face is not
the base with the colours.**

**The full recipe bans that look by name.** `NEG_QUALITY` ends on
`(washed out:1.3), (overexposed:1.3), (pale skin:1.3)`, and `NEG_TOON` bans
`(colored lineart:1.4), (light lineart:1.3), pale lineart` — between them, the
entire flat-colour aesthetic, in the negative prompt. No base can reach it from
there. `--style pastel --negative-preset pastel` exists to release exactly those
two blocks while keeping the guards that point the same way (anti-gloss,
anti-cast-shadow).

**But the style block was not the answer either.** The real difference is size:
the sheets run 6 tags and this recipe runs 91. Every tag is one more thing the
sampler is obliged to draw, so a "simple" style block is subtraction applied to
a prompt built by addition — and subtracting far enough stops it resolving at
all (`pa6`, with the canon colour weights dropped too, came back as pure noise).

`--minimal` starts from nothing instead: quality header, `1girl, solo`, the class
block, the pose, a flat field. No face preset, no legs block, no style block, no
LoRA, and a ten-word negative. 91 tags → 33, 2 LoRAs → 0. That is `mn-h-grey`,
the accepted colouring.

Three things fell out of it:

- **Not specifying beats specifying, again.** `--bg-color pink` on the same seed
  is worse than leaving the field grey. The accepted render names no colour it
  does not have to.
- **`--face` is the one block `--minimal` will take back**, because the face and
  eyes are the part being chosen rather than accepted. Passing `--face` is now
  distinguishable from letting the job default fill it in, which is why the
  parser default for `--face` is `None` rather than `"moe"`.
- **A non-grey field duplicates the figure on Hassaku.** Three tries at this
  seed, all twins: dropping the grey tag and appending a colour, and swapping the
  word in place with `--bg-color` at both `pink` and `cream`. So it is the hue,
  not the missing anchor — my first reading of this was wrong. It does not happen
  under `--style pastel`, and the cause is still unknown.

## Legwear: three problems that all live in the negative

`--minimal` carries no legs block, so legwear had to be added back —
`LEGWEAR_BY_JOB`, one short line per character. Saying the garment was the easy
part; the three things that went wrong all needed the negative instead:

- **Black came out brown.** `(black thighhighs:1.3)` renders as dark brown on
  Hassaku. Raising the weight does not fix it. `(brown legwear:1.5)` and the two
  garment-specific brown tags in the negative do.
- **Legwear left alone comes back knitted.** Banning `(fishnet:1.4)`,
  `(ribbed legwear:1.3)`, `knit`, `fabric texture`, `thread` is what keeps it a
  flat shape carrying a highlight, which is what "gloss without fibre" means.
- **Gloss asked for plainly turns to vinyl.** `(latex:1.35), (rubber:1.35),
  wet look` in the negative is the whole difference between a sheen and a shine;
  the positive side only needs `(glossy legwear:1.2), shiny legwear`.
  **This last bullet is wrong** — see the section below. `(glossy legwear:1.2)`
  produces no gloss at all; the render is flat black. It was written from
  contact-sheet-sized tiles, where flat black legwear and glossy black legwear
  look the same. Crop the legs and enlarge them before judging this.

A fourth thing fell out for free. Before the guard existed, adding
`(black pantyhose:1.3), pantyhose` to the sage's minimal prompt returned **pure
noise on both seeds** — the prompt stopped resolving, the same failure as `pa6`.
With `LEGWEAR_GUARD` in place the same seeds render cleanly. Naming what the
garment must not be gave the garment tag somewhere to land.

`--border` puts the full recipe's `(white outline:1.6), outline, sticker` on the
minimal path, opt-in. It draws cleanly on Hassaku for all three characters —
which contradicts the older entry below claiming Hassaku is better without the
border. That was measured under the full `cel` recipe, not this one.

## Gloss is shading, and the palette forbade shading

The spec was the same three words each time: gloss, no fibre, black not brown.
The first two were met; the gloss was not, and it took five rounds to find out
why. Twenty renders on the sage, two seeds each, one variable at a time.

The wall: a highlight band is a **shading feature**, and `--minimal` carries
`(flat color:1.3)`, which forbids shading. So every attempt to get shine out of
the positive had to push the material word until the model stopped *lighting*
the fabric and started *replacing* it.

| round | change | result |
|-------|--------|--------|
| A | `(glossy legwear:1.2), shiny legwear` (the standing recipe) | flat black, no highlight |
| B | `(shiny legwear:1.5)` + `(specular highlight:1.3)` | strong gloss, but **leather** — and the gloves and boots went glossy too |
| C | B, with `latex`/`rubber`/`wet look` dropped from the negative | identical to B |
| D | A, with those dropped | identical to A |
| e/f | shine at 1.3 / 1.4, plus `shiny skin/gloves/boots` banned | flat, all of them |
| h | `(shiny legwear:1.55)` alone | clean cel band on one seed, **wet latex on the other** |
| k/m/n/p | 1.45, 1.5, garment at 1.5, `(highlights:1.5)` | 1.5 marginal; the rest flat |
| **s** | **`(shiny legwear:1.45)` + `(soft shading:1.3), smooth shading`** | **band on cloth, nothing else in the frame shiny** |

What the table is actually saying:

- **D == A: the guard was innocent.** Banning `latex`/`rubber`/`wet look` was not
  what suppressed the gloss, so removing them buys nothing.
- **B == C: the guard is also powerless.** With the positive at 1.5 the fabric
  turned to leather *with* `(latex:1.45)` in the negative. Same lesson as the
  backdrop creature: naming the symptom does not remove it.
- **h is not a setting, it is a threshold.** 1.4 does nothing, 1.55 is a coin
  flip between a highlight and latex. Anything living on that edge is not a
  recipe.
- **Negative `shiny X` flattens `shiny Y`.** `(shiny skin:1.3), (shiny gloves:1.3),
  (shiny boots:1.3)` were meant to keep the shine on the legs. They killed it
  everywhere — a negative pulls the whole `shiny` direction down and takes the
  positive with it. Do not try to fence a quality in by banning it elsewhere.
- **`(specular highlight)` is a material word, not a lighting one.** It was in
  the two rounds that produced leather, and it glossed the gloves and boots as
  well. Tellingly, the `glossy` style block in the tool has always used
  `soft shading, smooth shading, rim light` instead.

So the answer was to stop asking for a shinier material and to let the shading
back in. `(shiny legwear:1.45)` is below the material-conversion threshold on
every seed tried; `(soft shading:1.3), smooth shading` supplies the gradient the
highlight is made of. `(flat color:1.3)` did **not** have to come down — round s
keeps the accepted palette weight untouched and still gets the band. Lowering it
to 1.15 (rounds j and q) changed the legs very little and is not worth the risk
to a colouring that was signed off.

The shading tags sit at the tail, immediately before `--extra`, because that is
the position they were measured in. Moving them next to the garment tag is
untested.

Verified after the change: sage 2/2, Takao 2/2, Yukari 2/2, all with the band,
all fabric, no backdrop intruder. Accepted: `b9ee5041` (sage), `1a6b81cb`
(Takao), `58ccdd81` (Yukari).

`--legwear-text` was added for this, mirroring `--pose-text`: the legwear block
is the one part of the prompt being tuned against a stated spec rather than
accepted from the base, so it needs to be swappable without editing the table.

### How this was nearly missed

The first report said the gloss was delivered. It was not — it was judged from a
three-tile contact sheet at 520px, where flat black and glossy black are the
same shape. The whole five rounds only started because the spec was repeated
verbatim. Cropping the lower 55% of the frame and enlarging it (`legcrop.py`)
makes the difference obvious at a glance; do that before claiming a legwear
result.

## The chair pose, brushed up — and what would not brush out

The chair render that was picked had the camera under the skirt. The cause was
structural, not stylistic: **the minimal path carried no framing negatives at
all.** The full recipe has `NEG_FRAMING`; `--minimal` never inherited it, and
none of the poses it was built on happened to need it. `MINIMAL_FRAMING_GUARD`
now adds the smallest part of it — `(upskirt:1.4), panties, (from below:1.35)`
— and leaves out the crowd-adjacent half, which has caused its own trouble here.
Confirmed not to disturb the sage's sitting or Takao's lookback.

Two more fixes on the same pose:

- **Three legs.** `(crossed legs:1.35)` at that weight makes the model draw the
  crossing rather than the legs. 1.2 renders two legs. Raising
  `(extra legs:1.6), (three legs:1.5)` in the negative on top of 1.35 did not
  help — the weight was the problem, not the absence of a ban.
- **The chair itself.** `(office chair:1.35), swivel chair, backrest,
  feet on floor` gives a coherent chair; without it the seat and base come out
  as separate objects.

**Unresolved: the backdrop intruder owns this pose for Yukari.** Roughly a dozen
renders across five seeds, and every lever failed:

| lever | result |
|-------|--------|
| `--border` off entirely | rabbits gone, a large eyeball instead |
| `sticker` dropped, border kept | unchanged |
| `rabbit print` dropped | unchanged — and worse in later rounds |
| `rabbit print` restored | milder on one seed (eyeless rabbit shapes), still there |
| heavy framing/anatomy negatives | unchanged |
| all negative extras removed | worse |
| 1024x1280 instead of 1536 | unchanged |
| four other seeds | 0 of 4 clean |
| **`--face default`** | **clean, 2 of 2** |

So the face block is still the only lever with anything behind it, exactly as
the bisection found — and the cost is the same as it always was, the moe face.

A methodology error worth keeping: `rabbit print` was dropped on a hypothesis,
the hypothesis failed, and the drop was carried into every later variant anyway.
Several rounds were then read against a baseline that had a known-useless change
in it. **When a hypothesis dies, revert its change before running the next one.**

### The gaming chair, facing front — swap the word, do not add it

Later, with the layered legwear on. The chair block turned out to have a budget,
and everything follows from where the boundary sits.

| chair block | chair drawn | legwear | intruder |
|-------------|-------------|---------|----------|
| 14 tags (the original, turned to front) | gaming chair | **one dark tights, layering gone** | none |
| 12 tags (two different subsets) | gaming chair | gone | **present** |
| 9 tags, `(office chair:1.35)` | grey mesh, or black high-back | **both layers** | none |
| 9 tags, `(gaming chair:1.4)` | **racing seat, armrests, five-star base** | **both layers** | none |

**The legwear is the first thing the pose block pushes out.** Between 9 and 12
pose tags the pale thighhighs disappear and one dark tights is drawn instead —
consistent with them being the weak end of the legwear block, the same tags that
went mid-purple when they were trimmed as redundant.

**Substituting a word costs nothing; adding tags costs the picture.** Asking for
a gaming chair as a five-tag block — `(gaming chair:1.45), racing seat,
(high backrest:1.3), headrest, armrest` — returned a full-frame noise field.
Replacing `(office chair:1.35)` with `(gaming chair:1.4)` at the same tag count
drew a proper gaming chair and kept everything else, and threw in a controller
in her hands that nothing had asked for.

**Two renders came back as pure noise**, this one and `TRIM` plus two body tags,
out of eight. Nothing in the log, at any level.

Re-running them byte-identically was the wrong test and proved nothing: the seed
fixes the whole computation, so an identical re-run reproduces whatever happened
the first time regardless of cause. **The seed is the discriminator.** Both were
run again on a different seed and both came back as noise there too, so these
are dead prompts and not bad pairings:

- `(gaming chair:1.45), racing seat, (high backrest:1.3), headrest, armrest`
- the 9-tag block plus `leaning back, hand on own knee`

No warning at any log level, and the output is a full-frame texture rather than
a bad picture. Nothing else in this project fails this way; worth recognising on
sight instead of debugging the tags.

**Cropped feet: raise `full body`, do not add a framing tag.** Every seed except
`151515151` cut the feet off at the bottom edge. `full body` was already in the
block, so it went to `(full body:1.4)` — a substitution, which the chair word
had just shown to be free. Two of three seeds then held the whole figure. On the
third the camera came down and in instead, which is the framing this project
does not develop; that seed was dropped rather than tuned.

The camera pair `(eye level:1.35), straight-on` correlates with the backdrop
intruder returning — present in both 12-tag runs that carried it without the
body tags, absent from the 9-tag and 14-tag runs. Four renders, so it is a lead
rather than a finding.

Kept, one prompt and three seeds — `pick/yk-chair-151` (`3ee2b60f`),
`pick/yk-chair-111` (`326942c1`), `pick/yk-chair-555` (`d69e1dee`). The full
command is in the tags; it is the layered-legwear recipe above with the chair
block substituted for the sitting pose:

```
--pose-text "(sitting on chair:1.4), (crossed legs:1.2), looking at viewer, full body, (front view:1.35), facing viewer, (gaming chair:1.4), swivel chair, backrest"
```

`(crossed legs:1.2)` and not 1.35: the three-legs failure recorded above is the
same tag at the same weight, and it did not need re-learning here.

## New poses: six tried, three kept

The table had three sitting variants plus standing, reaching and a
lying-adjacent one, so the gaps were movement and a compact silhouette. Tried on
Takao, one seed, then transferred.

| pose | result |
|------|--------|
| `chair` — sitting on a chair, legs crossed | **keep.** Draws the chair too, and transfers to the sage cleanly |
| `crouch` — squatting, arms on knees | **keep** on Takao and Yukari |
| `wave` — standing, one arm up | **keep** on Takao |
| `hugknees` | tangled arms and legs on the first pass; readable after naming the limbs |
| `jump` | first pass came out kneeling in mid-air; second pass reads as a jump on one seed of two, broken anatomy on the other |
| `walking` | **does not work.** Reads as standing on the first pass, and detached legs on both seeds of the second |

The three that failed all named the *action* — walking, jumping, hugging — and
not the shape the limbs make. Saying `(walking:1.5)` louder does not help; the
second pass got a jump only once it said feet off the ground, one knee bent,
arms raised. `walking` still fails that way and is not in the table.

`crouch` and `wave` attract the backdrop intruder on the sage and Yukari — an
eyed creature behind the sage's squat, chibi clones beside her wave, eyed
rabbit stickers around Yukari's. Both poses leave a lot of empty canvas beside
the figure. `chair` fills the frame and stays clean. Not enough seeds to call
that a mechanism, only a place to look.

## Two pairs of rabbit ears: give the demand one owner

Yukari's hoodie has rabbit ears, and the class block also asked for
`(pink rabbit ears:1.3), fake animal ears`. She came out wearing both — the
hood's, and a real white pair on her head above them. `fake animal ears` does
not make the model draw fake ones.

| change | seed 2331520658 (the one that started this) |
|--------|---------------------------------------------|
| baseline | two pairs |
| drop `(pink rabbit ears:1.3)` | extra pair survives |
| drop that and `fake animal ears` | survives, plus duplicates and floating objects on the other seeds |
| reword to `(fake rabbit ears:1.35), (ears on hood:1.2)` | survives |
| **drop the ear tag, raise `(rabbit hood:1.4)` to `1.55`** | **clean** |

Subtraction does not work here for the same reason it did not work on the
backdrop creature: a demand with nowhere to land gets resolved somewhere else
on the canvas, which is why deleting both ear tags produced a second figure
instead of a second pair of ears. Raising the hood gives the ears one owner.

5 of 6 seeds clean. The sixth is 3409564303, which has been Yukari's bad seed
since the backdrop-eye work and fails under the baseline too.

`--class-text` was added for this. `--drop` can remove a tag from the class
block but cannot reword one, and an ownership problem needs rewording.

## Mashing two renders together: what the seed owns, and what the prompt owns

The ask was one render's pose and one render's clothing. Splitting them showed
which half of the picture each input controls.

**The seed owns the pose, and it owns the hood.** Whether the hood is up or down
came out of the seed, not the prompt -- 2331520658 wore it up in every render
and 3514242666 wore it down, through completely different prompts. Asking for
`(hood down:1.5)` on the up seed does move it, so it is not fixed, but nothing
in the prompt had been touching it before.

**The prompt owns the garment and the palette.** Moving one render's legwear
block onto another's seed transferred exactly the legwear, and nothing else.

**Symmetry does not respond to being asked for.** One leg kept coming out
without its sock. `(both thighhighs:1.3), (matching thighhighs:1.35),
symmetrical legwear` in the positive made it *worse* -- that render drew one
sock where the run without those tags drew two. Only the negative guard
(`(mismatched legwear:1.5), (single thighhigh:1.5)`) tracks with clean results.
Sixth time this project has watched a symptom named in the positive get louder
rather than quieter.

**"Redundant" tags were not redundant.** Trimming five apparent duplicates --
`(white thighhighs:1.2)` and `(lavender tint:1.3)` next to
`(very pale purple thighhighs:1.5)`, `(charcoal pantyhose:1.35)` next to
`(sheer black pantyhose:1.5)` -- halved the duplicate-figure rate and cost the
colour: the thighhighs went mid-purple and the sheerness disappeared. The weaker
tags were holding the pale end of the range. There is a real trade here between
prompt weight and colour accuracy, and it was resolved in favour of colour,
using seeds that come out clean.

Duplicate figures ran 3 of 8 on the first sweep and 0 of 7 on the second, same
prompt. It is a seed property, not a prompt property, at this weight.

**The recipe that was kept.** Sixteen clean candidates went up on
`sheet-morning.png`; three were picked (tags `pick/yk-layered-737`,
`pick/yk-layered-151`, `pick/yk-layered-626`). None of this is in
`queue_dq3.py` — the negative is passed whole, which is deliberate: an explicit
`--negative` bypasses `LEGWEAR_GUARD` and `MINIMAL_FRAMING_GUARD`, so the string
below is the entire negative and the command reproduces byte-identically.

```bash
uv run scripts/queue_dq3.py --job yukari --pose sitting \
  --width 1024 --height 1536 --minimal --face moe-far-noeye --border \
  --seed <737373737|151515151|626262626> --flat-paint mild \
  --legwear-text "(sheer black pantyhose:1.5), (see-through pantyhose:1.45), (skin visible through pantyhose:1.4), (charcoal pantyhose:1.35), (glossy pantyhose:1.3), (very pale purple thighhighs:1.5), (white thighhighs:1.2), (lavender tint:1.3), (soft shading:1.25), smooth fabric, (thighhighs over pantyhose:1.55)" \
  --extra "(pale skin:1.25), (thick thighs:1.3), (wide hips:1.2), (hood down:1.5), (hood behind head:1.3), (visible hair:1.2)" \
  --negative "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, extra fingers, extra limbs, watermark, signature, text, (disembodied eye:1.4), (brown legwear:1.5), brown thighhighs, brown pantyhose, (fishnet:1.4), (ribbed legwear:1.3), knit, fabric texture, thread, (latex:1.45), (rubber:1.45), wet look, (leather legwear:1.45), leather pants, (upskirt:1.4), panties, (from below:1.35), (blue legwear:1.5), (periwinkle:1.45), (blue background:1.5), (navy:1.45), (blue tint:1.4), (opaque pantyhose:1.5), (solid black legwear:1.4), (mismatched legwear:1.5), (single thighhigh:1.5), (asymmetrical legwear:1.45), (uneven legwear:1.4), (hood up:1.5), (hood over head:1.4)"
```

`(thighhighs over pantyhose:1.55)` is what makes it two garments instead of one.
Without it the two colour blocks fight and the model draws a single legwear in
some blend of them; with it the pale thighhigh sits on top of the sheer black
and the thigh above the welt reads as skin through tights.

**Accepted with a known defect: the welt.** The band at the top of the
thighhighs is not drawn as a real garment edge — its width wanders, and on
`626262626` it sits at a different height on each leg. It was called good enough
rather than fixed. Worth knowing that this is the part of a two-layer legwear
the model is worst at: everything above and below it is clean, and the seam is
where a layered prompt shows its seam.

## Where a colour change belongs: in the prompt, or after the sampler

Three kinds of colour change, and they do not live in the same place.

**Across a category — prompt.** White to black, thin to wide, vertical to
horizontal, opaque to sheer. These land immediately.

**Within a category — after the sampler.** White to cream, purple to a deeper
purple. `off-white`, `skin colored` and `cream` all sit on the same point as
`white` and change nothing; raising their weight only makes the white whiter.
Yukari has white hair and white frills as well, so the image is anchored to the
white the legwear inherits. `recolor_stripes.py` sets the value afterwards, the
same conclusion `recolor_bg.py` reached for the backdrop.

**A material property with nothing underneath — only at generation time.** Sheer
legwear was the case that taught this. It cannot be added later: the tights are
drawn as solid white, there is no skin under them, and a masked pass asking for
see-through returned opaque bands at 0.55, 0.7, 0.85 and 0.95. Nor can the skin
be borrowed from a bare-legs pass and composited, though that pass does work and
is pixel-aligned. Asked for in the first render at `(sheer white stripes:1.6)`
it appears at once. **It had simply never been asked for at generation time --
every attempt had been downstream of an opaque render.**

Two costs came with it, both the same shape as everything else here: at 1.6 the
skin renders tanned, and pulling it back with `(pale skin:1.4)` plus a tan ban
costs the purple bands entirely. One quality can be pushed or the other, not
both.

## Masked refine: the denoise ceiling is a whole-image problem

`queue_refine.py --mask` restricts the sampler to one garment. Without a mask
the denoise has to stay at 0.25-0.3 or the picture comes apart, and that is too
weak to change what the legwear *is*. With one, 0.65-0.7 redraws the stripes as
cloth and every other pixel is bit-identical.

Two traps, both mine:

- `--positive-extra` appends. Asking for bare legs while the inherited positive
  still says `(striped pantyhose:1.45)` returns striped pantyhose at *any*
  denoise, including 0.95. `--positive` replaces, and then it works.
- The inherited negative bans sheer legwear, so reusing it verbatim asks for
  see-through tights while forbidding them.

## The geometric stripe layer: abandoned

`stripe_paint.py` lays bands perpendicular to each leg's axis at a fixed period,
with a drawn line at every boundary -- even by construction, which the prompt
cannot deliver. It is kept because the idea recurs, and the reason it fails is
not obvious until tried.

The two legs are crossed, so they are **one** connected region, at every
bridging width from 10 to 50 px. One region means one principal axis, so the
bands ignore each leg's own direction, and a leg that bends at the knee has no
single axis anyway. The result reads as paper laid over the figure, and the
masked pass at 0.7 that would redraw it as cloth also redraws the evenness away.
Separating the legs needs semantic segmentation or a local orientation field,
not morphology.

## Volume on the legs: ask for a body, not a part

"A bit more healthy volume on the legs" turned out to be a framing problem
rather than an anatomy one. The obvious phrasings deliver the volume and then
keep going.

| block | volume | framing |
|-------|--------|---------|
| `(thick thighs:1.2), thighs` | yes | camera drops to the hips, skirt rides up, rear becomes the subject — both seeds |
| `(thick thighs:1.3), thighs, (wide hips:1.15)` | yes | worse |
| `(healthy body:1.2), (thick thighs:1.15), soft thighs` | yes | same drift |
| `(thick thighs:1.15)` alone | some | still drifts |
| `(thick thighs:1.2)` moved next to the garment | most | most exposed of all |
| `healthy body, (plump legs:1.2)` | yes | unchanged |
| **`(toned legs:1.2)`** | **yes, without the chubbiness** | **unchanged** |

`thighs` and `wide hips` are the carriers. They sit next to rear-focused
compositions in the training data and bring the composition with them, and
lowering the weight only makes the drift smaller, not absent. Moving them next
to the garment — on the theory that adjacency would keep the effect local to
the legs — made it worse, not better.

Naming the framing in the negative was deliberately not tried. That is the move
that has failed on this project every time it has been reached for.

Verified: Takao 2/2, sage 2/2, Yukari 2/2 — volume up, framing intact, gloss
intact, no backdrop intruder.

`plump` then turned out to overshoot: healthy thighs were wanted, chubby ones
were not, and `plump` carries the second. Lowering it to 1.1 barely moved the
figure and adding `slim legs` alongside took the volume back off. `toned` keeps
the shape and drops the softness without going muscular.

**A trap in the ablation that ran this.** The variants dropped the old block
with `--drop` and passed the new one through `--extra`. `--drop` runs over the
joined string, so `--drop "healthy body"` also took `healthy body` out of the
replacement — every variant actually rendered without it. The accepted images
are therefore `(toned legs:1.2)` alone, and that is what the constant says.
Check what the run actually contained against `/history` before adopting the
string you *think* you tested.

## The backdrop creature: found, by bisecting the face block

The entry below was the first pass and it is superseded. `(disembodied eye:1.4)`
suppressed the symptom on one seed and was not a cause; with it in place the
defect still ran at 2/8 for Takao. The cause was found by bisecting the face
block one tag at a time against the two seeds that reliably grew it:

| variable | dirty seeds cleaned |
|----------|--------------------|
| drop `(large iris:1.4)` alone | **0/2 — worse both times** (eyes drawn onto her thigh) |
| drop `(large eyes:1.45)` alone | **2/2** |
| whole face block removed (`--face default`) | 5/5 |
| all four face weights at the moe-far rung | 2/2, and 4/4 previously-clean seeds stayed clean |

**It is eye AREA, not iris size.** The face block demands a large eye area; under
the minimal path's ten-word negative that demand overflows onto empty canvas and
resolves there. The floating eye, the chibi clone and the eyed grey object are
one phenomenon landing differently — the same seed slides between all three as
the prompt is perturbed, which is why every symptom-naming negative "worked"
once and then failed. Each such tag clears only the form it names and amplifies
the rest:

| symptom-naming attempt | what happened |
|---|---|
| `(disembodied eye:1.4)` | cleared one seed; 2/8 still defective |
| `(disembodied eye:1.8)` | no better than 1.4 |
| `(monster:1.4)` | nothing — the model does not classify it as a monster |
| `(chibi), (mascot), (doll)` | chibi clone became an eyed grey object |
| `(extra eyes), (eyeball)` | floating eyes cleared; chibi became an eyeball plush |
| `NEG_CROWD` whole block | cleared it; **sage palette turned lime** |
| `(2girls), (duplicate), (clone)` | did not clear Yukari; **backdrop turned blue** on the other two seeds |

The lime and the blue both come from the `multiple girls / background character /
stray object` half, not the monster half. Naming the symptom is the wrong lever
throughout.

`FACES["moe-far-noeye"]` is the fix — the already-documented moe-far rung without
a spelled colour, since `EYES_BY_JOB` supplies that. Validation at that rung,
all on the minimal path:

| set | clean | before |
|-----|-------|--------|
| Takao lookback, 5 seeds (2 previously dirty) | **5/5** | 2/8 defective |
| Takao standing, 2 seeds | **2/2** | 1/2 defective at the moe-mid rung |
| Sage sitting, 3 seeds | **3/3** | — |
| Yukari sitting, 5 seeds | 4/5 | 1/2 defective |

Standing was the open question — the pose fills the frame vertically and moves
the empty space — and the rung holds there too.

**Yukari has a residue, and it is not eye area.** One seed of five (1117511306)
still duplicates her at this rung. Isolated on that seed:

| variable | result |
|---|---|
| `--drop (large eyes:1.3)` — the eye-area tag gone entirely | **still duplicated** |
| `--face default` — whole face block gone | **clean** |

So for her the driver is the face block as a whole rather than the eye-area tag
that explains Takao and the sage. Which tag inside it is untested — `round eyes`,
`eyelashes` and `(large iris:1.25)` are the remaining candidates, and her class
block is also the heaviest of the three (hood, rabbit ears, sidelocks, two
garment colours), so an interaction is possible. `--face default` is the clean
fallback for her meanwhile.

One more hypothesis died here. `--border` adds the literal word `sticker`, and
the seed that failed with the border did so by growing what looked like sticker-
sheet items — a rabbit and two eyes. Tidy, and false: dropping `sticker` left
that seed's eyes exactly where they were, and the control that kept `sticker`
was clean on another seed. Her eleven renders at this rung:

| seed | no border | border | border, `sticker` dropped |
|------|-----------|--------|---------------------------|
| 1117511306 | duplicate | clean | clean |
| 2331520658 | clean | clean | clean |
| 3409564303 | clean | **eyes** | **eyes** |
| 3514242666 | clean | — | — |
| 618823993 | clean | — | — |

2 of 11, correlating with neither the border nor the word. It is the threshold
behaviour the bisection already described: she sits nearer the edge than the
other two, and any perturbation moves her across it. Do not read a mechanism
into which side a given seed lands on.

Two other things fell out:

- **`--drop` silently did nothing on the minimal path** — `build_minimal_positive`
  returned before `build_positive`'s drop loop. Worse than rejecting the flag,
  because an ablation run with `--drop` looked like it had been performed. Fixed.
- Symptom-naming has now failed in five distinct ways here and once before (the
  old entry about raising the anti-shadow negatives making things worse). When
  something unwanted appears, the question to ask is what the prompt is demanding
  that has nowhere to go — not what to call the thing that appeared.

### Superseded: the first pass at this

`--minimal` cut the negative to ten words, which threw away every guard the full
preset carried, so the backdrop intruder came back — a Dragon Quest mascot beside
the seated sage. Measured properly this time, on the one seed of four that grew
it, one variable at a time:

| change | result |
|--------|--------|
| drop `dragon quest iii, dragon quest` | **unchanged** |
| add `(monster:1.4)` | **unchanged** |
| add `(disembodied eye:1.4)` | **gone** |
| drop `(dark blue eyes:1.25)` (`moe-mid` → `moe-mid-noeye`) | gone |
| add the whole `NEG_CROWD` block | gone, but the palette turned lime |

So it is not a monster and the model does not treat it as one — naming monsters
does nothing. It is a cluster of disembodied eyes that happens to resolve into a
recognisable mascot, and only the tag that names *that* removes it. Which also
explains the older Takao case, where raising the anti-monster negatives made
things worse: those tags were never touching the cause.

Two things I got wrong on the way, both from reading one image:

- **"The cause is the spelled eye colour."** It is not. Dropping
  `(dark blue eyes:1.25)` did clear that render, but `moe-mid` *with* the colour
  is clean on three other seeds. It perturbed the seed; it did not remove a
  cause.
- **"A Dragon Quest prompt with no monster negative invites a monster."** Tidy,
  and false — dropping the franchise tags changed nothing.

What replaces the creature is the staff's cast shadow. The empty area is still
filled; the filling is just benign. That is the same shape as the older
finding that a traced shadow the style refuses to draw becomes an object.

`MINIMAL_FACE_GUARD` is therefore one tag, applied only when `--face` was asked
for — the face block is what puts eye pressure into a prompt that has none
otherwise, and the accepted colouring (`mn-h-grey`) carries no face, so its
reproduction is unaffected.

## The base draws the face; the face preset only nudges it

Six bases, one seed (1117511306), a byte-identical Takao `lookback` prompt — so
the checkpoint was the only variable:

| base | face | rest |
|------|------|------|
| `hassaku-il-v22` | long face, narrow eyes | thick lines, brown hair, shadow as one flat slab |
| `amanatsu-il-v11` | between the two, slightly tsurime | backdrop tints navy, skin gloss high |
| **`moe-vpred-v2`** | **small round face, large round irises, tareme** | cleanest palette, uniform blue correct, no breakage |
| `novaAnimeXL_ilV170` | long contour, medium eyes | shadow edge frays, boots break up |
| `NoobAI-XL-v1.1` | long face | uniform shifts teal, black spikes across the legs |
| `miaomiaoPixel_vPred11` | — | pixel art; it is a pixel model |

Every one of those received the same `moe-mid-noeye` tags —
`(large eyes:1.45), (tareme:1.4), (large iris:1.4)` — and drew a different face
from them. **The eye tags do not set the face; they scale whatever face the base
already draws.** That is why the eye-ratio work earlier in this file kept hitting
a ceiling, and why the standing collapse was a weight problem rather than a
drawing problem: on those bases the weights were the only lever, and it was the
wrong lever. Changing the base is the lever.

Confirmed as a property of the base, not seed luck: four further random seeds on
`moe-vpred-v2` (`mv-face1`..`4`) all came back with the same round small face.

**This was later overruled, and the overruling is the more useful finding.** The
base with the best face is not the base with the palette, and the palette turned
out to matter more: Hassaku and Amanatsu share the flat-colour family the whole
recipe now aims at, and `moe-vpred-v2` is the one base that does not — white
ground, heavy black line, and it refuses a coloured field outright. Every
accepted render after the colouring work is Hassaku's, so `BASE_BY_JOB` points
all three characters there and the face is bought back through the face preset
instead. The face-vs-palette trade is real and is decided in one dict.

The original entry, kept because the measurement stands: `takao` → `moe-vpred-v2`, bare
`--job takao --pose lookback --width 1024 --height 1536 --style cel-plain
--flat-paint mild` rebuilds `cac2cf43`'s graph byte-identically.
`--diffusers-path` still overrides.

Two things this does not fix, and both are the same cause — the weights in this
file are pitched for Amanatsu:

- The flesh dose (`EXTRA_BY_JOB`, the fl3 rung) reads weaker on `moe-vpred-v2`
  than it did on Hassaku. It wants a retune, not a different tag.
- `CHECKPOINT_TUNING["moe-vpred-v2"]` still claims the base "wants the halved
  face preset at every framing". That was measured with full `moe`;
  `moe-mid-noeye` holds on it at four seeds in `lookback`, and `FACE_BY_JOB`
  takes precedence anyway, so the `face: moe-far` entry there is now only
  reached by jobs with no face of their own.

## Momiji: 32 renders, and a character that does not behave like the others

Standing, black tights, a black inner layer under the sleeveless turtleneck.
The class block came off the danbooru wiki rather than out of memory — guessing
Takao's costume cost two rounds, and that was enough.

Round by round, one change at a time:

| round | change | result |
|-------|--------|--------|
| 1, 8 seeds | the block as written, tights, faint inner | 6 of 8 clean; no feet at all, inner reads as shoulder patches |
| 2a, 4 seeds | `(black turtleneck:1.45), (black undershirt:1.4), (black long sleeves:1.35), (layered clothes:1.3)` | the inner becomes a collar, sleeves and a waist band |
| 2b, 4 seeds | `(geta:1.3), sandals` | red tengu-geta, 4 of 4 |
| 3, 8 seeds | both at once, six extra tags | **8 of 8 clean, nothing pushed out** |
| 4, 8 seeds | sword and shield; two standing variants | armed 2 of 2 clean; the pose variants duplicated the figure on one seed and not the other |

**Adding tags did not cost anything here, and that is the surprise.** Six extra
tags on an already long block, then a sword and a shield on top, and the costume,
the legwear and the palette all held. Everywhere else in this file, weight is the
master variable and a new tag is paid for by an existing one.

The distinction that survives the evidence is not "new object versus existing
part" — the sword and the shield are new objects and they were free. It is the
seed. `4051776310` drew two figures for both pose variants, `737373737` drew one
for both, same tags. Duplicates on this character track the seed, not the length.

Momiji is also the first character whose danbooru tag carries almost the whole
costume: the maple-print skirt, the pom poms and the detached sleeves arrive
without being weighted, where Yukari's tag needed the hoodie spelled out.

Two recurring defects, both palette rather than structure: the maple leaves turn
yellow on some seeds (`3992482423`, `3062102535`, and `555666777` in round 1),
and the tights come out grey rather than black on others (`246813579`). Neither
was chased.

Left out on purpose and still out: nothing. Sword, shield and geta were all held
back at the start on the assumption they would be expensive, and all three were
free when finally tried.

## `--scene`: putting her in a place, in one flag

The warm-interior look was reached by hand: about forty tags of room, light and
lineart in `--extra`, plus `--drop` on three tags that are hardcoded into every
minimal render — `(flat color:1.3)`, `(simple background:1.3)` and the grey
background. Three `--drop`s to remove something there is no flag for is a
workaround, not a setting, and nothing about it was reproducible.

`--scene warm-room` substitutes for that block instead:

```bash
uv run scripts/queue_dq3.py --job momiji --pose sitting --scene warm-room \
  --width 1024 --height 1536 --minimal --face moe-far-noeye --seed 737373737 \
  --extra "<costume and body tags>"
```

Verified against `at-warm` (`1fa0982e`): identical tag set apart from the
per-render `--extra`, and the render holds the pose, the light, the room and the
costume. Not byte-identical — the scene tags now sit where the background line
was rather than at the tail, and position is known to matter here, so the two
renders differ in small ways.

Three things are deliberate in the entry:

- **Room, light and line travel together.** Splitting them was tried and the
  room came out lit like a studio; the light block is what makes a window at
  night read as a window at night.
- **Substitution, not addition.** Leaving the flat-colour field in and adding a
  room on top gives a room drawn in flat colour, which is what neither half
  wants.
- **`--scene` errors without `--minimal`** rather than doing nothing. A flag
  that silently no-ops on the wrong path has already cost this project a round
  of ablations that looked performed and were not.

`--border` is a cut-out device and does not belong with a scene.

## Substitution is free, addition is not — measured

The clearest measurement of this in the project, on Yukari stretching and
yawning from above, with the layered legwear on.

| change | how it was made | clean |
|--------|-----------------|-------|
| `(closed eyes:1.35)` | added to `--extra` | **0 of 4** |
| `full body` → `cowboy shot` | substituted in the pose block | 3 of 4 |
| `round eyes` → `(half-closed eyes:1.3)` | `--drop` plus `--extra`, net zero tags | 3 of 4 |

Same four seeds across the first two rows, everything else byte-identical. One
added tag tipped every seed into drawing a second figure; a swap of equal length
cost nothing. The rule had been inferred from the chair block before this
(`gaming chair` substituted for `office chair` was free, a five-tag gaming-chair
block returned noise) — here it is isolated.

`(half-closed eyes)` is also the tag that worked when `(squinting)` shut the
irises during the expression round. Same intent, different shape, and now it is
also the way to pay for a sleepy expression without adding to the count.

Two other things this round settled:

- **The chair brings the intruder back.** Both runs that added the gaming chair
  to this pose grew the backdrop creature at the top left. That is the failure
  already recorded against the chair for Yukari, and adding it to a different
  pose does not escape it.
- **The camera shows a thigh; a tag does not have to.** `(from above:1.4)` with
  a short dress does it on its own. `(overhead shot)` is a step too far — it
  puts the camera in the lap, which is the framing this project does not
  develop, and it was dropped rather than tuned.

## The rough-sketch feel: it was the surface block, and it needed a number

The complaint was that renders look like coloured roughs. Three rounds of tag
work missed it entirely, and the reason they missed it is worth more than the
answer.

What was tried and did nothing. Dropping `--flat-paint`, whose negative bans
`(heavy shading:1.2)` and `(detailed shading:1.2)` by name. Adding
`(clean lineart:1.4), (crisp edges:1.3), (smooth shading:1.35)`. Adding the two
Illustrious aesthetic-score tags `QUALITY_PLAIN` deliberately leaves out. All
three were single-variable runs on one seed, and all three came back
indistinguishable from the baseline.

A second pass at 1.25x added hair strands and softened the line — a trade, not a
fix. 1.5x is not available: VAEEncode at 1536x2304 dies on MPS with
`MPSGraph does not support tensor dims larger than INT_MAX`, so whole-image hires
tops out at 1280x1920 on this machine.

Framing does move it. Zooming the sage in to `cowboy shot` brought fabric folds
and chest shading that the full-body shot has no pixels for; and the reverse test
is the one that mattered — Yukari's accepted `resuba` recipe, re-shot at
`standing, full body`, comes back as flat as the sage, and duplicates on 2 of 2
seeds. She was never a better recipe. She was a closer crop.

### The actual cause

The `GLOSS` block — `(taut fabric:1.25), (stretched fabric:1.2),
(soft shading:1.25), smooth fabric, (specular highlights:1.3), light streaks` —
sprays short strokes across the inside of every flat garment, and stages the
figure to display cloth: from the render it entered onwards the sage stopped
holding his staff and stood with both arms spread holding the cape open. One
block, two symptoms, and the fix is to not use it.

### Why three rounds of eyeballing could not find that

Changing one tag does not edit the picture, it draws a different one. So a
one-render-versus-one-render comparison cannot separate a tag's effect from the
sample it happened to land on, and every confident reading here that came from
such a pair turned out to be wrong — including "`pt-c`'s line is cleaner than
`bs-a`'s", which the metric scores the other way round. Judging from torso crops
made it worse: the composition had broken while the crops looked fine.

`scripts/flat_scratch.py` is what replaced the eye. It counts edge pixels
surviving inside areas that should be flat fill. The first version counted short
edge components across the whole frame and ranked the best render worst, because
a gold trim line and a stray fold stroke look identical to it; restricting the
count to flat interiors is the entire idea.

    no surface block   0.06 - 0.22
    surface block      0.53 - 0.99
    lb-lap             2.04          costume dissolved outright

No overlap, across nine renders. Then six fresh seeds on the parts-only recipe,
with 0.25 declared as the threshold before the run: 0.059, 0.071, 0.115, 0.127,
0.156, 0.219. Six of six, worst case inside the bound, and all six hold the
staff, the trim, the legwear and a normal chest.

**Those numbers are the sage's and do not generalise.** The metric counts fine
line inside flat-ish areas, and whether that is a defect depends on whether the
costume is meant to be plain there. His garments are large unbroken fields, so
line inside them is stray. Yukari's dress is ribbed and her thighhighs carry
highlight bands by design, and on her the ranking inverts outright: the accepted
`rb-sh` scores 1.842 and `zy-full` — flat, duplicated, the render everyone agreed
was bad — scores 0.165. Calibrate per character, and never carry a threshold
across. This was first written up as a general roughness measure, which it is
not.

### What the parts block buys, and where it does not

Adding small parts is what closes the gap to Yukari without touching the
framing: `(gold trim:1.25), (embroidery:1.2), (cape clasp:1.2),
(belt buckle:1.2), (decorated hem:1.2), (hair strands:1.2)`. The sage's costume
is three large flat fields and has nowhere for a line to go; the block gives the
dress a gold hem band and the buckle an emblem, and it survives at full body.

It does not transfer blindly. On Takao it lands cleanly, because dress uniform
has trim and fastenings a line can follow. On Momiji it replaced the costume
rather than decorating it — `(fur trim)`, `(tassel)` and `(decorated hem)` came
back as a white robe over the sleeveless top. Her costume already carries the
small parts the sage's lacks, which is the density argument working in reverse.

### Two corrections to earlier entries

`(wide hips:1.2)` and `(thick thighs:1.3)` were being carried on characters that
never asked for them, copied over from Yukari's block. They are what inflated the
chest on every closer framing, worst on the sage because his dress is a strapless
tube top and there is nothing under the volume to support it. Removing the two
tags fixes it; naming the chest in the positive does not. `(medium breasts:1.3),
(perky breasts:1.25)` made it larger and pulled the framing in — naming a part
raises its salience whatever the adjective says, the same way lowering
`(large iris:1.4)` made the backdrop eye worse.

And the nine-tag pose-block ceiling recorded in the chair section is not about
tag count. `pt-b` added twenty-four tags with nothing pushed out, while a
thirteen-tag `kneesup` block shredded the costume. The rule is that a pose block
costs the garment only where the two specify the same thing: `kneesup` carries
`(soles:1.25)`, `(foreshortening:1.3)` and `(adjusting legwear:1.3)`, which are
bidding for the legs and the clothing. Decoration, which competes with nothing,
is free at any length.

## Fixing a character when pose and expression are explicitly not part of it

The brief was full hips and healthy thighs, upper body left slight, a character
confident and hopeless at once — and pose and expression deliberately excluded.
That last part decides the method: a spec that excludes framing can only be
validated by varying framing. Four expressions crossed with two framings and two
seeds, holding nothing but the body block. See `pick/yk-body-spec`.

    --extra "(wide hips:1.3), (thick thighs:1.35), (narrow waist:1.25),
             (petite:1.2), (pale skin:1.25), (hood down:1.5),
             (hood behind head:1.3), (visible hair:1.2)"
    --negative-extra "(huge breasts:1.4), (large breasts:1.25), cleavage"
    pose block opens with (solo:1.5)

`(narrow waist)` and `(petite)` are what make this read as the brief rather than
as bulk. 安産型 names the drop from hip to waist, not the size of the hip, and the
candidate that raised the volume instead — `(wide hips:1.4), (thick thighs:1.45)`
— gave fuller thighs and a worse silhouette.

### Three things that did not transfer, and one that did not work at all

The hardened chest guard from the sage does not transfer. `bs-c` established that
volume tags plus `(breasts:1.2)` in the negative holds his chest down; on Yukari
the same block pushed the entire palette to a saturated purple and destroyed the
pale-thighhigh-over-dark-tights contrast, on 9 of 9. The difference across those
nine was the guard alone. The plain three-tag guard is enough for her and costs
nothing.

The clone in the empty canvas is a positive-side problem, and this was learned
twice. Adding `(2girls:1.6), (multiple girls:1.6), (duplicate:1.55),
(another person:1.5)` and `(chibi:1.4)` to the negative took the clone rate from
5/8 to **7/8** and wrecked the palette, the border and the background with it.
`(solo:1.5)` at the head of the pose block took it to 0/8 and left everything
else untouched. This is the backdrop-eye lesson again: naming the intruder louder
feeds it.

Two framings are unusable for her, and neither is a body problem:

    standing, full body     9 of 9 duplicated
    sitting + cowboy shot   3 of 4 dropped to a low angle with the thighs forward

Yokozuwari and the chair both come back clean. The standing result matches
`zy-full` duplicating on 2 of 2 earlier — a full-body standing shot leaves
vertical canvas this prompt fills with a second figure, and `(solo:1.5)` was not
tested against it.

## Hamakaze: cloning a character onto the standard face, and six rounds after

The clone itself is cheap. Fill in `CLASSES`, `BASE_BY_JOB`, `EYES_BY_JOB`,
`FRANCHISE` and `LEGWEAR_BY_JOB`, and `--job hamakaze --minimal --face
moe-far-noeye --border --flat-paint mild` draws her in the same look as the
others. The class block came off the danbooru wiki and her co-tag frequencies,
per the rule Takao's two wasted rounds bought. `(hair over one eye:1.35)` carries
a weight because it is the one thing separating her from every other grey-haired
destroyer, and at 1.0 it came and went by seed.

What that got was a correct costume and nothing else — flat, and on six standing
renders, a giant disembodied eye on one seed and a duplicate on another. Six
rounds of brush-up followed. The recipe is `pick/hamakaze-invite`; what
generalises is below.

### A tag block cannot be moved out of the context it was tuned in

`(thin lineart:1.45), (black lineart:1.4), (defined lines:1.2)` lives in
`SCENES["warm-room"]`, where the note says Illustrious tints the outline to match
the fill and only asking for black ink brings the drawn line back. That diagnosis
is correct and it applies to Hamakaze exactly — a white shirt and grey hair over a
pale field is the case it describes. Copied across whole, the block *lowered* ink
coverage and edge contrast on 3 of 3, because `(thin lineart:1.45)` is also
obeyed and a thinner line is a weaker one. Dropping the thinning and keeping
`(black outline:1.4), (defined lines:1.25), (crisp lines:1.2)` raised edge
contrast on 3 of 3 and put real black in the frame: the darkest 1% of pixels went
from luminance 4–7 to 0–1. Adding `(outline:1.3), (thick outline:1.2)` on top
changed nothing measurable.

### "Yukari quality" is not a number

Measured with `scripts/inkiness`-style stats — fraction of pixels below 80/255,
mean luminance of the darkest 1%, mean Sobel magnitude — her own accepted renders
disagree with each other:

    rb-sh (resuba)        ink 18.73%   edge 48.35
    so-smug-yo            ink  7.70%   edge 35.90
    Hamakaze, six seeds   ink 9.7-14%  edge 32.7-57.3

Hamakaze sits inside Yukari's own range and exceeds `rb-sh` on two seeds. What
makes `rb-sh` read as inkier is a black hoodie filling most of the frame. The
residual gap is dark mass, which is a costume property, not the drawing.

### Repeats of things already in this file

`(lap pillow)` and `(pov)` name a second person. With `(solo:1.5)` in the
positive **and** four duplicate guards in the negative, they still drew a second
Hamakaze on her own lap on 5 of 6. Deleting them and describing the invitation
instead — seiza, a hand on her own thigh — gave 6 of 6 solo. Identical to the
`(head on lap)` finding in `pick/momiji-lap`.

`(cuffs:1.2)` was read as wrist cuffs and put dark restraints over her white
gloves on 3 of 3. A decoration tag lands on whatever in the frame will take it,
the same way `(fur trim)` replaced Momiji's costume rather than trimming it.

`(soft shading:1.3), (gradient shading:1.15)` measured flatter, not richer —
`flat_scratch` 0.580 → 0.224 — and were invisible by eye. Shading tags are not a
route to finish.

### A note on the metric trap

Of three `hi-c` renders, the one with the highest edge contrast (53.27) was the
one with a backdrop intruder in it: the intruder was supplying the contrast.
Numbers rank, eyes disqualify, and neither does the other's job.

## Matching a reference look is subtraction, and it is not the same as improving

Asked to put the `5f323a1a` look — a Yukari render, `gl-lecture-111222333` — onto
Hamakaze. Diffing the reference against what she had accumulated over six rounds
of brush-up showed the reference is the *simpler* prompt. It carries none of the
lineart block, none of the hair block, none of the collar/buttons parts block,
none of the cloth-wrinkle block, and none of the fabric-physics legwear — all
five of which had been added to her while trying to make her better. Reaching the
look meant deleting all five. See `pick/hamakaze-yk-style`.

The measurement that makes the point, on ink coverage, mean luminance of the
darkest 1% of pixels, and mean Sobel magnitude:

    reference (Yukari)        ink  8.81%   darkest 21.5   edge 29.28
    Hamakaze, ported          ink  4.80%   darkest 16.2   edge 35.02
    Hamakaze, previous build  ink 13.96%   darkest  1.1   edge 46.92

`darkest` is the one that decides it. **The reference does not draw black ink.**
At 21.5 its outline is tinted toward the fill — that tinting is the look, the
same behaviour `SCENES["warm-room"]` describes as something to fight when you
want a drawn line in a room. The previous build sat at 1.1, true black, because
`(black outline:1.4)` had been added and *measured as an improvement on three of
three seeds*. It was an improvement. It was also directly away from the target.

Better and matches-the-reference are different axes. A metric can rank one of
them; it cannot tell you which one you were asked for.

### Prefix collision

`ys-` had been used by an earlier session, so these landed as `_00002_` while the
`_00001_` files were a different day's Yukari renders. Three of four contact-sheet
cells showed the wrong character until the graph embedded in each PNG was read.
Check whether a prefix is already on disk before reusing it, and identify a
render from its embedded prompt rather than from its filename.

## Hamakaze: changing the art style, and getting a line into the hair

Six sweeps in one session, all on Hassaku, all seeded 111222333.

`scripts/style_sweep2.py` through `style_sweep6.py` are the sweeps, in order.
`scripts/line_overlay.py` extracts lineart from a finished render and multiplies
it back on; `scripts/colorize_lineart.py` colours an authored lineart through a
ControlNet.

Each sweep holds everything but one axis, so re-running one and reading its diff
against the numbers below is how to check whether a conclusion still stands.
`style_sweep2.py` reads the base it varies out of `/history` rather than carrying
a copy — `--from-prompt` refetches and caches it, which is needed after a ComfyUI
restart drops the history.

### A LoRA is not the style lever

`outlined-ill` at 0.8, 1.0 and 1.3, `usnr-style-ill-v1` at 0.8 and 1.1,
`moe-2000s-a` and `-b`, `mozudoll` — nine renders, one face. What moved was the
thickness of the silhouette outline and nothing else. The face, the hair
construction and the proportions were identical across all of them.

The style LoRAs on disk carry their style on a trigger the first sweep never
passed. From `ss_tag_frequency` in the safetensors metadata: `usnr` for
usnr-style, `cheeky \(mozudoll\)` for mozudoll, `re4lity_sync_illu` for re4lity.
`outlined-ill` has none. A style LoRA run without its trigger is stacked but not
fired, which is why `sw-lora-usnr-style-ill-v1` looked like the bare base.

### The era-tag slot

The `st-ukiyoe` / `st-water` / `st-retro` / `st-mono` sweep from a previous day
moved the palette and left the face alone, which reads as "abstract style words
do not move Illustrious". That is the wrong conclusion. The recipe already
carried `2000s (style)`; the slot was occupied, and a second style word on top of
it does nothing. Drop `2000s (style)` and `(1980s (style):1.5)` comes through
hard — face length, nose bridge, and where the hair highlight sits all change.
`1990s (style)` likewise, with heavy cheek blush as a side effect.

Only `st-chibi` moved under the old recipe, because head-to-body ratio is not a
style word competing for that slot.

### What made the face read as a child

`(petite:1.2)`, `(large eyes:1.3)`, `(large iris:1.25)`, `small mouth` and
`2000s (style)` in the positive, and `(realistic:1.1)` in the negative — the last
one placed there to ban oil paint, pushing away from adult proportions as a side
effect. Removing those five and releasing `realistic` narrows the eyes and
lengthens the face on its own, with nothing added. `mature female` + `aged up`
and a `tareme`→`tsurime` swap are separate dials on top of it and can be stacked.

Invented descriptors — `defined jawline`, `small head`, `realistic proportions`,
`thin face`, `long neck` — are outside the training vocabulary and do nothing.
Half of one proposed sweep was tags that could not fire. Check a tag exists
before spending a render on it.

### Interior hair line: two tags that are superadditive

Measured as the share of pixels in a box strictly inside the hair mass whose
local gradient exceeds 12, against 13.7% for the accepted render:

    strand tags raised to 1.5/1.55/1.3 alone       16.9%   +23%
    (flat color:1.3) released alone                17.5%   +28%
    both                                           23.0%   +68%

Neither is worth doing without the other, which is why releasing flat colour on
its own was first written off as ineffective. Two hypotheses died here:
`(shiny hair)`/`(hair highlights)` in the negative scored *below* the reference
(13.1%) — clearing the highlight blob does not free room for a line, it just
leaves the mass empty — and `outlined-ill` at 1.1 scored 13.6%, i.e. nothing.

### The line has to exist before the colour

`AnimeLineArtPreprocessor`, `Manga2Anime_LineArt_Preprocessor` and
`LineartStandardPreprocessor` at sigma 6/1 and threshold 8/4/2 — six extractions
from one finished render. Every one returned the bangs as an empty black region
with only the outer contour drawn. The bangs are a plane in the source, so there
is no line to recover, and multiply-compositing at 0.3/0.5/0.7 changed nothing
visible. Drawing the line last cannot work on a flat-coloured render.

Drawing it first can. A lineart pass — `(lineart:1.5), (monochrome:1.4),
(greyscale:1.35)`, with `(flat color)` and the sticker block absent — makes
Hassaku draw the bangs as strands, on the same seed and the same character tags.
The model always knew how; the flat-colour block was erasing it. Feed that
lineart inverted into `noob-canny-fp16` via `ControlNetApplyAdvanced` and the
strand lines survive the colour pass.

ControlNet strength runs slightly backwards: 0.6/end 0.8 keeps *more* line
(17.0%) than 1.0/end 1.0 (15.7%). Held hard enough, the colour pass reproduces
the lineart's white areas faithfully and stops drawing shading of its own. The
spread is 1.3 points, so 0.6 is a fine default.

### Bangs against side hair: still 0.66

The bangs carry 0.66 of the side hair's line density, and the deficit is already
in the lineart — the colour pass inherits it (0.65, 0.62) rather than causing it.
Seven lineart variants later the ratio sits between 0.66 and 0.70. Every tag
that helped raised both regions together; none raised the bangs alone.

`(hair over one eye:1.35)` was the suspect — a curtain across the face is a
smooth sheet by definition, and it covers exactly the short region. It is not the
cause: at 1.1 the ratio stays at 0.66 and the bangs gain 0.5 points. The
character's silhouette does not have to be given up for this.

`(messy hair:1.35)` raises the bangs 21% and is where the flyaway strands come
from — one tag, so it is available on demand, and avoidable. `(parted bangs:1.35),
(hair between eyes:1.3)` is the pick: +16% on the bangs, no flyaway, ratio 0.70.
Stacking everything (`lb-combo`) scores highest but breaks the monochrome
constraint — the hairclip picks up colour and the ground turns grey.

Raising the strand weights on top of `parted bangs` adds nothing: 17.75% against
17.78% for `parted bangs` alone. The two do not compose, unlike the strand/flat
pair above.

### The lineart's advantage does not survive the colour pass

`lb-parted` carries 16% more line in the bangs than the lineart it replaced.
Coloured at strength 0.6 / end 0.8, the finished renders come out at 0.64 and
0.59 against 0.65 for the old lineart — level, or worse. The gain is spent
somewhere in the colour pass, and on `lb-parted-dense` the side hair rose
(29.5% → 30.9%) while the bangs fell.

The obvious explanation — the ControlNet releases at 80% and the colour pass
redraws the hair over the last fifth — is wrong. Holding it to the end changes
nothing and costs line:

    s60-e80    18.97%   ratio 0.64
    s60-e100   18.41%   ratio 0.64
    s80-e100   18.07%   ratio 0.63
    s100-e100  17.49%   ratio 0.63

What is left is a constant. Every coloured render measured — from three different
linearts at ratios 0.66 to 0.70, across four strength/reach settings — lands
between 0.59 and 0.65. The colour pass imposes its own bangs-to-side ratio of
about 0.64 and neither the drawing it is given nor the force it is held with
moves it. That also settles the earlier reading that strength *hurts* line
retention: it was measured with the lineart held identical, and it holds here
too, where the lineart differs.

Both renders also came out nearly unshaded despite `(cel shading:1.45)` in the
positive, because `(shading:1.3)` was still in the negative — the lineart pass's
negative was reused wholesale for the colour pass. They need to be separate.

### Regional conditioning is what moves the ratio

`ConditioningSetMask` over a rectangle on the bangs, a strand-only prompt inside
it, `ConditioningCombine` with the ordinary one, and the ControlNet applied after
the combine so the line still holds across the whole frame. Core nodes only —
`SolidMask`, `MaskComposite`, `FeatherMask`, no custom pack.

    region strength 0.0   bangs 18.97%   side 29.54%   ratio 0.64
    region strength 0.6   bangs 19.29%   side 28.35%   ratio 0.68
    region strength 1.0   bangs 19.42%   side 27.70%   ratio 0.70
    region strength 1.5   bangs 19.27%   side 28.50%   ratio 0.68

1.0 is the peak and 1.5 is past it. It reaches the lineart's own 0.70, and the
bangs are the densest of any coloured render measured — but the number that
matters is that the bangs rose while the side hair *fell*. Nothing else tried
moved the two in opposite directions; a tag in the shared prompt cannot, because
it is the same prompt for both regions.

Strength 0.0 reproduces `cz-lb-parted-canny-s60-e80` to the digit (18.97/29.54),
which is what makes the rest of the ladder attributable.

The region prompt names no character and no costume, only hair rendering. That
is deliberate: a full prompt inside a mask is how a second face appears in the
region.

Covering more of the hair beats aiming at the bangs, which is backwards from what
narrowing a region is supposed to do. Adding two side rectangles to the bangs one
(`--mask hair`):

    no region                bangs 18.97%   side 29.54%   ratio 0.64
    bangs rectangle, 1.0     bangs 19.42%   side 27.70%   ratio 0.70
    whole hair, 1.0          bangs 21.82%   side 28.49%   ratio 0.77
    whole hair, 1.4          bangs 21.75%   side 28.42%   ratio 0.77

The bangs gain 15% over no region at all, and 1.0 is again the plateau. A guess
at why the narrower mask does worse: the bangs rectangle cuts across the middle
of the hair, so the two prompts compete along a border drawn through the thing
they are both describing, where the hair mask's borders mostly fall outside it.
Untested — it would need the same mask at different border positions.

The masks are rectangles (bangs is x 240, y 0, w 580, h 360, feather 48) — enough
to answer whether regional conditioning moves the ratio at all, which it does.
Cutting a mask that follows the hair is the obvious next step.

One bug worth remembering: the loop that adds a rectangle per mask allocates node
ids from 21 upward, and the `FeatherMask` after it was fixed at 23. With one
rectangle nothing collides; with three, the feather overwrites a `SolidMask` and
the composite chain ends up referring forward to it. Validate a built graph for
dangling references and cycles before queueing it — it costs nothing and this one
would have been three renders of confusing output.

### canny was the wrong ControlNet the whole time

`Eugeoter/noob-sdxl-controlnet-lineart_anime`, the diffusers `fp16` file renamed
to `noob-lineart-anime-fp16.safetensors` — 2.3GB, the same size class as the
other three, and ComfyUI loads the diffusers layout directly, so the 4.7GB
single-file build is not needed.

    canny,    strength 0.6 / end 0.8    bangs 18.97%   side 29.54%   ratio 0.64
    lineart,  strength 0.6 / end 0.8    bangs 21.63%   side 30.32%   ratio 0.71

That is the regional-conditioning result (21.82%, 0.77) reached with no mask at
all, from swapping the model. canny is trained to hold an edge *map*; handing it
a drawing and asking it to preserve the drawing is a mismatch, and the strand
lines were what fell through it.

The hint is fed as drawn, not inverted. canny and softedge want white-on-black,
which is why `ImageInvert` was in the graph; lineart_anime is trained on the
lineart itself, so inverting it hands the model a photographic negative of what
it expects. `CONTROLNETS` in `colorize_lineart.py` carries that flag per model.

### They do compose

Level separately, and I wrote down that there was no reason to expect them to
add. They add:

    canny,   no region                    bangs 18.97%   side 29.54%   ratio 0.64
    canny  + hair region                  bangs 21.82%   side 28.49%   ratio 0.77
    lineart, no region                    bangs 21.63%   side 30.32%   ratio 0.71
    lineart + hair region                 bangs 25.47%   side 33.65%   ratio 0.76
    lineart + hair region + flat-noreal   bangs 23.18%   side 31.83%   ratio 0.73

25.47% is 17% above the better of the two alone and 34% above where the two-pass
pipeline started. They are doing different jobs — the ControlNet decides how much
of the drawing survives, the region decides how much line is asked for where —
so the reason to expect no interaction was really just an absence of evidence.

Adding `flat-noreal` on top costs line (23.18%) and buys back the flat look. That
trade is a taste call, not a defect: it is still above lineart alone.

### (flat color) is free again once the ControlNet holds the line

It cost the strand lines when the prompt was the only thing asking for a line.
That is no longer the situation, and the finding does not survive the change —
with lineart_anime holding the drawing, putting the flat block back costs
nothing:

    cg (no flat block)          bangs 21.63%   side 30.32%   ratio 0.71
    + (flat color:1.3)          bangs 21.67%   side 34.26%   ratio 0.63
    + flat, white outline,
      outline, sticker          bangs 20.95%   side 30.90%   ratio 0.68
    + flat, (realistic) cut     bangs 19.39%   side 24.08%   ratio 0.81

Without the flat block the colour pass renders in the base's smooth CG shading,
and `(realistic:1.3)` in the face block is a second, independent source of it.
Cutting both is the flattest, most cel-like result and it holds the best ratio
measured anywhere — 0.81 — at some cost in absolute line, though still above
what canny managed with no flattening asked for at all.

A conclusion measured under one mechanism does not carry to another. This one was
recorded four sections above as a hard rule about `(flat color)` and was already
false by the time the ControlNet changed.

### Detail Daemon: the number goes up, the picture does not

`ComfyUI-Detail-Daemon` on the stacked best, region 1.0 through lineart_anime:

    KSampler                       bangs 25.47%   side 33.65%   ratio 0.76
    custom sampler, detail 0.0     bangs 25.47%   side 33.65%   ratio 0.76
    detail 0.10                    bangs 26.76%   side 36.19%   ratio 0.74
    detail 0.25                    bangs 30.35%   side 38.68%   ratio 0.78

The control matters: rebuilding on `SamplerCustomAdvanced` at `detail_amount` 0.0
reproduces `KSampler` to the digit, so the rest of the ladder is the node and not
the rebuild.

And the rest of the ladder is not line. At 0.25 the bangs have bright blue
strands running through grey hair, and there are yellow specks on the background;
at 0.10 the same thing is starting. Edge density counts a saturated colour band
exactly like a drawn line, so 30.35% is chroma breaking, measured as an
improvement. The caveat written a section below — that the measure counts any
luminance step — stopped being a caveat here and became the whole result. Look at
the render before believing the ladder.

Detail Daemon is not broken; grey hair under near-flat colour is just where it
breaks first. Under 0.10, or a narrower `start`/`end` window, is where it would
have to live on this character.

Yukari confirms that reading. `scripts/queue_dq3_detail.py` swaps the sampler
under whatever recipe queue_dq3 builds, so `--job yukari` runs the tuned recipe
with only the sampler changed. At 0.10 and 0.25 there is no chroma break at all —
what the node adds is strand lines in the hair, folds in the hood and a cast
shadow behind the figure, and the purple stays purple. A character made of colour
gives the extra detail somewhere to go; on grey under flat colour the only place
left is hue, which is what those blue strands were.

The control here is stronger than Hamakaze's: `detail_amount` 0.0 through
`SamplerCustomAdvanced` is *pixel-identical* to `KSampler`, same sha256.

Unrelated defect in those renders: all three drew two figures. It is present in
the base, so it is not the node — it is the duplicate-figure problem, run with no
`--pose` and so probably without the `(solo:1.5)` placement that fixed it.

### Measuring

Edge density in a hand-placed box ranks variants within one sweep and nothing
else. The framing changed between the flat-colour sweeps and the two-pass ones,
so those numbers are not comparable across the two, and the measure counts any
luminance step — a highlight boundary scores the same as a drawn line. It sorted
the rungs correctly every time it was checked against the images, which is all it
was used for.

## Swapping the character under a lineart ControlNet: 0.6 carries the hairstyle over

`7219d431` is a Hamakaze render on the lineart-ControlNet pipeline —
`noob-lineart-anime-fp16` at strength 0.6 over 0–80%, source
`br-src-lb-parted.png`, plus a hair-region prompt through `ConditioningSetMask`
and a Detail Daemon finish. Putting Yukari on it means editing the character
span of the positive and leaving everything else byte-identical
(`scratchpad/yk_face.py`). Her costume, colours and expression came over
correctly. Her hairstyle did not: she came out in Hamakaze's short parted bob,
and her hair was a much deeper purple than `(light purple hair:1.25)` asks for,
with teal streaks that nothing in the prompt names.

Two candidate causes, and the sweep (`hr-c60`/`hr-c35`/`hr-c00`, one seed,
prompt fix in all three, strength 0.60/0.35/0.00) separated them:

- the region prompt still said `(parted bangs:1.4)`, a Hamakaze hairstyle tag
  aimed at the hair mask at strength 1.0, left behind by the character swap;
- the ControlNet was holding the silhouette.

**It was the ControlNet alone.** `hr-c60` fixed the region prompt and changed
essentially nothing — same bob. At 0.35 the hairstyle is Yukari's outright:
long sidelocks in front, the ring hair ornaments, the rabbit hood sitting
properly on the head. The deep purple and the teal streaks went with it, which
says those were structure read out of the source lineart rather than anything
the prompt did. At 0.00 the hood closes over the head and the hair mostly
disappears, and a white sticker outline appears — worse for showing a hairstyle.

So a lineart ControlNet strong enough to be worth borrowing is also strong
enough to transfer the donor's silhouette. Tags that change an outline —
`(short hair with long locks:1.45)`, `(very long sidelocks:1.3)` — are exactly
the ones it overrides, while tags that only fill an area (costume, colour,
expression) pass through untouched. Around 0.35 both survive on this graph.
Upper-body framing held at 0.35, so the composition is not the thing that pays
for it here.

## Strand line does not come from the prompt, and the hood was hiding the hair

Following the 0.35 result: the hairstyle was right but the strand line was gone,
replaced by smooth colour blending. Two asks, and they came apart —

  hl-a  strand-line weights up ((defined hair strands:1.9),
        (hair strand outline:1.7), (black lineart:1.55)) plus (flat color:1.3)
        inside the hair mask
  hl-b  hl-a + (gradient:1.35), (soft shading:1.35), (airbrush:1.3),
        (smooth shading:1.3), (glossy hair:1.25) in the negative, which had no
        guard against tonal blending at all before this
  hl-c  hl-b + (hair strands:1.5), (clumped hair strands:1.4)

**All three went the wrong way.** Head-box edge density, comparable across these
four because the composition is identical: c35 12.5, hl-a 10.3, hl-b 9.6,
hl-c 9.8. The negative guards did remove the colour shading, which was half the
ask; nothing replaced it with line, so the hair just went flatter. Raising the
line weights to 1.55/1.7/1.9 added nothing — the same null result as `hr-c60`,
where fixing the region prompt changed nothing while the ControlNet held.

So on this graph the strand line is written by the ControlNet source, not by any
tag. `br-src-lb-parted.png` is a real lineart drawing with strand lines in it,
and at 0.6 those were being copied; the prompt was never doing that work.

`hd-yk` takes the hood off — `(rabbit hood:1.55), animal hood` substituted with
`(hood down:1.45)`, plus `(hood up:1.4), (animal hood:1.35)` in the negative —
and the hair comes back with drawn clumps and separations. The hood was covering
the hair at low strength, so no amount of hair-region prompting had anywhere to
land. Its edge density is 13.2, but **that number is not comparable to the four
above**: the box changed from mostly hood to all hair, so it is measuring
something else. The line is visible by eye; the number is not the evidence.

`hd-hz` is the same graph with Hamakaze back in it, and scores 11.9 against
Yukari's 13.2. The worry that Yukari was disadvantaged by being drawn over a
Hamakaze lineart is not supported at 0.35 — she gets more strand line than the
character the source depicts.

Next lever, and the only one left: extract a lineart that has strand lines in it
from `hd-yk` and drive the ControlNet with that at 0.6. That resolves the
silhouette-versus-detail tug-of-war, because the silhouette being enforced would
finally be hers.

## Her design lived in the tags the port dropped, and three of them were sign-flipped

The port kept Yukari's class block and nothing else, and by `hd-yk` the result
had stopped reading as her. Diffing against `gl-lounge-555666777` (job
`38918ed3`, the render Hamakaze was derived from — its graph is embedded in the
PNG; ComfyUI's `/history` only retains about 18 entries, so the file is the
record) found three tags pointing the opposite way:

| | `38918ed3` | the port |
|---|---|---|
| realistic | negative `(realistic:1.1)` | positive `(realistic:1.3)` |
| shading | `(flat color:1.3), (soft shading:1.3), smooth shading`, with `(heavy shading:1.2), (detailed shading:1.2)` negative | `(cel shading:1.45), (sharp shadow edges:1.35), (two-tone shading:1.3)` |
| hood | `(rabbit hood:1.55)` **kept** and pushed down with `(hood down:1.5), (hood behind head:1.3)`, `(hood up:1.5)` negative | hood up — and `hd-yk` deleted the rabbit hood outright, which the reference never does |

Missing entirely: `2000s (style)`, `(white outline:1.6), outline, sticker`, the
eye block (`(large eyes:1.3), (large iris:1.25), thin eyebrows, small mouth`),
and the body block. Restoring all of it (`scripts/yk_restore.py`) brought back
the near-white lavender hair, the spool hair ornaments, the red round ear
ornaments, the ribboned frilled dress and the red-lined hoodie in one step.

Two things fell out of it:

- **`(upper body:1.4)` does not hold the framing here.** All three restored
  renders came out down to the thighs with it in the positive.
- **Detail Daemon is invisible on this recipe.** `rc-b` (ControlNet off, Detail
  Daemon on) and `rc-c` (plain KSampler, neither) are near-identical. Its
  earlier gain was measured on a cel-shaded, chroma-breaking render; on flat
  colour there is nothing for it to sharpen.
- ControlNet at 0.35 still drags the pose even when the character reads right —
  `rc-a` put a spare arm up that neither of the others has.

The lesson to carry: a character's identity is not the class block. Porting one
onto another character's graph moves the class block and leaves the identity
behind, and the parts that go missing are the ones nobody wrote down as
belonging to her.

## The line is 1.91px wide and no tag changes that

Framing first: `(upper body:1.4)` lost to the canvas — all three restored renders
drew down to the thighs with it in the positive. `(portrait:1.5),
(head and shoulders:1.4), (close-up:1.2), (face focus:1.3)` plus `(full body:1.5),
(cowboy shot:1.45)` negative held it, but only once the canvas went square:
1024x1024 cropped to the chest, 1024x1280 did not. **The frame shape is a
framing control, not just an output size.**

Then the thinness question, which had an assumption in it worth checking before
spending renders on it. Median stroke width, from a distance transform over the
dark-ink mask:

    1024x1024 portrait          1.91px
    1024x1280                   1.91px
    1024x1536 full body         1.91px
    1024x1536 + thin-line tags  1.91px
    1280x1920                   1.91px

**The stroke never moves.** Full-body line reads heavier purely because the head
is ~230px instead of ~700px, so the same 1.9px stroke covers three times more of
it. `(thin lineart:1.3), (fine lines:1.25), (delicate lines:1.2)` changed the
picture and not the width, on a prompt with no `black lineart` tag for them to
fight — so the earlier "(thin lineart) cancelled (black lineart)" story is not
what is happening here; the tags simply do not control this.

That leaves resolution as the only working lever, and it is blocked: 1280x1920
improves the ratio to 1.53px (1536-equivalent) and **drew a second figure in both
renders that used it**, with `(solo:1.5)` already in the prompt. Matching the
portrait's ratio at full body would need a frame around 4000px tall. 1024x1536
is where it sits.

`scripts/yukari_recipe.py` is the settled recipe — `fb-b` / prompt `4c012937`,
verified byte-identical to that render's positive and negative. `--pose portrait`
switches to the 1024x1024 crop. `rabbit print` is out of the character block: with
`sticker` it drew a rabbit decal on her cheek, and `sticker` is the half of that
pair worth keeping.

## A tag that names a relationship summons the other party, and weight will not stop it

Asked for a lap-pillow invitation with one girl. `lap pillow` is the wrong tag to
begin with -- its wiki says to use `lap pillow invitation` for merely offering --
but the right one is no better here. Every attempt that carried it drew a second
Yukari lying across her lap:

    lap pillow invitation, plain negative              2 of 2 had two girls
    ... + (2girls:1.6), (multiple girls:1.6),
          (duplicate:1.55), (another person:1.5)       2 of 2 had two girls
    ... + (solo:1.7) instead of (solo:1.5)             2 of 2 had two girls

Deleting it worked on the first try: `(seiza:1.35), (hand on own thigh:1.45),
(beckoning:1.35), (looking down:1.4), (smug:1.4), (come hither:1.25)` — every tag
describing only her — came out solo on both seeds, and on all twelve renders of
the pattern sweep that followed. `pick/momiji-lap` had already recorded the same
thing about `(head on lap)` and `(hand on another's head)`: **a tag naming a
relationship names the other person, and `solo` does not outvote it.** The
generalisation is that this is about deletion, not weight — 1.7 changed nothing.

The guard block did something else, and it is the second time: mean saturation
went from ~25 to 105–163, neon backdrop and orange skin, with the headcount
unchanged. That is the same failure as the five duplicate-guard tags that wrecked
the palette earlier. **Duplicate guards in the negative are not a tool this
recipe has.**

One wrong turn worth recording: the blown colour was first blamed on
`(flat color:1.3), (simple background:1.3), (grey background:1.2)`, because
`pick/momiji-lap` had dropped them. Removing them made it worse — 163 against
138. The old note was about a warm-interior scene and did not transfer.

`--pose invite` is the settled version. `scripts/lap_invite.py` is the sweep, and
`.local/ComfyUI/output/sheet-invite-patterns.png` holds six readings of it
(smug, gentle, teasing, patting, head-tilt, full-body) at two seeds each.

## `patting` multiplies the hand, and it is the verb doing it, not the motion lines

The `pon` cell of the invitation sweep — `(patting:1.45), (motion lines:1.25)` —
drew a hand smeared across several positions with far too many fingers. Motion
lines are literally a convention for drawing one thing in several places, so they
looked like the culprit. Three arms, three seeds each:

    (patting:1.45), no motion lines    2 of 3 hands broken
    (patting:1.3),  no motion lines    2 of 3 hands broken
    no patting at all                  3 of 3 hands clean

**It is `patting`.** A verb for a repeated action gets drawn as a repeated hand,
with or without the convention beside it. Lowering the weight does not help,
which is the same shape as the relationship tags: the fix is deletion.

`--pose invite` never carried it — the gesture there is `(hand on own thigh:1.45)`
plus `(beckoning:1.35)`, which reads as the invitation without asking for motion.
Only the sweep cell was broken.

## Palette instability was three separate things, and only one of them was the prompt

"The colours are unstable" across the twelve invitation patterns turned out to be
three axes that needed separating before any of them could be fixed.

**Dress hue.** Spread 285-319 degrees over the set. It is not seed noise: within
a register it barely moves, and the whole spread is *between* registers.

    dowa  (smug, come hither)             319.3 / 319.2 / 320.3    1.1 deg
    tilt  (head tilt, smile)              317.4 / 318.0 / 320.1    2.7 deg
    kind  (smile, half-closed eyes)       313.2 / 307.0 / 300.6   12.6 deg
    tease (one eye closed, smug, tilt)    297.6 / 285.5 / 290.4   12.1 deg

The two loose ones are the two carrying an **eye-state tag**. `smile` is in a
stable register, so it is not expressiveness in general -- `(half-closed eyes)`
and `(one eye closed)` drag the hue down and scatter it. Dropping `blush` was
tried first on the theory that pink was pulling the palette; it changed the
spread from 34 to 35 degrees, which is to say nothing.

**Backdrop colour.** Five distinct values over twelve renders. Already known to
be beyond the prompt; `scripts/recolor_bg.py --color` settles it.

**Backdrop flatness.** New, and the reason recolor_bg was refusing on some
renders ("only 1.6% matched"). Some backdrops are streaked rather than flat, and
the tool is right to decline them -- widening `--tolerance` to 40 to force it
repainted 45.9% of the frame, eating the white outline and the pale socks.
`scripts/backdrop_flatness.py` scores it; under ~25 is workable.

Restricted to the two stable registers, on screened seeds, recoloured to
`#d0c0c0`: **dress hue spread 1.3 degrees, from 34.** The backdrops still carry
visible patches after recolouring, so that axis is improved and not solved.

## One tag, `seiza`, was behind the drifting art style — and the mottling, and a clone

The complaint was that the art style had changed. It had, and the measure that
shows it is stroke width, which had been fixed at exactly 1.91px on every render
this recipe made until the invitation poses:

    peace   4 of 4 at 1.91px
    coy     0 of 3          3.8 - 5.7
    yawn    0 of 3          5.5 - 8.2
    iv      6 of 12
    st      3 of 12
    fin     0 of 8          3.8 - 7.6

Two guesses were tested and both were wrong. `cowboy shot` cropping the figure at
the frame edge does break the die-cut outline — white pixels 8.2-10.6% on
`full body` against 6.2-9.5% cropped — but it does not restore the line; those
renders still measured 5.7-6.6. And `(come hither:1.25)`, suspected of dragging
the style into a softer register, came back at 1.91px on both seeds.

Swapping one element of `invite` into `peace` at a time found it:

    seiza                            6.56 / 8.47   and one seed drew two of her
    (come hither:1.25)               1.91 / 1.91
    (looking down:1.4)               1.91 / 1.91
    (hand on own thigh) + beckoning  1.91 / 1.91

**`seiza` alone.** It takes the line, the backdrop flatness and the headcount
together, which means the three "separate axes" of instability written up in the
section above were substantially one cause wearing three faces. That earlier
analysis — eye-state tags scattering the hue, seeds deciding backdrop flatness —
was measured on a set where every render carried `seiza`, so it attributed to
seeds and expressions what one pose tag was doing.

The invitation does not need it. `lap pillow invitation`, the tag whose wiki
describes seiza as the usual posture, is not in this recipe either; the gesture
is carried by `(hand on own thigh:1.45)`, `(beckoning:1.35)` and
`(looking down:1.4)`, all three of which measure clean. `yokozuwari` is the seat
with seven clean seeds under it and it costs nothing here.

## Garment length answers to the noun, not to weight — and each garment differently

The dress and the hoodie both looked too short, and the same lever did not fix
both.

**The dress** responded to its own weight. `(purple dress:1.2)` was being drawn as
a pleated skirt with a separate frill under it — a two-piece where the design is
one — and `(purple dress:1.45)` made it read as one garment and cover the
backside. Naming the wrong reading in the negative instead, `(skirt:1.35),
(pleated skirt:1.4)`, deleted the lower half of the garment outright on one seed
of two: hoodie and tights, no dress. That is the third guard tag in this recipe
to cost more than it bought.

**The hoodie did not respond to any of it**, over three seeds each:

    (black hoodie:1.35) -> 1.55           no visible change
    (cropped jacket:1.45) + (midriff)
      + (navel) in the negative           no visible change
    (oversized clothes:1.35)              destroyed the costume -- the dress went
                                          from 17-25% of the frame to 1.5-5.9%
    (wide hips) + (thick thighs) removed  no change to the hem

What moved it was **swapping the noun**:

    hoodie            dark pixels  18.4 / 13.6 / 15.6
    hooded jacket                  22.2 / 23.3 / 17.2
    hooded cardigan                23.7 / 26.1 / 17.9
    hooded coat                    20.5 / 25.1 / 16.6

`hoodie` is a pullover, `hooded jacket` a zip-up, `hooded cardigan` an
open-fronted knit — separate tags with separate cuts, and the cardigan is cut
longest. `hooded coat`, the one that sounds longest, is not. The lesson is that
these are different garments to the model, not one garment with a length dial,
and which lever works is a property of the garment.

The trade is unavoidable: as the outer layer lengthens the dress disappears
under it, 17.2% -> 11.4% -> 8.5% on one seed across hoodie, jacket, cardigan.

**Neither is settled.** The best single render (`62cd93dd`, hooded coat, seed
1117511306) did not reproduce on six further seeds — two drew a second figure,
two put foreign objects in frame. Dropping `sticker` removed the second figure on
all seven, and left the die-cut edge intact, but patterned rabbits, background
streaks and one garment turning piebald survived it. `sticker` was the duplicate
source, not the only decoration source. Three of seven are clean that way.

## Tags that name a garment's fit destroy it; tags that name a part's state do not

Asked for an oversized-hoodie silhouette — boxy body, big soft hood, hem at the
hip — off a reference photograph. Everything that names how the garment fits
failed, and failed differently each time:

    (oversized clothes:1.35)   costume replaced; dress 17-25% of frame -> 1.5-5.9%
    (oversized clothes:1.15)   same failure at a third of the excess weight,
                               stroke 1.91 -> 3.82 again
    (loose clothes:1.4)        stroke 1.91 -> 3.82 and 7.64, paint thickened;
                               it loosens the drawing, not the cloth
    (coattails:1.4)            narrow straps rather than spreading cloth, several
                               per figure on some seeds, reading as jointed legs;
                               two seeds drew a second girl. Confusable with the
                               hood's own black red-striped ears.
    (wind:1.35)                floating white shapes swarmed the figure; back
                               coverage went down, not up

What worked names a **part's state** instead: `(sleeves past wrists:1.35),
(wide sleeves:1.3)` took lower-back coverage from 54.6% to 78.5%, boxed the body
out and dropped the hem, at 1.91px. Same for length earlier — swapping the
garment noun moved the hem where every weight and guard had not, and the four
nouns rank hoodie < hooded jacket ≈ hooded coat < hooded cardigan.

So: **the noun and the parts are addressable, the fit is not.**

## The clutter has no prompt-side fix, and no cheap automatic screen either

Three of seven crouch renders carry a clone or a plush toy. Five tags were pulled
one at a time, seven seeds each, looking for the source:

    `sticker`          already out; it WAS the duplicate source earlier, and
                       removing it took clones from 2-of-7 to 0-of-7. The plushes
                       and patterns survived it.
    hood unpinned      (hood behind head) dropped, (hood down) 1.5 -> 1.25.
                       No change to colour or clutter; one seed grew a third girl.
    cardigan+sleeves   suspected of breaking the art style. They did not: the
                       original coat recipe measures 25-62 colours over the same
                       seven seeds, the same spread. The "broken" reading came
                       from comparing everything against seed 1117511306, which
                       happens to land at 29.
    `animal hood`      4-of-7 clean -> 2-of-7. Four figures on one seed, six on
                       another. It looks redundant beside (rabbit hood:1.55) and
                       is not -- it holds the figure together.
    `drawstring`       4-of-7 clean -> 2-of-7. Same collapse.

**Nothing to remove.** The full block scores better than any subset of it, which
is the opposite of the tag-budget picture that held for pose blocks.

Two automatic screens were built and both failed, so neither is in the repo:

- **Connected components of the non-backdrop mask.** Clones touch or overlap her,
  so they merge into one island. It scored a 4-of-7 set as 6-of-7 and a 2-of-7
  set as 7-of-7 — worse than useless, since it is confidently wrong.
- **Counting purple irises.** Her hair ornaments are red-purple discs in the same
  hue and saturation band. Single-figure renders scored 7 and 9 blobs.

Screening is by eye. And `scripts/flatten_palette.py`, written to handle the
other half of the drift, **cannot be used on her either**: quantising to 30
colours does drop the count from 36-57 to 17-23 at 1.91px, but it spends the
palette on backdrop, black coat and white hair and drops the small coloured
areas. Her purple fell from 9.3% of the frame to 4.0% and its saturation from
28.5 to 23.0 -- grey eyes, a near-neutral dress, no pink cuffs.

Whole-frame mean saturation reads 30.8 before and 30.3 after, so it hides this
completely. That number is what the tool was first checked against, and it is
the wrong number: measure the coloured region, not the image.

## The clones are a sampler property, not a prompt one

Every render in this repo since the recipe settled used `dpmpp_2m` / `karras`,
30 steps, cfg 5.0. That was never a variable, and the clone problem turned out
to live there.

Tested on the three seeds that reliably produced clutter, one change each:

    cfg 5.0 -> 4.0        all three still had two or more figures
    cfg 5.0 -> 6.5        one of three fixed
    30 -> 50 steps        two of three fixed
    dpmpp_2m -> euler_ancestral   **three of three single figures**

Stroke stayed 1.91px on all twelve, so the art style survives the swap.

The catch is that `euler_ancestral` re-injects noise every step, so the same seed
draws a different picture. Everything learned about which seed does what —
including `7d231c4f`, the render this whole line of work was aimed at — belongs
to `dpmpp_2m` and does not carry over. Choosing the sampler means choosing
between a known-good single render and a higher clean rate across seeds.

## Two tags that each destroy the drawing hold each other up together

The oversized-hoodie silhouette, second attempt, from `b1258b0c` reset. Stroke
width, 1.91px being correct, over two seeds:

    (oversized shirt:1.35)         3.82 / 13.69   destroyed
    (sleeves past fingers:1.4)     4.65 / 7.64    destroyed
    both, at 1.3 each              1.91 / 1.91    and lower-back coverage
                                                  54.6% -> 79.8% / 96.2%

Neither works alone. Both together, weakened, work better than anything else
tried. Same shape as the sock lengths, where removing one of two competing
length tags made the legwear worse rather than simpler.

**It also fixed two things that were being chased separately.** Over seven seeds:
colour count went from 25-62 to 20-33 — the spread that produced the "the art
style keeps drifting" complaint — and the clones and plush toys went from three
of seven to none, without changing the sampler. Five tags had been pulled one at
a time hunting the clutter, and `euler_ancestral` had been adopted to solve it;
neither was necessary.

This also retires the rule written here earlier, that garment **nouns** and
**part states** pass while **fit** words fail. `oversized shirt` is a noun,
`sleeves past fingers` is a part state, and both destroy the drawing on their
own. That rule was generalised from the two tags that happened to work.

## Substitute, never subtract — the blocks are balanced, not budgeted

Two separate attempts to simplify broke the drawing, and both were made on the
belief that removing tags is the safe direction. It is not.

**The garment pair.** `(oversized shirt:1.3), (sleeves past fingers:1.3)` at
1.15 each: the coat stopped covering her and the back came bare. Below 1.3 the
pair stops holding the garment on at all.

**The pose block.** Dropping it from eight tags to six — pulling the overhead
angle and the smug face to make the pose read as incidental rather than
presented — took stroke width from 1.91px to 3.82-5.73 and the colour count from
17-24 to 40-45. Worse, deleting only `(smug:1.2)` and leaving the count at seven
did the same: stroke held but colours went to 50, with background streaks and an
eyeball-shaped object in frame.

So the pose block is not a budget with room in it. It is a balance, like the two
sock lengths and like the oversized pair, and a hole in it is as damaging as an
addition. **Replacement keeps the slot filled; deletion does not.**

## Making the view incidental: two substitutions, and one that backfired

The brief was "she sat down and it happened to look big", not "she is showing it
off". The shape was already right; what read as staged was the face and the
camera. Both fixed by substitution, since deletion breaks this recipe.

    (smug:1.2)      -> (expressionless:1.2)    colours 21-24, held
                       (light smile:1.2)       colours 42-48, rejected
                       (looking back:1.2)      colours 38-44, rejected
    (searching:1.2) -> (picking up:1.3)        colours 14-25, six of seven seeds
                                               now look at the floor, not the lens

`searching` had been in the block since the pose was built and was never legible
in a single render — it held a slot and did nothing. `picking up` is defined as
"picking something up that has dropped on the floor", and being a definite action
it gets drawn. Same lesson as the dropped glasses: the vague version renders as
nothing.

**`(from above:1.2)` must stay.** It was read as the last piece of staging — an
observer who chose to look down — and replaced with a dropped object to buy both
a floor prop and a less deliberate angle. The object appeared (coins, keys;
`glasses` landed on her face instead of the floor) but the colour count went from
22/20 to 36/48, 27/39, 23/48, and losing the overhead angle put the camera level
with her backside on all six. The tag was doing a second job nobody had credited
it with: keeping the hips out of the centre of the frame.

## The hands were hidden, not malformed — and a rejected tag was only rejected locally

**Hands.** `(sleeves past fingers:1.3)` covers them completely and they render as
shapeless lumps. Two ways at it, five seeds each:

    weight the guards already in the negative --
      (bad hands:1.4), (extra fingers:1.4)      0 of 5 fixed; hands still buried
    (sleeves past fingers) -> (sleeves past wrists)
                                                4 of 5 have drawn fingers,
                                                and colours drop 26-50 -> 16-22

Forbidding the failure did nothing. Removing what hid the hands did. Note this
is the same substitution that once left her back bare — in a block without
`(coin:1.3)` in the pose. It behaves differently here, so a tag's past failure
is not a verdict on the tag.

That cuts both ways: `light smile` and `looking back` were rejected earlier at
42-48 and 38-44 colours. Re-measured in the current block they come in at 16-23.
**The measurement was of the block, not of the tag.**

**Expression.** `(smug:1.2)` was swapped for `(expressionless:1.2)` to answer
"she sat down and it happened to look big, not she is showing it off". That read
"not showing off" as "no expression", which removed the character with it. The
staging is carried by the action and the angle — `picking up` instead of
`searching`, and `(from above:1.2)` keeping the hips off centre — so the face
never had to be flattened. Smug is back and the pose still reads as incidental.

## Open, for next time

- **Nothing raises the bangs alone yet**, and the tag side looks exhausted: seven
  lineart variants plus `parted bangs` + raised strands all lifted both regions
  together or neither. If the ratio matters, it probably has to come from
  masking the bangs and treating them separately, not from another tag.
- **Split the two passes' negatives.** `colorize_lineart.py` inherits the lineart
  pass's `(shading:1.3)`, which cancels the `(cel shading:1.45)` it asks for.
- Cut a mask that follows the hair instead of the rectangle in
  `scripts/bangs_region.py`, now that the rectangle has shown the mechanism works.
- Two things found while looking for a way past the global dials and not yet
  tried: a lineart-trained ControlNet for this base family
  (`Eugeoter/noob-sdxl-controlnet-lineart_anime`, and an Illustrious-XL lineart
  anime one on Civitai) to replace canny, which is being used to hold a drawing
  it was not trained on; and `ComfyUI-Detail-Daemon`, which adjusts sigmas during
  sampling — a third axis that is neither prompt nor ControlNet. It wants a
  custom sampler node, so `colorize_lineart.py`'s plain `KSampler` would need
  rebuilding, and SDXL is said to want `detail_amount` under 0.25.
- `cel shading` and `soft shading, smooth shading` sit in the same positive in
  `hs-cel`, which should be the reason its line density stalled at 15.1%. The
  sweep that would have measured the cost of that contradiction (`cl-*`, with
  `cl-soft` as the control) was cancelled after five of eight renders.
- The two-pass pipeline has only been run on one face. Whether the lineart pass
  honours the face block (`db-real`, `db-tall`, `mature female`, `tsurime`) as
  well as a flat-colour render does is unknown.
- `re4lity` and `mozudoll` have still never been run with their triggers.
- `standing` no longer shreds the costume: `--pose-text "full body"` did that,
  with no working trace involved. Whether it also survives a real skeleton is
  untested — every `--pose-text` result so far had an empty one.
- **Redo the duplicate-figure comparison.** The one in the openpose section was
  measured against black frames and proves nothing. It needs the same seed with
  `ref-pose-bootoff` (the only reference that traces properly) against no trace.
- **Find references that actually trace.** Four of five candidates came back
  under 0.3% skeleton coverage. Without a supply of usable references, swapping
  the reference to change the pose does not work in practice, whatever the
  mechanism can do. An OpenPose editor node, or depth instead of a skeleton, are
  the two ways around the detector.
- `bootoff` goes dark.
- `ref-pose-headrest` and `ref-eye3-purple-gradient` cannot drive a trace at all
  — they are cropped above the legs. `ref-pose-bootoff` traces best but is shot
  from below, which runs into `(from below:1.2)` and `(upskirt:1.4)` in the
  negative.
- Face contour candidates (`cf-A`..`cf-D`) were generated but never reviewed —
  the current default carries `(round face:1.2), soft jawline, small chin`.
- Yukari's `reaching` pose is implemented and unverified.
- `gen_variants.py` (ollama) inherits the full recipe now, but its scene
  vocabulary fights the flat background rule. It needs a pose/expression
  vocabulary instead of a setting one before it is useful.
- Background colour is not worth chasing in the prompt — three attempts landed on
  yellow, cream and pale blue. Generate a flat field and set the exact value with
  `scripts/recolor_bg.py --color "#C1C3C2"`.

## Removing baked-in objects: redraw and composite, never the negative (2026-08-16)

`sm2-crouch-111222333` (f0a4b5c7) carried a pale mirror-image duplicate of her
along the left edge and a rabbit plush at bottom-left. Everything else about the
render was approved, so the job was removal, not regeneration.

- **The negative cannot do this.** Re-rendering the same seed with
  `stuffed animal, stuffed toy, reflection` appended — plain or at 1.3 — rebuilt
  the whole composition both times, and the plain version summoned a *bigger*
  plush (a full rabbit face filling the bottom-left). Naming an object in the
  negative hands the sampler the concept; on this seed that outweighed the
  suppression. This closes the question for seed-baked clutter: it answers to
  redrawing, not to prompt adjustment.
- **`VAEEncodeForInpaint` needs `denoise: 1.0`.** It blanks the latent under the
  mask, so 0.55/0.70/0.85 all returned the masked column as a flat grey
  rectangle. There is nothing under the noise to denoise toward.
- Four seeds of the denoise-1.0 redraw (mask: the left column, 22.8% of frame)
  all removed both objects. 777011 reconnected her arm down to a drawn hand and
  won; 777012/777013 ballooned the skirt into the empty space; 777010 invented a
  cushion. The redraw is a lottery over what fills the vacancy — plan on a few
  seeds.
- **Pasting the redraw back is its own problem**, solved in
  `scripts/inpaint_composite.py` (docstring has the full failure list): the
  redraw's backdrop lands ~30 levels darker; the original backdrop is warm
  beige toward left/bottom and neutral at top, so no constant shift matches
  both edges (and `cv2.seamlessClone` washed the figure's colours instead).
  Laplace-extend the original's outside-the-mask backdrop across the region,
  correct only backdrop pixels toward it, erase the seam line the sampler draws
  along the mask boundary, feather outward only. Final seam gap 0.2 levels.
- Result: `fin-crouch-111222333-noghost.png`, byte-identical to the original
  outside the feather ring.

Current reading of the settled render (user, on f0a4b5c7): expression, hoodie
volume, dress length and the dress pulled taut over the hips are all right; the
thighs being fully covered is the one regret, and the visible hand runs long.
Both would need the drawing to change, not the pixels — noted here so the next
pose iteration starts from them.

### Rebuild beats erase, and the model re-grows what you carve out (2026-08-16)

The bottom of `fin-crouch-111222333-noghost` still carried warm-taupe rounded
masses reading as a second body. Three rounds settled how to handle that class
of defect:

- **Erasing just the masses fails**: a denoise-1.0 redraw of only their pixels
  refills the cavity with new masses, four seeds out of four. The surrounding
  context (hips above, legs beside) demands volume there and the sampler
  supplies it. A background-only prompt for the cavity was queued as the next
  test and cancelled when the user called the better move: reconstruct.
- **Reconstructing the whole zone works**: mask everything below the hem —
  masses, legs, feet, plus the hand the user had flagged as long — and let the
  full recipe redraw it. Six seeds: two incoherent, one drew a body pillow, one
  hid the legs under drapery, one lost the hand to a wisteria bunch, and
  777043 drew a proper squat (thigh mass, pale-purple over-knee legs, and the
  hand re-drawn shorter, picking up a small purple object that suits the
  pose's `picking up`). Keeping small fragments of approved elements just
  outside the mask (sock top, one purple foot) anchors the redraw to them.
- **The re-drawn thigh still landed warm-taupe** (R−B ≈ +12 vs the approved
  pantyhose's +3, shadows stopping at 111 vs 90). What made it read as "mystery
  body" was the colour, not the shape: `(p − mean) × 1.18 + pantyhose_grey` on
  the blob's pixels settled it as her thigh. Cheaper and deterministic — try
  recolouring a wrong-coloured but well-shaped mass before re-rolling it.

Result: `fin-crouch-111222333-rebuild.png` (composite of iprb-777043 through
`inpaint_composite.py`, then the recolour).

### Hands: refine in place at double resolution, never blank-and-redraw (2026-08-16)

The rebuilt render's hand was mushy and its held object unreadable. Fixed at
`fin-crouch-111222333-glasses.png`; the route matters:

- **Crop and upscale first.** The hand occupies ~120px of a 1024×1536 canvas,
  and the model draws hands at that scale as blobs. Crop 512² around the hand,
  Lanczos to 1024², fix it there, downscale back, paste through
  `inpaint_composite.py` (which needed no changes to work in the crop domain).
- **`VAEEncodeForInpaint` deleted the hand six times out of six.** A blanked
  region bordered by sleeve and backdrop, with `simple background` in the
  positive and `sleeves past wrists` implying a hidden hand, resolves to "no
  hand, just backdrop" every time. The blank encoder is for regions whose
  content should be *invented*; a hand that exists but is badly drawn needs
  `VAEEncode` + `SetLatentNoiseMask`, which keeps the old drawing under the
  noise so the model cleans it instead of choosing whether it exists.
- **Denoise ladder at 0.45/0.55/0.65 × 2 seeds:** 0.45 stays faithful and
  stays sloppy; 0.65 redraws cleanly and turned the ambiguous purple object
  into unmistakable folded glasses. 0.65-777061 won: purple frame, both
  lenses, black temple tips, fingers pinching the temple.
- Tags verified before use: `holding_eyewear` does not exist (0 posts) — the
  real ones are `holding removed eyewear` (11k), `unworn eyewear` (21k),
  `purple-framed eyewear` (2k). The eyewear read closes the loop on the
  `hunt`/`crouch` pose family: she squatted to search, and now holds what she
  found.

### Finishing an unfinished bottom half: name the pose the drawing shows (2026-08-16)

"絵として完成していない" — the rebuilt lower half was soft, the thigh a
featureless bean-bag, the leg arrangement unreadable. What finished it,
`fin-crouch-111222333-complete.png`:

- **A 1.5× in-place refine (`SetLatentNoiseMask`) is a ladder of intent.**
  0.40/0.55 sharpened lines but could not re-shape the mass; 0.70 re-read it as
  hips over folded calves with both soles visible; 0.80 started inventing
  garments (frilled bloomers). Structure changes live around 0.70, style-only
  polish below 0.55.
- **The pose word was wrong and it mattered.** The crop showed soles-up feet
  tucked under — that is `kneeling`, not `squatting`. The 0.70 pass prompted
  with `(kneeling:1.3), knees, soles` is the one that produced readable
  anatomy. If a region refuses to resolve, check whether the prompt is naming
  a different pose than the pixels show.
- Refine passes invent small decorations at mask borders (gold heart
  embroidery on the cuff, twice). Budget a revert-from-previous-version patch
  as part of the workflow, not as a surprise.
- The leftover anchor foot from the rebuild became a third foot once the new
  legs existed. Anchors kept outside one mask can contradict the next mask's
  result — re-count limbs after every restructure. Removed by backdrop
  extension (`laplace_extend`), with the asymmetric band threshold again: a
  symmetric one let the white outline contaminate the fill with haze, and
  mid-grey shadow remnants needed their own darker-than-backdrop-by-12 term.

### "除去して完成": the figure can simply end at the hem (2026-08-16)

The reconstruction row (kneeling legs, refined at 0.70) was still judged
incomplete as a picture. The user's correction reframed the whole task:
completion meant the problem region should not exist, not that it should be
redrawn better. `fin-crouch-111222333-removed.png`:

- Everything below the hem was removed — legs, feet, the rebuilt thigh mass —
  keeping only the hanging arm with the picked-up glasses and the hair-tail.
  The dress hem lace is the figure's bottom edge. This is an ordinary
  illustration convention and it reads as finished where every redraw of the
  legs did not.
- The style's white outline does not exist along edges that used to be
  interior. Low-denoise refine passes will NOT draw it — they return haze or
  invent scratches (four attempts). What worked: draw the final contour as an
  explicit polyline, fill below it with Laplace-extended backdrop, and paint
  an 8px white band along it. Deterministic, one shot.
- After many rounds of regional fills the backdrop was a patchwork spanning
  28 grey levels, so every fill boundary showed as a faint rectangle.
  `recolor_bg.py`'s single-seed flood cannot cross that (its documented
  failure mode). A multi-reference candidate mask + border-connected
  components + one flat target colour flattened all of it at once. Guards
  that mattered: pale skin is within 10 levels of the beige patches, so
  hue (R−G ≈ 25 on skin vs ≤ 13 on every backdrop patch) is the reliable
  separator, applied per-pixel — per-component means get dragged over the
  threshold by the very fades being removed.
- Near-miss: a purple-grey shape beside the cuff resisted every haze filter
  and turned out to be the tip of her sidelock hair — real content with its
  own outline. When a "remnant" refuses to match haze thresholds, look at
  what it is before forcing it: the thresholds were saying it isn't haze.

### The cut edge was the failure, not the cut (2026-08-16)

The hem-terminated composition came back as "全く出来てない". A labeled
region map posted to the channel settled the scope question — remove
everything below the hem, A through E — so the rejection was about execution:
the bare thigh ended in a straight soft cut with a synthesized white arc
floating under it. An amputation plane, not a silhouette.

The fix that worked (`fin-crouch-111222333-clean.png`): mask just the cut
zone and refine at 0.70 with dress/lace vocabulary. The model would not
extend the lace trim leftward (four seeds, none drew lace), but it did
something as good: it rounded the thigh into a closed convex silhouette
tucking toward the hem. A body part may end at the frame of another garment
or curve to a close — what it cannot do is end on a straight line in open
backdrop.

Asking beat guessing: three consecutive misreadings of the removal scope
("削る" vs "再構築" vs "除去") were resolved by one annotated screenshot
with lettered boxes. When the same instruction has been re-interpreted three
times, the next round belongs to a labeled picture, not another attempt.

### Refining the accepted cut: frill border, tucked hair, squashed hand (2026-08-16)

The removal composition was accepted ("OK") with two notes: the cut regions
were rough, and the hand ran long. `fin-crouch-111222333-final.png`:

- The hazy wedge where the underskirt met the fill refined (0.6, 2×) into a
  scalloped frill border with its own white outline — the model closes a
  garment against backdrop happily when given `white frills, frilled dress`;
  it is body parts it refuses to terminate (previous note).
- The smudged hair-tail below the cuff resolved, in all four seeds, to "the
  strand ends behind the arm". A thin trailing strand that has gone muddy is
  better tucked than sharpened.
- "手が長い" was fixed geometrically: the hand+glasses block squashed to 0.84
  vertical, anchored at the wrist, vacated strip filled with backdrop. One
  deterministic step; no redraw lottery, no risk to the good glasses.
- Ended with the multi-reference backdrop flatten to erase the refine pass's
  faint mask-edge rectangles. That flatten is now the standard last step
  after any regional surgery.

### Context size decides whether a hand can be inpainted at all (2026-08-16)

`fin-yukari-square.png`. Three changes on the accepted removal base, chosen by
the user off a posted crop sheet: square crop, shorter right arm, left hand
restored.

- **The crop was the last missing piece.** The figure ended mid-canvas with the
  lower third empty, which reads as an amputation however clean the edges are.
  Cropping so the arm exits the frame edge converts the same pixels into an
  ordinary composition. Try the crop before trying to draw more.
- **A limb shortens by squash, not redraw** (second use): forearm block scaled
  0.85 vertically about the elbow, vacated strip filled with backdrop.
- **The same hand inpaint failed at a 300×260 crop and succeeded at full
  1024×1024.** Tight crops returned red scribbles, a pole, and dark smears —
  the model could see only fabric and had no idea a hand belonged there. Fed
  the whole square with the recipe's own positive plus `hand on own hip`, all
  four seeds drew a plausible hand from the ribbed cuff. Rule: for a region
  whose content is implied by body layout rather than by its immediate
  neighbours, inpaint at full frame. The 2× crop trick (previous note) is for
  regions whose content is already there and merely too small to be drawn well.
- The flat cut on the white petticoat closed with `lace trim, frills,
  petticoat` at 0.70 — a scalloped border with its own dark line. Third
  confirmation that garments terminate against backdrop happily.

### The `sip` pose, and what each of the eight slots is buying (2026-08-16)

Built from a reference photo by substituting into `crouch`'s eight slots, one
variable at a time. `fin-yukari-sip.png` (fcA, seed 3409564303). Findings:

- **Eight slots really is the ceiling, so every addition is a trade.** The
  reference needed four things `crouch` did not have — side view, knees tucked,
  a drink held to the mouth, a forward lean — and each one had to be paid for
  out of an existing slot. Mapping them onto `from behind` / `looking down` /
  `picking up` / `from above` at the same weights worked first try.
- **`drinking` is what lifts a vessel to the mouth.** Dropped in favour of
  `leaning forward`, on the reasoning that `holding can` plus the face would
  carry it, the can moved to her feet on all four renders. `holding X` places
  the object in the hand; it says nothing about where the hand goes.
- **A mug costs two slots.** `coffee mug` alone put a mug in frame but not
  reliably in her hands; `holding cup` alone drew a paper cup or a can. Both
  together draw a china mug, and on some seeds steam rising off it — the whole
  cosy read, for no extra tag.
- **Slots that can be spared, measured:** `full body` (the square canvas frames
  her anyway), `knees to chest` (`squatting` holds the tuck alone — though
  keeping it curls her tighter), and `smug` where the pose's mood contradicts
  it. `solo`, `squatting`, `from side` and `drinking` all carry unique work.
- Same seed-sensitivity as always: 3409564303 puts the cup at her mouth in every
  block tried; 111222333 put it on the ground in three of them.
- A side-on squat wants a square canvas. At 1024×1536 the identical block drew
  her small in a tall empty frame.

### `sip` seed sweep: 5 clean of 8 (2026-08-16)

The settled `sip` block over eight seeds, `sipf-sip-*`. Clean: 1886970040,
20250816, 31415926 (draws steam off the mug), 3409564303, 555666777. That is a
better clutter rate than `crouch` managed (4 of 7 on its worst sweep) and is
the same 60-70% this recipe has always run at under `dpmpp_2m`.

The three failures are each a known family, and all three are object/figure
duplication rather than anything about the drawing:

  1117511306   two mugs, one in each hand
  2557902837   a second girl, full size, beside her
  737373737    a chibi clone bottom-right

`solo` is at 1.5 here and did not prevent either figure. Consistent with the
older finding that duplicate guards in the negative are not a tool this recipe
has -- re-rolling the seed is the fix, and at 5-in-8 it is a cheap one.

Worth noting for `holding cup` + `coffee mug`: naming a vessel twice is what
makes it a mug, and it is presumably also what makes 1117511306 draw two of
them. The trade has been worth it so far.

### An unweighted tag is an absent tag (2026-08-17)

Her hair clips were missing from a dozen straight `nape` renders. The cause was
not that `hair ornament` was the wrong tag; it was in CHARACTER the whole time,
carrying no weight, in a prompt where everything around it sits at 1.3 or
above. At that ratio a bare tag is indistinguishable from one that was never
written. `(hair ornament:1.4)` brought them back on the first try.

`drawstring` was in exactly the same state and behaved exactly the same way --
weighted to 1.4, the coat's cord appears, pink bead and all.

Worth auditing the rest of CHARACTER on this basis rather than adding tags for
things that are already named.

**But the same fix does not generalise to every missing detail.** The dress
fastens at the back of the neck in black straps, and `(halterneck:1.45)` plus
`(black straps:1.35)` draws them correctly -- crossing, and knotted in a bow at
the nape. Measured on `sip`, the same pair pulls the coat off her shoulders and
bares her back; at 1.15/1.1 it still bares one shoulder. Naming a halter is
read as naming a garment that leaves the shoulders out, and the coat gets out
of its way. So it is spliced in for `nape` only, in `positive`.

`criss-cross halter` is worse than nothing. Naming the X spends the straps'
budget on it and the bow never gets drawn; `halterneck` alone draws both.

### The `nape` pose, and the turnaround sheet (2026-08-17)

She is sitting; the camera is standing behind her, looking down.

**Framing was the whole difficulty, and moving the camera closer is not the
answer.** `(upper body:1.35)` loses to `from behind` every time. The obvious
fix -- `close-up` and `head and shoulders`, which `portrait` uses -- draws a
character reference sheet instead: two figures side by side, front view and
back view, the back one in a strapless dress. A composition guard in the
negative (`character sheet`, `multiple views`, `reference sheet`, `turnaround`)
does not stop it; the control run with the guard still drew the sheet. Neither
tag is usable in a shot already looking at her from behind.

**Seating her solved it.** She is below the camera, so the nape is what faces
it, and `(upper body:1.3)` is enough. `from above` tilted a standing figure
diagonally and behaves against a seated one, which gives the angle somewhere to
land.

**`(nape of neck:1.45)` does not come down.** At 1.25 it does not merely soften
-- the pose collapses and she turns to face the camera.

### The bare back: seventeen attempts, and what none of them taught (2026-08-17)

`nape` draws a bare back and it could not be talked out of it. Recorded so the
next person does not repeat the list.

Prompt side, twelve: `(bare back)` in the negative at 1.3 / 1.4 / 1.45, plus
`backless dress` and `backless`; `halterneck` lowered to 1.2 and propped with
`sleeveless dress`; `halterneck` swapped for `neck ribbon` + `black bow`;
`black straps` dropped as well; `off shoulder` lowered to 1.15 and then removed
entirely; `back focus` removed; `camisole` (drew a separate white garment);
`racerback` (no effect); `purple dress` raised to 1.6 (marginal).

Second pass, three: `HIRES_DENOISE` at 0.45, and both upscale routes. The 1024
pass does cover more than the print does, which is what suggested the second
pass was the culprit -- it is not, the coverage is only relatively better
because there is less of everything at that size.

Inpaint, two, and the first was my own error: I handed the region the full
`positive(pose="nape")`, which contains `(nape of neck:1.45)`, `(from behind)`
and `(halterneck)`. I was asking for the defect inside the region I wanted
covered. A region-local prompt did better -- fabric began to appear at denoise
0.90 -- but only on one side.

Also: `VAEEncodeForInpaint` is the wrong node for this. It blanks the latent, so
at denoise 1.0 the model invented black straps from nothing and left the mask
rectangle visible. `VAEEncode` + `SetLatentNoiseMask` keeps the body underneath
as context and leaves no seam. Use the former to remove, the latter to change.

Three separate confident diagnoses of mine -- the fastening, `back focus`, the
second pass -- were each disproved by the next experiment. When a defect
survives twelve prompt levers, stop diagnosing and change tools.

### The thighs were a pose problem, and the fix was squash then crop (2026-08-17)

Five attempts read "太ももの長さに違和感" as a claim about length and adjusted
it: `thick thighs` to 1.15, `(long legs:1.4)` and `(bad proportions:1.4)` in
the negative, `(petite:1.35)`, `from above` eased from 1.45 to 1.3. None moved
anything, because the length was never asserted -- `sitting on floor` extends
the legs, and a leg extended away from a camera looking down occupies the frame
lengthwise whatever the tags claim. `yokozuwari` folds them and the proportions
come right immediately.

When a tag that plainly describes the defect does nothing at any weight, the
defect is implied by something else and the fix is upstream of the description.

A second complaint on the finished print -- the femur long relative to where
the buttocks sit -- was geometric, third use of squash-not-redraw. The warp is
a function of x alone: identity left of the hip, compressed 0.82 between hip
and knee, translated by the same amount beyond it. Legs, coat and frills move
as one piece, so no seam can open inside the region.

**Backfilling the vacated strip is wrong; crop it instead.** Filling with
backdrop sliced the leg flat and cut its white outline -- the amputation read.
Cropping the same 63px puts the leg back through the frame edge where it
started, and the matching crop off the top is all backdrop, so the result stays
square at 1985. `fin-yukari-nape.png`.

### Image-space upscaling clears the banding latent upscaling leaves (2026-08-17)

`bicubic` fixed the stairstepping `bislerp` drew, but flat areas at 2048 --
tights, the black coat -- still carried visible banding, worst in compositions
with large flat fields and long diagonal boundaries. Decoding the first pass,
resampling the picture with `lanczos`, and encoding it back removes it: the
resampler has eight times the detail to interpolate between. Paired with
denoise 0.45 the surfaces come out clean and the linework does not split.

Costs a VAE round trip, which is cheap against another 30 steps.

### The settled chair block was never written down as a pose (2026-08-17)

`yukari_recipe.py` carried a `chair` that went one clean seed in four, while the
chair block that had been settled three seeds deep lived only in `--pose-text`
strings inside `pick/yk-chair-151`, `-111` and `-555`. Two different poses under
one word, and the tested one was the one not in the file.

The two are not variants of each other. What was in the file was `peace` moved
off the floor onto a chair, keeping the double-V hands; the picks are a
front-facing gaming chair with the legs crossed and the hands free. Nothing was
ever kept from the first, so it is gone and `peace` remains the floor version.

Porting it needed one slot. Every `POSES` entry leads with `(solo:1.5)`, which
the `--pose-text` form had no reason to carry, and the block must stay at nine.
`looking at viewer` is what came out, because `FACE` already supplies it — the
same reason `lap` omits it. No weight was retuned and nothing was re-rendered.

**A measurement that lives only in a tag message is not in the recipe.** Three
seeds of evidence sat next to a pose that had one, and the gap survived every
later session because the word `chair` looked occupied. Worth a sweep of the
other `pick/*` tags for the same shape.

### Rendering it: twelve renders, four blocks, one clean seed (2026-08-17)

Three seeds -- the picks' own 151515151, 111222333, 555666777 -- through four
variants of the block. Windows worker, hassaku-il-v22, 30 steps, cfg 5.0,
dpmpp_2m karras, identical to the picks.

| variant | canvas | framing tag | result |
|---------|--------|-------------|--------|
| A | 1024x1536 | `(full body:1.4)` | layers collapsed on 151, no crossing on 111 |
| B | 1024x1536 | `full body` | layers back on 151 |
| C | 1024x1024 | none | closest to `sip`, front view lost on 2 of 3 |
| D | 1024x1024 | `full body` | **kept.** 111 clean, 151 three-quarter, 555 lost |

**Two picks disagreed about one substitution and the pessimistic one was
right.** render-notes recommended `full body` -> `(full body:1.4)` off three
seeds; `pick/yk-chair-gradient` recorded that exact substitution, alone,
collapsing the layered legwear into a single gradient stocking and noted it was
never reproduced. It reproduces. Porting picked the favourable note without
weighing the unfavourable one, and A is the cost of that.

**Flatness was a framing property, not a style one.** Next to `sip` the chair
renders had no highlights and no modelling, with the same STYLE and LINE blocks
in both. The docstring already holds the explanation: stroke is a constant
1.91px at every canvas here, so a figure drawn small in a tall frame carries a
line heavy relative to her head and has no pixels left to shade in. `sip` goes
square and drops `full body` for exactly this. Doing the same to `chair` brought
the shading back -- the black cardigan models, the hair takes highlights, and
the thighhigh-over-pantyhose boundary reads without being hunted for.

**The square is paid for out of the framing tags.** `(front view:1.35), facing
viewer` held on one seed of three; the other two swung to three-quarter or came
in on the legs. `full body` does not anchor them -- tried present and absent,
same spread -- which is consistent with it being a distance tag and not a
direction one. What has not been tried is easing the camera pair upward, or a
distance tag that is not `full body`.

Kept: `ykchairD-chair-111222333`. Front view, chair whole down to the base and
armrests, legs crossed, both legwear layers with the purple welt, rabbit hood
ears up, hands on the armrests. Cropped at the shins, which the square costs.

Nothing above changes a weight. `(crossed legs:1.2)` was never re-tested and
did not need to be -- it drew two legs on all twelve.

### Refining a chair render: the route decides the surface, the denoise decides the invention (2026-08-17)

`ykchairB-chair-555666777` (prompt `4c146593`) taken to 1368x2048 three ways.
The first pass was replayed verbatim out of `/history` rather than rebuilt from
the recipe, so no tag-order difference could move the picture underneath the
comparison -- `scripts/refine_from_history.py`.

| route | denoise | result |
|-------|---------|--------|
| `LatentUpscale` bicubic | 0.60 | most detail, and beads and cords on the dress that the base does not have |
| `ImageScale` lanczos | 0.60 | detail back, plus gloss on the thighhighs and hair |
| **`ImageScale` lanczos** | **0.45** | **kept.** flats clean, lineart unsplit, nothing invented |

Two variables, and running all three separates them: **the route decides the
surface and the denoise decides how much gets invented.** At a matched 0.60 the
image-space route has cleaner flat fields and adds less; at a matched route,
0.60 buys detail and pays in gloss. The nape session's pairing -- image-space
lanczos with 0.45 -- reproduces on a completely different composition, so it is
a property of the second pass and not of that one picture.

The recipe's `--hires` still only offers the latent route. Adding the other one
is a real change and is not made here.

**A second pass does not fix the first pass, and this base needed it to.** All
three refines agree that the thigh above the stocking is bare skin and that the
grey under the dress is a separate shorts-like garment -- so
`(thighhighs over pantyhose:1.55)` never landed in `4c146593`. At 1024 the
region was ambiguous enough to read either way; 2048 resolves it, and resolves
it against the recipe. The layering has to be won in the first pass or not at
all. `ykchair-chair-555666777`, variant A on the same seed, has the purple welt
band and is the better base if the layers are what is wanted.

### `boss`: the smirk, grown up, off the render that failed as `chair` (2026-08-17)

`ykchairD-chair-555666777` (prompt `c1629d37`) is the square render that lost the
front view and sank her into the seat. That is a failure for `chair` and a
starting point for something else, so it became its own pose rather than another
attempt at fixing that seed.

**The framing tags paid for the smirk.** `(front view:1.35), facing viewer` were
being bought and not collected on this seed -- it never held them across four
variants -- so they came out and `(smug:1.4), (half-closed eyes:1.3)` went in.
That pair is not new: `lounge`, `peace` and `invite` all carry it at those
weights. Nine tags in, nine tags out, and the legwear survived, which is the
test that matters for this block.

**Adult is two substitutions, spliced per-pose.** Measured separately from the
smirk, one variant each:

| | change | result |
|---|--------|--------|
| E1 | pose block only | smirk lands, face still reads young |
| E2 | E1 + `tareme`->`tsurime`, `petite`->`mature female` | **kept.** eyes sharpen and lid, proportions lengthen |

Both are one-for-one swaps in slots that were already occupied, which is the
only kind of change this prompt has room for. `tsurime` earns its slot twice:
drooping eyes are most of what reads young here, and upturned ones carry the
smirk as well. The rest of `BODY` -- wide hips, thick thighs, narrow waist --
was already adult proportion and was being held down by `petite` alone.

Spliced in `positive()` beside `nape`'s, not changed globally: every other pose
was settled against the young face.

Nothing asked for the hand at her chin on 555666777. It came with the smirk.

Kept: `rf-boss555`, E2 on 555666777 refined to 2048x2048 through image-space
lanczos at 0.45 -- the pairing measured on the previous render, used here
without re-testing it. The legwear layering that `4c146593` never had is
unambiguous at print size: welt band, grey pantyhose, pale thighhighs over.

Open: the backdrop splits into a grey block and white on 555666777, in the first
pass, so the second does not touch it. `recolor_bg.py` is the existing answer to
a backdrop this recipe does not control.

### Dialling the smirk down: the weight is the lever, the tag is not (2026-08-17)

`boss` at `(smug:1.4)` was gloating rather than self-assured. Three ways down
from it, two seeds each, everything else held identical by overriding the one
`POSES` entry in memory rather than editing between runs.

| | change from E2 | result |
|---|---------------|--------|
| F1 | `(smug:1.15)` | **kept.** composed, chin still up, arc intact |
| F2 | `smug` -> `(light smile:1.3)` | similar face, and **one foot loses its stocking** |
| F3 | `(smug:1.15)` + `(half-closed eyes:1.15)` | indistinguishable from F1 |

**Lowering the weight kept what the tag was structurally doing.** `sip` records
`smug` holding her chin up so head, spine and hip land on one arc -- it is
posture as much as expression, which is why easing it reads as composure while
swapping it out would have cost the bearing. F1 keeps the lift and loses only
the gloat. The hand at her chin, which came free at 1.4, does not survive the
drop; it belonged to the stronger reading.

**F2 is a counter-example to "substituting a word costs nothing."** That rule
was measured on the chair noun and it does not generalise: swapping `smug` for
`light smile` at the same tag count reached roughly the same face and took a
stocking off her foot and changed the hood on the way. Same count is not the
same thing as same cost -- what a tag holds elsewhere in the picture goes with
it.

**`half-closed eyes` was not carrying the swagger.** F3 eased it as well and
changed nothing visible on either seed, so it stays at 1.3. Worth knowing which
of two tags in a pair is inert before spending a round on it.

Kept: `rf-boss-calm`, F1 on 555666777 at 2048x2048 through the image-space
route. Layering unambiguous, expression composed.

### The eye tag had no job left, so it went (2026-08-17)

`(tsurime:1.3)` came in as half of the adult splice and read too sharp. Three
ways off it, two seeds each, edited into the built graph's positive text so
every other token stayed byte-identical.

| | change | result |
|---|--------|--------|
| G1 | `(tsurime:1.1)` | softer, still upturned |
| G2 | eye tag deleted | soft, and **a second empty gaming chair in the backdrop** |
| G3 | back to `(tareme:1.3)` | **kept.** sharpness gone, still adult |

**It was put in to do two jobs and by now neither was its own.** The reasoning
was that drooping eyes are most of what reads young and that upturned ones
would carry the smirk as well, so one swap would serve both asks. G3 reverts
the eyes alone and the adult read does not move, so `petite` -> `mature female`
was carrying that by itself; and the smirk had already gone to `(smug:1.15)`
two rounds earlier, which retired the other job. What was left was a tag with
nothing to do and a sharpness nobody asked for.

**Deleting a tag is not the neutral setting between its two values.** G2 looks
like it should sit between `tareme` and `tsurime` and instead it opened a hole:
the backdrop grew a second empty chair, which is the empty-frame failure this
pose's square canvas is already prone to. An occupied slot is doing work even
when the work is only holding the slot.

Kept: `rf-boss-soft`, G3 on 555666777 at 2048x2048 through the image-space
route. `(tsurime:1.1)` is recorded in the splice comment as the middle, if a
trace of the sharpness is ever wanted back.

### Feet at head height on a chair: twelve levers, and the seed was the tool (2026-08-17)

`boss` was built on 555666777, where her feet come up level with her head. No
chair supports that. Four families of fix, twelve renders, two seeds each:

| | attempt | result |
|---|--------|--------|
| H1-H3 | `feet on floor` -- bare and at 1.35, from two donor slots | nothing moved |
| J0 | `crossed legs` deleted outright | **knees still up** |
| J1-J2 | `(sitting on chair:1.6)` against `(crossed legs:1.05)` | nothing moved |
| K1-K2 | `(feet up:1.45), (legs up:1.4), (knees up:1.35)` in the negative, alone and with the positive | nothing moved |

**J0 is the one that settles it.** Deleting the crossing left the knees exactly
where they were, so the crossing was never lifting them -- which rules out the
obvious culprit and, with it, every fix aimed at the crossing. The raised legs
are the composition, decided in the first pass, and the composition on this seed
is the same one that made `chair` fail on it: camera in, low, on the legs.

**Why `feet on floor` was never going to work.** It asks for both feet, and
`crossed legs` puts one of them in the air -- a tag arguing with the pose,
which this recipe has measured as inert more than once. The negative form is
the version that does not contradict anything, and it did nothing either.

`1886970040` and `2557902837` seat her properly on the identical block. The
nape rule holds: when a defect survives this many prompt levers, stop
diagnosing and change tools. Here the tool was the seed, and one sweep of the
remaining `SWEEP_SEEDS` found two.

**Ground contact is not reachable on this canvas at all**, independently of the
seed. The square crops at the shins, so the floor is never in frame; the most
the pose can do is send the feet downward out of it. A planted foot needs the
floor visible, which needs the camera back, which is the tall canvas this pose
gave up in order to get its shading. That is a real trade and not a bug.

Kept: `rf-boss-1886` (1886970040, upright, hands on the armrests, both lower
legs going down) and `rf-boss-seated` (2557902837, reclined, and the only one of
the two with the legwear layering unambiguous). Neither shows a foot on a floor.

### The adult body was wearing a different dress (2026-08-17)

`boss` kept drawing a long pale button-front shirt dress instead of the purple
bodice, on most seeds. It reads as a seed lottery and it is not one.

**Reverting `(mature female:1.35)` to `(petite:1.2)` brought the purple bodice
straight back**, on the first seed tried and with nothing else changed. The
adult body tag was recruiting `(oversized shirt:1.3)` out of CHARACTER -- two
tags that agree with each other and outvote the dress.

Reverting is not available: the adult read is the point of the pose. So the
competing garment goes instead, spliced per-pose like the rest of `boss`:

    character = CHARACTER.replace("(oversized shirt:1.3), ", "")

Nine seeds under the fix and the bodice is back on almost all of them.
`sleeves past wrists` stays -- CHARACTER measured that one as what boxes the
coat out, and it was never part of this.

**Two fixes that looked equivalent were not.** Adding `(off shoulder:1.3)`
reaches a similar silhouette and takes the rabbit hood off her head, which the
module docstring rules out in as many words: deleting the hood costs more
identity than it buys. Same apparent result, and one of them is a documented
no-go.

**Not every seed recovers.** 757575757 -- chosen for its leg geometry, the lower
leg only slightly bent with the foot going down -- keeps the button-front
version through both the `oversized shirt` removal and the off-shoulder route.
121212121 has the same leg read and the correct dress, and is what `rf-boss-121`
was made from.

Contact sheets are the right tool for this and were underused until now: nine
tiles labelled with their prompt ids answered in one look what nine separate
reads would have cost. `scripts/contact_sheet.py --glob 'bossfix-*'`.

### The two legwear layers are a contrast, and weight cannot make both appear (2026-08-17)

On 757575757 the legs came out as pale thighhighs with no tights under them.
Four weights, one variable each, on the off-shoulder base:

| | change | result |
|---|--------|--------|
| P1 | `(grey pantyhose:1.45)` -> 1.65 | **whole leg goes grey**, thighhighs gone |
| Q1 | `(very pale purple thighhighs:1.5)` -> 1.65 | whole leg stays pale, no tights |
| Q2 | `(thighhighs over pantyhose:1.55)` -> 1.7 | whole leg goes grey |
| Q3 | `(frills:0.85)` -> 1.25 | dress only: frilled collar, ties and beads return |

**Whichever side is heavier takes the whole leg.** The layering is a contrast
between two garments and the prompt has no way to ask for a boundary -- it can
only ask for more of one thing. Even `thighhighs over pantyhose`, which names
the relation rather than either garment, behaves as a third vote for the grey
instead of drawing the join. Where the welt band has appeared, it appeared on
its own.

So the choice on a seed like this is pale thighhighs or grey tights, not both.
`rf-boss-q4` takes the tights, since that was the half that was missing.

**`(frills:0.85)` was below 1 in a prompt where everything else is 1.3+**, which
this recipe has twice measured as equivalent to absent -- `hair ornament` and
`drawstring` had the same disease. At 1.25 the frilled collar, the ribbon ties
and the beaded cords all come back, and it costs nothing visible. Third time
the same fix has worked; worth a sweep of the remaining sub-1.0 weights.

Kept: `rf-boss-q4` -- 757575757, off shoulder at 1.3, `(thighhighs over
pantyhose:1.7)`, `(frills:1.25)`, refined at 2048 through the image-space route.

### `opaque pantyhose` was flattening the knit (2026-08-17)

The vertical ribbing on the thighhighs, and the purple welt band with it, had
gone from the recent `boss` renders. Both are present on `bossfix-boss-343434343`
and absent from everything built on 757575757.

**The tag was describing the opposite surface.** `(opaque pantyhose:1.3)` names
a smooth unbroken face -- it is in LEGWEAR to stop the tights rendering sheer --
and it takes the thighhighs' texture down with it. Swapped one-for-one for
`(ribbed legwear:1.35)` the lines come straight back, and the welt band returns
unasked alongside them.

| | slot | result |
|---|------|--------|
| T1 | `(ribbed legwear:1.35)` | **kept.** knit lines the length of the leg, welt band back |
| T2 | `(vertical-striped legwear:1.35)` | lines, but they read as a printed stripe and the welt is lost |
| T3 | `off shoulder` removed instead | no change -- the shoulders were never involved |

T3 is the one that matters for the diagnosis. The obvious suspect was
`off shoulder`, since the flattening appeared in the same renders it did;
removing it changed nothing, which left the legwear block as the only place to
look.

**Three tags in this recipe have now been found describing the opposite of what
was wanted, and all three were doing it quietly** -- `sitting on floor`
extending the legs, `feet on floor` contradicting the crossing, and now
`opaque pantyhose` flattening the knit. None of them are wrong tags. They are
right tags for a picture nobody asked for.

`boss` now splices three things out of the shared blocks: `oversized shirt`
(the dress), `(frills:0.85)` -> 1.25 (the collar and ties), and
`(opaque pantyhose:1.3)` -> `(ribbed legwear:1.35)` (the knit). Plus
`(off shoulder:1.3)`, which costs the rabbit hood and is a deliberate exception
for this pose -- drop that one line to get the hood back.

Kept: `rf-boss-rib`, 757575757 at 2048x2048.

### `mature female` was also paying for a chest (2026-08-17)

Yukari is not built that way, and `boss` had drifted there. Same cause as the
dress: `(mature female:1.35)` brings an adult chest with it. One tag, two costs,
and both of them found upstream of the thing that changed rather than at it.

`(large breasts:1.25)` was already in NEGATIVE and simply being outvoted. Three
ways down, one variable each:

| | change | result |
|---|--------|--------|
| U1 | negative `(large breasts:1.25)` -> 1.5 | **kept.** modest without being flat, nothing else moves |
| U2 | `(mature female:1.35)` -> 1.15 | works, and gives back the adult read this pose exists for |
| U3 | `(small breasts:1.35)` added to the positive | works, grows the block by a tag, lands flatter than asked |

**Raise the guard that is there rather than adding a neighbour.** This recipe
has wrecked its own palette twice by stacking duplicate guards -- five of them
once, four another time, mean saturation 25 -> 105-163 -- so a weight on an
existing negative is the cheap move and a fourth guard is the expensive one.
U1 changes no tag count on either side.

That `mature female` has now cost the dress and the chest, and been the right
answer both times when left alone, is worth remembering: it is the tag this pose
is built on and the tag most of its defects trace back to. Fix downstream of it,
not by weakening it.

Kept: `rf-boss-bust`, 757575757 at 2048x2048 -- and this is the render that has
everything asked for over the session: the seated geometry, the lower leg only
slightly bent, the ribbed thighhighs with their welt band, the frilled collar
and ribbon ties, the composed rather than gloating smirk, and the adult read
without the chest that was coming with it.

### Correction: the ribbed-legwear splice was wrong, and one seed is why (2026-08-17)

The entry above claims `(opaque pantyhose:1.3)` flattens the knit. On 757575757
it does, and swapping it for `(ribbed legwear:1.35)` restored the lines and the
welt band there. Shipped on that evidence, it then removed the tights.

**`opaque pantyhose` is one of only three tags holding the grey side up** --
`(grey pantyhose:1.45)`, `pantyhose`, and it. Against three pale tags the sides
were even; taking it out let the pale side win the whole leg, which is the same
winner-takes-all behaviour measured two entries above. The fix for one defect
was the cause of another, and the connection was already written down.

Swept over nine seeds with the original block restored, the ribbing AND both
layers appear together on most of them -- `202020202`, `2557902837`,
`343434343`, `454545454`, `535353535`, `979797979`. Nothing needed changing.
757575757 is simply a seed that does not draw them, and three sessions were
spent making the recipe worse to make that one seed better.

**One seed is enough to find a lever and never enough to keep one.** Every
finding in this file that has held up was measured across at least three; this
one was measured across one and shipped. The splice is reverted and the comment
left in `positive()` so the same trade is not made again.

Kept: `rf-boss-final`, 979797979 at 2048x2048 -- pale thighhighs, purple welt,
grey above it, the frilled collar and ties, the modest chest, and the seated
geometry. Its knit lines are fainter than `343434343`'s, which has the strongest
ribbing of the nine and a more reclined pose.

### The rib is part of the costume, and it had to be added rather than swapped

Treated as a required element rather than a texture preference, and measured
across three seeds before shipping this time.

| | change | 979797979 | 343434343 | 2557902837 |
|---|--------|-----------|-----------|------------|
| earlier | `opaque pantyhose` -> `ribbed legwear` | rib, **no tights** | rib, no tights | rib, no tights |
| W1 | `white thighhighs` -> `ribbed legwear` | rib, **legs go mid-purple** | same | same |
| W2 | `ribbed legwear` **added** | **all four** | all four | all four |

The two substitutions each took something out of the balance the legwear block
is holding. `opaque pantyhose` is one of three tags on the grey side and
`white thighhighs` is one of three on the pale side; removing either hands the
other side something. Adding leaves both intact, and on three seeds nothing was
pushed out of the block to pay for it.

**This breaks the file's own rule that adding costs the picture, and the rule is
still right in general** -- it was measured on pose blocks, where the tag count
is what the composition is spending. The legwear block is not competing for the
same budget in the same way, or has more slack than nine tags of pose. Worth
knowing which blocks tolerate growth; this is the first one recorded that does.

Standing suspicion: the legwear is documented as the first thing this pose
spends. If a later change starts losing thighhighs, this extra tag is where to
look first.

Kept: `rf-boss-rib2`, 979797979 at 2048x2048. Ribbed pale thighhighs, purple
welt, grey above it, frilled collar and ties, modest chest, seated with the
lower leg only slightly bent.

### The halter straps, from the official design (2026-08-17)

Her dress is a halter: the straps cross at the chest, pass over the shoulders
and tie in a bow behind the neck. It is in the official character sheet and the
recipe had never drawn it outside `nape`, which splices `(halterneck:1.45),
(black straps:1.35)` for the same garment seen from behind.

`nape`'s comment says that pair costs every other pose its coat, which is why it
is spliced there and not global. **`boss` is the one pose that can afford it
anyway** -- the coat is already off her shoulders by its own splice, so the
documented cost is one this pose has already paid. Worth looking for: a
constraint recorded as global may only bind the poses that have not already
broken it.

Three forms, three seeds each:

| | tags | result |
|---|------|--------|
| Y1 | `halterneck` + `black straps` (nape's pair) | straps drawn, cross less definite |
| **Y2** | **`criss-cross halter` alone** | **kept.** clear cross, composition unmoved |
| Y3 | all three | clearest straps, and the camera comes in off the body |

Y3 is the tag-count lesson again in miniature: three tags draw the thing best
and cost the framing, one tag draws it well enough and costs nothing. The single
tag also names the part the reference is specific about -- the cross -- rather
than the garment category.

Kept: `rf-boss-straps`, 979797979 at 2048x2048. The tights read weaker on this
render than on the one before it; the straps landed, the grey above the welt did
not, and that trade has not been chased.

### No buttons on the dress, and one guard is the whole fix (2026-08-17)

The official design has a plain ribbed front -- ribbon, beads, frills, no
buttons -- and the renders had been drawing a button placket down the centre.
Nothing in the prompt asks for one; it arrives from the cardigan, or from the
garment being read as a shirt dress. Nothing to substitute, so a guard.

One, two and four guards, three seeds each. **All three remove the buttons**,
which makes this the cheapest of the three to choose:

| | negative | result |
|---|----------|--------|
| **Z1** | `(buttons:1.4)` | **kept.** buttons gone, nothing else moves |
| Z2 | + `(buttoned shirt:1.35)` | buttons gone, **rabbit silhouette on the chair back** |
| Z3 | + `(shirt:1.4), (placket:1.35)` | buttons gone, same intruder |

Third time stacking guards has cost something here, and the first time the cost
was an intruder rather than the palette -- the same backdrop rabbit this pose's
ancestors fought through a dozen renders, arriving with the stack rather than
with any one tag. Worth recording that the punishment is not always the same
shape; it was saturation twice and composition this time.

Kept: `rf-boss-nobtn`, 979797979 at 2048x2048.

### A cheap pass deletes; it does not add (2026-08-17)

`rf-boss-rib2` (prompt `88b01d73`) was the render whose shading was accepted, and
it predates three corrections: no buttons, the halter straps, the smaller chest.
Rather than re-render and lose the shading, a third pass was chained onto it --
its own two passes replayed verbatim from `/history`, the prompt re-encoded from
the current recipe, image-space lanczos at 2048.

| denoise | buttons removed | straps drawn | chest | shading |
|---------|-----------------|--------------|-------|---------|
| 0.35 | **yes** | barely a suggestion | partly down | intact |
| 0.50 | yes | faint | down | intact |
| **0.60** | **yes** | **drawn properly** | **down** | **intact** |

**Removing something the prompt now forbids is nearly free. Drawing something
the base does not contain costs real denoise.** 0.35 was enough to take a button
placket off a garment and nowhere near enough to put straps onto a bare chest,
and the gap between those two is the whole finding. A guard reaches down into a
cheap pass; a positive tag needs the pass to be expensive enough to redraw the
region.

0.60 was the level at which the straps landed, and the shading survived it --
which is not obvious, since 0.60 on a *first* pass is the denoise that was
measured inventing dress details two sessions ago. A late pass over a settled
picture tolerates more denoise than an early one over a rough one.

3072 was tried and abandoned: not wanted, and slow enough that the run was
interrupted. 2048 is the print size.

`scripts/refine_from_history.py --chain --pose boss --denoise 0.60` reproduces
it. Kept: `th-2048-d60`.

### Open the eyes: the tag is not gradual, and the guard is not portable (2026-08-17)

`(half-closed eyes:1.3)` was half of the smirk pair. Once `smug` came down to
1.15 the lids were the only thing still reading as attitude rather than
composure, so they came out. Three forms, chained onto `88b01d73` at 0.60:

| | change | result |
|---|--------|--------|
| Ea | `(half-closed eyes:1.1)` | still lidded |
| Eb | tag removed | more open |
| **Ec** | removed + `(half-closed eyes:1.4), (closed eyes:1.4)` in the negative | **open, iris visible** |

Ea confirms what F3 measured and reframes it. Easing the weight does nothing
because **the tag is not gradual** -- present or absent is the whole range it
has. Two sessions apart, the same null result meant something different once the
question changed from "how much" to "at all".

**And the guard does not port back.** Ec is safe chained onto a settled picture
and unsafe from scratch: run from the recipe it stacks with the buttons guard
and 979797979 grows a second chair with a rabbit face on it -- the same intruder,
the fourth time stacking has summoned something. So the recipe carries only the
removal, and the guard pair is documented for the chain.

That split follows from the pass-depth finding: a late pass only gets to delete,
and a guard is a deletion. A first pass gets to rearrange the composition around
the same guard, and it does.

Kept: `eyeEc`, 2048x2048, chained onto `88b01d73`.

### Corrections go on in one pass, not in a stack (2026-08-17)

Reducing the chest further was first tried by chaining a fourth pass onto
`eyeEc`, which already had three. It worked and **the palette went with it**:
the gaming chair drifted from purple-and-black to magenta and the linework
lightened, on all three tag variants alike. The drift belongs to the pass, not
to what was asked of it.

Going back to `88b01d73` and putting the eye guard and the stronger chest tags
into **one** pass gives the same corrections with the chair still purple.

**Each pass takes a little colour and line with it, so the count is the cost.**
Corrections discovered separately should be re-applied together from the last
approved render, not stacked in the order they were found.

Also fixed, and it nearly cost this comparison: `chain_pass` allocated node ids
20-23 as constants. Chaining onto a graph that was itself chained overwrote the
previous pass instead of extending it -- the second chain would have silently
redrawn the same picture. Ids are now allocated above whatever the graph already
uses. Fixed ids worked exactly once, which is the number of times a fixed id
works.

Kept: `one-d60` -- `88b01d73` plus a single pass at 0.60 carrying
`(small breasts:1.6)`, `(large breasts:1.8)` and the eye guard.

### Thinning the line: it is the denoise, and going bigger does nothing (2026-08-17)

`scripts/stroke_width.py` exists now. This file has been quoting stroke figures
since the beginning -- 1.91px, 3.82, "the line does not respond to tags" -- with
no tool behind any of them, so none could be re-checked. Median dark-run length,
horizontal and vertical, runs over `--max-run` dropped as fills.

The first thing it says is that the refine pass was already thinning the line
and nobody knew:

| render | canvas | median | per 1000px |
|--------|--------|--------|------------|
| first pass | 1024 | 3.00px | 2.93 |
| refined at 0.60 | 2048 | 4.00px | 1.95 |
| **refined at 0.65** | 2048 | **3.00px** | **1.46** |
| refined at 0.70 | 2048 | 3.00px | 1.46 |
| refined at 0.60, 3072 | 3072 | 6.00px | 1.95 |
| the same, downscaled to 2048 | 2048 | 4.00px | 1.95 |

A straight upscale would have taken 3px to 6px; it lands at 4, so the second
pass redraws contours finer than it inherits them.

**Going bigger does nothing, and that is a limit on an existing rule.** The
docstring says line width is roughly constant in pixels and resolution is the
reliable way to thin it. True of first passes, and false here: 3072 draws 6px
where 2048 draws 4, the same 1.95 normalised, so the stroke scales with the
canvas and the downscale gives it all back. **Denoise is the lever on a refine
pass; resolution is the lever on a first pass.**

**0.65 is the whole gain.** 0.70 measures identically and costs content -- the
chest ribbon slid to the waist and a seam appeared across the dress that the
design does not have. Same line, worse picture, which is the invention curve
already recorded for denoise arriving on top of the line curve.

Kept: `ln-d65`.

### Opening the eyes further: say it, do not ban it harder (2026-08-17)

One pass from `88b01d73` at 0.65 again, three ways:

| | change | result |
|---|--------|--------|
| Ga | guard to 1.65 + `(narrowed eyes:1.4)` | open, and **the backdrop goes mottled** |
| **Gb** | `(large eyes:1.3)` -> 1.55, guard unchanged | **kept.** open, backdrop clean |
| Gc | both | open, backdrop mostly clean |

**"Guards are cheap in a late pass" needs a correction: cheap, not free.** That
was written two entries ago on a chain that carried one guard pair. Carrying
three in the same pass mottles the backdrop -- so stacking is punished at every
pass depth, and what a late pass buys is a discount rather than an exemption.
Fifth distinct cost recorded for stacking: saturation, saturation, an intruder,
a second chair, and now backdrop texture.

Gb is also the cheaper move in the other sense. `(large eyes:1.3)` was sitting
in FACE unraised the whole time, so opening the eyes needed a weight on a tag
already present rather than a new ban on the tag already banned. The positive
was never asked before the negative was pushed twice.

Stroke held at 1.46 per 1000px, so the finer line survives the change.

Kept: `eyes2Gb`.

### Correction: the median was too coarse and the line barely moved (2026-08-17)

The two entries above are wrong where they quote line width, and the tool built
to stop exactly this kind of error is what produced them.

`stroke_width.py` reported the **median** dark-run length. On these renders that
is an integer landing on 3 or 4 with nothing between, so "0.65 thins the line by
25%" was the metric stepping down one whole count, and "0.70 measures
identically" was two different distributions sharing a median. Re-measured with
the mean, which moves continuously:

| render | per 1000px, median-based (wrong) | mean-based |
|--------|---------------------------------|------------|
| first pass, 1024 | 2.93 | 3.818 |
| refined 0.60 | 1.95 | 2.248 |
| refined 0.65 | 1.46 | **2.083** |
| refined 0.70 | 1.46 | 2.252 |
| 0.65 + `(large eyes:1.55)` | 1.95 | 2.272 |
| 0.65 + three guards | 1.95 | 2.575 |

What survives: **the refine pass is the whole effect**, 3.818 to 2.248, a 41%
thinner line relative to the figure. What does not: **denoise is worth about 7%
between 0.60 and 0.65 and nothing at all at 0.70.** There is no meaningful line
lever left in the second pass; the one that mattered was already switched on.

Two smaller things fall out of the honest numbers. Raising `(large eyes:1.55)`
gives back the 7%, so the eye and the line are competing for the same redraw.
And the three-guard stack thickens the line to 2.575 -- above even the 0.60
baseline -- which is a cost of stacking that the coarse metric had hidden
entirely.

**A tool built to check an assertion is only as good as its statistic**, and a
median over small integers is not a measurement, it is a vote between two
values. The mean is now the normalised figure and the median is kept beside it
as a reminder.

### `prone`: face down on the floor, and the first landscape canvas (2026-08-17)

「うつ伏せで寝転んでるゆかりさん」. `lying` and `on stomach` are one unit -- the
second qualifies the first and is not used alone -- so the posture costs two of
the eight slots before anything else is asked for. `chin rest` props her on her
elbows and `feet up` lifts the shins; without that pair the tags describe a body
face down on the ground rather than someone lying there on purpose. `smug` and
`half-closed eyes` are the pair `lounge`, `peace`, `invite` and `boss` all carry,
at the weights they carry it at.

**The canvas is the whole finding.** A body on the floor is longer than it is
tall and every canvas in this recipe was square or portrait. One seed,
555666777, three canvases:

| canvas | result | stroke /1000px |
|--------|--------|----------------|
| 1024x1024 | cropped at the frame edges, die-cut outline broken | 3.922 |
| 1024x1536 | drawn diagonally, hips raised toward the top of frame | 1.887 |
| **1536x1024** | **whole figure, outline intact** | **1.941** |

The square's 3.92 is not a style break, it is the figure being drawn large in a
frame too small for her: the line is heavy against her rather than against the
canvas, which is exactly what `stroke/1000px` was built to separate and here
fails to, because the crop changed the subject's scale as well.

The portrait is the one to remember. Nothing in the prompt asked for a rear
view -- `from above` is at 1.35, below `nape`'s 1.45 -- and the tall frame
produced one anyway by giving the hips the top half of the picture. The
composition this project has thrown work away over can arrive from the canvas
alone.

This does not violate "1024x1536 is the ceiling for full body". That ceiling is
a pixel count: 1536x1024 is the same 1.57M pixels turned on its side, not the
2.46M of 1280x1920 that drew a second figure. Six seeds here, none did.

**Six of six, first try.** `--pose prone --seeds 6`: one girl in all six, face
down with the chin on the hands and the feet up in all six, no clothing failure
and no bare skin. `crouch` needed eleven seeds to earn that sentence and `hunt`
never did. Stroke per 1000px: 1.72, 1.75, 1.94, 1.99, 2.18, 2.20 -- straddling
the recipe's 1.91. Median is 2.00 on every one of the six and says nothing,
which is the correction from the previous session doing its job.

737373737 is the loosest and is the one to look at before trusting the block
further: the hem rides over the hip and the grey tights carry the whole lower
half of the frame. Covered, and closer to the framing the portrait canvas drew
by itself than any other seed. 555666777, 111222333 and 2557902837 are clean.

Not measured here, and worth knowing before this pose is pushed: nothing has
been tried against the tights band, the hood ears (flattened under her on most
seeds, since she is lying on them), or the feet, which are the part of the
figure furthest from the camera and the part that comes back least resolved.

**The second pass has nothing to do here, and takes something.** Three prints
off 555666777, all against the 1536x1024 first pass at 1.941 per 1000px:

| print | stretch | denoise | per 1000px | outline |
|-------|---------|---------|------------|---------|
| 2048x1368 | 1.33x | 0.60 | 1.274 | doubled into a sketch |
| 2048x1368 | 1.33x | 0.45 | 1.454 | scribbled, flat colour lost |
| 3072x2048 | 2.00x | 0.60 | 0.982 | soft halo, no die-cut edge |

The refine pass is a line-thinner -- `boss` measured it taking 3.818 to 2.248,
which was the whole point of running it there. But that render's first pass was
heavy *because the square drew the figure small*, and this one is not: the
landscape canvas already lands on the recipe's 1.91 in one pass. Applied to a
line that is already right, the same pass walks it off the target in the only
direction it knows, and pays for the trip with the die-cut white outline, which
is drawn as an edge in the first pass and as a stroke in the second.

Kept: `ykprone-prone-555666777` -- the first pass, 1536x1024, no refine. The
first render in this repo that is finished at sweep size, and it is the canvas
that made it so rather than anything about the pose.

`--hires` is still the right tool for a square or portrait pose. It is the wrong
tool for this one, and the test for which is the first-pass stroke, not the
print size that was wanted.

**Retracted the same day: the pass I measured off is the one that was wanted.**
The picks came back as the two 2048/0.60 prints for the line -- `50a25cf1`
(111222333) and `c94fb07a` (555666777) -- and `188c2b27` (1886970040, first
pass) for the pose. So the settled render is the combination: `--pose prone
--seed 1886970040 --hires 2048`.

Nothing measured above is wrong. The stroke does go 1.941 -> 1.274, the die-cut
edge is drawn as a cut in the first pass and as a stroke in the second, and 0.45
and 3072 really are worse than 2048/0.60. What was wrong is the sentence built
on top of them: *"the canvas already lands on 1.91, so the second pass has
nothing to give."* 1.91 is a number `fb-b` happened to measure, and this file
has quietly promoted it to a target it is not. A thinner, looser line was
available and preferred, and no measurement here could have said so.

The same mistake as the median, one session apart, in the opposite direction: an
honest number, and then a judgement smuggled in beside it. Measure the line;
don't rule on it.

Kept: `ykprone2k-prone-1886970040`, 1536x1024 refined to 2048x1368 at 0.60.

Rendered: `ykprone2k-prone-1886970040`, stroke 2.177 -> 1.532 per 1000px. That
seed's first pass is the heavy end of the six, so the pass lands it nearer 1.91
than 555666777's did -- which is a coincidence of where that seed started and
not a reason to prefer it.

Two things the refine moved on this seed that the 1024-side prints did not show:
the raised legs come back lavender along their whole length rather than pale
socks over a grey band, so the layering reads as one stocking at print size; and
the hem sits above the hip, which the larger canvas makes plainer than the sweep
did. Both are properties of this seed being the one with the most rear in frame.
The layering is the one worth chasing if this pose gets another session --
`4c146593` lost it the same way and the lesson there was that it has to be won
in the first pass.

### The near hand on the prone print: 0.65 is where the fingers become countable (2026-08-17)

「指の数が怪しい」. On `ykprone2k-prone-1886970040` the hand under her chin drew
five or six tapering shapes with no knuckles and no clear boundaries -- the
count is not wrong so much as undecided. The far hand, half behind the sleeve,
reads as a fist and was left alone.

The route is the one settled on 2026-08-16 and it needed no changes: crop 512
square around the hand at print resolution, Lanczos to 1024 so the model is
drawing a hand at a size it can draw, `queue_refine.py --mask` (VAEEncode +
SetLatentNoiseMask, never the blank encoder), paste back.

The ladder came out the same way it did then, which is the useful part:

| denoise | result |
|---------|--------|
| 0.55 | cleaner, better separated, still four-or-five shapes |
| **0.65** | **a closed fist, three finger backs, unambiguous** |

0.55 polishes what is there and 0.65 re-decides what it is -- "structure changes
live around 0.70, style-only polish below 0.55" holds on a second, unrelated
hand. It costs the gesture a little: the loosely curled hand becomes a fist. The
prompt still says `chin rest` and the picture still shows one.

`inpaint_composite.py` was NOT used, and the reason is worth writing down: it is
built around a masked region that contains backdrop, and extends the surrounding
backdrop across the mask by Laplace diffusion. This mask holds skin, sleeve and
collar and no backdrop at all, so the correction it applies has nothing to act
on. What a `SetLatentNoiseMask` refine actually leaves behind is the VAE round
trip's tone nudge, which measured [1, 2, 1] per channel on the ring outside the
mask -- a constant, subtracted as one, then a 3px feather. Outside the crop the
output is byte-identical to the print.

Result: `ykprone2k-prone-1886970040-handfix.png`. The crop-and-paste is
`.local/hand_fix.py`, ad hoc to this render; the reusable half of it is the four
lines of procedure above.

### 「スパッツになってる」: a wrong reading that no tag was making (2026-08-17)

The grey over her rear on the prone print reads as bike shorts: a grey shape
with a hem edge, sitting over pale legs. It is in the first pass, so the refine
neither caused it nor can be blamed for it.

**Why the lexical route was never going to work.** Eight attempts on 1886970040,
all of them leaving the read exactly where it was:

| attempt | result |
|---------|--------|
| `(bike shorts:1.4)` in the negative | unchanged |
| + `(shorts:1.35)` | unchanged |
| `pantyhose` bare -> `(pantyhose:1.4)` | unchanged |
| `(very pale purple thighhighs:1.5)` -> 1.15 | unchanged |
| masked hip refine, 0.50 | unchanged |
| masked hip refine, 0.65 | unchanged |
| drop `(opaque pantyhose:1.3)` | composition re-rolled |
| drop it + ease the socks | composition re-rolled |

Nothing in the prompt says shorts. There is no tag to outvote, no weight to
lower, and a guard needs something to guard against. **The read is geometric:**
face down with the rear toward the camera, the pale thighhighs cover the leg to
the hip, so the only grey left in frame is the buttock, and a grey patch bounded
by a hem is a garment. The layering is drawn correctly and reads wrongly.

**The refine could not fix it either, and the contrast with the hand is the
lesson.** The same masked route at the same denoise re-decided that render's
hand an hour earlier. The hand was a badly drawn version of the right thing; the
hip is a well drawn version of the wrong thing. A refine cleans a region up. It
does not reinterpret it.

**What works: one layer, not two.** Easing the grey pair to 0.6 stops it
competing -- the dress hem covers the rear and the leg is a single pale garment
with a welt band. The mirror arm works too: easing the three pale tags gives
grey pantyhose the whole leg, which also reads correctly and costs the pale
palette this recipe spent a session choosing. The pale arm shipped.

**Weight, not deletion, when a picked composition has to survive.** Four weight
changes on this seed kept the framing; both deletions re-rolled it. That is the
rule this file has been missing while it substituted nouns and blamed the noun.

Kept: `v7pale2k-prone-1886970040`, spliced into `positive()` and verified to
reproduce from `--pose prone --seed 1886970040 --hires 2048` -- the prompt the
recipe now builds is byte-identical to the one that drew it. The hand needed no
fix on this render; the fist came out clean unaided.

### 「タイツになってないな…スパッツだ…」: the boundary was the garment (2026-08-17)

Easing the grey pair did not fix the spats read, it recoloured it. The rear came
back as a smooth plum shape with the frilled hem above it and the welt band
below -- the same fitted short garment, now in the dress's colour. The previous
entry's fix was wrong in the way a fix can be wrong while every measurement
under it is right: it removed the grey, and the grey was never the subject.

**Two layers cannot be drawn from behind without one of them being shorts.**
Whichever layer covers the buttock has to end somewhere, and a fitted shape that
ends in a hem, above legs of a different colour, is a pair of bike shorts. That
is what the eye is reading: not the colour, not the tag, the boundary. The pale
thighhighs and the grey pantyhose were both drawn exactly as asked.

So the fix is one garment, and the pantyhose is the one to keep -- it is the
layer that reaches the hip:

| arm | rear | legs | verdict |
|-----|------|------|---------|
| grey kept, socks eased | dress hem | warm brown-grey | reads as tights, wrong colour |
| `pale purple pantyhose`, socks eased | dress hem | pale lavender | **kept** |
| + `(white pantyhose:1.2)` alongside | -- | -- | composition re-rolled |

Two things fall out of that table. The colour has to travel with the surviving
garment: leaving `grey pantyhose` in place and raising `(lavender tint:1.5)`
gets tights that land warm brown-grey, against a negative that bans brown
legwear. And **a swap inside an existing span keeps the composition where an
addition beside it does not** -- the colour word changed freely, the extra tag
re-rolled the picture. That sharpens the rule from the previous entry: it is not
that weights are safe and edits are not, it is that the token count is part of
what a fixed seed is holding on to.

The cost is the layering this recipe spent a whole session measuring -- pale
thighhighs over grey tights, welt band, the lot. From behind it was never
visible, and every other pose keeps it. Spliced per-pose in `positive()`.

Kept: `ykprone-tights-prone-1886970040`, 2048x1368, stroke 1.242 per 1000px.
Legs, hips and feet are one pale garment with no hem in it. Both hands came out
as clean fists unaided, so the hand fix did not have to be redone.

### 「タイツのうえからニーハイ」: the model will not draw two layers at knee length (2026-08-17)

Stated precisely by the user, which is what made it testable: **tights run from
the hips to the toes, knee-highs run from the knee to the toes, and the
knee-highs go on over the tights.** Two layers, but with the boundary at the
knee -- which is exactly why it is not the spats geometry that sank the last two
attempts.

**Everything the prompt can do was tried, on 1886970040, and none of it works.**

| attempt | thigh | socks |
|---------|-------|-------|
| `(white kneehighs:1.45), (kneehighs:1.25)` | bare | correct, at the knee |
| tights to 1.6/1.45 | tights | gone |
| tights to 1.7/1.5 | tights | gone |
| `(kneehighs over pantyhose:1.4)` | bare | at the knee |
| `(socks over pantyhose:1.5)` | bare | at the knee |
| `(pantyhose under kneehighs:1.45)` | bare | at the knee |
| `(bare legs:1.5), (bare thighs:1.45)` negative | bare | at the knee |
| black socks, pale tights (max contrast) | bare | crisp, at the knee |
| masked refine of the calves, 0.55 / 0.65 | -- | no boundary drawn |

"Bare" is measured, not judged: with the socks strong enough to be drawn, the
buttock comes back at 253,240,231 against the cheek's 254,240,230. It is skin.

So the model has exactly one two-layer construction, `thighhighs over pantyhose`
-- a real tag -- and its length is in its name. `kneehighs` is a tag about a leg
with nothing else on it, and the two do not compose. The sock side and the
tights side take turns; they never share a leg.

**What does work is finishing the thigh outside the sampler.** The first pass
draws the socks correctly and draws the thigh as a well-shaped, well-shaded,
wrong garment -- which is the case this repo already settled once, on a
warm-taupe thigh: recolour a wrong-coloured but well-shaped mass before
re-rolling it. Two new tools, and the whole pose is now three commands:

    uv run scripts/yukari_recipe.py --pose prone --seed 1886970040 --hires 2048

    uv run scripts/recolor_skin.py out/ykprone-prone-1886970040_00001_.png \
        --box 1400 380 2048 1290 --from-color '#fdf0e7' --tolerance 16 \
        --color '#877f80' --out grey.png --mask-out grey-mask.png

    # crop 1280,450 768 -> 1024, queue_refine --mask at 0.45, then
    uv run scripts/paste_refined.py grey.png thigh-refined.png \
        --box 1280 450 768 --mask grey-mask.png --out final.png

`#877f80` is not a colour anyone picked: it is the grey this recipe's own
`(grey pantyhose:1.45)` measured at on the render two entries up, so the tights
keep the palette the session before last chose. Tolerance 16 is the widest that
catches no sock -- skin and sock are 4/1/22 apart per channel, so 22 is where
the socks start being repainted too.

`scripts/paste_refined.py` is the general form of the paste both fixes needed,
and its docstring carries the distinction from `inpaint_composite.py`: that one
extends BACKDROP across a mask, and a mask holding only figure has none.

Kept: `ykprone-knee-final.png`, 2048x1368, stroke 1.317 per 1000px. Dress hem,
grey tights over hip and thigh, white knee-highs from the knee over them, feet
covered. Byte-identical to the print outside the pasted box.

Open, and worth knowing before this is trusted on another seed: the recolour box
and the refine crop are hand-typed coordinates. They are correct for this render
and mean nothing on another one. Nothing here is automatic yet -- what is
persisted is the first pass, the two tools, and this procedure.

### The lower body was the shared BODY block, seen from the one angle it was never tested at (2026-08-17)

「めちゃ下半身太ってしまった…」. `BODY` carries `(wide hips:1.3)` and
`(thick thighs:1.35)` for every pose in this file, and every one of those poses
was judged from the front or the side, where the two tags read as proportion.
`prone` looks straight at the rear, foreshortened, so the same two tags land on
the largest object in the frame and read as bulk. Nothing about the pose block
or the legwear was wrong; a global constant met a new camera.

Eased on the same seed, weight-only so the framing survives:

| | wide hips | thick thighs | other | result |
|---|-----------|--------------|-------|--------|
| baseline | 1.3 | 1.35 | -- | the complaint |
| **s1** | **1.0** | **1.05** | -- | **kept.** shape without weight |
| s2 | 0.8 | 0.85 | `petite` 1.35 | slimmer, and leans on `petite` |
| s3 | 0.6 | 0.6 | `petite` 1.4, waist 1.4 | slimmest, and **a rabbit appeared in the backdrop** |

s3 is the useful failure. Pushing three body tags at once bought the same
backdrop intruder `boss` bought by stacking guards -- the fourth time in this
repo that pushing past what a change needs has summoned something nobody asked
for. Two tags eased is the whole fix.

`petite` is left alone on purpose: it is the tag `boss` swaps out to grow her
up, and leaning on it here would trade one wrong proportion for another.

And one tool fix the recolour needed at this size. The die-cut white outline is
2/15/24 from skin -- outside a tolerance of 16 -- but its antialiased edge
passes through every value in between, so the selection speckled the outline
with repainted dots. `recolor_skin.py` now opens the selection with one 3x3
pass, which removes every speck and costs nothing that is a garment.

Kept: `ykprone-slim-final.png`, 2048x1368, stroke 1.255 per 1000px, through the
same three steps as the entry above.

### Regions beat tags: knee-highs over tights in one pass (2026-08-17)

The previous entry concluded that this model cannot draw knee-highs over tights,
and that was true of the prompt. It is not true of the picture. The two garments
occupy different parts of the frame, and ComfyUI's stock `ConditioningSetMask`
conditions different parts of the frame separately, so the argument stops being
lexical and the tags stop competing.

`scripts/yk_prone_legwear.py`, three conditionings:

    base    the prone prompt with the legwear block cut out,
            masked to everything OUTSIDE the two regions
    thigh   the same prompt + grey pantyhose, over hip and thigh
    calf    the same prompt + white knee-highs, over the raised lower legs

**Three things had to be right, and each was a render.**

1. **A region prompt must carry the whole prompt, not just its garment.**
   Fragments of five tags measured nothing at strength 1.0, 2.0 and 3.0. The
   base describes the entire picture; a fragment cannot outvote it.
2. **The base must be masked to the complement.** This is the one that mattered.
   Left unmasked it still describes the thigh, and averaging a prompt that says
   nothing about legwear with one that does lands halfway: the tights came out
   at 236 and 242 grey-white at strength 2.5, 3.5 and 4.0 alike -- present, and
   too pale to read. Masked out with `MaskComposite` + `InvertMask`, the thigh
   lands at **134,131,134** against this recipe's own `grey pantyhose` measured
   at 135,127,128. The colour is not approximated, it is the same colour.
3. **`set_cond_area: "mask bounds"` is unusable.** Colour blocks and torn
   geometry. `"default"` throughout.

The diagnostic that unstuck it is worth copying: when the regions had no visible
effect, the region prompts were swapped for absurd ones -- black pantyhose on
the thigh, RED socks on the calves. The socks came out red exactly inside the
mask. That separated "the wiring is dead" from "the request is too weak", and it
was the second. **Ask a masked region for something outrageous before concluding
that masking does not work.**

Strength 1.0 and 1.5 both land it; 1.0 is cleaner and is the default.

Kept: `ykprone-reg2k-prone-1886970040`, 2048x1368, stroke 1.391 per 1000px.
Grey tights hip to knee, white knee-highs knee to toe, over them, from one
`--hires 2048` command and no post-processing at all. The three-step recolour
route in the entry above still works and is now the fallback, not the recipe.

Open: a thin white line crosses the backdrop beside the knee, which is the
region boundary printing itself. `recolor_bg.py` is the existing answer to a
backdrop this recipe does not control. And the masks in `assets/` belong to seed
1886970040 -- on any other seed they are wrong, and the honest way to get one is
to render it first and cut new masks from it.

### ニーハイ is `thighhighs`, and the mask is what decides it (2026-08-17)

「ハイソックスとニーハイの違いが曖昧になってる。私が欲しいのはニーハイです」.

The previous entry shipped `kneehighs`, which is **ハイソックス** -- knee-length,
stopping below the knee. **ニーハイ is `thighhighs`**: over the knee, ending on
the thigh. The translation was mine and it was wrong, and it did not stay a
wording problem, because the masks were cut to match the wrong garment: the sock
region covered the whole raised leg, so the sock top landed where the leg meets
the hip and the grey had only the buttock. That is the spats read, arrived at a
third time by a third route.

The fix is two lines and no new mechanism, which is the point:

- the sock region's tags become `(white thighhighs:1.8),
  (white over-kneehighs:1.6), (thighhighs:1.5)`;
- the two masks are re-cut against a line across the thigh at y=470, 12px of
  transition: below it tights, above it sock.

**The mask is the garment's length.** The tags say what it is made of and the
mask says where it stops, and of the two the mask is the one that decides
ニーハイ from ハイソックス. Nothing in the prompt has to change to move the sock
top up or down the leg -- redraw the line. A 40px transition and a 12px one both
work; the crisp one gives a slightly more definite boundary and shipped.

Kept: `ykprone-nh2k-prone-1886970040`, 2048x1368, stroke 1.399 per 1000px. Grey
tights over hip and thigh, white thigh-highs from mid-thigh to the toes, one
pass, no post-processing.

Open, and inherited: the thin white line across the backdrop beside the knee is
still there, and no welt band is drawn at the sock top -- the boundary is a
colour change, not a hem. `zettai ryouiki` is not available to ask for it, since
that names bare thigh above the sock and there is none.

### The rear is the dress's job, and a third region is what gives it back (2026-08-17)

「ワンピースの下に黒いキャミソール着てる？それはちがう。お尻を隠すのはワンピースです」.

Between the purple hem and the grey there was a black band hugging the hip,
reading as a camisole or a pair of shorts under the one-piece. Nothing asked for
it: the two regions owned the thigh and the legs, the rear belonged to the base
prompt, and the base prompt has a black coat in it. **An unassigned region gets
drawn from whatever is nearest in the prompt.**

The hem has never answered to length tags -- that is in the module docstring,
measured over three renders back in the first session. It answers to being given
a region. A third mask over the rear, prompted `(purple dress:1.9), (dress:1.7),
(dress hem:1.5), (frills:1.3), (long dress:1.4)`, and the dress covers the
buttocks with its own frilled edge. The black band is gone because there is no
longer anywhere for the coat to reach.

Two lines across the body now define the whole lower half, and they are the
tunable part:

    y=430   the sock top      above it sock, below it legwear
    y=620   the hem           below it dress, between the lines tights

**A thin region needs more strength than a fat one.** The tights band is the
narrowest of the three and sits between two much larger pale neighbours; at
parity it came back at 213,206,215 -- washed out -- against the 134,131,134 the
same prompt lands when it owns more of the leg. `WEIGHT` gives it 1.8x. That is
buying back what the neighbours take, not asking for a different colour.

Kept: `ykprone-dr2k-prone-1886970040`, 2048x1368, stroke 1.225 per 1000px.
Dress over the rear, a band of grey tights below the hem, white thigh-highs from
mid-thigh to the toes.

Open: the tights band is subtle at print size -- pale grey between a purple hem
and a white sock, and the eye can read it as shadow. Widening it means moving
one of the two lines, which is a mask edit and not a prompt edit.

### The socks' own design, which the regional rewrite had quietly dropped (2026-08-17)

「タイツの色とニーハイの色・模様は覚えてます？？」. The record says, and every
entry above it was built on:

| | design | measured |
|---|--------|----------|
| tights | grey, opaque | `#877f80` = 135,127,128 |
| ニーハイ | **very pale purple**, not white; **vertical knit ribbing** the length of the leg; a **purple welt band** at the top | `(ribbed legwear:1.35)` brings the rib back and the welt returns with it |

The regional rewrite asked its sock region for `(white thighhighs:1.8),
(white over-kneehighs:1.6), (thighhighs:1.5)` -- plain, white, smooth. Three
tags, and all three of them wrong about the garment. Rewriting a prompt into a
new mechanism is where settled detail goes missing, because the new thing is
built to test the mechanism and the detail is not what is being watched.

Corrected to `(very pale purple thighhighs:1.8), (ribbed legwear:1.5),
(lavender tint:1.3)`. Three tags again, deliberately: at five the coat sprawled
over the hip and the dress went missing, so **the token-count rule that governs
the global block governs a region too.**

One thing the regions buy that no global prompt could: `opaque pantyhose` lives
in the tights region and nowhere else. That tag is what the `boss` session
caught flattening the socks' knit when both garments shared one prompt. Split
into regions, the smooth face belongs to the tights and the rib belongs to the
socks, and neither has to be the other's surface.

Rendered: `ykprone-rib2k-prone-1886970040`, 2048x1368, stroke 1.289 per 1000px.
Ribbing the length of the sock, welt band at the top, pale purple.

**Not settled, and worth being plain about.** The grey tights band between the
hem and the sock top will not co-exist with the corrected socks. Six attempts on
this seed: with `dark grey`/`charcoal` in the region it draws a dark blob at the
hip; without them it is not drawn at all; at 1.4x region weight it vanishes, at
1.8x it blobs; shortening the sock to expose more thigh turned the whole leg
grey and ribbed instead. The shipped `ykprone-dr2k` has the band and plain white
socks; this render has the design and no band. Both are in the tree.

Also learned the hard way: **masks do not move with the picture.** After several
prompt changes the committed masks no longer sat on the anatomy they were cut
from -- the tights band ended up under the sock and the dress mask over bare
skin. Re-cutting from the current render is a real step in the loop, not a
one-off setup, and the re-cut has to exclude the backdrop explicitly (it drifts,
and on one render it came within tolerance of the sock colour and turned a leg
mask into a full-width stripe).

### A costume contract, since the prompt cannot hold one (2026-08-17)

「キャラの服装は強くコードで残したい。ポーズを変えると直ぐブレる」. It cannot be
held by prompt text -- this session is the evidence, and so is every splice in
`positive()`: `boss` five, `nape` three, `prone` six. Tags are one argument about
the whole picture and a new pose re-weights all of them.

The two things that would actually pin it are a **costume LoRA** and
**IPAdapter**, and both are blocked on the same fact: the Windows worker has
only the `hassaku-il-v22` diffusers folder. `LoraLoader`, `ControlNetLoader` and
`CLIPVisionLoader` all return empty lists and no IPAdapter node is installed.
With no SSH and no SMB, putting anything on that disk needs a command run over
RDP -- which `scripts/fetch-models-windows.ps1` exists for, and which the repo's
manifests are already written for (`ComfyUI_IPAdapter_plus` and
`ip-adapter-plus_sdxl_vit-h.safetensors` are both listed).

So `scripts/costume_check.py`: not prevention, **detection**.

**Prompt side, and it found its own reason to exist.** Each pose's prompt is
rebuilt from the shared blocks and diffed tag by tag against what `positive()`
returns; every difference must be declared with a reason. Writing the
declarations out was the first time the fifteen poses' splices have been in one
place -- they were written one session at a time, by `.replace()` calls that do
not know about each other. Fifteen poses, eighteen exceptions.

**And the blocks themselves are fingerprinted.** Comparing poses against the
shared blocks cannot see a change *to* the shared blocks -- that was tried:
swapping `black hooded cardigan` for `black hoodie` passed every pose, because
every pose was compared against the hoodie. A hash of the seven blocks catches
it. `--accept` prints the new one, for a change that is meant and written down.

**Render side, and absolute floors do not work.** With tolerances wide enough to
catch a shaded garment, hair satisfies "pale sock" and shading satisfies
"legwear grey": three renders this project had already rejected all passed. What
separates them is the share against a render that was *accepted* -- the
bare-legged arm reads 0.30x of the accepted pale-sock share. So the check is
relative and per-pose, with the band at 0.4-2.5x, set below the disagreement
between two accepted renders of one pose (0.49x on skin alone, because one has
the dress covering more) and above nothing else.

    uv run scripts/costume_check.py                          # all poses + fingerprint
    uv run scripts/costume_check.py --palette r.png --pose prone
    uv run scripts/costume_check.py --palette r.png --pose prone --record

What it is not: it measures colour presence, not garment identity. A grey sock
would pass as grey tights. It is a smoke alarm, and the reason it is worth
having is that everything it checks is something this project has already got
wrong at least once.

### Both at once: grey tights AND the ribbed pale ニーハイ (2026-08-17)

They would not co-exist in one pass, and the reason turned out to be measurable
rather than mysterious.

**The band region works; grey specifically loses.** The diagnostic that unstuck
the regions in the first place worked again: asked for `(red pantyhose:1.9)` the
band came back red, exactly inside its mask. So the mask is on the anatomy and
the conditioning reaches it -- what fails is grey against this palette. It is a
low-saturation neutral sitting between pale purple socks, a purple hem and cream
skin, and the base prompt says `pale skin`; a small perturbation loses to its
neighbours. Red survives because it is far from everything.

Pushing the grey harder is not available either: `(dark grey pantyhose:1.9),
(charcoal legwear:1.7)` on the same mask broke the composition and drew two of
her -- the fifth time in this repo that overshooting a fix has summoned
something nobody asked for.

**Masked negatives work, and did not help here.** A negative can be masked and
combined exactly like the positive, so the band can forbid `(bare skin:1.6),
(bare legs:1.5)` while the face keeps its skin. Wired, ran, and the band still
came back skin. Worth knowing the lever exists; it is not the lever for this.

**Re-cutting the masks each round does not converge.** Cutting them from the
current render moved the picture, which made them wrong again -- one round put
the socks bunched at the ankles and the feet bare. The loop oscillates because
each mask edit is also a conditioning edit.

**What shipped is the deterministic route, on top of the single-pass render that
already had two of the three right.** `ykprone-rib2k` has the dress over the
rear and the ribbed pale-purple thighhighs; the band between them was bare skin,
which is precisely the case `recolor_skin.py` exists for:

    uv run scripts/recolor_skin.py ykprone-rib2k...png \
        --box 1520 750 1920 1100 --from-color '#fdf2e8' --tolerance 16 \
        --color '#877f80' --out band-grey.png --mask-out band-grey-mask.png
    # crop 1280,541 768 -> 1024, queue_refine --mask 0.45, then
    uv run scripts/paste_refined.py band-grey.png bandgrey-r_00001_.png \
        --box 1280 541 768 --mask band-grey-mask.png --out final.png

One catch worth recording: `queue_refine.py --from-prompt` cannot read a
*regional* graph, because the sampler's positive points at a
`ConditioningCombine` and not at a `CLIPTextEncode`. Pass a plain render's
prompt id and give the text with `--positive`.

Kept: `ykprone-band-final.png`, 2048x1368, stroke 1.302 per 1000px. Dress over
the rear, grey tights on hip and thigh, ribbed pale purple thighhighs with their
welt over them from mid-thigh to the toes.

**And the check earned its keep on its first real change.** `costume_check.py
--palette` failed it: `legwear grey 4.32% (2.71x of baseline)`. That is the
intended change -- the grey went from a sliver to a band -- but the tool is
right that the costume is not what was accepted before, and accepting it is now
an explicit act (`--record`), not something that happens quietly.

### SSH to the worker, and IPAdapter on it (2026-08-17)

The box grew an SSH server, which changes what is possible: models and custom
nodes can be put on that disk from here instead of from a chair in front of it.

**Getting in cost three findings, each worth a round trip.**

- **A correctly listening sshd was still dropped**, because the firewall rule
  ships scoped to the *Private* profile and the LAN interface is classified
  *Public*. The tell is that the port *times out* instead of refusing:
  `netstat` showed `0.0.0.0:22 LISTENING` while nothing arrived.
  `Set-NetFirewallRule -DisplayName 'OpenSSH SSH Server (sshd)' -Profile Any`.
- **Quoting through ssh -> cmd -> powershell is not usable**, and the console is
  Shift-JIS so what comes back is mojibake with half the arguments eaten. Send
  `-EncodedCommand` with UTF-16LE base64 instead.
- **Windows OpenSSH kills the process tree when the session ends.** Two detached
  `Start-Process` downloads died at ~160MB the moment the ssh command returned.
  Hold the connection open for the length of the job, or create the process
  through `Invoke-CimMethod Win32_Process Create`, which is owned by the WMI
  service and survives -- that is how ComfyUI is restarted now.

The key is `~/.ssh/comfyui-worker`, dedicated and passphrase-less, deliberately
not the 1Password one: that agent wants approval for every signature, which is
right for GitHub and wrong for a host that unattended scripts talk to.

**IPAdapter is installed and verified.** `scripts/fetch-ipadapter-windows.ps1`
clones `ComfyUI_IPAdapter_plus` and fetches the two models, checking both
SHA256s against `manifests/models-sha256.txt` -- the hashes taken from the mac's
own copies before they were deleted, so what is on that disk is bit-for-bit what
this repo was built against. 35 IPAdapter nodes now load.

**First measurement: it transfers the picture, not the wardrobe.** At the
obvious settings it is unusable -- `weight 0.6` and `0.9` on `standard` brought
the reference's whole character across: painterly shading, a cluttered backdrop,
and the die-cut outline gone. This project's look *is* the flat colour and the
white cut edge, so the adapter has to be turned down until it stops carrying
them:

| weight | type | start | result |
|--------|------|-------|--------|
| 0.6 / 0.9 | standard | 0.0 | style destroyed, backdrop invented |
| 0.4 | prompt is more important | 0.0 | style holds, **and a second small figure** |
| 0.4 | prompt is more important | 0.25 | style holds, costume carried |
| 0.25 | standard | 0.15 | style holds, costume carried |

A late `start_at` is what buys it: the prompt sets composition and style over the
first quarter of the schedule, and the adapter only speaks after that.

**"Style holds" in that table is wrong, and the eye caught it before the tool
did.** Put those arms beside a control at the same pose and seed and the drawing
has changed in every one: the tights are airbrushed instead of cel-shaded, and
the contour is heavier.

| arm | stroke /1000px |
|-----|----------------|
| control, no adapter | **2.958** |
| 0.25 standard, start 0.15 | 3.933 |
| 0.40 prompt-first, start 0.00 | 3.547 |
| 0.40 prompt-first, start 0.25 | 3.685 |
| the reference itself | 1.302 |

20-33% heavier than the control, all of them. Note which way that runs: the
reference has the *finest* line of anything in the table and the outputs still
came back coarser than the control, so the adapter is not copying the reference's
stroke -- it is smearing the sampler's. "Use a flatter reference" is therefore not
the fix, and the lesson from the first table generalises the other way instead.

`end_at` was 1.0 in every one of those arms. The contour and the flat fills get
resolved in the *last* steps and the adapter was still speaking through all of
them. `start_at` protects the composition by handing the prompt the opening of
the schedule; `end_at` should protect the drawing by handing it the close. The
plain `IPAdapter` node cannot express that usefully -- `IPAdapterAdvanced` can,
and also exposes `attn_mask` if the window alone is not enough and the adapter
has to be confined to the clothes.

**It was the window.** Same pose, same seed, `linear`, `start_at` 0.25:

| arm | stroke /1000px | vs control |
|-----|----------------|------------|
| control, no adapter | 2.958 | -- |
| w 0.55, end 0.45 | **2.777** | -6%, *finer* than the control |
| w 0.40, end 0.45 | 3.377 | +14% |
| w 0.40, end 0.60 | 3.936 | +33% |
| w 0.40, end 1.00 (previous sweep) | 3.685 | +25% |

Flat fills and the die-cut edge are back in all three; the airbrushed tights are
gone. The surprise is that **raising the weight lowered the stroke** -- 0.40 at
end 0.45 measures 3.377 and 0.55 at the same end measures 2.777. So what was
coarsening the line is not how loudly the adapter speaks but how long: close the
window and the strength can go up. Don't read the column as monotonic, though --
end 0.60 scores worse than end 1.00, which is noise at this sample size.

**It does not hold the costume, and it does not keep the line either.** Both
halves of that claim were made here on one pose and one sample, and neither
replicates. Retracted in full; the numbers that killed them are below.

The claim was built on `sip` renders measured against the *prone* baseline, where
`legwear grey` went from 0.44x without the adapter to 0.99x with it. **That
measurement is confounded.** The reference image is `ykprone-band-final.png` --
itself a prone render. An adapter that pulls the output toward its reference
pulls it toward prone's baseline by construction. The number was measuring
"resembles the reference", which is what an adapter does by definition, not
"wears the approved costume".

Worse, the confound was avoidable: the same section already said that cross-pose
shares conflate costume with composition and that only same-pose control-vs-arm
comparisons carry an argument. The conclusion was then drawn from precisely the
comparison it had ruled out.

## 2026-08-17 -- the generation test, and a negative result

`boss` is the one pose with a baseline of its own, so it is the one comparison
with no framing confound. Same seed, adapter off and on, at
`weight 0.55 / start_at 0.25 / end_at 0.45`:

| boss | legwear grey | dress purple | coat black |
|------|--------------|--------------|------------|
| off | 0.60% (0.22x) FAIL | 1.47% (0.39x) FAIL | 25.18% (1.08x) ok |
| on | 0.56% (**0.20x**) FAIL | 8.93% (2.35x) ok | 10.90% (**0.47x**) ok |

The grey tights do not improve -- 0.22x to 0.20x, both failing. `coat black`
moves *away* from its baseline, 1.08x to 0.47x.

`prone` at seed 1886970040 is the sharpest version of the test, because there the
reference *is* this pose's own finished render -- the one that took a manual
recolour and a masked refine to reach. If the adapter can carry a costume at all,
it can carry it here:

| prone | legwear grey | pale sock |
|-------|--------------|-----------|
| off | 1.77% (0.41x) | 9.78% (0.35x) FAIL |
| on | 1.73% (0.40x) | 7.12% (0.25x) FAIL |

Nothing. 0.41x to 0.40x.

And the line thickens everywhere, so the `sip` result of 2.777 against a control
of 2.958 does not replicate either:

| pose | off | on |
|------|-----|-----|
| boss | 4.173 | 4.548 (+9%) |
| chair | 3.921 | 4.177 (+7%) |
| lounge | 2.220 | 2.224 (+0%) |
| peace | 1.769 | 2.030 (+15%) |

So IPAdapter, on this model at these settings, does not answer the question it
was installed for. The costume still cannot be held by conditioning; it has to be
held by weights. That points back at the LoRA route, and the dataset for it is
the `pick/*` renders that already exist.

Method lesson, more valuable than the result: one pose is not a measurement. Both
retracted claims came from a single sweep on `sip`, and a four-pose replication
cost one batch of renders and overturned both.

Still open: `sip` has no baseline of its own (only `prone` and `boss` do), so the
comparison above borrows prone's and pays for it with the framing caveat. Record
baselines per pose from an accepted render and the caveat goes away.

## 2026-08-17 -- `/upload/image` blinds the worker for minutes

Cost most of an evening, so it is written down. Symptom: `/prompt` returns 400
with

    model_path: 'hassaku-il-v22' not in []
    image - Invalid image file: ykprone-band-final.png

for a model that is on disk and an image that is in `input\`, while
`/object_info` in the same second lists both. Every graph fails, including ones
that rendered minutes earlier.

**The cause is still unknown.** Four explanations were proposed and all four
died, which is the useful content of this section:

- *A cache gone stale over hours.* Killed by a full restart that changed nothing.
- *`POST /queue {"clear": true}`.* Every rejected batch did have a clear just
  before it and every accepted batch did not -- a clean correlation across six
  batches, and coincidence.
- *The IPAdapter nodes.* Killed by submitting plain, `IPAdapter` and
  `IPAdapterAdvanced` graphs alternately, nine in a row: all accepted.
- *`/upload/image`.* This one survived a bisection of the caller down to the
  single differing line, and then died anyway: a later run that uploaded nothing
  at all was rejected for ten minutes straight while inline submissions of the
  same graph, in the same minutes, were accepted every time.

The only reproducible statement left is about the caller, not the server: the
graph is rejected when submitted from `.local/ip_end.py` and accepted when the
identical graph is submitted inline. That is not an explanation, and it is
recorded here as an open question rather than a finding.

Two practical rules did come out of it:

- **Don't re-upload an input the worker already holds.** Independent of cause,
  the sweep was pushing the same 1.9MB reference on every run for nothing.
- **Don't gate on the listing, and never fall back to uploading.** The image list
  flaps within seconds while the worker is in this state -- a curl found the name
  and a check one second later did not -- so a "is it there? no -> upload" guard
  is unreliable in both directions and feeds the very state it guards against.
  Two sweeps were lost to that loop.

And one warning about the fix I reached for: **a retry loop that swallows the
error makes a stuck run look like a working one.** The sweep sat in a 40-attempt
loop printing nothing while the worker was accepting everything else; from
outside it just looked slow. Retries should report each failure, not only the
last.

The reporting is what makes this expensive: the two nodes named in the error are
collateral. `input_config: [[], {}]` means ComfyUI could not get INPUT_TYPES at
validation time at all, so the node it points at is not the node with the
problem. Confirmed by submitting a LoadImage-only graph with the very same
filename -- accepted, while the full graph naming it was rejected.

**A headless restart costs you the log.** ComfyUI had been restarted through
`Invoke-CimMethod Win32_Process Create` to pick up the new nodes, which leaves no
console and so nothing to read when it misbehaves. Relaunch with the streams
redirected instead:

    cmd /c cd /d <portable> && .\python_embeded\python.exe -s ComfyUI\main.py ^
        --listen --windows-standalone-build > comfyui.log 2>&1

Also: `/system_stats` answers well before the server can validate a model path,
so it is the wrong readiness probe after a restart. Submit a known-good graph.

Not yet answered: whether this actually *stabilises* the costume across poses,
which is the reason it was installed. That is a measurement -- run the poses with
and without, and compare `costume_check.py --palette` against their baselines --
and it needs baselines for more than the two poses that have them.

### The lower body on `fuji-d042`: what a mask does to tags, to the line, and to the leg (2026-08-18)

「9cc0d762 の下半身をファインチューニング」. That id is the sock-only pass at
0.42; the picture under it has a white scribble where the sock's welt should be,
formless feet, and the grey band at the hip broken into segments. Widening the
mask to the whole leg and walking the denoise up was the obvious move and it is
the wrong one, three times over.

**A mask is somewhere for unspent tags to go.** The inherited positive holds
`(drawstring:1.4)`, `(frills:0.85)` and `(hair ornament:1.4)`, every one of them
for the hood or the hair. Inside a leg mask none of them has a referent, so the
sampler spends them on the leg -- white petals and tied bows around the ankle and
around the hip band -- and **spends them harder at every step up the ladder**:

| denoise, global positive | ankle | hip band |
|--------------------------|-------|----------|
| 0.45 | white shapes appear | grey, segmented |
| 0.55 | petals, larger | one segment turns purple |
| 0.65 | petals and leaves | two segments purple |

The nape session already recorded the shape of this -- handing a region the full
`positive()` is asking for the defect inside the region you want fixed -- but it
recorded it about a tag that *described* the defect. This is the other half: a
tag that describes nothing in the region does not go unused, it goes somewhere.
A region-local positive removes the ornament completely at the same denoise.

**A masked refine thickens and darkens the line inside its own mask.** The line
notes measure whole canvases, which cannot see this at all. `stroke_region.py`
is the same statistic over two boxes of one picture -- the face the pass never
touched, and a calf it redrew:

| render | calf/face stroke | calf ink luminance |
|--------|------------------|--------------------|
| `sock-fuji`, before any of it | 0.95x | 59.9 |
| `fuji-d042` | 1.02x | 48.9 |
| region-local 0.55 | **1.26x** | **35.3** |
| region-local 0.65 | 1.11x | 41.7 |
| region-local 0.75 | 0.94x | 54.7 |

「脚だけ線が太い」 is literally true and it is also darker, and the same
denoise that fixes it is the one that fixes the ankle. Restoring
`(delicate lines:1.2)`, which the region-local rewrite had dropped, is worth
3-5% and no more -- 1.26x to 1.22x, 1.11x to 1.05x. **Denoise is the lever,
again**, and a dropped line tag is not the explanation it looks like.

**And the leg's volume moves against the line.** Per-row width of the right leg,
which runs clear of the coat, at the row nearest the hip:

| render | y600 | y680 | y760 | calf/face stroke |
|--------|------|------|------|------------------|
| `fuji-d042` | 164 | 166 | **229** | 1.02x |
| 0.65 | 160 | 170 | **225** | 1.17x |
| 0.70 | 161 | 178 | 201 | 1.04x |
| 0.75 | 161 | 178 | 198 | 0.93x |

「太ももが細く感じる」, and it is 14% at 0.75. The crossover sits between 0.65
and 0.70: at 0.70 the thigh is already gone and the line has only just come
right. **One number on one mask cannot buy both.** `(toned legs:1.2)` raised to
1.4 does nothing about it -- 198 to 200 -- which is worth knowing, because that
tag is the recorded carrier of leg volume everywhere else in this file. It
asserts volume in a first pass; it does not restore volume a refine took away.

**What works is not sampling the thigh.** `.local/cut_calf.py` subtracts the
dilated thigh mask from the full leg mask; what is not sampled cannot be redrawn
thin. At 0.75 on that mask: thigh 217, stroke 0.94x, no ankle band, and every
line of `costume_check.py --palette` passes -- including `legwear grey` at 0.49x,
which every full-leg region-local pass had pushed to 0.40x and under the floor.
The grey band at the hip was collateral from a mask reaching further than the
work did.

Kept: `rl-calf-d075`. The slimming is not gone, it moved up the leg -- y600/y680
read 142/134 against the base's 164/166 -- and protecting that too means giving
up the redraw from the knee down.

**Two smaller results, both negative.** The welt band's colour does not answer
to its weight: 1.4 to 1.7 draws it louder and whiter, never purple. And asking
for the welt at all is what put a band at the *ankle*, where the design has
none; 「足首バンドは不要」. It is banned now, and the ban is what removes it --
0.75 was only ever thinning it.

**One process note, which cost the first ladder.** `--denoise 0.$d` over
`for d in 045 055 065` passes 0.045, not 0.45. Three renders came back nearly
identical to their input and, more usefully, nearly identical to *each other*:
in-mask mean change 3.84, 3.90, 3.97 across a denoise range that should have
moved it by a third. **A refine that does not respond to its own denoise is a
mis-passed parameter, not a stubborn picture** -- check `/history` for the value
the server actually got before diagnosing anything else.

### The prone legs were not fixable, and the skeleton is what replaced them (2026-08-18)

Continuing from the entry above, and ending it: the leg work there was polish on
a drawing that was wrong underneath, and the whole session's masked passes are
worth less than the one measurement that should have been taken first.

**Run the pose estimator before deciding a region is fixable.** ComfyUI ships
`SDPoseKeypointExtractor`/`SDPoseDrawKeypoints`, so no preprocessor node is
needed -- it wants `Comfy-Org/SDPose :: checkpoints/sdpose_wholebody_fp16` and
refuses a plain diffusion checkpoint, checking it for a `heatmap_head`. On
`wide-ink-d025` it found the face and both hands and **no hip, knee or ankle at
all**, and read a lock of hair as a limb. A whole-body pose model that cannot
find a hip in a leg is saying the region is not a human shape. That is the
difference the hand fix already recorded -- badly drawn version of the right
thing, versus the wrong thing -- and it can be measured in one render instead of
argued over ten.

What ten passes could not do, in order: three denoise ladders, a region-local
prompt, `(clean lineart)` with the whole sketch family banned, a 2x crop-and-zoom
redraw (which removed the rib instead of drawing it), and a geometric widening of
the thigh. The last one is the clearest: it added 25% to the thigh and the
complaint came back as 「お尻と太もものつながりが不自然」, because the width was
never the problem -- **the joint was, and a warp cannot add a joint.**

**The rebuild.** `noob-openpose-fp16` works on `hassaku-il-v22`; the family
split in `models.md` is about what each net was trained to read, not a checkpoint
it refuses. The skeleton has to be authored (`.local/pose_author.py`, COCO-18 and
the standard limb colours) since there is nothing extractable to edit and no node
accepts `POSE_KEYPOINT` as input. Applied to the FIRST pass only, at strength
0.8 over 0-80%, then the recipe's own 2048 pass: prone with the feet up means the
thigh lies along the floor and the shin rises from a bent knee, and stating that
as three points is what the prompt never could.

Kept: `rb-rough`, `28ad4b59`.

**Two corrections to make about sketch tags and about my own probes.**

`(sketch)`, `(rough sketch)`, `(sketchy)`, `(messy lines)` went into the negative
to kill the legs' draft feel. They belong in the POSITIVE at 1.1-1.15. Banning
them took the drawn quality with them and the complaint became 「手書き感がなく
なった」. **下書き感 and 手書き感 are not the same quality and do not share a
lever** -- one is uncertainty in the stroke, the other is the hand in it.

And the probes. Three graphs written here by hand came back as shattered mosaic,
and I read the first as the ControlNet being incompatible, the second as the
canvas being too large, and the third as the ControlNet again. All three were
wrong: the recipe's own graph renders cleanly on the same worker with the same
net at the same size, and splicing the net into *that* graph worked first try.
**Build from the graph that works, not from a fresh one that ought to.** What
actually broke the hand-written probes is still unknown, and is written down here
as unknown.

**Measuring the look, and four metrics that failed.** 「線も発色も良すぎる」 is
top-decile saturation of the figure, nothing else: mean saturation reads 22.1
against 21.5 across two renders anyone can tell apart, because the black coat and
the pale skin swamp it. The top decile reads 35 against 56, and the fraction of
figure above saturation 60 reads 3.3% against 9.9%. Stroke-width spread,
runs-per-megapixel and ink fraction all failed to separate drawn from vector
first -- runs-per-megapixel inverted, since a smaller canvas spends fewer pixels
per line and counts more of them.

### Two garments on one leg: abandoned, and what it cost to get there (2026-08-18)

The entry above left the grey tights band open with six failed attempts against
it. This closes it: **the two-layer costume is dropped.** 「タイツ×ニーハイは
修正コストが辛い、公式の別デザインでは[V6 sheet]だしタイツ1本にするか」. The
official V6 sheet draws the leg as one opaque pantyhose, so the layering was
never load-bearing for the character -- only for this recipe's own history.

Everything below was spent finding that out, and none of it made the two
garments co-exist.

**The lineart was the answer the whole time, and it took a question to see it.**
「線画時点でおかしくない?」. Stripping the colour off shows the drawing has
exactly two garment boundaries, both at the knees, and none anywhere on the
thigh. Every colour split I put there was therefore an edge with no line under
it, which is why each one read as a third garment rather than as one ending --
first as 「スパッツ」, then as 「ハイソックス、タイツ、スパッツ」. **A garment
edge that the lineart does not draw cannot be created by colouring, at any
tolerance.** Check the lineart before recolouring a region: `(g < 110)` and look.

**Colour cannot separate anything in this palette.** Three selections failed in
a row on distances the eye reads as obvious: the pale band and the backdrop are
10 apart, so restoring "the backdrop" after a repaint put the repainted band
back; the grey tights sit at luminance 128, under the 150 that `--line-max`
treats as lineart, so a flood fill saw the whole garment as a barrier; and the
die-cut outline is inside a 28 tolerance of skin, so the default repaints the
outline and prints the box's corner as a rectangle. What does work is shape:
threshold, close, fill holes, largest component for the figure; and connected
components of "tights-coloured" for a region, where the drawn contour breaks
connectivity precisely because it is not that colour.

**Regions: the wiring was fine and the request was too weak.** The notes'
own diagnostic settled it in one render -- ask the masked region for red
pantyhose, and the thigh came back red exactly inside the mask. So
`ConditioningSetMask` was working, the base was masked to the complement, and
grey still lost: raising the region weight from 1.8 to 2.6 and dropping
`(lavender tint:1.2)` moved 6% of the picture and not the thigh's colour. Grey
against a pale-purple neighbour is a near-tie in a way red never is. That is the
sixth attempt's finding restated, not a new one.

**Do not remove the ControlNet to test something else.** Without the skeleton
this prompt -- which has the legwear block cut out of it for the regions -- rerolls
to a bust and the legs leave the frame. I read the resulting hair as a thigh and
measured it. The skeleton is holding the composition, not just the anatomy.

**What shipped.** One garment: `(black pantyhose:1.55), (opaque pantyhose:1.5),
(matte legwear:1.2)`, with `thighhighs`, `kneehighs`, `socks`, `over-kneehighs`,
`two-tone legwear` and `legwear hem` banned by name -- those are the words the
two-layer recipe spent its weight on, and left in they put the second garment
straight back. `(gradient legwear:1.4)` is OUT although the sheet has one: it
came out inverted in both colours, dark at the ankle, because with the legs
raised "dark at the top" is the foot and the tag has no way to know which end of
a leg it is looking at. Flat is closer to the reference than a backwards
gradient.

Kept: **`one-muted`, `6e2c5592`** — one garment, the gradient running purple at
the thigh to black at the ankle. The three-step recolour route and
`yk_prone_legwear.py` both still work and are still correct; there is simply
nothing left for them to hold apart.

**Two corrections to the paragraph above, both mine.** `(gradient legwear:1.4)`
is IN, not out: I called it inverted against the sheet and dropped it, and the
purple-at-the-thigh end is the one that was wanted. And `one-flatblack` was
written up here as the keeper an hour before the picture was actually chosen —
it is the flat arm of a sweep, not a decision.

**The saturation numbers picked the wrong render, and that is the finding.**
Asked to take saturation down, six prompt arms failed — `(muted colors)` +
`(desaturated)`, black at 1.6, greyish purple, dusty purple, a vividness guard —
and three of them measured *higher* than the render they were meant to improve.
Then the arm measuring highest of all on my leg-saturation box (75.6 against
37.7) is the one that was chosen by eye. The box is fixed and the composition
moves under it, so it was reading dress and coat as often as leg. **A region
statistic on a fixed box is not a measurement when the thing being measured is
free to move.** Four metrics failed this way in one session: stroke-width
spread, runs-per-megapixel, ink fraction, and this. Each time the eye was right
and the number was answering a different question.

`.local/desat.py` scales HSV saturation and nothing else, so the gradient and
the line survive it: x0.55 puts the figure at mean 19.4 / p90 44 against the old
lineage's 22.1 / 35. It is the `recolor_bg.py` bargain — what the recipe does not
control, decide afterwards — and it is available on the keeper rather than baked
into it.

### Measuring 「手書き感」: four statistics that failed and one that works (2026-08-18)

「手書き感は数値パラメータで表現できるの？」. Yes, with three conditions, and
the four that failed first are what name them.

| statistic | why it failed |
|-----------|---------------|
| stroke-width spread (sd/mean) | 0.87-0.98 across renders anyone separates instantly |
| runs per megapixel | **inverted** -- a smaller canvas spends fewer pixels per line and counts more of them |
| ink fraction | dominated by whichever garment happens to be black |
| saturation in a fixed box | the composition moves under the box; it read dress and coat as often as leg |

What works, `scripts/handfeel.py`: **count marks in the figure's interior and
normalise by the figure's height.** Erode the figure by 25px first -- the
silhouette's contour is drawn just as firmly in a vector-flat render, and what
separates the two is what is drawn *inside* the shapes: hair strands, the
hatching in a coat fold. Count connected components rather than pixels, since it
is the number of marks the eye reads as drawn.

    cnrecipe (called vector-flat by eye)      72.9
    wide-ink-d025 (the pencil-feel lineage)  204.1
    rb-hires (the feel restored)             235.5

Three times the separation, on the pair where the other four moved by under ten
percent.

**It does not survive a change of canvas, and that is not a flaw in the
normalisation.** Same seed, same prompt: 1024 reads 36.9, 2048 reads 127.9.
Dividing by figure height cannot absorb it because a line's width in pixels does
not scale with the figure -- at 1024 two strokes occupy the pixels one does at
2048, and merge into a single component. **Compare at one canvas size only.** A
target band read off 2048 renders is not reachable by tuning a 1024 one, which
is the practical form of it: 1024 tells you the composition, and the line has to
be judged after the upscale.

**And the second pass reduces marks; the upscale is what adds them.** Stated
backwards here an hour ago. At 1024 with no second pass the figure reads 36.9;
adding a `denoise 0.6` pass at the SAME size takes it to 17.4. The 0.6 pass
smooths. What raises the count is the upscale splitting strokes that used to
share pixels, which also explains `one-lanczos` at 35.3 -- resampling the picture
with lanczos before the pass keeps the strokes merged, where a latent bicubic
upscale lets them separate.

**No tag reaches it.** Sweeping `(sketch)`/`(rough sketch)`/`(sketch lines)` from
1.15 to 1.75 gave 127.9, 147.0, 120.2, 122.1 -- a peak at 1.35 and no monotone
anywhere. The levers that actually moved this number were the upscale route and
`(muted colors)+(desaturated)` (158.2 to 123.6), both of which were added for
other reasons entirely. There is no dial; there is a configuration, a render,
and a measurement.

### The one-garment leg was a decision, not code (2026-08-18)

Another session, running its own pose through `yukari_recipe.positive()`, got
tights under knee-highs back. Nothing was broken. The decision to drop the
second garment was recorded in three places -- this file, the session's memory,
and `.local/onetights3.py` -- and in none of them was it the code that builds
the prompt. `scripts/yukari_recipe.py` still held the layered pair, and every
caller that did not know to splice over it got the retired costume.

That is the failure worth naming: a settled design change that lives only in
prose is a change the next session does not get. The renders that were approved
this session all reached the one-garment leg by rewriting the block from a
throwaway script, and the throwaway scripts are in `.local/`, which is not the
repo.

So it is in the blocks now:

- `LEGWEAR` is `(black pantyhose:1.5), (gradient legwear:1.4),
  (opaque pantyhose:1.4)`. `LEGWEAR_LAYERED` keeps the old text whole -- the
  grey-versus-black measurements, the over-kneehighs finding and the note that
  the sock-length arm was misjudged by a brightness metric are all still worth
  reading, and none of them were wrong.
- `LEGWEAR_BAN` -- `thighhighs`, `kneehighs`, `socks`, `over-kneehighs`,
  `two-tone legwear`, `legwear hem` -- is appended to every full-figure pose's
  negative. Portrait does not get it; the crop is above the legs and a guard
  against something out of frame is tokens spent on nothing.
- Prone's legwear splice is deleted. It was five replacements against tags that
  no longer exist, which would have silently done nothing. Its comment stays, as
  the record of what the model will not draw.
- `boss` appended `(ribbed legwear:1.35)` to `(thighhighs over pantyhose:1.55)`.
  That anchor is gone; it is appended to `(opaque pantyhose:1.4)` now, the slot
  in the new block that names the fabric rather than the colour. Same silent
  no-op otherwise.
- `yk_prone_legwear.legwear_block()` returns `LEGWEAR` unchanged. The module is
  the regional route to two garments and the costume has one; it still runs, and
  it is still the reference for masking a region out of the base conditioning.

Checked rather than assumed: `positive("prone")` plus the sketch-and-muted tail
now reproduces prompt `6e2c5592` -- the approved render -- string-for-string,
positive and negative both.

`costume_check.py` did its job and failed on the fingerprint, `ccf785bcfa21dbdc`
to `c8e405b1da502660`. Accepted here. Its five prone legwear exceptions are gone
with the splice they described; every pose passes.

What is NOT fixed, and is marked stale in the file rather than guessed at: the
`PALETTE` entries `legwear grey` and `pale sock` both belong to the retired
design, and `assets/costume-baseline.json` was recorded against them. A gradient
is not one RGB with a tolerance, so the replacement has to be measured off an
approved one-tights render and every pose re-recorded. Until then `--palette` is
checking a costume that is no longer built.

Still uncodified, and deliberately: the drawn-look tail `(sketch:1.15),
(rough sketch:1.1), (sketch lines:1.15)` with `(muted colors:1.3),
(desaturated:1.2)`. Every caller that wants it adds it by hand, which is the
same trap. It is left out because the poses approved before it -- portrait,
peace, boss, lounge -- were approved without it, and folding it into the shared
blocks would change their look on the quiet. Fixing that means re-approving
those renders, which is the user's call and not a refactor.

### Token cost is a property of the repo, and it was measured (2026-08-18)

「トークン節約施策を打ってください」. The repo is ~185k tokens of tracked text and
three files are more than half of it: this one at ~68k, `queue_dq3.py` at ~21k
and `yukari_recipe.py` at ~19k. Every one of them is what a one-line question
tempts a session to open whole.

What was done, and what each thing is actually worth:

- **`scripts/atlas.py`** — the map, computed rather than stored. `atlas.py`
  lists every script with its role, size and its own first docstring line
  (~1.5k); `atlas.py notes` prints this file's headings with line numbers and
  per-section sizes (~2.8k against 68k); `atlas.py notes <pattern>` prints just
  the matching sections; `atlas.py find <regex>` prints matching lines each
  under the heading it lives beneath. Table of contents plus one section is
  ~3.5k, a 19x saving on the file.
- **`--print-prompt` on `queue_dq3.py`**, mirroring the flag `yukari_recipe.py`
  already had. Read off the built graph rather than reassembled from the
  blocks, so what it prints is what would be sent. ~900 tokens against ~21k.
- **`scripts/archive/`** — fourteen scripts moved: nine `yk_*.py` design probes
  from before the recipe existed, and `style_sweep2`–`6`. Nothing imports them.
  The live surface went from 50 scripts to 36 and `__main__` from 33 to 19.

The index is deliberately NOT a committed file. A generated index is stale from
the moment of the next commit, and this repo has already been bitten once this
week by knowledge that was written down somewhere the next session did not
look. `atlas.py` re-reads the tree on every run, so it cannot be wrong about it.

What was considered and NOT done: splitting `render-notes.md` and the two big
recipes into smaller files. The section sizes make the case tempting — one
section, "Removing baked-in objects", is 97.7k characters on its own, 36% of the
file — but splitting buys nothing that `--offset`/`--limit` does not already
buy, and it costs the property that one grep covers everything. The recipes are
worse candidates still: their value is the commentary sitting next to the tag it
explains, and the reason to open them is almost always answered by
`--print-prompt` for a tenth of the tokens.

The general rule, since this will come up again: **the fix for an expensive file
is a command that answers the question, not a smaller file.**

## `stand` — the standing pose the file did not have (2026-08-18)

Fifteen poses and not one of them on its feet. `lounge`, `peace` and `nape` sit,
`prone` and `fall` lie, `sip` and `crouch` squat, `portrait` crops above the
waist — asked for a 立ち絵, this recipe had nothing to offer, which was worth
knowing before it was worth fixing.

The block, built to the file's usual budget (eight tags after `(solo:1.5)`,
`full body` last, no splice against any shared block):

```
(solo:1.5), (standing:1.5), (from front:1.3), (arms behind back:1.3),
(head tilt:1.2), (smug:1.35), (half-closed eyes:1.3), full body
```

Canvas 1024x1536 — the docstring's ceiling for full body, and a vertical figure
is what the height is for.

Two choices that are reasoning rather than measurement, recorded so the sweep
that follows can contradict them:

- **`(from front:1.3)` costs a tag on the camera.** Standing is the posture the
  model has the most other ideas about — three-quarter turns, walking, low
  angles — and the angle tags are what pick one. `(from below:1.35)` is already
  in NEGATIVE and works the same seam from the other side.
- **Hands behind the back, nothing held.** A prop is a second thing to get
  right, and a standing reference exists to show the costume.

The thing to watch is the crop. A standing body in a 2:3 frame is exactly the
case `full body` is carrying alone, and the poses that lost their shins here
lost them to a canvas and not to a tag.

First sweep, six seeds, the same set the other poses were settled on
(`yk-stand-<seed>_00001_.png`): 555666777, 111222333, 1886970040, 737373737,
2557902837, 3409564303. All six rendered; **not yet judged** — the block above
is as designed, not as measured, and nothing in it should be treated as settled
until a render is picked.

## The gradient had no direction in it (2026-08-18)

「グラデーションの向きが逆ですね。足先を黒に。これは固定化」.

`LEGWEAR` has asserted since the layering was retired that the garment runs
*purple at the thigh, black at the ankle* — and it was only ever asserted in the
comment. The three tags say what the garment is and nothing about which end is
which, and the model resolved that on its own the other way: black at the thigh,
fading pale at the ankle. All six seeds of the first `stand` sweep drew it that
way, so it was not a seed, and it had presumably been that way in every pose
since the one-garment change.

There is no directional tag to reach for. `gradient legwear` is the only
gradient word available and it carries no orientation, so the direction has to
be bought by naming the colour that goes at the top and letting black fall to
what is left. The tag for it was already in this file's record, filed as the
explanation of an accident:

> `pale purple pantyhose` gets DRAWN on the thigh and `grey pantyhose` does not.
> That is why the colours were inverted here for so long without anyone
> noticing: the wrong colour was buying thigh coverage.

That is now what the block is built on. **A finding recorded as the cause of a
bug turned out to be the mechanism for the fix** — which is the argument for
writing down the ones that look like nothing at the time.

Three wordings, one seed (1886970040), pose `stand`:

| block | result |
|---|---|
| `black, gradient, opaque` | black thigh, pale ankle — reversed |
| `black, PALE PURPLE, gradient, opaque` | purple thigh, black ankle — **kept** |
| `PALE PURPLE, black, gradient, opaque` | also right-way-up |

> **WRONG, corrected below — see "Naming the colour does not place it".** The
> table above was never measured. It was inferred from which render was picked,
> and the pick was made on the hands. Measured afterwards, none of the three
> arms fixed the direction. The rows are left standing because the wordings
> were really tried; only the results column is fiction.

Both of the four-tag arms fix it, so token order is not what carries the
direction here; naming the colour at all is. Black stays first and at 1.5, which
leaves it the garment's stated colour with the purple as the thing done to one
end of it.

```
LEGWEAR = "(black pantyhose:1.5), (pale purple pantyhose:1.35), (gradient legwear:1.4), (opaque pantyhose:1.4)"
```

Costume fingerprint `c8e405b1da502660` → **`a67b105340c90b52`**. This is a
costume change and therefore every pose in the file, not just `stand`: anything
rendered before today has the gradient the other way up, and comparisons against
older renders need to know that.

Four tags in a garment block, where the comment above `LEGWEAR` says three is
what it tolerates before the coat starts sprawling. Spent knowingly: if the coat
grows or the dress loses its frills, this tag is the first suspect.

## `stand` settled its hands (2026-08-18)

「ては出して欲しい。胸あたりに出す感じ」. `(arms behind back:1.3)` out,
`(own hands together:1.35)` in — one for one, the tag for the gesture.

`(hands up:1.25)` is a genuine ninth tag and it is what puts the hands at the
chest; without it the same seed lands them at the waist. The eight-tag budget
this file keeps quoting was measured on `yawn`, where a ninth pushed the pale
thighhighs out of a *layered* block that no longer exists, so it is worth being
explicit that the budget was not re-measured here — it was overruled, on one
seed, because the ninth tag is the whole ask.

Picked: `l2h2` on 1886970040 (prompt 9966667b). `positive("stand")` reproduces
that prompt exactly, which is the check that the settled block is the render.

### and its posture (2026-08-18)

`(arched back:1.2)` in `head tilt`'s slot, at eight tags. Picked over the same
tag added alongside `head tilt` (nine) and over `(arched back:1.35)` in the same
slot. Prompt 43ca8a03.

Why it had to be named at all: `l3h1` stood slightly chest-out and `l2h2` did
not, on the same seed, and those two arms differ **only in LEGWEAR's token
order**. The posture arrived from the encoding rather than from any tag, so it
was not reproducible and could not simply be kept. The range was swept downward
rather than up because `arched back` leans pin-up when raised, and the ask was
「少し」.

## Naming the colour does not place it (2026-08-18, corrects the entry above)

「グラデーションの向きが逆ですね。足先を黒に。これが治ってない」— said twice,
the second time about renders that were supposed to have fixed it.

Measured this time instead of inferred. The figure is the non-backdrop,
non-outline pixels; mean brightness per band down the lower 55% of the frame,
top to bottom (`.local/leg_direction.py`). Rising = pale at the ankle = wrong
way up:

```
l1h1  black, gradient, opaque                  66  56  46  47  64 106
l2h1  black, PALE PURPLE, gradient, opaque     71  91  98 103 108  79   rising
l3h1  PALE PURPLE, black, gradient, opaque     64  88  85 100 126  78   rising
l2h2  same as l2h1, other hand block           41  55  76  92 117  78   rising
```

So the four-tag block is **not** the fix that was written up an hour earlier,
and the earlier entry's result column was invented. What the arms actually
show is that adding a second colour name changes the leg's colour without
changing where on the leg it goes. `pale purple pantyhose` lands purple ON the
thigh, exactly as the old finding said — but the black does not move to the
ankle in exchange; it stays at the top and the ankle goes paler still.

Two things to try next, and the reason each is plausible:

- **`(two-tone legwear:1.4)` is in the NEGATIVE.** It was added to keep a second
  garment out, and purple-at-the-thigh-black-at-the-ankle *is* a two-tone leg.
  The ban may be fighting the very split being asked for.
- **The weights, not the order.** Black is the noun at 1.5 and purple the
  modifier at 1.35. If the model puts the dominant colour where the garment is
  widest and best-lit — the thigh — then the fix is to make purple dominant, and
  the order swap (l3) tested the wrong variable.

A mechanism worth ruling out either way: the dress is purple, and a purple thigh
against a purple hem has no boundary to draw, so the model may be placing black
at the top precisely because that is where contrast is needed. If that is what
is happening, no weighting will fix it and the direction has to be imposed after
the render, the way the backdrop already is.

### Seven wordings, and then it was done in post (2026-08-18)

Four more arms on 1886970040, measured the same way. Rising = pale at the ankle
= wrong way up:

```
g1  PALE PURPLE:1.5 dominant, black:1.35        85 108 111 121 113 130   rising
g2  g1, (two-tone legwear:1.4) out of NEGATIVE  70 100 109 118 108 123   rising
g3  committed block, ban lifted only            82 101 104  49  68 158   ankle pale
g4  no `gradient` word, two colours at 1.45     90 116 117 115 134  96   rising
```

With the three from the entry above that is **seven wordings**: a second colour
name, the order of the two names, the weights between them, the ban lifted,
and the gradient word removed. None of them moves the black to the ankle. This
is the shape already named in this file — when the tag describing the defect
does nothing at any weight, the defect is implied by something else — and the
`two-tone legwear` arms rule out the guard as the thing implying it.

The likeliest mechanism, and it explains every arm: **her dress is purple.** A
purple thigh under a purple hem has no boundary to draw, so the model puts the
black where the contrast has to be, which is the top. Nothing in a colour word
argues with that, which is why no weight reached it.

So it moves to post, which is where the backdrop already lives for the same
reason. `.local/leg_gradient.py` repaints the legwear-coloured pixels below the
hem along a purple->black ramp, scaling each pixel by its ratio to its own row's
mean so the shading and the line survive and only the colour underneath moves.
On 43ca8a03:

```
render      82 115  45  56  42 112
repainted   82  85 100  88  62  48    falling
```

Not promoted to `scripts/` yet — the hem is a fraction of the frame height
(0.55) rather than anything found in the image, so it is one pose's number and
not a tool's.

## The legs were never in the frame (2026-08-18)

Looked at one 20%-tall crop of 43ca8a03 after eleven arms of measuring, and the
picture answered two questions the numbers had been circling:

- **`stand` cropped at mid-calf.** No ankle, no foot, no toe. The pose was
  written with a warning that this was the risk and the warning was never
  checked, so every gradient arm above was arguing about the bottom of a leg
  that was not in the picture. The post-process ramp was worse than wrong: it
  ran from a fraction of the frame height to the frame's bottom edge, i.e. from
  nowhere in particular to a place the foot did not reach.
- **A rabbit is drawn into the backdrop.** The intruder this repo has fought
  before, on a pose nobody had inspected yet.

### Framing

Measured as "does the figure mask stop before the canvas does", which is a
number and not a look:

```
1024x1536  full body            ends at the last row          cropped
1024x1536  (full body:1.45)     ends at the last row          cropped
896x1728   full body            ends at the last row          cropped
832x1856   full body            ends at the last row, wide    badly cropped
896x1728   (full body:1.45)     ends 24px up, tapering        fits -- but no feet
```

896x1728 is 1.55M pixels against 1024x1536's 1.57M, so it is inside the
docstring's ceiling. `prone` already established that the ceiling is a pixel
count and not an aspect.

### The stumps, and the tag that fixed two things at once

At the canvas that fit, the legs ended in rounded stumps. **Nothing in this
prompt has ever named a shoe** — fifteen poses and no footwear tag — so there
was no foot to draw. `(black footwear:1.35)` draws one, and it is black, which
is where the leg was supposed to end anyway. Black sneakers with pink laces,
whole and inside the frame.

That leaves `stand` at ten tags after `(solo:1.5)` against the eight this file
keeps quoting. The budget was measured on a seated pose in a frame that fit; a
standing figure spends two tags just staying in the picture. The footwear is an
**addition to the costume** and has not been checked against the official
design — if the shoes are wrong it has to be replaced, not deleted, because
deleting it brings the stumps back.

### And then the gradient, in post, with anchors that exist

`.local/leg_gradient.py` now finds the hem (where the figure narrows out of the
dress into two legs) and the ankle (the narrowest row above the flare of the
shoes), and ramps purple->black between them. On t2: hem y=981, ankle y=1512,
108k pixels repainted, shoes untouched because the ramp arrives at their colour.

One bug worth keeping: the first version excluded "skin" by brightness and hue,
and the pale band just above the ankle — the exact part the ramp exists to
darken — is pale and slightly warm. It was masked out and survived as a pink
cuff above black shoes. Between the hem and the shoes she is wearing the
garment; there is no skin to protect.

## The gradient direction is ABANDONED (2026-08-18)

「グラデーションの向き直らないね。諦めます」.

Do not retry this. The record of what was tried, so that a later session does
not spend the afternoon again:

- **Eleven prompt arms.** A second colour name; the order of the two names; the
  weights between them; `(two-tone legwear:1.4)` lifted out of the negative; the
  word `gradient` removed entirely; and four framing/canvas arms on top. Not one
  of them put the black at the bottom of the leg.
- **Post-processing works and was still not accepted.** `.local/leg_gradient.py`
  ramps the legwear purple->black between the hem and the ankle and the
  measurement flips cleanly. It is kept in `.local/` and is not promoted.
- The likeliest mechanism is written up above: her dress is purple, so a purple
  thigh under a purple hem has no boundary, and the model puts the black where
  the contrast is needed — at the top.

The leg ships as the model draws it: dark at the thigh, pale at the ankle, and
then a black shoe under it.

## `stand` is adopted from a two-figure render (2026-08-18)

Picked: **2a2fc594**, left figure. That render is the committed `stand` block
plus `(wide shot:1.3)` at 1024x1536 — verified byte-identical against its own
history rather than assumed, which is a habit this file had to learn today.

It draws **two figures**, side by side, and the left one is the keeper. That is
normally a defect here and it is being accepted rather than fixed, because
`wide shot` is also what pulled the camera back far enough to get the whole
figure and the shoes into a 1024x1536 frame. `.local/split_left.py` finds the
trough in the column profile between the two bodies and cuts there, at full
resolution.

The pose that arrived with it is not the one that was settled: hands clasped
LOW rather than at the chest, head down, no visible arch. `(wide shot:1.3)`
rewrote the composition. The tags that were measured into the block are still
in it and are no longer describing what comes out — worth knowing before
reading the block as a description of the picture.

### The shoes

「靴に柄はいらない。うさぎ耳っぽいスニーカーは同意」. The sneakers carry a pink
butterfly decal on the outer side; the ear-like high collar is wanted and has to
survive whatever removes the decal. Three arms, same seed:

```
u1  + (logo:1.4), (print:1.35) in the negative      decal gone, magenta sole
u2  + (butterfly:1.5) as well                       decal gone, black with pink trim
u3  (black footwear:1.35) -> (plain black sneakers:1.4)   decal gone, white midsole
```

All three remove the pattern, so the choice is the sole, not the guard.

### Only one of her (2026-08-18)

「左だけ生成できる？」 Yes, and not by any guard.

```
v1  + (2girls:1.6), (multiple girls:1.6), (duplicate:1.55), (another person:1.5)
    the set `lap` uses, naming the second PERSON            two figures
v2  + (character sheet:1.4), (multiple views:1.4), reference sheet, turnaround
    the set `nape` uses, naming the LAYOUT, in front of NEGATIVE   two figures
v3  no guard at all, canvas 1024 -> 768 wide               ONE figure
```

Then four seeds at 768x1536 — 1886970040, 555666777, 111222333, 2557902837 —
and all four drew one figure. It is the canvas, not the seed, and not anything
lexical: **give the frame room beside her and the model puts someone in it.**
Neither guard set moved it at any of the weights they already carry elsewhere.

The cost is that the narrower canvas redraws the shoe. 768 gave a low-top, and
asking for the collar back by name (`(black high-top sneakers:1.4)`) gave a
third shoe again — white-soled, red-accented, not the ear-like pair that was
agreed to. The approved shoe came with the 1024 frame.

So both frames are live and the choice is about the shoes, not about the
composition:

- **1024x1536** — the adopted render (6217154d). Two figures; the left one is
  the keeper and `.local/split_left.py` cuts it at full resolution.
- **768x1536** — one figure straight out of the sampler, different shoes.

Committed: 1024x1536, `(wide shot:1.3)` in the block, and the decal guards in a
`stand` branch of `_negative_base`. `positive`, `negative` and the canvas all
verified byte-identical against 6217154d's own history.

Also seen in the four-seed check, and not chased: 555666777 puts the rabbit hood
UP, which the recipe rules out globally, and 111222333 and 2557902837 both drew
backdrop intruders. 1886970040 is the seed this pose has been settled on.

## Crops are banned while the prompt is being tuned (2026-08-18)

「crop系はプロンプト調整段階ではメリットがないので禁止したい」. Written into
CLAUDE.md as a standing rule, and `.local/split_left.py` is deleted rather than
promoted.

The reason is visible in this file's own last two entries. A two-figure render
had a good left half, and cutting it out would have shipped a `stand` that never
draws one figure while every later arm got judged against a picture the recipe
cannot produce. **A crop hides the unsolved defect inside an accepted-looking
result.** What actually solved it was the canvas.

`recolor_bg.py` is not the same thing and is unaffected: it sets a value the
prompt cannot hold. Removing part of the picture is not that.

## The shoe, at the canvas that draws one of her (2026-08-18)

768x1536 is now the committed frame, so the approved pair from the 1024 render
is gone and the shoe had to be found again. Four arms, 1886970040, all with
`(white footwear:1.45), (red footwear:1.4)` in the negative because a pale sole
arrived uninvited in every earlier attempt:

```
x1  (black high-top sneakers:1.4)                   high-top, white sole anyway
x2  (black footwear:1.35), (high tops:1.35)         high-top, black to the ground  <- kept
x3  (black high-top sneakers:1.4), (black sole:1.35)  white midsole AND a red flash
x4  (black sneakers:1.4)                            low-top, pale sole
```

`(black sole:1.35)` in the positive is the interesting failure: describing the
sole made it worse, adding a red flash the other arms did not have. The guard
route worked and the description did not, which is the opposite of this file's
usual preference and is recorded for that reason.

Kept: **x2**, prompt a5c494ef. `positive`, `negative` and the canvas verified
byte-identical against its own history.

The sole guards sit AFTER the legwear ban, not before it, because that is the
order the picked render was drawn in — `negative()` appends them, rather than
`_negative_base` returning them. Token order has already been found to matter
here, so the tail is reproduced rather than rebuilt.

That is five stand-only guards. The rule they look like they are breaking --
never stack guards -- is about guards that all point at ONE defect, which is
what wrecked the palette here twice. These point at three: a decal, a logo and
a colour.

## The ears were already off, and the dress was missing its trim (2026-08-18)

「3da541d2 ベースで頭から耳を外す。ワンピースを正しく見直す」.

### The ears

**Nothing was needed.** Rendering the committed block unchanged at 3da541d2's
own seed (555666777) drew no ears standing on her head. The hood ears in that
render belonged to the configuration it was made with — it predates
`(high tops:1.35)` and the sole guards — and adding those changed the picture
enough to drop them. Two arms were queued for a defect that had already gone:
`(rabbit ears:1.5), (animal ears:1.45)` in the negative, and `(hood down:1.25)`
raised to 1.55. Neither is needed and neither is kept.

The lesson is the cheap one: **render the control.** Four arms went out against
a render made two prompt-changes ago, and the control would have cost one.

### The dress

Three things this file had already measured and never applied. Two are kept:

- **`(frills:0.85)` -> 1.25, globally.** "Weighted down rather than deleted" was
  the stated intent and 0.85 did not deliver it — below 1 in a prompt where
  everything else is 1.3+ has meant *absent* four times here now. `boss` had
  spliced 1.25 for a session and got the frilled collar, the ribbon ties and the
  beaded cords back at no measurable cost, so the value was proven and simply
  never promoted. Measured again on 555666777 and 1886970040: frilled hem back,
  the coat's cord shows its pink bead, backdrop clean.
- **`(buttons:1.4)` in `stand`'s negative, in front.** Her dress has no buttons
  and nothing asks for any; they arrive from the cardigan being read as a shirt.
  `boss` established one guard is the whole fix, and this is the same guard in
  the same position.

Dropped: **`(criss-cross halter:1.45)`**. It does draw the crossed chest straps
of the official design — visibly, on 555666777 — and it brought backdrop
intruders on **both** seeds tried. That matches what `sip` measured a session
ago: naming a halter globally is destructive. It stays a `boss`/`nape`
splice.

Costume fingerprint `a67b105340c90b52` -> **`47b0d089d5a5ec77`**. Every pose
wears the frills now.

And the splice this broke, exactly as CLAUDE.md warns: `boss` replaced
`(frills:0.85)` with `(frills:1.25)`, and with the global value raised its
needle was gone, so the replacement silently did nothing. `costume_check`
caught it as a declared-but-absent exception rather than a render defect, which
is the entire reason that file exists. The splice and its `EXCEPTIONS` entry are
both deleted.

Verified byte-identical against 5949e5e4's own history: positive, negative and
canvas.

## 「解像度を上げれば手書き感が上がる」は第2パスでは逆 (2026-08-18)

The expectation was that a bigger render would look more drawn. It looked
softer instead, and the measurement says that is what the second pass does.

`scripts/handfeel.py`, interior marks per 1000 figure-height, `stand` on
1886970040:

```
first pass          768x1536   40.6      stroke 2.619 per 1000px
+ pass at 0.60      768x1536   34.7      2.330      <- same canvas: the pass SMOOTHS
+ pass at 0.60      1024x2048  37.8      1.745
+ pass at 0.65      1024x2048  39.2      1.821
+ pass at 0.70      1024x2048  41.2      1.668
+ pass at 0.65      1536x3072  64.6      1.230
```

The 1536-canvas pair is the only strictly comparable one — handfeel does not
survive a change of canvas — and it is the whole story: **40.6 -> 34.7.** The
pass removed marks. The 2048 numbers rise with denoise monotonically, which is
the one dial that works here, but they are rising from a floor the pass itself
created.

Why the upscale did not save it: marks come back when an upscale splits strokes
that used to share pixels, and this base is 1536 on its long side, so
`--hires 2048` is a **1.33x** upscale. There is very little splitting to do.
The prone lineage got its gain from 1024 -> 2048, twice that.

Native-pixel crops of the head agree with the numbers and with the eye: bigger
is smoother, with gradient shading and a finer line, which is the
「clean and vivid」 direction this project treats as a regression.

**`--hires 1536` on this pose is not an upscale at all.** The base long side is
already 1536, so the scale is 1.0 and the pass is a same-size redraw. That is
the arm that measured 34.7.

### The first pass is the only pass that draws, and its canvas is a composition

So: draw it bigger to begin with. Two arms, same prompt and seed:

```
832x1664 = 1.38M   44.2 marks   stroke 2.330
896x1792 = 1.61M   33.1 marks   stroke 2.024
```

But neither is "the same picture, bigger". 832x1664 reframes to a near-portrait
with the coat off her shoulders; 896x1792 moves the hands and the crop. **The
first-pass canvas is a composition variable in this recipe, not a resolution
knob** — which is already written here as "the canvas decides the composition,
including how many people are in it", and applies just as much when the count
stays at one.

### `scripts/line_overlay.py` cannot run on this worker

The repo's own "最後に線を引く" tool is dead against this box: none of the three
preprocessors it names — `AnimeLineArtPreprocessor`,
`Manga2Anime_LineArt_Preprocessor`, `LineartStandardPreprocessor` — is
installed. 886 nodes, no lineart among them.

**`/object_info/<name>` returns HTTP 200 with a body of `{}` for a node that
does not exist.** It was checked that way first and the check passed for all
three. Only `/prompt` says so, with `missing_node_type`. Check the body length,
not the status.

Done locally instead (`.local/line_last.py`, opencv, nothing re-diffused): a
pixel divided by a blurred copy of its neighbourhood is below 1 exactly where it
is darker than its surroundings, and multiplying that back darkens line and
interior hatching without touching flat fills. On the 2048 render: 39.2 ->
41.2 -> 46.6 at factor 0.35 / 0.60 / 0.85. It works as a dial, and by 0.85 the
face carries a grey cast and the picture reads grainy rather than drawn.

## `stand` settles its canvas and its proportions (2026-08-18)

**Canvas: 832x1664**, picked by eye over 768x1536 and 896x1792 (a71d4c57).
1.38M pixels, under the ceiling, and still narrow enough that nobody else fits
beside her — which is what the width is really carrying on this pose. All three
canvases frame her differently, so this was a composition choice and not a
resolution one.

**Proportions.** 「身長はそれで良い、だが上半身が少し長い。脚の長さに比重を
かけてほしい」. `.local/proportion.py` measures the share of figure height below
the hem — head top, hem and sole from the figure mask:

```
a71d4c57  the accepted render                        40.1%
c1  BODY + (long legs:1.35)                          55.7%   <- kept
c2  (petite:1.2) -> (long legs:1.35)                 55.1%
c3  (long torso:1.4) in the NEGATIVE                 38.9%
c4  the substitution at 1.45, plus the guard         57.0%
```

**Only the positive side of this axis is addressable, and that is now twice.**
`c3` names the defect directly in the negative and moves nothing; `prone` had
already found `(long legs:1.4)` in the negative did nothing to thighs that read
too long. Asking for the leg works, forbidding the torso does not.

Kept `c1` — added as a seventh tag rather than substituted into `(petite:1.2)`,
the slot that argues against it and the one `boss` swaps out for that reason.
The substitution measured within noise of the addition and was simply not the
one chosen.

Spliced into `stand`, not edited into `BODY`. Every other pose was settled
against the current block and would move under it, which is the same reason
`boss` and `prone` splice their own body changes.

**The measurement's limit, stated because the number looks stronger than it
is:** it is the share below the HEM, not below an anatomical hip. A dress that
rides up inflates it, and the dress did ride up in every arm that moved. The
figure is genuinely longer-legged; it is not 15 points longer-legged.

Verified byte-identical against 963bee1f: positive, negative, canvas.

## `seiza` was not what was wrong with `lap` — and the number that said it was, was read wrong (2026-08-19)

Six `lap` renders came back and the verdict was "どれも微妙". Rather than ask what
that meant, the line was measured, and `scripts/stroke_width.py` appeared to
answer at once:

    lap     (seiza)        6 seeds   median 3.00-4.00
    invite  (yokozuwari)   4 seeds   median 2.00   <- the settled, clean pose

Six of six off, four of four on, and `lap` carries `(seiza:1.25)` — the tag the
section above convicts of breaking the line, the mottling and the headcount all
at once, and which `invite`'s own comment says to keep out. It looked like the
same fix landing on only one of the two poses that were added in the same commit.

**It was not.** Swapping only the seat, three seeds each, changed nothing:

    lap, (seiza:1.25)          median 3-4    mean 3.83 - 5.41
    lap, (yokozuwari:1.25)     median 3-4    mean 4.32 - 5.24
    lap, no seat tag at all    median 4      mean 5.11
    invite, (yokozuwari:1.35)  median 2      mean 3.57 - 4.45

Two separate mistakes produced the false positive, and both are about the tool:

- **The median was read as if it were a measurement.** `stroke_width.py`'s own
  docstring says it "is an integer count and lands on 3 or 4 with nothing
  between, which is too coarse to compare two renders" and that the mean is what
  the normalised figure is built from. The means **overlap**:
  `lap-737373737` at 3.83 is *finer* than `invite-111222333` at 4.11. The clean
  3-4 / 2 split was quantisation drawing a line where the data has none.
- **1.91px is not a threshold this tool can be held to.** Every "1.91px" in this
  file predates `stroke_width.py` and was measured by hand — the tool exists
  because those numbers "can be re-checked" by nothing else. Under the tool, the
  known-good pose reads 2.00 median / 3.57-4.45 mean. Comparing a fresh number
  to the hand-measured constant is comparing two instruments.

So the difference between `lap` and `invite` is not the seat, and on this
evidence there may be no line difference at all — `cowboy shot` puts more figure
in the same canvas than `full body` does, and a bigger figure spends more pixels
per stroke. `norm` divides by the canvas long edge, which is identical here, so
it does not absorb that. **`stroke_width.py` cannot compare two framings**, the
same limitation `handfeel.py` carries about canvases.

This is the fifth image statistic in this repo to be believed and then withdrawn.
The pattern each time is the same: the number was consulted *instead of* asking
what the eye objected to. "微妙" was never established to mean the line.

`--pose lap` now says `(yokozuwari:1.25)` anyway, because
`ls-yz-lap-555666777` (8b51610f) is the render that was picked and that is what
drew it. `--pose lap --seed 555666777` reproduces it — canvas, positive and
negative all byte-identical against its own history entry. The seat is settled
by the pick, not by the argument that was made for it.

## `allnighter` — 徹夜明けの死んだ目 (2026-08-19)

「徹夜で目が死んでるゆかりさん」. A new pose, and it is a **head framing**, not a
body pose: the request is about the eyes, and at 1024x1536 the face is about a
hundred pixels tall. It is `portrait`'s block with the smug swapped out —

    (solo:1.5), (portrait:1.5), (head and shoulders:1.4), (close-up:1.2),
    (face focus:1.3), (empty eyes:1.45), (eyebags:1.4),
    (half-closed eyes:1.35), (expressionless:1.3)

at 1024x1024, the square `portrait` needed for the same reason.

Four choices worth writing down before any of it is judged:

- **`empty eyes` is the tag, because `dead eyes` is not one.** The danbooru
  vocabulary for an eye drawn without a highlight is `empty eyes`; it carries
  the whole idea and everything else here is supporting it.
- **`eyebags` is what makes it an all-nighter rather than a mood.** Without it
  the block describes someone bored.
- **NOT `(closed eyes)`.** `yawn` measured that at 1.35 and it drew a second
  figure on four seeds of four. It is also self-defeating: a closed eye cannot
  show that it is empty. `half-closed eyes` was already `portrait`'s at 1.3 and
  is raised to 1.35 for the droop.
- **No desk, no computer, no night.** SURFACE is `(simple background:1.3),
  (grey background:1.2)` and a scene argues with that contract. The state is
  carried on her face or it is not carried.

Nine tags where `portrait` has seven. The eight-tag ceiling recorded on `yawn`
is specifically about the legwear being pushed out of the prompt, and this crop
does not carry legwear — so it does not apply here.

**`HEAD_FRAMINGS` replaces four `pose == "portrait"` tests.** `portrait` was the
only cropped pose, so "is this the portrait" and "does this crop above the legs"
were the same question and the code asked the first one. They are now two
questions: `negative()` drops `LEGWEAR_BAN` and `positive()` drops `LEGWEAR`,
`BODY` (bar `pale skin`) and `THIN` for every member of the tuple. Adding a
head framing without adding it there would have shipped a close-up that names
pantyhose it cannot show.

Costume fingerprint unchanged (`47b0d089d5a5ec77`) — no shared block was
touched. `costume_check.py` carries `allnighter` with `portrait`'s one declared
exception, the same list for the same reason.

Queued as `yk-allnighter`, six sweep seeds:

    555666777   3bb10632    111222333   4aae869f    1886970040  c9ce7788
    737373737   a1d46a29    2557902837  b524eebf    3409564303  4c0051ef

**Unjudged at time of writing.** The open question is whether `empty eyes` and
`expressionless` together flatten the face past the point where it is still her
— FACE supplies `(tareme:1.3), (large eyes:1.3), (large iris:1.25)`, which are
arguing for the opposite, and `expressionless` is the tag to drop first if the
result reads as a doll rather than as exhausted.

## `allnighter` gets イーの口, and `expressionless` pays for it (2026-08-19)

「イーの口にして」. `(clenched teeth:1.45)` is the tag — teeth pulled back and
pressed together, which is how the 「い」 mouth shape is drawn. It went in as a
**swap for `(expressionless:1.3)`**, not as a tenth tag.

The swap is the point. A clenched grimace *is* an expression, so the two tags
were a straight contradiction, and leaving both in would have moved the argument
out of the recipe and into the sampler — where it gets settled per seed and
looks like instability rather than like a decision. `expressionless` was already
written down in the previous entry as the first tag to drop; the mouth is what
gave it a reason.

**Two tags come out of FACE here, not one.** Every earlier mouth change in this
file (`yawn`, `fall`) removes `closed mouth` and stops. This pose also removes
`small mouth`:

- `closed mouth` forbids the teeth, which is the whole request.
- `small mouth` forbids the width. It is the more dangerous of the two, because
  it is not a contradiction the model has to resolve — it is a *description of
  the same feature* as `clenched teeth`, at a comparable weight, and a
  description competes where a prohibition merely argues.

Declared in `costume_check.py` as `allnighter`'s second exception. Costume
fingerprint unchanged (`47b0d089d5a5ec77`).

Queued as `yk-allnighter-ii` on the same six sweep seeds as the first pass, so
the two are comparable seed by seed:

    555666777   b13aea42    111222333   d3ba3a6f    1886970040  9bedb658
    737373737   43a7b319    2557902837  1c343a54    3409564303  20856e8a

**Unjudged.** The thing to watch is whether `clenched teeth` drags the face
toward anger — it is a tag that lives mostly on rage and strain — when what is
wanted is exhaustion. `(empty eyes:1.45)` and `(eyebags:1.4)` are the two tags
holding it there, and if it reads as furious rather than fried, the lever is the
mouth's weight and not theirs.

## The gap is a different tag, not a lower weight (2026-08-19)

「食いしばらず少し歯が空いてる感じ？」. `(clenched teeth:1.45)` is out — deleted,
not eased — and the mouth is now:

    (teeth:1.45), (parted lips:1.3)

**A weight cannot fix a tag that means the opposite of the request.** `clenched`
*is* the teeth being pressed together; there is no value of it that leaves a
gap. Lowering it to 1.2 and adding `parted lips` beside it would have rebuilt
exactly the contradiction that `(expressionless:1.3)` was deleted for one commit
earlier — two tags arguing inside the prompt, settled per seed by the sampler,
and read afterwards as instability rather than as an undecided recipe. This is
the second time in two changes that the fix was a deletion.

Which half carries what:

- **`teeth` is load-bearing.** It is what draws both rows and what supplies the
  horizontal pull that made this an 「イー」 mouth in the first place.
- **`parted lips` is weighted below it deliberately.** On danbooru it is a soft,
  closed, mostly teethless look; it is here only to open the bite, and at equal
  weight it would take the teeth back out.

`clenched teeth` also had a cost that is worth recording even though it is being
dropped for a different reason: it lives on rage and strain, and it pulled the
face toward angry when the target is fried. Ten tags now where `portrait` has
seven; the `yawn` ceiling is about legwear and does not reach this crop.

Queued as `yk-allnighter-iii`, same six seeds again — three passes now
comparable seed by seed:

    555666777   7e83d4cc    111222333   b5ab47d4    1886970040  4a4971c0
    737373737   c1b7906d    2557902837  dc0d01e8    3409564303  8e8aabaf

**Unjudged.** The risk this time is the opposite of last time: with nothing
pulling the mouth wide except `teeth`, it may come back as an ordinary small
open mouth — an 「あ」 rather than an 「イー」. If the width is gone, the lever is
`(grin:1.3)`, which is danbooru's horizontal teeth-showing mouth; the reason it
is not in already is that it means smiling, and the eyes here are dead.

## The denoise direction reverses at 2x — a correction to the 8/18 hires entry (2026-08-19)

`c1b7906d` (`allnighter`, seed 737373737) redrawn at 2048, two arms. Its base is
1024x1024, so **`--hires 2048` here is a 2.0x upscale** — not the 1.33x that
「解像度を上げれば手書き感が上がる」は第2パスでは逆 (2026-08-18) was measured on.
That entry's own explanation says why the distinction matters: marks come back
when an upscale splits strokes that used to share pixels, and at 1.33x there is
very little splitting to do. This is a different regime, so it was worth a test
rather than a citation.

`handfeel.py`, the two 2048 arms only — same canvas, so comparable to each other
and to nothing else here:

```
+ pass at 0.60   2048x2048   411.5 marks per 1k fig-h
+ pass at 0.70   2048x2048   156.9
```

**That is the opposite direction.** On `stand` the marks rose monotonically with
denoise — 37.8 / 39.2 / 41.2 at 0.60 / 0.65 / 0.70 — and it was written down
there as "the one dial that works here". At 2x on this pose the same dial runs
backwards and 0.70 costs two thirds of the marks. Neither entry is wrong; the
earlier one is narrower than it sounds. **Do not carry a denoise recommendation
across an upscale ratio.**

`stroke_width.py`, same three renders, and this is the half that does not
improve:

```
                        mean px    per 1000px
1024 base                  4.43        4.324
+ pass at 0.60 -> 2048     4.16        2.029
+ pass at 0.70 -> 2048     3.55        1.736
```

The absolute stroke barely moves while the figure doubles, so the line ends up
**half as thick relative to her** — which is exactly the "finer line, therefore
smoother" signature the 8/18 entry called a regression. On this measure the 2x
upscale behaves like the 1.33x one. So the two statistics disagree: interior
marks say 0.60 at 2048 is rich, stroke says the line reads finer than the base.

**The first pass is byte-identical, verified rather than assumed.** Compared
node by node against `c1b7906d`'s own history entry: checkpoint, both CLIP
encodes, `EmptyLatentImage` and `KSampler` 3 (seed, steps, cfg, denoise) all
match, and the only differences are the `VAEDecode` rewired to the second
sampler and the save prefix. The docstring's claim that `--hires` does not
change the first pass holds for this pose.

Prompt ids: 0.60 `2bd865d8`, 0.70 `38178dcf`.

**Not judged by these numbers.** This repo has now believed and withdrawn five
image statistics, and two of the three here point opposite ways. Both arms are
posted; the eye picks. Recorded so that the next session does not re-run the
sweep, and does not quote the 8/18 denoise direction at a 2x upscale.

## The teeth were the anger, not the tag that asked for them (2026-08-19)

「ちょっと口がキレてるね・・・放心状態感で口が空いてる方が良さそう」. The mouth is now
`(open mouth:1.35)` and there are **no teeth in the prompt at all**.

This is a correction to the entry above it. When `(clenched teeth:1.45)` was
dropped, the anger was blamed on that tag specifically — "it lives on rage and
strain" — and the replacement kept the teeth under a different name,
`(teeth:1.45), (parted lips:1.3)`. That came back cross as well. **Bared teeth
carry the strain whichever tag asks for them**, and no weight on the tag beside
them undoes it. The right read of the first failure was the feature, not the
vocabulary; it was diagnosed one level too shallow and cost a round.

`parted lips` goes with the teeth rather than staying on as the gap. It
describes the mouth and so does `open mouth`, and this pose has now spent two
rounds on two tags arguing over one feature.

**Weighted 1.35, above `fall`'s 1.30, on purpose.** Both existing open mouths in
this file have something driving them — `(yawning:1.4)` and `(surprised:1.35)`.
放心 is the *absence* of an expression, so there is no engine behind it and the
weight is the entire engine. The asymmetry decides it: too wide is visible and
easy to walk back, a mouth that never opens loses the request outright.

**`(expressionless:1.3)` is deliberately not restored**, even though it names
exactly what 放心状態 is. On danbooru it sits on closed neutral mouths, so
against `open mouth` it would be a third description of the same feature — the
mistake this pose keeps making. The vacancy is carried by `(empty eyes:1.45)`
and by there being no smile or anger tag at all, which is what went wrong when
there was one.

**FACE is back to a one-tag departure.** `small mouth` was removed for the
「イー」 width; that mouth is gone, and a 放心 mouth is a small ぽかん one, so the
shared block is left alone and `allnighter` now removes only `closed mouth` —
the same departure `yawn` and `fall` make. Nine tags again.

Queued as `yk-allnighter-iv`, the same six seeds, fourth pass:

    555666777   3a321b69    111222333   c3580a09    1886970040  5ad025d2
    737373737   c575fc46    2557902837  38773ce2    3409564303  7f3c8e64

The 2048 hires question is unaffected — it replays whatever the first pass drew,
and the finding above (0.60 over 0.70 at a 2x upscale) is about the pass, not
about this mouth.

## `allnighter_full` — seiza, and 2 of 6 came back with two of her (2026-08-19)

「c575fc46 全身、正座」. A new pose rather than a size on `allnighter`: that one
is a 1024x1024 head framing, and this file already records that the first-pass
canvas is a composition variable and not a resolution knob. The picked close-up
cannot be enlarged into a full body; it has to be re-picked.

Block, at 1024x1536 — the canvas every seated full body here uses:

    (solo:1.5), (seiza:1.35), (empty eyes:1.45), (eyebags:1.4),
    (half-closed eyes:1.35), (open mouth:1.35), full body

`seiza` was asked for by name, and this file convicts it twice — 「One tag,
`seiza`, was behind the drifting art style」 has it taking the line, the backdrop
flatness and the headcount together. **Most of that was withdrawn earlier today**
(swapping only the seat in `lap` moved nothing; the stroke number that convicted
it was read off the wrong statistic). What was never withdrawn is the headcount:
one seed of that swap drew two of her, and no measurement since had addressed it.

So the sweep was counted. `.local/_solo.py`, column blocks in the figure mask:

```
555666777    2 bodies     111222333   ONE      1886970040  ONE
737373737    ONE          2557902837  2 bodies  3409564303  ONE
```

**2 of 6.** With `(solo:1.5)` leading the block, as everywhere in this file.
That is the un-withdrawn half of the old conviction showing up on its own, in a
pose that shares nothing with `invite` but the seat.

Read it as a flag, not a verdict — `_solo.py` counts column blocks, so a raised
arm or a detached object registers the same as a second girl, and both flagged
seeds are also marked CROPPED, where the measure is least trustworthy. This repo
has withdrawn five image statistics. But the direction agrees with the one
observation about `seiza` that survived, which is worth more than the number is.

The pose is left in the file. If it is picked up again, the seat is the first
suspect and `yokozuwari` — seven clean seeds — is the swap.

## `flop` — the couch, on `prone`'s geometry (2026-08-19)

「ソファーにダイブしてる姿の方がいいな」, which is a better idea than the seiza
anyway: 徹夜 is a body that stopped, not one that knelt.

    (solo:1.5), (couch:1.4), (lying:1.45), (on stomach:1.5),
    (from above:1.35), (empty eyes:1.45), (eyebags:1.4),
    (half-closed eyes:1.35), (open mouth:1.35), full body

at 1536x1024. Everything structural is `prone`'s and unmodified — the lying
triple, the landscape canvas, and the measurements behind that canvas are in its
own note. What comes OUT of `prone` is `chin rest` and `feet up`: both prop her
up and arrange her, and this is someone who stopped. `couch` is the danbooru
spelling; `sofa` is an alias to it.

**BODY's easing is transferred, not measured.** `prone` runs `(wide hips:1.3)`
and `(thick thighs:1.35)` down to 1.0 / 1.05 because a body seen from above and
behind is foreshortened and those two tags land on the largest thing in frame —
the 「めちゃ下半身太ってしまった…」 entry. `flop` has `lying`, `on stomach` and
`from above` all from `prone`, so it is the same geometry and it gets the same
splice. The alternative was to ship a pose knowing the complaint it was written
for is likely to recur. Declared in `costume_check.py` as such.

**SURFACE is deliberately NOT spliced.** `(simple background:1.3),
(grey background:1.2)` is a direct argument against drawing furniture, and the
temptation was to pre-emptively cut it. A couch on a flat grey field is coherent
with this recipe's look rather than a compromise with it, and the flat backdrop
*is* the look. If the couch does not draw, that is when `simple background`
comes out — one lever held in reserve, rather than changing the costume contract
before anything has failed.

Queued as `yk-flop`:

    555666777   08fb27ab    111222333   773e59fe    1886970040  dd78d85d
    737373737   8f46b2d1    2557902837  e939265d    3409564303  71d83693

## `flop` gets the skid, and it gets it without a dive tag (2026-08-19)

「ズサーッとダイブしている感じ」. The pose now reads:

    (solo:1.5), (couch:1.4), (lying:1.45), (on stomach:1.5),
    (outstretched arms:1.3), (motion lines:1.3), (empty eyes:1.45),
    (eyebags:1.4), (half-closed eyes:1.35), (open mouth:1.35), full body

**There is no dive tag, and that is the point.** `diving` or `falling` on top of
`(lying:1.45), (on stomach:1.5)` is precisely the construction `fall` already
paid for: tripping + falling + fallen down together drew two figures on three
seeds of three, one still upright and one already on the ground, because they
are three *moments* and the model resolves a set of moments by giving each one a
body. Mid-air and landed is two moments.

So one moment was chosen, and 「ズサーッ」 picks it out: the skid, not the leap —
she is already down and still moving. The motion is then carried the way `fall`
carries it, by comic convention rather than by a second moment:
`(motion lines:1.3)`, which that pose records as surviving flat colour, and
`(outstretched arms:1.3)`, the same tag at the same weight it uses.

`(from above:1.35)` came out. It was borrowed from `prone` for legibility rather
than chosen, and a top-down camera is the one view that flattens horizontal
momentum — it worked against the request.

**And the BODY easing came out with it.** One entry above, `flop` was given
`prone`'s `(wide hips:1.0)`, `(thick thighs:1.05)` on an explicitly geometric
argument: a body seen from above and from behind is foreshortened, so those tags
land on the largest thing in frame. Removing `from above` removed the geometry
that argument rested on, so the splice went back. A splice justified by a
geometry is not justified once the geometry leaves, and leaving it would have
put an unexplained deviation from BODY in the file for the next session to
reconstruct. `costume_check.py` is back to one declared exception for this pose.

Headcount, `.local/_solo.py`, both sweeps:

```
yk-flop   (static, from above)      6 of 6 ONE
yk-flop2  (skid, motion lines)      6 of 6 ONE
```

The trap was avoided by construction rather than survived by luck, but it is
worth having the number: `seiza` produced 2 of 6 two-body renders earlier today
on the same recipe and the same seeds, so the measure does report a problem when
there is one.

One thing to watch that is not the headcount: **the figure reaches the frame
edge on 5 of 6 static and 4 of 6 skid renders.** `prone` chose 1536x1024 partly
because it was the canvas that kept "the whole figure, outline intact" — the
die-cut white outline is part of the approved look and it breaks where the body
is cut by the frame. A couch takes room that `prone` had to itself. Not acted
on: for a body sliding across a couch, running out of frame may be exactly
right, and this is the user's call and not a statistic's.

    yk-flop2   555666777  f13bfa75   111222333  2cc03958   1886970040 be686786
               737373737  be70eaa8   2557902837 8fdc6d41   3409564303 8094e719

## The face goes down, and the face block goes with it (2026-08-19)

「顔も伏せてほぼ見えないくらいがいい」.

    (solo:1.5), (couch:1.4), (lying:1.45), (on stomach:1.5),
    (face down:1.5), (outstretched arms:1.3), (motion lines:1.3), full body

Eight tags, down from eleven. **`(empty eyes:1.45)`, `(eyebags:1.4)`,
`(half-closed eyes:1.35)` and `(open mouth:1.35)` are all deleted.**

This pose began the session as 「徹夜で目が死んでる」 and has arrived somewhere the
eyes are not visible, so those four tags now name a feature that is out of
frame. That is the mistake `portrait` exists to avoid, and this file already
records the cost in one line: naming what is out of frame is what invites it
back in. Four tags asking for eyes is the strongest available argument *against*
burying the face — keeping them out of loyalty to where the pose started would
have been keeping the one thing most likely to defeat the request.

**The exhaustion is the body's job now**, carried by the face being down, the
arms thrown ahead and the skid. If it stops reading, the lever is a body tag.
Adding a face tag back would be undoing this on purpose.

`looking at viewer` comes out of FACE, which is `nape`'s departure and `nape`'s
reason word for word: turned away from the camera, an instruction to face it has
no referent and either argues with the pose or spins her back around. `closed
mouth` stays, so the open-mouth exception is retired and `flop` is back to one
declared change.

`hair over face` is the reserve lever if `(face down:1.5)` does not bury it, and
is deliberately held back: it would be a second tag arguing about one feature —
this session's recurring failure — and it also rewrites the hairstyle CHARACTER
is holding.

### `_solo.py` said two bodies; a second measurement said furniture

Headcount on the sweep flagged 1886970040. Rather than believe it or discard it,
the blocks were measured (`.local/_blocks.py`, new — width, area and vertical
extent per column block, which is what tells a flung arm from a person):

```
1886970040   block 1   width 84.8%   area 92.9%   vertical extent 90.6%
             block 2   width 10.3%   area  6.9%   vertical extent 77.7%
737373737    block 1   width 88.8%   area 99.7%   vertical extent 90.1%   (one block)
```

The second block is 158px wide and 796px tall — **a 1:5 aspect ratio**, far too
narrow for a standing figure, which at that height would be two to three times
as wide. On a pose that now contains furniture by request, a tall narrow object
at the frame edge is much more likely the couch's back or arm than a person.

Reported as probable furniture, not proven. But this is the sixth time an image
statistic in this file has said something wrong, and it is the first time the
answer was to **measure one level deeper instead of choosing whether to believe
it**. `_solo.py` counts column blocks and cannot distinguish what fills them;
that is a fixable gap in the tool, not a reason to stop counting.

    yk-flop3   555666777  231cbd94   111222333  f14da3ad   1886970040 2f4e8e52
               737373737  fe7a7e59   2557902837 46781917   3409564303 7f96f8f1

## CORRECTION: `seiza` did not draw two of her, and `_solo.py` cannot count (2026-08-19)

**The entry 「`allnighter_full` — seiza, and 2 of 6 came back with two of her」
above is wrong.** Both flagged renders are one girl. Characterised with
`_blocks.py`:

```
yk-anf 555666777    block 1  98.6% of figure      block 2  1px wide, 0.0%
yk-anf 2557902837   block 1  99.7% of figure      block 2  1px wide, 0.0%
```

A one-pixel sliver at the frame edge, counted as a body. The finding was written
up as supporting the one part of this file's case against `seiza` that had
survived an earlier retraction — so a bad number was used to prop up a
conviction, on the same day the original conviction was withdrawn for being
built on a misread statistic. That is the sixth and seventh time.

It surfaced because the next sweep was absurd rather than merely plausible.
`flop` without the couch reported **four bodies on one seed and six on another**,
and nobody believes six. Measuring those blocks showed 1-4px slivers holding
0.0-1.3% of the figure — `motion lines`, which is a comic convention drawn as
separate marks on the backdrop *by definition*. `_solo.py` could never have
counted a pose that carries them.

The lesson is not "distrust the number". It is that **the flagged case was never
opened**. `_blocks.py` took one call and would have caught this at the time; the
2-of-6 was reported instead because it agreed with something already believed. A
statistic that confirms a prior is exactly the one to characterise.

### `scripts/headcount.py`

`_solo.py` is replaced rather than patched in place, and promoted out of
`.local/` because three false positives in one session make it load-bearing. A
block must hold at least `--min-share` (default 2%) of the figure's pixels
before it counts as a person — area, not width, because a lying figure is wide
and short and a standing one is narrow and tall. 2% is far under any real second
figure and far over every false positive seen here. `--detail` prints every
block with its share, so the next flag can be characterised in the same call
that raises it.

Re-counted with it: the seiza sweep is 6 of 6 one girl, and so is `flop`.

## `flop` loses the couch and gets its eyes back (2026-08-19)

「46781917 ソファーを外して死んだ目に」.

    (solo:1.5), (lying:1.45), (on stomach:1.5), (outstretched arms:1.3),
    (motion lines:1.3), (empty eyes:1.45), (eyebags:1.4),
    (half-closed eyes:1.35), (open mouth:1.35), full body

`(couch:1.4)` and `(face down:1.5)` out; the four face tags deleted one commit
ago are back at the weights they were settled on, and `looking at viewer`
returns to FACE with them.

**`(open mouth:1.35)` came back although only the eyes were named.** It was
never rejected — it was dropped as a consequence of burying the face, and
放心状態で口が空いてる was asked for and approved earlier in the same session.
Restoring the eyes alone would have silently kept half of a change that had one
cause.

**`(from above:1.35)` and `chin rest` stay out.** They are what `prone` uses to
keep a face legible while she is on her stomach, so the temptation was strong.
But 46781917 was drawn without them and both are composition tags: reaching for
one to solve a face problem hands back a different picture than the one that was
picked. Three eye tags and `looking at viewer` are the argument for the head
instead. If it stays down, those two are the known levers and the cost of either
is a re-pick.

With the couch gone SURFACE is uncontested again, and she is skidding across the
same flat ground `prone` lies on. BODY is untouched — the hip/thigh easing
belongs to `from above`, which is still absent.

**This is not 46781917 at a new setting.** Removing the couch changes the first
pass, and the first-pass canvas and contents are where composition is decided;
seed 2557902837 (`fcb4c377`) is the same seed drawing a new picture, not the
picked one with furniture erased.

    yk-flop4   555666777  c81b0716   111222333  33bfa9f2   1886970040 6aae4cec
               737373737  b3ff7b42   2557902837 fcb4c377   3409564303 3a7c94c5

6 of 6 one girl, `scripts/headcount.py`.

## `flop` puts the face back down, and one seed is probably two of her (2026-08-19)

「顔見えなくていいよ。床に埋まってて」.

    (solo:1.5), (lying:1.45), (on stomach:1.5), (face down:1.5),
    (outstretched arms:1.3), (motion lines:1.3), full body

Seven tags. This is the previous face-down configuration composed with the
couchless one — a combination that had not been rendered before, since the face
went down while the couch was still in and came up when it left.

**The face has now moved twice on this axis, so both ends are written into the
pose's comment** rather than only the current one. The switch is exactly two
edits, and nothing else travels with it:

- down: `(face down:1.5)` in, no eye or mouth tags, `looking at viewer` out of
  FACE (`nape`'s departure, `nape`'s reason)
- up: `(face down:1.5)` out; `(empty eyes:1.45)`, `(eyebags:1.4)`,
  `(half-closed eyes:1.35)`, `(open mouth:1.35)` in, `looking at viewer` back

What is **not** part of the switch is `(from above:1.35)` or `chin rest`. They
are how `prone` keeps a face legible on her stomach and they are the obvious
reach both times the head needed lifting — but they are composition tags, and
using one to solve a face problem hands back a different picture than the one
that was picked. Both times, the camera stayed where it was.

**「床に埋まって」 needs no floor tag.** With the couch gone she is already on the
ground, and `floor` or a room would import a scene arguing with SURFACE's
`(simple background:1.3), (grey background:1.2)` — the exact tension the couch
carried, now resolved. The burial is `(face down:1.5)` at `on stomach`'s weight.

### 555666777 is flagged, and this time the flag survives

`scripts/headcount.py --detail`, which now prints vertical extent because that
is the number that reads a block:

```
   555666777   block A   334px wide    8.32% of figure   61.7% of frame height
               block B  1030px wide   90.88% of figure   85.5% of frame height
               (six more blocks, all under 21px, filtered)
```

An outstretched arm on the ground is wide and flat — a small share of the
frame's height. This block is 334x632, tall for its width, which is
figure-shaped and not limb-shaped. **Treat 555666777 as probably two of her**,
with `(solo:1.5)` leading as always.

Not resolved, and not acted on. The render has not been opened — the tool
reports shape, not identity — and one seed of six is inside this recipe's normal
range; changing the prompt over it would be tuning against a statistic, which is
what the correction two entries up is about. The other five are clean.

`headcount.py` gained the vertical-extent column from this, so the discriminator
lives in the tool rather than in a `.local` script and one call now both raises
a flag and characterises it.

    yk-flop5   555666777  ad53cff6   111222333  b94537db   1886970040 1e189eea
               737373737  82378b10   2557902837 aeafb15d   3409564303 a2859012

## 2026-08-19 — `flop`: the face comes back up, and the skid comes out

「寝転んでるゆかりさん（寝不足放心状態）」. Two axes moved, and they are separate
axes, which is the point of writing this down rather than calling it one change.

**Face, third move.** The switch is the two edits the pose comment already
carried, run in the FACE UP direction: `(face down:1.5)` out, `(empty eyes:1.45),
(eyebags:1.4), (half-closed eyes:1.35), (open mouth:1.35)` in, `looking at
viewer` restored (i.e. `flop` out of the `nape` list in `positive()`, and into
`open_mouthed`). `(from above:1.35)` and `chin rest` were left alone again, which
is now three consecutive rounds where the head has moved and the camera has not.
`costume_check`'s `flop` entry flipped with it — `looking at viewer` removal out,
`closed mouth` removal in — and that entry is the thing that would catch a
half-applied switch, so it is worth keeping the two halves symmetric.

**Motion, first move.** `(motion lines:1.3)` came out. Motion lines are the tag
that says she is still moving; 放心状態 is already stopped. They were bought for
「ズサーッ」 and 「ズサーッ」 is not what is being asked for. The paragraph in the
pose that explains the dive is kept rather than deleted, because the trap it
records survives the request: a dive or falling tag over `(lying:1.45), (on
stomach:1.5)` is two moments, and the model settles two moments by drawing two
bodies. `(outstretched arms:1.3)` stayed — it arrived as the skid's arms, but
arms thrown out is also just what 寝転ぶ looks like. Second job, not the same job.

Nine tags:

    (solo:1.5), (lying:1.45), (on stomach:1.5), (outstretched arms:1.3),
    (empty eyes:1.45), (eyebags:1.4), (half-closed eyes:1.35),
    (open mouth:1.35), full body

### The one question the change could not answer from here, so it was rendered

On her stomach the face is only legible if the head is lifted, and the two tags
that lift it are the two the pose is on record as not reaching for. On her back
the face points at the camera for nothing. That is not decidable by argument, so
`.local/_onback.py` runs the same pose with `(on stomach:1.5)` → `(on back:1.5)`
and nothing else changed, on the same three seeds.

    yk-flop6    555666777 b89b6f5a   111222333 7a627150   1886970040 8b426633
    yk-onback   555666777 cf98c8aa   111222333 2ab57f7b   1886970040 c5d355af

`headcount.py --detail`, and this is a report of shapes, not of identities:

    yk-flop6   555666777    2 bodies   165px block, 9.2% of figure, 43.6% frame h
               111222333    ONE        99.85% in one block
               1886970040   ONE        99.97% in one block
    yk-onback  555666777    ONE        99.31% in one block
               111222333    ONE        99.59% in one block
               1886970040   ONE        99.98% in one block

**555666777 has now flagged twice in a row on this pose**, across a prompt change
that removed one tag and added four. Last round it was 334px / 8.3% / 61.7% of
frame height; this round 165px / 9.2% / 43.6%. The block shrank and dropped, so
it is not the same mass — but the seed producing a detached mass under two
different prompts is a property of the seed more than of the prompt, and that is
the useful thing to have written down. It is one of three either way, it has not
been opened, and nothing has been changed on account of it. Tuning a prompt
against a statistic is what the correction two entries up is about.

`on back` consolidating to 99.3–99.98% in a single block on all three seeds is
not evidence that it is the better picture — a body lying across a landscape
frame is one wide blob whether or not the face reads, and that is exactly the
kind of number this file has been wrong with before. The eye decides.

## 2026-08-19 — `flop` lands on her back, and borrows `stand`'s proportion lever

2ab57f7b — `yk-onback` 111222333 — is the picked render, so **`(on stomach:1.5)`
became `(on back:1.5)` in the recipe and `.local/_onback.py` is deleted.** The
probe existed for one question and the question is answered; leaving it in
`.local` is how a settled decision ends up living outside the blocks, which this
repo has already paid for once.

The pick also **couples two axes that were independent an hour ago.** The pose's
FACE DOWN / FACE UP switch was two edits either way; FACE DOWN now additionally
needs `(on stomach:1.5)` back, because there is no face-down on her back. Three
edits down, two up. Written into the pose so half a flip is not possible by
following the comment.

### 「ちょっと胴体が長い」 — the axis `stand` already settled

Same complaint as 「上半身が少し長い。脚の長さに比重をかけてほしい」, and it gets
the same answer: `(long legs:1.35)` added before `(pale skin:1.25)`, spliced into
the pose rather than edited into `BODY`, exactly as `stand` does it.

`costume_check` failed on it before it was declared, which is the check doing its
job — an added tag on a pose is a costume change and now says so.

**Not re-measured, and that is the deliberate part.** `.local/proportion.py` is
the metric that separated `stand`'s arms cleanly, and it reads rows: head at the
top, soles at the bottom, hem where the figure narrows into two legs. She is
lying across a landscape frame with her arms thrown out, so all three assumptions
are false, and a transposed version would be a new metric wearing a trusted one's
name. This file has enough of those. The lever transfers; the number does not.

The negative-side finding transfers too, and is repeated here because it is the
cheap thing to reach for: `(long torso:1.4)` in the NEGATIVE moved 40.1% to
38.9%, i.e. nothing, and `prone` found the same for `(long legs:1.4)` there.
**One side of this axis is addressable and it is the positive one.**

    yk-legs135  111222333 ce23f6c5   1886970040 00fac807   737373737 cd1b0a00
    yk-legs145  111222333 36f29df7   1886970040 bfb80973   737373737 49ef8830

Both weights are out because `stand` kept 1.35 over 1.45 on a difference it
called noise (55.7% vs 57.0%) — and that judgement was made with a metric that
does not run here, so there is nothing to call anything noise WITH. The eye picks
the weight instead of a number borrowed from another pose.

555666777 is off this sweep. It produced a detached figure-shaped mass on two
consecutive `flop` prompts, and a third of a three-seed proportion comparison is
too much to spend on a seed that may be drawing two people. 737373737 takes its
place, from the standard list. `headcount.py`: all six ONE.

## 2026-08-19 — `flop` takes 1.45, and gives the exhaustion back

49ef8830 — `yk-legs145` 737373737 — is the picked render, so the splice is
**`(long legs:1.45)`, one notch above `stand`'s 1.35.** Both were rendered
because the metric that called them noise-apart on `stand` does not run on a
figure lying across a landscape frame, and with nothing to call it noise with,
the eye picked the stronger one. The two poses may genuinely want different
weights: `stand` is measuring a vertical figure whose legs already run the full
height of the frame. `.local/_legs145.py` is deleted — the weight lives in the
recipe now.

### 「いつもの表情に戻して」 — and what that turned out to cost

The four tags came straight back out: `(empty eyes:1.45), (eyebags:1.4),
(half-closed eyes:1.35), (open mouth:1.35)`, plus `flop` out of `open_mouthed`
so `FACE` gets `closed mouth` back. Nothing else moved — not the body, not the
canvas, not the camera.

**That is the finding, and it is worth stating plainly: 徹夜 was entirely in four
expression tags.** The pose it was requested on has now shed the whole request
and kept its picture. Body, framing and camera never carried any of it, which is
why the expression lifted off cleanly instead of taking the composition with it.
The corollary is the useful half — an expression brief and a pose brief can be
tuned independently on this recipe, and eight rounds of work on the body were not
put at risk by dropping the face.

`flop` is five tags now, down from nine, and all four it lost were expression:

    (solo:1.5), (lying:1.45), (on back:1.5), (outstretched arms:1.3), full body

The small number is not the pose being under-specified.

**Three face states have now been live on this pose** — DEFAULT, 徹夜, FACE DOWN
— so all three are written into the pose comment rather than only the current
one, with their exact edits. FACE DOWN additionally carries `(on stomach:1.5)`
since the on-back pick coupled the two axes.

`costume_check` failed twice today on this pose, both times correctly and both
times on a half-applied face state: once on the added leg tag before it was
declared, once when the pose dropped `closed mouth` from its removals but the
declaration still claimed it. That file is doing exactly the job it was written
for — the churn in `flop`'s entry (a `looking at viewer` removal, then a `closed
mouth` removal, now neither) is the reason it exists.

    yk-flop7   737373737 7f2c7be7   111222333 29fc3f3e   1886970040 e1fbf846
               2557902837 3e8d8651  3409564303 a06e0171

Five seeds, 555666777 still excluded for the reason in the entry above.
`headcount.py`: all five ONE.

## 2026-08-19 — `flop` gets the smirk, and the file already had the answer

「ちょっとドヤ顔（自信ありげな顔）」. Fourth face state on this pose, and nothing
about it needed inventing: `(smug:1.35), (half-closed eyes:1.3)` is the pair
`portrait`, `lounge`, `stand`, `peace` and `prone` all wear unchanged, and
`prone` is the one that settles it — also lying, also full body, same pair.

**The reason to reach for the existing pair rather than a new word** is on
record twice. `smug` is doing posture as well as expression here: `sip` measured
it holding her chin up so head, spine and hip land on one arc, and `boss`'s F2
swapped it for `(light smile:1.3)` at the same tag count, reached roughly the
same face, and **took a stocking off her foot and changed the hood**. Substituting
a word is not free on this axis. If the smirk reads wrong, the weight is the
lever — that is the 8/17 heading and it has not been contradicted since.

    yk-smug135   737373737 6759b08f   111222333 6acb5085   2557902837 b90d5cb6
    yk-smug115   737373737 4b7d646c   111222333 0cbd4322   2557902837 c6fecc34

Both ends rendered because the request carried its own gloss. `boss` calls 1.4
gloating and 1.15 「composed, chin still up, arc intact」; ドヤ顔 points high and
（自信ありげな顔）points low, and there is no reading of the phrase that settles
which. The low arm drops `half-closed eyes` with it rather than holding it as a
second variable — `boss` F3 measured that tag indistinguishable at that weight
and dropped it, so two-at-1.35 against one-at-1.15 is the choice the file
actually offers.

`headcount.py`: all six ONE.

**Worth recording about the pose rather than the face:** this is the fourth
expression state `flop` has worn — 徹夜, face-down, default, smug — with the body
tags, the canvas and the camera untouched across all four. The expression axis
and the pose axis have now been shown independent on this recipe four times, not
once, which is a stronger claim than the entry above made.

## 2026-08-19 — `flop` takes 1.15, and the eyes were two problems with two fixes

4b7d646c — `yk-smug115` 737373737 — is the picked render, so **`flop` follows
`boss` rather than its neighbour `prone`: `(smug:1.15)` alone, no `half-closed
eyes`.** The request glossed ドヤ顔 as 自信ありげ and 1.15 is the weight `boss`
calls composed where 1.4 was gloating. `half-closed eyes` left with the weight
rather than as a separate choice — `boss` F3 measured it indistinguishable there
and `boss` Ea then found the tag is not gradual at all. One lever, not two.
Verified byte-identical against 4b7d646c: positive, negative, canvas, sampler.

### 「目も修正してほしい」 — looked at, because the render was named

Two defects in the picked render, and it is worth separating them because they
had different causes and different fixes:

1. **The eyes did not match each other.** Different sizes, different tilt,
   different lash lines. The face is about 250px across in a 1536x1024 frame.
2. **They were lidded.** `half-closed eyes` is long gone from this pose;
   `(smug:1.15)` narrows the lids by itself.

**A second pass at 2048 fixes (1). The eye guard fixes (2). Neither fixes both.**

`HIRES_NEGATIVE` is new in `yukari_recipe.py`: a per-pose string prepended to the
SECOND pass's negative only, through its own `CLIPTextEncode` node `7b`, leaving
node `7` and therefore the whole first pass untouched. `flop` carries
`(half-closed eyes:1.4), (closed eyes:1.4)` there — `boss`'s Ec pair.

This is the shape `boss` described and could not use: Ec was measured safe
chained onto a settled picture and unsafe from scratch, where it stacked with
that pose's buttons guard and grew a rabbit-faced chair. A guard is a deletion,
and the pass-depth finding says a late pass only gets to delete while a first
pass gets to rearrange the composition around it. **Putting the guard where only
the late pass sees it is what makes it portable**, and it is now in the recipe
rather than in a chain someone has to remember.

    yk-eyeguard  737373737  043ff116   guard on pass 2
    yk-noguard   737373737  6c2811ac   control, same pass 2, no guard

At face-crop zoom the two look the same and I said so. **That was a zoom
artefact.** At eye zoom the difference is not subtle: with the guard the eye is
tall and round, the whole iris is inside it with pupil and highlights, and there
is sclera below. Without it the upper lid cuts across the iris and the eye reads
almond and half-shut. Both are hugely better than the first pass, which is (1)
being fixed by pixels in both arms.

**Iris-pixel counting was attempted three times and never came out clean**, so it
is reported as agreement in direction and nothing more: 1020 px against 928 with
the guard. The first version counted the whole face crop and read the *control*
higher, because the bottom of that crop is the purple dress. The second used a
tight band and clipped the control's eyes at the band edge, so the band was
deciding the answer. The third widened it and the mask still spanned every row,
i.e. it is catching purple in the hair. Three contaminations in one measurement
that the eye settled in one look. Eighth statistic to lose here.

## 2026-08-19 — `flop`'s leg weight is bracketed from both sides

「ちょっと脚が長すぎる」 at `(long legs:1.45)`. Two rounds ago, with no tag at all,
the same pose read 「ちょっと胴体が長い」. **The weight is now bracketed and that is
the durable part of this entry** — whatever is right is strictly inside (0, 1.45),
and a later session does not get to go back to either end and call it new.

Moved to **1.40**, the midpoint, which is a guess and is labelled as one in the
splice comment. `yk-legs135b` runs 1.35 beside it:

    yk-legs140    737373737 f8777158    2557902837 f21a863a
    yk-legs135b   737373737 6a322845    2557902837 b2f1bec1

1.35 is being rendered again rather than ruled out by having lost once. It lost
against the *opposite* complaint — too little and too much fail in different
directions, so a loss on the torso side is not a win on the leg side — and it was
last seen on the 徹夜 face at a single pass. Both arms here carry the settled
finish, `--hires 2048` with the eye guard on pass 2, so the comparison happens at
the state the picked render was in.

**Leg length is a first-pass decision and there is no second-pass version of this
fix.** The eyes had one: `HIRES_NEGATIVE` puts a deletion where only the late
pass sees it, and the composition survives. 0.60 redraws the picture; it does not
re-proportion the figure. So every move on this axis costs the picked
composition and has to be re-picked, and that asymmetry between the two fixes is
worth carrying forward — it decides whether a complaint can be answered without
losing the render.

`headcount.py`: all four ONE.

## `kick`: a new pose from someone else's picture, and the foot needs two tags

「このような座って片足を前に突き出しているゆかりさん」, with a reference image
attached — not a render of this recipe. That is the first thing to say about
everything below: this is the only pose in the file built from an outside
picture, so nothing here has been measured yet and the block is a first guess.
What the reference actually shows is a seated figure leaning back with one knee
folded and the other leg thrust straight at the lens, sole first and nearest to
camera, the face still legible above it.

Eight slots, the house size:

```
(solo:1.5), (sitting:1.45), (soles:1.4), (foot focus:1.35),
(foreshortening:1.3), (knee up:1.25), (leaning back:1.25), (couch:1.2)
```

**The foot gets two slots and that is deliberate.** `sip` established the rule:
the thing a composition is built around does not fit in one tag — its mug needed
`coffee mug` and `holding cup` together, and either alone drew the wrong object
or put it in the wrong place. Here `soles` names what faces the camera and
`foot focus` names where the camera looks, and neither is the picture alone.

**`foreshortening` is bought rather than left to the seed**, and it is the slot
this pose's history most justifies. A leg pointed at the lens either compresses
or reads as a long leg lying across the frame — and reading too long is the
failure this recipe has spent the most on. `nape` found that `sitting on floor`
extends the legs and that a leg extended away from the camera runs the frame;
`flop` had to have its `long legs` weight bracketed from both sides over two
rounds. What was the defect in both of those is the subject here, so the tag
governing it does not get spared.

`knee up` is singular. One folded, one out is the whole asymmetry; `knees up`
raises both and draws a different picture.

**No footwear guard, as a decision.** `stand` is the only pose in this file that
names a shoe, so nothing here asks for one — and nothing forbids one either,
and a shoe sole is a different picture from a pantyhose sole. Guarding it means
naming a shoe in the negative, and `stand`'s own note records that naming a shoe
drew one, with a pink butterfly decal on it. Find out whether the guard is
needed before paying for it.

### The B arm is one tag: `full body`

`foot focus` can walk the camera down to the foot and leave the head out of
frame, which is this pose's likeliest failure, and `full body` is the
counterweight every other whole-figure block here carries. It is out of the
recipe and in the sweep instead, so the ninth slot is bought only if the first
round loses the face.

    yk-kick        1886970040 ed709125    2557902837 202e6fc0
    yk-kickfull    1886970040 a03af13b    2557902837 c6bb4795

Single pass, 1024x1536 — every seated whole figure in this file is that canvas,
and the extended leg goes into depth rather than across the frame, so it buys no
extra width. Round one is about whether the pose draws at all; the finish comes
after the composition is picked. Seeds are the two that `chair` found seat her
properly, and 555666777 is skipped for the reason `flop` skips it.

`headcount.py`: all four ONE.

### Written down before it is needed: the negative already argues with this pose

The shared negative carries `(from below:1.35)`, `(upskirt:1.4)` and `panties`,
all earned by other poses. A raised leg in a short dress seen from a seated
camera is close to the angle those guards forbid. Nothing has gone wrong yet and
nothing has been changed — but if the perspective refuses to arrive, or the leg
comes down on its own, **that trio is the first suspect and it is upstream in a
shared block**, not in this pose. Easing it there would touch every render this
repo has approved, so the fix would have to be a per-pose departure, declared.

## `kick` refines, and the pass boundary splits a tag in half

「202e6fc0 をリファイン。いつもの強気な表情で」 — a finish and an expression, on
a composition that had just been picked. Those two halves want opposite things
from the graph, and the round before had just established why: **leg length was
a first-pass decision with no second-pass version of the fix, and every move on
that axis costs the picked composition.** Putting `smug` in `POSES["kick"]` would
have been the same trade for the same reason.

So it went where the eye guard went. `HIRES_POSITIVE` is the positive-side
sibling of `HIRES_NEGATIVE`, node `6b` to its `7b`, spliced into the pose block
rather than appended to the whole string because that is where every other pose
carries the smirk and this file already records that token order changes the
encoding.

**Addition is affordable in a late pass, but only at 0.60.** The deletion half of
the pass-depth finding says a late pass gets to delete cheaply; the other half
was already measured and written in `refine_from_history`'s docstring — at 0.35 a
chained pass left newly-added halter straps a faint suggestion, and 0.60 drew
them properly. `HIRES_DENOISE` is 0.60, so the smirk draws.

### What it cannot spend is what makes it safe

`sip` measured that `smug` is not only a face: it lifts the chin and puts head,
spine and hip on one arc, and that is why `sip` keeps it. A late pass cannot
re-pose a figure. So this buys the half of `smug` that was asked for and is
structurally incapable of spending the half that would have moved the leg —
**the pass boundary splits the tag, and the half that survives is the half that
was wanted.** That is the general result here, not the weight.

### The eye guard rode along, and is not a variable

`kick` has no complaint about its eyes. It got `HIRES_NEGATIVE["kick"]` anyway,
on both arms. The reasoning is not speculative: `smug` narrowing the lids on its
own is the measured finding that `flop` bought this guard for two rounds ago,
and this round is adding `smug`. Applying a known correction alongside the known
cost of the tag that causes it is the pair travelling together, not an untested
addition — and putting it on both arms keeps the sweep to one variable.

    yk-kickA   smug 1.15   2557902837   4f9d232c
    yk-kickB   smug 1.35   2557902837   ebc93322

First pass verified byte-identical to the picked render — nodes 4, 5, 6, 7 and 3
all MATCH against `/history/202e6fc0`, checked rather than assumed. `--hires
2048`. `headcount.py`: both ONE.

1.15 against 1.35 because 「いつもの」 is ambiguous between the two settled
values in this file: `flop` and `boss` run 1.15 (composed), `stand`, `lap` and
`invite` run 1.35–1.4 (gloating at the top of that range). 「強気」 could be
either. **The pair is the next lever, not the third weight** — `stand` carries
`(smug:1.35), (half-closed eyes:1.3)` together, and `boss` dropped the lids only
because at 1.15 they were the last thing reading as attitude rather than
composure.

### Fixed in passing: `chain_pass` squashed to a square

`refine_from_history.chain_pass` scaled to `width: size, height: size`. That is
the same number for the square renders it had only ever been run on, and a
squash for anything else — found because `kick` is 1024x1536. It now uses the
same `sizes()` helper the other two routes already used. No behaviour change for
any square source, so nothing previously measured through it moves.

## The eye guard and the smirk pair cannot both be in pass 2

「もうちょっといつものドヤ顔で」 — 1.15 and 1.35 both landed short, so the answer
is the lever the previous round already named as next: the pair `stand` carries,
`(smug:1.35), (half-closed eyes:1.3)`, rather than a third weight.

**That required taking `HIRES_NEGATIVE["kick"]` back out, and the reason is a
direct contradiction rather than a preference.** That guard is
`(half-closed eyes:1.4), (closed eyes:1.4)`, and `half-closed eyes` is now in the
positive of the same pass. It was bought one round earlier to undo `smug`'s
lid-narrowing as an unwanted side effect; once narrowed lids are the thing being
asked for, the side effect was the feature all along.

So the two levers for "more smug" are mutually exclusive at this pass:

- **raising the weight** is compatible with the eye guard
- **reaching for the pair** is not, and removes it

Worth carrying forward, because the guard reads like a fixture once it is in a
pose's dict and it is not one — it encodes an assumption about which direction
the lids are wanted in.

## 足の指の数を5に: two routes, one variable

The toes survived the 2048 second pass wrong, so **pixels alone did not fix
this** — which separates it from the eye defect two rounds ago, where more pixels
was half the answer. Still a late-pass job: digit count is local detail, not
structure, and 0.60 already demonstrated it redraws eyes. Putting it in the first
pass would cost the picked composition for a defect that does not need it.

Both arms carry the new smirk pair, so the route is the only variable:

    yk-toesA   positive  + (five toes:1.3)      2557902837   f2b752b2
    yk-toesB   negative  + (extra toes:1.45)    2557902837   a6d83313

**A is the positive route on principle.** This file has twice found that only one
side of an axis is addressable and that it was the positive one — `stand`'s
proportion work and `prone`'s `(long legs:1.4)` in the negative, both null. Naming
what is wanted has beaten forbidding what is not, here, repeatedly.

**B is ONE guard and not a stack**, deliberately. Extra/fewer/bad-feet together
would be three guards pointing at a single defect, which is exactly the shape
that has wrecked this recipe's palette twice and bought it four backdrop
intruders. One guard also cannot cover both directions of a count error, and
that limitation is the price of the rule rather than an oversight.

**Neither tag has been checked against a wiki.** This file's own standard —
`crouching` and `reaching out` were dropped for having no wiki page — is not met
by `five toes` or `extra toes`, and there is no way to check it from here. If A
does nothing at all, an unknown tag is the first suspect, ahead of the route.

First pass untouched on both arms, asserted in the probe rather than assumed.
`headcount.py`: both ONE.

## The answer was in `/history`, and two rounds of weight-hunting were the wrong search

「この頃の表情ですね」 with `10915a12-b496-47a1-bf35-5b5843986e37` attached —
`pl-b-2331520658`, an upper-body portrait from the hoodie era, on a different
SURFACE and a different negative. Its expression cluster:

```
(smug:1.3), (confident:1.25), (half-closed eyes:1.25), (open mouth:1.35)
```

and, in the negative, `(clenched teeth:1.4), (wide mouth:1.3), (squinting:1.3),
(closed eyes:1.4), (angry:1.2)`.

Line by line against what had been tried:

- **`(smug:1.3)` sits between the 1.15 and 1.35 that both landed short.** The
  weight was never the missing piece, and the midpoint of two failed guesses was
  not going to be found by continuing to guess.
- **`(confident:1.25)` has never been used in this recipe** and is literally the
  word the request was made with — 「自信ありげ」, three rounds ago.
- **`(open mouth:1.35)`, and this is most of the difference.** A smirk with a
  closed mouth is composure; the same smirk with the mouth open is the ドヤ顔
  that had now been asked for three times. FACE nails the mouth shut for every
  pose outside `open_mouthed`, so **no weight on `smug` was ever going to reach
  it** — the tag that had to move was not the tag that had moved last.

That last clause is the finding worth keeping. The search stayed on `smug` for
two rounds because `smug` was what had changed most recently, and the axis that
was actually wrong had been fixed and invisible since the pose was written.
**A render the user remembers is a primary source, and this repo can read it:
`/history/<id>` had the answer the whole time.**

### The eye guard splits, it does not vanish

`kick`'s `HIRES_NEGATIVE` came back — as half of itself. 10915a12 bans
`(closed eyes:1.4)` while *asking for* `(half-closed eyes:1.25)`. It split the
two; the guard written here had fused them, which is why it read as
incompatible with the smirk pair last round. Forbid the lids all the way shut,
ask for them half. One tag banned, not a stack.

### The mouth is resolved where the contradiction is

`open_mouthed` is read inside `positive()`, so adding `kick` to it would open the
mouth in the pass that picks the composition too. Instead `build()` strips
`closed mouth, ` from the pass-2 text when `HIRES_POSITIVE` asks for an open
mouth — asserted, not silently replaced, because this file has been bitten by a
`.replace` against a string that no longer contained its target.

    yk-faceA   cluster only                 2557902837   aa99059b
    yk-faceB   cluster + the 4-guard tail   2557902837   405ad7a0

B carries `(clenched teeth:1.4), (wide mouth:1.3), (squinting:1.3), (angry:1.2)`
— the rest of what that render was drawn with. Four guards, but four *distinct
failures of one expression*, which is the LEGWEAR_BAN shape rather than the
palette-wrecking shape, and it is a late pass where guards are cheap. Four is
still four, so it is the variable rather than an assumption.

`(five toes:1.3)` rides on both arms and **is not validated** — the toe routes
have not been judged yet. Constant across the arms, so it cannot decide the
comparison; it is there so this round does not quietly hand the toes back.

Pass 1 asserted untouched and still saying `closed mouth`. `headcount.py`: both
ONE.

## The costume contract only ever covered the first pass

Found while doing the above, and it is structural rather than about this pose.
`check_prompt` reads `yk.positive(pose)`. `HIRES_POSITIVE` rewrites that text
afterwards, for pass 2. So a splice there could take a garment off and **every
line of `costume_check` would still print ok** — `kick` found it by legitimately
needing to drop `closed mouth`, and the same mechanism would drop
`(purple dress:1.45)` in silence.

`costume_check.py` now prints a `pass 2` section for every pose in either hires
dict: what it adds, what it removes, what it bans.

    pass 2  kick
      +   (smug:1.3), (confident:1.25), (half-closed eyes:1.25), (open mouth:1.35)
      -   closed mouth
      ban (closed eyes:1.4)

Reported rather than requiring a declaration, on purpose: a pass-2 departure is
not the same kind of thing as a costume change — it is a correction to a picture
that has already been picked, and the whole argument for `HIRES_POSITIVE` is
that such corrections are cheap there. It **does** hard-FAIL if pass 2 removes a
tag belonging to CHARACTER, LEGWEAR, BODY or HOOD. What was unacceptable was
that any of it could be invisible.

## Verbatim, and still 「表情が穏やかだねえ」 — so it is not the tags

The cluster from 10915a12 was copied word for word and weight for weight, plus
the guard tail, and the face still reads calm. **That rules out the tag
vocabulary as the cause**, which is worth as much as a positive result: three
rounds of this problem have now been spent on which words to use, and the words
turn out to be right and insufficient.

Two candidates left, and they are not variants of one idea — they fail in
different places, so one arm each.

    yk-calmA   attention   2557902837   091c42cd
    yk-calmB   the pass    2557902837   0e7735fc

**A — attention.** `(foot focus:1.35)` and `(foreshortening:1.3)` are in the
pass-2 positive only because the pose block is carried there whole. Their job is
composition, and pass 1 has already done it. In pass 2 they decide nothing; they
spend attention, and what they spend it on is **pointing the camera away from
the face** while the same text asks for a nuanced expression on it. Dropped from
pass 2 only, pass 1 asserted untouched.

This is `HIRES_NEGATIVE`'s argument run backwards. That dict exists because a
subtraction belongs in the pass that can act on it; this is the same claim about
an addition whose work is finished — **a composition tag should not be re-paid by
the pass that only refines.** If A wins, that generalises to every pose with a
camera-direction tag and a second pass, which is most of them.

**B — the pass.** The expression moved to pass 1, where the render it was copied
from had it. This is the honest test of whether 0.60 can overwrite a face the
base image has already drawn calm and closed-mouthed. **It costs the
composition** — same seed, but pass 1 is the pass that decides the picture, and
that is the trade this pose has refused four times running. It is on the table
now because the expression has been asked for four times and has not arrived,
and protecting the composition has started to cost more than it saves.

### If both fail, the next lever is pixels and it is not a crop

Not measured, and stated as reasoning rather than a number: 10915a12 is
`(upper body:1.45), (portrait:1.25)` at 1024x1280, where the head is a large
fraction of the frame. `kick` is a whole seated figure at 1024x1536 with a foot
in the foreground, so the head is a small one — roughly a two-to-three-fold
difference in linear face size in the pass that decides the expression. The eye
round two back already found this recipe's threshold from the other side: a face
about 250px across is where eyes stop matching each other.

Cropping in is not available — that rule is not suspended by a fourth failed
round. The lever would be a framing tag in pass 1, which changes the pose, and
that is a different conversation to have deliberately rather than by drift.

`headcount.py`: both ONE.

## The pass was the ceiling: an expression is a decision, not a finish

「表情は2枚目が正しい」 — `yk-calmB`, `0e7735fc`, the arm that put the expression
in **pass 1**. `HIRES_POSITIVE` lost, and the reason is worth more than the pose:

**A late pass reaches anything it can DRAW and reaches nothing pass 1 has already
DECIDED.** The straps that `refine_from_history` measured at 0.60 were the first
kind. A face that the base image has already drawn calm and closed-mouthed is
the second: the same words, at the same weights, copied verbatim from 10915a12,
did nothing from pass 2 and worked immediately from pass 1.

That is the general rule this session was groping for from both directions. It
also explains the earlier result rather than contradicting it — the eye guard
worked from pass 2 because a guard subtracts, and subtracting a lid is a finish.

Settled into the recipe:

- the cluster moved into `POSES["kick"]`, which is now **twelve tags** against
  this file's own note that a pose block breaks around nine. It held. That is a
  data point, not a licence: the four that pushed it past the line were all
  expression and none touched the pose.
- `kick` joined `open_mouthed`, and the departure is declared in
  `costume_check.py` (`removed: closed mouth`). While the expression lived in
  pass 2 this list was deliberately left alone, because membership would have
  opened the mouth in the pass that picks the composition.
- `HIRES_POSITIVE` is empty and stays in the file. The mechanism proved a rule
  worth keeping in code even with no entries.

The approved render's pass 1 differs from the settled recipe by exactly one tag,
diffed rather than assumed: `(five toes:1.3)`, retired below.

## Both sides of the tag axis fail on a COUNT, and they fail differently

「指が6本あるねえ」 — the toes, on the sole that is the nearest thing to the lens.
The hands are not in frame at all, so 指 is unambiguous once looked at.

    positive   (five toes:1.3)      four consecutive renders, including the
                                    approved one's PASS 1.  Six toes.
    negative   (extra toes:1.45)    pass 1, where the topology is decided
               (extra digits:1.45)  pass 1, the generic word as a control
                                    f69dbc73 / d47e01e7

**Neither guard corrected the count — both dissolved the toes**, leaving a smooth
sole with no separation at all. A guard is a deletion, and what it deleted was
the feature rather than the surplus. **Zero is not five.** And the positive side
did not merely fail: it failed while naming the exact number it was wrong about.

So a count is not the kind of axis this file's "only the positive side is
addressable" finding was about. That finding came from proportion, which is
continuous. A count is topology, and neither side of a text prompt addresses it.

Both guards are OUT of the recipe. Shipping one would ship a smooth sole.

## Changing tools did not work either, and it cost the framing

`nape`'s rule — when a defect survives that many prompt levers, stop diagnosing
and change tools — and the tool for a first-pass structural fact is the seed.
Raising the first-pass canvas to give the foot more room is the one escape this
file has already measured shut (a second figure at 1280x1920).

    yk-kickseed   1886970040 e960eefd   737373737 2cb4cf8f
                  111222333  6792bd20   3409564303 6dea7472

**Four seeds, four wrong counts.** And a second finding arrived uninvited: all
four put the camera down at the foot and **left the head out of frame**, which is
exactly the failure predicted when this pose was written. Both renders the user
has picked were on 2557902837, and that seed was carrying the framing.

So `(full body:1.4)` — the counterweight written out of the block as round one's
B arm and never judged — finally gets rendered against the approved expression:

    yk-kickfb     1886970040 4aace7ee   737373737 4011a0ec
                  111222333  fa504c93   3409564303 e9e77538

Not put in the recipe: both picked renders were drawn without it.

### Where the toe count stands, plainly

Every prompt-level lever is spent, and the seed is spent. What remains would be
repairing the foot — `inpaint_composite.py` exists and would do it — and **that
is banned by the same rule as cropping**: do not repair a render to deliver it
while the prompt is being tuned. The rule is not suspended by the count of
failed rounds; that is what it is for.

The honest position is that this recipe cannot currently draw five toes on a
sole presented flat to the lens at this size, through opaque pantyhose. The
choice left is the user's: accept it, or move the pose so the sole is not the
subject.

`headcount.py`: ONE on all four seeds.

## Naming the FEATURE is the lever the count arguments never tried

「指6本な点だけなんとかプロンプトで直してほしい。まじ。」 — reaffirmed after the
previous round said the tag axis was spent. It was not: everything tried until
now had talked about the NUMBER. The positive named it and got six; the guards
forbade a surplus and dissolved the feature. **Nothing had named the feature.**

`toes` is also the only word in this whole argument that is certainly in the
vocabulary. `five toes` and `extra toes` both behaved exactly like words the
model does not know — and `extra digits`, which certainly is one, behaved the
same, which is the evidence that the route and not the spelling was wrong.

`(full body:1.4)` is settled into `POSES["kick"]` first — the counterweight
written out as round one's B arm, now vindicated by four seeds losing the head
and by fa504c93 being the picked render. The recipe reproduces that render
node for node (5, 6, 7, 3, 10, 11 all MATCH), so the arms below differ from it
by exactly their one lever. Thirteen tags.

    yk-toeA   (toes:1.4)                            pass 1   f9bf9eaa
    yk-toeB   (toes:1.4) + (extra toes:1.15) neg    pass 1   97ad492e
    yk-toeC   (extra toes:1.15) neg alone           pass 1   f37392fa
    yk-toeD   (five toes:1.6)                       pass 1   729db547
    yk-toeE   (toes:1.4)                            PASS 2   a600673c

**C dissolved the toes again at 1.15.** That closes the guard route at any
weight: 1.45 and 1.15 fail the same way, so the sledgehammer was not the
problem — subtraction is. A, B, D and E all draw separated toes.

### E is the only arm that keeps fa504c93

Every other arm edits the pose block, so every other arm edits pass 1, so every
other arm moves the composition that was just called かなり良い. Prompt-only on a
topology defect has meant pass 1 all session.

E is the exception, and the reason is the pass rule settled two rounds ago
rather than an exception to it: **a late pass reaches what it can DRAW and balks
at what pass 1 has DECIDED**, and `toes` is a feature, not a count — sharpening
toe separation is a drawing job. Its pass 1 is asserted byte-identical to the
recipe's, so its composition is fa504c93's exactly.

So the two outcomes are worth different things: if E is right, the count was
five mushy toes reading as six and it cost nothing. If only A or B is right, the
count was really six and the composition is the price.

### Not counted here, on purpose

The toes are seen from the top edge rather than the pad side, and this file has
now lost **eight** image statistics to the user's eye. A ninth, on a count, at an
angle where separations and shading look alike, is not a bet worth making. What
is reported above is structural and legible — dissolved versus separated — and
the count is left to the eye that has won every previous disagreement.

`headcount.py`: ONE on all five.

## `(toe scrunch:1.35)` — eleven levers argued about the number; this one changed the drawing

「治らないねえ・・・」 after five arms, on top of four before them. The count had
been attacked from every side a prompt has:

    (five toes:1.3) / (five toes:1.6)          positive, two weights
    (extra toes:1.45) / (extra toes:1.15)      negative, two weights
    (extra digits:1.45)                        negative, a word certainly in
                                               the vocabulary -- same failure,
                                               which is what proved the ROUTE
                                               wrong rather than the spelling
    (toes:1.4) pass 1 / pass 2 / + soft guard  the feature named instead
    four alternative seeds

Every one of them asked for **five toes fanned in a row**, which is the hardest
thing in this frame to draw and the easiest thing to miscount. Curled toes
overlap instead of fanning, and an overlapping row does not have to be counted
to read right.

    yk-toeF   (toe scrunch:1.35)        956b3a42   five, countable
    yk-toeG   (spread toes:1.35)        a95e600b   long finger-like toes, worse
                                                   than any count tag
    yk-toeH   (opaque pantyhose:1.0)    8fc338ba   unchanged

**The lesson is the shape of the search, not the tag.** Eleven attempts treated
this as a quantity to be specified and the twelfth treated it as a structure to
be chosen. `(spread toes:1.35)` is the control that makes the point: the same
axis, the opposite direction, and it is worse than doing nothing — so this is
not "any new tag would have helped".

`(toe scrunch:1.35)` is in `POSES["kick"]` next to `(soles:1.4)`, and the recipe
reproduces `yk-toeF` node for node. Fourteen tags.

### Null: the toes are not at the dark end of the gradient

Measured before spending renders on it, because the hypothesis was cheap to
kill: if the toes sat at the black end of `(gradient legwear:1.4)`, every count
lever would have been arguing about separations that were barely drawn.

    yk-kickfb   figure mean 103.2   toe region 95.4   51.7% of the figure darker
    yk-toeA     figure mean  73.9   toe region 58.7   61.9% of the figure darker

They sit near the middle. **The hypothesis is false and the three renders it
would have bought were not spent.** Local contrast in the toe region does run
lower than the figure's (44.2 vs 51.7, and 35.3 vs 57.3), but a foot is a smooth
object and low variance is what a smooth object looks like — that is exactly the
inference that has lost eight times in this file, and it is not being made a
ninth time.

`(opaque pantyhose:1.0)` was the other upstream suspect — the theory that `soles`
and `toes` describe bare feet while this foot is inside fabric, so every toe tag
was describing something not in the picture. Rendered, unchanged, recorded here
so it is not retried.

    yk-kick   1886970040 8aac2eb9   737373737 767c39a4   2557902837 6e1a9b77

The settled recipe on three further seeds, for a composition to choose from now
that the foot draws.

## The little toe attaches to the side, and curl is the same axis that fixed the count

「小指が変なところから出てるよ」 — five toes, but the outer one splays off the
SIDE of the foot instead of ending the row. **Present on all four renders of the
settled block, so this is the block and not the seed** — the seed sweep already
did its job earlier and is not the tool twice.

Same axis, because the defect is the same KIND: a structure the model draws
badly, not a quantity it gets wrong. That distinction is now the whole method
for this foot.

    yk-toeI   (toe scrunch:1.55)              965a348f   every toe on the row
    yk-toeJ   (toe scrunch:1.70)              eceb041c   same, separations
                                                         starting to shallow out
    yk-toeK   (soles:1.4) -> (soles:1.2)      87e00852   no help

**The axis is monotonic**, which is worth having: more curl tucks the outer toe
into the row. Three points on it now (1.35, 1.55, 1.70) rather than a pair.

### 1.55 and not 1.70, and the reason is a failure this pose has already met

At 1.70 the separations shallow out and the row begins to read as one mass —
**which is exactly where `(extra toes:1.45)` and `(extra digits:1.45)` both
ended up.** Curl far enough and it dissolves the toes the same way a guard does,
by a completely different mechanism arriving at the same picture. 1.55 keeps
them distinct while fixing the attachment. 1.70 is rendered and is the next step
if the attachment ever reads wrong again, but it is a step toward that edge and
the note in the recipe says so.

### Null: easing `soles` does not move the outer toe

`(soles:1.4)` presents the plantar surface flat to the lens, which is what puts
the outer toe on screen at its worst angle, so easing it was the other
structural reading. Eased rather than deleted — `prone` got its win that way,
and deleting it would lose the pose. It changed nothing about the attachment.
Recorded so it is not retried.

    yk-kick2   1886970040 c823bbab   737373737 a688fb13

The settled block on two further seeds. Recipe reproduces `yk-toeI` node for
node.

## The palette breaks on POSITIVE toe tags, and the count criterion was never the costume's

Two findings this round, and the first one is a correction of something asserted
in this file an hour earlier.

### Correction: it is not the slot count

「カラーリングはおかしい」. Measured at seed 111222333, mean figure saturation
against the costume's own colours:

    13 tags, no toe tag                sat  52.5   coat 37.7%  hair 5.0%
    + (toes:1.4)                       sat 113.5   coat 20.7%
    + (five toes:1.6)                  sat 187.8   coat  0.2%
    + (toe scrunch:1.35)               sat 196.9   coat  0.1%
    + (toe scrunch:1.55)               sat 198.9   coat  0.0%

The costume colours do not shift, they LEAVE. **This was first read as the
fourteenth slot** — three unrelated fourteenth tags breaking it identically is a
persuasive shape, and `sip`'s ninth slot is the precedent. That read was wrong,
and the test that killed it was making room:

    13 tags, -(couch:1.2), scrunch kept    sat 196.0
    13 tags, -(soles:1.4), scrunch kept    sat 196.5
    12 tags, -both,        scrunch kept    sat 142.3

Deleting slots did not bring it back. The count was a coincidence of the toe tag
always having been the one added last. **The lever is the toe tag itself.**

And the direction matters: negative toe guards cost nothing.

    (extra toes:1.15) pass 1     sat 40.3   coat 48.4%
    (extra toes:1.45) pass 1     sat 51.0   coat 24.5%
    (extra digits:1.45) pass 1   sat 47.7   coat 23.2%

So a POSITIVE toe tag pulls this prompt somewhere with a different palette, and
subtraction does not. That is why `(toes:1.4)` was mildest at 113.5 and the two
tags that name a foot's *arrangement* were worst.

### 「分厚いタイツってことで足の指先を書かなくてもいいのでは？」

This dissolves the problem, and the picture it asks for is **one that two guards
had already drawn and this file had already written off.** `(extra toes:1.45)`
and `(extra digits:1.45)` were both recorded as failures for "dissolving the
toes, leaving a smooth sole with no separation at all" — judged against five
countable toes, **a criterion the costume never asked for.** She is in
`(opaque pantyhose:1.4)`. A foot in thick tights has a smooth toe box, and
drawing five toes through it was the error the whole time.

Eleven levers spent arguing about a count, one spent curling them, and the
answer was that the toes should not be individually drawn at all. **The defect
was in the acceptance criterion, not in the prompt** — worth more than the tag,
because nothing in a render tells you the target is wrong.

Settled: `(toe scrunch:1.55)` is out, the block is back to the thirteen that
drew fa504c93, and the guard went into `HIRES_NEGATIVE["kick"]`:

    "(toes:1.4), (extra toes:1.4), (closed eyes:1.4), "

**In pass 2 and not pass 1**, because this is the shape a late pass is best at
and the argument that built the dict in the first place: a guard is a deletion,
a late pass only gets to delete, and pass 1 stays byte-identical to fa504c93 —
so the picked composition and the clean palette both come through untouched and
pass 2 smooths the toe box off the end. Verified identical on nodes 5, 6, 7, 3
and 10.

    yk-smoothR   (toes:1.4), (extra toes:1.4)     111222333  f0a96428
                                                  1886970040 10cefa69
    yk-smoothT   the same pair at 1.55            111222333  1ee9fbc9

    f0a96428   sat 35.1   coat 35.4%  hair 10.4%  legwear 13.3%
    10cefa69   sat 40.9   coat 25.8%  hair  8.4%  legwear  9.9%
    1ee9fbc9   sat 34.8   coat 35.2%  hair  9.9%  legwear 14.7%

All three back in the approved range, and R and T are indistinguishable — so 1.4
is enough and the recipe takes it rather than the stronger pair.

`headcount.py`: all three ONE.

## 発色: the second toe guard was the whole cost, and the accents are the measure

「あとは発色かな？」 on 1ee9fbc9. The mean saturation was already known to be
low; what names the complaint is the **brightest tenth of the figure**, which is
where a picture's accents live:

    fa504c93   no toe guard                sat 52.0   brightest tenth  89.0
    1ee9fbc9   (toes:1.55)+(extra toes:1.55) sat 34.4   brightest tenth  52.0
    f60817db   (toes:1.55) alone           sat 60.7   brightest tenth 105.0

The mean falling by a third is the smaller half of the story. Every accent in
the picture flattening from 89 to 52 is 発色, and **one guard puts it back above
the approved render's own numbers while keeping the smooth toe box.** The second
guard bought nothing and paid for it in colour.

Hue moves with it: 210 clean, 221 under the pair, 210 again with one.

**Fourth time guard-stacking has cost this recipe something, and the first time
the cost was saturation** rather than the palette's shares or an intruder in the
backdrop. Worth noting that both guards name the same target — which is exactly
the shape the rule is about, not a coincidence of having two of them.

### Null: `(vivid colors)` in the second pass does nothing

The obvious counter to a flat picture, run at two weights in `HIRES_POSITIVE`
against the guard pair still in place:

    0a8ce5f0   pair + (vivid colors:1.25)   sat 37.6   brightest tenth 61.0
    a4c27b83   pair + (vivid colors:1.40)   sat 37.6   brightest tenth 61.0

Identical to each other to the decimal, and barely off the 34.4 they were
supposed to fix. **A tag that measures the same at two weights is a tag that is
not doing anything**, which is how `half-closed eyes` was diagnosed earlier in
this file — except that one was binary and this one is inert. Do not reach for
it; remove the guard that flattened the picture instead of adding a tag to argue
with it.

    yk-kick3   1886970034 d24dea41   2557902837 80870b8c   1886970040 d738a60b

Three further seeds on the settled block. 1886970034 is a mistyped seed, kept
because it rendered and measures well rather than pretended away.

    d24dea41   sat 72.0   brightest tenth 129.0
    80870b8c   sat 76.6   brightest tenth 115.0
    d738a60b   sat 57.9   brightest tenth  91.0

Recipe verified against `yk-colU` node for node, and its pass 1 verified
byte-identical to fa504c93 — so the picked composition and the restored colour
are the same graph.

## `situp` — the first pose here whose subject is an action NOT completing

「腹筋が全くできないゆかりさん」. Every other block in `POSES` names a state she
is in — sitting, lying, standing, kicking. This one names an attempt that fails,
and the picture is only right if the model draws the half of it that does not
happen: shoulders still on the floor.

Block, on `flop`'s canvas (1536x1024) for `flop`'s reason — a body on the floor,
and this one is longer than flop with the knees up and the elbows out:

    (solo:1.5), (lying:1.45), (on back:1.5), (knees up:1.4),
    (hands behind head:1.35), (sit-up:1.3), (clenched teeth:1.35),
    (sweatdrop:1.3), full body

Eight after `(solo:1.5)`, which is the budget this file keeps quoting.

Three choices are worth stating before any of it is measured, because they are
what the first sweep tests:

- **`(sit-up:1.3)` is the weakest tag in the block on purpose.** It names the
  feature — without it the four apparatus tags read as lying down comfortably —
  but it is also the one tag pulling toward a *successful* rep, which is the one
  picture this pose must not produce. It is the first weight to lower, not the
  first to raise.
- **`(clenched teeth:1.35)` costs `closed mouth` out of FACE**, so `situp` joins
  `open_mouthed` and declares the removal in `costume_check.py`. The smug 半目
  this character defaults to is precisely wrong here: composure reads as a rest.
- **`(sweatdrop:1.3)` over `sweat`.** The anime bead is a comic marker; `sweat`
  buys wet shine, and this recipe is flat colour.

The negative gains three tags for this pose only —
`(sportswear:1.45), (gym uniform:1.4), (yoga mat:1.3)`. An exercise scene is the
strongest pull away from the costume contract anything in this file has asked
for, and the stack is kept to three because two earlier long guard stacks
flattened the palette.

    yk-situp   555666777 1e54b47a   111222333 40ecdc95   1886970040 68d1d34b
               737373737 da1c9c91   2557902837 a8c7ddd0   3409564303 dff8c3cf

First sweep, unjudged at the time of writing. **No angle tag is spent yet**:
`flop` holds a body on the floor at this canvas without one. If the camera looks
straight down, the failure flattens out of the picture and `(from side:1.3)` is
the lever — a side view is what reads "shoulders still down".

### 「筋肉がなさすぎて猫背になってしまう」 — the punchline moves from an absence to a shape

The first `situp` block's failure was *she does not come up*. This one's is *she
comes up wrong*: no core to lift with, so the spine rounds and the neck does the
work. **A shape is drawable in a way that an absence is not**, which is the more
useful half of this — the earlier block was asking the model to withhold
something, and this one asks it to draw something.

`(slouching:1.4)` took `(sweatdrop:1.3)`'s slot rather than joining it. Nine is
where blocks in this file start losing things, and the bead was the only tag in
here that decorates rather than describes; the strain still has
`(clenched teeth:1.35)`.

**The negative is the load-bearing half.** 猫背 has a direct opposite, and it is
one this model volunteers for a girl on her back — `stand` spends a positive tag
to *get* that arch. So `situp`'s negative gains
`(arched back:1.4), (bridge (pose):1.3)`. Naming a shape in the positive without
forbidding its opposite is half a lever, and this file has the `stand` note
proving the model has its own opinion about that axis.

One tag for the feature, not two. `(hunched over:1.4)` names the same thing;
pairing them is the shape that cost the toe work its accents, so it is an arm
rather than a second guard.

    A  lying, (slouching:1.4)        555666777 75960c2f  111222333 3402549d
       + (arched back) banned        1886970040 3d932141  737373737 bc8d955c
    B  lying, (hunched over:1.4)     555666777 e6cddd3e  111222333 7bc3da9c
                                     1886970040 997bd335
    C  sitting, given up, 1024x1536  555666777 341d4536  111222333 2c347ca5
       (slouching:1.45)              1886970040 6b730647

C is the arm worth watching if A and B both come back flat on the floor:
**`slouching` is a word about an upright spine**, and lying down may leave it
nothing to grab. If the tag only works seated, that is a null for the lying
frame and the pose has to get its 猫背 from the composition instead — she gave
up and is sitting in a heap, rather than mid-rep.

B and C are `.local/situp_arms.py`, which assigns whole `POSES`/`SIZES` entries
rather than string-splicing them — a splice against a block that has moved
does nothing and says nothing.

### 「腹筋要素が0になった」 — and this file predicted it, in the toe section

The 猫背 round took the exercise out of the picture entirely. The diagnosis is
already written down, three sections up, from the other direction:

> A guard is a deletion, and what it deleted was the feature rather than the
> surplus. **Zero is not five.**

There it was a negative tag dissolving the toes. Here it is a *positive* weight
held down on purpose: `(sit-up:1.3)` was pinned at the bottom of the block with
a note saying that raising it would draw a successful rep. The failure that
actually arrived is the one where the exercise is not in the frame at all.

**Do not spend weight defending against a feature's excess before the feature
has been shown to appear.** A rep drawn too well is a note to write; no rep is
no picture. This is the second shape of the same error and it is worth naming as
its own rule, because the first one looked like a negative-side problem and this
one is nothing to do with the negative.

Three changes, all the same change — weight off the state, onto the action:

    (sit-up:1.5)      raised, and moved to the slot straight after (solo:1.5);
                      at position six, behind two tags saying she is lying
                      down, the subject of the picture was a footnote
    (on back:1.4)     lowered from 1.5 -- a crunch is not flat, and this tag
                      was saying "resting" louder than anything said "exercise"
    (slouching:1.35)  eased a notch; it won the last round outright, which is
                      exactly the problem

**And `(yoga mat:1.3)` came out of the negative.** That guard was written
against the wardrobe, and a mat is floor, not clothing — it was the one object
in the picture saying the scene is exercise, and banning it helped take 腹筋要素
to zero. `(sportswear:1.45), (gym uniform:1.4)` stay; they are what the guard
was actually for. **A costume guard that names a prop is guarding the wrong
noun.**

    D  recipe: (sit-up:1.5) first     555666777 e28c0c39  111222333 b9e02c79
       + mat allowed back             1886970040 51d8fdbf  737373737 3de0954d
    E  (exercise:1.45) in that slot   555666777 95222725  111222333 0c400781
                                      1886970040 76c83b7b
    F  D + (from side:1.35), 9 tags   555666777 8a3d614a  111222333 2f2bdf39
                                      1886970040 a61a67a8

E is the arm that matters if D still comes back empty: it asks whether this
model knows the word `sit-up` at all. `exercise` is a large tag and `sit-up` is
a small one, and **a rare tag at 1.5 is still a rare tag** — if E reads as
exercise and D does not, the feature never had a lever and the whole first three
rounds were spent weighting a word the model does not hold.

F tests the camera, which was flagged as the first lever two rounds ago and not
taken: a sit-up is legible from the SIDE — bent knees, torso at an angle — and
close to illegible from above, where it is a girl lying on the floor.

### `situp` settles on the F arm — the camera, which was the first lever and the last one tried

a61a67a8 (seed 1886970040) is the picked render, and it is the arm that added
`(from side:1.35)`. Its block is now `POSES["situp"]`, verified byte-identical
to a61a67a8's own graph — `positive()` and `negative()` both compared against
`/history` rather than rebuilt from memory.

**A sit-up is a silhouette before it is a tag.** Bent knees and a torso at an
angle read as the exercise from the side, and as a girl lying on the floor from
anywhere else. No weight on `sit-up` buys that geometry, because the geometry is
the camera and not the subject — which is why three rounds of weight arguments
(1.3 → pinned low → 1.5 → moved to the front) moved the reading so little.

The camera was written into this pose's very first note as "the first lever if
the picture flattens", and then not taken for three rounds. **When a note names
the lever, take the lever before re-weighting the words.**

Nine tags after `(solo:1.5)`, against the eight quoted throughout this file.
`kick` held thirteen; the budget is a smell and not a rule, and here the tag
that pushed it over is the one doing the work.

a61a67a8 was pass 1 only — 7 nodes, 1536x1024, no upscale. The print:

    yk-situp 1886970040 9744c93d   --hires 2048, denoise 0.60

which is `prone`'s settled second pass at the same canvas, for the same reason:
2048 at 0.60 specifically, since 0.45 scribbles the outline and 3072 blurs it to
a halo. Pass 1 is unchanged by `--hires`, so this is the picked drawing with
detail, not a re-roll.

## `dizzy` — 寝不足でぐるぐる目 (2026-08-20)

「寝不足ゆかりさん。目にクマがあってぐるぐる目」. `allnighter`'s crop, `allnighter`'s
クマ, and the dead eye swapped for a spinning one —

    (solo:1.5), (portrait:1.5), (head and shoulders:1.4), (close-up:1.2),
    (face focus:1.3), (@_@:1.45), (eyebags:1.4),
    (dizzy:1.3), (open mouth:1.35)

at 1024x1024, in `HEAD_FRAMINGS`, in `open_mouthed`. Nine tags — the same nine
`allnighter` spends, because this is a **substitution and not an addition**:
two tags out, two in, the framing five untouched.

What the substitution rests on:

- **`@_@` is the tag, and it takes `empty eyes`' slot.** ぐるぐる目 is `@_@` on
  danbooru; `spiral eyes` and `dizzy eyes` are not tags there. `empty eyes` at
  1.45 and `@_@` are both a single instruction about what is drawn inside the
  iris, so they cannot both be live — running them together is two drawings of
  one feature, and 1.45 is the weight that was already proven to carry an eye
  in this crop.
- **`half-closed eyes` leaves.** `allnighter` raised it to 1.35 for the droop; a
  lid at 1.35 covers the exact thing this request is about. The droop is carried
  by `eyebags` and the open mouth instead.
- **`(dizzy:1.3)` is support, not the expression.** `@_@` is punctuation and
  nothing in this file has yet carried a feature on a symbol tag alone. `dizzy`
  is a real danbooru tag for the same state and is deliberately *under* `@_@`.
- **`eyebags` stays at 1.4**, the weight it holds in every exhausted pose here.
  It is the クマ and it is what makes this 寝不足 rather than just startled.
- **No desk, no night, no motion lines.** Same reason as `allnighter`: SURFACE
  is `(simple background:1.3), (grey background:1.2)` and a scene argues with it.

The open question is whether `@_@` survives the tokenizer at all — if the sweep
comes back with ordinary purple irises, the tag was punctuation the model never
learned, and the next move is `(spiral pupils:1.4)` or a `(dizzy:1.5)` lead
rather than more weight on `@_@`.

Sweep queued at 1024x1024, six seeds: 555666777 d20e4b3a, 111222333 ac73c275,
1886970040 10fd38ab, 737373737 54dcff8f, 2557902837 f000b137, 3409564303
d67a7756. Unjudged at the time of writing.

### `@_@` is a real tag to this model, and `eyebags` is the one that did not land

54dcff8f (seed 737373737) picked on art style — 「絵柄的に近いかな」 — and it
answers the open question above outright: **`(@_@:1.45)` draws the spiral.**
Both irises come back as a drawn purple swirl on white, not a hint and not a
highlight-less iris, so the symbol tag survives the tokenizer and carries the
feature. `spiral pupils` and a `dizzy`-led block are not needed and are off the
table. The white sclera around them is `@_@`'s own drawing convention, not
`empty eyes` leaking back in — that tag is not in this block.

What did **not** land is the クマ. `(eyebags:1.4)` — the weight every exhausted
pose in this file uses — reads at most as two faint strokes under one eye at
this crop, and the face reads 「びっくり」 rather than 「寝不足」. The tag is not
being outvoted by another eye tag here, because the two that used to sit beside
it both left; it is just quiet. Worth noting against `allnighter`, where the
same 1.4 was called the tag that "makes it an all-nighter rather than a mood" —
that judgement was made with `(empty eyes:1.45)` and `(half-closed eyes:1.35)`
in the frame doing most of the exhaustion. **`eyebags` was never carrying it
alone, and this is the first render that asks it to.**

One tag, three settings, seed held at 737373737 so the drawing is comparable
(`.local/dizzy_eyebags.py`):

    eb155        (eyebags:1.55)                 55e9b8fc
    eb170        (eyebags:1.7)                  6fd02171
    eb155tired   (eyebags:1.55), (tired:1.3)    b4629be6

Unjudged at the time of writing. If 1.7 still does not draw a ring, the answer
is not more weight on `eyebags` — it is that this crop's flat-colour palette has
nowhere to put a shadow, and the next lever is the palette and not the word.

### `(eyebags:1.55), (tired:1.3)` is the クマ, and `@_@` at 1.45 is too loud for it

b4629be6 picked: 「最後のがいいけど、目のぐるぐるが強調されすぎて視線誘導されて
しまう」. Two results in one render.

**The クマ is solved, and it took two tags and not a heavier one.** `eyebags`
alone at 1.55 is on the sheet as eb155; what reads in b4629be6 is `(tired:1.3)`
beside it — the shadow is drawn as a dark mass under both eyes instead of a
stroke. Neither 1.55 nor 1.7 alone got there, so the fix was a second word and
not more weight on the first, which is the opposite of what the eyebags entry
above expected. **The palette was never the obstacle**; flat colour had somewhere
to put the shadow as soon as two tags asked for it.

**And the spiral is now the problem it solved.** At `(@_@:1.45)` it draws as a
thick near-black stroke on a white sclera — high contrast against a face whose
whole palette is pale — and the eye takes the picture. This is a composition
failure and not a drawing one: nothing in the render is wrong, the gaze just
has nowhere else to go. Note that it is the same 1.45 inherited from
`empty eyes`, and `empty eyes` is a *subtractive* tag — it takes the highlight
out. Handing its weight to an *additive* one was never like-for-like, and this
is the render that shows the difference.

`(dizzy:1.3)` is deliberately left where it is while `@_@` comes down. It argues
for the state without drawing the stroke, so it is the floor under the swirl:
if `@_@` at 1.0 loses the spiral entirely, `dizzy` is what keeps the face from
snapping back to ordinary.

Same seed, same クマ, one weight moving (`.local/dizzy_swirl.py`):

    sw130   (@_@:1.3)     f509ca7b
    sw115   (@_@:1.15)    e5039e07
    sw100   (@_@:1.0)     49b3aab4

Unjudged at the time of writing.

### `dizzy` settles at `(@_@:1.0)` — and the swirl is not drawn at 1.0

49b3aab4 picked. The block is now in `yukari_recipe.POSES` and the pose is
settled:

    (solo:1.5), (portrait:1.5), (head and shoulders:1.4), (close-up:1.2),
    (face focus:1.3), (@_@:1.0), (eyebags:1.55), (tired:1.3),
    (dizzy:1.3), (open mouth:1.35)

at 1024x1024, seed 737373737. Ten tags — one over `allnighter`'s nine, and the
extra one is `tired`, the tag that turned out to be doing the work.

**Say plainly what 1.0 costs: the spiral is gone.** Walked 1.45 → 1.3 → 1.15 →
1.0 on the one seed, and at the picked setting the irises are ordinary purple
with a small dark pupil — no drawn swirl at all. What `@_@` still contributes is
the wide flat eye and the white around it; what carries the state is the クマ,
the droop and the open mouth. So this pose as settled is **寝不足 with dead eyes,
not ぐるぐる目**, and the original request's ぐるぐる is now held only by
`(dizzy:1.3)` as a state rather than as a line. The nearest render that still
draws a visible spiral is e5039e07 at `(@_@:1.15)`; if a later session wants the
swirl back, that is the setting, and the thing it will cost is the same one that
got it turned down — the eye takes the picture.

`@_@` is kept in the block at 1.0 rather than deleted, on this file's standing
rule: it is in the accepted render, and a tag whose named effect measured null
is not removed on those grounds (the thin-line tags are the precedent). Deleting
it would ship a different picture than the one that was chosen.

Print: 11bad1ce — `--pose dizzy --seed 737373737 --hires 2048`, the same first
pass with the second at the default denoise for that upscale.

## A second costume, and `--costume` (2026-08-20)

「ゆかりさんベースで服装やポーズは変化させたい。服装はオリジナルに戻す可能性はある」.
The reference is a sporty one — grey oversized tee, denim shorts, plain black
tights, white high tops on a cyan flat backdrop — and the sentence that decided
the shape of the change is the second one: the original has to still be there.

So nothing was replaced. `CHARACTER` was split into `IDENTITY` (who she is) plus
its garments, a second set of garments was hung on the same `IDENTITY`, and the
two are selected with `--costume {default,sporty}`. A costume owns exactly three
blocks — character, legwear, hood. `FACE`, `SURFACE`, `BODY`, `THIN`, every pose
and the whole negative are shared, which is the claim being made: what changes
between them is the clothes, not her and not the drawing.

    SPORTY = IDENTITY + (
        "(grey shirt:1.45), (t-shirt:1.45), (oversized shirt:1.4), short sleeves, "
        "(denim shorts:1.45), (short shorts:1.25), "
        "vocaloid, voiceroid, "
        "(white footwear:1.4), (sneakers:1.45), (high tops:1.3)")
    SPORTY_LEGWEAR = "(black pantyhose:1.5), (opaque pantyhose:1.4)"
    SPORTY_HOOD    = "(visible hair:1.2), (purple eyes:1.2)"

**The split moved nothing.** `IDENTITY + <garments>` is byte-identical to the
`CHARACTER` that shipped, and this is not an argument, it was checked: every
pose's positive, negative and full graph (at `--hires 0` and `2048`) under
`--costume default` was compared against the same functions imported from the
previous commit, and came back identical for all 22. The fingerprint agreed
before the new blocks joined the hash — it was still `47b0d089d5a5ec77` after
the split and moved to `aa86759a39ffca43` only when `SPORTY`, `SPORTY_LEGWEAR`
and `SPORTY_HOOD` were added to `COSTUME_BLOCKS`. That is the whole reason to
hash a costume nothing has been approved in yet: the next edit to it is visible.

Three things carried over deliberately rather than by omission:

- **The leg is still ONE garment.** `SPORTY_LEGWEAR` is plain black where
  `LEGWEAR` is a purple-to-black gradient, and `LEGWEAR_BAN` still applies to
  both — the reference has tights running straight into the shoe with no sock at
  the ankle, so the six guards that keep a second garment off are as
  load-bearing here as they are there.
- **`(hood down:1.25)` is gone from `SPORTY_HOOD`.** It is an instruction about
  a garment this costume does not have, and this file's own history says naming
  an absent garment is how it gets drawn.
- **The shoes are in the costume, not in a pose.** `stand` is the only pose that
  names footwear and it names the settled costume's black high tops, so
  `pose_block()` splices that pair out under `sporty` — declared in
  `costume_check.py`, not done quietly.

### The splices had to start failing loudly

The garment splices in `positive()` match on `open cardigan`, `(drawstring:1.4)`
and `(oversized shirt:1.3)`. None of those tags exist in `SPORTY`, so under the
new costume all four would have matched nothing, done nothing, and reported
nothing — the exact failure this repo has a written rule about and has now had
two chances to repeat. `_splice()` replaces `str.replace` for them: it asserts
the needle is present, and takes a `when` flag so "this costume has no such
garment" is said outright instead of being indistinguishable from a miss.

`costume_check.py` follows: `EXCEPTIONS` now holds only the departures that are
costume-independent, `COSTUME_ONLY` holds the ones that exist because a
particular costume has the garment being spliced, and the check runs over every
(costume, pose) pair. Head framings' crop removal is generated per costume by
`_cropped()` — it names the legwear, and there is more than one legwear now.

### Guards released, and the one that was not

Three, all scoped to `sporty` alone:

- `situp`'s `(sportswear:1.45), (gym uniform:1.4)`. The guard exists because an
  exercise scene is the strongest pull off the settled costume anything here has
  asked for; this costume *is* a casual gym kit, so the guard would be arguing
  with the clothes. The `(arched back:1.4), (bridge (pose):1.3)` pair beside it
  is about her back and stays for both.
- `stand`'s `(white footwear:1.45), (red footwear:1.4)`. Its shoes are white.
- `(blue tint:1.4)`, because denim is blue.

**`(blue background:1.5)` was NOT released**, and the reason is worth writing
down because the delivered picture is meant to be cyan: the backdrop is not
prompt-stable here and is set afterwards with `recolor_bg.py`, so a blue
backdrop arriving from the prompt is still a defect, not a head start.

### `hype` — 両手ダブルピース、前傾 (2026-08-20)

    (solo:1.5), (standing:1.45), (from front:1.3), (leaning forward:1.35),
    (legs apart:1.3), (double v:1.45), (arms out:1.3), (grin:1.4),
    (full body:1.45)

Nine tags, 1024x1536. `peace` is the other double-V pose in this file and it is
a still one — hands up by the face, one V over an eye; the difference this pose
is for is the body, arms away from her and shoulders ahead of the hips.
`(arms out:1.3)` is what keeps the Vs off her face: without it `double v` is
drawn at the chin, which is `peace` again. `(grin:1.4)` puts the pose in
`open_mouthed` — a grin is drawn with teeth showing and `FACE`'s `closed mouth`
turns it back into the smirk every other pose already has.

The canvas is 1024 wide rather than `stand`'s 832: arms out to the sides need
the width, and `stand`'s narrow frame was chosen for the opposite problem.

First sweep queued at six seeds — 29d0df4a, 61fd2c81, bb35c89d, c67f05e6,
3be37c1b, 478fb1d2. Nothing measured yet; unread when this was written.

### The canvas, and the pick — 28e243ec (2026-08-20)

First sweep at 1024x1536, second at 832x1664, same six seeds, nothing else
changed. `headcount.py` on both:

| seed       | 1024x1536 | 832x1664 |
| ---------- | --------- | -------- |
| 555666777  | ONE       | 3 bodies |
| 111222333  | 2 bodies  | ONE      |
| 1886970040 | ONE       | ONE      |
| 737373737  | 3 bodies  | ONE      |
| 2557902837 | ONE       | ONE      |
| 3409564303 | 2 bodies  | ONE      |

3/6 clean against 5/6, and **that is not a result six seeds can settle** — the
narrow canvas also lost a render the wide one had. It is recorded here as the
weak evidence it is. What actually decided the canvas is that this is the same
lever `stand` was fixed with, against the same defect: width beside her is room
for a second person to stand in, and no tag in the negative has ever taken that
room away. The words were tried there and lost; they were not tried again here.

`3409564303` at 1024 is the clearest reading of the failure and the reason it
was not dismissed as a statistic: two column blocks at 51% and 46% of the
figure, each spanning ~90% of the frame height, with an empty vertical band
between them. One body cannot leave a strip like that.

Picked: **28e243ec**, `--pose hype --costume sporty --seed 1886970040`. The
canvas moved into `SIZES` before the print, and the recipe was then diffed
node-for-node against the render's own graph from `/history` — identical, so
the picked image is reproducible from the recipe and not only from the
throwaway in `.local/` that queued it. Print: ddf219a1 at `--hires 2048`.

**Print and delivery.** ddf219a1, `--hires 2048` on the picked first pass ->
`yk-sporty-hype-1886970040_00002_.png` (1024x2048). Backdrop set afterwards with
`recolor_bg.py --color '#c7e5e9'`, that value being the median corner colour of
the reference image the user posted rather than a guess at "cyan".

58.8% repainted, which is above the 45.9% this repo has on record as the point
where the tool starts eating the figure -- and it is fine here, for a reason the
share alone cannot show: the ORIGINAL colours under the repainted mask have a
per-channel std of 0.9/0.9/1.1, range 185-219. That is one flat colour and
nothing else. The 45.9% case was a tolerance widened until it bit; this one is
a taller canvas with more backdrop in it. `backdrop_flatness.py` said std 10.46,
flat, before the tool was reached for.

The share is the wrong number to screen on. The std of what was repainted is the
right one, and it is cheap.

## `roar` — がおーッ (2026-08-22)

    (solo:1.5), (standing:1.45), (from front:1.3), (claw pose:1.55),
    (hands up:1.35), (leaning forward:1.3), (open mouth:1.4), (fang:1.3),
    (full body:1.45)

Nine tags, 832x1664, first swept in `--costume sporty`. `(claw pose:1.55)` is
the tag that draws the hands and it carries the pose; everything else is there
to keep it playful rather than monstrous, which is the axis this one can fall
off. `(fang:1.3)` and not `(sharp teeth)` -- the second draws a mouthful and the
joke is one tooth. `(leaning forward:1.3)` is `hype`'s tag eased, because the
arms are already up and 1.35 was fighting nothing.

The canvas was taken from `hype` rather than re-derived: arms UP want width even
less than arms out, and until something shows otherwise the second-figure lesson
applies to every standing full body here.

First sweep, `headcount.py`: 555666777, 737373737, 2557902837 and 3409564303
ONE; 111222333 and 1886970040 flagged. Only one of the two is real --

    111222333    95.47% main, second block 2.22% at 41.3% frame height, 42px
    1886970040   54.68% and 41.61%, both spanning ~90%+ of frame height

-- and the difference between those two lines is what the 2% floor is for.
2.22% is a detached hand or a hair island clearing the cutoff, not a person;
the near-equal halves at full height are the same signature `hype` produced at
1024 wide. So 5/6, and the one failure is seed variance rather than the frame:
this canvas is the narrow one already.

Nothing picked yet at the time of writing; the sweep is with the user.

**Picked: f38695b8**, seed 555666777 -- the one the sweep's headcount had clean
without qualification. Diffed node-for-node against the recipe before printing;
identical, so nothing about it lives outside `yukari_recipe.py`.

Print: d3a4364b, `--hires 2048` -> `yk-sporty-roar-555666777_00002_.png`
(1024x2048). Backdrop `recolor_bg.py --color '#c7e5e9'`, the same value `hype`
was delivered at, 56.1% repainted at std 0.8/0.8/1.5 under the mask -- one flat
colour again, and the second time now that the share has read alarmingly high on
a tall canvas while the std said the tool never touched the figure. Two renders
is not a rule, but the pair is consistent: on 832x1664 at 2048, expect the
backdrop to be somewhere near 55-60% of the frame and screen on the std.

## The がおー family — `pounce`, `loom`, `snarl` (2026-08-22)

「今回のレパートリーのベースにがおーポーズは必須」, so the がおー stopped being a
spelling inside one pose and became a part:

    GAO_HANDS = "(claw pose:1.55)"
    GAO_FACE  = "(open mouth:1.4), (fang:1.3)"

Two fragments and not one, because `(hands up:1.35)` and `(leaning forward:1.3)`
sit between them in the order `roar` was rendered in and token order changes the
encoding. Splitting it that way is what made it a no-op, and that was checked
rather than asserted: all 23 existing poses, both costumes, `--hires 0` and
2048, byte-identical against the previous commit -- `roar` included, so f38695b8
is still the recipe's own output.

Three members, all first swept in `sporty`:

    pounce   1024x1024   crouched, a beat before it goes off
    loom     832x1664    up on her toes, arms overhead, as big as she gets
    snarl    1024x1024   the がおー with the body cropped off it

`snarl` is in HEAD_FRAMINGS -- it drops the legwear, most of BODY and the
thin-line block, and drops the legwear ban from the negative.

`pounce` has no low camera. `(from below:1.35)` is in NEGATIVE for every pose
but `lap`, and `lap` had to take it out by name; a pounce shot from below is the
obvious framing and it is not free.

First sweep, headcount: `loom` 6/6, `snarl` 5/6, `pounce` 4/6.

### 片膝 — the stance is a knee, and two tags beat one

978fb1f1 (pounce, seed 2557902837) was picked and then asked for 「片膝は着くくらい」.
That is not an adjustment: the prompt change redraws the picture, and a
low-denoise refine cannot move a limb into a new position. The squat's render
was spent knowingly. Two arms in the one slot that decides the stance:

    ka   (one knee:1.45)                    1-of-4 seeds usable
    kb   (kneeling:1.4), (one knee:1.45)    picked: 9b2dfdf6, seed 1886970040

**kb won, and it is the arm this file's usual rule argues against.** Two tags at
one defect is how the palette got wrecked twice here. This is not that case, and
the difference is worth keeping: those failures were GUARDS stacked in the
NEGATIVE, outvoting each other's neighbours. This is a stance named twice in the
positive, where `kneeling` is the posture and `one knee` is which knee. `ka`
alone drew the knee on some seeds and a deeper squat on others -- the disease
this file already describes as an unweighted tag being indistinguishable from an
absent one.

Both paws stay up and `(leaning forward:1.45)` stays. A knee down invites the
three-point stance, one hand to the ground, and that costs half the がおー.

Print: 36de43c0, `--hires 2048` (1024x1024 -> 2048x2048), backdrop `#c7e5e9`,
57.1% repainted at std 0.8/1.1/1.2 -- the third print in a row where the share
reads high and the deviation says one flat colour.

### A fifth statistic loses to the eye

`headcount.py` called the picked squat, 978fb1f1, TWO BODIES. The user picked it
by looking at it. That is the fifth image statistic in this repo to disagree with
the eye and lose, and the pattern in all five is the same: the number is measuring
something real and it is not measuring the thing it is being read as. Use it to
sort a sweep, never to reject a render someone has already looked at.

## 「じゃぎってる」 — the fringe was the tool, not the model (2026-08-22)

The `pounce` print came back jagged along every edge, and it was not the render.
`recolor_bg.py` repaints on a hard threshold, so the ring of pixels that is part
backdrop and part figure -- antialiasing, plus `(white outline:1.6)` fading into
whatever was behind it -- fails the test, keeps the ORIGINAL backdrop's hue, and
is then left sitting against a colour it no longer belongs to.

    ring +1px   25,148 px around the figure, 100.0% closer to the OLD backdrop
    ring +2px                                 99.9%
    ring +3px                                 99.9%

**Fix: set inside the mask, SHIFT outside it.** Within `--feather` pixels of the
mask each pixel moves by the same delta scaled by how much backdrop it looks
like it holds -- so the pixel keeps its figure component and only its backdrop
component changes. Setting those pixels instead would paint over the outline.

    hype      1px fringe  9.3% -> 0.3% still old hue
    roar                 99.4% -> 0.4%
    pounce              100.0% -> 4.7%

All three re-cut and re-delivered. `--feather 0` is the old behaviour and is
what everything before this was made with.

**The width is 2 and the ceiling is measured.** Genuine skin -- eroded 5x5, so a
one-pixel blend cannot qualify as skin -- is untouched at feather 2 and starts
moving at 3:

    feather 2   0 skin px shifted
    feather 3   174 px, worst channel move 25
    feather 4   425 px, worst 25

The first attempt to measure this was wrong in a way worth keeping. Counting
pixels within 16 of the skin swatch said 14,176 were tinted at feather 2 --
because the blend between the white outline and the backdrop lands at about
(239,231,231), which is inside that swatch. The number was real and it was not
counting skin. Erode before you count.

**Null: the colour ramp cannot separate skin from fringe.** Tightening
`--feather-tolerance` to buy a wider band was tried and is worse in both
directions at once -- the fringe comes BACK and the skin does not improve:

    feather 3, tolerance 54   ring2 11.7%  ring3 16.6%  skin 174 px
    feather 3, tolerance 45   ring2 46.2%  ring3 49.6%  skin 174 px
    feather 3, tolerance 40   ring2 58.9%  ring3 65.7%  skin 174 px

The skin pixels being caught sit as close to the backdrop as the fringe pixels
do, so no threshold on colour distance divides them. Spatial width is the only
lever, and 2 is where it stops. A warm band remains at 3px and is not addressed
by this change.

### The other jaggedness was real, and it is the upscale ratio (2026-08-22)

「生成でジャギジャギになってない？」 -- and yes, separately from the fringe above.
`pounce` is the only pose in this file whose print is a **2.0x** upscale: its
canvas is the 1024x1024 square, so `--hires 2048` doubles both axes. Everything
else prints at about 1.23x (832x1664 -> 1024x2048).

Measured on the left silhouette edge, per row: `stair` is the run length of an
unchanged edge x (long runs on a slanted edge are a visible staircase), `AA` is
how many partial pixels the backdrop-to-figure transition takes.

    pounce 2048 d0.60 (shipped)   stair mean  5.8 max 67   AA 2.15   hard-step 14.9%
    pounce 2048 d0.70             stair mean  2.1 max 53   AA 1.27   hard-step 19.3%
    pounce 1536 d0.60             stair mean  2.2 max 46   AA 1.34   hard-step 10.9%
    roar 2048 (1.23x, reference)  stair mean  2.0 max 38   AA 2.19   hard-step  3.3%
    pounce pass 1 (1024)          stair mean  2.1 max 31   AA 0.84   hard-step 29.2%

The staircase is the thing that failed and both arms fix it -- 5.8 back to ~2.1,
which is where a 1.23x print already sits. That supports the mechanism: at 2x,
denoise 0.60 leaves the first pass's own 1px steps stretched to 2px instead of
redrawing them, and the first pass has 29.2% hard-step rows to stretch.

**The two numbers then disagree and are recorded disagreeing.** d0.70 halves the
staircase but sharpens the edge (AA 2.15 -> 1.27, hard-step rows UP to 19.3%).
1536 is mildest everywhere and costs resolution. Which one the eye prefers is
not decided here; both were delivered for the user to pick. This file's record
on image statistics against the eye is 0-5.

`docs` note for whoever reprints a square-canvas pose: the rejected idea in the
`--hires` docstring is splitting the climb into several 1.5x STEPS. Changing the
single step's ratio is a different lever and it is not covered by that finding.

### Purely bigger: resample, because there is no upscale model (2026-08-22)

7b07fd12 (pounce, 1536, denoise 0.60) was picked and then asked to be made
larger without redrawing. `--hires` cannot do that -- it is a second diffusion
pass, which is exactly the thing being avoided -- and the worker has no upscale
model to do it properly: `UpscaleModelLoader` returns an empty options list, the
same null `LoraLoader` has. So it is a plain resample, and
`scripts/upscale_plain.py` is that, with the finding in its docstring.

    rows whose edge is a hard step, no partial pixel at all
        1536 source            10.9%
        2048 lanczos            0.9%
        3072 lanczos            0.0%
        2048 REDRAWN at 0.60   14.9%   <- the arm this replaces
    staircase run length       2.2 before, 2.2 after; the resample does not
                               lengthen the steps, it stops them being steps

Both delivered. Recolour AFTER resampling: feather 2 holds at 2048 and 3072
(1px fringe 5.5% and 3.2%, no genuine skin moved), and feather 3 at 3072 buys no
fringe while moving 218 skin pixels.

**A metric to not use again.** A "ringing" count was added to this measurement
-- rows where a pixel just outside the silhouette is brighter than the backdrop
-- to catch lanczos overshoot. It reads 39-65% on everything including the
untouched source, because `(white outline:1.6)` puts a bright ring around the
figure BY DESIGN. It was measuring the costume. Sixth statistic, same disease as
the other five: real number, wrong referent.

### 「輪郭の雰囲気とマッチしていない」 — feather 2 was tinting the white outline

The feathered edge shipped at 2px and the next thing back was that the contour
no longer matched. It was real and it was the tool again: at 2px the shift
reaches `(white outline:1.6)`, and 61,629 outline pixels went from (248,243,242)
-- warm white -- to (240,248,248). 8.3% of them stopped reading as brighter than
the backdrop at all. The die-cut edge had been painted the backdrop's new hue.

    feather 2   1px fringe 6.0% still old hue   outline moved mean 6.4  p90 21
    feather 1   1px fringe 6.0%                 outline moved mean 3.6  p90 18

**Width 1 is the whole fix**: the same correction for half the disturbance. The
default moved to 1.

**Two nulls on the same axis, and they are the useful part.** The backdrop
(223,207,206) and the white outline (248,243,242) are close enough in value that
nothing colorimetric separates them:

    matte estimate, p = a*bg + (1-a)*fg vs nearest figure   fringe back to 53.2%
    protect anything brighter than bg by +8 / +14 / +20     fringe back to 69/63/59%

The fringe IS the outline's outer blend. Repainting one without the other is not
available; only how far in it reaches is.

**A measurement bug worth naming.** The first pass at this said every variant
left the fringe at 100%, which made no sense against the earlier 4.7%. Cause:
`scipy.ndimage.binary_dilation(mask, iterations=0)` does not return the mask --
it iterates to a fixed point, i.e. floods. The 1px ring was being computed as
`dilation(m,1) & ~flood(m)`, which is empty, so the ring nothing was measured on
was also the ring nothing was corrected on. Two earlier tables in these notes
print `nan` in their first row for the same reason; the numbers beside them are
unaffected.

**Stroke width was checked first and is NOT the cause** -- the ドヤ arms redraw
the whole picture in pass 2, so the linework was the obvious suspect:

    yk1536 (accepted)  1.673 per 1000px      da  1.716
    dc                 1.587                 db  1.722

Within 3% of the accepted print. The lines did not move; the colour under them
did.

### 完成 — the delivery path for a square-canvas pose

The accepted `pounce` is three commands, and it is three because each of the
first two lost an arm to get there. Written down as a path rather than as prose,
because the middle step is the one a later session would skip:

    uv run scripts/yukari_recipe.py --pose pounce --costume sporty \
        --seed 1886970040 --hires 1536          # 7b07fd12, NOT --hires 2048
    uv run scripts/upscale_plain.py <that> --size 2048
    uv run scripts/recolor_bg.py <that> --color '#c7e5e9'

`--hires 1536` and not 2048 because this pose's canvas is square: 2048 is a 2.0x
upscale and denoise 0.60 does not cover it (staircase 5.8 against 2.1). The
pixels come back from a resample instead, which adds no detail and takes the
aliasing off. `recolor_bg.py` last, at its default feather of 1.

**The ドヤ arms are not in it.** 「表情をもう少しドヤって」 was swept in pass 2 --
`HIRES_POSITIVE`, so the picked composition survives -- with `kick`'s settled
smirk cluster:

    da  (smug:1.3), (confident:1.25), (half-closed eyes:1.25)   89a18a8d
    db  the same at 1.45 / 1.35 / 1.3                           d38b496e
    dc  (smug:1.4), (confident:1.3), no half-closed eyes        c4722f13

all three banning `(closed eyes:1.4)` in pass 2. None was picked and the recipe
was not changed, so `pounce` still has no smug tag. The mechanism is worth
keeping either way: a facial correction in pass 2 costs nothing and does not
touch the composition, and the stroke measurements above say it does not move
the linework either. If the ask comes back, start from `dc` -- the がおー has its
eyes wide and the half-closed pair is the part most likely to be fighting it.

## `straw` — ストローで紙コップのドリンク (2026-08-22)

    (solo:1.5), (standing:1.45), (from front:1.3), (holding cup:1.45),
    (drinking straw:1.55), (drinking:1.3), (full body:1.45)

Seven tags, 832x1664, swept in `sporty`. Built on `sip`'s measurements rather
than on `sip` itself -- that pose is a side-on squat with a china mug and shares
nothing with this but the fact that something is being drunk.

Two of those measurements carried straight over and one was overturned:

- **`drinking` is what lifts the vessel to the mouth.** Kept. `holding cup`
  places the cup in her hand and says nothing about where the hand goes; the
  sweep that dropped `drinking` put the can at her feet in four of four.
- **`holding cup` alone draws a paper cup or a can.** Which is the vessel this
  pose wants, so the noun came nearly free where `sip` had to spend a slot on
  `coffee mug` to get china.
- **Naming the vessel twice was NOT worth it here.** `(disposable cup:1.5)`
  beside `holding cup` was swept against four seeds without it, and 9082bedc was
  picked off the arm WITHOUT. The second noun bought nothing this pose needed --
  it is the tag `sip` had to pay for china, and a paper cup is what the model
  reaches for unaided. One slot back.

Headcount 4/4 on both arms, 8 of 8 overall. Arms at her sides instead of out is
apparently worth more than any canvas argument: the がおー family, with arms up
or out, ran 3-of-6 to 6-of-6 on the same seeds.

The cup comes out plain because `(logo:1.4), (print:1.35)` are already in
NEGATIVE -- a guard written for her clothes, doing unrelated work. Worth knowing
before someone deletes it.

Picked: 9082bedc, seed 1886970040, diffed node-for-node against the recipe.
Print: c91d2a66 at `--hires 2048`. **No resample step here**: this canvas is
832x1664, so 2048 is a 1.23x upscale rather than `pounce`'s 2.0x, and denoise
0.60 covers it.

## `ride` — ロードバイク (2026-08-22)

    (solo:1.5), (riding bicycle:1.5), (road bicycle:1.45), (bicycle:1.4),
    (from side:1.4), (leaning forward:1.3), (full body:1.45)

Seven tags, **1536x1024**, swept in `sporty`. Written against the vessel grammar
`sip` and `straw` worked out, because a bicycle is that problem one size up: an
object that has to be both in the picture and under her, with a type that has to
be pinned.

- `(bicycle:1.4)` puts one in frame and does nothing else. That is `holding
  cup`, and the sweep that trusted an object tag to imply the action found the
  can at her feet in four of four.
- `(riding bicycle:1.5)` is this pose's `drinking` -- the tag that says where
  she is in relation to the object -- and it is weighted above the noun for it.
- `(road bicycle:1.45)` is the second naming, and here it IS worth the slot,
  which is the opposite of what `straw` concluded an hour earlier. A paper cup
  is what the model reaches for unaided; a road bike is not, the default bicycle
  has flat bars. The two poses do not disagree: the rule is that the second noun
  is worth a slot exactly when the default vessel is the wrong one.

**The canvas spends the second-figure protection**, knowingly: 832 wide is what
keeps a second person out of the standing poses, and there is no way to shoot a
bicycle side-on in a narrow frame. Headcount came back 6/6 ONE anyway, with zero
sub-2% blocks -- though on this pose that number means very little, because the
bike is connected to the figure and the mask reads them as one mass.

### Null: circles do not count wheels

Wheels are circles and opencv is in the env, so `cv2.HoughCircles` was tried as
a way to count bicycles without opening the renders -- 0 wheels no bike, 2 one
bike, 4 two bikes. It does not work. Over the six seeds, at minDist h/4 and
radii from 0.12h to 0.40h, it found **5 to 9** wheel-sized circles per render
with radii from 135 to 408. It is fitting heads, hips and the arcs of the
backdrop.

Recorded rather than tuned. Tightening `param2` until the count reads 2 would be
fitting the measurement to a conclusion nobody has looked at yet, and this repo
has six statistics on file that were real numbers pointed at the wrong referent.
This is not a seventh; it is the one that was caught before it was believed.

## `swelter` — 暑くて床でジタバタ、真上から (2026-08-22)

    (solo:1.5), (lying:1.45), (on back:1.5), (from above:1.45),
    (flailing:1.4), (motion lines:1.3), (sweat:1.35), (open mouth:1.35),
    (full body:1.45)

Nine tags, 1536x1024, swept in `sporty`. `flop` is this body position at rest
and `prone` is the from-above camera that already works at this canvas; what is
new is motion and a reason for it.

**The heat is two tags and neither is a thermometer.** `(sweat:1.35)` and the
open mouth. `dizzy` and `allnighter` both arrived at the same thing from
different directions -- a STATE is drawn on the face, not named in the air --
and there is no `hot` this model draws as heat rather than as blush.

**The one pose whose flat backdrop is not a compromise.** Shot straight down,
SURFACE's `(simple background:1.3)` IS the floor she is lying on. Every other
pose in this file is standing in front of nothing; this one gets a setting for
free by pointing the camera at the ground.

### `headcount.py` cannot read a pose with motion lines

Not the failure its docstring warns about -- that one is about 1-4px slivers and
the 2% floor handles it, which is what the 12 to 23 ignored blocks per render
are. The new failure is the other end: **a dense bundle of motion lines is a
connected mass big enough to clear the floor.**

    111222333    84.06% main + 7.95% (58% of frame height) + 2.01%
    2557902837   84.91% main + 10.26% (79% of frame height)
    3409564303   75.99% main + 18.37% (99.9% of frame height) + 2.15%

Three of six flagged, and nothing in the tool can say whether those blocks are a
second girl or a fan of speed lines. The 2% floor was set from "the smallest
chibi clone on record is several percent" -- it was never an argument about
line-work, and 18% of the figure being lines is not something the number knows
how to be wrong about.

Do not raise the floor to make this pass. On a pose that draws marks as part of
its subject, this tool answers a different question than the one being asked.

### `swelter` settles at fifteen tags, and the subject was misread twice

The block reached EIGHTEEN tags chasing two reference images, and then came
back down. Both references were tantrum illustrations -- 「暑いので大暴れは
していないです。微動」 is the pose. `(motion lines:1.45)` and `(kicking:1.4)`
came out and `flailing` went 1.55 -> 1.25: the whole violence axis, turned down.

**A camera tag outlived the pose it was for.** `(foreshortening:1.3)` was added
while the leg was being snapped up, to draw a limb thrown at the viewer, and it
was right then. When the knee eased 1.55 -> 1.35 nothing removed it, so a camera
distortion was being applied to a leg that is barely raised, and 「足の長さが
不自然」 was the result. Three arms:

    ra   foreshortening out                    d35a67f8's sibling
    rb   ra + BODY (petite:1.2) -> (petite:1.4)   PICKED, seed 111222333
    rc   foreshortening kept, (long legs:1.4) added to the negative

`rc` is the lexical route and it is not the one that worked. This file has many
notes about a tag being wrong; this is its first about a tag whose supporting
setting was pulled out from under it, and the shape to remember is that the tag
did not become wrong -- its precondition left.

`petite` 1.2 -> 1.4 is `prone`'s from-above easing pointed at length instead of
bulk, and it is declared in `costume_check` as such.

### A splice failed silently in a scratch script, and shipped a picked render

6ce36efe was picked, and its prompt contains BOTH `closed mouth` AND
`(open mouth:1.35), (screaming:1.4)`. Cause: the `.local/` arm patched FACE
first --

    FACE ends  "... closed mouth, small mouth, looking at viewer"
    minus "small mouth, "        -> "... closed mouth, looking at viewer"
    minus ", looking at viewer"  -> "... closed mouth"          <- no trailing comma

-- and then `positive()` ran its own `.replace("closed mouth, ", "")`, which
matched nothing and said nothing. The recipe's `_splice` asserts and would have
caught it; the scratch script did not use it.

**`_splice` was written for the recipe and the scratch scripts are where the
failure actually lives.** The recipe's splices are read by `costume_check` on
every run; a throwaway arm is read by nobody. Use it there first.

Left unresolved: whether the accidental mouth was better. `(open mouth:1.35)`
and `closed mouth` in one prompt is a tug-of-war that lands the mouth somewhere
in between, which is a lever this file does not otherwise have. It was not
adopted, and it was not dismissed either.

### Print: 1.33x is fine for the staircase and bad for the edge

00062a2d, `--hires 2048` from the 1536x1024 canvas -- a 1.33x upscale, between
`roar`'s 1.23x and `pounce`'s failed 2.0x.

    swelter 2048 (1.33x)   stair 1.8/53   AA 0.96   hard-step 26.2%
    roar    2048 (1.23x)   stair 2.0/38   AA 2.19   hard-step  3.3%
    pounce  2048 (2.0x)    stair 5.8/67   AA 2.15   hard-step 14.9%

The staircase is fine -- 1.8 is better than the reference print. What is not
fine is the edge itself: AA 0.96 means the transition takes ONE pixel, and 26.2%
of rows have no partial pixel at all, the worst number on file. The two failures
are not the same failure, and the ratio only predicts the first one.

Delivered as it is, at 56.3% repainted, std 2.5/3.9/3.7 under the mask -- higher
than the three prints before it but still one flat colour. If the edge reads
hard, the fix is not another ratio: it is to print LARGER than the delivery size
and resample DOWN, which is the one antialiasing route this repo has not tried.

**Accepted: 00062a2d**, `--pose swelter --costume sporty --seed 111222333
--hires 2048`, backdrop `#c7e5e9`. Delivered direct -- no resample step.

And the edge number lost. 26.2% hard-step rows is the worst figure this file has
recorded, it was put in front of the user with that said plainly, and the render
was taken as final anyway. **Seventh statistic to disagree with the eye and
lose.** The supersampling route -- print larger than the delivery size, resample
down -- stays unbuilt: it was proposed on the strength of this number and the
number was not describing anything anyone could see.

What the number IS good for is unchanged: comparing two arms of the same pose.
`pounce`'s 5.8 staircase against its own 2.1 arm was a real difference and the
eye agreed. Across poses, against a threshold, it has now failed twice.

## Dropped: a head-only ドヤ icon (2026-08-23)

Abandoned before anything was judged -- 18 renders swept, none picked, nothing
committed to the recipe. Two things came out of it that are worth not
rediscovering.

**`(portrait:1.5)` asks for shoulders.** Danbooru defines `portrait` as an image
showing the head AND SHOULDERS. It is the same instruction as
`(head and shoulders:1.4)`, which sits beside it in `portrait`, `allnighter`,
`dizzy` and `snarl` -- every head framing in this file names the crop twice. For
those four that is harmless, because all of them want a collar in frame. For a
head-only icon it is the tag doing the damage, and it was left in for a whole
round because it is what every other head crop is built on.

**Banning the body in the negative did nothing.** `(neck:1.35),
(shoulders:1.4), (upper body:1.4), (body:1.3)` was reported as not working at
all. Consistent with what this file already knows -- `stand`'s second figure was
fixed by the canvas after the words lost, and the shorts that could not be
banned had no tag to outvote -- but worth having as its own line, because the
body is not a stray defect here, it is what the framing is asking for.

Untested and still open if this is ever picked up: pushing the crop by weight
(`close-up` 1.6, `face focus` 1.5, no `portrait`), `(head only:1.45)`, and the
user's own idea, `(yukkuri shiteitte ne:1.3-1.5)` -- a yukkuri IS a head with no
body, which makes it a third kind of instruction: not forbidding the body, and
not framing it out, but naming an entity that does not have one. All three were
rendered and none looked at.

## A second marker outline, in purple, outside the white one (2026-08-23)

Asked for: the drawing already carries a white marker band around it, and it
should get a purple one -- Yukari's colour -- along that band's outer edge.

**This is a post-process, not a tag, and the reason is the same one that made
`recolor_bg.py`.** Danbooru's outline tags name *an* outline; there is no
vocabulary for two concentric bands at stated widths in a stated colour, and
`(white outline:1.6)` is already at the weight it needs. A second colour asked
for by words would drift with the seed exactly the way the backdrop does. So
`scripts/outline_stroke.py` draws it: the same border flood plus enclosed
pockets that the repaint uses, a distance transform outward from the figure,
and a band painted into backdrop pixels only. Nothing under the drawing is
touched, and nothing is removed -- which is the line this repo draws between
post-processing that is allowed and a crop that is not.

**Measured on the accepted `swelter` print (`00062a2d`, 2048x1368):** walking
inward from the backdrop edge, the figure's own white marker is still 90%+
near-white at 9px in, 80% at 12-15px, and does not fall past 75% until 15. So
the band the model paints is roughly 15px at 2048 wide -- call it 0.7% of the
long side -- and a purple stroke of 10-14px sits against it as an equal, 6px as
an accent. `--width-pct` exists because the number is a share of the print, not
a constant: the same picture at 1024 wants half of it.

The purple was sampled rather than chosen. The hair's median is `#f6d7fe`, far
too pale to read against a `#c7e5e9` backdrop; the most saturated tenth of the
hair -- its shadow and accent side -- is `#b57acb`, and that is a colour already
in the picture. `#9256b8` is the same hue pushed to marker weight.

The outer edge of the band ramps over one pixel. A hard step against a flat
backdrop is the exact fringe `recolor_bg.py --feather` was written to stop, and
it would arrive by the same route.

Order matters: recolour first, then stroke. The stroke finds the backdrop by
flooding from the corner, so it has to run against the colour that is staying.

**Picked: `#9256b8` at 6px on 2048** -- the thinnest of the four arms, and the
deeper of the two purples. The equal-weight 12px band and the 22px one both
lost. What the stroke is for is a second edge you notice after the drawing, not
a second edge competing with the white one.

**And it is a per-picture number, not a setting.** 「これは絵の雰囲気で変えるべき
だと思った」. So the script defaults to the pick and stops there: `--width-pct`
0.3 and `#9256b8`, both overridable, with no attempt to bake a stroke into the
delivery path. A busier drawing, or a darker one, may well want the 12.

## Two asks in one message: the effect lines, and the purple line that was never there (2026-08-23)

「効果線は削除して　あと紫線がなくなった」. They are not the same kind of thing and
the second one is not a regression.

**The purple line is a post-process.** `outline_stroke.py` runs after the
render, so a prompt_id posted by `post_renders.py` has never carried one and
never will -- the channel shows raw renders, and the picture that was approved
was three commands further on. That gap is a real failure mode of this workflow:
a sweep gets judged against a delivered image it is not allowed to look like.
`scripts/deliver.py` closes it -- fetch, repaint, stroke, post, in that fixed
order, calling `recolor_bg.repaint` and `outline_stroke.stroke` at import level
so the result is what those two CLIs produce with their own defaults. Both
functions were split out of their `main()` for this and both were checked
byte-identical against the already-delivered file first.

**The effect lines have no tag asking for them.** The 微動 round took
`(motion lines:1.45)` out of the pose block and they came back anyway: the model
draws them from `flailing` and `screaming` as a matter of convention. So the
negative is the right side here, and this is the opposite of the cases this file
keeps losing on -- `(long torso:1.4)` moved a proportion by nothing and the
two-layer leg had no tag to outvote, but a speed line is a drawn object with a
name. `(motion lines:1.5), (speed lines:1.5), (emphasis lines:1.45)`, three
names because the model does not treat them as one and the burst behind the face
is `emphasis lines` specifically.

**The flat-backdrop share does not decide it, and is recorded as the weak
measurement it is.** Lines are drawn on the backdrop, so they cut the flood into
pieces; same seed, guard off (sa) against guard on (ta):

    seed          sa      ta      tb (also no `flailing`)
    1886970040   49.8%   48.5%   53.1%
    555666777    29.3%   38.6%    0.1%
    111222333    19.5%   21.7%   37.7%

ta moves the right way on two seeds of three and by nothing on the third. That
is not a result. tb's 0.1% is worth more than its wins: with `flailing` gone
that seed drew a backdrop that will not flood at all, which means the delivery
step cannot repaint it -- the pose was holding the plain background up. Read
within a seed only. Across seeds this measures the composition, which is the
mistake this file has made seven times.

Delivered through `deliver.py` rather than posted raw, which is the point of it.

## The arm that was never painted, and the pass that would not paint it (2026-08-23)

「9603280e の右腕が変な色になってる」. It is not a colour. Measured on that
render: the forearm thrown over her head sits at (255,243,240) against a cheek
at (250,230,233) and a backdrop at (238,225,230) -- lighter than her skin and
17 from the backdrop -- with the line around it drawn in pink-red instead of the
near-black the rest of the figure uses. **The flat was never laid down.** The
limb is sketch lines on paper, which is why it reads as belonging to a different
drawing rather than as a wrong hue.

Worth keeping as a diagnosis pattern: "wrong colour" and "no colour" look the
same in a thumbnail and are not the same defect. The tell is the LINE. Every
painted part of this recipe is outlined near-black; the unpainted arm is
outlined in the pink-red the model roughs with.

**Pass 2 at 0.60 does not fix it, and that is the finding.** Three arms, same
seed, same picture:

    ua   --hires 2048, nothing else                 arm still unpainted
    ub   ua + HIRES_NEGATIVE `(sketch:1.45), (lineart:1.45),
         (unfinished:1.4), (monochrome:1.35)`       arm painted, hand painted
    uc   ua at denoise 0.70                          arm painted

0.60 redraws the picture and it redrew this one with the same hole in it. The
white region is internally coherent -- it has its own linework -- so there is
nothing for the second pass to resolve unless it is told the region is wrong.
Naming the state does that, and it is a pass-2 negative, so the composition the
user picked is not re-rolled. 0.70 gets there too, by redrawing more of the
picture; it is the blunter of the two and it moves things that were not asked
about.

This corrects nothing earlier in the file but it does bound something: the note
that a refine cannot rebuild structure is about geometry. An unpainted region is
not structure, and it IS reachable at 0.60 -- with a word.

**Settled on ub: `174ce1dc`.** Both changes are in the recipe -- the pass-2
guard in `HIRES_NEGATIVE["swelter"]`, and `(flailing:1.25)` out of the pose
block. Checked the way this file requires: `yk.build("swelter", 1886970040,
hires=2048, costume="sporty")` was compared node for node against
`/history/174ce1dc`, every input bar the filename prefix, and matches.

So `swelter` now runs 14 tags, and the whole ジタバタ axis is spent: the motion
lines are guarded in the negative, `flailing` is gone from the positive, and
what is left doing the work is `knee up`, `spread legs` and `arm up`. If a later
round wants the motion back, it is the guard that comes out first, not the tag
-- the tag costs a floodable backdrop on at least one seed and the guard costs
nothing measured.

## テヘペロ, and a shoe with no foot to stand on (2026-08-23)

New pose `tehe`, settled off c08034a0 and its two corrections.

**`;p` is one token for the whole face and it lands.** Danbooru's emoticon tags
name a complete expression -- this one is a wink with the tongue out -- and it
drew both halves on the first sweep, judged against an arm spelling the same
face out as `(one eye closed:1.45), (wink:1.35), (tongue out:1.5)`. Kept beside
`(tongue out:1.4)` rather than alone: the emoticon decides the face and the
second tag keeps the tongue from being a detail it can drop. This is the first
emoticon tag in the file and the cheapest expression in it.

**`(v:1.6)` against `(hand on own cheek:1.15)`, and the weights are the whole
finding.** At 1.45/1.4 the cheek tag won outright and drew an open palm with
splayed fingers -- no V anywhere. `hand on own cheek` DESCRIBES an open palm, so
the two tags name different handshapes for the same hand and whichever is
heavier gets it. Inverted, the V is the shape and the cheek is only the place.
The general form is worth carrying: a placement tag that implies a handshape is
not neutral about the handshape.

`(upper body:1.35)` where the other head framings carry `(close-up:1.2)`. This
is the only crop in the file with a hand ON the face rather than beside it, and
at `close-up` the top of her head was outside the frame. It pays twice: the
backdrop share went from 7-30% to 30-41%, and `deliver.py` needs a floodable
backdrop.

**A shoe was floating in the backdrop, and it is this file's own rule catching
the file out.** c08034a0 drew a white high-top sneaker beside her head,
correctly rendered, attached to nothing. The head framings already drop LEGWEAR,
BODY and THIN because naming what is out of frame invites it back in -- but
`sporty` carries its shoes in the CHARACTER block, which no crop touched. Every
head framing under that costume was doing this. Removed now for all of them, and
removed rather than substituted: `swelter` swaps in `(no shoes:1.35)` because
its feet are in the picture, and here there is no foot at all. Measured: the
figure was 7 islands with a 1.77% one beside her head, and is 1 island now.

**The purple stroke was measured against the wrong thing.** 「大外の紫を復旧し
て」. It shipped as 0.3% of the longest side, and the white band it is supposed
to sit against is not a share of the canvas at all -- 19.2px on a 2048 print,
13.2px on a 1024 head crop, i.e. 0.94% of one frame and 1.29% of the other. A
constant share of the canvas makes the stroke thinnest exactly where the band is
thickest, which is why it vanished on a head. `--width-band` is the default now,
at 0.32, the share that reproduces the picked 6.1px on the picture the four arms
were judged on.

**And the band has to be measured to the LINE, not to the white.** The obvious
version -- walk in from the backdrop counting bright unsaturated pixels -- has
no threshold that works here: `(pale skin:1.25)` puts her face at (250,240,225),
brighter and barely more saturated than the band at (248,243,242). It also read
1px on any repainted image, because `recolor_bg`'s 1px feather tints the
outermost ring and that alone failed the test. The band's inner edge is
unambiguous -- it is the figure's own black outline -- so `band_thickness` takes
the median distance from the backdrop contour to the nearest dark pixel. Stable
across the repaint: 19.2 against 19.2, 13.2 against 13.0. Median, not mean:
parts of a contour have no line near them and read in the hundreds; the accepted
print's quartiles are 16 and 98.

## `tehe` is a square canvas, so its print is 2.0x, so it staircased (2026-08-23)

「ジャギジャギしてる」 on the tehe print, and this is a repeat, not a new
problem: `tehe` sits on the 1024x1024 square like `pounce`, so `--hires 2048`
doubles both axes. That ratio is already recorded as the one that breaks the
staircase, and the same measurement says the same thing here.

**`scripts/edge_profile.py` exists now.** The numbers quoted in the `pounce`
entry came from a throwaway in `.local/` that is gone, so they could not be
rerun -- which is the argument for the file. It also fixes a real bug in the
first version: the AA window was a fixed distance band, and a fixed band counts
the whole `(white outline:1.6)` (35 from the backdrop) and reports an AA of 30
pixels, which is the band's width and not a blend. It measures the ramp against
the value the ramp climbs to now, per row.

    tehe 2048, 2.0x, d0.60        stair mean 6.6 max 81   AA  6.5   hard  8.5%
    tehe pass 1, 1024             stair mean 3.8 max 32   AA 16.5   hard  0.6%
    swelter print, 1.33x          stair mean 1.8 max 54   AA 14.4   hard  0.3%

    ya  2048 at d0.70             stair mean 3.6 max 41   AA  3.8   hard 19.9%
    yb  1536 at d0.60, 1.5x       stair mean 3.8 max 69   AA 17.9   hard  0.7%
    yc  yb resampled to 2048      stair mean 3.8 max 87   AA  1.9   hard  3.3%

`pounce` measured 5.8/67 at 2.0x against 2.0 at 1.23x. Same failure, same
ratio, and the same trade at the bottom: **0.70 halves the staircase and pays
for it in hard-step rows** -- 8.5% to 19.9% -- exactly as recorded there. 1536
is the softest edge and costs resolution; resampling it back up returns the
pixels without letting the model near the picture again.

The purple stroke is not the cause and was checked rather than assumed: the raw
render measures jagged before any delivery step runs, and the stroke's own outer
edge is ramped over a pixel by construction.

All three delivered at a matched 7px stroke so the only difference on the sheet
is the render. Which one the eye prefers is not decided here; this file's record
on image statistics against the eye is 0-7.

**Standing note for square-canvas poses.** `pounce`, `snarl` and `tehe` are on
1024x1024, so every one of them prints at 2.0x and every one of them will do
this. It is a property of the canvas, not of the pose.

## 指が正常化するまで: 40 renders at 1024, and the answer was the seed (2026-08-23)

「一旦解像度を落として指が正常化するまで頑張って欲しい」. Pass 1 only, 1024,
judged off hand crops rather than off whole renders -- `.local/handcrop.py`
takes a fixed window at x 0.15-0.60, y 0.25-0.80, which is where this framing
puts the hand on every seed rendered so far. Nine crops tile into one sheet.

**The clever version of that crop is worth recording as a null.** Find the hand
as skin that is also THIN -- open the skin mask with a disk wide enough to
swallow a finger and subtract -- and it finds hair. `(light purple hair:1.25)`
highlights sit close enough to `(pale skin:1.25)` that no tolerance separates
them and still keeps the fingers. The fixed window is not a shortcut, it is the
thing that works.

**The hand guard moved into the PASS 1 negative for the sweep.** It had been in
`HIRES_NEGATIVE`, which is invisible at 1024, and a sweep judged at 1024 has to
be looking at what it is testing.

Three levers, six seeds each:

  * **`(clenched hand:1.2)` is dead.** It fixes the knuckle count by removing
    the V -- five of six seeds drew an open palm or a fist at the cheek. A V IS
    a fist with two fingers out, and saying `fist` gets a fist. This is the
    same shape of failure as `hand on own cheek`, from the opposite side.
  * **Dropping `hand on own cheek` draws the best hands and puts them in the
    wrong place.** The hand leaves the cheek for the neck or the chest and two
    of six left the crop entirely. So that tag is buying placement and paying
    in handshape -- a trade to price, not a tag to delete.
  * **Weight barely matters between 1.05 and 1.15.** Nine more seeds at each:
    the same two draws are good in both arms and the same seven are bad in
    both. That is the finding. **At this point the hand is the seed.**

2020202020 and 343434343 draw a V with two fingers up, a thumb tucked across
and a knuckle line that counts. Taken to 2048/d0.70 with the guard in both
passes, 2020202020 holds in both arms and **343434343 drew a second figure at
print size** -- the failure `stand` recorded against a taller canvas, arriving
here through the upscale instead.

Delivered: `9b33b436` (cheek 1.15) and `631e7cd1` (cheek 1.05), both on
2020202020, both 2048/d0.70, purple matched at 7px.

Not in the recipe: `tehe` still carries `(v:1.6)` with no hand guard. What is
waiting on a pick is `(v:1.45)`, the cheek weight, and whether the guard belongs
in the shared negative or only in pass 2.

## `tehe` settled: the emoticon that worked is the one that had to go (2026-08-23)

「舌出し止めて」 on a8efbbdc, then 「ベースのモデルでいいよ」. Settled on that
render's seed and composition, 1357913579, with the mouth shut.

**`;p` was chosen because it carries a wink AND a tongue in one token, and that
is exactly why it could not survive the tongue being cancelled.** An emoticon
names a whole expression; there is no half of `;p` to keep. So the face is
spelled out after all -- `(one eye closed:1.45), (wink:1.35), (smile:1.35)` --
which is the arm this file would have picked in the first round if the tongue
had never been asked for. The first round's finding still stands and is worth
keeping in that shape: **an emoticon tag is the cheapest way to draw a compound
expression and the most expensive one to edit.**

`tehe` leaves `open_mouthed` with the tongue -- it was only ever in that list to
let a tongue through FACE's `closed mouth` -- and its `closed mouth` departure
comes out of `costume_check`. A stale declaration and an undeclared exception
fail that file the same way.

Two other arms were rendered on the same seed and both work, if the expression
is ever re-opened: `(open mouth:1.25), (smile:1.3)` for the cheerful version,
and dropping `smile` for the flat one.

**The hand guard moved into pass 1, and the ORDER of it was caught by the
reproduction check.** Prepending versus appending five negative tags reproduced
every other node of d2106e99 and differed on exactly one, which is the check
doing the job it exists for -- this file has already recorded that token order
changes the encoding, which is why the がおー parts are two fragments. Both
guards are prepended now, hands in front of tongue, because that is the order
the sweep ran in.

**The square canvas did not staircase this time.** `tehe` is 1024x1024 so its
print is 2.0x, and the entry above says that is the ratio that breaks the
staircase. Measured on the settled print at 2048/d0.70: stair mean 2.0, max 68,
hard-step 0.1% -- level with the 1.33x `swelter` print at 1.8 and 0.3%. So 0.70
is not a workaround for that pose, it is the print setting, and `--hires-denoise
0.70` is part of how this pose prints:

    uv run scripts/yukari_recipe.py --pose tehe --costume sporty \
        --seed 1357913579 --hires 2048 --hires-denoise 0.70
    uv run scripts/deliver.py <prompt_id>

Delivered: `21c7a32a`. The recipe rebuilds `d2106e99` node for node.

## It is not the resolution, it is the redraw (2026-08-23)

「解像度を上げると途端に指の数がバグる」. Correct, and the mechanism is narrower
than "resolution": the second pass does not enlarge a hand, it draws a new one.
At 2048 the hand has four times the pixels and the model fills them with its own
idea of a hand rather than with the hand that was there.

Measured on 2557902837, one composition, four routes, same crop:

    1024 pass 1                 a correct V: two fingers up, thumb across the
                                folded ring and little finger, knuckles count
    lanczos to 2048             the same hand, bigger. Identical
    2048 / d0.70                wrecked: extra digits, tangled folds, a stray
                                finger at the hairline
    1536 / d0.60                also wrecked, differently

**Both denoises and both sizes break it, and the resample does not touch it.**
So `upscale_plain.py` is the print route for this pose, and the reason is
structural rather than a setting to tune: a hand is the one thing in this
picture whose correctness is combinatorial -- four fingers and a thumb in a
specific arrangement -- and 0.60 is enough freedom to rearrange it. A flat that
was never laid down (see the `swelter` arm) is the opposite kind of defect, and
that is why pass 2 fixes one and breaks the other. **Pass 2 is for paint, not
for anatomy.**

What it costs is real and is not hidden: lanczos adds no detail, so the print is
a 1024 drawing at 2048. On this style that is cheap -- flat colour, thin lines,
nothing photographic to lose -- and the edge measures better than the redraw:

    lanczos 2048    stair mean 1.8 max 30   AA 1.93   hard  0.0%
    2048 / d0.70    stair mean 1.9 max 39   AA 0.79   hard 30.6%

**Two more things fell out of the round and both are worth having.** At 2.0x,
d0.45 and d0.60 leave visible RGB fringing along every edge and 0.70 does not,
so the denoise on a square-canvas print is not free to come down for the hand's
sake -- another reason the answer is to not redraw at all. And d0.70 at 2.0x
**re-frames**: the print is visibly tighter on the head than its own pass 1. A
second pass at that denoise is not a refinement.

**And a correction to the round before this one.** 1357913579 was settled partly
on its hand, and its hand was never good -- `.local/handcrop.py`'s fixed window
cut the hand off the top of the frame, so it read as acceptable at 460px because
most of it was outside the crop. Three ways of finding the hand automatically
have now failed (thin-skin finds hair, the fixed window silently crops, line
density finds the hair ornament), and the tool takes a window as an argument
now. **A judging tool that silently crops the thing being judged is worse than
no tool.**

Re-hunted on the settled recipe, twelve seeds: 2557902837 first by a distance,
then 192837465, 555666777, 111222333; 86753090, 979797979 and 987654321 drew a
second figure. Delivered `yk-h-tehe-2557902837-big` (lanczos) beside
`be94da12` (the d0.70 redraw) so the difference is on one sheet.

## `tehe` printed: 1536 at the default denoise, on 2557902837 (2026-08-23)

Settled: `bb0d5baa`, which is

    uv run scripts/yukari_recipe.py --pose tehe --costume sporty \
        --seed 2557902837 --hires 1536
    uv run scripts/deliver.py <prompt_id>

No flags past `--hires`. The recipe rebuilds that graph node for node with
`HIRES_DENOISE` untouched at 0.60, which is worth saying plainly: the pose needs
no print settings of its own after all. `--hires-denoise 0.70` was the arm the
staircase round reached for and it is not what shipped.

**My read of that render's hand lost, and the entry above should be read with
this next to it.** I put `bb0d5baa` on the sheet as "also wrecked, differently"
and it is the one that was chosen. What the previous entry establishes stands --
the second pass redraws a hand rather than enlarging it, and the lanczos route
preserves pass 1 exactly -- but "the redraw is worse" is a judgement, and this
project's record on my judgement of a hand at crop scale is now no better than
its record on image statistics. **What the measurement supports is that the
hands DIFFER; which one is right was never mine to call.**

The edge is fine at this size and this is a 1.5x print, not a 2.0x one:

    1536 / d0.60, shipped    stair mean 1.8 max 21   AA 8.77   hard 7.5%

Purple at 6.5px from the band default, no override.

## まつ毛: the vocabulary exists, and the weight is bracketed from above (2026-08-23)

「ゆかりさんのまつ毛をより良くしたい」, refined to **「毛量は多いが長さは均一がいいかな」**
and then to **lashK**. That second sentence is the durable part of this entry:
the criterion is dense and EVEN, not long, and a later session judging this axis
by "more eyelash" will pick the wrong arm.

`FACE` has carried a bare, unweighted `eyelashes` since the block was written
and this repo had never swept it. The one prior mention is `queue_dq3`'s
duplicate-figure suspect list, where it was named and never tested.

**The tags are real, and that was checked rather than assumed.** Against
danbooru's tag list: `eyelashes` 262k, `colored_eyelashes` 56k, `long_eyelashes`
12k, `thick_eyelashes` 7.2k. So `long eyelashes` and `thick eyelashes` are
vocabulary, not prose — thin vocabulary next to the base tag, but vocabulary.
`colored_eyelashes` being the second-largest of the group is worth remembering:
it is the common idiom for "the lashes are drawn on purpose", and it draws them
as a mass rather than as separate hairs.

Four rounds, all `portrait` at 555666777, 1024 first pass then `--hires 1536`.
The face is the largest in the file and lash width at 1024 is under the line
width this model draws with, so the second pass is not optional here.

| round | arms |
|---|---|
| 1 | A control · B `(eyelashes:1.45)` · C long · D thick · E long+thick · F colored |
| 2 | G thick 1.45 · H = G **plus `(long eyelashes:1.35)` in the negative** · I +colored · J `(eyelashes:1.55)` |
| 3 | K/L/M — H's configuration at thick 1.35 / 1.25 / 1.15 |
| 4 | Kn (K without the guard) · K2, Kn2 (the same pair on 111222333) |

**H was called right on length, ほんの少し多い on density, and K was picked.** So:

    (eyelashes:1.3), (thick eyelashes:1.35)     positive
    (long eyelashes:1.35)                       negative, prepended

**The weight is bracketed from above and that is what a later session inherits:**
1.45 is too dense, 1.35 is right, and the two rungs below it were rendered in
the same round rather than left for another round trip. Whatever is right on
this axis is at or under 1.35, and going back to 1.45 is not new information.

### Open, and it decides what enters the recipe

K, L and M all carried the guard, so **nobody has yet seen K without it**. Round
4 is the isolation — Kn against K on the settled seed, Kn2 against K2 on a fresh
one — and it is unjudged at the time of writing. It matters because the guard
would go in a negative that EVERY POSE SHARES, where the recipe's own record
says a guard is a deletion that works on drawn objects and fails on properties
(`(long torso:1.4)` moved nothing). Lash length is nearer a property than an
object, so the guard being dead weight is the outcome to expect.

`FACE` is therefore UNCHANGED so far. Nothing above is in the recipe yet, and
that is deliberate: the positive was only ever judged with the guard present, so
shipping it alone would ship a state nobody has looked at.

## 肩紐: the head framings never drew the straps (2026-08-23)

「肩紐がないね」, said of a `portrait` render. It is correct and it was not a
regression — the pose never had the splice.

Her dress is a halter whose straps cross at the chest and pass over the
shoulders; it is the official design, recorded here 2026-08-17. The tag lives in
three poses — `boss` and `stand` take `(criss-cross halter:1.45)`, `nape` takes
`(halterneck:1.45), (black straps:1.35)` — and **it was tried globally once and
dropped**, for backdrop intruders on both seeds. `stand` then took it anyway:
the straps are the design and `recolor_bg.py` repaints the backdrop at delivery.

`portrait` is a head-and-shoulders crop, so the straps are in frame, and it is
delivered through the same repaint. The backdrop cost is one it had already
paid. Three arms, K's lashes carried so the pictures were judged in the state
they were being looked at:

| | tags | |
|---|---|---|
| **P1** | `(criss-cross halter:1.45)` | **picked — e4ff4f8a** |
| P2 | `nape`'s pair | |
| P3 | P1 + `(off shoulder:1.3)` — `boss`'s actual configuration | |

**The `boss` precedent predicted a cost this pose did not pay.** `boss`'s comment
says it could afford the tag *because* its coat was already off the shoulders,
which reads as a precondition. It is not one: P1 drew the straps with the
cardigan up, and P3 — the arm built to give the strap a bare shoulder to cross —
was not needed. A constraint recorded as the reason a pose could afford
something is not automatically a requirement for the next pose.

In the recipe as a `pose == "portrait"` splice, declared in `COSTUME_ONLY`.
Costume fingerprint unchanged: this is a pose-level departure, not a block edit.

**The other four head framings are still strapless.** `allnighter`, `dizzy`,
`snarl` and `tehe` crop at the shoulders for the same reason `portrait` does and
have the same gap. They are untested, and the global attempt is the reason they
get tested per pose rather than fixed with one edit.

Delivered `#9256b8` at 24.9px — the band-relative default, not an override. The
number looks heavy against the 6px picked on `swelter`, and it is the same
accent: the width is 0.32 of the figure's own white marker, and a head crop's
marker is wide. That share replaced a share-of-canvas after 「大外の紫を復旧して」.

## `(cola:1.4)` was not needed: the vessel was already the picture (2026-08-23)

「コーラを飲んでいるゆかりさんを」, and then, having seen it:
**「コーラ言ったけど、紙コップストローで飲んでる。で十分だった」.**

`straw` already carries `(holding cup:1.45), (drinking straw:1.55),
(drinking:1.3)`, and a paper cup with a straw in it IS the picture that was
being asked for. The drink was named as a subject and answered as a tag, and
the tag was the part that was not needed.

`cola` is a real danbooru tag (1.6k) and `coca-cola` a larger one (2.5k, a brand
name and not used here), so this is not the usual "the vocabulary does not
exist" null. **The vocabulary existed and the slot was already filled.** Worth
checking before adding a tag for a named object: whether the pose block already
draws the thing under a different name.

Not in the recipe. Four arms ran in `.local` and none of them are the reason
the picture worked.

## 174ce1dc's finish does not transfer, and the two halves break the palette TOGETHER (2026-08-23)

「絵柄・塗りのベースとして」 174ce1dc — `yk-ub-swelter-1886970040`. Two things in
that render are not in a stock `portrait` and look portable:

- its pass-2 negative, `(sketch:1.45), (lineart:1.45), (unfinished:1.4),
  (monochrome:1.35)`, the guard written for the arm that was never flatted
- `THIN`, which the head framings drop with the rest of the crop

Carried onto `portrait` together they drew 「なんか色がおかしいね」. Distinct flats
in the figure, quantised to 8 levels per channel, with the backdrop excluded by
`recolor_bg`'s own mask so the count is over the drawing only:

| arm | THIN | paint guard | figure | flats |
|---|---|---|---|---|
| R1 | — | — | 94.8% | **150** |
| T2 | — | yes | 94.9% | 168 |
| T1 | yes | — | 89.5% | 190 |
| S1 | yes | yes | 94.7% | **225** |

**+18 and +40 separately, +75 together.** The pair is superadditive, and neither
half predicts it. R1 and S1 have the same figure area to within 0.1%, so this is
not the mask measuring different amounts of picture.

**The prediction was wrong and the direction of the error is the useful part.**
The guard was the suspect — it bans `monochrome` and `unfinished`, which on a
picture with nothing unflatted reads as pressure to add colour. It does do that,
by 18 flats. `THIN` does more than twice as much, on a smaller figure, i.e. more
still per unit area. Asking for thin, fine, delicate lines subdivides the flats,
and this costume's whole look is `(flat color:1.3)` — few, large flats. **THIN is
not a neutral line-weight setting; it is a palette lever**, and it has been in
every full-figure prompt in this file since it was added, described in its own
comment as "measured to do nothing to stroke width".

That comment is now two-thirds of a null: it does nothing to stroke width and it
is not doing nothing.

**What this says about porting a finish.** 174ce1dc's paint is what a deletion
left behind on a picture that had a specific defect. On a picture without that
defect the same deletion has to find something else to delete. A finish that is
the residue of a fix is not a style, and the poses that would want it are the
poses with the same defect.

Picked out of this: **T2** — the paint guard, no THIN — 547b7b91.

## `outline_stroke.py`'s band measurement is not stable enough to deliver a comparison (2026-08-23)

The stroke width is a share of the figure's own white marker band, which was a
correction: it shipped as a share of the canvas and went invisible on a head
crop (「大外の紫を復旧して」). The share-of-band fixed that case and is not stable.

Across renders of the SAME pose at the SAME canvas, differing only in eyelash
tags, the automatic width came out at:

    1536x1536 tehe    6.5px   3.5px   1.0px
    1024x2048 straw   6.1px*  2.9px   2.3px   11.3px   12.7px

\* re-run with `--stroke-width-pct 0.3`; the automatic figures are the others.

A fivefold spread, and 1.0px is the same invisible stroke the share-of-canvas
version was replaced for producing. **A sweep delivered on the automatic width
is not a comparison** — the purple varies more between arms than the thing being
compared does, which is how a delivery step starts deciding a judgement.

Worked around by passing `--stroke-width-pct` explicitly for every set above.
That is not a fix: it is a number a human has to remember per canvas, and the
whole reason `deliver.py` exists is that the three-step finish was being
forgotten. The band estimate itself is what needs looking at.

## Settled: the lashes go in, and the reference image yielded one tag (2026-08-24)

Picked: **cf978c9c**, `yk-strawX-straw-737373737` — `straw`, sporty, `--hires
2048`. Verified: `yukari_recipe.build("straw", 737373737, ..., hires=2048,
costume="sporty")` reproduces nodes 6, 7 and 7b of that render's own graph
identically, so what is below is the picture and not a description of it.

**This corrects the まつ毛 entry above**, which said `FACE` was unchanged and
that nothing had entered the recipe. That was true when it was written and is
not true now.

In `FACE`, worn by every pose:

    2000s (style), (eyelashes:1.3), (thick eyelashes:1.35), (large iris:1.25)

In `NEGATIVE`, in front, worn by every pose:

    (long eyelashes:1.35)

Costume fingerprint `aa86759a39ffca43` -> **`2940a4b4552ad646`**.

`straw` alone also gets `HIRES_NEGATIVE_PAINT` on pass 2 and gives up `THIN`,
declared in `costume_check`. Those two are a pair and the entry above says why:
apart they are +18 and +40 flats, together +75.

### The length guard is in, and it was never isolated

K/Kn on 555666777, K2/Kn2 on 111222333, and qbK/qbKn on the `tehe` render — three
pairs whose only difference is `(long eyelashes:1.35)` in the negative. All six
were rendered and delivered; **none were judged.** The picked render carries the
guard, so the guard is in the recipe by selection rather than by measurement.

Recorded plainly because the recipe's own record predicts it does nothing: a
guard is a deletion, it works on drawn objects with names and fails on
properties (`(long torso:1.4)` moved nothing), and lash length is nearer a
property than an object. If a later session isolates it and finds it inert, the
line is one line and deleting it costs nothing else. **Do not re-derive the
three pairs — they exist, they are in the history, and what is missing is a
look, not a render.**

### What the reference image actually yielded

「な方面の目がいいかな」 came with a picture, and it decomposed into four things.
Checked against danbooru's tag list rather than guessed:

| from the reference | tag | outcome |
|---|---|---|
| thick dark upper lash band | `thick eyelashes` 7.2k | **in** — and it was already picked before the reference arrived |
| bright iris highlight | `sparkling eyes` 18k | out — 「キラキラは外してほしい」 |
| purple-to-gold iris | `gradient eyes` 13k | out — and it cost the flat backdrop on 2 of 3 arms carrying it, so `recolor_bg` refused to repaint them |
| wide open eyes | `unusually open eyes` 6.1k | never judged; it also requires deleting `(half-closed eyes:1.3)`, which is the pose's expression |

**One of four survived, and it was the one already chosen.** The reference did
not add a tag to this recipe; it confirmed one. That is worth saying because the
sweep it produced was eight renders across two rounds, and the cheaper move
would have been to ask which of the four differences from the current render
actually mattered before rendering any of them.

`(cola:1.4)` went the same way one message earlier. Two asks in a row where the
named thing was already in the picture or already in the prompt.

### Correction: the length guard was isolated, and it won all three pairs (2026-08-24)

The section above says the guard is in the recipe "by selection rather than by
measurement" and predicts it does nothing. **Both halves of that are now wrong.**
The three pairs were put on two contact sheets and judged:

| sheet | pair | picked |
|---|---|---|
| `sheet-guard-portrait` | `yk-lashK` / `yk-lashKn` (555666777) | **guard** |
| `sheet-guard-portrait` | `yk-lashK2` / `yk-lashKn2` (111222333) | **guard** |
| `sheet-guard-tehe` | `yk-qbK` / `yk-qbKn` (`tehe`, sporty) | **guard** |

Three for three, across two poses, two costumes and two seeds, with the positive
identical inside each pair. `(long eyelashes:1.35)` stays in `NEGATIVE` and it is
load-bearing.

**What this corrects is not the line, it is the rule that predicted it.** This
file has said, from `(long torso:1.4)` moving nothing and the two-layer leg
having no tag to outvote, that a guard deletes drawn objects and fails on
properties. Lash length was filed under properties and the prediction was made
out loud before rendering. It was wrong.

The distinction that survives is narrower than object-versus-property:
`long torso` asks the model to un-stretch a region it does not draw as a
separate mark, while `long eyelashes` names a variant of something it draws as
discrete strokes — the same shape as `speed lines` and the dress's buttons,
which guards did remove. **A tag whose subject the model draws with its own
strokes can be guarded, whether the tag names the object or an attribute of it.**
That is a smaller claim than the old rule and it is the one the evidence carries.

Nothing to re-render: the recipe already had the guard, and the sheets only
moved it from selected to measured.

The `yk-qbK` caveat did not decide anything, and it is left standing as a caveat:
that arm repainted 53.8% against its pair's 26.5%, so the two `tehe` tiles are
not only a lash difference. The two `portrait` pairs carry this result; the
`tehe` pair agrees with them.

## The purple stroke's automatic width was measuring the tail, in both directions (2026-08-24)

The band estimate produced 1.0, 2.3, 2.9, 3.2, 3.5, 4.5, 6.5, 11.3, 12.7 and
24.9px across one day's deliveries, on renders of the same poses at the same
canvases. **A sweep delivered on it is not a comparison** — the purple varied
more between arms than the thing being compared did.

`band_thickness` takes the median, over the backdrop's contour, of the distance
to the nearest dark pixel. Its docstring already recorded that the quartiles on
the accepted print were 16 and 98 — "parts of a contour have no line anywhere
near them and those read in the hundreds" — and chose the median for exactly
that reason. **The median only protects while the tail is under half.** Share of
contour with no line within 20px, on the renders that produced the spread:

    strawX (picked)   0.3%     band 10.0    ->  3.2px
    colaU1c          18.5%     band  7.1    ->  2.3px
    qbK              37.7%     band 11.3    ->  3.6px
    qbKn             44.8%     band  3.0    ->  1.0px
    qb               57.6%     band 20.6    ->  6.6px
    portrait P1      60.7%     band 77.6    -> 24.9px
    colaU2           81.2%     band 45.5    -> 14.6px

The two past 50% are the two whose numbers are absurd — 45.5px of "band" on a
print whose band is under 20, and 77.6 on a head crop.

**The 24.9px head crop was the same failure, and nobody noticed because it broke
in the flattering direction.** It was delivered, it was not complained about,
and it was read as the band rule working. It was not: at far 60.7% that median
is distance-to-nothing. A statistic can be wrong in a way that looks like taste.

Fixed in `outline_stroke.py`, two lines of behaviour:

- `band_thickness` returns 0.0 — could not find it, rather than it is zero —
  when the far share reaches 0.5. Not a tuned threshold: it is the point at
  which a median *is* the tail.
- the canvas share is a **floor** under the band estimate rather than the rule
  it replaced. Both rules only ever failed by drawing too thin, so the larger of
  the two is never the failure mode.

Every arm of a comparison now gets the same width: 4.6px across the three
`tehe` renders, 6.1px across the three `straw` ones, where before they were
6.5/3.5/1.0 and 12.7/2.3/3.2. 6.1 is what the eye picked on cf978c9c.

### Two picked widths, and no rule fits both

    head crop, 1536    24.9px    1.62% of the long side
    full print, 2048    6.1px    0.30%

A fivefold split that nothing measured predicts. The band rule does not: on
`eyeR1`, a head crop whose estimate is *healthy* at far 9.7%, it says 3.5px —
thin, in the same direction it was thin on the prints. **There is no example of
the band rule working on a head crop**, only one of it failing upward.

So no rule was written. Head framings need `--stroke-width-pct 1.6` passed
explicitly until there is more than one data point, and under the fix their
default is the 4.6px floor, which is the value 「大外の紫を復旧して」 was said about.
That is a real regression against an accident, and it is taken deliberately:
deterministic-and-overridable beats random, and the old behaviour was random —
the same framing got 24.9 on one render and 3.5 on another.

What the difference actually is, measured between the two head-crop tiles: 1.38%
of pixels differ, 97% of them inside the stroke annulus, 965 on the figure's own
edge where the wider band's inner ramp lands, and none anywhere else. The
pictures are identical apart from the line. It reads as a larger change than
that because a contact sheet scales the tiles down and a 4.6px line nearly
disappears at 1000px wide.

## `snack`: 菓子パン, and the crop that took her shoes off her feet (2026-08-24)

菓子パンを食べるゆかりさん. Written against the vessel grammar `sip`, `straw` and
`ride` worked out, because a sweet roll is a paper cup one size down and every
slot maps:

| role | `straw` | `snack` |
| --- | --- | --- |
| puts it in her hand | `(holding cup:1.45)` | `(holding food:1.45)` |
| lifts it to the mouth | `(drinking:1.3)` | `(eating:1.4)` |
| names the type | — (a paper cup is free) | `(melon bread:1.5)` |

**The second naming is the case `ride` paid for, not the one `straw` got free.**
Bare `bread` on danbooru is 21k with `bread_slice` at 5.5k, and both draw a loaf
— neither is a 菓子パン. `melon_bread` is 1.5k, the archetype, and the only
sweet roll there with a count worth a slot: `cream_bread` 143, `curry_bread` 66.
It drew a melon roll in 8 of 8 first-sweep renders, crust hatching and all.

The chair is deliberately **not** named twice, which is the same judgement from
the other side. `chair` spends three tags (`gaming chair, swivel chair,
backrest`) because a gaming chair is not what the model reaches for; a plain
chair is, like the paper cup. One slot back.

### The crop took the shoes off her feet and put them in her hand

The first sweep ran two framings on four shared seeds: `full body` at 832x1664
(`straw`'s own frame) and `cowboy shot` at 1024x1280, on the theory that a roll
is smaller than a cup and 「the cost is that the cup is small in it」 was
`straw`'s own open question.

The `cowboy shot` arm came back with her **holding a sneaker** — 872ba604 and
39289634 plainly, 27d3e771 with a loose one on the ground beside her. 「パンを
食べてるときに靴は触っちゃダメよw」.

**This is the HEAD_FRAMINGS rule one crop shallower, and it needed a deletion
rather than a guard.** `cowboy shot` cuts at the thigh, so the sporty costume's
`(white footwear:1.4), (sneakers:1.45), (high tops:1.3)` had no referent left in
frame — and `holding food` was sitting right there as an open slot for an
object, so the orphaned tags took it. Removing the three tags fixed it 4 of 4
(and, unasked, took out the two-figure render at 1886970040 as well).

Worth keeping because the instinct is backwards here: a negative guard would
have been the obvious reach and it could not have worked. A guard deletes a
drawn object; the orphaned tag stays in the prompt and finds somewhere else to
land. What was wrong was the prompt naming something the frame had cut.

### Picked: seated, and the framing is what makes the costume honest

1903f19a, seed 1886970040, `(sitting on chair:1.45)` at 1024x1536 — the frame
every seated full body in this file uses. 「椅子に座って食べるのもOK」.

The seated arm keeps its shoes, and that is not an inconsistency: the feet are
in frame, so the tags have their referent and there is no orphan to place. The
framing is the fix, not a per-pose deletion.

In `open_mouthed`, against `straw`'s reading of the identical question — lips
close around a straw and they do not close around a melon bread. FACE's
`closed mouth` is **removed and not replaced**; nothing here asks for
`(open mouth)`, so a bite is permitted rather than a shout commanded.

Finish is `straw`'s, carried rather than re-measured: sporty, THIN removed, the
pass-2 paint guard. That is the last standing full body the user approved
(cf978c9c), and this is its sibling in the same costume. `PAINT_FINISH` now
names the two poses that carry it, because it is two edits five hundred lines
apart in `yukari_recipe.py` and half of it is a deletion — a pose that got the
guard without the THIN removal would be the exact failure the `straw` entry
warns about, silently.

Print: 7c4ecd18 at `--hires 2048`. **No resample step**: 1024x1536 to 2048 is
1.33x on the long side, the same side of the line as `straw`'s 1.23x rather than
`pounce`'s 2.0x, and denoise 0.60 covers it. Delivered at 53.0% backdrop with
the stroke at 6.1px — the print value the repaired width rule was tuned to, on
its first unattended run since the repair.

## `fitness`: a third costume, arrived at by subtraction (2026-08-25)

「服をオリジナル服（紫のワンピースのあれ）ベースのTシャツにマッシュアップできる？」
started this, and eleven sweeps later what is in the file is a gym kit: a plain
ribbed light-purple tee, ankle-length black compression leggings with a side
stripe, white high tops. Almost nothing that was tried on the way is in it.

    (light purple shirt:1.45), (ribbed shirt:1.35), (t-shirt:1.45),
    (oversized shirt:1.4), short sleeves,
    (high-waist pants:1.4), (sportswear:1.35),
    (white footwear:1.4), (sneakers:1.45), (high tops:1.3)
    legwear: (leggings:1.45), (black leggings:1.4), (skin tight:1.45),
             (vertical-striped clothes:1.35)
    negative: + (striped shirt:1.5)

Picked: d218afdc and e8dacf7e, seeds 111222333 and 737373737, `stand` at
832x1664. Both reproduce from `--costume fitness` node-for-node. Print of the
round before it: f31d220d, delivered at 67.0% backdrop, stroke 6.1px.

Fingerprint `2940a4b4552ad646` → `9c4d0da38fc1378f`, and the settled blocks are
again untouched: 32 poses × {default, sporty} × {pass 1, 2048} rebuilt against
the previous commit, zero drift.

### The colour is spelled the way IDENTITY spells it

「少し薄めの紫」 is `(light purple shirt:1.45)` — the same `light purple` that
IDENTITY has been using for her hair since the file was written, borrowed rather
than invented. One colour tag in one slot: `purple shirt` is **not** stacked
beside it. `ribbed_shirt` is 8.3k, and the rib survives `(flat color:1.3)`.

### The guard that named the rare variant

「レーススカートが透けすぎている」 on a skirt that already carried
`(see-through clothes:1.5), (see-through skirt:1.5)`. Both legs were drawn
through it, outlines and all.

NEGATIVE's own long-standing guard is `(see-through dress:1.45)`. On danbooru
that tag is **9.3k**; `see-through_clothes` is **217k** and
`see-through_shirt` is 20k. The guard has been naming a rare variant of the
thing it was written to stop, for as long as it has existed. Nothing in this
repo had ever asked it to do work before, so nothing had caught it.

### Guarding a property while banning the fix

Raising the correct guard to 1.6 was still not the answer, and the reason is
worth more than the fix: **lace is not see-through because it has a lining, and
NEGATIVE bans the lining.** `(petticoat:1.35)` and `(layered skirt:1.25)` are
both in it. The prompt was asking for an opaque sheer garment while forbidding
the only construction that makes one.

Not resolved by render — the skirt was abandoned first
(「スカート案をやめた方が良さそう」) — so this is a mechanism with no measurement
behind it yet. Recorded because the next lace or chiffon anything will hit it.

### A guard pointing the wrong way, and the length that has no tag

Two errors in one axis, both mine.

**Danbooru has no midi.** The length vocabulary is `microskirt` 27k →
`miniskirt` 381k → *(unmarked `skirt` 2.2M)* → `long_skirt` 54k. The middle
length has no name because it is the default — so "knee-length" is
`(skirt:1.45)` with no length tag, and the way to hold it there is to bracket
both ends in the negative.

**And the bracket I wrote pointed both ends the same way.** `(long skirt:1.4)`
in the negative pushes the hem UP, and the model's prior for an unmarked skirt
is already `miniskirt` at 7× the count of `long_skirt`. Guarding both ends
guarded neither: four of four came out microskirt. Measured after removing it:

| positive | hem |
| --- | --- |
| none | mid-thigh, and the oversized tee hides it |
| `(long skirt:1.1)` | mid-thigh, barely distinguishable from none |
| `(long skirt:1.2)` | mid-calf |
| `(long skirt:1.3)` | ankle; 2 of 4 came out high-low |

A cliff between 1.1 and 1.2 with the knee inside it, which is where the dial
was still sitting when the skirt was dropped.

### The variable was not the hem

Half of that measurement was junk for a reason no weight would have fixed:
`(oversized shirt:1.4)` hangs to mid-thigh, so on three of four seeds **the tee
was covering the skirt** and the sweep was reading the shirt's hem, not the
skirt's. `(high-waist pants:1.4)` is in the settled costume partly for this —
it pins the waistband, so what is below it is visible enough to measure.

Two rounds of length arms were spent before anyone looked at what was on top.

### Slit height has no tag, and `side slit` means cheongsam

「脚は見せたいがロングスカート」 resolves to `side_slit` (59k) and nothing else —
`front_slit` is 3.9k, `back_slit` 160. But **there is no tag for how far up a
slit goes**, and `side_slit`'s training mass is qipao, so it draws hip-high:
「チャイナ服感があるな」. Weighting it down removes the slit rather than
shortening it, which is why the round after that was three *constructions* with
a low opening rather than three settings of one dial.

`(chinese clothes:1.5)` (161k) is the guard for the style, not `china dress` —
what was showing up was a skirt's tailoring, not a dress.

### Three guards that a pose owned and a costume needed

The recurring shape of this whole session, and the reason the promotion took as
long as the sweeps:

- **`(buttons:1.4)` is banned by `stand` and `boss`.** 「ボタンでちゃんと留めたい」
  was a request to release a guard. It went in because her dress has no buttons
  and the cardigan reads as a shirt — a costume-shaped reason living in a pose.
- **`(logo:1.4), (print:1.35)` are `stand`-only.** The `straw` block claimed
  they were in NEGATIVE and that this is why its paper cup comes out plain.
  **They are not, and the cup is the model's own doing.** The claim was
  disproved by a render, not by reading: `snack`'s sweep put a watermelon print
  on the tee, on a pose with no such guard. Corrected in the block.
- **`(vertical-striped clothes:1.35)` needed its own.** The tag names clothes,
  not trousers, so it stripes the tee this costume spends three tags keeping
  plain. `(striped shirt:1.5)` is gated on the COSTUME, which is the same
  mistake not repeated — and it goes after the legwear ban because that is
  where the swept arm put it.

### `costume == "sporty"` in four places

Four gates were written as an equality against the only shod costume that
existed, and a third one walks past all four in silence: `stand` would carry two
pairs of shoes, and every head framing would go back to drawing a sneaker
floating in the backdrop (c08034a0). They are `costume in SHOD` now.

The two `costume == "default"` gates were already correct by luck — `situp`'s
`(sportswear:1.45), (gym uniform:1.4)` and `stand`'s white-shoe ban both had to
be skipped for this costume, and "not default" happens to say that.

### The stripe: presence pinned, hue not

The white side line arrived unasked on **one seed of four** under
`(sportswear:1.35)` alone — 「白のラインが良い！！！！」 — which is this file's
usual signature for a value the model cannot hold. Naming it
`(vertical-striped clothes:1.35)` took it to **three of four** (555666777 is the
one that comes out plain), and the shirt guard held on all four.

**The colour did not come along.** The two renders picked out of that arm are
purple-lined; the render that started it is white-lined. Presence is pinned and
hue is not, and there is no tag between them — `side-striped_clothes` does not
exist, and `striped_clothes` at 354k does not know which garment was meant.

### `(bike shorts:1.5)` was queued and withdrawn

「フィットネスパンツは？」 was answered with three arms including bike shorts, and
then the reference photo arrived: ankle-length high-waist compression leggings.
Bike shorts are a knee-length garment and a different one. The arm was cleared
off the queue before it rendered, so it cost nothing — worth noting only because
the queue was cleared twice this session for the same reason, and both times the
already-finished half was still posted.

### Correction: the loose tee is the look, not the defect (2026-08-25)

The section above ("The variable was not the hem") reads as if
`(oversized shirt:1.4)` hanging to mid-thigh were a problem to design around.
**It is the intended look.** 「服はしまってないのでふわっとしてるのが正解」, on
2bc9d8dc.

What that section actually established is narrower and still holds: while
*measuring a skirt hem*, a shirt that covers the hem makes the measurement read
the wrong garment. That is a fact about the sweep, not about the costume. The
untucked, loose tee over the leggings is what was picked, twice, and
`(high-waist pants:1.4)` earns its slot by placing the waistband — not by
tucking anything into it.

## `hoops`: バスケなんてやりたくないですよぉ〜〜〜 (2026-08-25)

    (solo:1.5), (standing:1.45), (from front:1.3), (holding ball:1.45),
    (basketball:1.5), (@_@:1.0), (wavy mouth:1.4), (flying sweatdrops:1.4),
    (dizzy:1.3), (full body:1.45)

832x1664, in `fitness`. Picked: 2bc9d8dc, seed 1886970040, off the arm WITH
`(dizzy:1.3)`.

The object grammar is `straw`'s and `ride`'s, filled in rather than worked out:
`holding ball` (13k) puts it in her hand, `basketball` is the second naming that
`ride` pays for because a bare ball is any ball.

**One place the tag-count discipline has to bend.** Danbooru's tag is
`basketball_(object)` at 6k, and the parentheses are weight syntax in a prompt —
it cannot be written as the tag. The plain word reaches the text encoder and
draws a basketball in 12 of 12. Worth recording as the boundary: the tag list is
evidence about what the model saw in training, not a spelling this file is
obliged to reproduce when the tokenizer disagrees.

**`(@_@:1.0)` was copied, not re-swept.** `dizzy` owns that measurement and the
value is the finding — 1.45 draws a near-black spiral on a white sclera, and
neither `spiral eyes` nor `dizzy eyes` is a danbooru tag at all. Three arms were
run on the whine (`wavy mouth` alone, + `flying sweatdrops`, + `dizzy`) and the
fullest was picked, so `dizzy`'s floor under the symbol is doing visible work
here rather than sitting there as insurance.

### The pose was picked against a costume that has since moved

The `hoops` sweep was queued before the side stripe was settled, so 2bc9d8dc
carries neither `(vertical-striped clothes:1.35)` nor `(striped shirt:1.5)`.
`build("hoops", 1886970040, costume="fitness")` therefore does **not** reproduce
it — the two tags are the whole diff, one in each encode.

Handled by not pretending otherwise: the 2048 print (352b3a8e) was built by
reading the picked graph back from `/history` and attaching only the second
pass, so nodes 3/5/6/7 are the worker's own and the print is that drawing at
size. The costume's current form was run separately as a four-seed check, because
whether the pose survives the stripe is a measurement and not an assumption.

### Finalising `hoops` and `fitness`: the rib was the wrong dial (2026-08-25)

Picked: 81e14661 (「服装はこれ！！！」, seed 1886970040) and 6755b2ec
(「ポーズはこれ！！」, seed 737373737) — the same arm, two seeds, praised for
different halves. Both reproduce from
`--pose hoops --costume fitness` node-for-node.

Fingerprint `9c4d0da38fc1378f` → `910a022f1d495234`. 32 poses × {default,
sporty} × both passes rebuilt: zero drift. `hoops` itself moved, which is the
pose being settled.

**The rib was the wrong dial, and two rounds of weight-sweeping went into
turning it.** `(ribbed shirt:1.35)` made the hem unsettleable: a ribbed knit
falls against the body, so 1.4 drew 「少し服が長すぎる」 and 1.3 drew
「服を中に入れるのは違う」 — no window between two adjacent weights, which should
have been read as "wrong dial" the first time rather than as "narrow window".

It was removed for an unrelated reason (「スポーツ着としては合ってない」), and the
hem then settled at **1.45 — longer than the 1.4 already rejected as too long.**
That is what a wrong dial looks like from the far side: the correct value was
outside the range the sweep had been searching, in the direction it had ruled
out.

### A property tag with no garment, three times in one costume

The pattern is now the rule rather than a surprise:

| tag | slot it was in | garment it went to |
| --- | --- | --- |
| `(vertical-striped clothes:1.35)` | legwear (the side stripe) | the tee, striped |
| `(skin tight:1.45)` | legwear (the compression fit) | the tee, pulling into a V at the crotch |
| `(logo)`/`(print)` — absent | nowhere | `snack`'s tee, a watermelon |

**A tag that names how cloth behaves needs a guard on every garment it was not
meant for.** `(striped shirt:1.5)` and `(taut clothes:1.45), (taut shirt:1.5)`
are those guards, both gated on the costume rather than on a pose — which is the
correction this costume forced, since `(logo)`/`(print)` sit under `stand` and
leave every other pose unguarded.

The stripe guard is not perfect: hemH13 at 555666777 came back a striped tunic,
1 of 4, before the taut pair was added.

### The midriff guard was placed for provenance, not for effect

「お腹が見えてるのも not for me」, on a prompt that already carried
`(midriff:1.35), (navel:1.3)`. The block's own comment says why they could not
help: "these three measured nothing — the hem did not move with them in or out —
and are kept for identity with 7d231c4f rather than for effect." Weights placed
to match a reference render, asked to do work for the first time.

`(crop top:1.5)` 282k is the garment name that was missing. Raised to
`(midriff:1.5), (navel:1.45)` alongside.

Gated on the costume and skipped when the tags are already absent — **`swelter`
releases exactly this pair on purpose**, and a fitness `swelter` has to keep
that release. `_splice` would have asserted on a legitimate combination, so this
one tests rather than asserts, which is the one place in this file where that is
the right call.

### Two balls, and a grip with no name

`(holding ball:1.45), (basketball:1.5)` — the two-noun form the vessel grammar
prescribes — drew **two basketballs**, which is the hazard `ride` records for its
own second naming and accepts because a road bike is not the default bicycle.
Here it does not have to be accepted: `(holding basketball:1.5)` is one noun and
pins the type anyway.

**There is no tag for holding something with both hands.** Not in `holding_*`,
not under `*both_hands*`; `holding_to_chest` is 102 posts. The reference photo —
ball at chest height, a palm on each side, fingers open — is spelled as
`(hugging object:1.4)` 32k plus `(spread fingers:1.3)` 5.6k: a clutch and a hand
shape, because the picture is in the training data and the word for it is not.
Same position `side_slit` left this file in.

`HAND_BAN` is in both passes from the first sweep rather than after the fact.
Two hands closed around an object is `tehe`'s accident class, and that pose's
conclusion was about placement — a pass-2-only guard leaves the 1024 sweep
judging a prompt the print does not use.

### The proportion metric returned a constant on three seeds of four

「もしかして脚が長すぎる？」 — and the leg side of that axis is **not
addressable**: `(long legs:1.4)` in the negative is recorded as doing nothing by
`prone`, `(long torso:1.4)` moved 40.1% to 38.9% for `flop`, and `hoops` carries
no positive `long legs` to turn down. The hem was the only lever, which is also
what was asked for.

`.local/proportion.py` was run on the three hem weights across four seeds:

| seed | 1.35 | 1.4 | 1.45 |
| --- | --- | --- | --- |
| 737373737 | 37.0% | 36.2% | 35.4% |
| 1886970040 | 59.9% | 60.5% | 60.5% |
| 111222333 | 60.6% | 60.7% | 61.0% |
| 555666777 | 60.5% | 60.5% | 60.5% |

The bottom three rows all report the hem at row **665 exactly**. That is not a
hem that did not move, it is a hem that was never found: the detector looks for
where the figure narrows into two legs, and a figure holding a ball with elbows
out narrows somewhere else first.

**The dangerous row is the top one.** It is smooth, monotone, and points the
right way, and it is the same broken script — one seed in four happened to
produce a plausible number. A metric that works on the seed you are looking at
and returns a constant on the rest has not been validated by the row that looks
good. See the `metrics-lie-here` note; this is that failure mode again, and this
time it was caught before the number was used.

### Where the second pass's reach ends, measured on cloth (2026-08-25)

`HIRES_POSITIVE`'s note already said it: "reaches anything a late pass can DRAW,
and does not reach anything pass 1 has already DECIDED. A face is the second
kind." Settling `hoops` put four more things on each side of that line, and the
split turns out to be **delete vs. add** rather than detail vs. composition.

| put in pass 2 only | result |
| --- | --- |
| `(tied shirt:1.5), (front-tie top:1.5)` | **knot removed**, composition untouched |
| `(extra arms:1.5)` | **third arm removed**, composition untouched |
| `(covered navel:1.4)` | nothing, twice (covG3, hipL2) |
| `(lavender shirt:1.5)` + desaturation | shirt 182 → 114, and **the hair went silver** |

A late pass can take a knot out of cloth pass 1 already drew. It cannot put
cloth where there is none — the hem is a pass-1 decision in the same way a face
is. So a longer hem always costs the composition, and the pose has to be
re-hunted at the new length. That was two seed hunts this round and it is not
avoidable.

### The knot was pulling the hem up, and three rounds of weights could not win

`(oversized shirt:...)` was swept across 1.1, 1.2, 1.3, 1.35, 1.4, 1.45, 1.55 —
seven weights in four rounds — against 「お腹お尻はシャツで隠れて欲しい」. None of
it worked, and the reason was visible in the render the whole time: **the tee was
tied at the front.** A knotted tee rides up at the back, so the hem's weight was
fighting a knot.

Second time in one costume that a weight sweep was searching the wrong dial —
the rib was the first. The tell is the same both times: **two adjacent weights
drawing opposite complaints, with no window between them.** That should be read
as "wrong dial", not "narrow window".

What finally covered her was not a weight at all but a noun: `(short dress:1.35)`
130k, the silhouette an oversized tee makes once it reaches the thigh. Named
directly, the model draws that shape.

### `(spread fingers:1.3)` was the cause of the bad fingers

`HAND_BAN` was in both passes from the first sweep and the fingers were still
wrong. The tag to remove was not a guard that was missing — it was a request
that was present: `spread fingers` asked for open fingers and the model supplied
too many of them. Dropping it gave the cleanest hand of any arm.

**The lower hand is a separate problem and it is pass-1.** Under the ball there
is a hand-shaped void in every arm of every round: not a bad hand, no hand.
`HAND_BAN` cannot help — a guard deletes, and there is nothing there to delete.
Only a seed with the hand already drawn fixes it, which is what the second hunt
was for.

### A saturation guard has no garment either

`(vivid colors:1.5), (high saturation:1.4)` in pass 2 took the shirt from 182 to
114 — and turned her hair silver. **Fourth tag in this costume that names a
property without naming a garment**, after `vertical-striped clothes` (striped
the tee), `skin tight` (pulled the tee into a V at the crotch) and `snack`'s
missing print guard (a watermelon).

The colour was left to post-processing in the end, for `recolor_bg`'s reason:
five spellings — `light purple`, `pale purple`, `white + light purple`,
`lavender`, and a desaturation guard — produced 182, 161, 159, 155, 139. The
post-process reaches 75 and touches nothing else. This is a value the prompt
cannot hold.

Two of those numbers are worth distrusting rather than reading: adding
`(purple shirt:1.5)` to the negative moved saturation the WRONG way (140 against
E1's 117), and removing a *finger* tag moved it 27 points. There is no
mechanism for either. Pass 2 at denoise 0.5 is simply that noisy, and a
three-point ladder cannot see through it.

### `deliver.py --enclosed-tolerance -1`

`recolor_bg`'s enclosed-pocket pass finds backdrop the border flood cannot reach
— the gap between an arm and the body. It finds it by colour, and **it cannot
tell that gap from a pale detail drawn inside the figure.** The light-grey side
stripe on black leggings matched, so the stripe was repainted as backdrop and
the purple stroke was drawn down the middle of her thigh, with a trail of dots
between her legs.

Diagnosed by delivering the same raw render both ways rather than by guessing:
at tolerance 4 the speckling is there, at -1 it is gone and the stripe is
intact. A flag rather than a new default, because the arm gaps are what the pass
was written for.

**The stripe is also damaged before delivery**, and that half is not fixed:
pass 2 at denoise 0.5 redraws a thin light line on black as a torn slash.
Removing `vertical-striped clothes` from the pass-2 positive did not help, so it
is the redraw itself and not the instruction. Open.

## `winded`: 運動不足で息も絶え絶え (2026-08-25)

「運動不足で息も絶え絶えで床に座り込むゆかりさん」, then a stick-figure reference:
legs stretched out in front, both hands planted on the floor behind, head back,
mouth open, sweatdrops flying. `hoops`'s sequel and the same `fitness` kit.
Picked pass 1 is 96c28abc; the print is 21daf140, reproduced node-for-node by
`--pose winded --costume fitness --hires 2048 --denoise 0.5`.

### Half the vocabulary for this state does not exist

Counted on danbooru before use, and the misses are the useful part:

| tag | posts |
| --- | --- |
| `panting` | 0 |
| `tired` | 0 |
| `fatigue` | 0 |
| `sitting_on_floor` | 0 |
| `outstretched_legs` | 956 |
| `hands_on_floor` | 985 |
| `after_exercise` | 50 |
| `heavy_breathing` | **51k** |
| `arm_support` | **118k** |
| `knees_up` | **81k** |

Four of the first words that come to mind are not tags at all, and three more
are on the shelf where `after_exercise` sits — real, and too thin to move a
picture. The state is carried by `heavy_breathing`; the hands-behind shape is
carried by `arm_support`, which already means exactly that gesture, so the
985-count literal was never needed.

### The legs are straightened by a deletion

There is no usable tag for "legs extended". There is one for the bend:
`knees_up` 81k, in the negative. Same shape as the knot and the third arm —
when the thing wanted has no name, name the thing in the way and remove it.
`legs_together` 37k keeps them closed, which is what the costume's standing
「股を出さずに」 needs.

### The camera was the first sweep's mistake

Nine renders, three leg arrangements, all shot `from front`, and the legs read
as stumps in every one: thrown forward at the camera they are foreshortened
into nothing. `from_side` 333k is not framing taste on this pose, it is what
makes the legs legible. It costs the face its turn toward the viewer, which is
why `looking at viewer` comes out — `nape`'s reason, arrived at from the
opposite direction.

### `(>_<:1.0)`, and the two priors are both about weight

「死んだ目というよりは＞＜な感じかな」. `>_<` is 93.7k, *more* than `@_@` at
55.7k, so the tag is real. What is not real is 1.4:

- `dizzy` found `(@_@:1.45)` draws literal black spirals on the whites, and
  picked 1.0.
- `swelter` swept `(>_<:1.4)` head to head against `(closed eyes:1.4)` and the
  symbol **lost** (b2370dcc).

So the sweep here was 1.0 against 1.3 rather than symbol against no-symbol, and
1.0 is the pick. A face symbol on this model wants roughly the weight of a
plain tag, not the weight of an instruction.

`(sweat:1.3)` is the lowest weight in the block on purpose. 763k and strong,
but it is drawn as **sheen**, which is the same axis as the pass-2 gloss this
round was spent removing. The state goes to the symbol side instead:
`flying_sweatdrops` 126k. `steaming_body` 42k is left out for `hoops`'s reason —
steam is scenery and SURFACE is a flat backdrop.

### 1152×1152, the only square full body in the file

Legs forward and arms back put the figure's long axis on the **diagonal**, so
neither family of frames fits: `snack`'s 1024×1536 runs the feet into the edge,
`flop`'s 1536×1024 leaves half the frame empty beside a seated girl.

### The hand guard is per-pose, and a new pose gets none

Measured while building the print: `(bad hands:1.5)` counted **zero** in the
picked render's negative. The five names live in `negative()` behind `pose ==`
gates, so `tehe` and `hoops` are covered and anything new is not. Both hands are
flat on the floor carrying her weight and pass 2 redraws them. Named once, in
`HIRES_NEGATIVE`.

Worth knowing generally: a guard that reads as global because it appears in
every printed prompt you have looked at may be gated on the poses you looked at.
Count it in the actual negative before assuming it is there.

## 「線画の絵柄が変わったね」: the gloss is the second pass, and the guard was already there (2026-08-25)

Distinct flats over the figure: 849 on the first `hoops` render, 643 on knotK2,
1154 and 1167 on the two finalised prints. The gloss arrived between them —
specular hair highlights, gradient irises, airbrushed skin, i.e. the "clean and
vivid" regression this file exists to prevent.

Two suspects were cleared by measurement:

- **Not the pass-1 prompt.** The same pass 1, decoded with no second pass at
  all, measures 552.
- **Not `6b`.** The 1167 render has no `6b` node.
- **Not `(short dress:1.35)`.** Dropping it from the pass-2 positive measured
  1147 against 1154 — nothing. This was my suspicion and it was wrong; the tag
  covering the hem stays.

What was actually happening: `(detailed shading:1.2), (heavy shading:1.2),
(impasto:1.25), (painterly:1.25)` have been in NEGATIVE all along, and at 1024
that weight was never losing. At 2× the redraw out-argues them. Raising the same
four to 1.45/1.5 **for the second pass only** measured 590 against 1154 on an
identical pass 1.

`SHADE_BAN`, and it is applied to every pose rather than added to
`HIRES_NEGATIVE` pose by pose: the gloss is a property of the redraw, not of any
one pose, so `build` now always writes a `7b` node and the dict only decides
what goes in front of it. Pass 1 keeps 1.2/1.25 untouched — raising it there
would re-roll the composition of every picked render in the file, which is the
same rule `HIRES_NEGATIVE` was written on.

**A caution about the number.** `flats` was re-derived when it was needed again
on `winded` and the definition is not the one that produced 590 and 1154, so
those two are not comparable to anything measured after them. On `winded`'s own
print the guard moved 144 to 136 — a much smaller gap, because that picture was
not glossy to begin with. Per `metrics-lie-here`: the statistic localised the
problem, and the face crop is what confirmed it.

### One guard's duplication turned out not to be load-bearing

The first arm that raised the shading weights also prepended the seam, limb and
knot guards a second time on top of a picked graph that already had them, and
measured 691. Re-run in the exact shape the recipe emits — each guard appearing
once, asserted — it measured 590. The duplication was not helping and was
mildly in the way.

## `winded` settled: the seed was the colour dial all along (2026-08-25)

Final is 292ad788, from seed **111222333**, reproduced node-for-node by

```
uv run scripts/yukari_recipe.py --pose winded --costume fitness --seed 111222333
```

with no `--hires` flag — see `HIRES_PRINT`, which supplies both the print size
and the denoise for this pose.

### 「絵柄がだいぶCGっぽくなってる」 was the pass-2 SCALE, not the pass-2 prompt

`--hires` is a longest-side number, not a scale factor. On the file's portrait
poses 2048 is a 1.23× redraw; on this pose's 1152 square it is 1.78×, i.e. twice
the pixels for the second pass to fill — and it filled them with specular skin,
coloured shadows and gradient irises.

The ladder, all on the same pass 1, skin colour count measured at a common
resolution: no second pass 24, 1416 (1.23×) 23, 1664 (1.44×) 33, 2048 (1.78×)
38. And sharpness on the figure runs the other way from what "more pixels"
suggests: **1152 (1.0×, no upscale at all) measured 62.9 against 19.7 at 2048.**
The bicubic latent upscale is what softens the picture; the redraw on top of it
is what hardens the shading. Printing at 1.0× gets both back.

**Two corrections to entries above, both caught by controls.**

- The first skin ladder (24 / 26 / 33 / 47 / 57) was measuring resolution, not
  drawing. A Lanczos enlargement of one render — no new detail by construction —
  scored 55 against its own 36. Colour counts are not comparable across sizes;
  everything now downsamples to a common longest side first. Fourth entry for
  [[metrics-lie-here]], and the control is the only reason it was caught.
- Sharpness across DIFFERENT pictures is confounded by content. A standing girl
  holding a ball has more edge per pixel than a seated one in an oversized tee,
  so `hipL2` scoring above every `winded` arm meant nothing. Only same-content
  comparisons were kept.

### The colour is a property of the seed

Same prompt, same everything, five seeds, whole-figure saturation: **21.3, 21.6,
31.0, 41.6, 51.2.** A 2.4× spread with nothing changed but the seed — and the
seed this pose had been settled on, 1886970040, was the most saturated of the
five.

That is why a week of prompt work could not reach `lineT3`'s colour. Restoring
that render's exact pass-2 configuration (SHADE_BAN in, `shiny skin` out) moved
purple 46.6 → 41.5 against a target of 27.5. Switching seed reached 24.2 in one
step.

Canvas was ruled out in the same sweep: 832×1664 and 960×1408 both measured 40.1
against the square's 41.6.

**So: check the seed before tuning the prompt for colour.** Three separate
guards were designed, measured and argued about — `shiny skin`, dropping
`sweat`, raising SHADE_BAN to 1.6 — and all three were noise on a dial the seed
was holding.

### `(shiny skin:1.5)` and `(sweat:1.3)` both failed, twice each

`shiny_skin` 157k is the name for lit skin and it made skin *worse* every time
it was measured — 23 → 27 in the colour count, and the arm carrying it was
further from the reference than the arm without. `sweat` 763k was suspected of
glazing the skin on a panting pose; removing it from the second pass moved
nothing, in two separate sweeps. Neither is in the shipped pose.

### The symbol's weight window moves with the seed

`(>_<:1.0)` was swept against 1.3 and picked, on seed 1886970040. On 111222333
it drew **nothing** — ordinary open eyes. 1.3 and 1.45 both brought the symbol
back with no glyph on the whites, and 1.45 is the pick.

This file had the too-high failure written down twice (`@_@` at 1.45 drawing
spirals; `swelter` losing `>_<` at 1.4 to `closed eyes`) and had quietly
generalised it to "keep face symbols low". The other end exists too. Re-check a
face symbol on any seed it is carried to, in both directions.

`(closed eyes:1.35)` added underneath as a floor — `dizzy`'s pattern — is not
here, and the reason is worth keeping: it took the figure from 47% of the frame
to 74% and pulled saturation back up. A floor tag under a symbol is not free on
every pose.

### 「手書き風」 is a second-pass finish, and it barely moves the numbers

THIN comes off and `traditional_media` 125k + `marker_(medium)` 18k go on, at
the END of the prompt rather than spliced after the pose block — `HIRES_FINISH`
exists separately from `HIRES_POSITIVE` for that reason alone.

Measured, the three arms are indistinguishable: ink coverage 32.2 / 32.3 / 32.9
/ 32.7, saturation 22.4 / 21.6 / 24.7 / 22.4. The pick was made by eye, on a
difference the statistics cannot see. `traditional media` was expected to bring paper
texture and fight the flat backdrop; it did not — corner variance 0.29 against
the baseline's 0.32.

`sketch` 194k is deliberately absent despite being the largest tag in the
family: it means *unfinished*, which is the state `HIRES_NEGATIVE_PAINT` was
written to remove.

### Two defects shipped with it

The floor. `(on floor:1.45)` draws a wooden plane under her, and its colour sits
43 from the corner while pale skin sits 15 — so no single `recolor_bg` tolerance
both swallows the floor and spares her arm. Guarding it in the second pass
(`wooden floor`, `indoors`) halved the area, 3.07% → 1.40%, and did not clear
it. Not fixed.

The repaint leaks into her arm and hand at the shipped tolerance of 18, for the
same reason: pale skin is inside it. Visible as teal speckling on the forearm.
Not fixed, and it is the reason to look at a delivered file rather than a raw
one when judging.

Delivered without the purple stroke — `deliver.py --stroke ''` — on request.

### Correction: `winded` is settled on seed 737373737, not 111222333 (2026-08-25)

The entry above settles the pose on 111222333 for its colour. That render's
ankles do not survive inspection — 「足首から靴の向きが骨折しているとしか見えない」
— so the pose has moved to **737373737** with `(feet out of frame:1.4)` in the
block. Final is 00041991. Everything else in that entry stands.

**Three second-pass guards were tried on the shoes and all three did nothing.**
`shoe_soles` 18.4k named the sole-on view, `single_shoe` 10.8k named the odd
count, and the costume's own `(high tops:1.3)` was dropped as a suspect. Ink
coverage over the lower half of the figure: 44.93 → 44.65 → 44.42 → 44.27. A
late pass deletes drawn objects; it does not re-articulate a joint.
[[refine-cannot-rebuild-structure]], now measured on a fourth pose.

Worth recording separately: **`(high tops:1.3)` has 1903 posts.** It has been in
the `fitness` costume since the costume was written, on the same shelf as
`after_exercise` at 50 — a tag that cannot move a picture. It was not removed,
because removing it is a costume change and nothing has been rendered to justify
one; but nothing should be attributed to it either.

### `feet out of frame` is a framing decision, and it does not land on every seed

236k, and it belongs in pass 1 for the same reason the shoe guards failed in
pass 2. Four seeds run with and without, share of the bottom 12% of the frame
the figure still touches:

| seed | plain | + feet out of frame |
| --- | --- | --- |
| 111222333 | 51.1% | **100%** |
| 555666777 | 100% | 24.2% |
| 737373737 | 52.4% | 67.6% |
| 424242424 | 100% | 13.6% |

On 111222333 the tag made the figure reach the edge *more*. That is the seed the
pose had just been settled on for colour, so the cheapest exit was closed on
precisely the render that needed it — and the pick cost saturation, 22.4 → 31.4.

**A tag that names a framing outcome is not a framing guarantee.** The seed
decides whether the composition has anywhere to put the feet.

### The seed is now recorded in code

`SETTLED_SEED`. Not a default — `--seed` stays explicit — but on this pose the
seed holds the colour and decides whether the framing tag works, which makes it
part of the recipe rather than a detail of one run. Before this it was
recoverable only from a filename in a worker's history.

### Correction: the print is 1416 (1.23×), and the scale ladder was measured on the wrong render (2026-08-26)

Final for `winded` is **cc988f40** — seed 737373737, printed at 1416×1416,
denoise 0.50. `HIRES_PRINT` now holds 1416.

The entry above sets it to 1152 — print at 1.0×, no upscale at all — on a ladder
that measured skin colour count rising 23 / 33 / 38 with the scale and sharpness
falling 62.9 to 19.7. **That ladder was taken on seed 1886970040, which the seed
sweep in the same entry later showed to be the most saturated of five on an
identical prompt.** Retaken on the render that actually ships:

| pass 2 | skin colours | saturation | value sd | darkest p1 |
| --- | --- | --- | --- | --- |
| 1152 (1.0×) | 18 | 31.4 | 83.6 | 0.3 |
| 1416 (1.23×) | 27 | 21.2 | 70.0 | 25.7 |
| 2048 (1.78×) | 28 | 19.7 | 68.6 | 30.0 |

Bigger prints came out **flatter and with lighter shadows** — the opposite of
the first ladder — and 1.23× is where the eye stopped. The skin colour count
still rises with size, but that is the metric this pose already corrected once
(a Lanczos enlargement scores higher with no new detail in it by construction),
and the saturation and black-floor movement is far larger.

**A property measured across seeds is not a property of the setting.** Retake
any such measurement on the render that will ship. This pose spent a full
session on that sentence: the colour turned out to live in the seed, and then
the scale conclusion turned out to have been read off the seed as well.

### What this pose cost, and the shape of the mistake

Five properties were wanted — colour, line, ankles, framing, print size — and
four of them are decided in the first pass, which re-rolls all of them together
whenever a single token moves. Fixing them one at a time therefore broke a
settled property on almost every round: the colour fix changed the seed and
broke the ankles; the ankle fix cost 22.4 → 31.4 in saturation; the line-art
attempt pulled the feet back into frame and took saturation to 49.2.

The way out was the last question asked rather than the first: **change only the
second pass.** Print size is the one lever of the five that pass 1 does not own,
so it moved saturation 31.4 → 21.2 without touching anything already settled.

For the next pose: settle the pass-1 prompt in one piece, sweep seeds in a
batch, and pick a render that is acceptable on every axis at once. Sequential
single-dial fixes do not converge here.

### Still open, and shipped anyway

- The wooden floor `(on floor:1.45)` draws. Second-pass guards took it from
  3.07% to 1.40% of the frame and no further.
- `recolor_bg` at tolerance 18 leaks into her forearm and hand, because pale
  skin sits 15 from the corner colour while the floor sits 43. No single
  tolerance does both.
- `(high tops:1.3)` in the `fitness` costume has 1903 posts and cannot be
  moving anything.
- The three second-pass shoe guards (`shoe_soles`, `single_shoe`, dropping
  `high tops`) all measured as no-ops. The shoes were solved by framing.

## `doze`: バスケ帰りの電車で寝落ち (2026-08-26)

「バスケ帰りで疲れ果てて電車で寝てるゆかりさん」. `hoops` → `winded` の続きで、
costume は `sporty` — 練習帰りの私服という読み。1152×1152、`winded` の正方形を
その理由ごと借りている（座った人物は縦にも横にも収まらない）。

Counts taken before the block was written: `sleeping` 100332,
`sleeping_upright` 4258, `head_tilt` 172547, `zzz` 15769,
`towel_around_neck` 9420, `messy_hair` 91176, `bench` 21720,
`arms_at_sides` 38750. `exhausted` is real at 3696 and was still left out —
the state is posture and symbol here, as it is in `winded`.

Three words this scene wants do not exist: `dozing` 0, `nodding_off` (no page),
and `tired` 0 for the third time in this file.

`(sleeping upright:1.45)` sits ABOVE the 100k `sleeping` under it on purpose.
4.3k is thin for the tag that decides the whole pose, and `sleeping` unopposed
draws a girl in a bed.

### An existing tag that is not a tag

`hoops` carries `(holding basketball:1.5)`. `holding_basketball` has **0 posts**
— the ball is presumably arriving from `basketball_(object)` 5977 plus the
`hugging object` grip that block already names. Not touched here, and not
re-measured; written down because the block's own comment reasons about that
tag as though it were doing work.

### The carriage, measured against the contract

`ride` puts her on a bike in front of nothing and `hoops` keeps the court out,
because SURFACE is a flat grey backdrop. A train interior is a scene, so the
pose says 帰り with `(towel around neck:1.4)` instead — a worn object cannot
fall out of the composition the way a loose bag can, which is `sip`'s finding.

The user asked for a train, so the contract was given one sweep rather than one
argument. Same pose, same four seeds, same costume; `(simple background:1.3),
(grey background:1.2)` replaced by `(train interior:1.4), (vehicle
interior:1.3), (window:1.2)`, plus a crowd guard the flat arm does not need
(`.local/_dozetrain.py`).

- flat: 4f711db5, 65194aee, fa6340d7, 09555835
- train: d4a0b072, 95dadbd4, dcbb65bc, b393e171

### `headcount.py` cannot judge the train arm at all

It reported 2, 3, 4 and 2 bodies there, and every one of those numbers is
noise: the tool takes the background colour from the median of the border
pixels, so a carriage full of seats, poles and windows is figure by
construction. **It is a flat-backdrop instrument and the arm that breaks the
flat backdrop is exactly the arm it cannot be pointed at.** Nothing about the
crowd risk was learned from it.

On the flat arm it works, and reported ONE on three seeds. The fourth,
737373737, came back "2 bodies" and `--detail` disposes of it: the extra block
is 73px wide at 2.84% of the figure and 53% of frame height, i.e. the bench
running out to one side. A second girl is tall for her width; this is not.

### Picked: b393e171, and the carriage moved into the recipe (2026-08-26)

The user picked the train arm, seed 737373737. So the contract lost to a
measurement rather than to an argument, and it lost on exactly one pose:
`SCENE_TRAIN` and `CROWD_BAN` are in `yukari_recipe.py` now, spliced over
SURFACE's `(simple background:1.3), (grey background:1.2)` and prepended to the
negative respectively. The rest of SURFACE is untouched, which is why the
carriage arrives as pale line and stripe rather than as a photograph.

`.local/_dozecheck.py` is `_kickseeds.py`'s check pointed at this: nodes 5, 6, 7
and 3 all MATCH against the picked render's own `/history`, so the pose in the
file is the picture and not a reconstruction of it.

`costume_check.py` earned its keep here — it failed the change three times over
(once per costume) with the exact five tags, and the declaration in `EXCEPTIONS`
is now the written record that this pose replaces the backdrop.

### The print collapses the colour, and both sizes do it

    render                       px   ink%   sat  sat90  dark%  flats
    b393e171 pass 1            1152   32.1  46.6  154.0  11.18   4453
    9f1b8edb 1416 @ 0.50       1416   33.8  17.6   37.0   1.39   2682
    179eab42 2048 @ 0.60       2048   38.7  18.5   34.0   0.82   3142

Saturation over the whole frame is meaningless on this pose -- most of it is a
pale carriage -- so `ink%` is everything not near-white and the rest is measured
inside that.

The brightest tenth falling 154 → 35 is the finding, and it is visible: pass 1's
seat is green and its hair is purple; both prints are cream and pale blue. The
drawing is BETTER in the print -- the shoes and the seat frame gain real detail
and the line stays drawn rather than clean -- and the colour is what it costs.

**The two prints differ in two variables at once (1416/0.50 against 2048/0.60),
so nothing here says anything about size.** `winded`'s 1.23× finding is neither
confirmed nor refuted; 17.6 against 18.5 is inside the noise this file already
put on a pass-2 measurement at 0.5.

Two doors this file has already closed, checked before spending a render on
either: `(vivid colors)` in `HIRES_POSITIVE` measured IDENTICAL at 1.25 and 1.40
and is not even a danbooru tag, and `(vivid colors:1.5), (high saturation:1.4)`
in a pass-2 negative turned her hair silver. The remaining levers are the ones
that do not argue with the tags: a lower pass-2 denoise, or `upscale_plain.py`,
which keeps pass 1's colour by not letting the model touch it.

## `brush`: 疲れ顔で歯磨き、チェストアップ (2026-08-26)

Assembled entirely from precedent and picked on the first sweep — no slot in
the block was newly measured this round, so what this entry records is which
precedents composed and the one place the file had to be told something new.

- Framing is `tehe`'s four tags verbatim, on `tehe`'s square. The request said
  チェストアップ and `tehe`'s `(upper body:1.35)` is already that crop — it was
  chosen there because a hand ON the face pushed the head out of `close-up`,
  and a toothbrush at the mouth is the same geometry.
- `(brushing teeth:1.45), (toothbrush:1.3)` is `sip`'s two-slot rule (action
  lifts the object to the mouth, object tag decides what it is), with the
  action taking the heavier weight because it carries the whole pose.
- The exhaustion is `allnighter`'s `(eyebags:1.4), (half-closed eyes:1.35)`,
  and no expression tag beside them, for `allnighter`'s reason.
- `brush` joins `open_mouthed`, on `snack`'s side of the straw rule: lips do
  not close around a brush that has to move.

### Picked: 4e56f616, seed 737373737 (2026-08-26)

Sweep was the front four of SWEEP_SEEDS (555666777, 111222333, 1886970040,
737373737); the user picked yk-brush-737373737_00001_ by filename. Third pose
in a row settled on 737373737 and still coincidence — every sweep starts from
the front of the same list. Recorded in `SETTLED_SEED`.

Delivered with `deliver.py` defaults: 15.1% repainted, stroke #9256b8 at 5.4px.
Backdrop share sits between `tehe`'s 30-41% and the tight crops' 7-30%, which
is consistent with the same framing plus a raised arm eating into the field.

## 紫フチの再選定: #6a3494 / band 0.80 (2026-08-26)

colW `kick`（a4c27b83 の再生成 3a9c9905、seed 111222333）を素材に、色2×太さのはしごで振った。

- 色: 濃い #6a3494 と薄い #b591d6 を同幅で並べ、濃い方が採られた。元の #9256b8（髪のアクセント色）は両者の中間で、退役。
- 太さ: band 0.32 (6.1px) → 0.50 (7.8px) → 0.80 (12.5px) → 1.2 (18.7px)。「もっと太く」が2回続き、12.5px で止まった。1.2 は行き過ぎ。
- 採用: `yk-colW-kick-111222333_00002_-p12-delivered.png` の濃い紫。`outline_stroke.DEFAULT_COLOR = "#6a3494"`、`DEFAULT_WIDTH_BAND = 0.80` に反映済み。

同じ p12 名で濃・薄2枚が投稿される事故があった。deliver.py の出力名は色を含まないので、同一 prompt_id を色違いで振るときはファイル名では区別できない — 投稿順で覚えるか、色を聞き直すことになる。

## `stand` が銀紙ノイズに崩壊する回帰: 犯人は 08-24 の睫毛ペア (2026-08-26)

ワンピース精度の A/B のために `stand` を現行レシピで組んだら、4枚全てが
アルミホイル状のノイズになった（deliver も「backdrop 0.1-0.5%、フラットでない」
で全滅）。切り分けの行列:

- worker は健全: kick プロンプト新シード 832x1216 → きれい (grad-mean 5.2)
- kick プロンプト @832x1664 → きれい。キャンバスは無実
- stand プロンプト @832x1216 → 崩壊。プロンプト自体が犯人
- ネガを kick のものに差し替え → 崩壊のまま。ネガは無実
- `(criss-cross halter:1.45)` 除去 → 描けた。ただし 1.2 に下げても崩壊、
  つまり halter は「引き金の一部」であって真犯人ではない
- 睫毛を 08-24 以前（素の `eyelashes`、ネガの guard なし）に戻す → halter
  1.45 のままきれい。胸のクロス紐も出る
- 分離: POS ペア `(eyelashes:1.3), (thick eyelashes:1.35)` だけ除去 → きれい
  (grad 3.4)。NEG `(long eyelashes:1.35)` だけ除去 → 崩壊 (grad 13.8)。
  真犯人は POS ペア、ネガの guard は無実

`portrait` と `brush` は同じペアを積んで正常なので、衝突相手は `stand` の
全身タグ群のどこかにある（未特定）。処置は per-pose: `stand` だけ FACE の
ペアを素の `eyelashes` に戻すスプライスを入れ、costume_check に申告した。
grad-mean（グレースケール勾配平均）は崩壊 10.4-13.8 / 正常 3.4-8.7 で、
今回は目と一致した。

08-24 のペア導入時、`stand` は再レンダーされていなかった。衣装変更後に
全身ポーズを1枚も焼かずに済ませると、この種の回帰は次にそのポーズを触る
セッションが踏む。

## ワンピース精度 A/B: 襟なし・ボタンなしガード (2026-08-26)

「肩紐、襟無し、ボタンなし」のうち肩紐は既に per-pose の
`(criss-cross halter:1.45)` で対応済み、buttons は `stand` のネガに
`(buttons:1.4)` が既存。新規はネガ先頭の `(buttons:1.35), (collared dress:1.35)`
のみで、`stand` 2シード（555666777, 111222333）の素 vs ガードを dg-a / dg-b
として投入。選定待ち。差が見えなければガードは入れない。

## `kick` 改め「ソファなしステッカー」: 0db8e020, seed 737373737 (2026-08-26)

「キャラクターだけに白・紫枠」の依頼。白帯はモデルが被写体ひとかたまりに
描くので、ソファごと枠が付く。ソファ外周の白帯を後から消すのは修復であり
禁じ手 -- 消せるのはタグの方、ということで `(couch:1.2)` を落とした。

- couch を抜くとモデルは台を発明して座らせる。台は許容された（接地して
  いるので枠は台込みになるが、ソファよりずっと小さい）
- seed 111222333 は空いた背景に落書き（うさぎ・集中線・赤い影）を描き
  続けた。speed lines / motion lines / emphasis lines の三連ガードでも
  止まらず、シードを離れたら 3/3 で消えた。ガードが効かなかった記録として
  残す（swelter では同じ三連が効いている -- あちらは positive が線を
  誘発していた分の差か）
- 4シード掃引から 737373737 を採用。POSES から couch を削除、negative() に
  kick 分岐（三連＋ワンピースガード、pick のバイト再現）、SETTLED_SEED 登録
- 2048 は image route / 0.45（rf-kick-nc, ff1901b3）。配信は clean-bg 版

### 背景クリーン配信 (`.local/deliver_clean_bg.py`)

dg-b-111222333 の「背景の枠と紫枠を消して」から。border flood の外にある
非背景成分（最大成分＝本体以外）を配信色に均してから repaint + stroke。
本体に接触している異物には無力（111222333 の落書きは残った）。常用する
ようなら deliver.py のフラグに昇格。

### ワンピース精度、その後

`(buttons:1.35), (collared dress:1.35)` は stand の dg-b と kick の pick が
両方積んでいる。stand の a/b は明示判定なしのまま dg-b 系統が選ばれ続けて
いるので、kick は per-pose で正式化した。NEGATIVE へのグローバル昇格は
明示の一言が出るまで保留。

## `kick` のつま先: `(purple pantyhose:1.15)` (2026-08-26)

「つま先のタイツのグラデーションを白ではなく紫に」。LEGWEAR の
`(pale purple pantyhose:1.35)` はグラデーションの明側で白に飛び、この
ポーズは足裏がカメラに向いている。挟み込み:

- `(purple pantyhose:1.35)`: マゼンタ寄りに飽和。「コントラストが高すぎる」
- `(light purple pantyhose:1.35)`: 色名で1段の中間
- `(purple pantyhose:1.15)`: 色はそのまま重みを弱める -- 採用 (eb2533f6)

色名でなく重みが勝った。kick 限定の per-pose スプライス（COSTUME_ONLY
に申告）で、LEGWEAR 本体は据え置き -- 明側が顔の前に来るのはこの
ポーズだけ。2048 は rf-kick-toe (8dde11a2)、image route / 0.45。

1タグの置換でも1パス目が動くので構図は座り直す。この pick は台も消えて
宙座りになり、枠が完全に彼女だけになった -- couch 削除の回で許容した台は
結果的に不要だった。

## roomwear costume 初回スイープ (2026-08-26)

部屋着コス。夏のエアコンの効いた部屋、白Tにうさぎフードカーディガンを
寒いから羽織る、だらけてる — が発注。実装は白T + 本来衣装のカーディガン
タグ流用 + dolphin shorts + bare legs/barefoot。lounge / flop / doze を
6シードずつ。batch 20pgz1 / exirzf / 1zbnkd、検品は chimera に semantic +
rating で記録済み（good 8 / neutral 9 / bad 1）。

観測、シード横断:

- **ショーツの色は指定しなかったので座らない。** 紫・ピンク・黒がシード
  ごとにランダム。18枚では欠陥として数えなかったが、採用色を決めたら
  `(purple shorts:1.3)` 程度で置きにいく。色未指定のカラー安定性の前例は
  fitness のストライプ（存在は座る・色は座らない）と同じ挙動。
- **doze は部屋着と混ぜられない。** pose 側に電車内・首タオル・zzz が
  焼き込まれていて（帰り電車のシーン pose）、6枚全部が電車で寝た。部屋着
  のうたた寝が欲しければ doze から電車を抜くのではなく、シーンなしの
  眠り pose を別に作ること。355svk は背景が電車とも部屋とも読めない淡黄に
  崩壊、be3gzv は二人に分裂（solo:1.5 貫通、このスイープ唯一の bad）。
- **xf8eu9 の座面に謎の黒い履物が置かれた。** roomwear の negative に
  入れた (shoes:1.4) と barefoot の衝突痕とみられる。履かせずに置く、が
  モデルの妥協点だった。
- lounge は正座寄りに畳んだ2枚（noko9g, 9sgcgm）で太腿が過大になり下腿が
  消える。横座りに開いた4枚は問題なし。
- 1ibrbu で midriff がわずかに露出。(midriff:1.35) ban は貫通することが
  ある、程度の頻度（18枚中1枚）。
- nax012 の T シャツに頼んでいない RABBIT プリント（うさぎシルエット付き）
  が出た。rabbit hood の語彙が漏れたとみられるが、部屋着コンセプトには
  むしろ刺さる。プリントを固定したければ `(rabbit print:1.3)` を試す価値
  はあるが未検証。
- tczmqo はカーディガンを脱いで下に敷いた。「暑くて脱いだ」文脈が一枚で
  語れており、open cardigan 指定でも脱衣まで揺れる、は覚えておく。

flop が最も打率が高い（6枚中 good 4）。だらけの本命は flop。

## roomwear lounge の潜る脚問題 → あぐらで解消 (2026-08-26)

「どれも下に潜ってる脚の関節がおかしい」。yokozuwari（横座り）は下の脚が
太腿の裏に消える座り方で、モデルは見えない関節を毎回適当に埋める。refine
（aan9dj / 1v4yqa）で面は磨けても関節は直らない — 構造は1パス目でしか
決まらない、の再確認。

座り方ごと置換した2アーム、各3シード（batch c259uu / 4jeuxa）:

- **(indian style:1.35)（あぐら）は3/3で関節が全部読めた。** 潜る脚が
  構図から消滅するので問題自体が発生しない。だらけ感もむしろ増す。
  11ohpe / 2mf60u / 77pmoq、全部 good。
- (wariza:1.35) は1/3。fvlo0p だけ正面対称の正しいぺたん座りになり good、
  残り2枚は横座りに崩れて潜る脚が再発した。wariza はタグとして座らない。

部屋着の座り姿勢は yokozuwari でなく indian style を既定にする価値がある。

## roomwear 初採用: 6d970y → finalize pclbfb (2026-08-26)

部屋着コスの最初の採用作。あぐら（indian style）+ 脱力、表情は sleepy
アーム — smug を (sleepy:1.35), (half-closed eyes:1.35), (parted lips:1.2)
に置換し、FACE の closed mouth を外したもの。シードは znyqao 系 2743458075、
太さは thick thighs 1.05 + wide hips 1.15。ショーツはピンクが出た個体。

表情3アームでは sleepy が採用、jitome (l73z22) と yurui (6mqs68) は不採用。
「ドヤ顔の状況が分からない」が発注理由で、だらけ姿勢には smug より sleepy
が正解だった。

finalize は barefoot 条件付きで (toes:1.55) を外す変更後の初運用
（f907f5d）。2048 raw が j6xvoh、delivered が pclbfb。

### 膝枕深掘り: sheer は今回も色で払った、muted は背景ごと奪った (2026-08-27)

kfuthu -> b2c54r -> lx2mjb の膝枕深掘りで、タイツの質感アームが二度、
パレットで失敗した。

- `(muted color:1.25)` は全体のコントラストを下げたが、背景ごと脱色して
  「白夜みたいな配色」になった。1.1 でも本質は同じで、採用されたのは
  muted も `(high contrast:1.4)` ガードもない素のパレット（arm j, lx2mjb）。
  コントラストの元凶はタイツのグラデ（pale purple + gradient legwear）で、
  それを消して黒単色 + `(shiny legwear:1.45)` にしたことが実際の解だった。
- `(sheer black pantyhose:1.4)`（arm k）と + `(skin visible through
  pantyhose:1.3)`（arm l）は 6 枚全てで「色がぐちゃぐちゃ」。この file の
  古い記録 -- sheer 1.5 は色を代償にし、弱めると透けが消える -- の再現。
  negative の `(transparent clothing:1.3)` を外して挑んでも同じだった。
  このスタイルで sheer 系タグは閉じた扉。リアル質感は 2048 パスが乗せる
  微細シェーディングで判断する。
- `(ribbed legwear:1.35/1.55)`（arm g/h）は編みを描いたが「一般的なタイツ
  素材」で却下。ltpge6 の構図保持には refine パスでの ribbed -> opaque
  差し替え（mat-ltpge6, batch 9xardj）が機能した。素材の平滑化は refine で
  できる。sheer 化はできない。この非対称は既知のとおり。

### 根本原因: negative は凍結された過去の修正の要塞で、誰も読み返さない (2026-08-27)

膝枕深掘りで同じ形の事故が繰り返された。sheer を頼んだ 6 アームの色崩壊、
水色背景の指定が「無視」された件、その代償に選んだ後処理の範囲ぐちゃぐちゃ。
並べると一つの構造に還元される:

**positive の新しい要求が、別の見た目のために昔立てた negative の ban と
衝突している。** sheer は `(transparent clothing:1.3)` に、"もっと薄く" は
`(black pantyhose)` の重みと `(dark)` に、水色背景は `(blue background:1.5),
(blue tint:1.4)` に、それぞれ正面からぶつかっていた。ban は一度入ると全アーム
に黙って継承され、衝突してもエラーは出ない — 絵が壊れて初めて分かる。
8921 行の「Guarding a property while banning the fix」と同じ病で、今回は
それが3連発した。逃げ場を全部塞がれたモデルが緑に逃げてセージ背景と
カーキタイツになったのも同根。

**解決はコードに置いた。** `scripts/prompt_lint.py` が positive と negative
の矛盾（同じ色・素材・対象の両面指名、sheer vs transparent 系、色付き背景
vs 色 ban）を検出し、`generate.py` は explicit prompt の request で矛盾が
あると停止する（意図的なペアは `--force`）。素のレシピは全 costume × 全
pose で無警告、今回の事故2種（k の sheer、水色背景）は検出されることを
確認済み。

lint が守れないもの: 「sheer はこのスタイルでは色を代償にする」のような
グローバルな相性は矛盾ではないので通る。それはこの file の仕事のまま。

副産物の教訓: img2img は denoise 0.65 でも元 latent の色に錨を降ろす。
黒タイツに (white pantyhose:1.3) を頼んでも輝度 39 にしかならなかった
（元 52、狙い 145）。色を変えるなら生成し直すか、数値で塗ってから低
denoise で描き直す（queue_refine の docstring どおり）。プロンプトで色を
持ち上げる操作は img2img には存在しない。

### 是正: 見せる前に測る — palette_check が受け入れゲートになった (2026-08-27)

膝枕深掘りの事故は全部、意見になる前に数字だった。ネオン背景（#00e1ea、
背景彩度255）、彩度爆発（135〜188）、ピンク寄り（77〜86）— どれも承認作の
帯（kfuthu 54.5 / lx2mjb 41.6 / uk1jfi 41.5）から機械的に外れていたのに、
最初の検出器が毎回人間の目だった。それが根本の間違い。

`scripts/palette_check.py` が受け入れゲート: 全体平均彩度 30-70、背景彩度
60 以下。arm が ingest されたら人間に見せる前に必ず通す。FAIL は候補として
提示しない（pass は合格であって承認ではない — 判断は rating のまま人間）。
検証: kfuthu/uk1jfi は pass、sdawrn（セージ）・ia8s6p（ネオン）・fqbtb2
（ピンク寄り）は FAIL を検出する。

同日の他の是正と合わせて三点セット:
- prompt_lint（positive と negative の矛盾を生成前に止める）
- 派生規律（壊れた arm の上に重ねず、直近 good の prompt+α で組み直す）
- palette_check（見せる前に帯で合否）

fqbtb2（構図採用・色は不同意）は WB 補正 — 背景実測を uk1jfi の背景に写す
チャンネル毎線形ゲイン — で帯に着地した（9m58uo、彩度 53.2）。透けタグの
skin が全体をピンクに引く漏れは、生成では避けられず補正で戻すのが現状の解。

### 膝枕: 透けタグの色漏れ地図と、成立した z4 の構成 (2026-08-27 深夜)

uk1jfi（グレータイツ good）からの単一αスイープで、透け系タグの色漏れが
タグごとに向きを持つことが分かった。全て palette_check の実測:

| α | 全体彩度 | 漏れの向き |
|---|---|---|
| skin visible through pantyhose 1.25-1.4 | 68-86 | ピンク（skin が全体に乗る） |
| sheer legwear 1.25 単発 | 63-104 | 緑（背景セージ、タイツオリーブ） |
| ↑ + purple dress 1.6 の錨 (z3) | 78-97 | 錨がむしろ彩度を押し上げた |
| skin visible 1.3 + skindentation 1.2 + purple dress 1.6 (z4) | 33-47 | 漏れなし。帯ど真ん中 |

z4 が成立した構成: 透けを 1.3 に下げ、(skindentation:1.2) が肌の情報を
タイツ領域に局在させ、紫の錨がドレスを守る。3/3 で palette gate pass、
目視でもドレスはラベンダー紫・タイツはグレー光沢のまま。

検品通過: iy6dwy / w546qv → 背景のみ #c7e5e9 で xa7c4g / kf12s9。
gk2wk0 は股部の淡い面が不自然に読め目視で落とした（gate は pass — 帯は
色しか見ないので、構造の検品は目視のまま）。

### 膝枕 採用: 9g298c → 2048 は plain で (2026-08-27)

膝枕深掘りの決着。採用は 9g298c — 系譜は kfuthu → b2c54r → lx2mjb →
uk1jfi → z4(w546qv) → z6(tefgig) → z8(6naw05) → z9(ryr4wd) → 下半分
masked reroll（shiny 削除 + gloss ban、denoise 0.3）→ 背景のみ #c7e5e9。
構成: 濃チャコールタイツ（マット寄り微光沢）、halterneck + 濃紫リボン、
白フリル、blush 肌（pale skin 1.15）、hair strands 1.3、あぐら POV。

2048 化で一つ確定: denoise 0.45 の img2img パスは、ピクセル単位で
確定させた絵に対しては裏切る — 背景の平坦グレーに模様を湧かせ、マットに
調整したタイツを紫光沢に戻した（fin-lap i7rs9p/40v8g2、目視棄却）。
採用作の拡大は upscale_plain（モデル不介入）が正解で、これは notes が
以前から言っていたことの再確認。delivered は ybhanv。

タイツの光沢の目盛（ryr4wd 下半分 reroll、全て seed 424242）:
reroll gfwak3 / matte(shiny1.2) mvtl9r / d0.3 9g298c / d0.7+ban 1zbd5y。
shiny weight は d0.5 では効かず（3案同値）、光沢を消す実効レバーは
denoise の深さと negative の gloss ban だった。数値フラット化は
旧ハイライトが青縞で残り棄却。

### 膝枕 最終確定: 39corc — 髪と袖の順序は根元から直す (2026-08-27)

ybhanv 確定後にユーザーが髪と袖の前後関係の破綻を発見（サイドロックが
袖の下から出て途中で上に乗る）。交差部だけの masked reroll（denoise 0.6）
は順序自体を直したが「房が肘から生えている」読みが残った — 頭への接続が
袖に隠れて切れていたのが本因で、マスクを房の根元側（y240-780, x40-520、
顎と手指ゾーンは除外）まで広げ denoise 0.65 で経路ごと再決定したら4/4で
自然になった。局所の occlusion 破綻は、破綻点でなく構造の根元を含めて
描き直す。

最終 delivered: 39corc（seed 606060 の reroll → 背景のみ #c7e5e9 →
upscale_plain 2048 → 紫外縁 #6a3494 10px）。前版 ybhanv/b2lvjj は
系譜として chimera に残る。

## 部屋着 glo2s4 ブラッシュアップ: ボタンは negative では消えない (2026-08-27)

glo2s4（部屋着あぐら smug、good）の胸元に描かれた4つのボタンを除去する依頼。

masked reroll（denoise 0.6、negative に `(buttons:1.5), (button placket:1.4)`
追加、4シード）は 4/4 でボタンを再生成した。タイツの色と同じ機構 — 下地の
暗斑が denoise 0.6 では構造として生き残り、negative は既に画素にあるものを
消せない。

効いたのは二段: ボタン画素を形状で検出（連結成分、面積 150-2500・充填率
>0.55 の丸い暗斑。紐・リボンは巨大連結成分として除外）→ 周辺の明色中央値で
塗り潰し → その領域だけの soft mask（σ4）で denoise 0.35 refine。1パスで
4つとも消え、リボンと編み目は不変。

マスク外は VAE 再エンコードで輪郭に 1px 級の差分が散る。採用時は soft mask
で元画像にアルファ合成し、変更をボタン列（y506-686, x461-513）だけに限定した。

delivered: glo2s4 → ボタン除去 (uf2uaq) → plain 2048 → 紫外縁 #6a3494 10px
= tsrog3（batch 7kvboq）。
