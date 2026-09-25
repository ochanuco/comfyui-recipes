# The GPU box

ComfyUI and the worker run on the Windows GPU box; the Mac only edits recipes
and reads chimera. The box's address and ssh alias are in the untracked
`CLAUDE.local.md`. Deploys and restarts are in [release.md](release.md).

## Setting it up

```powershell
git clone https://github.com/ochanuco/comfyui-recipes.git
uv venv --python <uv-managed 3.12 python.exe> .venv
uv pip install --python .venv\Scripts\python.exe -e . pillow numpy opencv-python scipy websockets pytest
$env:PYTHONPATH = "scripts"; .\.venv\Scripts\pytest.exe -q
powershell -ExecutionPolicy Bypass -File .\scripts\worker\register-nodes.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\worker\register-comfyui.ps1 -PortableRoot <dir>
```

`register-nodes.ps1` junctions `comfy_nodes/yukari_finalize` and
`comfy_nodes/yukari_worker` into ComfyUI's `custom_nodes/`.
`register-comfyui.ps1` registers the portable ComfyUI as the logon task
`comfyui` with the launch arguments the script holds and
`COMFYUI_RECIPES_WORKER=1`, so the worker runs as a thread inside ComfyUI
and a reboot brings both back once the user logs on. Changing an argument
means editing the script and re-running it; `run_nvidia_gpu.bat` is not
used. `register-watch.ps1` / `watch.ps1` still register a standalone
`comfy-recipes work` loop for running it by hand; the deploy does not use
them. `.local/chimera-token` and `.local/discord-webhook` are copied onto
the box by hand; they are never tracked. The box must stay on a checkout
whose branch matches the `recipe_ref` of the rows it should serve (see
[queueing.md](queueing.md#worker)).

Two things that only show up over `ssh comfyui-worker`:

- Reparse points do not resolve in that session. The WinGet `uv.exe` link
  fails with "no application is associated", and uv's
  `cpython-3.12-windows-x86_64-none` alias is a junction that fails with
  "untrusted mount point". Call the package's own `uv.exe` and point
  `uv venv` at the versioned `cpython-3.12.<patch>-...` directory instead.
- The locale encoding is cp932. Text I/O in this repo passes
  `encoding="utf-8"` explicitly, and the wrapper sets `PYTHONUTF8=1` for
  the CLI's stdout.

## Getting models onto it

They have to be on that machine's disk, and nothing in the ComfyUI HTTP API can
put them there. `/experiment/models` is read-only, there is no download
endpoint, and no standard node fetches a URL. Short of ComfyUI-Manager, that
leaves running a command over there.

[models.md](models.md) is the inventory to work from, with the Hugging Face
repo or Civitai version each model came from and its SHA256. `scripts/fetch-models-windows.ps1` automates that pull for a
Windows portable install, but only for hassaku-il-v22 and two LoRAs, so anything
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

### A download must outlive the ssh session

A process started over `ssh comfyui-worker` — `Start-Process` included — dies
the moment the session closes, and a `hf_hub_download` or `curl` that was
half-way through a 6GB file just stops without an error (measured three
times: 20s, 45s and 60s of session gave 1GB, 2.7GB and 4.7GB). Register the
fetch as a scheduled task and run it from there instead:

```powershell
schtasks /Create /TN fetch_ckpts /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\...\fetch_ckpts.ps1" /SC ONCE /ST 00:00 /F
schtasks /Run /TN fetch_ckpts
```

The script itself is a `curl.exe -L -C - --retry 5 --retry-all-errors` loop
per file into `<name>.part`, renamed on exit 0; `.local/ab2/fetch_ckpts.ps1`
is the one that fetched the 2026-09-05 checkpoints. Civitai's
`/api/download/models/<version>` worked anonymously for the Nova models; a
`CIVITAI_TOKEN` is only needed for gated ones. Watch the `.part` size from
here, not the log line — the log only moves when a file finishes.

## Checking whether the far end is up

Windows blocks ICMP by default, so `ping` fails against a machine that is up and
serving. Check the port, or ask `/system_stats`:

```bash
curl -s http://$COMFYUI_HOST:8188/system_stats
```

`/object_info` is also the honest answer to "does it have the models" — an empty
`CheckpointLoaderSimple` list means an empty `models/checkpoints`, whatever the
disk looks like from over here.
