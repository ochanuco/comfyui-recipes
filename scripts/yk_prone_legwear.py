#!/usr/bin/env python3
"""`prone` with knee-highs over tights, done by REGION instead of by tag.

    uv run scripts/yk_prone_legwear.py                 # 1536x1024
    uv run scripts/yk_prone_legwear.py --hires 2048    # the print

The problem this exists for is written up in `yukari_recipe.py`'s prone splice
and in render-notes: **this model has no two-layer construction at knee length.**
`thighhighs over pantyhose` is the only layering tag it knows and its length is
in its name; `kneehighs` describes a leg with nothing else on it. Nine
prompt-side attempts -- length words, three layering phrases, weights walked
both ways, a bare-leg guard, maximum colour contrast, and a masked refine --
left the two garments taking turns, never sharing a leg.

They do not have to share a *prompt*, though. They occupy different parts of the
picture, and ComfyUI conditions parts of the picture separately:

    base    the whole prompt with the legwear block removed,
            masked to everything OUTSIDE the two regions
    thigh   the same prompt plus grey pantyhose, masked over hip and thigh
    calf    the same prompt plus white knee-highs, masked over the lower legs

Three measurements are baked into that shape and each cost a render:

- **The region prompt has to carry the whole prompt, not just its garment.** A
  five-tag fragment measured nothing at strength 1, 2 and 3: the base
  conditioning describes the entire picture and a fragment cannot outvote it.
- **The base has to be masked to the complement.** Left covering everything, it
  still describes the thigh, and averaging a prompt that says nothing about
  legwear with one that does lands halfway -- pale, barely-there tights at
  strength 2.5, 3.5 and 4.0 alike. Masked out, the thigh comes back at
  134,131,134 against `grey pantyhose`'s own measured 135,127,128. Exact.
- **`set_cond_area: "mask bounds"` is not usable here.** It returned colour
  blocks and torn geometry; `"default"` is what works.

The masks are `assets/prone-thigh-mask.png` and `assets/prone-calf-mask.png`,
1536x1024, cut by colour from the settled first pass on seed 1886970040 and then
dilated and blurred hard so they survive the picture moving a little. They are
specific to that seed. On any other seed they are wrong, and the honest way to
get another one is to render it first and cut new masks from it.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

import yukari_recipe as yk
from comfy_host import DEFAULT_HOST, DEFAULT_PORT, stage_input

REPO = Path(__file__).resolve().parent.parent
INPUT_DIR = REPO / ".local/ComfyUI/input"
MASKS = {"thigh": REPO / "assets/prone-thigh-mask.png",
         "calf": REPO / "assets/prone-calf-mask.png"}

# The garment each region adds to the shared prompt. Weighted well above the
# recipe's usual 1.45 because a region is arguing with nothing -- the base is
# masked out of it -- and because the pale side of the palette wins ties here.
REGION = {
    "thigh": ("(grey pantyhose:1.9), (dark grey legwear:1.7), "
              "(charcoal pantyhose:1.5), (opaque pantyhose:1.5)"),
    "calf": "(white kneehighs:1.8), (white socks:1.6), (kneehighs:1.5)",
}


def legwear_block() -> str:
    """The legwear span `positive('prone')` builds, to cut it back out."""
    return (yk.LEGWEAR
            .replace("(grey pantyhose:1.45)", "(pale purple pantyhose:1.45)")
            .replace("(opaque pantyhose:1.3)", "(opaque pantyhose:1.5)")
            .replace("(very pale purple thighhighs:1.5)", "(white kneehighs:1.45)")
            .replace("(white thighhighs:1.2)", "(kneehighs:1.25)")
            .replace("(thighhighs over pantyhose:1.55)",
                     "(thighhighs over pantyhose:0.6)"))


def build(seed: int, prefix: str, hires: int, strength: float,
          host: str, port: int) -> dict:
    graph = yk.build("prone", seed, prefix, hires)

    block = legwear_block()
    base = yk.positive("prone").replace(block + ", ", "")
    if base == yk.positive("prone"):
        raise SystemExit("the legwear block no longer matches; update legwear_block()")
    graph["6"]["inputs"]["text"] = base

    combined = ["6", 0]
    mask_refs = []
    node = 20
    for name, path in MASKS.items():
        staged = stage_input(path, INPUT_DIR, host=host, port=port)
        load, tomask, encode, setmask, combine = (str(node + i) for i in range(5))
        graph[load] = {"class_type": "LoadImage", "inputs": {"image": staged}}
        graph[tomask] = {"class_type": "ImageToMask",
                         "inputs": {"image": [load, 0], "channel": "red"}}
        graph[encode] = {"class_type": "CLIPTextEncode",
                         "inputs": {"clip": ["4", 1],
                                    "text": f"{base}, {REGION[name]}"}}
        graph[setmask] = {"class_type": "ConditioningSetMask",
                          "inputs": {"conditioning": [encode, 0],
                                     "mask": [tomask, 0], "strength": strength,
                                     "set_cond_area": "default"}}
        graph[combine] = {"class_type": "ConditioningCombine",
                          "inputs": {"conditioning_1": combined,
                                     "conditioning_2": [setmask, 0]}}
        combined = [combine, 0]
        mask_refs.append([tomask, 0])
        node += 5

    # The base, masked to what the regions do not cover.
    graph["40"] = {"class_type": "MaskComposite",
                   "inputs": {"destination": mask_refs[0], "source": mask_refs[1],
                              "x": 0, "y": 0, "operation": "add"}}
    graph["41"] = {"class_type": "InvertMask", "inputs": {"mask": ["40", 0]}}
    graph["42"] = {"class_type": "ConditioningSetMask",
                   "inputs": {"conditioning": ["6", 0], "mask": ["41", 0],
                              "strength": 1.0, "set_cond_area": "default"}}
    graph["24"]["inputs"]["conditioning_1"] = ["42", 0]

    # Both passes sample against the same regional conditioning; the second one
    # would otherwise redraw the legs from the legwear-less base and undo it.
    for sampler in ("3", "11"):
        if sampler in graph:
            graph[sampler]["inputs"]["positive"] = combined
    return graph


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=1886970040,
                    help="the masks belong to this seed and no other")
    ap.add_argument("--hires", type=int, default=0)
    ap.add_argument("--strength", type=float, default=1.0,
                    help="1.0 and 1.5 both measured correct; 1.0 is cleaner")
    ap.add_argument("--prefix", default="ykprone-reg")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--print-prompt", action="store_true")
    args = ap.parse_args()

    if args.print_prompt:
        block = legwear_block()
        print(yk.positive("prone").replace(block + ", ", ""))
        for name, extra in REGION.items():
            print(f"\n--- {name} ---\n{extra}")
        return

    graph = build(args.seed, args.prefix, args.hires, args.strength,
                  args.host, args.port)
    req = urllib.request.Request(
        f"http://{args.host}:{args.port}/prompt",
        data=json.dumps({"prompt": graph}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(args.seed, json.load(resp)["prompt_id"])


if __name__ == "__main__":
    main()
