"""Finalize one selected generation as a recorded refinement batch."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..domain.generation.models import PromptPair
from ..domain.repair.prompt import repair_prompt
from ..domain.repair.regions import rects_from_fractions, regions_from_pose, scale_circles
from ..domain.yukari import delivery_style
from ..domain.yukari.recipe import refinement_prompt
from ..domain.yukari_anima import delivery_style as anima_delivery_style
from ..domain.yukari_anima.recipe import refinement_prompt as anima_refinement_prompt
from ..domain.yukari_sketch import delivery_style as sketch_delivery_style
from ..domain.yukari_sketch.prompt_style import LORA as SKETCH_LORA
from ..domain.yukari_sketch.recipe import refinement_prompt as sketch_refinement_prompt
from ..infrastructure.comfyui.base_graph import base_roles
from ..infrastructure.comfyui.pose_graph import pose_from_outputs, pose_graph
from ..infrastructure.comfyui.refinement_graph import DELIVERED_SUFFIX, MATTE_SUFFIX
from ..infrastructure.comfyui.repair_graph import redraw_canvas, splice_repair
from ..infrastructure.imaging.delivery import image_size
from ..infrastructure.imaging.masks import mask_bbox_fraction, render_mask_png

# The delivery redraw's longest side.
FINALIZE_SIZE = 2560


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


def finalize(generation_id: str, services: FinalizeServices, *,
             denoise: float | None = None, handdrawn: bool = False,
             apply_repin: bool = False, apply_skin: bool = False,
             apply_recolor: bool = False,
             keep_legwear: float | None = None,
             keep_scene: bool = False,
             transparent: bool | None = None,
             toe_guard: float | None = None,
             size: int | None = None, latent_route: bool | None = None,
             finalizer: str | None = None,
             key_prefix: str | None = None,
             backdrop: str | None = None,
             upscale: str | None = None,
             lora_strength: float | None = None,
             deliver_size: int | None = None,
             stroke_light: str | None = None,
             repair: Sequence[str] | None = None,
             repair_regions: Sequence[Sequence[float]] = (),
             repair_denoise: float = 0.6,
             repair_pad: float = 1.0,
             repair_size: int = 1024) -> dict:
    context = services.management.request(
        "GET", f"/api/v1/generations/{generation_id}/context")
    picked = services.management.fetch_generation_image(generation_id)
    base = services.graph_from_png(picked)
    roles = base_roles(base)
    # A LoraLoader in the base graph marks a sketch render; a UNETLoader
    # (checked only once sketch is ruled out) marks an anima render -- a
    # base graph carries at most one of the two.
    is_sketch = any(node.get("class_type") == "LoraLoader"
                    for node in base.values())
    is_anima = (not is_sketch) and any(
        node.get("class_type") == "UNETLoader" for node in base.values())
    # A base with its own layerdiffuse alpha finalizes as compose-then-redraw:
    # the RGBA composites onto the sticker backdrop before the redraw ever
    # sees it, so there is no birefnet matte and no separate delivery node.
    is_layerdiffuse = any(node.get("class_type") == "LayeredDiffusionApply"
                          for node in base.values())
    if lora_strength is not None and not is_sketch:
        raise SystemExit("lora_strength needs a recipe with a LoRA")
    if apply_recolor and is_sketch:
        raise SystemExit("recolor asserts the lap-look palette and strips a "
                         "yukari-sketch render's own; use repin or nothing")
    redraw_lora = None
    if is_sketch and (is_layerdiffuse or lora_strength is not None):
        strength = SKETCH_LORA[1] if lora_strength is None else lora_strength
        redraw_lora = (SKETCH_LORA[0], strength, strength)
    if denoise is None:
        denoise = (sketch_delivery_style.FINALIZE_DENOISE if is_sketch
                   else anima_delivery_style.FINALIZE_DENOISE if is_anima
                   else delivery_style.FINALIZE_DENOISE)
    if size is None:
        size = (sketch_delivery_style.FINALIZE_SIZE if is_sketch
                else anima_delivery_style.FINALIZE_SIZE if is_anima
                else FINALIZE_SIZE)
    if deliver_size is None:
        deliver_size = sketch_delivery_style.DELIVER_SIZE if is_sketch else None
    caller_latent_route = latent_route
    if latent_route is None:
        latent_route = is_sketch and sketch_delivery_style.FINALIZE_LATENT_ROUTE
    if transparent is None:
        transparent = False if backdrop else (
            is_sketch and sketch_delivery_style.FINALIZE_TRANSPARENT)
    if keep_scene:
        transparent = False
    if is_layerdiffuse:
        # The RGBA composites straight onto the sticker backdrop, so there is
        # no cutout left for the delivery node to make; only an explicit
        # opt-in encodes the composite and upscales it in latent space.
        latent_route = (caller_latent_route if caller_latent_route is not None
                        else False)
        transparent = False
    if roles.stitched:
        # A stitched base's sampler latent is the inpaint crop, not the whole
        # picture -- the pixel route is the only correct one, so a caller's
        # explicit opt-in does not survive here.
        latent_route = False
    seed = base[roles.sampler_id]["inputs"]["seed"]
    prefix = f"fin-{generation_id}"
    base_prompt = PromptPair(
        base[roles.positive_id]["inputs"]["text"],
        base[roles.negative_id]["inputs"]["text"],
    )
    if is_sketch:
        prompt = sketch_refinement_prompt(base_prompt)
        sampler = sketch_delivery_style.FINALIZE_SAMPLER
        loader = None
        sampling = None
    elif is_anima:
        prompt = anima_refinement_prompt(base_prompt)
        sampler = anima_delivery_style.FINALIZE_SAMPLER
        loader = finalizer or anima_delivery_style.FINALIZE_MODEL
        sampling = (anima_delivery_style.FINALIZE_STEPS,
                    anima_delivery_style.FINALIZE_CFG)
    else:
        prompt = refinement_prompt(
            base_prompt, handdrawn=handdrawn, toe_guard=toe_guard)
        sampler = delivery_style.FINALIZE_SAMPLER
        loader = finalizer
        sampling = None
    # Recolor wins over repin, same rule the redraw graph applies. None of
    # the three apply to a layerdiffuse base -- there is no matte for them
    # to run against.
    recolor_applied = apply_recolor and not is_layerdiffuse
    repin_applied = apply_repin and not apply_recolor and not is_layerdiffuse
    skin_applied = apply_skin and not is_layerdiffuse
    repair_parts = list(repair) if repair else []
    repair_region_list = [list(region) for region in repair_regions]
    repair_requested = bool(repair_parts) or bool(repair_region_list)
    # One staged name per run, shared by skin and repair: a second upload of
    # the same picked bytes buys nothing, and ComfyUI would report a cached
    # node's pose text for nothing if the pose pass reused a stale name.
    staged_prefix = f"{prefix}-{uuid.uuid4().hex[:8]}" if repair_requested else None
    source_image = None
    staged_source = None
    if repair_requested:
        staged_source = services.comfyui.upload_image(
            f"{staged_prefix}-source.png", picked)
    if skin_applied:
        source_image = staged_source or services.comfyui.upload_image(
            f"{prefix}-source.png", picked)
    if is_layerdiffuse:
        graph = services.chain_pass(
            base, size, denoise, prefix,
            prompt=(prompt.positive, prompt.negative),
            matte_model=None,
            latent_route=latent_route,
            sampler=sampler,
            loader=loader,
            sampling=sampling,
            deliver=False,
            compose=True,
            backdrop=backdrop,
            upscale=upscale or "bicubic",
            redraw_lora=redraw_lora,
            deliver_size=deliver_size,
            stroke_light=stroke_light,
            canvas=services.image_size(picked))
    else:
        graph = services.chain_pass(
            base, size, denoise, prefix,
            prompt=(prompt.positive, prompt.negative),
            matte_model=delivery_style.MATTE_MODEL,
            latent_route=latent_route,
            sampler=sampler,
            loader=loader,
            sampling=sampling,
            deliver=True,
            skin=skin_applied,
            repin=repin_applied,
            recolor=recolor_applied,
            keep_legwear=keep_legwear,
            keep_scene=keep_scene,
            source_image=source_image,
            transparent=transparent,
            backdrop=backdrop,
            upscale=upscale or "bicubic",
            redraw_lora=redraw_lora,
            deliver_size=deliver_size,
            stroke_light=stroke_light,
            canvas=services.image_size(picked))

    repair_mask_png = None
    repair_mask_bbox = None
    if repair_requested:
        raw_width, raw_height = services.image_size(picked)
        redraw_width, redraw_height = redraw_canvas(graph)
        circles = []
        if repair_parts:
            pose_prompt_id = services.comfyui.submit(
                services.pose_graph(staged_source, prefix=prefix))
            pose_outputs = services.comfyui.wait_for_outputs(pose_prompt_id)
            pose = pose_from_outputs(pose_outputs)
            raw_circles = regions_from_pose(pose, repair_parts, repair_pad)
            circles = scale_circles(
                raw_circles, redraw_width / raw_width, redraw_height / raw_height)
        rects = rects_from_fractions(repair_region_list, redraw_width, redraw_height)
        if not circles and not rects:
            wanted = ", ".join(repair_parts) if repair_parts else "(none requested)"
            raise SystemExit(
                f"no repair region found: pose detection located none of "
                f"[{wanted}] on {generation_id}, and no repair_regions "
                "rectangles were given")
        repair_mask_png = render_mask_png(redraw_width, redraw_height, circles, rects)
        repair_mask_bbox = mask_bbox_fraction(redraw_width, redraw_height, circles, rects)
        mask_name = services.comfyui.upload_image(
            f"{staged_prefix}-mask.png", repair_mask_png)
        repaired_positive = repair_prompt(prompt.positive, repair_parts)
        graph = services.splice_repair(
            graph, mask_name=mask_name, positive=repaired_positive,
            negative=prompt.negative, denoise=repair_denoise, size=repair_size)

    prompt_id = services.comfyui.submit(graph)
    services.emit(f"{prefix} {prompt_id}")
    outputs = services.comfyui.wait_for(prompt_id)
    if is_layerdiffuse:
        # Compose-then-redraw is one SaveImage, already the finished picture:
        # no birefnet pass ran, so there is no separate matte or delivered
        # output to classify.
        if not outputs:
            raise SystemExit(f"{prefix} produced no output; one is required")
        image = outputs[-1]
        raw = services.comfyui.fetch(image)
        matte_name = matte = None
        delivered_name, delivered = image["filename"], raw
    else:
        mattes = [out for out in outputs if MATTE_SUFFIX in out["filename"]]
        delivereds = [out for out in outputs if DELIVERED_SUFFIX in out["filename"]]
        pictures = [out for out in outputs
                    if MATTE_SUFFIX not in out["filename"]
                    and DELIVERED_SUFFIX not in out["filename"]]
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
    if not is_layerdiffuse:
        (services.output_root / matte_name).write_bytes(matte)
        (services.output_root / delivered_name).write_bytes(delivered)
    if services.measure is not None:
        summary = services.measure(delivered)
        status = "FAIL" if summary["fails"] else "pass"
        services.emit(
            f"palette {status}: fig mid {summary['fig_sat_mean']:.1f} "
            f"p90 {summary['fig_sat_p90']:.0f} light {summary['light_sat']:.1f}")

    git = services.git_metadata()
    batch = services.management.request("POST", "/api/v1/batches", {
        "idempotency_key": key_prefix or str(uuid.uuid4()),
        "raw_instruction": (f"{generation_id} を高解像度化"
                            + ("・手書き風の仕上げ" if handdrawn else "")),
        "recipe": "yukari",
        "parameters": {"kind": "hires-chain",
                       "base_generation": generation_id,
                       "size": size, "denoise": denoise,
                       **({"route": "latent"} if latent_route else {}),
                       **({"finalizer": loader} if loader else {}),
                       "repin": repin_applied,
                       "skin": skin_applied,
                       **({"recolor": True} if recolor_applied else {}),
                       **({"keep_legwear": keep_legwear}
                          if keep_legwear is not None else {}),
                       **({"keep_scene": True} if keep_scene else {}),
                       **({"transparent": True} if transparent else {}),
                       **({"compose": True} if is_layerdiffuse else {}),
                       **({"backdrop": backdrop} if backdrop else {}),
                       **({"upscale": upscale} if upscale else {}),
                       **({"lora_strength": lora_strength}
                          if lora_strength is not None else {}),
                       **({"deliver_size": deliver_size}
                          if deliver_size is not None else {}),
                       **({"stroke_light": stroke_light}
                          if stroke_light is not None else {}),
                       **({"repair": {
                              "parts": repair_parts, "regions": repair_region_list,
                              "denoise": repair_denoise, "pad": repair_pad,
                              "size": repair_size,
                              "mask_bbox": list(repair_mask_bbox)}}
                          if repair_requested else {}),
                       **({"finish": "handdrawn"} if handdrawn else {})},
        "git_commit": git["commit"], "git_dirty": git["dirty"],
        "references": [{"source_generation_id": generation_id,
                        "purpose": "rebuild", "aspect": "composition",
                        "instruction": "この生成の 2048 プリント"}],
        "refinement": {"source_batch_id": context["batch"]["id"],
                       "actor": "human", "reason": "採用作の高解像度化"},
    })
    job = services.management.request(
        "POST", f"/api/v1/batches/{batch['id']}/jobs",
        {"idempotency_key": (f"{key_prefix}:job:0" if key_prefix else str(uuid.uuid4())),
         "seed": seed, "index": 0})
    services.management.request(
        "PATCH", f"/api/v1/jobs/{job['id']}",
        {"status": "queued", "comfy_prompt_id": prompt_id, "graph": graph})
    services.management.request(
        "PATCH", f"/api/v1/jobs/{job['id']}", {"status": "completed"})
    uploads = ([(image["filename"], raw)] if is_layerdiffuse
              else [(image["filename"], raw), (delivered_name, delivered)])
    ids, urls = [], []
    for index, (name, data) in enumerate(uploads):
        rendered = services.management.request(
            "POST", f"/api/v1/jobs/{job['id']}/generations",
            multipart=({"seed": seed, "original_filename": name,
                        "comfy_output_index": index},
                       "image", name, data, "image/png"))
        ids.append(rendered["id"])
        urls.append(rendered["canonical_url"])
        services.emit(f"{name} -> {rendered['canonical_url']}")
    if not is_layerdiffuse:
        # The matte is the silhouette of the raw redraw, not of the delivered
        # composite, so it hangs off generation 0. Storing it is what lets the
        # cutout be redone later without re-running the 2048 pass.
        services.management.request(
            "POST", f"/api/v1/generations/{ids[0]}/assets",
            multipart=({"role": "mask"}, "file", matte_name, matte, "image/png"))
        services.emit(f"{matte_name} -> mask on {ids[0]}")
    if repair_requested:
        mask_filename = f"{staged_prefix}-mask.png"
        services.management.request(
            "POST", f"/api/v1/generations/{ids[0]}/assets",
            multipart=({"role": "repair-mask"}, "file", mask_filename,
                       repair_mask_png, "image/png"))
        services.emit(f"{mask_filename} -> repair-mask on {ids[0]}")
    services.management.request(
        "PATCH", f"/api/v1/jobs/{job['id']}", {"status": "ingested"})
    services.management.request(
        "PATCH", f"/api/v1/batches/{batch['id']}", {"status": "completed"})
    services.notifier.send(
        f"**finalize** `{generation_id}`\n"
        f"**file** `{delivered_name}`\n"
        f"**chimera** {urls[-1]}", delivered_name, delivered)
    services.emit(f"batch {batch.get('short_id', batch['id'])} done")
    return {"batch_id": batch["id"], "generation_ids": ids}
