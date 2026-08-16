#!/usr/bin/env python3
"""Colour an authored lineart with the bangs conditioned separately from the rest.

Every global dial has now failed to raise the bangs against the side hair. Seven
lineart variants, three linearts through the colour pass, four ControlNet
strength/reach settings: the lineart can reach a bangs-to-side ratio of 0.70, and
the colour pass lands at 0.59-0.65 regardless of what it is handed or how hard
the ControlNet holds it. A tag that helps the bangs helps the side hair by the
same amount, because it is the same prompt for both.

So this stops asking globally. ConditioningSetMask pins a second, strand-heavy
prompt to a rectangle over the bangs, ConditioningCombine adds it to the ordinary
one, and the ControlNet is applied after the combine so the line still holds
everywhere. No custom nodes -- this is all core ComfyUI.

The mask is a rectangle rather than a traced silhouette on purpose: a rectangle
is reproducible and has three numbers to tune, and the question being asked first
is whether regional conditioning moves the ratio at all. If it does, a real mask
is worth cutting.
"""

from __future__ import annotations

import argparse
import json
import shutil
import urllib.request
from pathlib import Path

import colorize_lineart
from comfy_host import DEFAULT_HOST, DEFAULT_PORT, ensure_local, stage_input

REPO = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO / ".local/ComfyUI/output"
INPUT_DIR = REPO / ".local/ComfyUI/input"

WIDTH, HEIGHT = 1024, 1280

# The box the measurements use is x 300-760, y 30-300. The bangs rectangle is a
# little wider and taller so the feather falls outside the region being scored
# rather than across it.
#
# "bangs" answers whether the two regions can be moved apart. "hair" gives up on
# separating them and asks for more line everywhere the hair is -- once the
# region prompt is known to raise what it covers, covering more of the hair is
# the way to raise the whole of it.
BANGS = (240, 0, 580, 360)
MASKS = {
    "bangs": [BANGS],
    "hair": [BANGS, (60, 240, 320, 620), (640, 240, 340, 620)],
}
FEATHER = 48

# The global prompt, the negative, the ControlNet table and the render blocks are
# colorize_lineart's. This script is that pipeline with a region added, so the two
# have to stay in step -- they were byte-identical copies until this import, which
# is exactly the arrangement that drifts.
NEGATIVE = colorize_lineart.NEGATIVE
CONTROLNETS = colorize_lineart.CONTROLNETS
RENDERS = colorize_lineart.RENDERS

# Only what the bangs are short of. Naming the character or the costume here
# would put a second face in the region.
REGION = (
    "(detailed hair:1.7), (defined hair strands:1.8), (hair strand outline:1.5), "
    "(parted bangs:1.4), (hair between eyes:1.3), "
    "(black lineart:1.45), (defined lines:1.35), (crisp lines:1.25)"
)


