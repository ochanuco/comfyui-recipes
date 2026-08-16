# Running ComfyUI on this machine

None of this is needed to drive a ComfyUI that already runs somewhere else — see
[remote.md](remote.md) for that. This is what to run if the machine holding these
scripts should also serve ComfyUI.

The repository manages that install without vendoring it: the upstream checkout
lands in `.local/`, which is not tracked.

## Bootstrap

```bash
./scripts/bootstrap-comfyui.sh
```

Python 3.12 is required. The script will:

1. clone ComfyUI into `.local/ComfyUI`
2. create or reuse `.venv`
3. install upstream Python requirements
4. render `.local/ComfyUI/extra_model_paths.yaml`
5. sync custom nodes listed in `manifests/custom-nodes.toml`

Step 3 installs the upstream `requirements.txt` into the same `.venv` the client
scripts use, which pulls torch in and takes it from roughly 231MB to 1.9GB.
Models are not fetched; [models.md](models.md) is the list.

## Day to day

```bash
./scripts/update-comfyui.sh
./scripts/run.sh
./scripts/install-custom-nodes.sh
```

The upstream pin lives in `config/upstream.env` and the checkout stays on that
release tag until you change it. A tag checkout leaves `.local/ComfyUI` in
detached `HEAD`, which is expected.

Treat `.local/ComfyUI` as disposable runtime state and rebuild it with the
scripts rather than editing it by hand — with one exception:
`.local/ComfyUI/output` holds finished renders, and nothing regenerates those.

## Custom nodes on macOS

`install-custom-nodes.sh` does not install requirements for
`comfyui_controlnet_aux`: its `requirements.txt` pins `onnxruntime-gpu`, which
publishes no macOS wheel, and the script runs under `set -e`. Install what
DWPose needs by hand instead —

```bash
./.venv/bin/python -m pip install opencv-python scikit-image matplotlib onnxruntime
```

Plain `onnxruntime` carries `CoreMLExecutionProvider` on Apple silicon. The other
preprocessors in that repo want `mediapipe`, `fvcore` and friends; without them
those node modules fail their import and drop out with a warning, which is the
intended behaviour and leaves DWPose working.

Restart ComfyUI after installing a custom node — the node list is built at
startup, and `/object_info/<name>` returns `200` with an empty body for a node
that is not registered, so it is not a usable readiness check on its own.

## The Python environment

`.venv` serves two purposes, which is why `pyproject.toml` declares no
dependencies and sets `[tool.uv] managed = false`.

For driving a remote ComfyUI it needs four packages — **pillow, numpy,
opencv-python, scipy** — which is everything the scripts here import. None of
them imports torch; the GPU stack belongs to whichever machine serves ComfyUI.

```bash
uv venv --python 3.12 .venv
VIRTUAL_ENV=.venv uv pip install pillow numpy opencv-python scipy
```

`update-comfyui.sh` then installs the upstream checkout's `requirements.txt`
into that same environment. uv would treat those packages as extraneous and
uninstall them, hence `managed = false`: `uv run` uses `.venv` without syncing,
and `uv sync` / `uv lock` refuse to run. Change what ComfyUI itself needs
through `config/upstream.env` and the update script, not by editing
`pyproject.toml`.
