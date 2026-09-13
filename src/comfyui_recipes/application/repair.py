"""Repair one generation's hands/feet as a masked local redraw, recorded as a batch."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..domain.repair.controlnet import DEFAULT_CONTROL_STRENGTH
from ..domain.repair.loras import part_loras
from ..domain.repair.prompt import repair_prompt
from ..domain.repair.regions import rects_from_fractions, regions_from_pose
from ..infrastructure.comfyui.pose_graph import pose_from_outputs, pose_graph
from ..infrastructure.comfyui.repair_controlnet import control_hook
from ..infrastructure.comfyui.repair_graph import (
    DELIVERED_SUFFIX,
    MATTE_SUFFIX,
    repair_graph,
    source_prompts,
)
from ..infrastructure.comfyui.repair_model import anima_model_hook
from ..infrastructure.imaging.masks import mask_bbox_fraction, render_mask_png
from ..infrastructure.imaging.toe_template import reference_hint


@dataclass(frozen=True)
class RepairServices:
    management: object
    comfyui: object
    graph_from_png: Callable[[bytes], dict]
    image_size: Callable[[bytes], tuple[int, int]]
    git_metadata: Callable[[], dict]
    notifier: object
    output_root: Path
    emit: Callable[[str], None] = print
    pose_graph: Callable[..., dict] = pose_graph
    repair_graph: Callable[..., dict] = repair_graph


def _source_short(generations: Sequence[Mapping], generation_id: str) -> str:
    for entry in generations:
        if entry.get("id") == generation_id:
            return entry.get("short_id") or generation_id
    return generation_id


def _resolve_source(batch: dict, generation_id: str) -> str:
    """The redraw generation a repair actually redraws.

    A finalize batch's `generations` holds the raw redraw and the delivered
    sticker side by side; the sticker is smaller (repin/deliver crop and
    downscale it), so the largest by pixel count is the redraw regardless of
    which sibling the caller named.
    """
    if (batch.get("parameters") or {}).get("kind") != "hires-chain":
        return generation_id
    return max(
        batch["generations"],
        key=lambda g: g["image_width"] * g["image_height"])["id"]


def repair(generation_id: str, services: RepairServices, *,
          parts: Sequence[str] = ("hands", "feet"),
          regions: Sequence[Sequence[float]] = (),
          denoise: float = 0.6, seeds: Sequence[int] = (1, 2, 3, 4),
          size: int = 1024, pad: float = 1.0,
          lora: float | None = None,
          model: str | None = None,
          control: str | None = None,
          control_strength: float = DEFAULT_CONTROL_STRENGTH,
          key_prefix: str | None = None,
          context: dict | None = None, batch: dict | None = None) -> dict:
    if context is None:
        context = services.management.request(
            "GET", f"/api/v1/generations/{generation_id}/context")
    if batch is None:
        batch = services.management.request(
            "GET", f"/api/v1/batches/{context['batch']['id']}")
    source_id = _resolve_source(batch, generation_id)
    source_short = _source_short(batch.get("generations") or [], source_id)
    prefix = f"rep-{source_short}"

    picked = services.management.fetch_generation_image(source_id)
    # The job graph is what ran; the PNG prompt can be a cached older submission's.
    record = services.management.request(
        "GET", f"/api/v1/generations/{source_id}")
    source_graph = ((record.get("comfy_job") or {}).get("graph")
                    or services.graph_from_png(picked))
    width, height = services.image_size(picked)

    # A fresh staged name per run: ComfyUI reports a cached node's pose text
    # for nothing, so the pose pass must not hit the cache.
    staged = f"{prefix}-{uuid.uuid4().hex[:8]}"
    staged_source = services.comfyui.upload_image(f"{staged}-source.png", picked)

    circles = []
    if parts:
        pose_prompt_id = services.comfyui.submit(
            services.pose_graph(staged_source, prefix=prefix))
        pose_outputs = services.comfyui.wait_for_outputs(pose_prompt_id)
        pose = pose_from_outputs(pose_outputs)
        circles = regions_from_pose(pose, parts, pad)
    rects = rects_from_fractions(regions, width, height)
    if not circles and not rects:
        wanted = ", ".join(parts) if parts else "(none requested)"
        raise SystemExit(
            f"no repair region found: pose detection located none of "
            f"[{wanted}] on {source_id}, and no --region rectangles were given")

    mask_png = render_mask_png(width, height, circles, rects)
    mask_bbox = mask_bbox_fraction(width, height, circles, rects)
    staged_mask = services.comfyui.upload_image(f"{staged}-mask.png", mask_png)

    base_positive, base_negative = source_prompts(source_graph)
    positive = repair_prompt(base_positive, parts)
    loras = () if model else part_loras(parts, lora)
    model_hooks = [anima_model_hook(model)] if model else ()

    conditioning_hooks = []
    if control:
        staged_control_ref = services.comfyui.upload_image(
            f"{staged}-control.png", reference_hint(size))
        conditioning_hooks.append(
            control_hook(control, control_strength, staged_control_ref))

    git = services.git_metadata()
    batch_payload = {
        "idempotency_key": key_prefix or str(uuid.uuid4()),
        "raw_instruction": f"{source_id} の hands/feet を局所描き直し",
        "recipe": batch.get("recipe", "yukari"),
        "parameters": {
            "kind": "repair",
            "base_generation": source_id,
            "requested_generation": generation_id,
            "parts": list(parts),
            "regions": [list(region) for region in regions],
            "denoise": denoise,
            "size": size,
            "pad": pad,
            "lora": lora,
            "model": model,
            "control": control,
            "control_strength": control_strength if control else None,
            "seeds": list(seeds),
            "mask_bbox": list(mask_bbox),
        },
        "git_commit": git["commit"], "git_dirty": git["dirty"],
        "references": [{"source_generation_id": source_id,
                        "purpose": "rebuild", "aspect": "composition",
                        "instruction": "局所描き直しの元"}],
        "refinement": {"source_batch_id": batch["id"], "actor": "human",
                       "reason": "手足の局所描き直し"},
    }
    created = services.management.request("POST", "/api/v1/batches", batch_payload)
    services.output_root.mkdir(parents=True, exist_ok=True)

    ids: list[str] = []
    urls: list[str] = []
    last_raw_filename, last_raw = None, None
    for index, seed in enumerate(seeds):
        job_prefix = f"{prefix}-s{seed}"
        graph = services.repair_graph(
            source_graph, image_name=staged_source, mask_name=staged_mask,
            positive=positive, negative=base_negative, seed=seed,
            denoise=denoise, size=size, prefix=job_prefix, loras=loras,
            model_hooks=model_hooks, conditioning_hooks=conditioning_hooks)
        prompt_id = services.comfyui.submit(graph)
        services.emit(f"{job_prefix} {prompt_id}")
        outputs = services.comfyui.wait_for(prompt_id)
        mattes = [out for out in outputs if MATTE_SUFFIX in out["filename"]]
        delivereds = [out for out in outputs if DELIVERED_SUFFIX in out["filename"]]
        pictures = [out for out in outputs
                    if MATTE_SUFFIX not in out["filename"]
                    and DELIVERED_SUFFIX not in out["filename"]]
        if not pictures:
            raise SystemExit(f"{job_prefix} produced no raw output")
        raw_out = pictures[-1]
        raw = services.comfyui.fetch(raw_out)
        (services.output_root / raw_out["filename"]).write_bytes(raw)
        last_raw_filename, last_raw = raw_out["filename"], raw

        job_key = f"{key_prefix}:job:{index}" if key_prefix else str(uuid.uuid4())
        job = services.management.request(
            "POST", f"/api/v1/batches/{created['id']}/jobs",
            {"idempotency_key": job_key, "seed": seed, "index": index})
        services.management.request(
            "PATCH", f"/api/v1/jobs/{job['id']}",
            {"status": "queued", "comfy_prompt_id": prompt_id, "graph": graph})
        services.management.request(
            "PATCH", f"/api/v1/jobs/{job['id']}", {"status": "completed"})

        rendered = services.management.request(
            "POST", f"/api/v1/jobs/{job['id']}/generations",
            multipart=({"seed": seed, "original_filename": raw_out["filename"],
                        "comfy_output_index": 0},
                       "image", raw_out["filename"], raw, "image/png"))
        raw_generation_id = rendered["id"]
        ids.append(raw_generation_id)
        urls.append(rendered["canonical_url"])
        services.emit(f"{raw_out['filename']} -> {rendered['canonical_url']}")

        if delivereds:
            delivered_out = delivereds[-1]
            delivered = services.comfyui.fetch(delivered_out)
            (services.output_root / delivered_out["filename"]).write_bytes(delivered)
            rendered = services.management.request(
                "POST", f"/api/v1/jobs/{job['id']}/generations",
                multipart=({"seed": seed, "original_filename": delivered_out["filename"],
                            "comfy_output_index": 1},
                           "image", delivered_out["filename"], delivered, "image/png"))
            ids.append(rendered["id"])
            urls.append(rendered["canonical_url"])
            services.emit(f"{delivered_out['filename']} -> {rendered['canonical_url']}")

        if mattes:
            matte_out = mattes[-1]
            matte = services.comfyui.fetch(matte_out)
            (services.output_root / matte_out["filename"]).write_bytes(matte)
            services.management.request(
                "POST", f"/api/v1/generations/{raw_generation_id}/assets",
                multipart=({"role": "mask"}, "file", matte_out["filename"], matte,
                           "image/png"))
            services.emit(f"{matte_out['filename']} -> mask on {raw_generation_id}")

        services.management.request(
            "POST", f"/api/v1/generations/{raw_generation_id}/assets",
            multipart=({"role": "repair-mask"}, "file", f"{job_prefix}-mask.png",
                       mask_png, "image/png"))

        services.management.request(
            "PATCH", f"/api/v1/jobs/{job['id']}", {"status": "ingested"})

    services.management.request(
        "PATCH", f"/api/v1/batches/{created['id']}", {"status": "completed"})
    services.notifier.send(
        f"**repair** `{generation_id}`\n"
        f"**parts** {', '.join(parts) if parts else '(regions only)'}\n"
        f"**chimera** {urls[-1]}",
        last_raw_filename, last_raw)
    services.emit(f"batch {created.get('short_id', created['id'])} done")
    return {"batch_id": created["id"], "generation_ids": ids}
