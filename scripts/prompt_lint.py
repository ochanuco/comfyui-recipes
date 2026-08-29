#!/usr/bin/env python3
"""Check a request or prompt pair for positive/negative contradictions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from comfyui_recipes.domain.generation.prompt_lint import conflicts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--pos")
    parser.add_argument("--neg")
    args = parser.parse_args()
    if args.request:
        generation = json.loads(args.request.read_text()).get("generation", {})
        positive = generation.get("prompt", "")
        negative = generation.get("negative_prompt", "")
    else:
        positive, negative = args.pos or "", args.neg or ""
    hits = conflicts(positive, negative)
    for positive_tag, negative_tag, why in hits:
        print(
            f"positive asks ({positive_tag}) while negative bans "
            f"({negative_tag})  [{why}]")
    if not hits:
        print("no contradictions")
    raise SystemExit(1 if hits else 0)


if __name__ == "__main__":
    main()
