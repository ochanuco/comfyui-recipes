# Rendering on another machine

The GPU doing the work does not have to be the one you are typing on.
`COMFYUI_HOST` points every queue script at a ComfyUI elsewhere on the network:

```bash
export COMFYUI_HOST=192.168.x.x   # COMFYUI_PORT too, if it is not 8188
uv run comfy-recipes generate --request request.json
```

Unset it and everything falls back to `127.0.0.1:8188`, which is what the
scripts did before this existed. `--host`/`--port` still win where a script
exposes them. The far end has to have been started with `--listen`, or it only
answers itself.

## The one assumption that breaks

The scripts and ComfyUI stop sharing a filesystem. `SaveImage` writes to the
other machine's `output/`, and `LoadImage` reads the other machine's `input/`.

`scripts/comfy_host.py` closes that at the two points where it matters.
`ensure_local()` pulls a render back through `/view` into the local
`.local/ComfyUI/output` before anything opens it, and `stage_input()` pushes an
input through `/upload/image` after making the usual local copy. Both do nothing
when the server is local — they do not open a socket at all — which is why the
post-processing scripts (`recolor_bg.py`, `analysis/legcrop.py`, `analysis/inpaint_composite.py`
and the rest) needed no changes. What reaches them is still a plain local path.

Uploads are capped at 100MB by the server.

Custom nodes are per-machine as well, so a remote box without them cannot run
the IPAdapter (`--ref-image`) or ControlNet (`--trace-mode`) paths. txt2img and
img2img need nothing past the checkpoint.

## Getting models onto it

They have to be on that machine's disk, and nothing in the ComfyUI HTTP API can
put them there. `/experiment/models` is read-only, there is no download
endpoint, and no standard node fetches a URL. Short of ComfyUI-Manager, that
leaves running a command over there.

[models.md](models.md) is the inventory to work from: every model these recipes
were tuned against, with the Hugging Face repo or Civitai version it came from
and its SHA256. `scripts/fetch-models-windows.ps1` automates that pull for a
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
