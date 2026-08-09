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
| `f066dccc` | `abc-F-softline_00001_` | 4051776310 | ab-C rescued by self-trace: same composition, no intruder (tag `pick/abc-F`) |
| `23e7f00f` | `mn-h-grey_00001_` | 1117511306 | the colouring. `--minimal` on Hassaku: flat field, thin tinted line, no cast shadow, no gloss (tag `pick/mn-h-grey`). Reproduced by bare `--job takao --pose lookback --width 1024 --height 1536 --minimal --diffusers-path hassaku-il-v22` — prompt verified byte-identical |
| `cac2cf43` | `bm-moevpred_00001_` | 1117511306 | the face. `moe-vpred-v2` draws the small round face with large round irises that the identical tags do not produce on any other base — see the base sweep below. Reproduced by bare `--job takao --pose lookback --width 1024 --height 1536 --style cel-plain --flat-paint mild` |
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

So `BASE_BY_JOB` now gives `takao` `moe-vpred-v2` — bare
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

## Open, for next time

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