def build(filename: str, rects: list[tuple[int, int, int, int]], region_strength: float,
          controlnet: str, invert: bool, cn_strength: float, cn_end: float,
          seed: int, render: str, detail_amount: float | None, prefix: str) -> dict:
    graph = {
        "1": {"class_type": "LoadImage", "inputs": {"image": filename}},
        "4": {"class_type": "DiffusersLoader", "inputs": {"model_path": "hassaku-il-v22"}},
        "11": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": controlnet}},
        # An empty full-size mask with the rectangles added into it one at a time.
        "20": {"class_type": "SolidMask", "inputs": {
            "value": 0.0, "width": WIDTH, "height": HEIGHT}},
    }
    mask_src, node_id = ["20", 0], 21
    for x, y, w, h in rects:
        solid, comp = str(node_id), str(node_id + 1)
        graph[solid] = {"class_type": "SolidMask", "inputs": {
            "value": 1.0, "width": w, "height": h}}
        graph[comp] = {"class_type": "MaskComposite", "inputs": {
            "destination": mask_src, "source": [solid, 0],
            "x": x, "y": y, "operation": "add"}}
        mask_src, node_id = [comp, 0], node_id + 2

    # Numbered clear of the loop above: with more than one rectangle the loop
    # reaches into the 20s, and a fixed id here would overwrite one of its
    # SolidMasks and leave the composite chain referring back to this node.
    graph["40"] = {"class_type": "FeatherMask", "inputs": {
        "mask": mask_src, "left": FEATHER, "top": 0,
        "right": FEATHER, "bottom": FEATHER}}

    graph.update({
        "6": {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["4", 1], "text": colorize_lineart.positive_for(render)}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": NEGATIVE}},
        "30": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": REGION}},
        "31": {"class_type": "ConditioningSetMask", "inputs": {
            "conditioning": ["30", 0], "mask": ["40", 0],
            "strength": region_strength, "set_cond_area": "default"}},
        "32": {"class_type": "ConditioningCombine", "inputs": {
            "conditioning_1": ["6", 0], "conditioning_2": ["31", 0]}},

        # After the combine, so the line is held over the whole frame and not
        # only outside the region.
        "12": {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["32", 0], "negative": ["7", 0], "control_net": ["11", 0],
            "image": ["2", 0] if invert else ["1", 0], "strength": cn_strength,
            "start_percent": 0.0, "end_percent": cn_end}},

        "5": {"class_type": "EmptyLatentImage", "inputs": {
            "batch_size": 1, "width": WIDTH, "height": HEIGHT}},
        "9": {"class_type": "SaveImage", "inputs": {
            "images": ["8", 0], "filename_prefix": prefix}},
    })
    sampling, latent_out = colorize_lineart.sampler_nodes(
        ["4", 0], ["12", 0], ["12", 1], ["5", 0], seed, detail_amount)
    graph.update(sampling)
    graph["8"] = {"class_type": "VAEDecode", "inputs": {
        "samples": latent_out, "vae": ["4", 2]}}
    if invert:
        graph["2"] = {"class_type": "ImageInvert", "inputs": {"image": ["1", 0]}}
    return graph


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--line", default="lb-parted", help="output/ basename of the lineart")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--mask", choices=sorted(MASKS), default="bangs",
                        help="bangs separates the two regions; hair raises both")
    parser.add_argument("--region-strength", action="append", type=float, default=[],
                        help="ConditioningSetMask strength; repeat for a ladder")
    parser.add_argument("--controlnet", choices=sorted(CONTROLNETS), default="canny")
    parser.add_argument("--render", choices=sorted(RENDERS), default="cg",
                        help="how flat the colour pass is asked to be")
    parser.add_argument("--cn-strength", type=float, default=0.6)
    parser.add_argument("--cn-end", type=float, default=0.8)
    parser.add_argument("--detail-amount", type=float, action="append", default=[],
                        help="route through Detail Daemon at this amount; SDXL "
                             "wants under 0.25. 0.0 is the rebuild-only control")
    parser.add_argument("--seed", type=int, default=111222333)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    src = ensure_local(
        f"{args.line}_00001_.png", OUTPUT_DIR, host=args.host, port=args.port
    )
    if not src.exists():
        raise SystemExit(f"no such lineart: {src}")
    # stage_input keeps the source basename; this pipeline renames on the way
    # in so a human browsing the flat input dir can tell which script staged
    # the file, so rename locally first and hand stage_input that copy.
    renamed = INPUT_DIR / f"br-src-{args.line}.png"
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, renamed)
    filename = stage_input(renamed, INPUT_DIR, host=args.host, port=args.port)

    rects = MASKS[args.mask]
    controlnet, invert = CONTROLNETS[args.controlnet]
    for strength in args.region_strength or [0.0, 0.6, 1.0, 1.5]:
        for detail in args.detail_amount or [None]:
            tail = "" if args.render == "cg" else f"-{args.render}"
            if detail is not None:
                tail += f"-d{int(round(detail * 100)):03d}"
            prefix = (f"br-{args.line}-{args.mask}-{args.controlnet}"
                      f"-r{int(round(strength * 100)):03d}{tail}")
            print(f"{prefix:50s} region={strength}  cn={args.cn_strength}/{args.cn_end}"
                  f"  detail={detail}")
            if args.dry_run:
                continue
            req = urllib.request.Request(
                f"http://{args.host}:{args.port}/prompt",
                data=json.dumps({"prompt": build(
                    filename, rects, strength, controlnet, invert,
                    args.cn_strength, args.cn_end, args.seed, args.render,
                    detail, prefix)}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                print("   ->", json.load(resp)["prompt_id"])


if __name__ == "__main__":
    main()
