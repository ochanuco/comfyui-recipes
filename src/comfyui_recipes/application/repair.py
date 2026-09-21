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
from ..domain.yukari import delivery_style
from ..infrastructure.comfyui.pose_graph import pose_from_outputs, pose_graph
from ..infrastructure.comfyui.repair_controlnet import control_hook
from ..infrastructure.comfyui.repair_graph import (
    deliver_only_repair_graph,
    repair_graph,
    source_prompts,
)
from ..infrastructure.comfyui.repair_model import anima_model_hook
from ..infrastructure.imaging.masks import mask_bbox_fraction, render_mask_png
from ..infrastructure.imaging.toe_template import reference_hint
from .ingest import ingest_seed_render


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
    deliver_repair_graph: Callable[..., dict] = deliver_only_repair_graph


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
          deliver_only: bool = False,
          matte_model: str | None = None,
          repin: bool = False, recolor: bool = False, skin: bool = False,
          backdrop: str | None = None, stroke_light: str | None = None,
          transparent: bool = False, deliver_size: int | None = None,
          graph_generation_id: str | None = None,
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
    # `graph_generation_id` lets a caller that already knows better -- a
    # finalize of a repaired raw, which must draw its reroll's prompt from
    # the original generation rather than the repair-emphasized text baked
    # into its own graph -- name a different generation's graph, while the
    # picture cropped stays `source_id`'s own.
    graph_id = graph_generation_id or source_id
    # The job graph is what ran; the PNG prompt can be a cached older submission's.
    record = services.management.request(
        "GET", f"/api/v1/generations/{graph_id}")
    if graph_id == source_id:
        source_graph = (record.get("comfy_job") or {}).get("graph") or services.graph_from_png(picked)
    else:
        source_graph = ((record.get("comfy_job") or {}).get("graph")
                        or services.graph_from_png(
                            services.management.fetch_generation_image(graph_id)))
    width, height = services.image_size(picked)
    # The part LoRA chain (Feet XL / Hands XL) is trained for the
    # Illustrious checkpoint only; a UNETLoader marks an anima source.
    is_anima_source = any(node.get("class_type") == "UNETLoader"
                          for node in source_graph.values())
    resolved_matte_model = matte_model or delivery_style.MATTE_MODEL

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
    loras = () if (model or is_anima_source) else part_loras(parts, lora)
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
            **({"deliver_only": True, "repin": repin, "recolor": recolor,
                "skin": skin, "matte_model": resolved_matte_model,
                **({"backdrop": backdrop} if backdrop else {}),
                **({"stroke_light": stroke_light} if stroke_light is not None else {}),
                **({"transparent": True} if transparent else {}),
                **({"deliver_size": deliver_size} if deliver_size is not None else {})}
               if deliver_only else {}),
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
        if deliver_only:
            graph = services.deliver_repair_graph(
                source_graph, image_name=staged_source, mask_name=staged_mask,
                positive=positive, negative=base_negative, seed=seed,
                denoise=denoise, size=size, prefix=job_prefix,
                matte_model=resolved_matte_model, skin=skin, repin=repin,
                recolor=recolor, transparent=transparent, backdrop=backdrop,
                stroke_light=stroke_light, deliver_size=deliver_size,
                canvas=(width, height), loras=loras, model_hooks=model_hooks,
                conditioning_hooks=conditioning_hooks)
        else:
            graph = services.repair_graph(
                source_graph, image_name=staged_source, mask_name=staged_mask,
                positive=positive, negative=base_negative, seed=seed,
                denoise=denoise, size=size, prefix=job_prefix, loras=loras,
                model_hooks=model_hooks, conditioning_hooks=conditioning_hooks)
        prompt_id = services.comfyui.submit(graph)
        services.emit(f"{job_prefix} {prompt_id}")
        result = ingest_seed_render(
            comfyui=services.comfyui, management=services.management,
            output_root=services.output_root, emit=services.emit,
            batch_id=created["id"], key_prefix=key_prefix, index=index,
            seed=seed, prompt_id=prompt_id, graph=graph, job_prefix=job_prefix,
            mask_png=mask_png)
        ids.extend(result["generation_ids"])
        urls.extend(result["generation_urls"])
        last_raw_filename, last_raw = result["raw_filename"], result["raw"]

    services.management.request(
        "PATCH", f"/api/v1/batches/{created['id']}", {"status": "completed"})
    services.notifier.send(
        f"**repair** `{generation_id}`\n"
        f"**parts** {', '.join(parts) if parts else '(regions only)'}\n"
        f"**chimera** {urls[-1]}",
        last_raw_filename, last_raw)
    services.emit(f"batch {created.get('short_id', created['id'])} done")
    return {"batch_id": created["id"], "generation_ids": ids}
