#!/usr/bin/env python3
"""Run a queue_dq3 recipe through Detail Daemon, changing nothing else.

Detail Daemon measured well on Hamakaze and the gain turned out to be chroma
breaking -- bright blue strands through grey hair, scored as line by an edge
counter. Grey hair under near-flat colour may simply be where it breaks first,
so the question is what it does to a character built out of colour.

The recipe is not reimplemented here. queue_dq3.build_prompt produces the graph
its own flags describe, and this swaps the sampler underneath it, so the prompt,
LoRA stack, negative preset and per-checkpoint tuning are whatever queue_dq3
would have used. Every flag it takes works here; --detail-amount is the only
addition, and it is repeatable for a ladder.

    ./scripts/queue_dq3_detail.py --job yukari --detail-amount 0.0 \\
        --detail-amount 0.1 --detail-amount 0.25

0.0 is not a no-op flag: it still routes through SamplerCustomAdvanced and is
the control that separates the node's effect from the rebuild's.
"""

from __future__ import annotations

import argparse
import json
import sys

import colorize_lineart
import queue_dq3


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--detail-amount", type=float, action="append", default=[],
                        help="repeat for a ladder; SDXL wants under 0.25")
    parser.add_argument("--detail-prefix", default="dd",
                        help="filename prefix; the amount is appended")
    parser.add_argument("--dry-run", action="store_true")
    mine, rest = parser.parse_known_args()

    args = queue_dq3.parse_args_from(rest)
    queue_dq3.apply_defaults(args)

    for amount in mine.detail_amount or [None]:
        tag = "base" if amount is None else f"d{int(round(amount * 100)):03d}"
        prefix = f"{mine.detail_prefix}-{args.job}-{tag}"
        seed = args.seed if args.seed >= 0 else 111222333
        graph = queue_dq3.build_prompt(args, seed, prefix)

        # Read the wiring off the sampler queue_dq3 built rather than assuming
        # it: the model ref is the tail of whatever LoRA chain the recipe made,
        # and the conditioning refs may come from a ControlNet apply.
        ks = graph["3"]["inputs"]
        sampling, latent_out = colorize_lineart.sampler_nodes(
            ks["model"], ks["positive"], ks["negative"], ks["latent_image"],
            seed, amount, sampler=ks["sampler_name"], scheduler=ks["scheduler"],
            steps=ks["steps"], cfg=ks["cfg"])
        if amount is not None:
            del graph["3"]
        graph.update(sampling)
        graph["8"]["inputs"]["samples"] = latent_out

        for nid, node in graph.items():
            for value in node["inputs"].values():
                if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                    if value[0] not in graph:
                        raise SystemExit(f"{prefix}: node {nid} references missing {value[0]}")

        print(f"{prefix:24s} detail={amount}  sampler={ks['sampler_name']}/{ks['scheduler']}"
              f"  steps={ks['steps']} cfg={ks['cfg']}")
        if mine.dry_run:
            continue
        result = queue_dq3.queue_prompt(args, graph)
        print("   ->", result["prompt_id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
