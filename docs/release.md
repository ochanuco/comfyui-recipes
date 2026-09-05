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
