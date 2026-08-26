# comfyui-recipes

A command-line front end for [ComfyUI](https://github.com/Comfy-Org/ComfyUI).
No web UI, no custom nodes of its own — just scripts that build a graph, POST it
to `/prompt`, and pull the result back.

Two things make it more than a thin API wrapper:

**The defaults are the recipe.** `scripts/queue_dq3.py --job sage` is a complete
command. Checkpoint, sampler, resolution, LoRA stack and the tag preset
blocks are already set to values that took batches of rendering to find, so the
bare command reproduces the look it was tuned to. Overriding any one of them is
a normal flag, and `--print-prompt` shows what a given combination would send
without queueing anything.

**The GPU does not have to be local.** One environment variable points every
script at a ComfyUI on another machine, and nothing else changes — including the
post-processing scripts, which still receive plain local paths.
`scripts/comfy_host.py` closes the filesystem gap through `/view` and
`/upload/image`.

```bash
export COMFYUI_HOST=192.168.x.x        # omit for a local ComfyUI
uv run scripts/queue_dq3.py --job sage --count 3
```

## Finding your way

There is no list of scripts here, and no table of contents for the notes. Both
are things that have to be maintained, and both are wrong the week after they
are written. The repository describes itself instead:

```bash
uv run scripts/atlas.py             # every script: its role, its size, its own first line
uv run scripts/atlas.py notes       # docs/render-notes.md by heading, with line numbers
```

`config/`, `docs/`, `manifests/`, `scripts/` and `workflows/` are tracked;
`.local/` is not, and is where a ComfyUI checkout, the models, the cached
`input/`/`output/` pair and a session's throwaway scripts live.
`scripts/archive/` is scripts that answered one question and were kept as a
record rather than as tools.

[`docs/`](docs/) holds the operating notes — queueing, remote and local install,
configuration, model provenance. [`docs/render-notes.md`](docs/render-notes.md)
is the measurements, per character, including the ones that turned out to be
wrong. It is the point of the repository; the scripts are how it was produced.

## What it runs on

Python 3.12 and [uv](https://github.com/astral-sh/uv), plus a ComfyUI reachable
over HTTP — on this machine or another one. The client environment is the
packages below; nothing here imports torch.

```bash
uv venv --python 3.12 .venv
VIRTUAL_ENV=.venv uv pip install pillow numpy opencv-python scipy
```

Models are not included and not downloaded automatically.
[`docs/models.md`](docs/models.md) lists the exact upstream and SHA256 of every
model these recipes were tuned against.

## Recording runs in chimera

`scripts/generate.py` runs a batch the same way the recipes do, but records it
in the [chimera](https://chimera.chanu.co) Management API on the way through:
Batch and Job registration, image ingest into R2, and a Discord notification
that carries the generation's canonical URL.

```bash
uv run scripts/generate.py --request request.json            # run and record
uv run scripts/generate.py --request request.json --dry-run  # show what would be sent
```

`request.json` follows the contract in the chimera repository's
`docs/generation-request.md` (`schema_version` 1). The parts this CLI reads:
`generation.recipe` must be `yukari` for now; `generation.parameters` carries
the builder arguments (`pose` required; `costume`, `hires`, `denoise`
optional); `generation.prompt` / `negative_prompt`, when set, replace the
built node text wholesale. For attribution, `parameters.character` takes a
character *name* and resolves it against the API (creating it if new), while
`parameters.character_id` passes a known UUID straight through.

Authentication is a Cloudflare Access service token, read from
`$CHIMERA_CF_CLIENT_ID` / `$CHIMERA_CF_CLIENT_SECRET`, then from the untracked
cache `.local/chimera-token`, and only failing both from the 1Password item
`chimera-claude-agent` — which prompts Touch ID, so a successful fetch writes
the cache (mode 0600) and later runs stay unattended. The values are
credentials: they never go into a tracked file.

A run writes `<request>.state.json` next to the request. That file is what
makes re-running the same command safe — it holds the idempotency keys, batch
and job ids, and the seeds, so a retry resumes from wherever the last run
stopped instead of creating duplicates.

## What this is, and what it is not

This is personal tooling, published because the measurements in
[`docs/render-notes.md`](docs/render-notes.md) are worth more written down than
kept — a record of what was tried, what worked, and the several occasions where
the first conclusion turned out to be wrong. The recipes are tuned to specific
Illustrious-family checkpoints and to one set of characters. Nothing here is
packaged, versioned, or supported, and it is not trying to be.

Read it as a notebook rather than as a tool you are meant to adopt.

## Derivative work

The recipes draw characters from existing works. That matters more than anything
about the code, so it belongs above the licence and not in a footnote.

| character | source work |
|---|---|
| sage, priest, mage | Dragon Quest III |
| Takao, Hamakaze | Kantai Collection |
| Momiji | Touhou Project |
| Yuzuki Yukari | VOICEROID / VOCALOID |

Every right in those characters and their source works belongs to the original
creators and their rights holders. Nothing here claims any part of it, and
nothing here could grant it.

Each work also sets its own terms for derivative work, and those terms are not
the same from one to the next — Touhou publishes a permissive guideline, others
do not. Anyone acting on what is written here answers to those terms. This
repository does not stand between them.

## No licence

No licence is granted for the writing in this repository — the scripts, the
notes, the tag strings and the measurements. It is published to be read, not
used: every right is reserved, so it may not be copied, modified, or
redistributed. GitHub's terms of service still allow viewing and forking it
here, and that is the extent of it.

That is a deliberate choice rather than a missing file. If something in here is
useful to you, the ideas and the measurements are yours to take — take those and
write your own.

To be plain about the boundary: this covers only what was written here. It says
nothing about the characters above, which were never this repository's to
license either way.
