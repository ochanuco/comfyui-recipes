# Configuration

## Files meant to be edited

- `config/upstream.env` — the upstream ComfyUI ref to follow. Keep it on a
  validated release tag for normal use, and move it only when you decide to
  adopt a newer upstream release.
- `config/launch.env` — default listen host, port and extra launch flags for a
  local server.
- `config/extra_model_paths.yaml.tmpl` — template for model search paths,
  rendered by `scripts/render-extra-model-paths.py`.
- `manifests/custom-nodes.toml` — custom node repositories and pinned refs.
- `workflows/` — saved workflow JSON.

### The two meanings of `COMFYUI_HOST`

They are opposites, and mixing them up sends a local server off to bind an
address it does not have.

| | |
|---|---|
| the environment variable | where a **client** connects — the machine running ComfyUI |
| `COMFYUI_HOST` in `config/launch.env` | where a **local server** binds |

`run.sh` sources `launch.env` rather than reading the environment, so an
exported value cannot leak into the bind address.

## Files that are generated

`docs/models.md` and `manifests/models-sha256.txt` record what the model set was
on 2026-08-17 — every file, its upstream, and its SHA256. Regenerate them from a
live model root rather than editing them by hand.

## Before deleting a model

Check it is still fetchable rather than assuming. Neither of these requires a
token or a download:

- Hugging Face returns a file's SHA256 as `lfs.oid` from
  `/api/models/<repo>/tree/main/<dir>`, so a local copy can be proven identical
  to the remote one without transferring it.
- Civitai resolves a file straight to its model and version through
  `/api/v1/model-versions/by-hash/<sha256>`.

That is how `docs/models.md` was built, and it is the check worth repeating
before anything gets removed.
