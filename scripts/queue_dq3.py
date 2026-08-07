#!/usr/bin/env python3
"""Queue Dragon Quest III class portraits through the local ComfyUI API.

Wraps the novaAnimeXL recipe that was tuned interactively: black pantyhose with
a sheer/shiny finish, calves weighted up without widening the hips, and negative
prompts that keep the model from adding horned helmets, swords or glossy skin.
"""

from __future__ import annotations

import argparse
import json
import random
import time
import urllib.error
import urllib.request

# Body and legwear. Tuned so "thick" reads as soft tissue rather than muscle:
# muscular* in the negatives is what stops calves from turning sinewy, and the
# hip/ass negatives keep the extra volume in the legs instead of the pelvis.
LEGS = (
    "young woman, long legs, (thick thighs:1.6), (thick calves:1.4), (thick legs:1.15), "
    "soft calves, soft legs, smooth legs, "
    "(black pantyhose:1.75), (opaque legwear:1.45), (black legwear:1.3), nylon legwear, (taut clothes:1.35), (stretched fabric:1.25), (shiny legwear:1.4), (specular highlights:1.25), light streaks"
)

# Per class, because the weighted thighs above are a Dragon Quest choice and the
# legs negatives that support them rule out thighhighs entirely.
LEGS_BY_JOB = {
    "yukari": (
        "young woman, long legs, slender legs, "
        "(purple thighhighs:1.3), (zettai ryouiki:1.2), thighhighs"
    ),
}


QUALITY = "masterpiece, best quality, amazing quality, very aesthetic, absurdres"
# masterpiece and very aesthetic are Illustrious aesthetic-score tags: they buy
# polish at the cost of pulling every face toward the same averaged one.
QUALITY_PLAIN = "best quality, absurdres"

# Left unset the model emits its default face, which is what reads as generic.
# Eyebrows and eye size matter more than they look -- they are the parts the
# averaged face flattens hardest.
FACES = {
    "default": "",
    "sharp": (
        "(tsurime:1.2), narrow eyes, small eyes, (thick eyebrows:1.15), "
        "sharp chin, high cheekbones, small mouth, expressionless"
    ),
    "soft": (
        "(tareme:1.2), hooded eyes, round face, soft jawline, thin eyebrows, "
        "small mouth, light smile, (mole under eye:1.2)"
    ),
    "retro": (
        "retro artstyle, 1980s (style), (small eyes:1.2), thin eyebrows, "
        "sharp chin, narrow eyes, flat color"
    ),
    "freckled": (
        "(freckles:1.3), round face, (thick eyebrows:1.2), small eyes, "
        "wide nose, light smile, (mole under mouth:1.1)"
    ),
    # Rebuilt against ref-eye1 and ref-face2: tall round eyes with the outer
    # corner dropped, a deep blue iris, and lashes kept to a plain dark upper
    # line. The long/thick lash tags that used to be here drew fans of separate
    # hairs, which is busier than either reference. tareme and large eyes both
    # need weights -- unweighted they lose to the eye LoRA's own shape.
    "moe": (
        # The state that produced the preferred result. Later passes rebuilt it
        # against newer references -- round face, 2010s era, a reworked iris --
        # and every one of them drifted away from it; reverted wholesale.
        "(tareme:1.5), (large eyes:1.65), round eyes, "
        "2000s (style), eyelashes, (dark blue eyes:1.3), (large iris:1.6), "
        "thin eyebrows, (light smile:1.2), closed mouth, small mouth, "
        "soft expression, looking at viewer"
    ),
    # moe's weights assume the face fills a good part of the frame. In a
    # full-body standing shot it does not, and demanding a huge iris on a small
    # face has no solution -- the render comes back as coloured blocks. This is
    # the same intent at weights the distance can carry.
    "moe-far": (
        "(tareme:1.3), (large eyes:1.3), round eyes, "
        "2000s (style), eyelashes, (dark blue eyes:1.2), (large iris:1.25), "
        "thin eyebrows, light smile, closed mouth, small mouth, "
        "soft expression, looking at viewer"
    ),
    "halflid": (
        "(half-closed eyes:1.15), hooded eyes, tareme, eyeliner, thin eyebrows, "
        "swept bangs, side locks, "
        "sharp chin, small mouth, closed mouth, expressionless, "
        "(blush:1.25), nose blush"
    ),
}

