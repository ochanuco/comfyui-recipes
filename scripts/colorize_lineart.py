#!/usr/bin/env python3
"""Second pass of "line first, then colour": colour an authored lineart via ControlNet.

Pass 1 (ln-lineart / ln-coloring) established the thing every prompt-side sweep
had failed to get: with no fill available, hassaku draws the bangs as strands
rather than as a plane. Six extractors across three sensitivities could not
recover those lines from a finished flat-coloured render, because they were
never drawn -- so the line has to exist before the colour does.

This pass holds that lineart with a ControlNet and renders colour under it. The
axis is ControlNet strength and how long it stays engaged: too weak and the
colour pass redraws the hair as a mass again, which is the failure this whole
approach exists to avoid; too strong and the render is a tinted line drawing
with no shading of its own.

The lineart is black-on-white and the ControlNets here expect white-on-black, so
it is inverted before it is handed over.
"""

from __future__ import annotations

import argparse
import json
import shutil
import urllib.request
from pathlib import Path

from comfy_host import DEFAULT_HOST, DEFAULT_PORT, ensure_local, stage_input

REPO = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO / ".local/ComfyUI/output"
INPUT_DIR = REPO / ".local/ComfyUI/input"

# invert: canny and softedge are trained on white-on-black edge maps, so a
# black-on-white lineart has to be flipped for them. lineart_anime is trained on
# the drawing itself and takes it as it is -- feeding it an inverted one is
# handing it a photographic negative of what it expects.
CONTROLNETS = {
    "canny": ("noob-canny-fp16.safetensors", True),
    "softedge": ("ill-softedge-fp16.safetensors", True),
    "lineart": ("noob-lineart-anime-fp16.safetensors", False),
}

# The colour prompt. (flat color) and the sticker block are not in it, because
# they are what erased the strand lines in the first place -- but that was
# measured when the prompt was the only thing asking for a line. The ControlNet
# holds the drawing now, and a lineart-trained one holds it well, so whether the
# flat block can come back is a live question rather than a settled one. Without
# it the colour pass renders in the base's own smooth CG shading.
POSITIVE = (
    "best quality, absurdres, 1girl, solo, hamakaze (kancolle), (grey hair:1.3), "
    "short hair, (hair over one eye:1.35), (eyes visible through hair:1.2), "
    "(blue eyes:1.25), (hairclip:1.25), hair ornament, (serafuku:1.3), "
    "(white shirt:1.25), (blue sailor collar:1.35), (yellow neckerchief:1.3), "
    "kantai collection, (solo:1.5), (upper body:1.4), looking at viewer, "
    "(closed mouth:1.2), (smug:1.4), (half-closed eyes:1.3), (tareme:1.2), "
    "eyelashes, (pale skin:1.15), (realistic:1.3), "
    "(detailed hair:1.5), (defined hair strands:1.55), (hair strand outline:1.3), "
    "(black lineart:1.35), (defined lines:1.25), "
    "(cel shading:1.45), (sharp shadow edges:1.35), (two-tone shading:1.3), "
    "(simple background:1.3), (grey background:1.2)"
)
NEGATIVE = (
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text, (disembodied eye:1.4), "
    "(impasto:1.25), (painterly:1.25), (oil painting (medium):1.2), "
    "(monochrome:1.3), (greyscale:1.3), (sketch:1.2)"
)

# Appended to POSITIVE. "cg" is what the colour pass does when nothing asks it to
# flatten; the rest walk back toward the flat sticker look the recipe started
# from, one block at a time, so whichever one costs the line can be identified.
RENDERS = {
    "cg": "",
    "flat": "(flat color:1.3)",
    "flat-sticker": "(flat color:1.3), (white outline:1.6), outline, sticker",
    # (realistic:1.3) sits in the face block and is a second, separate source of
    # rendered-looking shading, so it gets its own rung rather than riding along.
    "flat-noreal": "(flat color:1.3)",
}

RUNGS = [
    ("s60-e80", 0.6, 0.8),
    # Strength and reach are separate questions and the first ladder confounded
    # them. Releasing at 80% hands the last fifth of the render back to the
    # colour pass, which is where a lineart's extra bangs detail was suspected of
    # being redrawn away; this rung holds the same strength to the end instead.
    ("s60-e100", 0.6, 1.0),
    ("s80-e80", 0.8, 0.8),
    ("s80-e100", 0.8, 1.0),
    ("s100-e100", 1.0, 1.0),
]


SAMPLER, SCHEDULER, STEPS, CFG = "dpmpp_2m", "karras", 30, 5.0


