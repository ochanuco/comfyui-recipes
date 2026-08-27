# comfyui-recipes — session brief

Read this before the first tool call. It is the stuff that is not in the code
and costs a session an hour to rediscover.

## What you are working on

A command-line front end for ComfyUI: scripts build a graph, POST it to
`/prompt`, and pull the result back. There is no web UI here and no custom node
of its own. **The defaults are the recipe** — a bare `--job` or `--pose` is a
complete command, and every preset in it was arrived at by rendering.

Two recipes are live, and they do not share code beyond `comfy_host.py`:

- `scripts/yukari_recipe.py` — Yukari. Shared costume blocks plus a pose table;
  this is where the current work happens.
- `scripts/queue_dq3.py` — the DQ3 / KanColle / Touhou jobs, `--job` per
  character.

Everything measured goes in `docs/render-notes.md`, including the measurements
that came back null and the conclusions that were later wrong. That file is the
point of the repository; the scripts are how it was produced.

Run everything through `uv run` — the client env is pillow, numpy,
opencv-python and scipy, and nothing here imports torch.

## Branch strategy: `main` only

**Work on `main`. Commit to `main`. Do not open a task branch for this repo.**

This is a deliberate, standing override of the global "never commit to a
protected branch" rule — the user has asked for it repeatedly and by name
(「mainのみで作業してください」). Nothing here is shared, reviewed or deployed;
a branch only splits the record of what was rendered from the renders.

If you find yourself on another branch, someone else's session put you there.
Finish on the branch you are on rather than switching under them, then
fast-forward `main` onto it with `git branch -f main HEAD` — that leaves the
working tree and their `HEAD` untouched.

## Look things up; do not read them

Three files are more than half this repository — `docs/render-notes.md` (~68k
tokens), `scripts/queue_dq3.py` (~21k) and `scripts/yukari_recipe.py` (~19k) —
and all three are exactly what a one-line question tempts you to open whole.
Opening any of them without a line range is a mistake, not a thorough approach.

```bash
uv run scripts/atlas.py                    # every script: role, size, one line  (~1.5k)
uv run scripts/atlas.py notes              # the notes' headings + line numbers   (~2.8k)
uv run scripts/atlas.py notes <pattern>    # just the sections that match
uv run scripts/atlas.py find <regex>       # matching lines, each under its heading
```

`atlas.py` reads the tree every time it runs, so unlike a committed index it
cannot be stale. Use it first; then `Read` with `offset`/`limit` on the lines it
gave you.

For what a recipe actually sends, ask the recipe instead of reading it:

```bash
uv run scripts/yukari_recipe.py --pose prone --print-prompt      # ~0.6k, not 19k
uv run scripts/queue_dq3.py --job sage --print-prompt            # ~0.9k, not 21k
uv run scripts/costume_check.py                                  # the blocks, verified
```

Rough shape of what that saves: the notes' table of contents plus one section is
about 3.5k tokens against 68k for the file, and a printed prompt is about 900
against 21k. If you find yourself about to read a file over ~5k tokens to answer
something narrow, there is probably a command for it — and if there is not,
adding one to `atlas.py` is cheaper than the read you were about to do.

`scripts/archive/` is fourteen scripts that ran once and are kept as a record.
Nothing imports them and nothing maintains them; do not read them looking for
how something works today.

## Where the GPU is

**ComfyUI does not run on this Mac.** It runs on another machine, and every
script reads the address from `scripts/comfy_host.py`, which defaults to
`127.0.0.1` — so `COMFYUI_HOST` has to be exported or nothing will connect:

```bash
export COMFYUI_HOST=...                # port 8188 is the default
```

The address, the ssh alias for a shell on that box, and the checkpoint in use
are in `CLAUDE.local.md`, which is not tracked. Read it; do not copy what it
says into anything this repo commits.

`comfy_host.py` is also the filesystem seam: the worker's disk is not this one,
so outputs come back over `/view` and inputs go up through `/upload/image`. A
script that opens a local path for a render the worker just made is a bug.

HTTP surface: `/prompt`, `/history/<prompt_id>`, `/queue`, `/view`,
`/object_info`, `/upload/image`, `/system_stats`.

ComfyUI writes the graph into each output PNG's metadata (`im.info['prompt']`)
but **not** the prompt_id. When the user names a render by prompt_id, get the
prompt from `/history/<id>` while the worker still has it.

## Renders reach the user through chimera; Discord is a side channel

