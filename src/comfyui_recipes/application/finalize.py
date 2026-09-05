"""Finalize one selected generation as a recorded refinement batch."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..domain.generation.models import PromptPair
from ..domain.yukari import delivery_style
from ..domain.yukari.recipe import refinement_prompt
from ..domain.yukari_anima import delivery_style as anima_delivery_style
from ..domain.yukari_anima.recipe import refinement_prompt as anima_refinement_prompt
from ..domain.yukari_sketch import delivery_style as sketch_delivery_style
from ..domain.yukari_sketch.recipe import refinement_prompt as sketch_refinement_prompt
from ..infrastructure.comfyui.refinement_graph import DELIVERED_SUFFIX, MATTE_SUFFIX

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


def finalize(generation_id: str, services: FinalizeServices, *,
             denoise: float | None = None, handdrawn: bool = False,
             apply_repin: bool = False, apply_skin: bool = False,
             apply_recolor: bool = False,
             keep_legwear: float | None = None,
             keep_scene: bool = False,
             toe_guard: float | None = None,
             size: int | None = None, latent_route: bool | None = None,
             finalizer: str | None = None,
             key_prefix: str | None = None) -> dict:
    context = services.management.request(
        "GET", f"/api/v1/generations/{generation_id}/context")
    picked = services.management.fetch_generation_image(generation_id)
    base = services.graph_from_png(picked)
    # A LoraLoader in the base graph marks a sketch render; a UNETLoader
    # (checked only once sketch is ruled out) marks an anima render -- a
    # base graph carries at most one of the two.
    is_sketch = any(node.get("class_type") == "LoraLoader"
                    for node in base.values())
    is_anima = (not is_sketch) and any(
        node.get("class_type") == "UNETLoader" for node in base.values())
    if denoise is None:
        denoise = (sketch_delivery_style.FINALIZE_DENOISE if is_sketch
                   else anima_delivery_style.FINALIZE_DENOISE if is_anima
                   else delivery_style.FINALIZE_DENOISE)
    if size is None:
        size = (sketch_delivery_style.FINALIZE_SIZE if is_sketch
                else anima_delivery_style.FINALIZE_SIZE if is_anima
                else FINALIZE_SIZE)
    if latent_route is None:
        latent_route = is_sketch and sketch_delivery_style.FINALIZE_LATENT_ROUTE
    seed = base["3"]["inputs"]["seed"]
    prefix = f"fin-{generation_id}"
    base_prompt = PromptPair(
        base["6"]["inputs"]["text"],
        base["7"]["inputs"]["text"],
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
    # Recolor wins over repin, same rule the redraw graph applies.
    recolor_applied = apply_recolor
    repin_applied = apply_repin and not apply_recolor
    skin_applied = apply_skin
    source_image = None
    if skin_applied:
        source_image = services.comfyui.upload_image(
            f"{prefix}-source.png", picked)
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
        source_image=source_image)
    prompt_id = services.comfyui.submit(graph)
    services.emit(f"{prefix} {prompt_id}")
    outputs = services.comfyui.wait_for(prompt_id)
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
    ids, urls = [], []
    for index, (name, data) in enumerate(
            [(image["filename"], raw), (delivered_name, delivered)]):
        rendered = services.management.request(
            "POST", f"/api/v1/jobs/{job['id']}/generations",
            multipart=({"seed": seed, "original_filename": name,
                        "comfy_output_index": index},
                       "image", name, data, "image/png"))
        ids.append(rendered["id"])
        urls.append(rendered["canonical_url"])
        services.emit(f"{name} -> {rendered['canonical_url']}")
    # The matte is the silhouette of the raw redraw, not of the delivered
    # composite, so it hangs off generation 0. Storing it is what lets the
    # cutout be redone later without re-running the 2048 pass.
    services.management.request(
        "POST", f"/api/v1/generations/{ids[0]}/assets",
        multipart=({"role": "mask"}, "file", matte_name, matte, "image/png"))
    services.emit(f"{matte_name} -> mask on {ids[0]}")
    services.management.request(
        "PATCH", f"/api/v1/jobs/{job['id']}", {"status": "ingested"})
    services.management.request(
        "PATCH", f"/api/v1/batches/{batch['id']}", {"status": "completed"})
    services.notifier.send(
        f"**finalize** `{generation_id}`\n"
        f"**file** `{delivered_name}`\n"
        f"**chimera** {urls[1]}", delivered_name, delivered)
    services.emit(f"batch {batch.get('short_id', batch['id'])} done")
    return {"batch_id": batch["id"], "generation_ids": ids}
