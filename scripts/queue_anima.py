#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import random
import urllib.error
import urllib.request

from comfy_host import DEFAULT_HOST, DEFAULT_PORT

DEFAULT_NEGATIVE = (
    "worst quality, low quality, normal quality, score_1, score_2, score_3, "
    "blurry, jpeg artifacts, bad anatomy, bad hands, extra fingers, missing fingers, "
    "extra limbs, poorly drawn hands, watermark, signature, text, sepia"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Queue an Anima txt2img prompt through the local ComfyUI API."
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--negative", default=DEFAULT_NEGATIVE)
    parser.add_argument("--width", type=int, default=1216)
    parser.add_argument("--height", type=int, default=832)
    # Anima preview3 is not a distilled model: low steps or cfg 1.0 collapse the image.
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--cfg", type=float, default=4.0)
    parser.add_argument("--sampler", default="er_sde")
    parser.add_argument("--scheduler", default="simple")
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--prefix", default="anima")
    parser.add_argument("--unet-name", default="anima-preview3-base.safetensors")
    parser.add_argument("--clip-name", default="qwen_3_06b_base.safetensors")
    parser.add_argument("--vae-name", default="qwen_image_vae.safetensors")
    return parser.parse_args()


def build_prompt(args: argparse.Namespace) -> dict[str, dict]:
    seed = args.seed if args.seed >= 0 else random.randint(0, 2**32 - 1)
    return {
        "44": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": args.unet_name,
                "weight_dtype": "default",
            },
        },
        "45": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": args.clip_name,
                "type": "stable_diffusion",
                "device": "default",
            },
        },
        "15": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": args.vae_name,
            },
        },
        "11": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["45", 0],
                "text": args.prompt,
            },
        },
        "12": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["45", 0],
                "text": args.negative,
            },
        },
        "28": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": args.width,
                "height": args.height,
                "batch_size": 1,
            },
        },
        "19": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["44", 0],
                "positive": ["11", 0],
                "negative": ["12", 0],
                "latent_image": ["28", 0],
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
            "inputs": {
                "samples": ["19", 0],
                "vae": ["15", 0],
            },
        },
        "46": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["8", 0],
                "filename_prefix": args.prefix,
            },
        },
    }


def queue_prompt(args: argparse.Namespace, prompt: dict[str, dict]) -> dict:
    payload = json.dumps({"prompt": prompt}).encode("utf-8")
    req = urllib.request.Request(
        f"http://{args.host}:{args.port}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def main() -> int:
    args = parse_args()
    prompt = build_prompt(args)
    try:
        response = queue_prompt(args, prompt)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"ComfyUI rejected the prompt: {exc.read().decode()}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"failed to reach ComfyUI at http://{args.host}:{args.port}: {exc}"
        ) from exc

    print(json.dumps({"seed": prompt["19"]["inputs"]["seed"], **response}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
