#!/usr/bin/env python3
"""Re-render an existing image at low denoise, with the prompt that made it.

A repaint from recolor_stripes.py is exact but flat: the new colour is pasted
into the old shading, so the boundary lines and the gloss belong to the colour
that used to be there. Sending it back through the sampler at a low denoise
redraws it as a picture rather than a paste-over.

The prompt is not retyped -- it is read out of /history for the prompt id that
produced the original, so the second pass agrees with the first about what it
is drawing. queue_img2img.py cannot do this: it loads a single-file checkpoint,
and Hassaku is only present in diffusers form.

    uv run scripts/queue_refine.py out/re-r80_00001_.png \\
        --from-prompt ce6963a6-... --denoise 0.3
"""

from __future__ import annotations

import argparse
import json
import shutil
import urllib.request
from pathlib import Path

from comfy_host import DEFAULT_HOST, DEFAULT_PORT

REPO = Path(__file__).resolve().parent.parent
INPUT_DIR = REPO / ".local/ComfyUI/input"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="image to refine")
    parser.add_argument(
        "--from-prompt",
        required=True,
        help="prompt id whose graph supplies the prompt, model and sampler",
    )
    parser.add_argument(
        "--mask",
        type=Path,
        help="white where the sampler may work. Without one the denoise has to "
        "stay low enough for the whole picture to survive it; with one the "
        "legwear can be redrawn hard while every other pixel is left alone",
    )
    # With a mask the second pass only touches one garment, so it can be told
    # something the first pass was not. The first pass's negative bans sheer
    # legwear, among much else; reusing it verbatim asks for see-through tights
    # while forbidding them.
    parser.add_argument("--positive-extra", default="", help="appended to the positive")
    # Appending is not enough when the second pass wants the opposite of the
    # first. Asking for bare legs while the inherited positive still says
    # (striped pantyhose:1.45) returns striped pantyhose, at any denoise.
    parser.add_argument("--positive", help="replaces the positive entirely")
    parser.add_argument("--negative", help="replaces the negative entirely")
    parser.add_argument("--denoise", type=float, default=0.3)
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--prefix", default="refine")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def fetch_graph(host: str, port: int, pid: str) -> dict:
    with urllib.request.urlopen(f"http://{host}:{port}/history/{pid}") as response:
        history = json.loads(response.read())
    if pid not in history:
        raise SystemExit(f"{pid} is not in history")
    return history[pid]["prompt"][2]


def find(graph: dict, class_type: str) -> tuple[str, dict]:
    for node_id, node in graph.items():
        if node.get("class_type") == class_type:
            return node_id, node
    raise SystemExit(f"no {class_type} in the source graph")


def main() -> None:
    args = parse_args()
    source = fetch_graph(args.host, args.port, args.from_prompt)

    sampler_id, sampler = find(source, "KSampler")
    positive_ref = sampler["inputs"]["positive"]
    negative_ref = sampler["inputs"]["negative"]
    positive = source[positive_ref[0]]["inputs"]["text"]
    negative = source[negative_ref[0]]["inputs"]["text"]
    if args.positive is not None:
        positive = args.positive
    if args.positive_extra:
        positive = f"{positive}, {args.positive_extra}"
    if args.negative is not None:
        negative = args.negative
    loader_id, loader = find(source, "DiffusersLoader")

    # ComfyUI's LoadImage only sees its own input directory.
    staged = INPUT_DIR / args.image.name
    if args.image.resolve() != staged.resolve():
        shutil.copy(args.image, staged)

    latent_ref = ["11", 0]
    mask_nodes: dict[str, dict] = {}
    if args.mask:
        staged_mask = INPUT_DIR / args.mask.name
        if args.mask.resolve() != staged_mask.resolve():
            shutil.copy(args.mask, staged_mask)
        mask_nodes = {
            "12": {"class_type": "LoadImage", "inputs": {"image": staged_mask.name}},
            "13": {
                "class_type": "ImageToMask",
                "inputs": {"image": ["12", 0], "channel": "red"},
            },
            "14": {
                "class_type": "SetLatentNoiseMask",
                "inputs": {"samples": ["11", 0], "mask": ["13", 0]},
            },
        }
        latent_ref = ["14", 0]

    seed = args.seed if args.seed is not None else sampler["inputs"]["seed"]
    graph = {
        **mask_nodes,
        "4": {"class_type": "DiffusersLoader", "inputs": dict(loader["inputs"])},
        "10": {"class_type": "LoadImage", "inputs": {"image": staged.name}},
        "11": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["10", 0], "vae": ["4", 2]},
        },
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["4", 1], "text": positive}},
        "7": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["4", 1], "text": negative}},
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": latent_ref,
                "seed": seed,
                "steps": args.steps,
                "cfg": sampler["inputs"]["cfg"],
                "sampler_name": sampler["inputs"]["sampler_name"],
                "scheduler": sampler["inputs"]["scheduler"],
                "denoise": args.denoise,
            },
        },
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0], "filename_prefix": args.prefix}},
    }

    body = json.dumps({"prompt": graph}).encode()
    request = urllib.request.Request(
        f"http://{args.host}:{args.port}/prompt",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        print(json.dumps(json.loads(response.read())))


if __name__ == "__main__":
    main()
