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

The default upstream pin is `v0.16.4`. The local checkout will stay on that release tag until you change `config/upstream.env`.

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
