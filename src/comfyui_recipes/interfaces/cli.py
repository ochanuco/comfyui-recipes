"""The single public command-line interface for comfyui-recipes."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from ..application import metadata
from ..application.finalize import FinalizeServices, finalize
from ..domain.yukari.recipe import TOE_GUARD
from ..application.generate import GenerateServices, generate, request_graph
from ..application.watch import WatchServices, watch
from ..domain.generation.prompt_lint import conflicts
from ..domain.yukari.costumes import COSTUMES
from ..domain.yukari.poses import POSES
from ..domain.yukari.recipe import negative, positive
from ..domain.yukari.recipe import render_spec as yukari_render_spec
from ..domain.yukari_anima.costumes import COSTUMES as ANIMA_COSTUMES
from ..domain.yukari_anima.expressions import EXPRESSIONS as ANIMA_EXPRESSIONS
from ..domain.yukari_anima.poses import POSES as ANIMA_POSES
from ..domain.yukari_anima.recipe import negative as anima_negative
from ..domain.yukari_anima.recipe import positive as anima_positive
from ..domain.yukari_anima.recipe import render_spec as anima_render_spec
from ..infrastructure.chimera.client import ChimeraClient
from ..infrastructure.comfyui.anima_graph import build_graph as anima_build_graph
from ..infrastructure.comfyui.client import ComfyUIClient
from ..infrastructure.comfyui.refinement_graph import chain_pass
from ..infrastructure.comfyui.yukari_graph import build_graph as yukari_build_graph
from ..infrastructure.imaging.delivery import (
    clean_background, graph_from_png,
)
from ..infrastructure.imaging.palette import (
    repin_png, repin_skin_png, summarize)
from ..infrastructure.imaging.recolor import recolor_png
from ..infrastructure.notifications.discord import DiscordNotifier
from ..infrastructure.persistence.run_state import JsonRunState
from ..infrastructure.repository import discover_repository, git_metadata

# `generation.recipe` -> (RenderSpec builder, ComfyUI graph builder).
RECIPES = {
    "yukari": (yukari_render_spec, yukari_build_graph),
    "yukari-anima": (anima_render_spec, anima_build_graph),
}


def _build_generation_graph(generation: dict, seed: int, prefix: str) -> dict:
    if generation.get("graph"):
        return request_graph(generation, seed, prefix, None, None)
    spec_builder, encode = RECIPES[generation["recipe"]]
    return request_graph(generation, seed, prefix, spec_builder, encode)


def _positive_finite_seconds(raw: str) -> float:
    """argparse type= for --interval: rejects 0, negatives, nan and inf."""
    try:
        value = float(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {raw!r}") from None
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError(
            f"--interval must be a finite number > 0, got {raw!r}")
    return value


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="comfy-recipes")
    commands = root.add_subparsers(dest="command", required=True)

    generate_parser = commands.add_parser("generate", help="run and record a batch")
    generate_parser.add_argument("--request", required=True, type=Path)
    generate_parser.add_argument("--dry-run", action="store_true")
    generate_parser.add_argument("--force", action="store_true")

    watch_parser = commands.add_parser(
        "watch", help="poll chimera for pending ExperimentRuns and generate them")
    watch_parser.add_argument(
        "--interval", type=_positive_finite_seconds, default=30)
    watch_parser.add_argument("--once", action="store_true")
    watch_parser.add_argument("--dry-run", action="store_true")

    finalize_parser = commands.add_parser("finalize", help="deliver one picked render")
    finalize_parser.add_argument("generation_id")
    finalize_parser.add_argument("--denoise", type=float)
    finalize_parser.add_argument("--handdrawn", action="store_true")
    finalize_parser.add_argument(
        "--repin", action="store_true", help="repin the delivery's palette")
    finalize_parser.add_argument(
        "--toe-guard", type=float, nargs="?", const=TOE_GUARD, metavar="WEIGHT",
        help="ban the toes in the redraw, hiding the count behind a smooth "
             "toe box; off by default because the checkpoint draws five")
    finalize_parser.add_argument(
        "--skin", action="store_true",
        help="pin the redraw's skin back to the base render's own")
    finalize_parser.add_argument(
        "--size", type=int, metavar="LONGEST",
        help="longest side of the delivery redraw; a DiT's cost tracks pixel "
             "count, so this is the speed dial")
    finalize_parser.add_argument(
        "--latent-route", action="store_true",
        help="upscale the latent instead of the decoded image; the staircase "
             "it leaves is what the redraw turns into visible stroke")
    finalize_parser.add_argument("--recolor", action="store_true")
    finalize_parser.add_argument(
        "--keep-legwear", nargs="?", const=0.62, type=float, default=None,
        metavar="COL_CUT",
        help="keep the asserted legwear verbatim through repin; the value is "
             "the width share the legs stay left of (default 0.62)")

    metadata_parser = commands.add_parser("metadata", help="manage generation metadata")
    metadata_commands = metadata_parser.add_subparsers(
        dest="metadata_command", required=True)
    semantic = metadata_commands.add_parser("semantic")
    semantic.add_argument("generation_id")
    semantic.add_argument("file", type=Path)
    tag = metadata_commands.add_parser("tag")
    tag.add_argument("generation_id")
    tag.add_argument("name")
    asset = metadata_commands.add_parser("asset")
    asset.add_argument("generation_id")
    asset.add_argument("role")
    asset.add_argument("file", type=Path)
    asset.add_argument("--region", default="")
    assets = metadata_commands.add_parser("list-assets")
    assets.add_argument("generation_id")

    yukari_parser = commands.add_parser("yukari", help="inspect the Yukari domain")
    yukari_commands = yukari_parser.add_subparsers(dest="yukari_command", required=True)
    prompt = yukari_commands.add_parser("prompt")
    prompt.add_argument("--pose", required=True, choices=sorted(POSES))
    prompt.add_argument("--costume", default="default", choices=sorted(COSTUMES))
    prompt.add_argument("--json", action="store_true")

    anima_parser = commands.add_parser("anima", help="inspect the Yukari-anima domain")
    anima_commands = anima_parser.add_subparsers(dest="anima_command", required=True)
    anima_prompt = anima_commands.add_parser("prompt")
    anima_prompt.add_argument("--pose", required=True, choices=sorted(ANIMA_POSES))
    anima_prompt.add_argument("--costume", choices=sorted(ANIMA_COSTUMES))
    anima_prompt.add_argument("--expression", choices=sorted(ANIMA_EXPRESSIONS))
    anima_prompt.add_argument("--json", action="store_true")
    return root


def main(argv: list[str] | None = None) -> None:
    args = parser().parse_args(argv)
    if args.command == "yukari":
        prompts = {
            "positive": positive(args.pose, args.costume),
            "negative": negative(args.pose, args.costume),
        }
        if args.json:
            print(json.dumps(prompts, ensure_ascii=False, indent=2))
        else:
            print(prompts["positive"], "\n\n---\n\n", prompts["negative"])
        return
    if args.command == "anima":
        prompts = {
            "positive": anima_positive(args.pose, args.costume, args.expression),
            "negative": anima_negative(args.pose, args.costume, args.expression),
        }
        if args.json:
            print(json.dumps(prompts, ensure_ascii=False, indent=2))
        else:
            print(prompts["positive"], "\n\n---\n\n", prompts["negative"])
        return

    repository = discover_repository()
    chimera = ChimeraClient(repository)
    comfyui = ComfyUIClient()
    notifier = DiscordNotifier(repository)

    def repository_metadata() -> dict:
        return git_metadata(repository)

    if args.command == "generate":
        services = GenerateServices(
            management=chimera,
            comfyui=comfyui,
            state=JsonRunState(),
            notifier=notifier,
            graph_builder=_build_generation_graph,
            git_metadata=repository_metadata,
            conflicts=conflicts,
            output_root=repository / ".local/_nogit/chimera",
            measure=summarize,
        )
        generate(args.request, services, dry_run=args.dry_run, force=args.force)
        return
    if args.command == "watch":
        services = GenerateServices(
            management=chimera,
            comfyui=comfyui,
            state=JsonRunState(),
            notifier=notifier,
            graph_builder=_build_generation_graph,
            git_metadata=repository_metadata,
            conflicts=conflicts,
            output_root=repository / ".local/_nogit/chimera",
            measure=summarize,
        )
        watch_services = WatchServices(management=chimera, generate_services=services)
        watch(watch_services, interval=args.interval, once=args.once,
              dry_run=args.dry_run)
        return
    if args.command == "finalize":
        services = FinalizeServices(
            management=chimera,
            comfyui=comfyui,
            graph_from_png=graph_from_png,
            chain_pass=chain_pass,
            deliver=clean_background,
            git_metadata=repository_metadata,
            notifier=notifier,
            output_root=repository / ".local/_nogit/finalize",
            repin=lambda data: repin_png(data, keep_legwear=args.keep_legwear),
            repin_skin=repin_skin_png,
            measure=summarize,
            recolor=recolor_png,
        )
        finalize(args.generation_id, services, denoise=args.denoise,
                 handdrawn=args.handdrawn, apply_repin=args.repin,
                 apply_skin=args.skin,
                 apply_recolor=args.recolor,
                 keep_legwear=args.keep_legwear,
                 size=args.size,
                 latent_route=args.latent_route,
                 toe_guard=args.toe_guard)
        return

    if args.metadata_command == "semantic":
        metadata.put_semantic(chimera, args.generation_id, args.file)
        print(f"semantic -> {args.generation_id}")
    elif args.metadata_command == "tag":
        metadata.add_tag(chimera, args.generation_id, args.name)
        print(f"tag {args.name!r} -> {args.generation_id}")
    elif args.metadata_command == "asset":
        row = metadata.upload_asset(
            chimera, args.generation_id, args.role, args.file, args.region)
        where = args.role + (f".{args.region}" if args.region else "")
        print(f"asset {where} -> {args.generation_id} ({row.get('size', '?')} bytes)")
    else:
        for row in metadata.list_assets(chimera, args.generation_id):
            region = row.get("region") or ""
            name = row["role"] + (f".{region}" if region else "")
            print(f"{name}  {row['content_type']}  {row['size']}")


if __name__ == "__main__":
    main()
