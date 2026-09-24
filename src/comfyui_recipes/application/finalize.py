"""Finalize one selected generation as a recorded refinement batch."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

from ..domain.generation.models import PromptPair
from ..domain.repair.loras import part_loras
from ..domain.repair.prompt import repair_prompt
from ..domain.repair.regions import rects_from_fractions, regions_from_pose, scale_circles
from ..domain.yukari import delivery_style
from ..domain.yukari.recipe import refinement_prompt
from ..infrastructure.comfyui.base_graph import BaseRoles, base_roles
from ..infrastructure.comfyui.pose_graph import pose_from_outputs, pose_graph
from ..infrastructure.comfyui.refinement_graph import sizes
from ..infrastructure.comfyui.repair_graph import redraw_canvas, splice_repair
from ..infrastructure.imaging.delivery import image_size
from ..infrastructure.imaging.masks import (
    mask_bbox_fraction,
    render_mask_png,
    render_soft_mask_png,
)
from ..infrastructure.persistence.run_state import (
    JsonRunState,
    operation_state_path,
)
from .ingest import (
    asset_key,
    attach_asset,
    classify_outputs,
    generation_key,
    record_job,
    upload_generation,
)
from .repair import RepairServices
from .repair import repair as repair_use_case

# `render_soft_mask_png`'s feather, as a share of the redraw canvas' longest side.
KEEP_FEATHER_FRACTION = 0.03

# Passed for apply_repin/backdrop/stroke_light/deliver_only to mean "use the
# base recipe's own FINALIZE_DEFAULTS value".
RECIPE_DEFAULT = object()


@dataclass(frozen=True)
class FinalizeServices:
    management: object
    comfyui: object
    graph_from_png: Callable[[bytes], dict]
    chain_pass: Callable[..., dict]
    git_metadata: Callable[[], dict]
    notifier: object
    output_root: Path
    emit: Callable[[str], None] = print
    measure: Callable[[bytes], dict] | None = None
    pose_graph: Callable[..., dict] = pose_graph
    splice_repair: Callable[..., dict] = splice_repair
    image_size: Callable[[bytes], tuple[int, int]] = image_size
    # deliver_only + repair/repair_regions routes through the repair use
    # case instead of the redraw's own splice -- same masked reroll, and the
    # same batch/job/generation recording repair() already does.
    repair_use_case: Callable[..., dict] = repair_use_case
    state: JsonRunState = field(default_factory=JsonRunState)


@dataclass(frozen=True)
class _Source:
    context: dict
    picked: bytes
    batch: dict
    is_repaired_raw: bool
    base_generation_id: str
    graph: dict
    roles: BaseRoles
    is_anima: bool


@dataclass(frozen=True)
class _Plan:
    deliver_only: bool
    repin: bool
    recolor: bool
    skin: bool
    stroke_light: str | None
    backdrop: str | None
    transparent: bool
    denoise: float
    size: int
    deliver_size: int | None
    latent_route: bool
    prompt: PromptPair | None
    sampler: object
    loader: str | None
    sampling: tuple | None
    keep_legwear: float | None
    keep_scene: bool
    upscale: str | None
    matte_model: str
    keep_regions: list[list[float]]
    keep_strength: float
    repair_parts: list[str]
    repair_regions: list[list[float]]
    repair_denoise: float
    repair_pad: float
    repair_size: int | None
    repair_lora: float | None
    repair_seeds: int | None

    @property
    def repair_requested(self) -> bool:
        return bool(self.repair_parts) or bool(self.repair_regions)


@dataclass(frozen=True)
class _Staged:
    staged_prefix: str | None
    source_image: str | None
    staged_source: str | None
    keep_mask_image: str | None


@dataclass(frozen=True)
class _Outputs:
    image_filename: str
    raw: bytes
    matte_name: str
    matte: bytes
    delivered_name: str
    delivered: bytes


def _load_source(generation_id: str, services: FinalizeServices,
                 context: dict | None) -> _Source:
    if context is None:
        context = services.management.request(
            "GET", f"/api/v1/generations/{generation_id}/context")
    picked = services.management.fetch_generation_image(generation_id)
    source_batch = services.management.request(
        "GET", f"/api/v1/batches/{context['batch']['id']}")
    source_kind = (source_batch.get("parameters") or {}).get("kind")
    is_repaired_raw = source_kind in ("repair", "masked_redraw")
    base_generation_id = (source_batch["parameters"]["base_generation"]
                          if is_repaired_raw else generation_id)
    base_record = services.management.request(
        "GET", f"/api/v1/generations/{base_generation_id}")
    base = (base_record.get("comfy_job") or {}).get("graph")
    if base is None:
        base = services.graph_from_png(
            services.management.fetch_generation_image(base_generation_id)
            if is_repaired_raw else picked)
    roles = base_roles(base)
    if any(node.get("class_type") == "LayeredDiffusionApply"
           for node in base.values()):
        raise SystemExit("LayerDiffuse 由来の絵は finalize できません")
    # A UNETLoader in the base graph marks an anima render -- the only
    # source finalize redraws; every other source can still be delivered
    # with deliver_only.
    is_anima = any(node.get("class_type") == "UNETLoader"
                   for node in base.values())
    return _Source(context=context, picked=picked, batch=source_batch,
                   is_repaired_raw=is_repaired_raw,
                   base_generation_id=base_generation_id, graph=base,
                   roles=roles, is_anima=is_anima)


def _resolve_plan(source: _Source, generation_id: str, *,
                  denoise: float | None, apply_repin: bool | object,
                  apply_skin: bool, apply_recolor: bool,
                  keep_legwear: float | None, keep_scene: bool,
                  transparent: bool | None, size: int | None,
                  latent_route: bool | None, finalizer: str | None,
                  backdrop: str | None | object, upscale: str | None,
                  deliver_size: int | None, stroke_light: str | None | object,
                  repair: Sequence[str] | None,
                  repair_regions: Sequence[Sequence[float]],
                  repair_denoise: float, repair_pad: float,
                  repair_size: int | None, repair_lora: float | None,
                  repair_seeds: int | None,
                  keep_regions: Sequence[Sequence[float]], keep_strength: float,
                  deliver_only: bool | object,
                  matte_model: str | None) -> tuple[_Plan, int, str]:
    redraw_shaping_conflicts = [name for name, present in (
        ("denoise", denoise is not None),
        ("size", size is not None),
        ("latent_route", latent_route is not None),
        ("finalizer", finalizer is not None),
        ("keep_regions", bool(keep_regions)),
        ("upscale", upscale is not None),
    ) if present]
    recipe_defaults = delivery_style.FINALIZE_DEFAULTS
    if deliver_only is RECIPE_DEFAULT:
        deliver_only = (recipe_defaults.get("deliver_only", False)
                        if not redraw_shaping_conflicts else False)
    if apply_repin is RECIPE_DEFAULT:
        apply_repin = recipe_defaults.get("repin", False)
    if stroke_light is RECIPE_DEFAULT:
        stroke_light = recipe_defaults.get("stroke_light")
    if backdrop is RECIPE_DEFAULT:
        backdrop = None if transparent is True else recipe_defaults.get("backdrop")

    if deliver_only and redraw_shaping_conflicts:
        raise SystemExit(
            "deliver_only cannot combine with " + ", ".join(redraw_shaping_conflicts))
    if not source.is_anima and not deliver_only:
        raise SystemExit(
            "描き直しができるのは Anima で描いた絵だけです。この絵は "
            "deliver_only（描き直し無しの納品）なら finalize できます")

    if denoise is None:
        denoise = delivery_style.FINALIZE_DENOISE
    if size is None:
        size = delivery_style.FINALIZE_SIZE
    if latent_route is None:
        latent_route = False
    if deliver_only:
        latent_route = False
    if transparent is None:
        transparent = False
    if keep_scene:
        transparent = False
    if source.roles.stitched:
        # A stitched base's sampler latent is the inpaint crop, not the whole
        # picture -- the pixel route is the only correct one, so a caller's
        # explicit opt-in does not survive here.
        latent_route = False
    seed = source.graph[source.roles.sampler_id]["inputs"]["seed"]
    prefix = f"fin-{generation_id}"
    base_prompt = PromptPair(
        source.graph[source.roles.positive_id]["inputs"]["text"],
        source.graph[source.roles.negative_id]["inputs"]["text"],
    )
    if source.is_anima:
        prompt = refinement_prompt(base_prompt)
        sampler = delivery_style.FINALIZE_SAMPLER
        loader = finalizer or delivery_style.FINALIZE_MODEL
        sampling = (delivery_style.FINALIZE_STEPS,
                    delivery_style.FINALIZE_CFG)
    else:
        # Unused: deliver_only (the only way a non-anima source reaches this
        # point) skips the redraw before any of these are read.
        prompt = None
        sampler = None
        loader = finalizer
        sampling = None
    # Recolor wins over repin, same rule the redraw graph applies.
    recolor_applied = apply_recolor
    repin_applied = apply_repin and not apply_recolor
    skin_applied = apply_skin
    repair_parts = list(repair) if repair else []
    repair_region_list = [list(region) for region in repair_regions]
    if repair_seeds is not None and not deliver_only:
        raise SystemExit("repair_seeds needs deliver_only")

    plan = _Plan(
        deliver_only=deliver_only, repin=repin_applied, recolor=recolor_applied,
        skin=skin_applied, stroke_light=stroke_light, backdrop=backdrop,
        transparent=transparent, denoise=denoise, size=size,
        deliver_size=deliver_size, latent_route=latent_route, prompt=prompt,
        sampler=sampler, loader=loader, sampling=sampling,
        keep_legwear=keep_legwear, keep_scene=keep_scene, upscale=upscale,
        matte_model=matte_model or delivery_style.MATTE_MODEL,
        keep_regions=[list(region) for region in keep_regions],
        keep_strength=keep_strength, repair_parts=repair_parts,
        repair_regions=repair_region_list, repair_denoise=repair_denoise,
        repair_pad=repair_pad, repair_size=repair_size, repair_lora=repair_lora,
        repair_seeds=repair_seeds)
    return plan, seed, prefix


def _deliver_with_repair(generation_id: str, services: FinalizeServices,
                         source: _Source, plan: _Plan,
                         key_prefix: str | None) -> dict:
    # deliver_only skips the redraw entirely, so there is no whole-canvas
    # sampler for `splice_repair` to splice into -- route through the
    # repair use case instead, once per seed, with a delivery spec so it
    # hangs the same deliver-only tail off each seed's own stitched crop.
    seeds_count = plan.repair_seeds if plan.repair_seeds is not None else 4
    if not (1 <= seeds_count <= 8):
        raise SystemExit("repair_seeds must be between 1 and 8")
    repair_size = plan.repair_size
    if repair_size is None:
        long_side = max(services.image_size(source.picked))
        repair_size = 1536 if long_side >= 2048 else 1024
    repair_services = RepairServices(
        management=services.management, comfyui=services.comfyui,
        graph_from_png=services.graph_from_png, image_size=services.image_size,
        git_metadata=services.git_metadata, notifier=services.notifier,
        output_root=services.output_root, emit=services.emit,
        pose_graph=services.pose_graph)
    return services.repair_use_case(
        generation_id, repair_services, parts=plan.repair_parts,
        regions=plan.repair_regions, denoise=plan.repair_denoise,
        seeds=list(range(1, seeds_count + 1)), size=repair_size,
        pad=plan.repair_pad, lora=plan.repair_lora, deliver_only=True,
        matte_model=plan.matte_model,
        repin=plan.repin, recolor=plan.recolor, skin=plan.skin,
        backdrop=plan.backdrop, stroke_light=plan.stroke_light,
        transparent=plan.transparent, deliver_size=plan.deliver_size,
        graph_generation_id=source.base_generation_id if source.is_repaired_raw else None,
        key_prefix=key_prefix, context=source.context, batch=source.batch)


def _stage_inputs(services: FinalizeServices, source: _Source, plan: _Plan,
                  prefix: str) -> _Staged:
    # One staged name per run, shared by skin and repair: a second upload of
    # the same picked bytes buys nothing, and ComfyUI would report a cached
    # node's pose text for nothing if the pose pass reused a stale name.
    staged_prefix = (f"{prefix}-{uuid.uuid4().hex[:8]}"
                     if plan.repair_requested or source.is_repaired_raw else None)
    source_image = None
    staged_source = None
    if plan.repair_requested:
        staged_source = services.comfyui.upload_image(
            f"{staged_prefix}-source.png", source.picked)
    if source.is_repaired_raw or plan.skin or plan.deliver_only:
        source_image = staged_source or services.comfyui.upload_image(
            f"{staged_prefix or prefix}-source.png", source.picked)
    keep_mask_image = None
    if plan.keep_regions:
        redraw_width, redraw_height = sizes(*services.image_size(source.picked), plan.size)
        keep_rects = rects_from_fractions(plan.keep_regions, redraw_width, redraw_height)
        feather = round(KEEP_FEATHER_FRACTION * max(redraw_width, redraw_height))
        keep_mask_png = render_soft_mask_png(
            redraw_width, redraw_height, keep_rects, plan.keep_strength, feather)
        keep_mask_image = services.comfyui.upload_image(
            f"{prefix}-keep-mask.png", keep_mask_png)
    return _Staged(staged_prefix=staged_prefix, source_image=source_image,
                   staged_source=staged_source, keep_mask_image=keep_mask_image)


def _build_graph(services: FinalizeServices, source: _Source, plan: _Plan,
                 staged: _Staged, prefix: str) -> dict:
    return services.chain_pass(
        source.graph, plan.size, plan.denoise, prefix,
        prompt=(plan.prompt.positive, plan.prompt.negative)
               if plan.prompt is not None else None,
        matte_model=plan.matte_model,
        latent_route=plan.latent_route,
        sampler=plan.sampler,
        loader=plan.loader,
        sampling=plan.sampling,
        deliver=True,
        skin=plan.skin,
        repin=plan.repin,
        recolor=plan.recolor,
        keep_legwear=plan.keep_legwear,
        keep_scene=plan.keep_scene,
        source_image=staged.source_image,
        keep_mask_image=staged.keep_mask_image,
        transparent=plan.transparent,
        backdrop=plan.backdrop,
        upscale=plan.upscale or "bicubic",
        deliver_size=plan.deliver_size,
        stroke_light=plan.stroke_light,
        deliver_only=plan.deliver_only,
        redraw_from_source=source.is_repaired_raw and not plan.latent_route,
        canvas=services.image_size(source.picked))


def _splice_repair(services: FinalizeServices, source: _Source, plan: _Plan,
                   staged: _Staged, graph: dict, prefix: str,
                   generation_id: str) -> tuple[dict, bytes | None, tuple | None]:
    if not plan.repair_requested:
        return graph, None, None
    raw_width, raw_height = services.image_size(source.picked)
    redraw_width, redraw_height = redraw_canvas(graph)
    circles = []
    if plan.repair_parts:
        pose_prompt_id = services.comfyui.submit(
            services.pose_graph(staged.staged_source, prefix=prefix))
        pose_outputs = services.comfyui.wait_for_outputs(pose_prompt_id)
        pose = pose_from_outputs(pose_outputs)
        raw_circles = regions_from_pose(pose, plan.repair_parts, plan.repair_pad)
        circles = scale_circles(
            raw_circles, redraw_width / raw_width, redraw_height / raw_height)
    rects = rects_from_fractions(plan.repair_regions, redraw_width, redraw_height)
    if not circles and not rects:
        wanted = ", ".join(plan.repair_parts) if plan.repair_parts else "(none requested)"
        raise SystemExit(
            f"no repair region found: pose detection located none of "
            f"[{wanted}] on {generation_id}, and no repair_regions "
            "rectangles were given")
    repair_mask_png = render_mask_png(redraw_width, redraw_height, circles, rects)
    repair_mask_bbox = mask_bbox_fraction(redraw_width, redraw_height, circles, rects)
    mask_name = services.comfyui.upload_image(
        f"{staged.staged_prefix}-mask.png", repair_mask_png)
    repaired_positive = repair_prompt(plan.prompt.positive, plan.repair_parts)
    graph = services.splice_repair(
        graph, mask_name=mask_name, positive=repaired_positive,
        negative=plan.prompt.negative, denoise=plan.repair_denoise,
        size=plan.repair_size, loras=part_loras(plan.repair_parts, plan.repair_lora))
    return graph, repair_mask_png, repair_mask_bbox


def _collect_outputs(services: FinalizeServices, prefix: str,
                     prompt_id: str) -> _Outputs:
    outputs = services.comfyui.wait_for(prompt_id)
    pictures, delivereds, mattes = classify_outputs(outputs)
    missing = [name for name, outs in
               (("raw", pictures), ("matte", mattes), ("delivered", delivereds))
               if not outs]
    if missing:
        raise SystemExit(
            f"{prefix} is missing its {', '.join(missing)} output(s); one of "
            "each is required")
    image = pictures[-1]
    raw = services.comfyui.fetch(image)
    matte_name = mattes[-1]["filename"]
    matte = services.comfyui.fetch(mattes[-1])
    delivered_name = delivereds[-1]["filename"]
    delivered = services.comfyui.fetch(delivereds[-1])
    services.output_root.mkdir(parents=True, exist_ok=True)
    (services.output_root / image["filename"]).write_bytes(raw)
    (services.output_root / matte_name).write_bytes(matte)
    (services.output_root / delivered_name).write_bytes(delivered)
    if services.measure is not None:
        summary = services.measure(delivered)
        status = "FAIL" if summary["fails"] else "pass"
        services.emit(
            f"palette {status}: fig mid {summary['fig_sat_mean']:.1f} "
            f"p90 {summary['fig_sat_p90']:.0f} light {summary['light_sat']:.1f}")
    return _Outputs(image_filename=image["filename"], raw=raw, matte_name=matte_name,
                    matte=matte, delivered_name=delivered_name, delivered=delivered)


def _batch_parameters(generation_id: str, plan: _Plan,
                      repair_mask_bbox: tuple | None) -> dict:
    return {"kind": "hires-chain",
           "base_generation": generation_id,
           **({"deliver_only": True} if plan.deliver_only else {}),
           **({} if plan.deliver_only else {"size": plan.size, "denoise": plan.denoise}),
           **({"route": "latent"} if plan.latent_route else {}),
           **({"finalizer": plan.loader} if plan.loader and not plan.deliver_only else {}),
           "repin": plan.repin,
           "skin": plan.skin,
           **({"recolor": True} if plan.recolor else {}),
           **({"keep_legwear": plan.keep_legwear}
              if plan.keep_legwear is not None else {}),
           **({"keep_scene": True} if plan.keep_scene else {}),
           **({"transparent": True} if plan.transparent else {}),
           **({"backdrop": plan.backdrop} if plan.backdrop else {}),
           **({"upscale": plan.upscale} if plan.upscale else {}),
           **({"deliver_size": plan.deliver_size}
              if plan.deliver_size is not None else {}),
           **({"stroke_light": plan.stroke_light}
              if plan.stroke_light is not None else {}),
           **({"repair": {
                  "parts": plan.repair_parts, "regions": plan.repair_regions,
                  "denoise": plan.repair_denoise, "pad": plan.repair_pad,
                  "size": plan.repair_size, "lora": plan.repair_lora,
                  "mask_bbox": list(repair_mask_bbox)}}
              if plan.repair_requested else {}),
           **({"keep_regions": plan.keep_regions,
               "keep_strength": plan.keep_strength}
              if plan.keep_regions else {})}


def _record(services: FinalizeServices, generation_id: str, source: _Source,
           plan: _Plan, staged: _Staged, graph: dict, prompt_id: str,
           outputs: _Outputs, batch_parameters: dict, seed: int,
           repair_mask_png: bytes | None, key_prefix: str | None) -> dict:
    git = services.git_metadata()
    batch = services.management.request("POST", "/api/v1/batches", {
        "idempotency_key": key_prefix or str(uuid.uuid4()),
        "raw_instruction": f"{generation_id} を高解像度化",
        "recipe": "yukari",
        "parameters": batch_parameters,
        "git_commit": git["commit"], "git_dirty": git["dirty"],
        "references": [{"source_generation_id": generation_id,
                        "purpose": "rebuild", "aspect": "composition",
                        "instruction": "この生成の 2048 プリント"}],
        "refinement": {"source_batch_id": source.context["batch"]["id"],
                       "actor": "human", "reason": "採用作の高解像度化"},
    })
    job = record_job(services.management, batch["id"], key_prefix=key_prefix,
                     index=0, seed=seed, prompt_id=prompt_id, graph=graph)
    uploads = ([(outputs.delivered_name, outputs.delivered)] if plan.deliver_only
              else [(outputs.image_filename, outputs.raw),
                    (outputs.delivered_name, outputs.delivered)])
    ids, urls = [], []
    for index, (name, data) in enumerate(uploads):
        rendered = upload_generation(services.management, services.emit,
                                     job["id"], seed=seed, name=name, data=data,
                                     index=index,
                                     idempotency_key=generation_key(
                                         key_prefix, 0, index))
        ids.append(rendered["id"])
        urls.append(rendered["canonical_url"])
    # The matte hangs off the first ingested generation: the raw redraw
    # when there is one, otherwise the delivered picture.
    attach_asset(services.management, ids[0], role="mask", name=outputs.matte_name,
                data=outputs.matte,
                idempotency_key=asset_key(key_prefix, 0, "mask"))
    services.emit(f"{outputs.matte_name} -> mask on {ids[0]}")
    if plan.repair_requested:
        mask_filename = f"{staged.staged_prefix}-mask.png"
        attach_asset(services.management, ids[0], role="repair-mask",
                    name=mask_filename, data=repair_mask_png,
                    idempotency_key=asset_key(key_prefix, 0, "repair-mask"))
        services.emit(f"{mask_filename} -> repair-mask on {ids[0]}")
    services.management.request(
        "PATCH", f"/api/v1/jobs/{job['id']}", {"status": "ingested"})
    services.management.request(
        "PATCH", f"/api/v1/batches/{batch['id']}", {"status": "completed"})
    services.notifier.send(
        f"**finalize** `{generation_id}`\n"
        f"**file** `{outputs.delivered_name}`\n"
        f"**chimera** {urls[-1]}", outputs.delivered_name, outputs.delivered)
    services.emit(f"batch {batch.get('short_id', batch['id'])} done")
    return {"batch_id": batch["id"], "generation_ids": ids}


def finalize(generation_id: str, services: FinalizeServices, *,
             denoise: float | None = None,
             apply_repin: bool | object = False, apply_skin: bool = False,
             apply_recolor: bool = False,
             keep_legwear: float | None = None,
             keep_scene: bool = False,
             transparent: bool | None = None,
             size: int | None = None, latent_route: bool | None = None,
             finalizer: str | None = None,
             key_prefix: str | None = None,
             backdrop: str | None | object = None,
             upscale: str | None = None,
             deliver_size: int | None = None,
             stroke_light: str | None | object = None,
             repair: Sequence[str] | None = None,
             repair_regions: Sequence[Sequence[float]] = (),
             repair_denoise: float = 0.6,
             repair_pad: float = 1.0,
             repair_size: int | None = None,
             repair_lora: float | None = None,
             repair_seeds: int | None = None,
             keep_regions: Sequence[Sequence[float]] = (),
             keep_strength: float = 0.25,
             deliver_only: bool | object = False,
             matte_model: str | None = None,
             context: dict | None = None) -> dict:
    state_path = operation_state_path(services.output_root, "finalize", key_prefix)
    if state_path:
        state_path.parent.mkdir(parents=True, exist_ok=True)
    state = services.state.load(state_path) if state_path else {}
    if state.get("status") == "completed" and state.get("result"):
        return state["result"]
    source = _load_source(generation_id, services, context)
    plan, seed, prefix = _resolve_plan(
        source, generation_id,
        denoise=denoise, apply_repin=apply_repin, apply_skin=apply_skin,
        apply_recolor=apply_recolor, keep_legwear=keep_legwear,
        keep_scene=keep_scene, transparent=transparent, size=size,
        latent_route=latent_route, finalizer=finalizer, backdrop=backdrop,
        upscale=upscale, deliver_size=deliver_size, stroke_light=stroke_light,
        repair=repair, repair_regions=repair_regions,
        repair_denoise=repair_denoise, repair_pad=repair_pad,
        repair_size=repair_size, repair_lora=repair_lora,
        repair_seeds=repair_seeds, keep_regions=keep_regions,
        keep_strength=keep_strength, deliver_only=deliver_only,
        matte_model=matte_model)

    if plan.deliver_only and plan.repair_requested:
        return _deliver_with_repair(
            generation_id, services, source, plan, key_prefix)

    if plan.repair_size is None:
        plan = replace(plan, repair_size=1024)
    staged = _stage_inputs(services, source, plan, prefix)
    graph = _build_graph(services, source, plan, staged, prefix)
    graph, repair_mask_png, repair_mask_bbox = _splice_repair(
        services, source, plan, staged, graph, prefix, generation_id)

    prompt_id = state.get("prompt_id")
    knows = getattr(services.comfyui, "knows", None)
    if prompt_id and (knows is None or knows(prompt_id)):
        services.emit(f"{prefix} resume {prompt_id}")
    else:
        prompt_id = services.comfyui.submit(graph)
        if state_path:
            state["prompt_id"] = prompt_id
            services.state.save(state_path, state)
    services.emit(f"{prefix} {prompt_id}")
    outputs = _collect_outputs(services, prefix, prompt_id)

    batch_parameters = _batch_parameters(generation_id, plan, repair_mask_bbox)
    result = _record(services, generation_id, source, plan, staged, graph,
                     prompt_id, outputs, batch_parameters, seed,
                     repair_mask_png, key_prefix)
    if state_path:
        state.update({"status": "completed", "result": result})
        services.state.save(state_path, state)
    return result
