# Queueing

> Yuzuki Yukari belongs to her original creators and rights holders — see
> [Derivative work](../README.md#derivative-work) in the README.

Yuzuki Yukari generation requests are recorded through `comfy-recipes generate`,
which validates the request, submits the graph to ComfyUI, and ingests the
result into Chimera. Use the same command for dry runs and real batches:

```bash
uv run comfy-recipes generate --request request.json --dry-run
uv run comfy-recipes generate --request request.json
```

The request contract is schema version 1. `generation.recipe` must be
`yukari` or `yukari-anima`, and `generation.parameters.pose` is required.
`costume` is optional for either; `hires` and `denoise` are yukari-only,
and `expression` is anima-only. A `semantic.summary` is required so each
render has evaluation context before it is ingested. State is kept beside
the request as `<request>.state.json`; retain it to resume safely after a
crash.

The ComfyUI server may be local or remote. Set `COMFYUI_HOST` and optionally
`COMFYUI_PORT`; inputs and outputs are transferred through the server API when
the host is remote. See [remote.md](remote.md).

## `generation.patches`

`generation.patches` declares typed diffs applied to the resolved render
spec, for draft arms and revisions that must not touch the settled recipe.
Text targets are `prompt.positive`, `prompt.negative`,
`prompt.hires.positive`, and `prompt.hires.negative`, with ops `append`,
`prepend`, `replace`, and `remove`; `replace` and `remove` require an `old`
needle, and a needle absent from the text is an immediate error rather than
a silent no-op. Number targets are `render.cfg`, `render.steps`,
`render.width`, `render.height`, and `hires.denoise`, with op `set`;
`render.cfg` and `render.steps` govern both sampling passes, since the spec
holds one value for each. `render.width` and `render.height` each require
an int that is at least 64 and a multiple of 8.

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
