# Queueing

> Yuzuki Yukari belongs to her original creators and rights holders — see
> [Derivative work](../README.md#derivative-work) in the README.

A generation request is queued on chimera (MCP `derive_request` /
`create_request`, or `POST /api/v1/requests`) and executed by the worker's
`comfy-recipes generate`, which validates the request, submits the graph to
ComfyUI, and ingests the result into Chimera. The same command runs a request
file by hand, for dry runs and real batches:

```bash
uv run comfy-recipes generate --request request.json --dry-run
uv run comfy-recipes generate --request request.json
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
`finalize` and `repair`), executes it, and reports `done`/`failed` back
(`PATCH /api/v1/requests/{id}`). While a row runs it heartbeats
`{"status": "running"}` every 30 seconds; `--interval` is how long it sleeps
when the queue is empty. `--once` claims and executes a single row then
exits; `--dry-run` never claims -- it fetches and prints the next queued row
instead. `--worker-id` defaults to the machine's hostname;
`--kinds` (comma-separated, default `generate,finalize,repair`) narrows which
kinds this worker claims.

A `generate` row's payload is a request.json body, written verbatim to
`<output_root>/requests/<id>.json` before running the same `generate()` use
case `comfy-recipes generate` does. A `finalize` row's payload is
`{"generation_id", "options": {...}}`; `options` maps to `finalize()`'s CLI
flags (`denoise`, `repin`, `recolor`, `keep_legwear`, `route`, `finalizer`,
`size`, `deliver_size`, `handdrawn`, `skin`, `toe_guard`, `keep_scene`,
`stroke_light`, `repair`, `repair_regions`, `repair_denoise`, `repair_pad`,
`repair_size`) with the same defaults `comfy-recipes finalize` has when a
flag is omitted. A `repair` row's payload is `{"generation_id", "options":
{...}}` too; see [Repair](#repair) below for its options.

`backdrop` (`--backdrop` on the CLI) takes a `#RRGGBB` colour or the named
pattern `stripes`; setting it turns off the sketch recipe's transparent
default and delivers an opaque sticker on that backdrop instead.

Idempotency keys are derived from the request id, so a re-claimed row
resumes the same batch/job/generation records: batch `request:{id}`, job
`request:{id}:job:{index}`, generation
`request:{id}:job:{index}:gen:{output_index}`. finalize and repair use the
same batch and job keys.

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
(`yukari-anima` also lists `expressions`), and one `poses` entry per pose:
name, default costume, face override (`null` where the recipe has none),
`expression` (anima poses only), the canvas `render_spec` would use, and the
fully assembled positive/negative prompt for that pose's own default
costume. A `patches` block mirrors `domain/generation/patches.py`'s
`TEXT_TARGETS`/`NUMBER_TARGETS`/`STRING_TARGETS` -- ops, one-line numeric
constraints, and the closed string enums -- so an agent with no shell can
compose `generation.patches` from the catalog alone.

```bash
uv run comfy-recipes catalog                # print the document
uv run comfy-recipes catalog --publish       # print it, then PUT and print the response
```

`--publish` PUTs the document to `PUT /api/v1/catalogs/{recipe_ref}`
(upsert), where `recipe_ref` is this worker's git branch -- the same value
`work`'s rows compare `recipe_ref` against. `comfy-recipes work` publishes
the catalog once at startup, best-effort: a publish failure is logged and
does not stop the worker from serving. Pass `--no-catalog` to skip it.

## Repair

`comfy-recipes repair <generation>` masks and redraws just the hands and/or
feet of an existing generation instead of the whole canvas: DWPose locates
the region, `InpaintCropImproved` crops to it, the source's own model, LoRA
and prompt resample it at a moderate denoise, and `InpaintStitchImproved`
blends the crop back into the full frame. It is a queue kind
(`{"kind": "repair", "payload": {"generation_id": ..., "options": {...}}}`)
and a CLI subcommand with the same options:

The same reroll is available inside finalize: `--repair`/`--repair-region`/
`--repair-denoise`/`--repair-pad`/`--repair-size` on `comfy-recipes finalize`
(or `repair`/`repair_regions`/`repair_denoise`/`repair_pad`/`repair_size` in a
queued finalize row's `options`) splice the same masked reroll into the
delivery redraw's own ComfyUI submission, instead of queueing a second
`repair` request against the finalized result. Pose detection runs on the
raw pick, and the resulting regions are scaled into the redraw's own (larger)
canvas before the mask is rendered.

```bash
uv run comfy-recipes repair <generation_id> \
  --parts hands,feet --denoise 0.6 --seeds 1,2,3,4 --size 1024 --pad 1.0
```

| option | CLI flag | default | meaning |
| --- | --- | --- | --- |
| `parts` | `--parts` | `["hands", "feet"]` | which auto-detected regions (from DWPose) to include |
| `regions` | `--region x0,y0,x1,y1` (repeatable) | `[]` | extra rectangles, as fractions (0..1) of width/height, added to the mask |
| `denoise` | `--denoise` | `0.6` | the local redraw's own denoise, `0 < d <= 1` |
| `seeds` | `--seeds` | `[1, 2, 3, 4]` | one job per seed |
| `size` | `--size` | `1024` | the crop's target long side, a multiple of 8, at least 256 |
| `pad` | `--pad` | `1.0` | multiplier on the auto-detected region radius, `0.5..3` |

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

## `generation.patches`

`generation.patches` declares typed diffs applied to the resolved render
spec, for draft arms and revisions that must not touch the settled recipe.
Text targets are `prompt.positive`, `prompt.negative`,
`prompt.hires.positive`, and `prompt.hires.negative`, with ops `append`,
`prepend`, `replace`, and `remove`; `replace` and `remove` require an `old`
needle, and a needle absent from the text is an immediate error rather than
a silent no-op. Number targets are `render.cfg`, `render.steps`,
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
