# Queueing

> Yuzuki Yukari belongs to her original creators and rights holders — see
> [Derivative work](../README.md#derivative-work) in the README.

Every render is a row on chimera's `requests` queue, posted through the MCP
(`derive_request`, `finalize_generation`, `repair_generation`,
`masked_redraw_generation`, `create_request`) or `POST /api/v1/requests`.
`comfy-recipes work` on the GPU box claims a row, runs it, and ingests the
result back into chimera. Nothing else submits to ComfyUI.

## Where the details are

This page only covers rules that cannot be read from one place in the code.
Options, defaults and ranges live here:

| Question | Source |
|---|---|
| The wire contract (claim, heartbeat, done/failed) | chimera `docs/worker-protocol.md` |
| Every option of a kind, its default and range | `uv run comfy-recipes <generate\|work\|finalize\|repair\|masked_redraw> --help`, `application/request_options.py` |
| Poses, costumes, parts, patch targets, dials, finalize defaults | `list_catalog` / `get_catalog_pose` on the MCP, or `uv run comfy-recipes catalog` |
| Patch targets and their ops | `domain/generation/patches.py` |
| What a request would render, without rendering | `uv run comfy-recipes generate --request r.json --dry-run` |

## Kinds

| Kind | Payload | Does |
|---|---|---|
| `generate` | a request.json body | render the recipe with its parameters and patches |
| `finalize` | `{generation_id, options}` | deliver a pick: matte, repin, backdrop, stroke; redraw only on request |
| `repair` | `{generation_id, options}` | DWPose-masked crop-and-stitch reroll of hands/feet |
| `masked_redraw` | `{generation_id, options}` | the same reroll on caller rectangles with a free-text prompt patch |

## Rules the code spreads across files

### Worker

- A row's `recipe_ref` must equal the worker's git branch, or the row fails.
- Idempotency keys come from the request id (`request:{id}`,
  `…:job:{i}`, `…:gen:{j}`, `…:asset:{role}`), so a re-claimed row resumes
  its own records. A ComfyUI prompt id the server forgot is resubmitted.
- The WorkerHub websocket claims rows as they are posted and relays
  progress. Polling at `--interval` always runs underneath it.
- The worker publishes its catalog at startup (best-effort). The catalog
  describes the worker's checkout, not your branch.

### Finalize options

- An absent `backdrop`, `stroke_light`, `repin` or `deliver_only` takes the
  recipe's `finalize.defaults`, the same values the WebUI sends. An explicit
  `null` keeps its own meaning: no backdrop, or a uniform rim.
- `deliver_only` defaults to false when the request names a redraw-shaping
  option (`denoise`, `size`, `route`, `finalizer`, `keep_regions`,
  `upscale`); combining it with one explicitly is an error. `repair` and
  `repair_regions` are not redraw-shaping.
- `deliver_only` + `repair` runs `repair_seeds` reroll seeds through the
  delivery tail in one submission and records one `kind: "repair"` batch.
- Dial words (`"keep"`, `"on"`, …) are accepted wherever a number is. The
  row's result carries `resolved_options` with what actually ran.

### Repair and masked redraw

- Pointed at a finalize batch, repair redraws the largest sibling (the raw
  redraw), not the delivered sticker.
- Finalizing a repair or masked_redraw output reads recipe, prompts, seed and
  loaders from `parameters.base_generation`. The repaired pixels are what
  gets redrawn.
- The repair prompt drops face, hair and framing tags. Part LoRAs
  (`lora`, `repair_lora`) are skipped on an Anima source.

### Generate requests

- `generation.parameters` is a closed set. Annotations go in
  `semantic.attributes`, and diffs go in `generation.patches`.
  `semantic.summary` is required.
- Patches apply in order after the recipe compiles, and each needs a
  `reason`. A `replace`/`remove` whose `old` is absent fails; it never
  silently skips.
- `prompt.positive.<part>` edits one component. A legacy group name
  resolves to the single member containing `old`.
- Patches are exclusive with `generation.graph` and with a full
  `prompt`/`negative_prompt`. `generation.graph` is the escape hatch for a
  graph the recipe cannot build. In graph mode, `parameters` only records
  what the graph really contains.
- After all edits, every identity tag of the unpatched prompt must still be
  in the positive, compared bare. Otherwise the request fails, unless
  `generation.identity_override` gives a reason, which is recorded on the
  generation and the batch.
- `experiment.overrides.patches` (from a chimera ExperimentRun) uses the
  same vocabulary and is exclusive with `generation.patches`.
