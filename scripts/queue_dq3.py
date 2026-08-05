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
    "young woman, long legs, (thick thighs:1.5), (thick calves:1.4), "
    "soft calves, soft legs, smooth legs, "
    "(black pantyhose:1.4), sheer legwear, shiny legwear"
)

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
    # Half-lidded eyes plus a closed mouth are what carry this one: letting the
    # model smile drags the face straight back to its default. Both weights are
    # deliberately mild -- at 1.3 the eyes shut completely and the bangs cover
    # the visible eye, which loses the iris the look depends on.
    # Taken off ref-style3: large round gradient eyes, a closed-mouth smile and
    # heavy blush. The opposite end from "sharp" and "halflid" -- here the eyes
    # want to be as open and as tall as the model will draw them.
    # Steered onto a reference whose eyes carry a heavy dark upper lash line, a
    # vertical iris gradient and a large iris with a small pupil. gradient eyes
    # is back but mild -- at 1.4 alongside an eye LoRA it went rainbow.
    # Older-style eyes: tall and round, taking up a lot of the face, with the
    # outer corner clearly dropped. tareme and large eyes both needed weights --
    # unweighted they lost to the eye LoRA's modern shape.
    "moe": (
        "(tareme:1.6), drooping eyes, (large eyes:1.55), round eyes, wide eyes, "
        "2000s (style), (thick eyelashes:1.4), (dark eyelashes:1.3), long eyelashes, "
        "(gradient eyes:1.15), (detailed eyes:1.35), shiny eyes, "
        "highlights in eyes, reflective eyes, large pupils, "
        "thin eyebrows, light brown eyebrows, "
        "(light smile:1.2), closed mouth, small mouth, "
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
        "sage (dq3), (light blue hair:1.2), (medium hair:1.3), straight hair, (red eyes:1.3), "
        "(gold headband:1.3), blue gem, (cap sleeves:1.2), "
        "white dress, short dress, brown belt, (yellow elbow gloves:1.3), "
        "teal cape, teal scarf, (yellow boots:1.2), (holding staff:1.2), wooden staff"
    ),
    # (mini robe:1.3) is load-bearing: at full length the robe drapes over the
    # legs and the pantyhose comes out blotched with stray dark or light patches.
    "priest": (
        "priest (dq3), (light blue hair:1.2), (medium hair:1.3), red eyes, "
        "blue robe, (mini robe:1.3), thigh length robe, yellow cross, tall hat, "
        "yellow gloves, yellow boots, (holding staff:1.2), wooden staff"
    ),
    "mage": (
        "mage (dq3), (purple hair:1.2), (medium hair:1.3), "
        "(blue wizard hat:1.2), pointy hat, (yellow robe:1.2), short robe, blue cape, "
        "white belt, orange gloves, orange boots, (holding staff:1.2), wooden staff"
    ),
}

