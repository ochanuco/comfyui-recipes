#!/usr/bin/env python3
"""Check a request or prompt pair for positive/negative contradictions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from comfyui_recipes.domain.generation.prompt_lint import conflicts
from comfyui_recipes.domain.yukari.recipe import negative, positive


def request_prompts(request: dict) -> tuple[str, str]:
    generation = request.get("generation", {})
    parameters = generation.get("parameters", {})
    pose = parameters["pose"]
    costume = parameters.get("costume", "default")
    return (
        generation.get("prompt") or positive(pose, costume),
        generation.get("negative_prompt") or negative(pose, costume),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--pos")
    parser.add_argument("--neg")
    args = parser.parse_args()
    if args.request:
        positive_prompt, negative_prompt = request_prompts(
            json.loads(args.request.read_text()))
    else:
        positive_prompt, negative_prompt = args.pos or "", args.neg or ""
    hits = conflicts(positive_prompt, negative_prompt)
    for positive_tag, negative_tag, why in hits:
        print(
            f"positive asks ({positive_tag}) while negative bans "
            f"({negative_tag})  [{why}]")
    if not hits:
        print("no contradictions")
    raise SystemExit(1 if hits else 0)


if __name__ == "__main__":
    main()
