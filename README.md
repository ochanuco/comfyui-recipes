# ai-comfyui-env

This repository manages the local runtime around [ComfyUI](https://github.com/Comfy-Org/ComfyUI) without vendoring the upstream application itself.

## Layout

- `config/`: tracked runtime configuration
- `docs/`: local operating notes
- `manifests/`: tracked custom-node inventory
- `scripts/`: bootstrap, update, and launch entrypoints
- `.local/ComfyUI`: upstream clone created by the scripts and excluded from Git
- `.local/assets`: model storage root created by the scripts and excluded from Git

## First-Time Setup

```bash
./scripts/bootstrap-comfyui.sh
```

Python `3.12` is required. The scripts reuse `.venv` when it already exists and matches that version.

The bootstrap script will:

1. clone `ComfyUI` into `.local/ComfyUI`
2. create or reuse `.venv`
3. install upstream Python requirements
4. render `.local/ComfyUI/extra_model_paths.yaml`
5. sync custom nodes listed in `manifests/custom-nodes.toml`

## Daily Commands

```bash
./scripts/update-comfyui.sh
./scripts/run.sh
./scripts/install-custom-nodes.sh
```

The default upstream pin is `v0.30.1`. The local checkout will stay on that release tag until you change `config/upstream.env`.

## Queue A Minimal Prompt

Start ComfyUI first, then queue a simple txt2img job:

```bash
uv run scripts/queue_prompt.py \
  --ckpt-name your-model.safetensors \
  --prompt "pixel art, 16-bit, game sprite, limited palette, crisp edges, simple shading"
```

`./.venv/bin/python scripts/queue_prompt.py ...` works the same way if you prefer not to use uv.

The API workflow shape used by that script is also tracked at `workflows/templates/minimal-txt2img-api.json`.

For img2img with a file already placed under `.local/ComfyUI/input`:

```bash
uv run scripts/queue_img2img.py \
  --ckpt-name your-model.safetensors \
  --image your-base-image.png \
  --prompt "retro jrpg pixel art sprite"
```

## Queue An Anima Prompt

[Anima](https://huggingface.co/circlestone-labs/Anima) needs three files under
`.local/assets`: `diffusion_models/anima-preview3-base.safetensors`,
`text_encoders/qwen_3_06b_base.safetensors` and `vae/qwen_image_vae.safetensors`.

```bash
uv run scripts/queue_anima.py \
  --prompt "masterpiece, best quality, 1girl, solo, retro artstyle, cel shading"
```

Anima preview3 is a base (non-distilled) model. The defaults — 30 steps, cfg 4.0,
`er_sde`/`simple` — reflect that. Turbo-style settings such as 8 steps or cfg 1.0
produce collapsed images, and cfg 1.0 also disables the negative prompt entirely.

## Queue A Dragon Quest III Portrait

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

1280x1920 costs roughly four minutes an image on an M1 Max. For iteration,
`--width 1024 --height 1536 --steps 22` is visually close and about four times
faster -- `dpmpp_2m` has converged well before 30 steps.

### What the presets encode

Each of these cost a batch to find, and most are not obvious:

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

## Swap The Checkpoint

Changing checkpoint moves the art style further than any tag or IPAdapter
setting does, so it is worth trying before tuning either. Most Civitai
checkpoints are mirrored to Hugging Face by `John6666` in **diffusers layout**,
which `CheckpointLoaderSimple` cannot read — `--diffusers-path` routes the graph
through `DiffusersLoader` instead, which returns the same MODEL/CLIP/VAE:

```bash
# fetch every non-.bin file of the repo into assets/diffusers/<name>/
uv run scripts/queue_dq3.py --job sage --diffusers-path amanatsu-il-v11
```

Place the repo under `.local/assets/diffusers/<name>/` keeping its `unet/`,
`vae/`, `text_encoder*/`, `tokenizer*/`, `scheduler/` and `model_index.json`,
then restart ComfyUI so the path is registered. Everything else — presets,
IPAdapter, masks — works unchanged.

## Vary Scenes With A Local LLM

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

Tracked API workflow templates:

- `workflows/templates/minimal-txt2img-api.json`
- `workflows/templates/anima-txt2img-api.json`
- `workflows/templates/dq3sage.json`

You can import either JSON into ComfyUI and then edit the checkpoint name, prompt text, and input image filename in the UI.

## Python Environment

`.venv` is populated from the pinned upstream checkout's `requirements.txt` by
`./scripts/update-comfyui.sh`, so those packages are deliberately not declared in
`pyproject.toml`. To keep uv from treating them as extraneous and uninstalling them,
the project is marked `[tool.uv] managed = false`. As a result `uv run` uses `.venv`
without syncing, and `uv sync` / `uv lock` refuse to run. Change dependencies through
`config/upstream.env` and the update script, not by editing `pyproject.toml`.

## Tracked Files You Should Edit

- `config/upstream.env`: choose the upstream ref to follow
- `config/launch.env`: default listen host, port, and extra launch flags
- `config/extra_model_paths.yaml.tmpl`: template for model search paths
- `manifests/custom-nodes.toml`: custom node repositories and pinned refs
- `workflows/`: your saved workflow JSON files

## Recommended Workflow

- Keep `COMFYUI_REF` on a validated release tag for normal use.
- Update `COMFYUI_REF` only when you decide to adopt a newer upstream release.
- A tag checkout leaves `.local/ComfyUI` in detached `HEAD`, which is expected for this repo.
- Keep models under `.local/assets` or another external directory rendered through `extra_model_paths.yaml`.
- Treat `.local/ComfyUI` as disposable runtime state. Rebuild it with the scripts rather than editing it manually.
