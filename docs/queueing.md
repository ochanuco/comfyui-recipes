# Queueing

> Yuzuki Yukari belongs to her original creators and rights holders — see
> [Derivative work](../README.md#derivative-work) in the README.

A generation request is queued on chimera (MCP `derive_request` /
`create_request`, or `POST /api/v1/requests`) and executed by
`comfy-recipes work` on the GPU box. For a `generate` row the worker runs the
same code path as `comfy-recipes generate --request`: validate the request,
submit the graph to ComfyUI, ingest the result into chimera. `generate` by
hand is for replaying a recorded request file on the worker box, or for a
dry run that validates a file without sending anything:

```bash
uv run comfy-recipes generate --request request.json --dry-run   # validate only
uv run comfy-recipes work                                        # serve the queue
```

The request contract is schema version 1. `generation.recipe` must be
`yukari`, `yukari-anima` or `yukari-sketch`, and `generation.parameters.pose`
is required. `costume` is optional for all three; `hires` and `denoise` are
yukari-only, and `expression` is anima-only -- `yukari-anima` and
`yukari-sketch` both reject `hires`/`denoise` (neither has a second pass),
and `yukari-sketch` rejects `expression` too (it has no expression records).
A `semantic.summary` is required so each render has evaluation context
before it is ingested. State is kept beside the request as
`<request>.state.json`; retain it to resume safely after a crash. A recorded
`comfy_prompt_id` that ComfyUI no longer knows about is resubmitted rather
than waited on.

The ComfyUI server may be local or remote. Set `COMFYUI_HOST` and optionally
`COMFYUI_PORT`; inputs and outputs are transferred through the server API when
the host is remote. See [remote.md](remote.md).

## Queue worker

`comfy-recipes work` is a resident worker: it claims one row at a time from
chimera's `requests` queue (`POST /api/v1/requests/claim`, kinds `generate`,
`finalize`, `repair` and `masked_redraw`), executes it, and reports
`done`/`failed` back (`PATCH /api/v1/requests/{id}`). While a row runs it
heartbeats `{"status": "running"}` every 30 seconds; `--interval` is how long
it sleeps when the queue is empty. `--once` claims and executes a single row
then exits; `--dry-run` never claims -- it fetches and prints the next
queued row instead. `--worker-id` defaults to the machine's hostname;
`--kinds` (comma-separated, default `generate,finalize,repair,masked_redraw`)
narrows which kinds this worker claims.

A `generate` row's payload is a request.json body, written verbatim to
`<output_root>/requests/<id>.json` before running the same `generate()` use
case `comfy-recipes generate` does. A `finalize` row's payload is
`{"generation_id", "options": {...}}`; `options` maps to `finalize()`'s CLI
flags (`denoise`, `repin`, `recolor`, `keep_legwear`, `route`, `finalizer`,
`size`, `deliver_size`, `handdrawn`, `skin`, `toe_guard`, `keep_scene`,
`stroke_light`, `repair`, `repair_regions`, `repair_denoise`, `repair_pad`,
`repair_size`, `repair_lora`) with the same defaults `comfy-recipes finalize`
has when a flag is omitted. A `repair` row's payload is `{"generation_id", "options":
{...}}` too; see [Repair](#repair) below for its options. A `masked_redraw`
row's payload is the same shape again; see
[Masked redraw](#masked-redraw) below for its options.

`backdrop` (`--backdrop` on the CLI) takes a `#RRGGBB` colour or the named
pattern `stripes`; setting it turns off the sketch recipe's transparent
default and delivers an opaque sticker on that backdrop instead.

Idempotency keys are derived from the request id, so a re-claimed row
resumes the same batch/job/generation records: batch `request:{id}`, job
`request:{id}:job:{index}`, generation
`request:{id}:job:{index}:gen:{output_index}`. finalize, repair and
masked_redraw use the same batch and job keys.

A row's `recipe_ref` must equal the worker's current git branch; a worker on
the wrong branch fails the row rather than generating from a recipe it
cannot vouch for. chimera's own `docs/worker-protocol.md` (in the chimera
repo) is the authoritative wire contract this command implements -- this
section is only what `--help` does not already say.