# Per-class outfits follow the original Toriyama artwork: bare shoulders with
# elbow-length gloves, not the sleeved robe the bare class tag tends to produce.
CLASSES = {
    "sage": (
        # Eye colour is left to the face preset now, so the two cannot argue.
        "sage (dq3), (dark blue hair:1.5), (black hair:1.2), black tinted shadows, (medium hair:1.3), straight hair, "
        "(gold headband:1.3), blue gem, (tube top:1.35), strapless, bare shoulders, "
        "(plain white dress:1.35), white dress, (thigh length dress:1.3), (no pattern:1.2), brown belt, (yellow elbow gloves:1.3), "
        "teal cape, teal scarf, (yellow boots:1.2), (quarterstaff:1.35), plain wooden pole, holding pole"
    ),
    # (mini robe:1.3) is load-bearing: at full length the robe drapes over the
    # legs and the pantyhose comes out blotched with stray dark or light patches.
    "priest": (
        "priest (dq3), (light blue hair:1.2), (medium hair:1.3), red eyes, "
        "blue robe, (mini robe:1.3), thigh length robe, yellow cross, tall hat, "
        "yellow gloves, yellow boots, (holding staff:1.2), wooden staff"
    ),
    # Yukari's own tag carries her colouring; what needs spelling out is the
    # hooded outfit, since the tag alone returns her default costume.
    "yukari": (
        "yuzuki yukari, (light purple hair:1.25), (short hair with long locks:1.45), (very long sidelocks:1.3), sidelocks, "
        "(purple eyes:1.25), hair between eyes, hair ornament, "
        "(black hoodie:1.35), open hoodie, (rabbit hood:1.4), animal hood, "
        "(pink rabbit ears:1.3), fake animal ears, rabbit print, "
        "long sleeves, drawstring, (purple dress:1.2), short dress, frills"
    ),
    "mage": (
        "mage (dq3), (purple hair:1.2), (medium hair:1.3), "
        "(blue wizard hat:1.2), pointy hat, (yellow robe:1.2), short robe, blue cape, "
        "white belt, orange gloves, orange boots, (holding staff:1.2), wooden staff"
    ),
}

# Applied when --lora is not passed at all. Each entry carries the trigger word
# its LoRA expects, so callers do not have to remember them.
# Checkpoints that need ModelSamplingDiscrete. DiffusersLoader does not read the
# scheduler config, so this has to be stated somewhere, and the checkpoint knows
# it better than the caller does.
V_PRED_MODELS = {"moe-vpred-v2"}

DEFAULT_LORAS = [
    ("perfect-eyes-ill.safetensors", 0.7, "perfect eyes"),
    ("detailed-perfection-ill.safetensors", 0.5, "detailed"),
]

