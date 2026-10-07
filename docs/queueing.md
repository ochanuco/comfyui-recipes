# Queueing

> Yuzuki Yukari belongs to her original creators and rights holders — see
> [Derivative work](../README.md#derivative-work) in the README.

Every render is a row on chimera's `requests` queue, posted through the MCP
(`derive_request`, `redraw_generation`, `deliver_generation`,
`repair_generation`, `masked_redraw_generation`, `create_request`) or `POST /api/v1/requests`.
`comfy-recipes work` on the GPU box claims a row, runs it, and ingests the
result back into chimera. Nothing else submits to ComfyUI.

## Where the details are

This page only covers rules that cannot be read from one place in the code.
Options, defaults and ranges live here:

| Question | Source |
|---|---|
| The wire contract (claim, heartbeat, done/failed) | chimera `docs/worker-protocol.md` |
| Every option of a kind, its default and range | `uv run comfy-recipes <generate\|work\|redraw\|deliver\|repair\|masked_redraw> --help`, `application/request_options.py` |
| Poses, costumes, parts, patch targets, dials, redraw and deliver defaults | `list_catalog` / `get_catalog_pose` on the MCP, or `uv run comfy-recipes catalog` |
| Patch targets and their ops | `domain/generation/patches.py` |
| What a request would render, without rendering | `uv run comfy-recipes generate --request r.json --dry-run` |

## Kinds

| Kind | Payload | Does |
|---|---|---|
| `generate` | a request.json body | render the recipe with its parameters and patches |
| `redraw` | `{generation_id, options}` | one pixel-changing `method` (`canvas`, `hires` or `light`) on a picture Generation; uploads one green-background picture |
| `repair` | `{generation_id, options}` | DWPose-masked crop-and-stitch reroll of hands/feet; uploads one picture per seed |
| `masked_redraw` | `{generation_id, options}` | the same reroll on caller rectangles with a free-text prompt patch |
| `deliver` | `{generation_id, options}` | cut and decorate a picture Generation: repin, backdrop, stroke; never redraws |

A `finalize` row is refused. `redraw`, `repair` and `masked_redraw` leave a
picture on the green key; only `deliver` makes the delivered picture.

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

### Redraw options

- `options` is required and names a `method`; any key the method does not
  take is an error. One request changes the picture once and uploads one
  picture Generation (green background, no delivery, no `mask` asset) that
  refines the source, saved under `rdw-<generation id>`. The request's
  `parameters` are `kind: "redraw"`, `method`, `base_generation` and the
  resolved options; `seed` is the sampler seed that ran.
- `canvas` takes `denoise`, `size`, `route`, `finalizer`, `upscale`,
  `keep_regions` and `keep_strength`, with the defaults the catalog publishes
  as `redraw.defaults.canvas`.
  `denoise` accepts the `redraw` dial words. It re-samples the source on a
  bigger canvas and only redraws an Anima source.
- `hires` takes `hires` (the long side in px of the area a 1024x1640 canvas
  has) and `denoise` (0 < d <= 1, default 0.45). It re-samples the stored
  graph of the Anima generate output, so a `repair`, `masked_redraw` or
  `redraw` output and a stitched base are refused.
- `light` takes `scene` (`sunset` or `moon`) and `from` (any `stroke_light`
  direction, default `nw`; `redraw.light` in the catalog): the picture is painted with the
  scene's shade, tint and rim, then re-sampled at denoise 0.40 with the
  original graph's seed and negative and a positive that adds the scene's
  words. It works on any Anima picture, a `repair`, `masked_redraw` or
  `redraw` output included. The scene is cut with the source's `alpha` and
  `depth` assets under the same `cut` rule as deliver; assets that are
  missing or stale are cut in the graph and attached to the source.
- A source is refused when it is a delivered picture (the same set deliver
  refuses) or a LayerDiffuse picture. A `repair`, `masked_redraw` or
  `redraw` output is redrawn from its own pixels, with prompts and seed read
  from the original generate graph by following `base_generation`
  (at most 10 hops).
- Dial words are accepted for the `canvas` `denoise`. The row's result
  carries `resolved_options` with what actually ran.

### Deliver options

- The source must be a picture: a delivered picture and a LayerDiffuse
  picture are refused. Any other recipe or model is delivered as drawn.
- The options are `repin`, `recolor`, `skin`, `keep_legwear`, `keep_scene`,
  `transparent`, `backdrop`, `stroke_light`, `deliver_size`, `dof` and
  `light`; any other key is an error. An absent `repin`, `stroke_light` or
  `backdrop` takes the recipe's `deliver.defaults`, the same values the WebUI
  sends. `light` only shades the stroke and tints the backdrop; it does not
  redraw. An explicit `backdrop: null` without `transparent` delivers a
  transparent picture; `transparent: false` keeps the white background.
- `stroke_light` is a light direction (`n` .. `nw`), `even` (a uniform
  purple rim, the same as `null`) or `none` (no purple rim). Only a direction
  throws the drop shadow, straight away from the light. `light.scene`
  (`sunset` or `moon`) tints and brightens the backdrop toward the light and
  casts the sticker shadow in the scene's colour, both from `light.from`; an
  absent `stroke_light` follows `from`, `none` and `even` keep their rim and
  still get the scene's shadow, and a different direction is an error.
  Transparent and `keep_scene` deliveries take the lit figure without the
  backdrop tint.
- Dial words (`"keep"`, `"on"`, …) are accepted wherever a number is. The
  row's result carries `resolved_options` with what actually ran.
- The cut is stored on the source Generation: `alpha` (ViTMatte alpha),
  `depth` (only built when `dof` is set) and a json `cut` asset recording
  the matte model, matting model and revision, trimap and tile sizes, and
  the depth checkpoint and resolution. A later deliver loads an asset when
  its `cut` entry equals the worker's current values, and cuts again (and
  replaces the asset) when it differs or the asset is missing. Both are cut
  from the unrepinned source, so changing `repin`, `recolor` or `dof` reuses
  them; the foreground colour is estimated again after the repin each time.
- The delivered Generation refines the source; `dof.viewfinder: "both"`
  adds the viewfinder picture as a second one. No `mask` asset is attached.
- An absent `light` takes the `scene` and `from` of the nearest `light`
  redraw in the source's lineage (the source, then `base_generation` or what
  it refines, at most 10 hops). The inherited light is recorded in the
  request's `parameters`, and an absent `stroke_light` follows its `from`;
  an explicit `stroke_light` direction that differs is an error.

### Repair and masked redraw

- The source must be a picture: a delivered picture is refused. Each seed
  uploads one picture Generation (plus a `repair-mask` asset); there is no
  delivered output.
- Redrawing or delivering a repair or masked_redraw output reads recipe,
  prompts, seed and loaders from `parameters.base_generation`. The repaired
  pixels are what gets redrawn.
- The repair prompt drops face, hair and framing tags. Part LoRAs (`lora`)
  are skipped on an Anima source.

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
  generation.
- `experiment.overrides.patches` (from a chimera ExperimentRun) uses the
  same vocabulary and is exclusive with `generation.patches`.