By default `work` also keeps an outbound websocket open to chimera's
WorkerHub, so a queued row is claimed as soon as it is posted instead of on
the next `--interval` poll; the socket also relays ComfyUI's own sampling
progress (`/ws`) back to chimera as it happens. Either side dropping just
means the next poll or the next reconnect picks the claim back up --
`--interval` polling is the fallback, not a fallback that needs enabling.
Pass `--no-hub` to disable the socket and poll only.

## Catalog

`comfy-recipes catalog` prints this worker's recipe vocabulary as one JSON
document -- schema version 1, with `git_commit`/`git_branch`/`git_dirty`,
`generated_at` (ISO 8601 UTC) and a `recipes` array (`yukari`,
`yukari-anima`, `yukari-sketch`). Each recipe entry has the checkpoint its
`render_spec` uses, a `parameters` block (`allowed`/`rejected` keys, agreeing
with `generate.py`'s own per-recipe validation), its `costumes`
(`yukari-anima` also lists `expressions`), a `parts` list (the recipe's named
positive-prompt parts in join order -- `[]` for `yukari`, which has none),
an `identity_tags` list (bare identity tags for the recipe's default
costume), and one `poses` entry per pose: name, default costume, face
override (`null` where the recipe has none), `expression` (anima poses
only), the canvas `render_spec` would use, the fully assembled
positive/negative prompt for that pose's own default costume, and -- for
`yukari-sketch`/`yukari-anima` only -- a `parts` list of `{"name", "text"}`
whose texts concatenate to `positive` byte for byte. A `patches` block
mirrors `domain/generation/patches.py`'s
`TEXT_TARGETS`/`NUMBER_TARGETS`/`STRING_TARGETS` -- ops, one-line numeric
constraints, and the closed string enums -- plus `text.part_target`
(`"prompt.positive.<part>"`) and an `overrides` block documenting
`identity_override`, so an agent with no shell can compose
`generation.patches` from the catalog alone.

```bash
uv run comfy-recipes catalog                # print the document
uv run comfy-recipes catalog --publish       # print it, then PUT and print the response
```

`--publish` PUTs the document to `PUT /api/v1/catalogs/{recipe_ref}`
(upsert), where `recipe_ref` is this worker's git branch -- the same value
`work`'s rows compare `recipe_ref` against. `comfy-recipes work` publishes
the catalog once at startup, best-effort: a publish failure is logged and
does not stop the worker from serving. Pass `--no-catalog` to skip it.

## Named dials

Each catalog recipe entry carries a `dials` object -- up to three scopes
(`finalize`, `repair`, `patches`), each mapping an option key to a
`{word: number}` vocabulary a caller can name instead of typing the raw
number. A finalize/repair/masked_redraw row's `options`, and a
`generation.patches` number-target patch's `value`, accept a dial word
anywhere a number is legal; the worker resolves it against the source
generation's batch (`batch.recipe`) and rejects an unknown word, or a word
for a key/recipe with no dials, the same way it rejects a number out of
range. `masked_redraw`'s own `denoise` resolves against the recipe's
`repair` scope rather than a `masked_redraw` scope of its own. The bare
tri-state `true` (`keep_legwear`, `toe_guard`, `repair_lora`, `lora`) keeps
its existing constant; a recipe's `"on"` word, where published, resolves to
that same number.

```json
{"denoise": "tidy", "repin": true, "keep_legwear": true}
```

resolves to `{"denoise": 0.65, "repin": true, "keep_legwear": 0.62}` on
`yukari-sketch`, and a finalize/repair/masked_redraw row's result gains
`resolved_options` -- the request's own options, words and `true` replaced
by what they resolved to, keys the request did not give omitted -- so a
caller can read back what actually ran without re-deriving it from the
catalog. `comfy-recipes finalize --denoise/--lora-strength/--repair-denoise
/--keep-legwear/--toe-guard/--repair-lora` and `comfy-recipes repair
--denoise/--lora` accept a word the same way; the CLI already has the
generation id, so it looks up the recipe itself.

## Repair

`comfy-recipes repair <generation>` masks and redraws just the hands and/or
feet of an existing generation instead of the whole canvas: DWPose locates
the region, `InpaintCropImproved` crops to it, the source's own model, LoRA
and prompt resample it at a moderate denoise, and `InpaintStitchImproved`
blends the crop back into the full frame. It is a queue kind
(`{"kind": "repair", "payload": {"generation_id": ..., "options": {...}}}`)
and a CLI subcommand with the same options:

The same reroll is available inside finalize: `--repair`/`--repair-region`/
`--repair-denoise`/`--repair-pad`/`--repair-size`/`--repair-lora` on
`comfy-recipes finalize` (or `repair`/`repair_regions`/`repair_denoise`/
`repair_pad`/`repair_size`/`repair_lora` in a queued finalize row's
`options`) splice the same masked reroll into the delivery redraw's own
ComfyUI submission, instead of queueing a second `repair` request against
the finalized result. Pose detection runs on the raw pick, and the
resulting regions are scaled into the redraw's own (larger) canvas before
the mask is rendered.

```bash
uv run comfy-recipes repair <generation_id> \
  --parts hands,feet --denoise 0.6 --seeds 1,2,3,4 --size 1024 --pad 1.0 --lora
```

| option | CLI flag | default | meaning |
| --- | --- | --- | --- |
| `parts` | `--parts` | `["hands", "feet"]` | which auto-detected regions (from DWPose) to include |
| `regions` | `--region x0,y0,x1,y1` (repeatable) | `[]` | extra rectangles, as fractions (0..1) of width/height, added to the mask |
| `denoise` | `--denoise` | `0.6` | the local redraw's own denoise, `0 < d <= 1` |
| `seeds` | `--seeds` | `[1, 2, 3, 4]` | one job per seed |
| `size` | `--size` | `1024` | the crop's target long side, a multiple of 8, at least 256 |
| `pad` | `--pad` | `1.0` | multiplier on the auto-detected region radius, `0.5..3` |
| `lora` | `--lora [WEIGHT]` | off | load each redrawn part's own LoRA (Feet XL for `feet`, Hands XL for `hands`) inside the crop; bare flag/`true` is weight `0.8`, or give a number in `0..2` |
| `model` | `--model` | off | sample the crop on another checkpoint instead of the source's own, from the vocabulary in `domain/repair/models.py` (`anima`, `anima-hassaku`, `anima-base`); the crop/mask/stitch stay on the source graph, only the reroll's model/CLIP/VAE/sampler move. Skips `lora` -- the part LoRA chain is Illustrious-only |
| `control` | `--control SIGNAL` | off | route the crop's conditioning through a ControlNet fed by a synthetic reference hint (see `domain/repair/controlnet.py`); the only signal currently defined is `lineart` |
| `control_strength` | `--control-strength STRENGTH` | `0.8` | the ControlNet's own strength, `0 < s <= 2`; only used when `control` is set |

`repair_lora` on a finalize-carried repair works the same way; `--repair-lora
[WEIGHT]` / `repair_lora` in a queued finalize row's `options`. `model` /
`control` / `control_strength` are not available on a finalize-carried
repair, only on the standalone `repair` request kind and CLI subcommand.

At least one of `parts` or `regions` must be non-empty; a request with both
empty is rejected before anything is submitted.

**Source resolution**: repair does not necessarily redraw the generation it
was pointed at. If that generation's batch is a finalize batch
(`parameters.kind == "hires-chain"`), repair picks the largest (by pixel
count) sibling in that batch's `generations` -- the raw redraw, not the
smaller delivered sticker -- regardless of which one the caller named.
Otherwise it uses the given generation directly.

**Outputs**: one job per seed, ingested the same way `finalize` ingests its
graph's outputs -- a `-matte` suffixed output becomes a `mask` asset on the
raw generation, a `-delivered` suffixed output becomes a second generation,
anything else is the raw generation. The rendered region mask itself is
also stored as a `repair-mask` asset on every job's raw generation, so the
exact region redrawn is on record without recomputing it from the pose.

## Masked redraw

`comfy-recipes masked_redraw <generation>` is `repair` without DWPose: the
mask is built only from caller-given rectangles, and the prompt edit is a
free-text patch instead of a fixed hands/feet vocabulary -- for any region a
caller can already point at (garment swaps, prop removal, background
patches), not just hands and feet. It shares `repair`'s crop/resample/stitch
machinery (`InpaintCropImproved` -> `KSampler` -> `InpaintStitchImproved`)
and its source-resolution and output-ingestion rules verbatim; see
[Repair](#repair) above for both. It is a queue kind
(`{"kind": "masked_redraw", "payload": {"generation_id": ..., "options":
{...}}}`) and a CLI subcommand with the same options:

```bash
uv run comfy-recipes masked_redraw <generation_id> \
  --region 0.18,0.42,0.86,0.96 \
  --prompt-patch "replace only the waist-to-hem garment with a long loose A-line mid-calf dress" \
  --denoise 0.48 --mask-padding 24 --mask-feather 8 --size 768 --seeds 101,202
```

| option | CLI flag | default | meaning |
| --- | --- | --- | --- |
| `regions` | `--region x0,y0,x1,y1` (repeatable) | required, at least one | rectangles, as fractions (0..1) of width/height, that make up the mask; `x0<x1`, `y0<y1`, non-overlapping |
| `prompt_patch` | `--prompt-patch` | required | text appended to the source's own positive prompt (after the same face/hair/framing drop `repair` applies), at most 4096 characters |
| `denoise` | `--denoise` | `0.45` | the local redraw's own denoise, `0 < d <= 0.75` |
| `mask_padding` | `--mask-padding` | `0` | `InpaintCropImproved`'s `mask_expand_pixels`, `0..512` |
| `mask_feather` | `--mask-feather` | `32` | `InpaintCropImproved`'s `mask_blend_pixels`, `0..256` |
| `size` | `--size` | `1024` | the crop's target long side, a multiple of 8, at least 256 |
| `seeds` | `--seeds` | `[1, 2, 3, 4]` | one job per seed, at most 16 |

Unlike `repair`, there is no `parts`/pose-driven region and no part-specific
prompt vocabulary -- `regions` is always required, and DWPose never runs.

## `generation.patches`

`generation.patches` declares typed diffs applied to the resolved render
spec, for draft arms and revisions that must not touch the settled recipe.
Text targets are `prompt.positive`, `prompt.negative`,
`prompt.hires.positive`, and `prompt.hires.negative`, with ops `append`,
`prepend`, `replace`, and `remove`; `replace` and `remove` require an `old`
needle, and a needle absent from the text is an immediate error rather than
a silent no-op. `prompt.positive.<part>` targets one named part of the
recipe's positive prompt instead of the whole string -- same ops and fields
as `prompt.positive` -- then the parts are rejoined; targeting a part on a
recipe with none (`yukari`) or an unrecognised part name is a clear
`ValueError` naming the valid parts. Number targets are `render.cfg`, `render.steps`,
`render.width`, `render.height`, `hires.denoise`, `render.layerdiffuse_weight`,
and `render.lora_strength`, with op `set`; `render.cfg` and `render.steps`
govern both sampling passes, since the spec holds one value for each.
`render.width` and `render.height` each require an int that is at least 64
and a multiple of 8. `render.layerdiffuse_weight` requires `-1 <= value <= 3`.
`render.lora_strength` requires `0 <= value <= 2` and sets every LoRA in the
recipe to that strength; it fails on a recipe with no LoRA. String targets
are `render.model`, `render.sampler`, `render.scheduler`, and
`render.layerdiffuse_config`, with op `set` only and a required non-empty
string `value`; `render.layerdiffuse_config` must be `"SDXL, Attention
Injection"` or `"SDXL, Conv Injection"`.

Every patch requires a one-line `reason`. The patch list is recorded into
each generation's semantic attributes at ingest, and the submitted graph
remains the effective record. Patches apply in list order after the recipe
compiles, and are mutually exclusive with `generation.graph` (which stays
available as the escape hatch for structural experiments) and with full
`prompt`/`negative_prompt` overrides.

`generation.parameters` is a closed set: `pose`, `costume`, `hires`,
`denoise`, `expression`, `character`, `character_id`, `arm`. Unknown keys
are rejected -- annotations belong in `semantic.attributes`, executable
diffs in `generation.patches`.

```json
"generation": {
  "recipe": "yukari",
  "parameters": {"pose": "lounge"},
  "patches": [
    {"target": "prompt.positive", "op": "replace",
     "old": "(pale skin:1.25)", "value": "(pale skin:1.2)",
     "reason": "softer skin tone for this arm"},
    {"target": "render.cfg", "op": "set", "value": 4.5,
     "reason": "lower guidance for the draft pass"}
  ]
}
```

`--dry-run` compiles the patched spec without submitting anything: it prints
the resolved positive prompt, the graph nodes, and the applied patch count,
and a patch that cannot compile (an absent needle, a bad type) fails there
-- and on a real run it fails before the batch is created.

After presets, a `generation.prompt` override and every patch are applied,
the worker checks that every identity tag in the recipe's unpatched prompt
(hair colour/length, sidelocks, eye colour, hair ornament, eye-shape
identity, and the costume's cardigan/hood, compared bare -- weight syntax
and parentheses stripped) is still present in the final positive. If one is
missing and `generation.identity_override` is absent, the request fails
before rendering with a message listing the removed tags. A non-empty
`identity_override` (validated like `lint_waiver`) lets it render anyway,
and the removed tags plus the override reason are recorded on the
generation's `semantic.attributes` and on the Batch.

Every render is measured against the palette bands at ingest, and the
numbers -- plus a pass/FAIL verdict -- land in its semantic attributes.
`comfy-recipes finalize` can repin the render before the layered delivery;
`--repin` opts in (off by default). The repin compresses saturation per V
band toward the reference render's knees (`delivery_style`'s `REPIN_*`):
below a knee a pixel is untouched, above it only a fraction of the excess
survives, and accent-grade saturation -- the iris, the hair pins -- keeps
most of its excess and its own hue, so the eyes stay vivid while vivid
fields pin pale.
`--keep-legwear [COL_CUT]` additionally keeps an asserted legwear region
verbatim, fading the correction to zero over its feathered edge; the cut is
the width share the legs stay left of (default 0.62), a property of the
composition.

`--recolor` replaces repin in the same slot for renders where repin cannot
reach the actual defect: repin only ever nudges saturation, so a washed-out
black or a flat white fill has no gradation left for any curve to open.
Recolor instead detects the render's own linework, labels the fills it
encloses, classifies each fill as a material (hair, hoodie, dress, skin,
legwear, ...), and repaints it from a measured reference palette outright --
asserting the render's colour rather than nudging it, at the cost of
trusting the classifier where repin trusts the render. `--recolor` and
repin are mutually exclusive; the flag wins when both would otherwise apply.

## A minimal prompt

```bash
uv run scripts/queue_prompt.py --ckpt-name your-model.safetensors \
  --prompt "pixel art, 16-bit, game sprite, limited palette, crisp edges"
```

The API workflow shape is tracked at
`workflows/templates/minimal-txt2img-api.json`. For img2img with an image in
the server's `input/` directory:

```bash
uv run scripts/queue_img2img.py --ckpt-name your-model.safetensors \
  --image your-base-image.png --prompt "retro jrpg pixel art sprite"
```

## Yukari prompt inspection

```bash
uv run comfy-recipes yukari prompt --pose lounge
uv run comfy-recipes yukari prompt --pose lounge --costume sporty
```

The recipe has 40 poses and four costumes. Prompt edits are ordered and fail
loudly when their expected text is absent; do not reconstruct prompt strings
outside the recipe.

## Anima

[Anima](https://huggingface.co/circlestone-labs/Anima) needs its split model
files on the ComfyUI machine. See [models.md](models.md) for exact paths and
hashes. The retained helper uses the base model defaults (30 steps, cfg 4.0,
`er_sde`/`simple`); turbo-style settings can collapse the result.

```bash
uv run scripts/queue_anima.py \
  --prompt "masterpiece, best quality, 1girl, solo, retro artstyle, cel shading"
```

## Reopening and changing workflows

API-format templates describe the graph posted to `/prompt`; they do not load
as a ComfyUI canvas workflow. UI-format workflows include the metadata needed
to reopen a graph in the web UI. A recorded job stores its submitted graph,
which is the authoritative replay record.

## Swapping the checkpoint

Most Hugging Face checkpoints used here are in diffusers layout. Keep the
`unet/`, `vae/`, `text_encoder*/`, `tokenizer*/`, `scheduler/`, and
`model_index.json` files under `models/diffusers/<name>/`, then restart
ComfyUI. See [models.md](models.md) for model provenance.

## Tracked workflow templates

- `workflows/templates/minimal-txt2img-api.json` (API format)
- `workflows/templates/anima-txt2img-api.json` (API format)

Every recorded job stores its submitted graph. A graph can therefore be
replayed from Chimera without relying on an undocumented second queue path.
