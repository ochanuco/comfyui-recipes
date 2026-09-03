# yukari-anima

> Yuzuki Yukari belongs to her original creators and rights holders -- see
> [Derivative work](../../README.md#derivative-work) in the README.

A second Yukari recipe, built for the `hassakuAnima_v13.safetensors`
checkpoint (`src/comfyui_recipes/domain/yukari_anima/`). It shares no code
with `yukari` -- the two checkpoints do not share a prompt vocabulary or a
graph shape -- and has no second pass.

## Fixed vs. variable

`prompt_style.py` holds the blocks every pose wears: `QUALITY`,
`CHARACTER`, `IDENTITY`, `BODY`, `BACKGROUND`, `FACE`, `STYLE` (positive),
and the negative bans (`DIGIT_BAN` through `NEGATIVE_TAIL`).

The variable part is three small record sets:

- `poses.py`: one `Pose` per pose -- `action`, `mood`, `gesture`, `scene`,
  the pose's own default `expression` and `costume`, and an optional
  pose-specific negative addition.
- `costumes.py`: one tag block per costume (`roomwear`, `outing`).
- `expressions.py`: one `mouth`/`eyes` pair per expression (`resting`,
  `sleepy`, `doya`).

## Assembly order

`recipe.py` is the only place that joins them. Positive:

```
QUALITY + CHARACTER + IDENTITY
+ pose.action + expression.mouth + pose.mood + expression.eyes + pose.gesture
+ COSTUMES[costume] + pose.scene
+ BODY + BACKGROUND + FACE + STYLE
```

Negative:

```
DIGIT_BAN + DETAIL_BAN + COLORED_LINE_BAN + THIN_BODY_BAN
+ pose.negative
+ SHINE_BAN + HATCH_BAN + GRADIENT_BAN + NEGATIVE_TAIL
```

`costume` and `expression` default to the pose's own; passing either
overrides just that block. An unknown pose, costume or expression is a
`KeyError`.

## Render constants

Fixed in `prompt_style.py`: `MODEL = "hassakuAnima_v13.safetensors"`,
canvas `1536x1920`, `steps=25`, `cfg=3.5`, sampler `er_sde`, scheduler
`normal`, denoise `1.0`. There is no hires pass -- `render_spec` raises
`ValueError` if `hires` or `denoise` is requested.

The graph builder (`infrastructure/comfyui/anima_graph.py`) wires a
`UNETLoader` + `CLIPLoader` + `VAELoader` triple (`qwen_3_06b_base` /
`qwen_image_vae`) rather than yukari's single `DiffusersLoader`; the
KSampler is node `"3"` and the tail is a `VAEDecode` feeding `SaveImage`,
the same shape `refinement_graph.chain_pass` reads off any base graph.

## Finalize defaults

`delivery_style.py`: `FINALIZE_SIZE = 2560`, `FINALIZE_DENOISE = 0.20`.
`application/finalize.py` picks these over yukari's own defaults by
inspecting the base graph it fetched: a `UNETLoader` node means an anima
base, and its `FINALIZE_DENOISE`/`FINALIZE_SIZE` apply; anything else keeps
the yukari defaults. `--denoise`/`--size` still override either way.

## Requesting it

```json
"generation": {
  "recipe": "yukari-anima",
  "parameters": {"pose": "coffee", "costume": "outing", "expression": "doya"}
}
```

`pose` is required; `costume` and `expression` are optional and fall back
to the pose's own. `hires` and `denoise` are rejected for this recipe --
see [queueing.md](../queueing.md).

```bash
uv run comfy-recipes anima prompt --pose coffee --json
```
