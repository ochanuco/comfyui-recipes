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
`yukari`, and `generation.parameters.pose` is required. `costume`, `hires`,
and `denoise` are optional. A `semantic.summary` is required so each render
has evaluation context before it is ingested. State is kept beside the request
as `<request>.state.json`; retain it to resume safely after a crash.

The ComfyUI server may be local or remote. Set `COMFYUI_HOST` and optionally
`COMFYUI_PORT`; inputs and outputs are transferred through the server API when
the host is remote. See [remote.md](remote.md).

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
