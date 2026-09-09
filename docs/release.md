# Release path

`main` is where PRs land; `production` is what the GPU worker runs. The two
are joined by a promotion PR, the same shape as ochanuco/webull-trading.

## Branches and rulesets

- `main`: deletion and force-push blocked, PR required (no approval), merge
  commits only.
- `production`: PR required with one approval from a code owner and every
  thread resolved, the `production deploy preflight` check required, admins
  may bypass. Nothing pushes to it except the promotion PR's merge.

## Workflows

- `production release PR` runs on every push to `main`. It snapshots
  `main`'s tree onto `release/production` (a `read-tree`, not a merge) and
  opens or updates the PR into `production`. Merging that PR is the release.
  It authenticates as a GitHub App (secrets `APP_ID`, `APP_PRIVATE_KEY`) so
  the PR is not self-authored and its checks run.
- `production preflight` is the required check on that PR: tests with
  `PYTHONPATH=scripts`, then `scripts/costume_check.py`.
- `deploy worker` runs on `push` to `production` only, on the self-hosted
  runner labelled `gpu-box`. It calls `scripts/worker/deploy.ps1` in the
  standing checkout named by the repository variable `WORKER_CHECKOUT`,
  which moves it to `origin/production`, refreshes the venv and re-registers
  the `work` task. The repository is public; limiting the runner to
  `production` pushes is what keeps fork PRs off the box.
  `deploy.ps1` also re-junctions `comfy_nodes/yukari_finalize/` into the
  ComfyUI install named by the repository variable `COMFYUI_ROOT`, brings
  the third-party node packs under its `custom_nodes/` to the commits pinned
  in `manifests/worker-nodes.toml` (`scripts/worker/sync-nodes.ps1`: clone,
  detached checkout, `requirements.txt` into the portable Python when an
  entry moved), and restarts ComfyUI (`scripts/worker/restart-comfyui.ps1`)
  only when the deploy changed our node pack, the imaging code under it, or
  a pinned node -- ComfyUI reads `custom_nodes` once, at startup.
- `restart worker comfyui` is a manual `workflow_dispatch` that runs the same
  restart on the box, for changes made outside a deploy.

## Draining before a deploy

`deploy.ps1` asks the worker to stop before it moves the checkout: it writes
`.local/_nogit/worker/drain` in the checkout and waits. The worker stops
claiming, finishes the request it is running, and deletes the file on its way
out, so the wait ends on the worker's own word rather than on a clock. Only
then does the checkout move; the `taskkill` that follows is for a worker
already gone or wedged. A drain that times out deletes the file itself -- one
left behind would drain the next worker the moment it started.

The bound is `-DrainSeconds`, 300 by default. What it has to cover is one
request, not the queue: the worker claims nothing new once the file appears.
A sketch seed takes about 45 seconds, a finalize about 90, a four-seed batch a
few minutes. The ceiling above it is the deploy job's own `timeout-minutes:
15`, which also has to hold `git fetch` and the `uv pip install`.

Today a killed worker was not losing renders -- ComfyUI is a separate process
that survives the deploy, and a re-claimed request rejoins the running job
through the `comfy_prompt_id` in its state file. What it lost was the wait.
Draining matters for its own sake once the worker runs inside ComfyUI, because
then the restart takes the render with it.

## The box

`scripts/worker/register-runner.ps1 -Token <registration token> -Version <x.y.z>`
downloads the runner, registers it against this repository with the label
`gpu-box`, and installs `run.cmd` as the per-user logon task `actions-runner`
next to `comfyui` and `comfyui-recipes-watch`. The registration token comes
from `gh api -X POST repos/ochanuco/comfyui-recipes/actions/runners/registration-token`
and is valid for an hour.

Rows in chimera's requests queue default to `recipe_ref = production`; the
worker serves only the branch it is checked out on, so the box stays on
`production` between releases.
