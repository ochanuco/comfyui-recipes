"""Redraw an arbitrary caller-given region of a generation, recorded as a batch."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..domain.repair.prompt import masked_redraw_prompt
from ..domain.repair.regions import rects_from_fractions
from ..infrastructure.comfyui.repair_graph import (
    DELIVERED_SUFFIX,
    MATTE_SUFFIX,
    masked_redraw_graph,
    source_prompts,
)
from ..infrastructure.imaging.masks import mask_bbox_fraction, render_mask_png


@dataclass(frozen=True)
class MaskedRedrawServices:
    management: object
    comfyui: object
    graph_from_png: Callable[[bytes], dict]
    image_size: Callable[[bytes], tuple[int, int]]
    git_metadata: Callable[[], dict]
    notifier: object
    output_root: Path
    emit: Callable[[str], None] = print
    masked_redraw_graph: Callable[..., dict] = masked_redraw_graph


def _source_short(generations: Sequence[Mapping], generation_id: str) -> str:
    for entry in generations:
        if entry.get("id") == generation_id:
            return entry.get("short_id") or generation_id
    return generation_id


def _resolve_source(batch: dict, generation_id: str) -> str:
    """The redraw generation a masked redraw actually redraws.

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


def masked_redraw(generation_id: str, services: MaskedRedrawServices, *,
                  regions: Sequence[Sequence[float]], prompt_patch: str,
                  denoise: float = 0.45, mask_padding: int = 0,
                  mask_feather: int = 32, size: int = 1024,
                  seeds: Sequence[int] = (1, 2, 3, 4),
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
    prefix = f"mrd-{source_short}"

    picked = services.management.fetch_generation_image(source_id)
    # The job graph is what ran; the PNG prompt can be a cached older submission's.
    record = services.management.request(
        "GET", f"/api/v1/generations/{source_id}")
    source_graph = ((record.get("comfy_job") or {}).get("graph")
                    or services.graph_from_png(picked))
    width, height = services.image_size(picked)

    staged = f"{prefix}-{uuid.uuid4().hex[:8]}"
    staged_source = services.comfyui.upload_image(f"{staged}-source.png", picked)

    rects = rects_from_fractions(regions, width, height)
    mask_png = render_mask_png(width, height, [], rects)
    mask_bbox = mask_bbox_fraction(width, height, [], rects)
    staged_mask = services.comfyui.upload_image(f"{staged}-mask.png", mask_png)

    base_positive, base_negative = source_prompts(source_graph)
    positive = masked_redraw_prompt(base_positive, prompt_patch)

    git = services.git_metadata()
    batch_payload = {
        "idempotency_key": key_prefix or str(uuid.uuid4()),
        "raw_instruction": prompt_patch,
        "recipe": batch.get("recipe", "yukari"),
        "parameters": {
            "kind": "masked_redraw",
            "base_generation": source_id,
            "requested_generation": generation_id,
            "regions": [list(region) for region in regions],
            "prompt_patch": prompt_patch,
            "denoise": denoise,
            "mask_padding": mask_padding,
            "mask_feather": mask_feather,
            "size": size,
            "seeds": list(seeds),
            "mask_bbox": list(mask_bbox),
        },
        "git_commit": git["commit"], "git_dirty": git["dirty"],
        "references": [{"source_generation_id": source_id,
                        "purpose": "rebuild", "aspect": "masked_redraw",
                        "instruction": prompt_patch}],
        "refinement": {"source_batch_id": batch["id"], "actor": "human",
                       "reason": prompt_patch},
    }
    created = services.management.request("POST", "/api/v1/batches", batch_payload)
    services.output_root.mkdir(parents=True, exist_ok=True)

    ids: list[str] = []
    urls: list[str] = []
    last_raw_filename, last_raw = None, None
    for index, seed in enumerate(seeds):
        job_prefix = f"{prefix}-s{seed}"
        graph = services.masked_redraw_graph(
            source_graph, image_name=staged_source, mask_name=staged_mask,
            positive=positive, negative=base_negative, seed=seed,
            denoise=denoise, mask_padding=mask_padding, mask_feather=mask_feather,
            size=size, prefix=job_prefix)
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
        f"**masked_redraw** `{generation_id}`\n"
        f"**patch** {prompt_patch}\n"
        f"**chimera** {urls[-1]}",
        last_raw_filename, last_raw)
    services.emit(f"batch {created.get('short_id', created['id'])} done")
    return {"batch_id": created["id"], "generation_ids": ids}
