"""Flag positive/negative contradictions before a render is spent.

    uv run scripts/prompt_lint.py --request <request.json>
    uv run scripts/prompt_lint.py --pos "..." --neg "..."

One failure shape produced most of this repo's wasted arms: asking for a
property in the positive while a ban erected for an *earlier* look still
forbids it in the negative -- sheer tights under `(transparent clothing)`,
an aqua backdrop under `(blue background:1.5), (blue tint:1.4)`. The notes
call it 「透けを頼みつつ透明を禁じる」; nothing surfaced it until the render
came back wrong, because the negative is a fortress of frozen fixes and no
one rereads it per arm. This does the rereading.

A hit is not always a mistake -- `wet look` banned next to `shiny legwear`
was once the deliberate sheen/shine split -- so generate.py treats hits as
a hard stop with `--force` to say "yes, on purpose".
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

COLORS = {"black", "white", "grey", "gray", "blue", "aqua", "navy", "brown",
          "green", "pink", "purple", "red", "yellow", "orange", "charcoal",
          "lavender", "periwinkle", "cream", "silver"}
SYNONYM = {"see-through": "sheer", "transparent": "sheer", "sheer": "sheer",
           "aqua": "blue", "navy": "blue", "periwinkle": "blue",
           "gray": "grey", "charcoal": "grey",
           "glossy": "shiny", "wet": "shiny"}
PROPERTIES = COLORS | {"sheer", "opaque", "shiny", "ribbed", "knit", "muted"}
LEGWEAR = {"legwear", "pantyhose", "thighhighs", "thighhigh", "kneehighs",
           "socks", "tights", "stockings"}
# Nouns that scope a ban to the whole frame rather than one garment.
UNSCOPED = {"clothing", "clothes", "tint", "look", "color", "colors"}


def tags(prompt: str) -> list[str]:
    out = []
    for part in prompt.split(","):
        part = part.strip().strip("()")
        part = re.sub(r":\d+(\.\d+)?$", "", part)
        if part:
            out.append(part)
    return out


def properties(tag: str) -> set[str]:
    words = set(tag.replace("-", " ").split()) | set(tag.split())
    return {SYNONYM.get(w, w) for w in words if
            SYNONYM.get(w, w) in {SYNONYM.get(p, p) for p in PROPERTIES}}


def nouns(tag: str) -> set[str]:
    words = set(tag.split())
    out = set()
    if words & LEGWEAR:
        out.add("legwear")
    if "background" in words:
        out.add("background")
    if words & UNSCOPED:
        out.add("*")
    rest = [w for w in tag.split() if w not in PROPERTIES
            and SYNONYM.get(w, w) not in PROPERTIES]
    if rest:
        out.add(rest[-1])
    if not out:
        out.add("*")
    return out


def conflicts(positive: str, negative: str) -> list[tuple[str, str, str]]:
    hits = []
    neg_tags = [(n, properties(n), nouns(n)) for n in tags(negative)]
    for p in tags(positive):
        p_props, p_nouns = properties(p), nouns(p)
        if not p_props:
            continue
        for n, n_props, n_nouns in neg_tags:
            shared = p_props & n_props
            if not shared:
                continue
            # Banning the solid/opaque form of a colour is how a sheer ask is
            # *supported*, not fought -- same colour on both sides is fine there.
            if "sheer" in p_props and ({"solid", "opaque"} & set(n.split())):
                continue
            if "*" in p_nouns or "*" in n_nouns or (p_nouns & n_nouns):
                hits.append((p, n, "/".join(sorted(shared))))
    return hits


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--pos")
    parser.add_argument("--neg")
    args = parser.parse_args()
    if args.request:
        gen = json.loads(args.request.read_text()).get("generation", {})
        pos, neg = gen.get("prompt", ""), gen.get("negative_prompt", "")
    else:
        pos, neg = args.pos or "", args.neg or ""
    hits = conflicts(pos, neg)
    for p, n, why in hits:
        print(f"positive asks ({p}) while negative bans ({n})  [{why}]")
    if not hits:
        print("no contradictions")
    raise SystemExit(1 if hits else 0)


if __name__ == "__main__":
    main()