# Rendering, as opposed to FACES (features) and POSES (framing). Illustrious
# carries style mostly on artist tags, so these only approximate a look -- they
# get the gloss and the light right and leave the linework to the checkpoint.
STYLES = {
    "default": "",
    "glossy": (
        "(shiny hair:1.2), glossy hair, detailed hair, soft shading, "
        "smooth shading, detailed skin, sharp lineart, "
        "depth of field, blurry background, bokeh, soft lighting, "
        "warm lighting, backlighting, rim light"
    ),
    # Thin lines and gradients instead of sharp lineart. "subsurface scattering"
    # and "ambient occlusion" used to be here: they are 3D-render vocabulary this
    # model has no grounding for, and combined with a masked IPAdapter pass they
    # filled the unconstrained area with a rendered-looking panel.
    "painterly": (
        "(thin lineart:1.2), delicate lines, fine linework, "
        "(soft shading:1.2), smooth shading, gradient shading, "
        "(shiny hair:1.15), detailed hair, detailed skin, "
        "depth of field, blurry background, soft lighting"
    ),
    # Bishoujo-game CG: bloom, particles and jewel eyes. Pair it with
    # --negative-preset light, since the tuned negatives suppress exactly the
    # glow and contrast this look is made of.
    # "pastel colors" and a bare "gradient" used to be here and turned the
    # rendering chalky, like crayon. The light effects are weighted down too:
    # at 1.2 they spent themselves on the background instead of the figure.
    "rich": (
        "(detailed shading:1.35), volumetric lighting, rim light, "
        "(gradient shading:1.15), soft shadows, ambient light, "
        "(detailed skin:1.15), skin shading, (shiny hair:1.2), detailed hair, "
        "colorful, vivid colors, depth of field, "
        # Illustrious tints outlines to match the fill, which reads as soft and
        # machine-made; asking for thin black ink is what brings the drawn look.
        "(thin lineart:1.55), (fine linework:1.3), delicate lines, thin outlines, "
        "(black outline:1.4), (black lineart:1.3), (dark lineart:1.2), crisp lines, clean lineart, (defined hair strands:1.2), hair strand outline"
    ),
    # Flat colour with hard-edged shadow shapes, the opposite of "rich". Black
    # interior lines and cel shading reinforce each other; gradients fight them,
    # which is why mixing the two never looked right.
    "cel": (
        "(cel shading:1.5), (flat color:1.45), (limited palette:1.35), "
        "few colors, (anime screencap:1.15), "
        "(sharp shadow edges:1.45), (two-tone shading:1.35), "
        "(hard shadow edge:1.2), (dark shadows:1.3), deep shadow tone, "
        "(saturated colors:1.15), (shaded:1.25), "
        "(thin lineart:1.5), (black lineart:1.35), (simple lineart:1.2), "
        "simple clothes, (simple hair:1.2), hair as masses, "
        "clean lineart, crisp lines, simple shading, soft colors, "
        "(white outline:1.6), outline, sticker"
    ),
    "galge": (
        "(game cg:1.15), official art, visual novel cg, "
        "(detailed eyes:1.3), shiny eyes, "
        "(smooth shading:1.15), soft shading, cel shading, clean lineart, "
        "shiny hair, detailed skin, soft lighting, depth of field"
    ),
}

# Kept beside CLASSES rather than hardcoded into the prompt: it anchors the
# palette for the Dragon Quest classes, and would poison anything else.
# The moe face carries weights pushed to their limit for the sage; stacked on
# another character's tag the prompt stops resolving and the render turns to
# noise. Classes can name a face that suits them instead.
FACE_BY_JOB = {"yukari": "default"}

# Framings where the face is too small to carry moe's weights.
FACE_BY_POSE: dict[str, str] = {}

FRANCHISE = {
    "sage": "dragon quest iii, dragon quest",
    "priest": "dragon quest iii, dragon quest",
    "mage": "dragon quest iii, dragon quest",
    "yukari": "vocaloid, voiceroid",
}

# Individual terms a class has to remove from the assembled negative. Dropping a
# whole block was tried first and wrecked the render: the blocks carry more than
# their name suggests, and losing the rest of NEG_GEAR made the image melt.
NEG_DROP = {
    "yukari": ["(hood:1.4)", "headgear", "(headscarf:1.4)",
               "thighhighs", "skinny legs", "thin legs", "thin calves"],
}

# Same idea for poses. bootoff puts the feet toward the camera on purpose, which
# the default framing negatives rule out; the upskirt terms stay in place.
# Class tags a pose has to give up. reaching wants both hands open and empty.
POSE_TAG_DROP = {"reaching": ["(quarterstaff:1.35)", "plain wooden pole", "holding pole"]}

POSE_NEG_DROP = {
    "bootoff": ["feet focus", "lower body"],
    "kneesup": ["feet focus", "lower body"],
}

# Appended to every pose. A scene gives the eye tags somewhere to put an extra
# eye -- a balcony backdrop grew a shadow creature with a fully drawn iris -- and
# a flat field leaves them nothing to latch onto.
# Weights are pitched for moe-vpred-v2, which needs more push than Amanatsu did
# before the backdrop goes properly flat.
BACKGROUND = (
    "(simple background:1.4), (grey background:1.35), plain background, "
    "flat background, no scenery"
)

