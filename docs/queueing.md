# Queueing

> The characters described here belong to their original works — see
> [Derivative work](../README.md#derivative-work) in the README. Rights in
> them rest with their creators, not with this repository.

Every script here takes `--host`/`--port` where it makes sense, and otherwise
reads `COMFYUI_HOST`/`COMFYUI_PORT`. Unset, they fall back to `127.0.0.1:8188`.
See [remote.md](remote.md) for what changes when the server is elsewhere.

`./.venv/bin/python scripts/<name>.py ...` works the same as `uv run` throughout,
if you prefer not to use uv.

## A minimal prompt

```bash
uv run scripts/queue_prompt.py \
  --ckpt-name your-model.safetensors \
  --prompt "pixel art, 16-bit, game sprite, limited palette, crisp edges, simple shading"
```

The API workflow shape this posts is tracked at
`workflows/templates/minimal-txt2img-api.json`.

For img2img with a file already placed in the server's `input/`:

```bash
uv run scripts/queue_img2img.py \
  --ckpt-name your-model.safetensors \
  --image your-base-image.png \
  --prompt "retro jrpg pixel art sprite"
```

## Anima

[Anima](https://huggingface.co/circlestone-labs/Anima) needs three files on
whichever machine serves ComfyUI:
`diffusion_models/anima-preview3-base.safetensors`,
`text_encoders/qwen_3_06b_base.safetensors` and `vae/qwen_image_vae.safetensors`.
All three come from that repo's `split_files/`; [models.md](models.md) has the
exact paths and hashes.

```bash
uv run scripts/queue_anima.py \
  --prompt "masterpiece, best quality, 1girl, solo, retro artstyle, cel shading"
```

Anima preview3 is a base (non-distilled) model. The defaults — 30 steps, cfg 4.0,
`er_sde`/`simple` — reflect that. Turbo-style settings such as 8 steps or cfg 1.0
produce collapsed images, and cfg 1.0 also disables the negative prompt entirely.

## The Dragon Quest III portrait recipe

`scripts/queue_dq3.py` carries a settled recipe as its defaults, so the bare
command reproduces the look it was tuned to:

```bash
uv run scripts/queue_dq3.py --job sage --count 3
uv run scripts/queue_dq3.py --job priest --pose sitting
```

The defaults are Amanatsu in diffusers layout, `dpmpp_2m`/`karras`, 1280x1920,
the `moe` face, the `cel` style, and a two-LoRA stack (`perfect-eyes` 0.4 and
`detailed-perfection` 0.5) whose trigger words are appended automatically. Pass
`--lora` yourself to replace the stack entirely; anything else is a normal
override. `--diffusers-path ''` falls back to `--ckpt-name`.

`--job` picks the class, `--pose` the framing, `--face` and `--style` select tag
presets, `--extra` appends to the positive prompt and `--negative-preset light`
drops the shine and toon blocks.

`--style cel-plain` is `cel` without the sticker border. Dropping those three
tags changes more than the outline: the cape spreads wider, the legwear gloss
comes up, and the result reads as an illustration rather than a die-cut
sticker.

1280x1920 costs roughly four minutes an image on an M1 Max. For iteration,
`--width 1024 --height 1536 --steps 22` is visually close and about four times
faster — `dpmpp_2m` has converged well before 30 steps.

### What the presets encode

Each of these cost a batch to find, and most are not obvious. The long form,
with the measurements behind them, is in [render-notes.md](render-notes.md).

- **The class tag alone drifts.** `sage (dq3)` pulls in warrior gear and sleeved
  robes, so the outfit is spelled out and the gear negatives carry weights.
- **Shine has to be pinned to the legwear** or skin and cloth render as latex,
  and `muscular*` belongs in the negatives so thicker calves read as soft.
- **Black linework and gradient shading cancel out.** They describe the same
  surface two different ways. `cel` commits to flat colour with hard shadow
  edges; `rich` commits to gradients. Mixing them looked wrong both times.
- **Illustrious tints outlines to match the fill**, which is a large part of what
  reads as machine-made, so `colored lineart` is negated at weight.
- **Resolution is the reliable way to thin lines.** Line width is roughly
  constant in pixels, so a bigger frame thins them without the negatives that
  also drain the black out.
- **The prompt is saturated.** Adding weighted tags visibly costs the existing
  ones: two thigh tags flattened the shading, and seven sleeve tags rewrote the
  outfit. Prefer replacing a tag over adding one.
- **Negatives must not describe a legitimate shape.** `ragged`/`tattered` shrank
  the cape, because the sage's cape genuinely has a pointed hem.
- **`dragon quest` anchors the palette.** Removing it to escape the anime's look
  made the drift worse, not better; the anime association comes from the
  saturation tags instead.

## Reopening a render as a graph

Every queued job also submits a UI-format ("litegraph") copy of the graph
alongside the API graph, built from `/object_info` by `scripts/workflow_ui.py`.
That copy shows up under `extra_data.extra_pnginfo.workflow` in
`/history/<prompt_id>`, and ComfyUI writes it into the PNG as a `workflow`
text chunk, so dropping a generated image onto the ComfyUI canvas reopens the
graph that made it.

`--export-workflow PATH` writes that same UI-format JSON to a file for the first
image in the run, without changing anything else about the queue behaviour:

```bash
uv run scripts/queue_dq3.py --job sage --export-workflow workflows/templates/dq3sage.json
```

If `/object_info` cannot be reached, the script warns on stderr and queues the
image without a workflow attached rather than failing the run.

## Swapping the checkpoint

Changing checkpoint moves the art style further than any tag or IPAdapter
setting does, so it is worth trying before tuning either. Most Civitai
checkpoints are mirrored to Hugging Face by `John6666` in **diffusers layout**,
which `CheckpointLoaderSimple` cannot read — `--diffusers-path` routes the graph
through `DiffusersLoader` instead, which returns the same MODEL/CLIP/VAE:

```bash
uv run scripts/queue_dq3.py --job sage --diffusers-path amanatsu-il-v11
```

Place the repo under the serving machine's `models/diffusers/<name>/` keeping
its `unet/`, `vae/`, `text_encoder*/`, `tokenizer*/`, `scheduler/` and
`model_index.json`, then restart ComfyUI so the path is registered. Everything
else — presets, IPAdapter, masks — works unchanged.

The four checkpoints these recipes were tuned against are listed in
[models.md](models.md) with their John6666 repo names, so `--diffusers-path
amanatsu-il-v11` and friends can be put back without hunting for which upstream
they came from.

## Varying scenes with a local LLM

`scripts/gen_variants.py` asks a local ollama model for scene tags and queues one
image per variant, so batches vary without hand-writing `--extra` each time:

```bash
uv run scripts/gen_variants.py --job sage --count 5 --wait
uv run scripts/gen_variants.py --job mage --theme "夕暮れの街道" --dry-run
```

`--dry-run` prints the variants without queueing, `--theme` accepts free text in
any language, and `--model` selects the ollama model (default `qwen3:30b-instruct`).

The model is handed a fixed `VOCABULARY` and told to recombine it rather than to
write tags freely. Local models recall Danbooru vocabulary poorly but recombine a
supplied list reliably, and the constraint also keeps them away from the outfit
and legwear tags in `queue_dq3.py`. The vocabulary deliberately omits
`from below`, `cowboy shot` and `close-up`, which fight that script's framing
negatives.

## Tracked workflow templates

- `workflows/templates/minimal-txt2img-api.json` (API format)
- `workflows/templates/anima-txt2img-api.json` (API format)
- `workflows/templates/dq3sage.json` (UI format)

The two API-format files are the shape `/prompt` takes; they do not load as a
graph in the ComfyUI web UI and only serve as a reference for what those scripts
POST. `dq3sage.json` is a UI ("litegraph") workflow instead — drag it onto the
ComfyUI canvas, or load it through the Workflow menu, and edit the checkpoint,
prompt text, or anything else from there. It is regenerated with
`--export-workflow`, above.
