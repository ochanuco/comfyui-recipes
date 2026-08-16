#!/usr/bin/env python3
"""Second style sweep for Hamakaze: push the art style further than sw-lora-outlined-ill.

The first sweep (sw-base-*, sw-lora-*) varied one base or one LoRA at 0.8 and
never passed a trigger word, so the LoRAs that carry their style on a token --
usnr-style-ill-v1 ("usnr"), mozudoll ("cheeky (mozudoll)") -- were only ever
half applied. This sweep fixes that, walks outlined-ill past 0.8, and stacks it
with the retro LoRAs. Everything else (seed, prompt, sampler, size) is held from
the accepted run 21ea087e so only the style axis moves.

That base is not retyped here. It is read out of /history for the prompt id that
produced the accepted render, the way queue_refine.py does it, so this sweep and
the render it varies cannot disagree about what they are drawing. History is
per-process, so a restarted ComfyUI no longer has it -- hence the cache under
.local, written on the first successful fetch.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import urllib.request

from comfy_host import DEFAULT_HOST, DEFAULT_PORT

REPO = pathlib.Path(__file__).resolve().parent.parent
BASE_CACHE = REPO / ".local/_sw_base.json"
ACCEPTED_PROMPT_ID = "21ea087e-331a-4c70-9619-9ea8745ddbc6"


def load_base(host: str, port: int, prompt_id: str | None) -> dict:
    """Return the prompt, negative, sampler and latent settings being held fixed."""
    if prompt_id is None:
        if BASE_CACHE.exists():
            return json.loads(BASE_CACHE.read_text())
        raise SystemExit(
            f"no cached base at {BASE_CACHE}; pass --from-prompt "
            f"(the accepted render was {ACCEPTED_PROMPT_ID})"
        )
    url = f"http://{host}:{port}/history/{prompt_id}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        history = json.load(resp)
    if not history:
        raise SystemExit(f"{prompt_id} is not in this ComfyUI's history")
    graph = list(history.values())[0]["prompt"][2]
    base = {
        "pos": graph["6"]["inputs"]["text"],
        "neg": graph["7"]["inputs"]["text"],
        "k": graph["3"]["inputs"],
        "lat": graph["5"]["inputs"],
    }
    BASE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    BASE_CACHE.write_text(json.dumps(base, ensure_ascii=False, indent=1))
    return base

# (prefix, base model, [(lora, strength), ...], positive prefix tokens)
VARIANTS = [
    ("st-outlined-10", "hassaku-il-v22", [("outlined-ill.safetensors", 1.0)], ""),
    ("st-outlined-13", "hassaku-il-v22", [("outlined-ill.safetensors", 1.3)], ""),
    ("st-usnr-08", "hassaku-il-v22", [("usnr-style-ill-v1.safetensors", 0.8)], "usnr, "),
    ("st-usnr-11", "hassaku-il-v22", [("usnr-style-ill-v1.safetensors", 1.1)], "usnr, "),
    ("st-out-usnr", "hassaku-il-v22",
     [("outlined-ill.safetensors", 0.7), ("usnr-style-ill-v1.safetensors", 0.7)], "usnr, "),
    ("st-out-2000sa", "hassaku-il-v22",
     [("outlined-ill.safetensors", 0.8), ("moe-2000s-a.safetensors", 0.45)], ""),
    ("st-out-2000sb", "hassaku-il-v22",
     [("outlined-ill.safetensors", 0.8), ("moe-2000s-b.safetensors", 0.6)], ""),
    ("st-amanatsu-out", "amanatsu-il-v11", [("outlined-ill.safetensors", 0.9)], ""),
    ("st-sweetmix-out", "sweet-mix-v14", [("outlined-ill.safetensors", 0.9)], ""),
]


def build(base: dict, base_model: str, loras: list[tuple[str, float]],
          pos_prefix: str) -> dict:
    graph: dict = {
        "4": {"class_type": "DiffusersLoader", "inputs": {"model_path": base_model}},
    }
    model_src, clip_src = ["4", 0], ["4", 1]
    for i, (name, strength) in enumerate(loras):
        node = str(60 + i)
        graph[node] = {
            "class_type": "LoraLoader",
            "inputs": {
                "model": model_src, "clip": clip_src, "lora_name": name,
                "strength_model": strength, "strength_clip": strength,
            },
        }
        model_src, clip_src = [node, 0], [node, 1]

    graph["6"] = {"class_type": "CLIPTextEncode",
                  "inputs": {"clip": clip_src, "text": pos_prefix + base["pos"]}}
    graph["7"] = {"class_type": "CLIPTextEncode",
                  "inputs": {"clip": clip_src, "text": base["neg"]}}
    graph["5"] = {"class_type": "EmptyLatentImage", "inputs": dict(base["lat"])}
    graph["3"] = {"class_type": "KSampler", "inputs": dict(
        base["k"], model=model_src, positive=["6", 0], negative=["7", 0], latent_image=["5", 0])}
    graph["8"] = {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}}
    return graph


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--only", action="append", default=[], help="run just these prefixes")
    parser.add_argument(
        "--from-prompt", metavar="ID",
        help=f"read the held-fixed base out of /history and cache it "
             f"(the accepted render was {ACCEPTED_PROMPT_ID})")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    base = load_base(args.host, args.port, args.from_prompt)

    for prefix, base_model, loras, pos_prefix in VARIANTS:
        if args.only and prefix not in args.only:
            continue
        graph = build(base, base_model, loras, pos_prefix)
        graph["9"] = {"class_type": "SaveImage",
                      "inputs": {"images": ["8", 0], "filename_prefix": prefix}}
        stack = ", ".join(f"{n}@{s}" for n, s in loras) or "-"
        print(f"{prefix:18s} {base_model:16s} {stack}")
        if args.dry_run:
            continue
        req = urllib.request.Request(
            f"http://{args.host}:{args.port}/prompt",
            data=json.dumps({"prompt": graph}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            print("   ->", json.load(resp)["prompt_id"])


if __name__ == "__main__":
    main()
