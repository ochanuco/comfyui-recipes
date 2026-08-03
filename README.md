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
