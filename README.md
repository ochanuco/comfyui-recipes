# ai-comfyui-env

This repository manages the runtime around [ComfyUI](https://github.com/Comfy-Org/ComfyUI) without vendoring the upstream application itself.

## Where Things Run

Since 2026-08-17 this mac does not run ComfyUI. It drives one over the network
instead, and everything else — prompts, inputs, post-processing, the Discord
post — stays here. Point the toolchain at the worker and go:

```bash
export COMFYUI_HOST=192.168.x.x
uv run scripts/queue_dq3.py --job sage
```

[Render On Another Machine](#render-on-another-machine) is the section that
matters; the local-install sections below are kept as the way back.

What that clean-up removed, and what it left:

- `.local/ComfyUI` no longer holds a checkout. Only `output/`, `input/` and
  `user/` remain, because `comfy_host.py` uses the first two as its cache for
  `/view` and `/upload/image`.
- `.local/assets` is gone — all 42 model files, 67GB. Every one was hash-checked
  against a live upstream before deletion, so all of it is recoverable:
  `docs/models.md` says where each file comes from and
  `manifests/models-sha256.txt` verifies a re-download.
- `.venv` no longer carries torch. It holds what the client scripts actually
  import and nothing else.

## Layout

- `config/`: tracked runtime configuration
- `docs/`: local operating notes, including where every model came from
- `manifests/`: tracked custom-node inventory and model hashes
- `scripts/`: queue clients, post-processing, and the local-install entrypoints
- `.local/ComfyUI`: `output/`, `input/` and `user/` only, excluded from Git
- `.local/assets`: model root when a local ComfyUI exists; currently absent

## Restoring A Local ComfyUI

Nothing below is needed to drive a remote worker. It is what to run if this
machine should host ComfyUI again.

```bash
./scripts/bootstrap-comfyui.sh
```

Python `3.12` is required. Note that the script installs the upstream
`requirements.txt` into `.venv`, which will pull torch back in and take it from
231MB to roughly 1.9GB. Models have to be fetched separately, from
`docs/models.md`.

The bootstrap script will:

1. clone `ComfyUI` into `.local/ComfyUI`
2. create or reuse `.venv`
3. install upstream Python requirements
4. render `.local/ComfyUI/extra_model_paths.yaml`
5. sync custom nodes listed in `manifests/custom-nodes.toml`

### Running it once it is back

```bash
./scripts/update-comfyui.sh
./scripts/run.sh
./scripts/install-custom-nodes.sh
```

The default upstream pin is `v0.30.1`. The local checkout will stay on that release tag until you change `config/upstream.env`.

`install-custom-nodes.sh` does not install requirements for
`comfyui_controlnet_aux`: its `requirements.txt` pins `onnxruntime-gpu`, which
publishes no macOS wheel, and the script runs under `set -e`. Install what
DWPose needs by hand instead —

```bash
./.venv/bin/python -m pip install opencv-python scikit-image matplotlib onnxruntime
```

Plain `onnxruntime` carries `CoreMLExecutionProvider` on this machine. The other
preprocessors in that repo want `mediapipe`, `fvcore` and friends; without them
those node modules fail their import and drop out with a warning, which is the
intended behaviour and leaves DWPose working.

Restart ComfyUI after installing a custom node — the node list is built at
startup, and `/object_info/<name>` returns `200` with an empty body for a node
that is not registered, so it is not a usable readiness check on its own.

## Queue A Minimal Prompt

With `COMFYUI_HOST` set (or a local ComfyUI running), queue a simple txt2img
job:

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

[Anima](https://huggingface.co/circlestone-labs/Anima) needs three files on
whichever machine serves ComfyUI:
`diffusion_models/anima-preview3-base.safetensors`,
`text_encoders/qwen_3_06b_base.safetensors` and `vae/qwen_image_vae.safetensors`.
All three come from that repo's `split_files/`; `docs/models.md` has the exact
paths and hashes.

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

`--style cel-plain` is `cel` without the sticker border. Dropping those three
tags changes more than the outline: the cape spreads wider, the legwear gloss
comes up, and the result reads as an illustration rather than a die-cut
sticker.

1280x1920 costs roughly four minutes an image on an M1 Max. For iteration,
`--width 1024 --height 1536 --steps 22` is visually close and about four times
faster -- `dpmpp_2m` has converged well before 30 steps.

Every queued job now also submits a UI-format ("litegraph") copy of the graph
alongside the API graph, built from `/object_info` by `scripts/workflow_ui.py`.
That copy shows up under `extra_data.extra_pnginfo.workflow` in
`/history/<prompt_id>`, and ComfyUI writes it into the PNG as a `workflow`
text chunk, so dropping a generated image onto the ComfyUI canvas reopens the
graph that made it. `--export-workflow PATH` writes that same UI-format JSON
to a file for the first image in the run, without changing anything else
about the queue behaviour:

```bash
uv run scripts/queue_dq3.py --job sage --export-workflow workflows/templates/dq3sage.json
```

If `/object_info` cannot be reached, the script warns on stderr and queues
the image without a workflow attached rather than failing the run.

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

Place the repo under the serving machine's `models/diffusers/<name>/` keeping
its `unet/`, `vae/`, `text_encoder*/`, `tokenizer*/`, `scheduler/` and
`model_index.json`, then restart ComfyUI so the path is registered. Everything
else — presets, IPAdapter, masks — works unchanged.

The four that were in use are listed in `docs/models.md` with their John6666
repo names, so `--diffusers-path amanatsu-il-v11` and friends can be put back
without hunting for which upstream they came from.

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

Tracked workflow templates:

- `workflows/templates/minimal-txt2img-api.json` (API format)
- `workflows/templates/anima-txt2img-api.json` (API format)
- `workflows/templates/dq3sage.json` (UI format)

`minimal-txt2img-api.json` and `anima-txt2img-api.json` are in the API format
`/prompt` takes; they do not load as a graph in the ComfyUI web UI, only serve
as a reference for the shape those scripts POST. `dq3sage.json` is a UI
("litegraph") workflow instead -- drag it onto the ComfyUI canvas, or load it
through the Workflow menu, and edit the checkpoint, prompt text, or anything
else from there. It is regenerated with `--export-workflow`, documented above.

## Render On Another Machine

The GPU doing the work does not have to be this one. `COMFYUI_HOST` points
every queue script at a ComfyUI elsewhere on the network:

```bash
export COMFYUI_HOST=192.168.x.x   # COMFYUI_PORT too, if it is not 8188
uv run scripts/yukari_recipe.py --seed 555666777
uv run scripts/post_renders.py
```

Unset it and everything falls back to `127.0.0.1:8188`, which is what the
scripts did before this existed. `--host`/`--port` still win where a script
exposes them. The far end has to have been started with `--listen`, or it only
answers itself.

One assumption breaks, and it breaks everywhere: the scripts and ComfyUI stop
sharing a filesystem. `SaveImage` writes to the other machine's `output/`, and
`LoadImage` reads the other machine's `input/`.

`scripts/comfy_host.py` closes that at the two points where it matters.
`ensure_local()` pulls a render back through `/view` into `.local/ComfyUI/output`
before anything opens it, and `stage_input()` pushes an input through
`/upload/image` after making the usual local copy. Both do nothing when the
server is local -- they do not open a socket at all -- which is why the
post-processing scripts (`recolor_bg.py`, `legcrop.py`, `inpaint_composite.py`
and the rest) needed no changes. What reaches them is still a plain local path.
Uploads are capped at 100MB by the server.

### Getting models onto it

They have to be on that machine's disk, and nothing in the ComfyUI HTTP API can
put them there. `/experiment/models` is read-only, there is no download
endpoint, and no standard node fetches a URL. Short of ComfyUI-Manager, that
leaves running a command over there.

`docs/models.md` is the inventory to work from: every file that used to be
under `.local/assets`, with the Hugging Face repo or Civitai version it came
from and its SHA256. `scripts/fetch-models-windows.ps1` automates that pull,
but only for hassaku-il-v22 and two LoRAs — about 7GB of the 67GB — so anything
else still needs a command by hand.

For a checkpoint mirrored to Hugging Face in diffusers layout:

```powershell
# on the Windows machine, from the portable install root
.\python_embeded\python.exe -c "from huggingface_hub import snapshot_download; snapshot_download('John6666/hassaku-xl-illustrious-v22-sdxl', local_dir=r'.\ComfyUI\models\diffusers\hassaku-il-v22')"
```

The `hf` CLI is a trap on a portable install. It imports `venv` on startup,
which the embedded Python does not ship, so it dies before downloading
anything; `snapshot_download` never touches that import.

`DiffusersLoader` lists a directory the moment its `model_index.json` lands,
which is long before the 5GB `unet/` does. A model showing up in
`/object_info/DiffusersLoader` is therefore not a signal that it can be loaded.
Loading a half-fetched folder fails with `'NoneType' object has no attribute
'lower'`, which is ComfyUI reporting a missing file badly.

Custom nodes are per-machine as well, so a remote box without them cannot run
the IPAdapter (`--ref-image`) or ControlNet (`--trace-mode`) paths. txt2img and
img2img need nothing past the checkpoint.

Windows blocks ICMP by default, so `ping` fails against a machine that is up
and serving. Check the port, or ask `/system_stats`.

## Python Environment

`.venv` currently holds four packages — **pillow, numpy, opencv-python, scipy** —
which is everything the scripts here import. None of them imports torch; the
GPU stack belongs to whichever machine serves ComfyUI. That makes the
environment about 231MB.

It is still marked `[tool.uv] managed = false` with no dependencies declared in
`pyproject.toml`, because `./scripts/update-comfyui.sh` installs the upstream
checkout's `requirements.txt` straight into this same `.venv`, and uv would
treat those packages as extraneous and uninstall them. So `uv run` uses `.venv`
without syncing, and `uv sync` / `uv lock` refuse to run.

Rebuilding the client environment from scratch:

```bash
uv venv --python 3.12 .venv
VIRTUAL_ENV=.venv uv pip install pillow numpy opencv-python scipy
```

## Tracked Files You Should Edit

- `config/upstream.env`: choose the upstream ref to follow
- `config/launch.env`: default listen host, port, and extra launch flags. Its
  `COMFYUI_HOST` is where a local server *binds*, which is the opposite of the
  `COMFYUI_HOST` above; `run.sh` sources this file, so an exported value cannot
  leak in and send a local server off to bind an address it does not have
- `config/extra_model_paths.yaml.tmpl`: template for model search paths
- `manifests/custom-nodes.toml`: custom node repositories and pinned refs
- `workflows/`: your saved workflow JSON files

Generated rather than edited: `docs/models.md` and
`manifests/models-sha256.txt` record what the model set was on 2026-08-17.
Regenerate them from a live `.local/assets`, not by hand.

## Recommended Workflow

- Keep `COMFYUI_REF` on a validated release tag for normal use.
- Update `COMFYUI_REF` only when you decide to adopt a newer upstream release.
- A tag checkout leaves `.local/ComfyUI` in detached `HEAD`, which is expected for this repo.
- Keep models under `.local/assets` or another external directory rendered through `extra_model_paths.yaml`.
- Treat `.local/ComfyUI` as disposable runtime state. Rebuild it with the scripts rather than editing it manually.
- `.local/ComfyUI/output` is the exception: those are finished renders, and
  nothing regenerates them.
- Before deleting a model, check it is still fetchable rather than assuming.
  Hugging Face returns a file's SHA256 as `lfs.oid` from
  `/api/models/<repo>/tree/main/<dir>`, and Civitai resolves a file to its model
  and version through `/api/v1/model-versions/by-hash/<sha256>` without a token.
  That is how `docs/models.md` was built.