The user reviews renders on chimera (https://chimera.chanu.co), not Discord.
A render that reached Discord but not chimera **is not delivered** — never
close out a prompt on the strength of a Discord post alone. Every render,
including one-off probes and chained passes from `.local/` scripts, gets a
chimera record (see the invariants below; `.local/_hige_ingest.py` is the
template for after-the-fact ingest of renders that bypassed `generate.py`).

`scripts/post_renders.py --interval 20` still posts finished renders to a
Discord webhook as a low-latency notification. Keep it running
(`pgrep -f post_renders`), but treat it as a courtesy ping, not delivery.

The webhook is a credential and lives in `.local/discord-webhook` or
`$DISCORD_WEBHOOK`. Never put it in a tracked file.

## chimera 連携の不変条件

- 生成の記録は chimera Management API（https://chimera.chanu.co）。CLI は
  `scripts/generate.py` で、実行と記録のみを担う — semantic 判断（prompt
  組み立て、reference の意味付け、検品）は Claude Code 側の仕事。
- chimera への記録は生成の完了条件。画像だけでなく semantics（各 arm の狙い、
  base からの差分、何を検証する render か）も ingest 直後に書く — 選抜が済んで
  から書くのでは遅い。作業途中の評価はユーザーが chimera の semantics を見て
  行う。semantics/tag は AI が書いてよい（rating だけが人間専用）。
- semantics の実装: request JSON の `semantic` ブロック（`summary` 必須）が
  ingest 直後に各 generation へ自動 PUT される（`generate.py` が強制）。
  事後の追記・上書きは `generate.py --semantic <generation_id> <file.json>`、
  tag は `--tag <generation_id> <name>`。API は
  `PUT /api/v1/generations/{id}/semantic`（schema_version:1、部分ペイロード可、
  再 PUT で全置換）。`generated_by` は CLI が補完する。generation_id には
  short_id も使える。`generate.py` を通らなかった render の一括 backfill は
  `.local/_semantic_backfill.py` が雛形（batch GET が generations を内包）。
- idempotency key は CLI が uuid4 で生成し `<request>.state.json` に保持。
  再送は必ず同じ key で行う。失敗後の再実行は同一 batch/job を再利用して
  ingest から再開する — state ファイルを消すと重複レコードができる。
- chimera への全リクエストに User-Agent の明示が必須（urllib のデフォルトは
  Cloudflare が 403/1010 で弾く）。
- rating（bad/neutral/good）を書くのは人間だけ。Claude は人間の rating と
  semantic を API で読んで改善を進める。AI が画像を開く検品は、rating と
  semantic だけでは判断できない場合の最終手段（トークン消費が理由）。
- Service Token は 1Password `chimera-claude-agent`。取得後は untracked の
  `.local/chimera-token`（0600）にキャッシュされ、以後 Touch ID なしで動く。
  値をトラックされるファイルに書かない。

## The costume is a contract, not a preference

`scripts/yukari_recipe.py` holds shared blocks — `CHARACTER`, `LEGWEAR`, `BODY`,
`FACE`, `SURFACE` — that **every pose wears at once**. Editing one changes every
render this repo has ever approved, which is why `scripts/costume_check.py`
hashes them and fails on any change it was not told about:

```bash
uv run scripts/costume_check.py            # fingerprint + per-pose declarations
uv run scripts/costume_check.py --accept   # the new hash, for a change that is meant
```

When it fails, nothing is broken — something was changed. Paste the new
fingerprint, and write in `docs/render-notes.md` what the costume is now.

Two rules that follow from this, both learned the expensive way:

- **A settled design decision that lives only in prose is a decision the next
  session does not get.** The one-garment leg was agreed, written into the notes
  and into memory, and applied by throwaway scripts in `.local/` — while
  `yukari_recipe.LEGWEAR` still built the retired two-layer costume, so another
  session got tights under knee-highs straight out of the recipe. If a change is
  settled, put it in the blocks.
- **Splices are string replacements and fail silently.** A per-pose
  `legwear.replace("(old tag:1.55)", ...)` against a block that no longer
  contains that tag does nothing at all and reports nothing. After touching a
  shared block, check the poses that splice it.

## Working files

`.local/` is untracked (`.gitignore`) and is where one-off probe scripts,
sweeps and logs go — `uv run .local/foo.py`. It is not the repo: anything worth
keeping moves into `scripts/` or `docs/render-notes.md`.

`docs/render-notes.md` is the record of what was measured, including what was
measured and came back *null*. Append to it; do not tidy it. Findings that
contradict an earlier entry get a correction written next to them, not a
deletion — several entries exist only to stop something being retried.

## No crops while the prompt is being tuned

**Do not crop, cut out or repair a render to deliver it.** If a picture needs a
crop to be acceptable, the prompt has not solved the problem, and the next arm
gets judged against an image the recipe cannot produce.

This was learned on `stand`: a two-figure render had a good left half, and
cutting it would have shipped a pose that never draws one figure. What actually
fixed it was the canvas -- 768 wide leaves no room beside her -- and that was
only reached because the crop was off the table.

Post-processing that sets a value the prompt cannot hold is a different thing
and is still fine: `recolor_bg.py` exists because the backdrop is unstable under
any perturbation. Removing part of the picture is not that.

## Reading images

Rendered images are expensive in context. **Do not open renders to browse them.**
Queue, let Discord post, and let the user pick — they name the prompt_id or the
filename of the one they want, and that is when you look. Measure with numpy
instead where a number will do, and keep in mind that four of this repo's
image statistics have already disagreed with the user's eye and lost.
