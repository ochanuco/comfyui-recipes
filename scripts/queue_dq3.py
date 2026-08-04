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
    "young woman, long legs, (thick thighs:1.15), (thick calves:1.4), "
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
        "sage (dq3), (light blue hair:1.2), (medium hair:1.3), straight hair, red eyes, "
        "(gold headband:1.3), blue gem, (bare shoulders:1.2), sleeveless, "
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
    # Same gloss, but asking for thin lines and gradients instead of sharp
    # lineart -- the combination that stops it reading as toon-rendered CG.
    "painterly": (
        "(thin lineart:1.2), delicate lines, fine linework, "
        "(soft shading:1.2), smooth shading, gradient shading, subsurface scattering, "
        "(shiny hair:1.15), detailed hair, detailed skin, "
        "depth of field, blurry background, soft lighting, ambient occlusion"
    ),
}

POSES = {
    "standing": "standing, full body, looking at viewer, simple background",
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
    "armor, warrior, headgear, (headscarf:1.4), (hood:1.4), mitre, bishop hat"
)
NEG_FRAMING = "cropped, head out of frame, close-up, lower body, feet focus"
NEG_ARTIFACT = "long robe, floor length robe, patterned legwear, polka dot, spots, mottled"
# IPAdapter at high weight hardens edges and bands the shading, which together
# read as late-90s toon-rendered CG. These pull back on both.
NEG_TOON = (
    "(thick outlines:1.3), bold outline, heavy lineart, thick lineart, "
    "cel shading, toon shading, flat shading, posterization, vector art, "
    "hard shadows, high contrast"
)
NEG_MISC = "3d, cgi, render, photorealistic, realistic, loli, child, mature female, milf, old"

DEFAULT_NEGATIVE = ", ".join(
    [NEG_QUALITY, NEG_SHINE, NEG_LEGS, NEG_GEAR, NEG_FRAMING, NEG_ARTIFACT,
     NEG_TOON, NEG_MISC]
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Queue a Dragon Quest III class portrait through the local ComfyUI API."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8188)
    parser.add_argument("--job", choices=sorted(CLASSES), default="sage")
    parser.add_argument("--pose", choices=sorted(POSES), default="standing")
    parser.add_argument("--face", choices=sorted(FACES), default="default")
    parser.add_argument("--style", choices=sorted(STYLES), default="default")
    parser.add_argument(
        "--plain-quality",
        action="store_true",
        help="drop the aesthetic-score tags that flatten faces toward one look",
    )
    parser.add_argument("--extra", default="", help="appended to the positive prompt")
    parser.add_argument("--negative", default=DEFAULT_NEGATIVE)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--width", type=int, default=832)
    parser.add_argument("--height", type=int, default=1216)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--cfg", type=float, default=5.0)
    parser.add_argument("--sampler", default="euler_ancestral")
    parser.add_argument("--scheduler", default="normal")
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--prefix")
    parser.add_argument("--ckpt-name", default="novaAnimeXL_ilV170.safetensors")
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
    # "V only" is the strongest and the quickest to harden edges. The C penalty
    # variants trade some of the reference's influence for a softer result.
    parser.add_argument(
        "--ref-scaling",
        default="V only",
        choices=["V only", "K+V", "K+V w/ C penalty", "K+mean(V) w/ C penalty"],
    )
    parser.add_argument("--ipadapter-file", default="ip-adapter-plus_sdxl_vit-h.safetensors")
    parser.add_argument(
        "--clip-vision-name", default="CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
    )
    parser.add_argument("--wait", action="store_true", help="poll until the images are written")
    return parser.parse_args()


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
    prompt = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": args.ckpt_name},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["4", 1], "text": build_positive(args)},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["4", 1], "text": args.negative},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"batch_size": 1, "width": args.width, "height": args.height},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["4", 0],
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
        (g("ref_image"), g("ref_mask"), g("ref_weight", 1.0), g("ref_type", "style transfer")),
        (g("ref2_image"), g("ref2_mask"), g("ref2_weight", 1.0), g("ref2_type", "style transfer")),
    ]
    passes = [p for p in passes if p[0]]

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
        model_ref = ["4", 0]
        node_id = 40
        for image, mask, weight, weight_type in passes:
            image_id, node_id = str(node_id), node_id + 1
            prompt[image_id] = {"class_type": "LoadImage", "inputs": {"image": image}}

            inputs = {
                "model": model_ref,
                "ipadapter": ["31", 0],
                "image": [image_id, 0],
                "clip_vision": ["32", 0],
                "weight": weight,
                "weight_type": weight_type,
                "combine_embeds": "concat",
                "start_at": 0.0,
                "end_at": 1.0,
                "embeds_scaling": g("ref_scaling", "V only"),
            }

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


def main() -> int:
    args = parse_args()
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
