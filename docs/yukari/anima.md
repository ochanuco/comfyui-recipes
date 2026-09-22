# yukari

> Yuzuki Yukari belongs to her original creators and rights holders -- see
> [Derivative work](../../README.md#derivative-work) in the README.

The Yukari recipe that draws, built for the Anima Turbo checkpoint,
`anima-turbo-v1.1.safetensors` (circlestone-labs/Anima on Hugging Face)
(`src/comfyui_recipes/domain/yukari/`).

## Fixed vs. variable

`prompt_style.py` holds the blocks every pose wears: `QUALITY`,
`CHARACTER` (the series tags plus two weighted artist tags --
`(@oshiki hitoshi:0.85), (@yoshikawa hideaki:0.5)`; on Anima Turbo a weight
below `1.0` still registers, `0.85` on `oshiki hitoshi` keeps the thick
black line, and `0.5` on `yoshikawa hideaki` keeps the face from
elongating and the eyes from shrinking while still suppressing the
handwritten text `oshiki hitoshi` brings alone), `IDENTITY`, `BODY`,
`BACKGROUND` (`simple background, (green background:1.3)` -- every pose
draws on the green screen, the key colour `clean_background` despills; the
earlier grey default sat too close to the paper-white skin for the matte
edge), `FACE`, `STYLE` (positive:
`flat color`, `sketch` and `traditional media` -- `flat color` and
`sketch` together draw a hatched line into the shadows that neither does
alone; the earlier thirteen-tag flat/cel block turned the skin paper-white),
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
  `standard`, `suspender`) and a matching `LEGWEAR` block per costume, layered on top
  of the garments when the pose's `legwear` is `True`. `standard` is a
  black hooded cardigan, rabbit hood and purple dress; its `LEGWEAR` is
  black tights with a purple gradient. `suspender` is a muted orange t-shirt with
  a knee-length navy suspender skirt over black tights; no pose defaults
  to it, so it is picked with `parameters.costume`. `COSTUME_BAN` holds the
  negative tags a costume adds (`suspender` bans shirt prints and bright
  orange). `HOODED_COSTUMES` names the
  costumes whose garments already include a hood or cardigan (`standard`).
  The request parameter `legwear` picks between `opaque` (the costume's
  own `LEGWEAR`, the default) and `sheer-gloss` (`SHEER_GLOSS_LEGWEAR`, the
  same low-denier block on every costume). `sheer-gloss` also edits the
  negative: it drops the garment-gloss runs of `SHINE_BAN`
  (`GARMENT_GLOSS_TAGS`) and appends `SHEER_BAN` (opaque legwear, latex,
  photo-realism, tanned or brown skin tones). A pose with `legwear=False`
  ignores the parameter on both sides.
- `expressions.py`: one `mouth`/`eyes` pair per expression (`resting`,
  `sleepy`, `doya`, `smile`, `gao`).

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
  legwear (`legwear=False`) and overrides `body` to a bare adult-proportions
  block with no leg tags.
- `gao`: expression `gao`, costume `standard`. A claw pose with an open,
  fanged mouth, leaning forward with hands up, cowboy shot from the front.

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
+ SHINE_BAN + GRADIENT_BAN
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

Fixed in `prompt_style.py`: `MODEL = "anima-turbo-v1.1.safetensors"`,
canvas `1024x1640`, `steps=10`, `cfg=2.0`, sampler `euler`, scheduler
`normal`, denoise `1.0`. Turbo is the distilled Anima: about 33 s a render
against 75-85 s for the base model at `steps=25`/`cfg=3.5`/`er_sde`. Its
card recommends `cfg=1`, but at `1` the negative prompt does nothing -- the
shine, shadow and mouth bans all stop working -- so `2.0` keeps them in
play; the base model is `anima_baseV10.safetensors` through a
`render.model` patch.

### Hires pass

`hires` is the target longest side in pixels. The second-pass canvas is
computed proportionally from
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
`qwen_image_vae`). The KSampler is node `"3"` and the tail is a `VAEDecode`
feeding `SaveImage`,
the same shape `refinement_graph.chain_pass` reads off any base graph.
`render_spec` passes the pose's own `loras` straight through; each pair
chains a `LoraLoaderModelOnly` node off the `UNETLoader` (or the previous
LoRA), in order, starting at node id `"10"`. The hires `LatentUpscale` and
second `KSampler` are appended after that chain, continuing the same id
counter -- so a pose with one LoRA gets hires nodes `"11"`/`"12"`, and a
pose with none gets `"10"`/`"11"`.

## Finalize defaults

`delivery_style.py`: `FINALIZE_SIZE = 2560`, `FINALIZE_DENOISE = 0.4`,
`FINALIZE_MODEL = "hassaku-il-v22"`, `FINALIZE_SAMPLER = ("dpmpp_2m",
"karras")`, `FINALIZE_STEPS = 30`, `FINALIZE_CFG = 5.0`. `application/
finalize.py` inspects the base graph it fetched: a `UNETLoader` node marks
an anima source, the only one finalize redraws; a source with no
`UNETLoader` (a plain or already-refined generation) must go through
`deliver_only` instead, or finalize refuses it. `--denoise`/`--size` still
override the redraw's own defaults. `0.4` is the strength the user picked
on bases drawn with no style LoRA,
over `0.55`, `0.75` and `0.9`; on a base that carries the sketch-style LoRA,
`0.55` and up adds gloss to the legwear and re-decides buttons and
ornaments.

