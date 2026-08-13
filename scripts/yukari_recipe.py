#!/usr/bin/env python3
"""Yukari's settled recipe, and a seed sweep to check it stays settled.

This is `fb-b` (prompt id 4c012937), chosen after the design was restored from
gl-lounge-555666777 / job 38918ed3. Everything here is the reference's own
vocabulary; the port onto the Hamakaze graph is not part of it.

    uv run scripts/yukari_recipe.py --seeds 6          # sweep fresh seeds
    uv run scripts/yukari_recipe.py --seed 555666777   # the settled render
    uv run scripts/yukari_recipe.py --pose portrait    # head and shoulders

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

CHARACTER = (
    "yuzuki yukari, (light purple hair:1.25), (short hair with long locks:1.45), "
    "(very long sidelocks:1.3), sidelocks, (purple eyes:1.25), hair between eyes, "
    "hair ornament, (black hoodie:1.35), open hoodie, (rabbit hood:1.55), "
    "animal hood, long sleeves, drawstring, (purple dress:1.2), short dress, "
    # Weighted down rather than deleted: the dress is meant to have frill trim,
    # it just should not be the loudest thing in the lower half.
    "(frills:0.85), vocaloid, voiceroid"
)

# rabbit print is deliberately absent: paired with `sticker` it drew a rabbit
# decal on her cheek in the 1024x1024 portrait. `sticker` earns its place --
# it is half of the white-outline idiom -- so the print is the one that goes.

FACE = (
    "(tareme:1.3), (large eyes:1.3), 2000s (style), eyelashes, "
    "(large iris:1.25), thin eyebrows, closed mouth, small mouth, "
    "looking at viewer"
)

SURFACE = (
    "(flat color:1.3), (simple background:1.3), (grey background:1.2), "
    "(white outline:1.6), outline, sticker, (soft shading:1.3), smooth shading"
)

BODY = (
    "(toned legs:1.2), (wide hips:1.3), (thick thighs:1.35), (narrow waist:1.25), "
    "(petite:1.2), (pale skin:1.25)"
)

HOOD = "(hood down:1.5), (hood behind head:1.3), (visible hair:1.2), (purple eyes:1.2)"

# Measured to do nothing to stroke width; present because fb-b carried them.
THIN = "(thin lineart:1.3), (fine lines:1.25), (delicate lines:1.2)"

# Pale thighhighs over opaque black tights. The layering failed before with
# (sheer black pantyhose:1.5) underneath -- the sheer tights vanished and left
# the socks alone. Solid black is a much stronger thing to ask for, so the pair
# gets another go rather than being abandoned.
#
# (lavender tint:1.3) and the pale sock colours are not only leg tags: dropping
# them took the whole palette darker and flatter, because they were where the
# pale cast came from.
#
# What did have to go is the see-through set -- (see-through pantyhose:1.45),
# (skin visible through pantyhose:1.4) never stayed on the legs and left the
# dress sheer over her stomach.
LEGWEAR = (
    "(black pantyhose:1.45), pantyhose, (opaque pantyhose:1.3), "
    # over-kneehighs ends just above the knee and, per its danbooru wiki, exists
    # to "leave a larger gap between the stocking and the skirt or dress" --
    # which is the shortening that was wanted. It is ADDED, not substituted:
    # swapping the whole block to over-kneehighs removed the socks entirely,
    # because `thighhighs over pantyhose` is a real tag carrying the layering
    # and `over-kneehighs over pantyhose` is a phrase that is not.
    "(very pale purple thighhighs:1.5), (white thighhighs:1.2), "
    "(over-kneehighs:1.4), (lavender tint:1.3), "
    "(thighhighs over pantyhose:1.55)"
)

POSES = {
    "lounge": (
        "(solo:1.5), (yokozuwari:1.35), sitting on floor, legs to the side, "
        "(arms behind head:1.3), (smug:1.35), (half-closed eyes:1.3), full body"
    ),
    "portrait": (
        "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), (close-up:1.2), "
        "(face focus:1.3), (smug:1.35), (half-closed eyes:1.3)"
    ),
}

# The portrait needs a square-ish frame: (portrait:1.5) alone lost to the canvas
# at 1024x1280 and drew down to the thighs. 1024x1024 held it.
SIZES = {"lounge": (1024, 1536), "portrait": (1024, 1024)}

NEGATIVE = (
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text, (disembodied eye:1.4), "
    "(brown legwear:1.5), brown thighhighs, brown pantyhose, (fishnet:1.4), "
    "(latex:1.45), (rubber:1.45), (leather legwear:1.45), "
    "(upskirt:1.4), panties, (from below:1.35), "
    "(blue legwear:1.5), (blue background:1.5), (blue tint:1.4), "
    # (opaque pantyhose:1.5) used to live here, from when the tights were meant
    # to be sheer. It is the direct opposite of the current ask and had to go.
    #
    # So did (thighhighs:1.4), (white legwear:1.4), which forbade the socks
    # outright -- they were added while abandoning the layering and are the
    # reason it could not come back.
    #
    # The sheer guard names the dress and nothing else. A four-tag block of
    # (see-through), (see-through clothes), (transparent clothing),
    # (sheer clothes) went in with it and the palette came back flat and dark,
    # which is the same shape as the duplicate-guard block that wrecked the
    # colours once before.
    # (thighhighs:1.3) was tried here to stop the socks creeping back to full
    # length. It removed them outright: the model does not hold thighhighs and
    # over-kneehighs apart, whatever the danbooru wiki separates. Length has to
    # come from the positive tag alone.
    "(mismatched legwear:1.5), "
    "(petticoat:1.35), (layered skirt:1.25), "
    "(see-through dress:1.45), (transparent clothing:1.3), "
    "(hood up:1.5), (hood over head:1.4), "
    "(impasto:1.25), (painterly:1.25), (oil painting (medium):1.2), "
    "(heavy shading:1.2), (detailed shading:1.2), (realistic:1.1), "
    "(huge breasts:1.4), (large breasts:1.25), cleavage"
)

# Fixed list rather than random: a sweep that cannot be repeated cannot be used
# to show that a later change did or did not break something.
SWEEP_SEEDS = [555666777, 111222333, 1886970040, 737373737, 2557902837, 3409564303]


def positive(pose: str) -> str:
    parts = ["best quality, absurdres, 1girl, solo", CHARACTER, POSES[pose]]
    if pose == "lounge":
        parts.append(LEGWEAR)
    parts += [FACE, SURFACE]
    if pose == "lounge":
        parts.append(BODY)
    else:
        parts.append("(pale skin:1.25)")
    parts.append(HOOD)
    if pose == "lounge":
        parts.append(THIN)
    return ", ".join(parts)


def build(pose: str, seed: int, prefix: str) -> dict:
    width, height = SIZES[pose]
    return {
        "4": {"class_type": "DiffusersLoader",
              "inputs": {"model_path": "hassaku-il-v22"}},
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"batch_size": 1, "width": width, "height": height}},
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["4", 1], "text": positive(pose)}},
        "7": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["4", 1], "text": NEGATIVE}},
        "3": {"class_type": "KSampler", "inputs": {
            "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["5", 0], "seed": seed, "steps": 30, "cfg": 5.0,
            "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode",
              "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0],
                         "filename_prefix": f"{prefix}-{pose}-{seed}"}},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pose", choices=sorted(POSES), default="lounge")
    parser.add_argument("--seed", type=int, action="append", default=[])
    parser.add_argument("--seeds", type=int, default=0,
                        help="take this many from the fixed sweep list")
    parser.add_argument("--prefix", default="yk")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8188)
    parser.add_argument("--print-prompt", action="store_true")
    args = parser.parse_args()

    if args.print_prompt:
        print(positive(args.pose), "\n\n---\n\n", NEGATIVE)
        return

    seeds = args.seed or SWEEP_SEEDS[:args.seeds] or [SWEEP_SEEDS[0]]
    for seed in seeds:
        req = urllib.request.Request(
            f"http://{args.host}:{args.port}/prompt",
            data=json.dumps({"prompt": build(args.pose, seed, args.prefix)}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(seed, json.load(resp)["prompt_id"], flush=True)


if __name__ == "__main__":
    main()
