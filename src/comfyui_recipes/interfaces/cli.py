"""The single public command-line interface for comfyui-recipes."""

from __future__ import annotations

import argparse
import json
import math
import socket
from pathlib import Path

from ..application import metadata
from ..application.catalog import build_catalog
from ..application.catalog import publish_catalog as publish_catalog_document
from ..application.finalize import finalize
from ..domain.yukari.recipe import TOE_GUARD
from ..application.generate import generate
from ..application.masked_redraw import masked_redraw
from ..application.repair import repair
from ..application.watch import WatchServices, watch
from ..application.work import (
    FINALIZE_DIAL_KEYS,
    REPAIR_DIAL_KEYS,
    dials_scope,
    fetch_source,
    resolve_dial,
    work,
)
from ..domain.repair.controlnet import CONTROL_MODELS, DEFAULT_CONTROL_STRENGTH
from ..domain.repair.loras import DEFAULT_PART_LORA_WEIGHT
from ..domain.repair.models import MODELS
from ..domain.yukari.costumes import COSTUMES
from ..domain.yukari.delivery_style import STROKE_LIGHTS
from ..domain.yukari.poses import POSES
from ..domain.yukari.recipe import negative, positive
from ..domain.yukari_anima.costumes import COSTUMES as ANIMA_COSTUMES
from ..domain.yukari_anima.expressions import EXPRESSIONS as ANIMA_EXPRESSIONS
from ..domain.yukari_anima.poses import POSES as ANIMA_POSES
from ..domain.yukari_anima.recipe import negative as anima_negative
from ..domain.yukari_anima.recipe import positive as anima_positive
from ..domain.yukari_sketch.costumes import COSTUMES as SKETCH_COSTUMES
from ..domain.yukari_sketch.poses import POSES as SKETCH_POSES
from ..domain.yukari_sketch.recipe import departures as sketch_departures
from ..domain.yukari_sketch.recipe import lineage as sketch_lineage
from ..domain.yukari_sketch.recipe import negative as sketch_negative
from ..domain.yukari_sketch.recipe import plain_request as sketch_plain_request
from ..domain.yukari_sketch.recipe import positive as sketch_positive
from ..infrastructure.chimera.client import ChimeraClient
from ..infrastructure.comfyui.client import ComfyUIClient
from ..infrastructure.notifications.discord import DiscordNotifier
from ..infrastructure.repository import discover_repository, git_metadata
from .agent import (
    build_finalize_services,
    build_generate_services,
    build_masked_redraw_services,
    build_repair_services,
    wire_work_services,
)


def _number_or_word(raw: str) -> float | str:
    """argparse type= for a dial-eligible flag: a recipe word passes through
    as a string for `_resolve_word_args` to resolve once the generation's
    recipe is known.
    """
    try:
        return float(raw)
    except ValueError:
        return raw


