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

`scripts/queue_dq3.py` wraps a novaAnimeXL recipe tuned for DQ3 class portraits:

```bash
uv run scripts/queue_dq3.py --job sage --pose standing --count 3
uv run scripts/queue_dq3.py --job priest --pose sitting --wait
```

`--job` picks the class (`sage`, `priest`, `mage`), `--pose` the framing
(`standing`, `sitting`), `--extra` appends to the positive prompt and `--wait`
polls until the images land in `.local/ComfyUI/output`.

The prompt defaults encode a few findings that are easy to lose: the class tags
alone drift toward sleeved robes and horned helmets, so the outfits are spelled
out and the gear negatives carry weights. Shine has to be pinned to the legwear
or the model renders skin and cloth as latex, and `muscular*` belongs in the
negatives so thicker calves read as soft tissue.

## Steer The Look With A Reference Image

`--face` and `--style` pick from tag presets in `scripts/queue_dq3.py`; `--ref-image`
routes the model through IPAdapter so a reference image drives the rendering:

```bash
./scripts/install-custom-nodes.sh      # installs ComfyUI_IPAdapter_plus
uv run scripts/make_ref_masks.py       # writes mask-head.png / mask-legs.png

uv run scripts/queue_dq3.py --job sage \
  --ref-image ref-face.png --ref-mask mask-head.png \
  --ref2-image ref-legs.png --ref2-mask mask-legs.png \
  --ref-weight 0.9 --ref2-weight 0.9 --style painterly
```

Two adapter models are required and are not downloaded by the scripts:

- `assets/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors`
  (`h94/IP-Adapter` → `models/image_encoder/model.safetensors`)
- `assets/ipadapter/ip-adapter-plus_sdxl_vit-h.safetensors`
  (`h94/IP-Adapter` → `sdxl_models/`)

Four findings are baked into the defaults, each of which cost a batch to learn:

- **Crop the reference to a square yourself.** IPAdapter centre-crops whatever it
  is given, so a portrait-orientation reference feeds it the middle of the image
  and never sees the face.
- **Masks are not optional.** Unmasked, the reference repaints the dress, the
  boots and the background in its own colours. `--ref-mask` confines it to the
  head, `--ref2-mask` to the legs, and the torso keeps the class outfit.
- **Bound masks horizontally too.** Full-width bands style the background inside
  them; `make_ref_masks.py` keeps them near the figure and stops the leg band
  above the boots.
- **Weight above ~0.9 hardens every edge**, which reads as late-90s toon-rendered
  CG. `NEG_TOON` and the `painterly` style counter it; `--ref-scaling` barely did.

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