POSES = {
    "standing": "standing, full body, looking at viewer",
    "sitting": (
        "sitting, knees up, one knee raised, from side, three quarter view, "
        "looking at viewer, full body"
    ),
    # Arms thrown out towards the camera, leaning in. The reference this came
    # from frames it from low enough to look up the skirt; the framing tags keep
    # the shot on the upper body instead.
    "reaching": (
        "(outstretched arms:1.4), reaching towards viewer, (leaning forward:1.25), "
        "open hands, spread fingers, looking at viewer, open mouth, smile, "
        "(upper body:1.2), (medium breasts:1.2), dutch angle"
    ),
    # Knees drawn up together with the feet toward the camera and a hand at the
    # legwear. Taken off ref-pose-kneesup.
    "kneesup": (
        "sitting, (knees up:1.4), knees together, legs together, legs raised, "
        "feet up, (soles:1.25), (foreshortening:1.3), perspective, (large feet:1.2), (adjusting legwear:1.3), hand on own leg, "
        "head tilt, looking at viewer, full body"
    ),
    # Sitting back with the knees up, one boot off and held. The reference this
    # came from shoots from low enough to put the crotch in frame; that half is
    # left out, and the framing negatives keep it out.
    "bootoff": (
        "sitting, leaning back, (knees up:1.3), legs raised, "
        "(holding boot:1.4), single boot removed, undressing, "
        "(soles:1.2), feet up, looking at viewer, "
        "(black pantyhose:1.35), full body"
    ),
    # Side-sitting with the torso turned away and the head looking back. The
    # balcony it came from is dropped along with every other backdrop.
    "lookback": (
        "(yokozuwari:1.35), sitting on floor, legs to the side, "
        "(looking back:1.4), looking at viewer, from behind, from side, "
        "full body, head tilt, (medium breasts:1.2)"
    ),
}

# Grouped so each block's purpose stays readable when tweaking one of them.
NEG_QUALITY = (
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text, "
    "(washed out:1.3), (overexposed:1.3), (pale skin:1.3)"
)
NEG_SHINE = "shiny skin, oily skin, sweat, (latex:1.3), (rubber:1.3)"
NEG_LEGS = (
    "bare legs, barefoot, thighhighs, thin legs, muscular legs, bony knees, "
    "(grey legwear:1.4), (sheer legwear:1.3), see-through legwear, pale legwear, "
    "obese, wide hips, huge ass, short legs"
)
NEG_GEAR = (
    "(sword:1.4), knife, axe, spear, shield, (horns:1.4), (helmet:1.4), "
    "armor, warrior, headgear, (hood:1.4), mitre"
)
NEG_DISTORT = ("(warped:1.3), melting, distorted, deformed, (bent staff:1.3), "
               "(thick staff:1.4), oversized staff, club, mace, "
               "(ornate staff:1.4), decorated staff")
NEG_FRAMING = (
    "cropped, head out of frame, close-up, lower body, feet focus, "
    "(upskirt:1.4), panties, (from below:1.2), (zoom layer:1.4), multiple views"
)
NEG_ARTIFACT = (
    "long robe, patterned legwear, spots, mottled, (torn clothes:1.2), "
    "(microskirt:1.4), exposed buttocks, (emblem:1.4), (logo:1.4), chest print, "
    "(wrinkled clothes:1.2), busy details"
)
NEG_TOON = (
    "(thick outlines:1.4), heavy lineart, (colored lineart:1.4), (light lineart:1.3), "
    "pale lineart, lineless, monochrome, sketch, (intricate:1.3), (highly detailed:1.3)"
)
NEG_SPARKLE = "(sparkle:1.25), (star (symbol):1.25), light particles, lens flare, glitter"
NEG_BLUSH = "blush, nose blush, embarrassed"
NEG_BREASTS = "(huge breasts:1.4), (large breasts:1.25), cleavage"
NEG_CROWD = (
    "(multiple girls:1.4), background character, crowd, (dark figure:1.3), "
    "(dark shape:1.3), stray object, (disembodied eye:1.4), (monster:1.4)"
)
NEG_EYECOLOR = (
    "(rainbow eyes:1.3), heterochromia, (tsurime:1.3), (small eyes:1.4), "
    "(sanpaku:1.5), (constricted pupils:1.4), (visible sclera:1.4)"
)
NEG_GREEN = ("(green hair:1.5), mint hair, (yellow-green:1.4), lime, (yellow background:1.4), "
             "(light blue hair:1.4), (purple hair:1.4), silver hair, white hair")