def _resolve_word_args(chimera: ChimeraClient, generation_id: str, scope: str,
                       values: dict) -> tuple[dict | None, dict | None, dict]:
    """Resolve any word (string) values in `values` against the source
    generation's recipe dials for `scope`; numbers and `None` pass through.

    Returns the `context`/`batch` `fetch_source` fetched (or `(None, None)`
    if no word was given, so the numeric-only path stays fetch-free) so the
    caller can pass them into finalize()/repair() and avoid re-fetching.
    """
    if not any(isinstance(value, str) for value in values.values()):
        return None, None, values
    context, batch, recipe = fetch_source(chimera, generation_id)
    dials = dials_scope(recipe, scope)
    resolved = {}
    for key, value in values.items():
        try:
            resolved[key] = resolve_dial(key, value, dials)
        except ValueError as error:
            raise SystemExit(str(error)) from error
    return context, batch, resolved


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

    work_parser = commands.add_parser(
        "work", help="claim and execute rows from chimera's requests queue")
    work_parser.add_argument(
        "--interval", type=_positive_finite_seconds, default=30)
    work_parser.add_argument("--once", action="store_true")
    work_parser.add_argument("--dry-run", action="store_true")
    work_parser.add_argument("--worker-id", default=socket.gethostname())
    work_parser.add_argument(
        "--kinds", default="generate,finalize,repair,masked_redraw",
        help="comma-separated request kinds to claim")
    work_parser.add_argument(
        "--no-hub", action="store_true",
        help="poll only; do not open the WorkerHub websocket")
    work_parser.add_argument(
        "--no-catalog", action="store_true",
        help="skip publishing the recipe catalog to chimera at startup")

    finalize_parser = commands.add_parser("finalize", help="deliver one picked render")
    finalize_parser.add_argument("generation_id")
    finalize_parser.add_argument("--denoise", type=_number_or_word)
    finalize_parser.add_argument("--handdrawn", action="store_true")
    finalize_parser.add_argument(
        "--repin", action="store_true", help="repin the delivery's palette")
    finalize_parser.add_argument(
        "--toe-guard", type=_number_or_word, nargs="?", const=TOE_GUARD, metavar="WEIGHT",
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
        "--deliver-size", type=int, metavar="LONGEST",
        help="downscale the delivered file to this longest side (lanczos) "
             "after the redraw; the redraw itself still runs at --size")
    route_group = finalize_parser.add_mutually_exclusive_group()
    route_group.add_argument(
        "--latent-route", dest="latent_route", action="store_const",
        const=True, default=None,
        help="upscale the latent instead of the decoded image; the staircase "
             "it leaves is what the redraw turns into visible stroke")
    route_group.add_argument(
        "--pixel-route", dest="latent_route", action="store_const",
        const=False,
        help="force the pixel-space route on a recipe (yukari-sketch) whose "
             "own default is the latent route")
    finalize_parser.add_argument(
        "--finalizer", metavar="MODEL",
        help="DiffusersLoader model_path that redraws instead of the base "
             "pass's own checkpoint")
    finalize_parser.add_argument(
        "--keep-scene", action="store_true",
        help="deliver the redraw uncut, background and all")
    transparent_group = finalize_parser.add_mutually_exclusive_group()
    transparent_group.add_argument(
        "--transparent", dest="transparent", action="store_const",
        const=True, default=None,
        help="deliver the figure alone as an RGBA cutout (yukari-sketch's "
             "default)")
    transparent_group.add_argument(
        "--opaque", dest="transparent", action="store_const", const=False,
        help="composite on the backdrop with the purple stroke instead")
    finalize_parser.add_argument("--recolor", action="store_true")
    finalize_parser.add_argument(
        "--keep-legwear", nargs="?", const=0.62, type=_number_or_word, default=None,
        metavar="COL_CUT",
        help="keep the asserted legwear verbatim through repin; the value is "
             "the width share the legs stay left of (default 0.62)")
    finalize_parser.add_argument(
        "--backdrop", metavar="#RRGGBB|stripes",
        help="backdrop under the sticker -- a colour or a named pattern; "
             "setting it delivers opaque instead of the transparent cutout")
    finalize_parser.add_argument(
        "--upscale",
        choices=["bicubic", "nearest-exact", "bilinear", "lanczos"],
        help="pixel-route upscale method feeding the redraw, overriding the "
             "delivery's own bicubic default")
    finalize_parser.add_argument(
        "--lora-strength", type=_number_or_word, metavar="STRENGTH",
        help="strength the redraw's LoRA runs at, overriding the recipe's "
             "own default")
    finalize_parser.add_argument(
        "--stroke-light", choices=sorted(STROKE_LIGHTS),
        help="light direction the purple stroke is shaded from; thin toward "
             "it, thick away from it")
    finalize_parser.add_argument(
        "--repair", metavar="PARTS",
        help="comma-separated hands/feet to reroll in this same submission "
             "(default: off)")
    finalize_parser.add_argument(
        "--repair-region", dest="repair_regions", action="append",
        metavar="X0,Y0,X1,Y1",
        help="fractional rectangle [0..1], in the redraw's own frame, added "
             "to the repair mask; repeatable")
    finalize_parser.add_argument(
        "--repair-denoise", type=_number_or_word, default=0.6,
        help="the repair reroll's own denoise")
    finalize_parser.add_argument(
        "--repair-pad", type=float, default=1.0,
        help="multiplier on the repair's auto-detected region radius")
    finalize_parser.add_argument(
        "--repair-size", type=int, default=1024, metavar="LONGEST",
        help="the repair crop's target long side")
    finalize_parser.add_argument(
        "--repair-lora", type=_number_or_word, nargs="?",
        const=DEFAULT_PART_LORA_WEIGHT, metavar="WEIGHT",
        help="load each repaired part's own LoRA (Feet XL / Hands XL) inside "
             "the repair crop, at this strength; off by default")

    repair_parser = commands.add_parser(
        "repair", help="masked local redraw of hands/feet on an existing generation")
    repair_parser.add_argument("generation_id")
    repair_parser.add_argument(
        "--parts", default="hands,feet",
        help="comma-separated: hands, feet (default: both)")
    repair_parser.add_argument(
        "--region", dest="regions", action="append", metavar="X0,Y0,X1,Y1",
        help="fractional rectangle [0..1] added to the mask; repeatable")
    repair_parser.add_argument("--denoise", type=_number_or_word, default=0.6)
    repair_parser.add_argument(
        "--seeds", default="1,2,3,4",
        help="comma-separated seeds; one job per seed")
    repair_parser.add_argument(
        "--size", type=int, default=1024, metavar="LONGEST",
        help="crop target's longest side")
    repair_parser.add_argument(
        "--pad", type=float, default=1.0,
        help="multiplier on the auto region radius")
    repair_parser.add_argument(
        "--lora", type=_number_or_word, nargs="?", const=DEFAULT_PART_LORA_WEIGHT,
        metavar="WEIGHT",
        help="load each repaired part's own LoRA (Feet XL / Hands XL) inside "
             "the crop, at this strength; off by default")
    repair_parser.add_argument(
        "--model", choices=sorted(MODELS),
        help="sample the crop on this checkpoint instead of the source's own; "
             "skips the part LoRA chain, which is Illustrious-only")
    repair_parser.add_argument(
        "--control", choices=sorted(CONTROL_MODELS), metavar="SIGNAL",
        help="route the crop's conditioning through this ControlNet signal; "
             "off by default")
    repair_parser.add_argument(
        "--control-strength", type=float, default=DEFAULT_CONTROL_STRENGTH,
        metavar="STRENGTH",
        help="the ControlNet's own strength, used only with --control")

    masked_redraw_parser = commands.add_parser(
        "masked_redraw", help="masked local redraw of a caller-given region")
    masked_redraw_parser.add_argument("generation_id")
    masked_redraw_parser.add_argument(
        "--region", dest="regions", action="append", required=True,
        metavar="X0,Y0,X1,Y1",
        help="fractional rectangle [0..1] added to the mask; repeatable, at "
             "least one required")
    masked_redraw_parser.add_argument(
        "--prompt-patch", required=True,
        help="text appended to the source's own positive prompt after the "
             "face/hair/framing drop")
    # A queued masked_redraw row's own `denoise` resolves a dial word the
    # same as repair's (see dials_scope(recipe, "repair") in work.py); the
    # CLI flag stays numeric-only here since masked_redraw is not one of the
    # named-dial commands this branch's CLI support covers.
    masked_redraw_parser.add_argument("--denoise", type=float, default=0.45)
    masked_redraw_parser.add_argument(
        "--mask-padding", type=int, default=0, metavar="PIXELS",
        help="InpaintCropImproved mask_expand_pixels")
    masked_redraw_parser.add_argument(
        "--mask-feather", type=int, default=32, metavar="PIXELS",
        help="InpaintCropImproved mask_blend_pixels")
    masked_redraw_parser.add_argument(
        "--size", type=int, default=1024, metavar="LONGEST",
        help="crop target's longest side")
    masked_redraw_parser.add_argument(
        "--seeds", default="1,2,3,4",
        help="comma-separated seeds; one job per seed")

    catalog_parser = commands.add_parser(
        "catalog", help="print the recipe catalog chimera composes requests from")
    catalog_parser.add_argument(
        "--publish", action="store_true",
        help="also PUT the catalog to chimera and print its response")

    metadata_parser = commands.add_parser("metadata", help="manage generation metadata")
    metadata_commands = metadata_parser.add_subparsers(
        dest="metadata_command", required=True)
    semantic = metadata_commands.add_parser("semantic")
    semantic.add_argument("generation_id")
    semantic.add_argument("file", type=Path)
    tag = metadata_commands.add_parser("tag")
    tag.add_argument("generation_id")
    tag.add_argument("name")
    publish = metadata_commands.add_parser("publish")
    publish.add_argument("generation_id")
    publish.add_argument("--url")
    publish.add_argument("--idempotency-key")
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

    sketch_parser = commands.add_parser("sketch", help="inspect the Yukari-sketch domain")
    sketch_commands = sketch_parser.add_subparsers(dest="sketch_command", required=True)
    sketch_prompt = sketch_commands.add_parser("prompt")
    sketch_prompt.add_argument("--pose", required=True, choices=sorted(SKETCH_POSES))
    sketch_prompt.add_argument("--costume", choices=sorted(SKETCH_COSTUMES))
    sketch_prompt.add_argument("--json", action="store_true")
    sketch_lineage_parser = sketch_commands.add_parser("lineage")
    sketch_lineage_parser.add_argument("--pose", choices=sorted(SKETCH_POSES))
    sketch_lineage_parser.add_argument("--json", action="store_true")
    sketch_plain_parser = sketch_commands.add_parser("plain")
    sketch_plain_parser.add_argument("--pose", required=True, choices=sorted(SKETCH_POSES))
    sketch_plain_parser.add_argument("--seed", type=int, required=True)
    sketch_plain_parser.add_argument("--costume", choices=sorted(SKETCH_COSTUMES))
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
    if args.command == "sketch":
        if args.sketch_command == "lineage":
            data = ({args.pose: sketch_departures(args.pose)} if args.pose
                    else sketch_lineage())
            if args.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                for name, dep in data.items():
                    parent = dep["parent"] or "base"
                    print(f"{name}  <- {parent}  "
                         f"costume={SKETCH_POSES[name].costume}")
                    for part, changes in dep["parts"].items():
                        marker = (" (full override)"
                                 if part == "face" and dep["face_override"]
                                 else "")
                        print(f"  {part}:{marker} " + " ".join(changes))
            return
        if args.sketch_command == "plain":
            payload = sketch_plain_request(args.pose, args.seed, args.costume)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return
        prompts = {
            "positive": sketch_positive(args.pose, args.costume),
            "negative": sketch_negative(args.pose, args.costume),
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
        services = build_generate_services(
            chimera, comfyui, notifier, repository, repository_metadata)
        generate(args.request, services, dry_run=args.dry_run, force=args.force)
        return
    if args.command == "watch":
        services = build_generate_services(
            chimera, comfyui, notifier, repository, repository_metadata)
        watch_services = WatchServices(management=chimera, generate_services=services)
        watch(watch_services, interval=args.interval, once=args.once,
              dry_run=args.dry_run)
        return
    if args.command == "work":
        work_services = wire_work_services(
            chimera, comfyui, notifier, repository, repository_metadata,
            worker_id=args.worker_id,
            kinds=tuple(kind.strip() for kind in args.kinds.split(",") if kind.strip()),
            hub=not args.no_hub,
        )
        work(work_services, interval=args.interval, once=args.once,
             dry_run=args.dry_run, publish_catalog=not args.no_catalog)
        return
    if args.command == "finalize":
        services = build_finalize_services(
            chimera, comfyui, notifier, repository, repository_metadata)
        repair_parts = ([part.strip() for part in args.repair.split(",") if part.strip()]
                        if args.repair else None)
        repair_regions = [[float(value) for value in region.split(",")]
                          for region in (args.repair_regions or [])]
        context, _batch, dial_values = _resolve_word_args(
            chimera, args.generation_id, "finalize",
            {key: getattr(args, key) for key in FINALIZE_DIAL_KEYS})
        finalize(args.generation_id, services, denoise=dial_values["denoise"],
                 handdrawn=args.handdrawn, apply_repin=args.repin,
                 apply_skin=args.skin,
                 apply_recolor=args.recolor,
                 keep_legwear=dial_values["keep_legwear"],
                 keep_scene=args.keep_scene,
                 transparent=args.transparent,
                 size=args.size,
                 latent_route=args.latent_route,
                 finalizer=args.finalizer,
                 toe_guard=dial_values["toe_guard"],
                 backdrop=args.backdrop,
                 upscale=args.upscale,
                 lora_strength=dial_values["lora_strength"],
                 deliver_size=args.deliver_size,
                 stroke_light=args.stroke_light,
                 repair=repair_parts,
                 repair_regions=repair_regions,
                 repair_denoise=dial_values["repair_denoise"],
                 repair_pad=args.repair_pad,
                 repair_size=args.repair_size,
                 repair_lora=dial_values["repair_lora"],
                 context=context)
        return
    if args.command == "catalog":
        git = repository_metadata()
        document = build_catalog(git)
        print(json.dumps(document, indent=2, ensure_ascii=False))
        if args.publish:
            response = publish_catalog_document(chimera, git, catalog=document)
            print(json.dumps(response, indent=2, ensure_ascii=False))
        return
    if args.command == "repair":
        services = build_repair_services(
            chimera, comfyui, notifier, repository, repository_metadata)
        parts = [part.strip() for part in args.parts.split(",") if part.strip()]
        regions = [[float(value) for value in region.split(",")]
                  for region in (args.regions or [])]
        seeds = [int(seed.strip()) for seed in args.seeds.split(",") if seed.strip()]
        context, batch, dial_values = _resolve_word_args(
            chimera, args.generation_id, "repair",
            {key: getattr(args, key) for key in REPAIR_DIAL_KEYS})
        repair(args.generation_id, services, parts=parts, regions=regions,
              denoise=dial_values["denoise"], seeds=seeds, size=args.size,
              pad=args.pad, lora=dial_values["lora"], model=args.model,
              control=args.control, control_strength=args.control_strength,
              context=context, batch=batch)
        return
    if args.command == "masked_redraw":
        services = build_masked_redraw_services(
            chimera, comfyui, notifier, repository, repository_metadata)
        regions = [[float(value) for value in region.split(",")]
                  for region in args.regions]
        seeds = [int(seed.strip()) for seed in args.seeds.split(",") if seed.strip()]
        masked_redraw(args.generation_id, services, regions=regions,
                      prompt_patch=args.prompt_patch, denoise=args.denoise,
                      mask_padding=args.mask_padding, mask_feather=args.mask_feather,
                      size=args.size, seeds=seeds)
        return

    if args.metadata_command == "semantic":
        metadata.put_semantic(chimera, args.generation_id, args.file)
        print(f"semantic -> {args.generation_id}")
    elif args.metadata_command == "tag":
        metadata.add_tag(chimera, args.generation_id, args.name)
        print(f"tag {args.name!r} -> {args.generation_id}")
    elif args.metadata_command == "publish":
        metadata.record_publication(
            chimera, args.generation_id, url=args.url,
            idempotency_key=args.idempotency_key)
        where = f" ({args.url})" if args.url else ""
        print(f"publish -> {args.generation_id}{where}")
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
