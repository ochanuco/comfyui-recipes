# yukari-anima

> Yuzuki Yukari belongs to her original creators and rights holders -- see
> [Derivative work](../../README.md#derivative-work) in the README.

A second Yukari recipe, built for the `hassakuAnima_v13.safetensors`
checkpoint (`src/comfyui_recipes/domain/yukari_anima/`). It shares no code
with `yukari` -- the two checkpoints do not share a prompt vocabulary or a
graph shape -- but has a hires second pass that mirrors `yukari`'s.

## Fixed vs. variable

`prompt_style.py` holds the blocks every pose wears: `QUALITY`,
`CHARACTER`, `IDENTITY`, `BODY`, `BACKGROUND`, `FACE`, `STYLE` (positive),
and the negative bans (`DIGIT_BAN` through `PROPORTION_BAN`). `BODY`
carries the mature-female build: adult proportions, wide hips, thick and
soft thighs, long legs, a narrow waist, and seven heads tall.

The variable part is three small record sets:

- `poses.py`: one `Pose` per pose -- `action`, `mood`, `gesture`, `scene`,
  the pose's own default `expression` and `costume`, and an optional
  pose-specific negative addition. A pose may also override `legwear`
  (default `True`; `False` drops the costume's leg tags), `body` and
  `style` (replace `BODY`/`STYLE` wholesale), and carry its own `loras`
  (default empty).
- `costumes.py`: one garment tag block per costume (`roomwear`, `outing`,
  `standard`) and a matching `LEGWEAR` block per costume, layered on top
  of the garments when the pose's `legwear` is `True`. `standard` is a
  black hooded cardigan, rabbit hood and purple dress; its `LEGWEAR` is a
  pale-purple gradient tights. `HOODED_COSTUMES` names the costumes whose
  garments already include a hood or cardigan (`standard`).
- `expressions.py`: one `mouth`/`eyes` pair per expression (`resting`,
  `sleepy`, `doya`, `smile`).

## Poses

- `brush`: expression `sleepy`, costume `roomwear`.
- `coffee`: expression `resting`, costume `outing`.
- `amae`: expression `doya`, costume `outing`.
- `step`: expression `resting`, costume `outing`.
- `stand`: expression `doya`, costume `outing`.
- `sofa`: expression `sleepy`, costume `roomwear`, canvas `2048x1280`.
  Lying on her side on a couch after a bath: wet hair, a towel around the
  neck, and baggy purple thighhighs.
- `cinema`: expression `doya`, costume `outing`. Walking through a movie
  theater lobby with a popcorn bucket in one hand and a cola cup with a
  straw in the other.
- `bust`: expression `smile`, costume `standard`, canvas `1280x1280`.
  Head-and-shoulders portrait, looking at viewer. Drops the costume's
  legwear (`legwear=False`), overrides `body` to a bare adult-proportions
  block with no leg tags, overrides `background` to a green screen
  (`(green background:1.3)`, the key colour `clean_background` despills),
  prefixes `STYLE` with the sketch-style LoRA's trigger tag via `style`,
  and loads that LoRA (`anima-sketch-style-chosen.safetensors`, weight
  `0.8`) via `loras`.

A pose may carry its own `canvas`; `render_spec` uses it in place of the
default `1024x1640`.

## Assembly order

`recipe.py` is the only place that joins them. Positive:

```
QUALITY + CHARACTER + IDENTITY
+ pose.action + expression.mouth + pose.mood + expression.eyes + pose.gesture
+ COSTUMES[costume] + (LEGWEAR[costume] if pose.legwear else "") + pose.scene
+ (pose.body if pose.body is not None else BODY) + BACKGROUND + FACE
+ (pose.style if pose.style is not None else STYLE)
```

Negative:

```
DIGIT_BAN + DETAIL_BAN + COLORED_LINE_BAN + THIN_BODY_BAN
+ pose.negative
+ SHINE_BAN + HATCH_BAN + GRADIENT_BAN
+ NEGATIVE_TAIL + (HOOD_BAN unless costume in HOODED_COSTUMES) + SCORE_BAN
+ PROPORTION_BAN
```

`PROPORTION_BAN` is the fixed tail: it bans the builds `BODY` argues
against -- fat, chubby, short legs, muscular, toned, and the
child/loli/chibi/aged-down range. `HOOD_BAN` bans a bare hood/cardigan;
it is left out for any costume in `HOODED_COSTUMES` so the negative
doesn't ban the garment the costume just drew.

`costume` and `expression` default to the pose's own; passing either
overrides just that block. `legwear`, `body`, `style` and `loras` are
fixed by the pose and are not overridable per call -- `pose.legwear`
still gates the costume override's own `LEGWEAR` entry, so
`positive("stand", costume="standard")` carries `standard`'s legwear
tags because `stand.legwear` is `True`. An unknown pose, costume or
expression is a `KeyError`.

## Render constants

Fixed in `prompt_style.py`: `MODEL = "hassakuAnima_v13.safetensors"`,
canvas `1024x1640`, `steps=25`, `cfg=3.5`, sampler `er_sde`, scheduler
`normal`, denoise `1.0`.

### Hires pass

`hires` is the target longest side in pixels, same convention as
`yukari.recipe`. The second-pass canvas is computed proportionally from
the pose's own first-pass canvas -- `1024x1640` becomes `1280x2048` at
`hires=2048` -- and rounded to a multiple of 8; `render_spec` raises
`ValueError` if either dimension would come out below 8. The second pass
is a `LatentUpscale` (bicubic) into a second `KSampler` on the same
UNET/LoRA chain, with the same prompts as the first pass: anima has no
pass-2 positive/negative records of its own, so `HiresSpec.positive` is
always `None` and `HiresSpec.negative` is always the base negative.
`denoise` defaults to `HIRES_DENOISE = 0.4`; passing `denoise` without
`hires` is a `ValueError`.

The graph builder (`infrastructure/comfyui/anima_graph.py`) wires a
`UNETLoader` + `CLIPLoader` + `VAELoader` triple (`qwen_3_06b_base` /
`qwen_image_vae`) rather than yukari's single `DiffusersLoader`; the
KSampler is node `"3"` and the tail is a `VAEDecode` feeding `SaveImage`,
the same shape `refinement_graph.chain_pass` reads off any base graph.
`render_spec` passes the pose's own `loras` straight through; each pair
chains a `LoraLoaderModelOnly` node off the `UNETLoader` (or the previous
LoRA), in order, starting at node id `"10"`. The hires `LatentUpscale` and
second `KSampler` are appended after that chain, continuing the same id
counter -- so a pose with one LoRA gets hires nodes `"11"`/`"12"`, and a
pose with none gets `"10"`/`"11"`.

## Finalize defaults

`delivery_style.py`: `FINALIZE_SIZE = 2560`, `FINALIZE_DENOISE = 0.55`,
`FINALIZE_MODEL = "hassaku-il-v22"`, `FINALIZE_SAMPLER = ("dpmpp_2m",
"karras")`, `FINALIZE_STEPS = 30`, `FINALIZE_CFG = 5.0`.
`application/finalize.py` picks these over yukari's own defaults by
inspecting the base graph it fetched: a `UNETLoader` node means an anima
base, and its finalize constants apply; anything else keeps the yukari
defaults. `--denoise`/`--size` still override either way. `0.55` holds the
figure apart from dark furniture it touches; `--denoise 0.75` is the rougher
pencil for a figure standing alone on a plain ground.

`--keep-scene` delivers the redraw uncut, background and all, instead of
the die-cut sticker; the matte is still rendered and stored.

The redraw runs through a different checkpoint, `hassaku-il-v22`
(Illustrious, loaded through `DiffusersLoader`), rather than
`hassakuAnima_v13`. `refinement_graph.chain_pass`'s `loader` argument adds
that `DiffusersLoader` node and reroutes the redraw's model, CLIP and both
VAEs (encode and decode) through it, re-encoding the base prompts on its
CLIP. `--finalizer MODEL` overrides `FINALIZE_MODEL` with a different
checkpoint.

`domain/yukari_anima/recipe.py`'s `refinement_prompt` builds the redraw
prompt: the positive replaces `STYLE`, hassakuAnima's flat/cel-shaded tail,
with `ROUGH_STYLE`, aiming the IL checkpoint at a rough, unfinished line
instead. The negative drops `HATCH_BAN`, `DETAIL_BAN`, `GRADIENT_BAN` and
`COLORED_LINE_BAN` -- bans against a look the redraw is now asking for --
and prefixes `ROUGH_BAN + PAINT_BAN + HAND_BAN + SHADE_BAN + DOT_BAN`
(`HAND_BAN`, `SHADE_BAN` and `DOT_BAN` are the same redraw guards `yukari`
uses, imported from `yukari.prompt_style`).

The catalog publishes `delivery_style.py`'s `FINALIZE_DEFAULTS` --
`deliver_only: true, repin: false, stroke_light: "n"` -- as chimera's GUI's
finalize form defaults for this recipe.

## Requesting it

```json
"generation": {
  "recipe": "yukari-anima",
  "parameters": {"pose": "coffee", "costume": "outing", "expression": "doya"}
}
```

`pose` is required; `costume` and `expression` are optional and fall back
to the pose's own. `hires` and `denoise` are accepted for this recipe --
`hires` is the target longest side of the second pass, `denoise` overrides
`HIRES_DENOISE` and needs `hires` set -- see [queueing.md](../queueing.md).

`domain/yukari_anima/dials.py` publishes `render.width`/`render.height` as
words for `generation.patches` -- `draft` (`1024`/`1640`, the default
canvas) and `full` (`1280`/`2048`); `docs/queueing.md`'s "Named dials"
section covers the resolution rule shared by every recipe.

```bash
uv run comfy-recipes anima prompt --pose coffee --json
```