NEG_SHADOW = "(cast shadow:1.5), (shadow on ground:1.45), soft shadow, gradient shadow"
NEG_MISC = (
    "3d, cgi, render, photorealistic, loli, child, mature female, old, "
    "(gradient shading:1.4), airbrush, smooth shading, (many colors:1.3)"
)

NEG_BLOCKS = {
    "quality": NEG_QUALITY, "shine": NEG_SHINE, "legs": NEG_LEGS, "gear": NEG_GEAR,
    "framing": NEG_FRAMING, "artifact": NEG_ARTIFACT, "toon": NEG_TOON,
    "distort": NEG_DISTORT,
    "sparkle": NEG_SPARKLE, "blush": NEG_BLUSH, "crowd": NEG_CROWD,
    "eyecolor": NEG_EYECOLOR, "green": NEG_GREEN,
    "shadow": NEG_SHADOW, "breasts": NEG_BREASTS,
    "misc": NEG_MISC,
}
FULL_ORDER = ["quality", "shine", "legs", "gear", "distort", "framing", "artifact",
              "toon", "sparkle", "blush", "crowd", "eyecolor", "green",
              "shadow", "breasts", "misc"]
LIGHT_ORDER = [b for b in FULL_ORDER if b not in ("shine", "toon")]


def build_negative(preset: str, job: str, pose: str = "") -> str:
    order = FULL_ORDER if preset == "full" else LIGHT_ORDER
    terms = [t.strip() for b in order for t in NEG_BLOCKS[b].split(",")]
    drop = set(NEG_DROP.get(job, [])) | set(POSE_NEG_DROP.get(pose, []))
    return ", ".join(t for t in terms if t and t not in drop)


