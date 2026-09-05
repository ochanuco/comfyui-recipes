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
`FACE`, `BODY` (also positive, always the tail), and `NEGATIVE` -- one
fixed string, since there is no pose-specific ban and no style guard to
vary it.

The variable part is two small record sets:

- `poses.py`: one `Pose` per pose -- `action`, the costume it defaults
  to, an optional `face` override used whole in place of `FACE`, and an
  optional `canvas` used in place of the recipe's `WIDTH x HEIGHT`.
  Unlike `yukari` and `yukari-anima`, there is no mood, gesture or scene
  split; the pose is one tag block.
- `costumes.py`: one tag block per costume (`default`, `outing`).

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

## Assembly order

`recipe.py` is the only place that joins them. Positive:

```
QUALITY + TRIGGER + CHARACTER + IDENTITY
+ COSTUMES[costume] + pose.action
+ PROPORTION + BACKGROUND + LEGWEAR + (pose.face or FACE) + BODY
```

Negative is `NEGATIVE` verbatim -- `pose` and `costume` are still validated
against their tables so an unknown one is a `KeyError`, but neither
contributes a tag of its own to the negative.

`costume` defaults to the pose's own; passing it overrides just that block.

## Render constants

Fixed in `prompt_style.py`: `MODEL = "hassaku-il-v22"`, canvas `832x1664`
(a pose's own `canvas` replaces it -- `cafe` is `1024x1280`), `steps=30`, `cfg=5.0`, sampler `dpmpp_2m`, scheduler `karras`, denoise
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
`FINALIZE_SAMPLER = ("euler", "normal")`, `FINALIZE_LATENT_ROUTE = True`.
`application/finalize.py` detects a sketch base by a `LoraLoader` node in
the base graph (checked before the anima check -- a base graph carries at
most one of the two) and picks these constants over yukari's and anima's
own. `--denoise`/`--size` still override either way.

The redraw reuses the base pass's own checkpoint and prompt --
`domain/yukari_sketch/recipe.py`'s `refinement_prompt` returns the prompt
pair unchanged, since the LoRA (not a prompt swap) is what gives the base
pass its look. `refinement_graph.chain_pass` reads the redraw's model and
CLIP off the base graph's own KSampler and `CLIPTextEncode` nodes, so the
LoRA rides into the redraw automatically with no `loader` override.

The latent route is this recipe's own default (`FINALIZE_LATENT_ROUTE`):
`--latent-route` is then a no-op, and `--pixel-route` forces the pixel-space
route instead.

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

```bash
uv run comfy-recipes sketch prompt --pose cinema --json
```
