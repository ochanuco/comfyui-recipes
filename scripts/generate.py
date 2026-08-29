#!/usr/bin/env python3
"""Deprecated compatibility wrapper for :command:`comfy-recipes`.

New code should use ``comfy-recipes generate|finalize|metadata``. This file
only translates the former flags; generation logic lives in the package.
"""

from __future__ import annotations

import sys

from comfyui_recipes.interfaces.cli import main


def legacy_arguments(arguments: list[str]) -> list[str]:
    if "--request" in arguments:
        return ["generate", *arguments]
    mappings = {
        "--finalize": "finalize",
        "--semantic": "semantic",
        "--tag": "tag",
        "--asset": "asset",
        "--list-assets": "list-assets",
    }
    for flag, command in mappings.items():
        if flag not in arguments:
            continue
        index = arguments.index(flag)
        values = arguments[index + 1:]
        before = arguments[:index]
        if command == "finalize":
            return ["finalize", values[0], *before, *values[1:]]
        return ["metadata", command, *values, *before]
    return arguments


if __name__ == "__main__":
    main(legacy_arguments(sys.argv[1:]))