def sampler_nodes(model, positive, negative, latent, seed: int,
                  detail_amount: float | None, sampler: str = SAMPLER,
                  scheduler: str = SCHEDULER, steps: int = STEPS,
                  cfg: float = CFG) -> tuple[dict, list]:
    """The sampling half of a graph, as plain KSampler or through Detail Daemon.

    Detail Daemon wraps a SAMPLER rather than sitting beside one, so using it
    means rebuilding on SamplerCustomAdvanced -- noise, guider, sampler and
    sigmas as separate nodes. Returns the nodes and the ref to feed VAEDecode.

    detail_amount None keeps the plain KSampler. 0.0 does not: it still goes the
    custom-sampler route, which is the control that says whether the rebuild
    alone changes the image.

    The sampler settings are arguments rather than constants because the other
    caller is queue_dq3, whose recipe sets its own and must not be altered by
    being routed through here.
    """
    if detail_amount is None:
        return {"3": {"class_type": "KSampler", "inputs": {
            "model": model, "positive": positive, "negative": negative,
            "latent_image": latent, "seed": seed, "steps": steps, "cfg": cfg,
            "sampler_name": sampler, "scheduler": scheduler, "denoise": 1.0}}}, ["3", 0]

    return {
        "50": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "51": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": sampler}},
        "52": {"class_type": "DetailDaemonSamplerNode", "inputs": {
            "sampler": ["51", 0], "detail_amount": detail_amount,
            "start": 0.2, "end": 0.8, "bias": 0.5, "exponent": 1.0,
            "start_offset": 0.0, "end_offset": 0.0, "fade": 0.0,
            "smooth": True, "cfg_scale_override": 0.0}},
        "53": {"class_type": "BasicScheduler", "inputs": {
            "model": model, "scheduler": scheduler, "steps": steps, "denoise": 1.0}},
        "54": {"class_type": "CFGGuider", "inputs": {
            "model": model, "positive": positive, "negative": negative, "cfg": cfg}},
        "55": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["50", 0], "guider": ["54", 0], "sampler": ["52", 0],
            "sigmas": ["53", 0], "latent_image": latent}},
    }, ["55", 0]


def positive_for(render: str) -> str:
    text = POSITIVE
    if render == "flat-noreal":
        text = text.replace(", (realistic:1.3)", "")
        assert text != POSITIVE, "the realistic tag moved; fix this replacement"
    extra = RENDERS[render]
    return f"{text}, {extra}" if extra else text


def build(filename: str, controlnet: str, invert: bool, strength: float,
          end: float, seed: int, render: str, prefix: str) -> dict:
    hint = ["2", 0] if invert else ["1", 0]
    graph = {
        "1": {"class_type": "LoadImage", "inputs": {"image": filename}},
        "4": {"class_type": "DiffusersLoader", "inputs": {"model_path": "hassaku-il-v22"}},
        "11": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": controlnet}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["4", 1], "text": positive_for(render)}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": NEGATIVE}},
        "12": {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["6", 0], "negative": ["7", 0], "control_net": ["11", 0],
            "image": hint, "strength": strength,
            "start_percent": 0.0, "end_percent": end}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {
            "batch_size": 1, "width": 1024, "height": 1280}},
        "3": {"class_type": "KSampler", "inputs": {
            "model": ["4", 0], "positive": ["12", 0], "negative": ["12", 1],
            "latent_image": ["5", 0], "seed": seed, "steps": 30, "cfg": 5.0,
            "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {
            "images": ["8", 0], "filename_prefix": prefix}},
    }
    if invert:
        graph["2"] = {"class_type": "ImageInvert", "inputs": {"image": ["1", 0]}}
    return graph


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--line", default="ln-lineart", help="output/ basename of the pass-1 lineart")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--controlnet", choices=sorted(CONTROLNETS), default="canny")
    parser.add_argument("--render", action="append", default=[], choices=sorted(RENDERS),
                        help="how flat the colour pass is asked to be; repeat for a ladder")
    parser.add_argument("--seed", type=int, default=111222333)
    parser.add_argument(
        "--only", action="append", default=[], choices=[r[0] for r in RUNGS],
        help="run just these strength rungs; the ladder is for comparing, "
             "s60-e80 is the one to use")
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
    renamed = INPUT_DIR / f"cz-src-{args.line}.png"
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, renamed)
    filename = stage_input(renamed, INPUT_DIR, host=args.host, port=args.port)

    controlnet, invert = CONTROLNETS[args.controlnet]
    for render in args.render or ["cg"]:
        for suffix, strength, end in RUNGS:
            if args.only and suffix not in args.only:
                continue
            tail = suffix if render == "cg" else f"{suffix}-{render}"
            prefix = f"cz-{args.line}-{args.controlnet}-{tail}"
            print(f"{prefix:44s} strength={strength} end={end}"
                  f" hint={'inverted' if invert else 'as drawn'}")
            if args.dry_run:
                continue
            req = urllib.request.Request(
                f"http://{args.host}:{args.port}/prompt",
                data=json.dumps({"prompt": build(
                    filename, controlnet, invert, strength, end,
                    args.seed, render, prefix)}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                print("   ->", json.load(resp)["prompt_id"])


if __name__ == "__main__":
    main()