`--keep-scene` delivers the redraw uncut, background and all, instead of
the die-cut sticker; the matte is still rendered and stored.

The redraw runs through a different checkpoint, `hassaku-il-v22`
(Illustrious, loaded through `DiffusersLoader`), rather than the
stage-1 Anima checkpoint. `refinement_graph.chain_pass`'s `loader` argument adds
that `DiffusersLoader` node and reroutes the redraw's model, CLIP and both
VAEs (encode and decode) through it, re-encoding the base prompts on its
CLIP. `--finalizer MODEL` overrides `FINALIZE_MODEL` with a different
checkpoint: a name ending in `.safetensors` loads from `models/checkpoints`
through `CheckpointLoaderSimple`, anything else is a `models/diffusers`
folder.

`domain/yukari/recipe.py`'s `refinement_prompt` builds the redraw
prompt: the positive replaces `STYLE`, the recipe's style tail,
with `ROUGH_STYLE`, aiming the IL checkpoint at a rough, unfinished line
instead. The negative drops `DETAIL_BAN`, `GRADIENT_BAN` and
`COLORED_LINE_BAN` -- bans against a look the redraw is now asking for --
and prefixes `ROUGH_BAN + PAINT_BAN + HAND_BAN + SHADE_BAN + DOT_BAN`
(`HAND_BAN`, `SHADE_BAN` and `DOT_BAN` live in this recipe's own
`prompt_style.py`; see below for what each guards against).

The catalog publishes `delivery_style.py`'s `FINALIZE_DEFAULTS` --
`deliver_only: true, repin: true, stroke_light: "n", backdrop: "dots"` -- as
chimera's GUI's finalize form defaults for this recipe: an option-less
finalize cuts the matte, repins and delivers the Anima pick itself, and the
redraw above is a per-request opt-in via `denoise`, `size`, `route` or
another redraw-shaping option.

## Requesting it

```json
"generation": {
  "recipe": "yukari",
  "parameters": {"pose": "coffee", "costume": "outing", "expression": "doya"}
}
```

`pose` is required; `costume` and `expression` are optional and fall back
to the pose's own. `hires` and `denoise` are accepted for this recipe --
`hires` is the target longest side of the second pass, `denoise` overrides
`HIRES_DENOISE` and needs `hires` set -- see [queueing.md](../queueing.md).

`domain/yukari/dials.py` publishes `render.width`/`render.height` as
words for `generation.patches` -- `draft` (`1024`/`1640`, the default
canvas) and `full` (`1280`/`2048`); `docs/queueing.md`'s "Named dials"
section covers the resolution rule shared by every recipe.

```bash
uv run comfy-recipes yukari prompt --pose coffee --json
```

## HAND_BAN and the pass-depth split

This split exists because of one measured asymmetry. `boss` found that
removing `half-closed eyes` opens the eyes some, and that removal PLUS
`(half-closed eyes:1.4), (closed eyes:1.4)` in the negative opens them the
rest of the way -- 「open, iris visible」 -- and in the same breath found
that the pair is safe chained onto a settled picture and unsafe from
scratch: run from the recipe, it stacked with that pose's buttons guard and
grew a second chair with a rabbit face on it, the fourth intruder this file
has bought by stacking guards.

The reasoning kept: a late pass only gets to delete, and a guard IS a
deletion. A first pass gets to rearrange the composition around the same
guard, and it does. So a guard whose job is subtraction belongs in the
pass-2-only set (`HAND_BAN` and friends) rather than in the base negative,
where it would be handed to a pass that can still rearrange around it.

## SHADE_BAN

「線画の絵柄が変わったね」. Every pose gets these tags on the second pass
only, at 1.45/1.5/1.45/1.45 -- the same four tags already sit in NEGATIVE at
1.2/1.25, this is the same guard at a weight that survives a 2x redraw.

The diagnosis is worth keeping because it exonerates two suspects. Distinct
flats over the figure measured 849 on the first `hoops` render, 643 on
`knotK2`, and 1154 and 1167 on the two finalised prints -- the gloss
arrived between them. It is not the pass-1 prompt: the same pass 1 measured
552 with no second pass at all. It is not `6b` either: the 1167 render has
no `6b` node. What changed is that pass 1 handed pass 2 a different latent,
and the redraw landed in a glossier style -- specular hair, gradient
irises, airbrushed skin, i.e. exactly the "clean and vivid" regression this
guard exists to prevent.

Raising the guard weights to 1.45/1.5 for the second pass measured 590
against 1154 on the same pass 1. `(short dress:1.35)` was the other
suspect and it is innocent: dropping it from the pass-2 positive measured
1147, i.e. nothing.

Pass 1 keeps its weights at 1.2/1.25, untouched: at 1024 that weight was
never losing, and raising it there would re-roll the composition of every
picked render in the file. The guard belongs to the pass that redraws.