DEFAULT_NEGATIVE = ", ".join(
    [NEG_QUALITY, NEG_SHINE, NEG_LEGS, NEG_GEAR, NEG_FRAMING, NEG_ARTIFACT,
     NEG_TOON, NEG_SPARKLE, NEG_BLUSH, NEG_CROWD, NEG_EYECOLOR, NEG_SHADOW, NEG_MISC]
)
# Drops NEG_SHINE and NEG_TOON: between them they suppress glossy skin, bloom
# and contrast, which is most of what makes a rendering read as game CG. Keeps
# the blocks that guard anatomy, the outfit and the framing.
LIGHT_NEGATIVE = ", ".join(
    [NEG_QUALITY, NEG_LEGS, NEG_GEAR, NEG_FRAMING, NEG_ARTIFACT, NEG_SPARKLE, NEG_BLUSH, NEG_CROWD, NEG_EYECOLOR, NEG_SHADOW, NEG_MISC]
)
NEGATIVE_PRESETS = {"full": DEFAULT_NEGATIVE, "light": LIGHT_NEGATIVE}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Queue a Dragon Quest III class portrait through the local ComfyUI API."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8188)
    parser.add_argument("--job", choices=sorted(CLASSES), default="sage")
    parser.add_argument("--pose", choices=sorted(POSES), default="standing")
    parser.add_argument("--face", choices=sorted(FACES), default="moe")
    parser.add_argument("--style", choices=sorted(STYLES), default="cel")
    parser.add_argument(
        "--plain-quality",
        action="store_true",
        help="drop the aesthetic-score tags that flatten faces toward one look",
    )
    parser.add_argument("--extra", default="", help="appended to the positive prompt")
    parser.add_argument("--negative")
    parser.add_argument(
        "--negative-preset", choices=sorted(NEGATIVE_PRESETS), default="full"
    )
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--cfg", type=float, default=5.0)
    parser.add_argument("--sampler", default="dpmpp_2m")
    parser.add_argument("--scheduler", default="karras")
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--prefix")
    parser.add_argument("--ckpt-name", default="novaAnimeXL_ilV170.safetensors")
    # Many Civitai checkpoints are only mirrored in diffusers layout, which
    # CheckpointLoaderSimple cannot read. DiffusersLoader returns the same
    # MODEL/CLIP/VAE triple, so the rest of the graph is unchanged.
    parser.add_argument(
        "--diffusers-path",
        default="amanatsu-il-v11",
        help="subdirectory under assets/diffusers; pass '' to fall back to --ckpt-name",
    )
    # Structure, as opposed to IPAdapter's --ref-image, which carries style.
    # Canny is the only preprocessor ComfyUI ships, so the trace goes through it.
    parser.add_argument(
        "--trace-image",
        help="filename under input/ whose outlines constrain the composition",
    )
    parser.add_argument("--trace-strength", type=float, default=0.6)
    parser.add_argument("--trace-start", type=float, default=0.0)
    # Releasing it partway lets the trace set the structure and leaves the detail
    # to the prompt; held to the end it reproduces the reference outright.
    parser.add_argument("--trace-end", type=float, default=0.5)
    parser.add_argument("--trace-low", type=float, default=0.2)
    parser.add_argument("--trace-high", type=float, default=0.6)
    parser.add_argument("--controlnet-name", default="noob-canny-fp16.safetensors")
    parser.add_argument(
        "--v-pred",
        action="store_true",
        help="checkpoint is v-prediction (NoobAI vpred and similar)",
    )
    # Repeatable: --lora a.safetensors --lora b.safetensors chains them.
    parser.add_argument(
        "--lora",
        action="append",
        default=[],
        metavar="NAME",
        help="LoRA filename under assets/loras; repeat to stack several",
    )
    parser.add_argument(
        "--lora-strength",
        action="append",
        type=float,
        default=[],
        help="strength for the matching --lora (default 0.8 each)",
    )
    parser.add_argument(
        "--ref-image",
        help="filename under .local/ComfyUI/input to steer the look through IPAdapter",
    )
    parser.add_argument("--ref-weight", type=float, default=1.0)
    # "style transfer" leaves composition alone; plain "linear" drags the
    # reference's subject and colours in with it.
    parser.add_argument("--ref-type", default="style transfer")
    parser.add_argument(
        "--ref-mask",
        help="greyscale image under input/ limiting where this reference applies",
    )
    # A second pass so one reference can steer the face while another steers the
    # legwear, instead of one reference repainting the whole outfit.
    parser.add_argument("--ref2-image")
    parser.add_argument("--ref2-mask")
    parser.add_argument("--ref2-weight", type=float, default=1.0)
    parser.add_argument("--ref2-type", default="style transfer")
    parser.add_argument("--ref2-start", type=float, default=0.0)
    parser.add_argument("--ref2-end", type=float, default=1.0)
    # "V only" is the strongest and the quickest to harden edges. The C penalty
    # variants trade some of the reference's influence for a softer result.
    parser.add_argument(
        "--ref-scaling",
        default="V only",
        choices=["V only", "K+V", "K+V w/ C penalty", "K+mean(V) w/ C penalty"],
    )
    # Sampling window. Releasing the reference partway (--ref-end 0.4) lets it
    # shape the rendering while the prompt's own colours reassert afterwards,
    # which is the way to apply it unmasked without the palette going warm.
    parser.add_argument("--ref-start", type=float, default=0.0)
    parser.add_argument("--ref-end", type=float, default=1.0)
    parser.add_argument("--ipadapter-file", default="ip-adapter-plus_sdxl_vit-h.safetensors")
    parser.add_argument(
        "--clip-vision-name", default="CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
    )
    parser.add_argument("--wait", action="store_true", help="poll until the images are written")
    return parser.parse_args(argv)


def parse_args_from(argv: list[str]) -> argparse.Namespace:
    """Same parser, for wrappers that forward a subset of flags."""
    return parse_args(argv)


def build_positive(args: argparse.Namespace) -> str:
    quality = QUALITY_PLAIN if getattr(args, "plain_quality", False) else QUALITY
    class_tags = CLASSES[args.job]
    for tag in POSE_TAG_DROP.get(args.pose, []):
        class_tags = class_tags.replace(tag + ", ", "").replace(", " + tag, "")
    parts = [quality, "1girl, solo", class_tags]
    franchise = FRANCHISE.get(args.job)
    if franchise:
        parts.append(franchise)
    parts += [LEGS_BY_JOB.get(args.job, LEGS), POSES[args.pose], BACKGROUND]
    face = FACES[getattr(args, "face", "default")]
    if face:
        parts.append(face)
    style = STYLES[getattr(args, "style", "default")]
    if style:
        parts.append(style)
    if args.extra:
        parts.append(args.extra)
    return ", ".join(parts)


