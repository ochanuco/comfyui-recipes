#!/usr/bin/env python3
"""Yukari's settled recipe, and a seed sweep to check it stays settled.

This is `fb-b` (prompt id 4c012937), chosen after the design was restored from
gl-lounge-555666777 / job 38918ed3. Everything here is the reference's own
vocabulary; the port onto the Hamakaze graph is not part of it.

    uv run scripts/yukari_recipe.py --seeds 6          # sweep fresh seeds
    uv run scripts/yukari_recipe.py --seed 555666777   # the settled render
    uv run scripts/yukari_recipe.py --pose portrait    # head and shoulders
    uv run scripts/yukari_recipe.py --pose peace       # double v, v over eye
    uv run scripts/yukari_recipe.py --pose invite      # patting her lap, one girl

**There are two costumes now, and `default` is still the settled one.** The
second is `sporty` -- grey oversized tee, denim shorts, plain black tights,
white high tops -- and it was added the way it was so that the first one is one
flag away and unchanged: both hang on the same `IDENTITY`, and `--costume
default` builds the same prompt and the same graph, tag for tag, as the commit
before it existed. That was checked across every pose rather than assumed.

    uv run scripts/yukari_recipe.py --pose hype --costume sporty --seeds 6

What a costume owns is three blocks -- character, legwear, hood -- and nothing
else. FACE, SURFACE, BODY, THIN, every pose and the whole negative are shared,
which is the claim: what changes is the clothes, not her and not the drawing.
Two things follow, and both are in the code rather than in this paragraph:

- The garment splices in `positive()` (`open cardigan`, `(drawstring:1.4)`,
  `(oversized shirt:1.3)`) name tags only the settled costume has, so they are
  gated on the costume and go through `_splice`, which ASSERTS. A splice that
  matches nothing does nothing and says nothing; with two costumes in the file
  that stopped being a hypothetical.
- Three guards are released under `sporty` and only there: `situp`'s
  `(sportswear:1.45), (gym uniform:1.4)` (that costume IS a gym kit -- the
  arched-back guard beside it is about her back and stays), `stand`'s
  `(white footwear:1.45), (red footwear:1.4)` (its shoes are white), and
  `(blue tint:1.4)` (denim is blue). `(blue background:1.5)` is NOT released:
  the backdrop is set afterwards by recolor_bg.py and a blue one in the render
  is still a defect.

Sweep cheap, then print big. The first pass does not change when `--hires` is
added -- same seed, same latent, same picture -- so a seed picked at the sweep
size comes back as the same drawing, only with detail the small render had no
room for:

    uv run scripts/yukari_recipe.py --pose sip --seeds 8              # find one
    uv run scripts/yukari_recipe.py --pose sip --seed 999999999 \
        --hires 2048                                                  # keep it

Which also means a render the sweep did not produce is not waiting at 2048.
The arc that 1029384756 refuses to draw at 1024 is refused there too: the
second pass redraws what the first one decided, it does not reconsider it.

**The leg is ONE garment, and that is deliberate across every pose.** A single
pantyhose, purple at the thigh running to black at the ankle, with the second
garment banned by name in the negative. Pale socks over grey tights was this
repo's own design and it is retired -- `LEGWEAR_LAYERED` keeps its text and its
measurements, and the note above `LEGWEAR` says what broke it. So `--pose peace`
no longer reproduces 9d24700e pixel-for-pixel, and neither does anything else
from the layered lineage; the `pick/yk-recipe` tag still points at the commit
that does.

Settled on the prone pose and then kept global rather than split per pose,
because it is the costume and not a framing: the palette is one palette. If a
future pose wants the layering back, name `LEGWEAR_LAYERED` in a splice and take
`LEGWEAR_BAN` back out of that pose's negative -- both halves, or the guards
will delete the garment the splice just asked for.

Then set the backdrop, which the prompt does not control -- it landed on
#d0d0c0, #a0a0a0 and #909090 across three renders whose only difference was two
leg-tag weights:

    uv run scripts/recolor_bg.py out/yk-peace-555666777_00001_.png --color '#d0d0c0'

Three findings are baked into the constants and should not be quietly undone:

- **`(realistic:1.1)` belongs in the NEGATIVE.** The Hamakaze pipeline had it
  positive at 1.3, and that single flip did more damage to her look than any
  other change. Same for shading: flat colour with soft shading, and
  (heavy shading), (detailed shading) held out.
- **The rabbit hood stays on her and goes down.** (rabbit hood:1.55) with
  (hood down:1.5), (hood behind head:1.3) and (hood up:1.5) negative. Deleting
  the hood to uncover the hair costs more identity than it buys.
- **1024x1536 is the ceiling for full body.** 1280x1920 improves the stroke-to-
  figure ratio from 1.91 to 1.53 (in 1536-equivalent pixels) but drew a second
  figure in both renders that tried it, with (solo:1.5) already in the prompt.

And one non-finding, recorded so it is not retried: **the line width does not
respond to tags.** Median stroke is 1.91px in the 1024x1024 portrait, at
1024x1280, at 1024x1536, and with (thin lineart:1.3), (fine lines:1.25),
(delicate lines:1.2) added. Full-body line reads heavier only because the head is
smaller, not because the stroke changed.

Those thin-line tags are kept anyway, because `fb-b` is the render that was
accepted and they are in it. They do change the image -- just not the thing they
are named for. Dropping them on the grounds that the measurement came back null
would quietly ship a different picture than the one that was chosen.
"""

