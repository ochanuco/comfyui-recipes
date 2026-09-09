#!/usr/bin/env python3
"""Push experiments/**/*.jsonl records into chimera's Observation index.

experiments/ stays the source of truth and the write path; this script syncs
a derived, queryable copy to chimera. See AGENTS.md "Where information
lives" and experiments/README.md.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from comfyui_recipes.infrastructure.chimera.client import ChimeraClient
from comfyui_recipes.infrastructure.repository import discover_repository

# Five records carry neither pose nor component but should be indexed: the
# A/B-round records shaped {date, model, axis, arms, ...}. Line 48 is not
# "delivery_style" -- its axis is a prompt-BODY-block round, and that file's
# own records carry four different component values of their own.
COMPONENT_OVERRIDES: dict[tuple[str, int], str] = {
    ("experiments/yukari/prompt_style.jsonl", 33): "prompt_style",
    ("experiments/yukari/prompt_style.jsonl", 34): "prompt_style",
    ("experiments/yukari/prompt_style.jsonl", 35): "prompt_style",
    ("experiments/yukari/prompt_style.jsonl", 36): "prompt_style",
    ("experiments/yukari/delivery_style.jsonl", 48): "prompt_style",
}


def build_files(root: Path) -> list[dict]:
    """One entry per experiments JSONL file, records in line order."""
    files = []
    experiments = root / "experiments"
    for path in sorted(experiments.rglob("*.jsonl"),
                        key=lambda p: p.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        records = []
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_no, raw in enumerate(lines, start=1):
            if not raw.strip():
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as error:
                raise SystemExit(f"{rel}:{line_no}: invalid JSON: {error}")
            entry: dict = {"line": line_no, "record": record}
            if "pose" not in record and "component" not in record:
                override = COMPONENT_OVERRIDES.get((rel, line_no))
                if override is not None:
                    entry["component"] = override
            records.append(entry)
        files.append({"path": rel, "records": records})
    return files


def unlabelled(files: list[dict]) -> list[tuple[str, int]]:
    """(path, line) for records carrying no pose, component or override."""
    result = []
    for file in files:
        for entry in file["records"]:
            record = entry["record"]
            if "pose" in record or "component" in record or "component" in entry:
                continue
            result.append((file["path"], entry["line"]))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None,
                         help="repository root (default: discovered from git)")
    parser.add_argument("--dry-run", action="store_true",
                         help="print counts and unlabelled records; post nothing")
    args = parser.parse_args()

    root = args.root or discover_repository()
    files = build_files(root)

    if args.dry_run:
        total = 0
        for file in files:
            count = len(file["records"])
            total += count
            print(f"{file['path']}: {count}")
        print(f"total: {total} records across {len(files)} files")
        for path, line in unlabelled(files):
            print(f"unlabelled: {path}:{line}")
        return

    chimera = ChimeraClient(root)
    response = chimera.request(
        "POST", "/api/v1/observations/sync", {"files": files})
    print(f"inserted: {response['inserted']}")
    print(f"unchanged: {response['unchanged']}")
    for item in response.get("skipped", []):
        print(f"skipped: {item}")


if __name__ == "__main__":
    main()
