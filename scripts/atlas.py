#!/usr/bin/env python3
"""Where things are, without reading them.

`docs/findings/` holds the current conclusions, one short file per topic.
`docs/archive/` is the frozen measurement log (~160k tokens) that the findings
were distilled from; it is grepped, never opened whole.

    uv run scripts/atlas.py                 # every script: role, size, one line
    uv run scripts/atlas.py docs            # every doc: size and title
    uv run scripts/atlas.py notes           # findings headings; archive files by size
    uv run scripts/atlas.py notes legwear   # the sections whose heading matches
    uv run scripts/atlas.py find "denoise"  # matches, each under its file and heading

Nothing here is written to disk: it reads the tree every time, so it cannot
be stale. Sizes are chars/4.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
NOTE_DIRS = ("findings", "archive")


def tokens(text: str) -> int:
    return len(text) // 4


def tracked(pattern: str) -> list[Path]:
    out = subprocess.run(["git", "ls-files", pattern], cwd=REPO,
                         capture_output=True, text=True, check=True).stdout
    return [REPO / line for line in out.split("\n") if line]


def summary(path: Path) -> str:
    try:
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8")))
    except (SyntaxError, UnicodeDecodeError):
        return ""
    return (doc or "").strip().split("\n")[0]


def imported_by(paths: list[Path]) -> dict[str, set[str]]:
    names = {p.stem for p in paths}
    used: dict[str, set[str]] = {p.stem: set() for p in paths}
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        # Credits every dotted component, so `from .model import ...` counts too.
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
        text = path.read_text(encoding="utf-8", errors="replace")
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


def note_files() -> list[Path]:
    return [p for d in NOTE_DIRS for p in sorted((DOCS / d).rglob("*.md"))]


def headings(path: Path) -> list[tuple[int, int, str, int]]:
    """(line, level, text, size) for every ## / ### heading in one file."""
    lines = path.read_text(encoding="utf-8").split("\n")
    marks = [(i + 1, len(m.group(1)), m.group(2))
             for i, line in enumerate(lines)
             if (m := re.match(r"^(#{2,3}) (.+)$", line))]
    out = []
    for index, (line, level, text) in enumerate(marks):
        end = marks[index + 1][0] if index + 1 < len(marks) else len(lines) + 1
        out.append((line, level, text, tokens("\n".join(lines[line - 1:end - 1]))))
    return out


def map_docs() -> None:
    paths = [p for p in tracked("docs/*.md") if p.exists()]
    total = 0
    for path in sorted(paths):
        text = path.read_text(encoding="utf-8")
        total += tokens(text)
        title = next((l[2:] for l in text.split("\n") if l.startswith("# ")), "")
        print(f"~{tokens(text):6d}  {str(path.relative_to(REPO)):52s} {title[:60]}")
    print(f"\n~{total} tokens in all. Findings first; archive only by line range.")


def map_notes(pattern: str | None) -> None:
    for path in note_files():
        rel = path.relative_to(REPO)
        marks = headings(path)
        if pattern is None:
            text = path.read_text(encoding="utf-8")
            print(f"\n{rel} -- ~{tokens(text)} tokens, {len(marks)} sections")
            if "archive" in rel.parts:
                continue
            for line, level, text, tok in marks:
                print(f"{line:6d}  ~{tok:5d}  {'  ' * (level - 2)}{text}")
            continue
        lines = path.read_text(encoding="utf-8").split("\n")
        for line, level, text, tok in marks:
            if not re.search(pattern, text, re.I):
                continue
            after = [h for h in marks if h[0] > line and h[1] <= level]
            end = after[0][0] if after else len(lines) + 1
            print(f"--- {rel}:{line}")
            print("\n".join(lines[line - 1:end - 1]))


def find(pattern: str) -> None:
    """Matches in findings and archive, each shown under its file and heading."""
    for path in note_files():
        rel = path.relative_to(REPO)
        current = ""
        for index, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            if m := re.match(r"^#{2,3} (.+)$", line):
                current = m.group(1)
            if re.search(pattern, line, re.I):
                print(f"{rel}:{index}  [{current[:40]}]  {line.strip()[:100]}")


def main() -> None:
    argv = sys.argv[1:]
    if not argv:
        map_scripts()
    elif argv[0] == "docs":
        map_docs()
    elif argv[0] == "notes":
        map_notes(argv[1] if len(argv) > 1 else None)
    elif argv[0] == "find" and len(argv) > 1:
        find(argv[1])
    else:
        print(__doc__)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