def build_prompt(args: argparse.Namespace, seed: int, prefix: str) -> dict[str, dict]:
    diffusers_path = getattr(args, "diffusers_path", None)
    loader = (
        {"class_type": "DiffusersLoader", "inputs": {"model_path": diffusers_path}}
        if diffusers_path
        else {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": args.ckpt_name}}
    )

    # LoRAs sit between the loader and everything downstream, so the rest of the
    # graph keeps pointing at one node id whether or not any are stacked.
    model_src, clip_src = ["4", 0], ["4", 1]

    # v-prediction checkpoints need saying so. DiffusersLoader does not read the
    # scheduler config, so without this the image comes out as noise or a flat
    # field -- which is at least an unmistakable failure.
    sampling_nodes: dict[str, dict] = {}
    if getattr(args, "v_pred", False):
        sampling_nodes["59"] = {
            "class_type": "ModelSamplingDiscrete",
            "inputs": {"model": model_src, "sampling": "v_prediction", "zsnr": True},
        }
        model_src = ["59", 0]

    lora_nodes: dict[str, dict] = {}
    for index, lora_name in enumerate(getattr(args, "lora", []) or []):
        strengths = getattr(args, "lora_strength", []) or []
        strength = strengths[index] if index < len(strengths) else 0.8
        node = str(60 + index)
        lora_nodes[node] = {
            "class_type": "LoraLoader",
            "inputs": {
                "model": model_src,
                "clip": clip_src,
                "lora_name": lora_name,
                "strength_model": strength,
                "strength_clip": strength,
            },
        }
        model_src, clip_src = [node, 0], [node, 1]

    positive_src, negative_src = ["6", 0], ["7", 0]
    trace_nodes: dict[str, dict] = {}
    trace_image = getattr(args, "trace_image", None)
    if trace_image:
        trace_nodes["70"] = {"class_type": "LoadImage", "inputs": {"image": trace_image}}
        trace_nodes["71"] = {
            "class_type": "Canny",
            "inputs": {
                "image": ["70", 0],
                "low_threshold": args.trace_low,
                "high_threshold": args.trace_high,
            },
        }
        trace_nodes["72"] = {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": args.controlnet_name},
        }
        trace_nodes["73"] = {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["6", 0],
                "negative": ["7", 0],
                "control_net": ["72", 0],
                "image": ["71", 0],
                "strength": args.trace_strength,
                "start_percent": args.trace_start,
                "end_percent": args.trace_end,
            },
        }
        positive_src, negative_src = ["73", 0], ["73", 1]

    prompt = {
        "4": loader,
        **trace_nodes,
        **sampling_nodes,
        **lora_nodes,
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": clip_src, "text": build_positive(args)},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": clip_src, "text": args.negative},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"batch_size": 1, "width": args.width, "height": args.height},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "model": model_src,
                "positive": positive_src,
                "negative": negative_src,
                "latent_image": ["5", 0],
                "seed": seed,
                "steps": args.steps,
                "cfg": args.cfg,
                "sampler_name": args.sampler,
                "scheduler": args.scheduler,
                "denoise": 1,
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"images": ["8", 0], "filename_prefix": prefix},
        },
    }

    g = lambda name, default=None: getattr(args, name, default)
    passes = [
        {
            "image": g(f"{p}image"),
            "mask": g(f"{p}mask"),
            "weight": g(f"{p}weight", 1.0),
            "weight_type": g(f"{p}type", "style transfer"),
            "start_at": g(f"{p}start", 0.0),
            "end_at": g(f"{p}end", 1.0),
        }
        for p in ("ref_", "ref2_")
    ]
    passes = [p for p in passes if p["image"]]

    if passes:
        prompt["31"] = {
            "class_type": "IPAdapterModelLoader",
            "inputs": {"ipadapter_file": args.ipadapter_file},
        }
        prompt["32"] = {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": args.clip_vision_name},
        }

        # Passes chain model-to-model, so each one narrows what the next sees.
        model_ref = model_src
        node_id = 40
        for spec in passes:
            image_id, node_id = str(node_id), node_id + 1
            prompt[image_id] = {
                "class_type": "LoadImage",
                "inputs": {"image": spec["image"]},
            }

            inputs = {
                "model": model_ref,
                "ipadapter": ["31", 0],
                "image": [image_id, 0],
                "clip_vision": ["32", 0],
                "weight": spec["weight"],
                "weight_type": spec["weight_type"],
                "combine_embeds": "concat",
                "start_at": spec["start_at"],
                "end_at": spec["end_at"],
                "embeds_scaling": g("ref_scaling", "V only"),
            }

            mask = spec["mask"]
            if mask:
                mask_image_id, node_id = str(node_id), node_id + 1
                mask_id, node_id = str(node_id), node_id + 1
                prompt[mask_image_id] = {
                    "class_type": "LoadImage",
                    "inputs": {"image": mask},
                }
                prompt[mask_id] = {
                    "class_type": "ImageToMask",
                    "inputs": {"image": [mask_image_id, 0], "channel": "red"},
                }
                inputs["attn_mask"] = [mask_id, 0]

            ipadapter_id, node_id = str(node_id), node_id + 1
            prompt[ipadapter_id] = {"class_type": "IPAdapterAdvanced", "inputs": inputs}
            model_ref = [ipadapter_id, 0]

        prompt["3"]["inputs"]["model"] = model_ref

    return prompt


