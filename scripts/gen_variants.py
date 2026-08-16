#!/usr/bin/env python3
"""Ask a local ollama model for scene variations, then queue them through ComfyUI.

The point is to vary composition without spending tokens on a hosted model, so
the LLM is handed a fixed vocabulary and told to recombine it. Local 30B models
recall Danbooru tags poorly but recombine a supplied list just fine, and the
constraint also stops them from touching the outfit and legwear tags in
queue_dq3.py that were tuned by hand.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import urllib.error
import urllib.request

import queue_dq3
from comfy_host import DEFAULT_HOST, DEFAULT_PORT

# Deliberately scene-only: no body, outfit or legwear tags, and nothing that
# fights queue_dq3's NEG_FRAMING. "from below", "cowboy shot" and "close-up" are
# excluded on purpose -- they crop the head or drag framing toward the hips.
VOCABULARY = {
    "setting": [
        "forest", "deep forest", "grassy field", "riverbank", "mountain path",
        "stone ruins", "ancient ruins", "castle town", "cobblestone street",
        "marketplace", "tavern interior", "library", "cathedral interior",
        "campsite", "snowy field", "desert", "cliff", "ocean in background",
        "flower field", "bridge", "castle courtyard",
    ],
    "lighting": [
        "sunset", "golden hour", "dawn", "morning light", "overcast",
        "dappled sunlight", "moonlight", "starry sky", "firelight", "candlelight",
        "backlighting", "soft lighting", "god rays", "lens flare",
    ],
    "camera": [
        "from side", "three quarter view", "from behind", "looking back",
        "wide shot", "scenery focus", "dutch angle",
    ],
    "expression": [
        "smile", "gentle smile", "serious", "closed eyes", "looking away",
        "looking at viewer", "surprised", "determined",
    ],
    # Posture belongs to --pose, so nothing here may imply one. "sitting on rock"
    # used to live in this list and it beat "--pose standing" outright.
    "motion": [
        "wind", "floating hair", "cape flutter", "casting spell",
        "magic circle", "glowing staff", "falling leaves", "rain", "snowing",
        "petals", "fog", "fireflies", "birds",
    ],
}

SYSTEM_PROMPT = """You generate Danbooru-style scene tags for an image generator.

RULES:
- Reply with JSON only: {"variants": ["...", "..."]}
- Each variant is a comma-separated tag string, 4 to 7 tags long.
- Use ONLY tags from the VOCABULARY below. Never invent tags.
- Pick at most one tag from "camera" per variant.
- Every variant must be clearly different from the others.
- Never output tags about the character's body, outfit, hair, legwear or age.
  Those are supplied elsewhere and must not be duplicated or contradicted.
- Never imply a posture (standing, sitting, lying). Posture is supplied elsewhere.

VOCABULARY:
{vocabulary}"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate scene variants with a local LLM and queue them through ComfyUI."
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--job", choices=sorted(queue_dq3.CLASSES), default="sage")
    parser.add_argument("--pose", choices=sorted(queue_dq3.POSES), default="standing")
    parser.add_argument("--face", choices=sorted(queue_dq3.FACES), default="default")
    parser.add_argument("--style", choices=sorted(queue_dq3.STYLES), default="default")
    parser.add_argument("--plain-quality", action="store_true")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--theme", default="", help="free-text hint, any language")
    parser.add_argument("--ollama-url", default="http://localhost:11434/api/chat")
    parser.add_argument("--model", default="qwen3:30b-instruct")
    parser.add_argument("--temperature", type=float, default=0.9)
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--prefix")
    parser.add_argument("--dry-run", action="store_true", help="print variants, queue nothing")
    parser.add_argument("--wait", action="store_true")
    # Anything else is handed straight to queue_dq3, so --diffusers-path, --lora,
    # --sampler and friends keep working here without being restated.
    return parser.parse_known_args()


def format_vocabulary() -> str:
    return "\n".join(f"{name}: {', '.join(tags)}" for name, tags in VOCABULARY.items())


def extract_json(text: str) -> dict:
    # Thinking-tuned checkpoints leak <think> blocks even in JSON mode.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise SystemExit(f"could not parse JSON from model output:\n{text}")
        return json.loads(match.group(0))


def ask_ollama(args: argparse.Namespace) -> list[str]:
    user = f"Generate {args.count} variants."
    if args.theme:
        user += f" Theme to respect where the vocabulary allows: {args.theme}"

    payload = json.dumps(
        {
            "model": args.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT.replace(
                    "{vocabulary}", format_vocabulary())},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": args.temperature},
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        args.ollama_url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            body = json.loads(response.read())
    except urllib.error.URLError as exc:
        raise SystemExit(f"failed to reach ollama at {args.ollama_url}: {exc}") from exc

    variants = extract_json(body["message"]["content"]).get("variants", [])
    if not variants:
        raise SystemExit("the model returned no variants")
    return [v.strip() for v in variants if isinstance(v, str) and v.strip()]


def resolve_defaults(passthrough: list[str]) -> dict:
    """queue_dq3's parsed args, so this wrapper inherits its defaults."""
    parsed = queue_dq3.parse_args_from(passthrough)
    queue_dq3.apply_defaults(parsed)
    return vars(parsed)


def main() -> int:
    args, passthrough = parse_args()
    base_defaults = resolve_defaults(passthrough)
    for key in ("job", "pose", "face", "style", "plain_quality", "host", "port"):
        base_defaults[key] = getattr(args, key)
    variants = ask_ollama(args)

    if len(variants) < args.count:
        print(f"note: model returned {len(variants)} variants, wanted {args.count}")
    variants = variants[: args.count]

    prefix = args.prefix or f"dq3v-{args.job}-{args.pose}"
    prompt_ids = []

    for index, extra in enumerate(variants):
        # Unbuffered so background runs show progress before the process exits.
        print(f"[{index + 1}] {extra}", flush=True)
        if args.dry_run:
            continue

        seed = args.seed if args.seed >= 0 else random.randint(0, 2**32 - 1)
        if args.seed >= 0:
            seed += index

        # queue_dq3's builders read a flat namespace, so mirror its defaults here
        # rather than duplicating the prompt assembly.
        # Start from queue_dq3's own defaults rather than restating them: this
        # file used to pin the checkpoint and sampler by hand and silently went
        # stale every time those moved.
        job_args = argparse.Namespace(**base_defaults)
        job_args.extra = extra
        prompt = queue_dq3.build_prompt(job_args, seed, prefix)
        try:
            response = queue_dq3.queue_prompt(job_args, prompt)
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"ComfyUI rejected the prompt: {exc.read().decode()}") from exc
        prompt_ids.append(response["prompt_id"])
        print(f"    queued {response['prompt_id']} seed={seed}", flush=True)

    if args.wait and prompt_ids:
        queue_dq3.wait_for(argparse.Namespace(host=args.host, port=args.port), prompt_ids)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
