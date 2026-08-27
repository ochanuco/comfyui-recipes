#!/usr/bin/env python3
"""Where things are, without reading them.

This repo is expensive to look at. `docs/render-notes.md` is ~68k tokens,
`scripts/queue_dq3.py` ~21k and `scripts/yukari_recipe.py` ~19k -- between them
more than half the repository, and all three are files an agent is tempted to
open whole to answer a one-line question. This prints the answer instead.

    uv run scripts/atlas.py                 # every script: role, size, one line
    uv run scripts/atlas.py notes           # the notes' headings, with line numbers
    uv run scripts/atlas.py notes legwear   # the sections whose heading matches
    uv run scripts/atlas.py find "denoise"  # matches, each under its heading

Nothing here is written to disk. A generated index is a file that goes stale
between the change and the next person who trusts it; this reads the tree it is
describing, every time it runs, so it cannot be wrong about it.

Sizes are chars/4, which is close enough for deciding whether to open something.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NOTES = REPO / "docs/render-notes.md"


def tokens(text: str) -> int:
    return len(text) // 4


def tracked(pattern: str) -> list[Path]:
    out = subprocess.run(["git", "ls-files", pattern], cwd=REPO,
                         capture_output=True, text=True, check=True).stdout
    return [REPO / line for line in out.split("\n") if line]


def summary(path: Path) -> str:
    """The first line of the module docstring, which is the file's own claim."""
    try:
        doc = ast.get_docstring(ast.parse(path.read_text()))
    except (SyntaxError, UnicodeDecodeError):
        return ""
    return (doc or "").strip().split("\n")[0]


def imported_by(paths: list[Path]) -> dict[str, set[str]]:
    """Which tracked modules each file imports, by module name."""
    names = {p.stem for p in paths}
    used: dict[str, set[str]] = {p.stem: set() for p in paths}
    for path in paths:
        text = path.read_text(errors="replace")
        # `from yukari.costumes import ...` and the package's own relative
        # `from .model import ...` both count: credit every dotted component.
        for match in re.finditer(r"^\s*(?:from|import)\s+\.?([\w.]+)", text, re.M):
            for part in match.group(1).split("."):
                if part in names and part != path.stem:
                    used[part].add(path.stem)
    return used


def map_scripts() -> None:
    paths = [p for p in tracked("scripts/*.py") if p.exists()]
    users = imported_by(paths)
    rows = []
    for path in sorted(paths):
        text = path.read_text(errors="replace")
        callers = users[path.stem]
        if "archive/" in str(path.relative_to(REPO)):
            role = "archive"
        elif callers:
            role = f"lib<-{len(callers)}"
        elif '__name__ == "__main__"' in text:
            role = "cli"
        else:
            role = "one-shot"
        rows.append((role, path.relative_to(REPO), tokens(text), summary(path)))

    order = {"lib<-": 0, "cli": 1, "one-shot": 2, "archive": 3}
    rows.sort(key=lambda r: (next(v for k, v in order.items() if r[0].startswith(k)),
                             -r[2]))
    total = sum(r[2] for r in rows)
    print(f"{len(rows)} scripts, ~{total} tokens if you read them all\n")
    print("  lib<-N   imported by N others -- read before changing anything")
    print("  cli      has its own __main__")
    print("  one-shot ran once, kept as a record; not a tool")
    print("  archive  the same, and moved out of the way\n")
    for role, rel, tok, first in rows:
        print(f"{role:9s} {str(rel):38s} ~{tok:6d}  {first[:78]}")


def headings() -> list[tuple[int, int, str, int]]:
    """(line, level, text, size) for every heading in the notes."""
    lines = NOTES.read_text().split("\n")
    marks = [(i + 1, len(m.group(1)), m.group(2))
             for i, line in enumerate(lines)
             if (m := re.match(r"^(#{2,3}) (.+)$", line))]
    out = []
    for index, (line, level, text) in enumerate(marks):
        end = marks[index + 1][0] if index + 1 < len(marks) else len(lines) + 1
        out.append((line, level, text, tokens("\n".join(lines[line - 1:end - 1]))))
    return out


def map_notes(pattern: str | None) -> None:
    if pattern is None:
        total = tokens(NOTES.read_text())
        print(f"docs/render-notes.md -- ~{total} tokens whole. "
              f"Read a section with --offset/--limit, or name it here.\n")
        for line, level, text, tok in headings():
            indent = "  " * (level - 2)
            print(f"{line:6d}  ~{tok:5d}  {indent}{text}")
        return

    lines = NOTES.read_text().split("\n")
    marks = headings()
    hits = [h for h in marks if re.search(pattern, h[2], re.I)]
    if not hits:
        print(f"no heading matches {pattern!r}; try `atlas.py find` for the body")
        return
    for line, level, text, tok in hits:
        after = [h for h in marks if h[0] > line and h[1] <= level]
        end = after[0][0] if after else len(lines) + 1
        print("\n".join(lines[line - 1:end - 1]))


def find(pattern: str) -> None:
    """Matches in the notes, each shown under the heading it lives beneath."""
    lines = NOTES.read_text().split("\n")
    marks = headings()
    current = ""
    for index, line in enumerate(lines, 1):
        head = [h for h in marks if h[0] == index]
        if head:
            current = head[0][2]
        # Headings are searched too. A phrase that turns out to be a section
        # title is the best possible hit -- it means `atlas.py notes <pattern>`
        # will print the whole thing.
        if re.search(pattern, line, re.I):
            print(f"{index:6d}  [{current[:44]}]  {line.strip()[:100]}")


def main() -> None:
    argv = sys.argv[1:]
    if not argv:
        map_scripts()
    elif argv[0] == "notes":
        map_notes(argv[1] if len(argv) > 1 else None)
    elif argv[0] == "find" and len(argv) > 1:
        find(argv[1])
    else:
        print(__doc__)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
