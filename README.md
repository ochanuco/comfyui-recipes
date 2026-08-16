# comfyui-recipes

A command-line front end for [ComfyUI](https://github.com/Comfy-Org/ComfyUI).
No web UI, no custom nodes of its own — just scripts that build a graph, POST it
to `/prompt`, and pull the result back.

Two things make it more than a thin API wrapper:

**The defaults are the recipe.** `scripts/queue_dq3.py --job sage` is a complete
command. Checkpoint, sampler, resolution, LoRA stack, and eleven blocks of tag
presets are already set to values that took batches of rendering to find, so the
bare command reproduces the look it was tuned to. Overriding any one of them is
a normal flag.

**The GPU does not have to be local.** One environment variable points every
script at a ComfyUI on another machine, and nothing else changes — including the
post-processing scripts, which still receive plain local paths.
`scripts/comfy_host.py` closes the filesystem gap through `/view` and
`/upload/image`.

```bash
export COMFYUI_HOST=192.168.x.x        # omit for a local ComfyUI
uv run scripts/queue_dq3.py --job sage --count 3
```

## What is here

| | |
|---|---|
| `scripts/queue_*.py` | build and queue a graph — txt2img, img2img, Anima, the DQ3 portrait recipe, refinement passes |
| `scripts/yk_*.py`, `scripts/style_sweep*.py` | narrower sweeps over one variable at a time |
| `scripts/comfy_host.py` | the local/remote seam every other script imports |
| `scripts/workflow_ui.py` | rebuilds a UI-format ("litegraph") graph from `/object_info`, so a generated PNG reopens on the ComfyUI canvas |
| `scripts/gen_variants.py` | asks a local ollama model for scene tags and queues one image per variant |
| post-processing | `recolor_bg.py`, `legcrop.py`, `inpaint_composite.py`, `contact_sheet.py` and friends — plain PIL/numpy, no ComfyUI involved |
| `scripts/*.sh` | install, update and launch a ComfyUI on this machine, if you want one here |

## What it runs on

Python 3.12 and [uv](https://github.com/astral-sh/uv), plus a ComfyUI reachable
over HTTP — on this machine or another one. The client environment is four
packages (pillow, numpy, opencv-python, scipy); nothing here imports torch.

```bash
uv venv --python 3.12 .venv
VIRTUAL_ENV=.venv uv pip install pillow numpy opencv-python scipy
```

Models are not included and not downloaded automatically.
[`docs/models.md`](docs/models.md) lists the exact upstream and SHA256 of every
model these recipes were tuned against.

## Documentation

| | |
|---|---|
| [`docs/queueing.md`](docs/queueing.md) | every kind of job these scripts queue, and what the presets encode |
| [`docs/remote.md`](docs/remote.md) | driving a ComfyUI on another machine, and getting models onto it |
| [`docs/local-install.md`](docs/local-install.md) | running ComfyUI on this machine instead |
| [`docs/configuration.md`](docs/configuration.md) | what is in `config/`, and which files are meant to be edited |
| [`docs/models.md`](docs/models.md) | where every model came from, with hashes |
| [`docs/render-notes.md`](docs/render-notes.md) | 3000 lines of measurements, per character — including the ones that were wrong |

## Layout

- `config/` — tracked runtime configuration
- `docs/` — operating notes and measurements
- `manifests/` — custom-node inventory and model hashes
- `scripts/` — everything above
- `workflows/` — tracked workflow JSON, API and UI format
- `.local/` — untracked: a ComfyUI checkout if one exists here, models, and
  the `output/`/`input/` pair `comfy_host.py` caches through

## What this is, and what it is not

This is personal tooling, published because the measurements in
[`docs/render-notes.md`](docs/render-notes.md) are worth more written down than
kept — a record of what was tried, what worked, and the several occasions where
the first conclusion turned out to be wrong. The recipes are tuned to specific
Illustrious-family checkpoints and to one set of characters. Nothing here is
packaged, versioned, or supported, and it is not trying to be.

Read it as a notebook rather than as a tool you are meant to adopt.

## No licence

No licence is granted. This repository is published to be read, not used:
every right is reserved, so it may not be copied, modified, or redistributed.
GitHub's terms of service still allow viewing and forking it here, and that is
the extent of it.

That is a deliberate choice rather than a missing file. If something in here is
useful to you, the ideas and the measurements are yours to take — take those and
write your own.