def queue_prompt(args: argparse.Namespace, prompt: dict[str, dict]) -> dict:
    payload = json.dumps({"prompt": prompt}).encode("utf-8")
    req = urllib.request.Request(
        f"http://{args.host}:{args.port}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def wait_for(args: argparse.Namespace, prompt_ids: list[str]) -> None:
    pending = list(prompt_ids)
    while pending:
        time.sleep(10)
        for pid in list(pending):
            url = f"http://{args.host}:{args.port}/history/{pid}"
            with urllib.request.urlopen(url) as response:
                history = json.loads(response.read())
            if not history:
                continue
            pending.remove(pid)
            for entry in history.values():
                for output in entry.get("outputs", {}).values():
                    for image in output.get("images", []):
                        print(f"done {pid} -> {image['filename']}")


def apply_defaults(args: argparse.Namespace) -> None:
    """Fill in the settled recipe for anything the caller left alone."""
    if getattr(args, "diffusers_path", None) in V_PRED_MODELS:
        args.v_pred = True
    if args.face == "moe" and args.job in FACE_BY_JOB:
        args.face = FACE_BY_JOB[args.job]
    elif args.face == "moe" and args.pose in FACE_BY_POSE:
        args.face = FACE_BY_POSE[args.pose]
    if not args.lora:
        args.lora = [name for name, _, _ in DEFAULT_LORAS]
        args.lora_strength = [strength for _, strength, _ in DEFAULT_LORAS]
        triggers = ", ".join(t for _, _, t in DEFAULT_LORAS if t)
        args.extra = ", ".join(p for p in (triggers, args.extra) if p)
    if args.negative is None:
        args.negative = build_negative(args.negative_preset, args.job, args.pose)


def main() -> int:
    args = parse_args()
    apply_defaults(args)
    if args.negative is None:
        args.negative = build_negative(args.negative_preset, args.job, args.pose)
    prefix = args.prefix or f"dq3-{args.job}-{args.pose}"
    prompt_ids = []

    for index in range(args.count):
        seed = args.seed if args.seed >= 0 else random.randint(0, 2**32 - 1)
        if args.seed >= 0 and args.count > 1:
            seed += index
        prompt = build_prompt(args, seed, prefix)
        try:
            response = queue_prompt(args, prompt)
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"ComfyUI rejected the prompt: {exc.read().decode()}") from exc
        except urllib.error.URLError as exc:
            raise SystemExit(
                f"failed to reach ComfyUI at http://{args.host}:{args.port}: {exc}"
            ) from exc
        prompt_ids.append(response["prompt_id"])
        print(json.dumps({"seed": seed, **response}, ensure_ascii=True))

    if args.wait:
        wait_for(args, prompt_ids)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
