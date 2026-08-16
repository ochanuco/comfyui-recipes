#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import random
import urllib.error
import urllib.request

from comfy_host import DEFAULT_HOST, DEFAULT_PORT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Queue a minimal ComfyUI txt2img prompt through the local API."
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ckpt-name", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument(
        "--negative",
        default="blurry, smooth shading, gradient, anti-aliased, photorealistic",
    )
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--cfg", type=float, default=7.0)
    parser.add_argument("--sampler", default="euler")
    parser.add_argument("--scheduler", default="normal")
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--prefix", default="pixel-art")
    parser.add_argument("--lora-name")
    parser.add_argument("--strength-model", type=float, default=0.3)
    parser.add_argument("--strength-clip", type=float, default=0.3)
    return parser.parse_args()


def build_prompt(args: argparse.Namespace) -> dict[str, dict]:
    seed = args.seed if args.seed >= 0 else random.randint(0, 2**32 - 1)
    model_ref = ["4", 0]
    clip_ref = ["4", 1]
    prompt: dict[str, dict] = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": args.ckpt_name,
            },
        },
    }

    if args.lora_name:
        prompt["12"] = {
            "class_type": "LoraLoader",
            "inputs": {
                "model": ["4", 0],
                "clip": ["4", 1],
                "lora_name": args.lora_name,
                "strength_model": args.strength_model,
                "strength_clip": args.strength_clip,
            },
        }
        model_ref = ["12", 0]
        clip_ref = ["12", 1]

    prompt.update({
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "cfg": args.cfg,
                "denoise": 1,
                "latent_image": ["5", 0],
                "model": model_ref,
                "negative": ["7", 0],
                "positive": ["6", 0],
                "sampler_name": args.sampler,
                "scheduler": args.scheduler,
                "seed": seed,
                "steps": args.steps,
            },
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "batch_size": 1,
                "height": args.height,
                "width": args.width,
            },
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": clip_ref,
                "text": args.prompt,
            },
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": clip_ref,
                "text": args.negative,
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2],
            },
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": args.prefix,
                "images": ["8", 0],
            },
        },
    })
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


def main() -> int:
    args = parse_args()
    prompt = build_prompt(args)
    try:
        response = queue_prompt(args, prompt)
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"failed to reach ComfyUI at http://{args.host}:{args.port}: {exc}"
        ) from exc

    print(json.dumps({"seed": prompt["3"]["inputs"]["seed"], **response}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
