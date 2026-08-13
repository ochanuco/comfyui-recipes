#!/usr/bin/env python3
"""Yukari's settled recipe, and a seed sweep to check it stays settled.

This is `fb-b` (prompt id 4c012937), chosen after the design was restored from
gl-lounge-555666777 / job 38918ed3. Everything here is the reference's own
vocabulary; the port onto the Hamakaze graph is not part of it.

    uv run scripts/yukari_recipe.py --seeds 6          # sweep fresh seeds
    uv run scripts/yukari_recipe.py --seed 555666777   # the settled render
    uv run scripts/yukari_recipe.py --pose portrait    # head and shoulders
    uv run scripts/yukari_recipe.py --pose peace       # double v, v over eye

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

CHARACTER = (
    "yuzuki yukari, (light purple hair:1.25), (short hair with long locks:1.45), "
    "(very long sidelocks:1.3), sidelocks, (purple eyes:1.25), hair between eyes, "
    "hair ornament, (black hoodie:1.35), open hoodie, (rabbit hood:1.55), "
    # The hem does not respond to length tags. Asked to cover the buttocks, three
    # renders moved bare skin in the upper-leg band 37.4% -> 40.1% -> 38.3%:
    # (medium dress:1.3), then (medium dress:1.45) with (short dress:1.4),
    # (microdress:1.4) opposing it in the negative. All noise. `short dress` per
    # its wiki already spans "the middle of the thighs at the lowest to just
    # below the crotch and ass at the highest" and this sits at the top of that
    # range and stays there.
    #
    # The likely reason -- untested -- is that the costume comes from
    # `yuzuki yukari` itself rather than from these garment tags, so a length tag
    # is arguing with the character prior and losing. Lengthening it will need
    # something with more authority than a tag: a different garment noun, or
    # inpainting the hem.
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
    # `sticker` draws literal stickers -- a rabbit decal on her cheek in the
    # portrait, then rabbit patches and floating cut-outs around the figure --
    # and removing it also took the left/right sock mismatch from 15 to 4.
    # It is kept anyway: this block is pv1 (prompt 37ac6c0d), reverted to on
    # request after a run of single-tag corrections drifted the design. The
    # measurement is real and the tag is a known cost, not a mistake left in.
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
    # 1.2/1.5 measured sock saturation 22.9 against fb-b's 12.2, and 1.45/1.25
    # overshot to 8.7. Left at the first, because the second cost dress hue
    # (306 -> 280 against a 300 target) and whiteness is the cheaper of the two
    # to fix afterwards.
    #
    # The background moved too -- #d0d0c0, #a0a0a0, #909090 across 1.2/1.5,
    # 1.45/1.25 and 1.35/1.35 -- and the middle setting was the darkest of the
    # three. That is not these tags controlling it, it is the backdrop being
    # unstable under any small perturbation, which is already written down:
    # generate against whatever flat value turns up and set the real one with
    # scripts/recolor_bg.py --color. fb-b's is #d0d0c0.
    "(very pale purple thighhighs:1.5), (white thighhighs:1.2), "
    # over-kneehighs is OUT. This is lyC-555666777 (prompt 9d24700e), checked
    # afterwards across seven seeds: all seven put pale socks over black tights
    # on both legs, with the tights showing as a band at the top of the thigh.
    #
    # It was written up as the least consistent arm on the strength of a
    # left/right brightness difference that peaked at 73.9. That measure reads
    # pose and overlap, not sock length -- 737373737, reported here as having
    # lost a sock, has both -- and it had already been found unfit for judging
    # legwear one arm earlier. The number was wrong, not the recipe. Judge this
    # block by looking at it.
    "(lavender tint:1.3), "
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
    # Both hands making a V, one held over the eye and one arm thrown out
    # towards the camera. `double v` (42k posts) and `v over eye` (10k, "with
    # the eye between the fingers") are both real tags; the gesture is not
    # something a description of fingers would get.
    #
    # This is pv1 (prompt 37ac6c0d) exactly, reverted to on request. Nine tags.
    #
    # Trimming it was tried three ways and none of them held together. At eight
    # -- (outstretched arm:1.3) dropped -- the dress palette recovered (value
    # 116 -> 196) but the socks split left from right. At seven without
    # `legs to the side` the legwear came right and the colour count went 20 ->
    # 52, but rabbit cut-outs and a small second figure appeared. At seven
    # without `full body` instead, the leg mismatch went to its worst and the
    # frame cropped at the shins.
    #
    # So the count was never the variable, whatever the earlier notes here said:
    # two seven-tag blocks went opposite ways. What each individual tag holds is
    # the variable, and the nine together are what was actually wanted.
    #
    # (solo:1.5) stays at the head at exactly this weight -- measured, took
    # clones from 5-of-8 to 0-of-8.
    "peace": (
        "(solo:1.5), (yokozuwari:1.35), legs to the side, (double v:1.45), "
        "(v over eye:1.4), (outstretched arm:1.3), (smug:1.35), "
        "(half-closed eyes:1.3), full body"
    ),
}

# The portrait needs a square-ish frame: (portrait:1.5) alone lost to the canvas
# at 1024x1280 and drew down to the thighs. 1024x1024 held it.
SIZES = {"lounge": (1024, 1536), "portrait": (1024, 1024),
         "peace": (1024, 1536)}

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
    # All four asymmetry guards, as gl-lounge-555666777 carried them. Rebuilding
    # the legwear block had left only the first.
    #
    # Judged over four seeds, not one: restoring them raised the visible tights
    # band from a 7.7% worst case to 23.0%, so socks-over-tights now reads on
    # every seed tried rather than most of them. Worst case is the number that
    # matters here -- the mean barely moved.
    #
    # They do NOT fix left/right symmetry, which is what they were restored for:
    # mean leg difference went 11.0 -> 16.5. By eye both legs are correctly
    # layered in all four, so that measure is reading pose and overlap, not
    # sock length. It should not be used to judge legwear again.
    #
    # Dropping (over-kneehighs:1.4) alongside was tried and is much worse --
    # worst-case leg difference 73.9, with one sock nearly gone at 737373737.
    # Two competing length tags are apparently holding each other in place.
    "(mismatched legwear:1.5), (single thighhigh:1.5), "
    "(asymmetrical legwear:1.45), (uneven legwear:1.4), "
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
    # The legwear, body and thin-line blocks belong to whole-figure framings;
    # the portrait crops above them and naming what is out of frame is what
    # invites it back in.
    full_figure = pose != "portrait"
    parts = ["best quality, absurdres, 1girl, solo", CHARACTER, POSES[pose]]
    if full_figure:
        parts.append(LEGWEAR)
    parts += [FACE, SURFACE]
    parts.append(BODY if full_figure else "(pale skin:1.25)")
    parts.append(HOOD)
    if full_figure:
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