from __future__ import annotations

import argparse
import json
import urllib.request

from comfy_host import DEFAULT_HOST, DEFAULT_PORT

# The recipe lives in the package domain now -- prompt_style / costumes /
# poses / recipe -- and this file is the temporary CLI plus public facade. Every
# name below is re-exported explicitly because a decade of scripts (and
# .local probes) import them from here; `costume_check.py` fingerprints them
# from here too. Adding to the package? Export it here or it does not exist.
from comfyui_recipes.domain.yukari.costumes import (
    CHARACTER,
    COSTUME_NEGATIVE_EDITS,
    COSTUMES,
    FITNESS,
    FITNESS_HOOD,
    FITNESS_LEGWEAR,
    HOOD,
    IDENTITY,
    LEGWEAR,
    LEGWEAR_BAN,
    LEGWEAR_LAYERED,
    ROOMWEAR,
    ROOMWEAR_HOOD,
    ROOMWEAR_LEGWEAR,
    SHOD,
    SPORTY,
    SPORTY_HOOD,
    SPORTY_LEGWEAR,
)
from comfyui_recipes.domain.yukari.models import Edit, Pose
from comfyui_recipes.domain.yukari.poses import (
    CROWD_BAN,
    GAO_FACE,
    GAO_HANDS,
    POSE_RECORDS,
    POSES,
    SCENE_TRAIN,
)
from comfyui_recipes.domain.yukari.prompt_style import (
    RESTING_EYES,
    BODY,
    FACE,
    HAND_BAN,
    HANDDRAWN_FINISH,
    HIRES_DENOISE,
    HIRES_NEGATIVE_PAINT,
    NEGATIVE,
    SHADE_BAN,
    SURFACE,
    THIN,
)
from comfyui_recipes.domain.yukari.recipe import (
    HEAD_FRAMINGS,
    HIRES_FINISH,
    HIRES_NEGATIVE,
    HIRES_POSITIVE,
    HIRES_PRINT,
    PAINT_FINISH,
    SETTLED_SEED,
    SIZES,
    SWEEP_SEEDS,
    _apply,
    _splice,
    negative,
    pose_block,
    positive,
)
from comfyui_recipes.infrastructure.comfyui.yukari_graph import build


def _negative_base(pose: str) -> str:
    """NEGATIVE with the pose's base edits -- kept for the probes that read it.

    Compat surface only: `negative()` no longer routes through this name, so
    monkeypatching it (as old .local probes did) no longer reaches the
    recipe. Patch the record's `negative_base` instead.
    """
    from comfyui_recipes.domain.yukari.recipe import _apply as apply_edits
    return apply_edits(NEGATIVE, POSE_RECORDS[pose].negative_base, "default")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pose", choices=sorted(POSES), default="lounge")
    parser.add_argument("--costume", choices=sorted(COSTUMES), default="default",
                        help="which set of clothes; the settled one is `default`")
    parser.add_argument("--seed", type=int, action="append", default=[])
    parser.add_argument("--seeds", type=int, default=0,
                        help="take this many from the fixed sweep list")
    parser.add_argument("--prefix", default="yk")
    parser.add_argument(
        "--hires",
        type=int,
        default=0,
        help="redraw at this size on a second pass (1536 and 2048 are measured)",
    )
    parser.add_argument(
        "--hires-denoise",
        type=float,
        help="override the second pass denoise; the default follows the upscale",
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--print-prompt", action="store_true")
    args = parser.parse_args()

    if args.print_prompt:
        print(positive(args.pose, args.costume), "\n\n---\n\n",
              negative(args.pose, args.costume))
        return

    # The costume goes in the filename. Two sets of clothes through one pose at
    # one seed are otherwise two files a letter apart in the output directory,
    # and the second one is the one nobody can name afterwards.
    prefix = (args.prefix if args.costume == "default"
              else f"{args.prefix}-{args.costume}")
    seeds = args.seed or SWEEP_SEEDS[:args.seeds] or [SWEEP_SEEDS[0]]
    for seed in seeds:
        req = urllib.request.Request(
            f"http://{args.host}:{args.port}/prompt",
            data=json.dumps({"prompt": build(args.pose, seed, prefix,
                                             args.hires or HIRES_PRINT.get(
                                                 args.pose, (0,))[0],
                                             args.hires_denoise,
                                             args.costume)}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(seed, json.load(resp)["prompt_id"], flush=True)


if __name__ == "__main__":
    main()
