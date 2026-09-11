# yukari-sketch

> Yuzuki Yukari belongs to her original creators and rights holders -- see
> [Derivative work](../../README.md#derivative-work) in the README.

A third Yukari recipe, built for the `hassaku-il-v22` checkpoint plus the
`sketch-style-xl-linaqruf` LoRA (`src/comfyui_recipes/domain/yukari_sketch/`).
It has no style block, no texture bans and no second pass -- the LoRA and its
trigger words are what a minimal prompt needs to read as a sketch.

## Fixed vs. variable

`prompt_style.py` holds the blocks every pose wears: `QUALITY`, `TRIGGER`,
`CHARACTER`, `IDENTITY` (positive), `PROPORTION`, `BACKGROUND`, `LEGWEAR`,
`FACE`, `BODY`, `FINISH` (also positive; `FINISH` is always the tail and
holds the one finish tag, `(flat color:1.05)`), `NEGATIVE` -- one fixed
string, since there is no pose-specific ban and no style guard to vary
it -- and `GLOSS_BAN`, the shine tags every negative ends with.

The variable part is two small record sets:

- `poses.py`: one `Pose` per pose -- `action`, the costume it defaults
  to, an optional `face` override used whole in place of `FACE`, and an
  optional `canvas` used in place of the recipe's `WIDTH x HEIGHT`.
  Unlike `yukari` and `yukari-anima`, there is no mood, gesture or scene
  split; the pose is one tag block.
- `costumes.py`: one tag block per costume (`default`, `outing`, `bath`),
  plus two small per-costume tables: `LEGWEAR_BY_COSTUME` (the garment on
  the leg when it is not the recipe's `LEGWEAR` -- `bath` is bare-legged)
  and `NEGATIVE_BY_COSTUME` (appended to `NEGATIVE` -- `bath` bans the
  pantyhose and shoes the shared negative never had to).

## Poses

- `cinema`: costume `default`. Walking with popcorn and a drinking-straw
  cup, full body.
- `stand`: costume `default`. Standing with hands together, arched back,
  from the front, wide shot.
- `date`: costume `outing`. The cinema props plus white sneakers, a
  knee-length outing dress, and a jitome smirk with a blush and head
  tilt in place of the default `FACE`.
- `cafe`: costume `outing`, canvas `1024x1280`. Sitting at a table with
  her cheek on her hand, a coffee cup and saucer, seen slightly from
  above, upper body; the face is tareme and jitome with upturned eyes,
  a light smile and parted lips -- asking, not smirking.
- `home`: costume `outing`, canvas `1024x1280`. Sunk into a bean bag chair
  with shopping bags beside her, slouching with her arms limp, seen from
  above, upper body; the face is tareme and jitome with the head thrown
  back, mouth open, exhausted -- a groan, not a smile.
- `bath`: costume `bath`, canvas `1024x1280`. On the floor after a bath,
  one knee up and the other leg stretched out, leaning forward with both
  hands rubbing the stretched leg, seen slightly from above, cowboy shot;
  the face is tareme and jitome looking down at the leg, closed mouth,
  flushed.

## Assembly order

`recipe.py` is the only place that joins them. Positive:

```
QUALITY + TRIGGER + CHARACTER + IDENTITY
+ COSTUMES[costume] + pose.action
+ PROPORTION + BACKGROUND + (LEGWEAR_BY_COSTUME[costume] or LEGWEAR)
+ (pose.face or FACE) + BODY + FINISH
```

Negative is `NEGATIVE` plus the costume's `NEGATIVE_BY_COSTUME` entry when
it has one, then `GLOSS_BAN` -- `pose` and `costume` are still validated
against their tables so an unknown one is a `KeyError`, and the pose never
contributes a tag of its own to the negative.

`costume` defaults to the pose's own; passing it overrides just that block.

## Render constants

Fixed in `prompt_style.py`: `MODEL = "hassaku-il-v22"`, canvas `832x1664`
(a pose's own `canvas` replaces it -- `cafe`, `home` and `bath` are `1024x1280`), `steps=30`, `cfg=5.0`, sampler `dpmpp_2m`, scheduler `karras`, denoise
`1.0`. `LORA = ("sketch-style-xl-linaqruf.safetensors", 0.8)`. There is no
hires pass -- `render_spec` raises `ValueError` if `hires` or `denoise` is
requested.

The graph builder is `infrastructure/comfyui/yukari_graph.py`'s
`build_graph`, the same one `yukari` uses: a single `DiffusersLoader`
answers model, CLIP and VAE. When `RenderSpec.loras` is non-empty,
`build_graph` inserts one `LoraLoader` node per entry (ids `"10"`, `"11"`,
... chained), rewires the base pass's KSampler (`"3"`) to take its model
from the last loader and both `CLIPTextEncode` nodes (`"6"`, `"7"`) to take
their CLIP from it, and asserts `spec.hires is None` -- the hires ids would
otherwise collide with the loader chain. With `spec.loras` empty the graph
is exactly the pre-existing `yukari` shape.

## Finalize defaults

`delivery_style.py`: `FINALIZE_SIZE = 2560`, `FINALIZE_DENOISE = 0.55`,
`FINALIZE_DENOISE_LAYERDIFFUSE = 0.55`, `FINALIZE_SAMPLER = ("euler", "normal")`,
`FINALIZE_LATENT_ROUTE = True`, `FINALIZE_TRANSPARENT = True`.
`application/finalize.py` detects a sketch base by a `LoraLoader` node in
the base graph (checked before the anima check -- a base graph carries at
most one of the two) and picks these constants over yukari's and anima's
own. A layerdiffuse base picks `FINALIZE_DENOISE_LAYERDIFFUSE` instead of
`FINALIZE_DENOISE`. `--denoise`/`--size` still override either way.
`domain/yukari_sketch/dials.py` publishes this recipe's finalize denoise as
words -- `keep` (0.55, the default), `tidy` (0.65), `redraw` (0.8, the
value that turned a paper cup into a sheet of paper on a full-body base) --
plus `keep_legwear`, `toe_guard`, `lora_strength` and the repair-carried
options; `docs/queueing.md`'s "Named dials" section covers the resolution
rule shared by every recipe.

The redraw runs at `FINALIZE_SIZE` (2560), but the delivered file is then
downscaled (lanczos) to `delivery_style.DELIVER_SIZE` (1536), the recipe's
own default for the `deliver_size` request option (`--deliver-size` on the
CLI). A value at or above the redraw's own longest side means no downscale.

The delivered generation (gen 1) is an RGBA sticker by default: the refined
birefnet matte decides the silhouette, the soft matte only ramps the 1-px
edge, the white band and purple stroke are drawn around it exactly as in the
framed composite, and outside the stroke the alpha is 0 -- there is no
backdrop. `--opaque` (or request option
`"transparent": false`) restores the composite on the flat backdrop instead; `--keep-scene`
wins over both and delivers the redraw uncut.

`--backdrop stripes` (request option `"backdrop": "stripes"`) ships the
cutout on the lavender diagonal stripes with the white burst, opaque;
`--backdrop #RRGGBB` a flat colour. Either leaves `transparent` unset to
resolve to `false` instead of this recipe's usual `true`.

`--stroke-light` (request option `stroke_light`, one of the eight compass
keys) shades the purple stroke's width by that light direction instead of
drawing it at the uniform width; unset, the stroke stays uniform.

The redraw reuses the base pass's own checkpoint and prompt --
`domain/yukari_sketch/recipe.py`'s `refinement_prompt` returns the prompt
pair unchanged, since the LoRA (not a prompt swap) is what gives the base
pass its look. `refinement_graph.chain_pass` reads the redraw's model and
CLIP off the base graph's own KSampler and `CLIPTextEncode` nodes, so the
LoRA rides into the redraw automatically with no `loader` override.

The latent route is this recipe's own default (`FINALIZE_LATENT_ROUTE`):
`--latent-route` is then a no-op, and `--pixel-route` forces the pixel-space
route instead.

A base rendered with `layerdiffuse` carries its own RGBA, so its finalize
composes before it redraws: `YukariCompose` places the RGBA onto the
delivery's own flat backdrop with the white band and purple stroke drawn
around it -- the same hand-cut rim every other delivery gets -- and the
pixel-route upscale and redraw (the recipe's own LoRA riding into the
redraw's model and CLIP as usual) run on that composite, so the rim is
redrawn into the picture along with everything else. The redraw itself
runs at `FINALIZE_DENOISE_LAYERDIFFUSE` (0.55), its own constant rather than
`FINALIZE_DENOISE`: the layerdiffuse raw already holds its own scene at full
opacity, and a stronger redraw lets it invent background objects the raw
never drew.

By default (`FINALIZE_TRANSPARENT`) the redrawn picture then goes through
`YukariCutBackdrop`: no birefnet matte, since there is no silhouette left
to find by segmentation -- the only thing outside the rim is the flat
backdrop, redrawn, so it is cut by colour tolerance
(`delivery_style.CUT_BACKDROP_TOLERANCE`), bounded by `YukariCompose`'s own
MASK output (the geometry outside its bands, at the compose's own scale)
so a light figure passage -- pale hair, a pale prop -- never falls through
just for sitting inside the colour tolerance. The mask is resized to the
redraw's own scale and dilated by `delivery_style.CUT_BACKDROP_MARGIN` (a
share of the white band's own width) to absorb the redraw's edge drift
before the colour test runs, keeping the redrawn white band and purple rim
as part of the picture. The cut's own matte (the
`MaskToImage` of `YukariCutBackdrop`'s mask output) and the delivered RGBA
follow the usual `-matte`/`-delivered` `SaveImage` shape, with the
`deliver_size` scale applied to the delivered output only. An explicit
`backdrop`, `keep_scene`, or `transparent: false` selects the legacy path
instead: the composed-and-redrawn picture (bands and backdrop both baked
in) is the whole delivered picture, and nothing cuts it. The `backdrop`
request option (`--backdrop` on the CLI, a `#RRGGBB` hex colour or the named
pattern `stripes`) overrides the composite's backdrop on either path; unset,
it is the delivery's own flat default, and giving one forces the legacy
path since `YukariCutBackdrop` only means something against a flat colour.
The `upscale` request option (`--upscale` on the CLI: `bicubic`,
`nearest-exact`, `bilinear` or `lanczos`) selects the pixel-route
`ImageScale` node's `upscale_method` feeding that redraw; unset, it stays
`bicubic`. The `lora_strength` request option (`--lora-strength` on the CLI)
overrides the redraw's LoRA `strength_model`/`strength_clip`; unset, it stays
the recipe's own default. `route: "latent"` (`--latent-route`) encodes the
composite and upscales it in latent space instead.

## Requesting it

```json
"generation": {
  "recipe": "yukari-sketch",
  "parameters": {"pose": "cinema", "costume": "default"}
}
```

`pose` is required; `costume` is optional and falls back to the pose's own.
`hires`, `denoise` and `expression` are rejected for this recipe -- see
[queueing.md](../queueing.md).

`layerdiffuse` (bool, default `false`) adds a LayerDiffuse stage to the base
pass -- conv injection against the SDXL model by default
(`render.layerdiffuse_config` patches it), decoded through
`LayeredDiffusionDecode` and joined with its alpha by the core
`JoinImageWithAlpha` (whose alpha input is inverted, hence the `InvertMask`
between them) -- so the output PNG is RGBA instead of RGB. The
canvas must be a multiple of 64 in both dimensions; the recipe's own pose
canvases already are.

```bash
uv run comfy-recipes sketch prompt --pose cinema --json
```