# Applied when --lora is not passed at all. Each entry carries the trigger word
# its LoRA expects, so callers do not have to remember them.
DEFAULT_LORAS = [
    ("perfect-eyes-ill.safetensors", 0.4, "perfect eyes"),
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
        "(cel shading:1.25), (flat color:1.2), "
        "(sharp shadow edges:1.35), two-tone shading, (shaded:1.15), "
        "(thin lineart:1.5), (black lineart:1.35), (detailed lineart:1.3), "
        "(cloth folds:1.45), (fabric folds:1.3), drapery, wrinkled clothes, taut clothes, (detailed clothes:1.2), "
        "(defined hair strands:1.35), separated hair strands, "
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

POSES = {
    "standing": (
        "standing, full body, looking at viewer, "
        "(simple background:1.3), (beige background:1.3), cream background, "
        "warm background, plain background"
    ),
    "sitting": (
        "sitting, knees up, one knee raised, from side, three quarter view, "
        "looking at viewer, full body, indoors, stone floor"
    ),
}

# Grouped so each block's purpose stays readable when tweaking one of them.
NEG_QUALITY = (
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text"
)
# The model renders skin and cloth as latex unless shine is pinned to the legwear.
NEG_SHINE = (
    "shiny skin, glossy skin, oily skin, sweat, shiny clothes, glossy clothes, latex, wet"
)
NEG_LEGS = (
    "bare legs, barefoot, thighhighs, skinny legs, thin legs, thin calves, "
    "muscular, muscular legs, muscular calves, veins, bony knees, defined knees, "
    "fat, obese, bbw, overweight, wide hips, huge ass, large ass, big butt, "
    "thick waist, short legs"
)
# Weighted: at plain strength the class tag still pulls in warrior gear.
NEG_GEAR = (
    "(sword:1.5), (katana:1.4), knife, dagger, axe, spear, bow, shield, "
    "(horns:1.5), (helmet:1.4), viking helmet, horned helmet, demon horns, antlers, "
    "armor, warrior, headgear, (headscarf:1.4), (hood:1.4), mitre, bishop hat, "
    "(bent staff:1.4), curved staff, broken staff, warped staff, bending"
)
# zoom layer / multiple views: detail LoRAs are trained on showcase images that
# park a huge close-up behind the figure, and they bring that layout with them.
NEG_FRAMING = (
    "cropped, head out of frame, close-up, lower body, feet focus, "
    "(zoom layer:1.4), (multiple views:1.3), inset, split screen, "
    "picture frame, eye focus, reference sheet"
)
NEG_ARTIFACT = ("long robe, floor length robe, patterned legwear, polka dot, spots, mottled, "
                "bare shoulders, off-shoulder, "
                "(torn clothes:1.2), damaged clothes, holes in clothes")
# IPAdapter at high weight hardens edges and bands the shading, which together
# read as late-90s toon-rendered CG. These pull back on both.
NEG_TOON = (
    "(thick outlines:1.5), (bold outline:1.4), (heavy lineart:1.4), thick lineart, "
    "(colored lineart:1.4), brown lineart, (light lineart:1.3), grey lineart, pale lineart, soft lineart, blurry lines, lineless, "
    "vector art, monochrome, sketch"
)
# The galge vocabulary tends to spend itself decorating the background with
# particles instead of changing how the figure is drawn.
NEG_BLUSH = "blush, nose blush, blush stickers, embarrassed, flustered"
NEG_EYECOLOR = ("(rainbow eyes:1.3), multicolored eyes, heterochromia, colored sclera, "
                "(tsurime:1.3), narrow eyes, small eyes, squinting")
NEG_SHADOW = "blurry shadow, soft shadow, gradient shadow"
NEG_CROWD = (
    "(multiple girls:1.4), (2girls:1.4), (multiple views:1.3), background character, "
    "crowd, silhouette, another person, extra person, doll, statue, poster, painting"
)
NEG_SPARKLE = (
    "(sparkle:1.25), (star (symbol):1.25), light particles, glitter, "
    "confetti, lens flare, floating particles, magic circle, starburst, twinkle"
)
NEG_MISC = ("3d, cgi, render, photorealistic, realistic, loli, child, mature female, milf, old, "
            "shounen (style), 1990s (style)")

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
    parts = [quality, "1girl, solo", CLASSES[args.job], "dragon quest iii, dragon quest",
             LEGS, POSES[args.pose]]
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

    prompt = {
        "4": loader,
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
                "positive": ["6", 0],
                "negative": ["7", 0],
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
    if not args.lora:
        args.lora = [name for name, _, _ in DEFAULT_LORAS]
        args.lora_strength = [strength for _, strength, _ in DEFAULT_LORAS]
        triggers = ", ".join(t for _, _, t in DEFAULT_LORAS if t)
        args.extra = ", ".join(p for p in (triggers, args.extra) if p)
    if args.negative is None:
        args.negative = NEGATIVE_PRESETS[args.negative_preset]


def main() -> int:
    args = parse_args()
    apply_defaults(args)
    if args.negative is None:
        args.negative = NEGATIVE_PRESETS[args.negative_preset]
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
