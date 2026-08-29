"""Finalize one selected generation as a recorded refinement batch."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..domain.yukari import delivery_style
from ..domain.yukari.prompt_style import HANDDRAWN_FINISH, SHADE_BAN, THIN


@dataclass(frozen=True)
class FinalizeServices:
    management: object
    comfyui: object
    graph_from_png: Callable[[bytes], dict]
    chain_pass: Callable[..., dict]
    deliver: Callable[[bytes], tuple[bytes, str]]
    git_metadata: Callable[[], dict]
    notifier: object
    output_root: Path
    emit: Callable[[str], None] = print


def finalize(generation_id: str, services: FinalizeServices, *,
             denoise: float | None = None, handdrawn: bool = False) -> None:
    if denoise is None:
        denoise = delivery_style.FINALIZE_DENOISE
    context = services.management.request(
        "GET", f"/api/v1/generations/{generation_id}/context")
    picked = services.management.fetch_generation_image(generation_id)
    base = services.graph_from_png(picked)
    seed = base["3"]["inputs"]["seed"]
    prefix = f"fin-{generation_id}"
    positive = base["6"]["inputs"]["text"]
    if handdrawn:
        positive = positive.replace(", " + THIN, "") + HANDDRAWN_FINISH
    toe_ban = "" if "barefoot" in positive else "(toes:1.55), "
    negative = toe_ban + SHADE_BAN + base["7"]["inputs"]["text"]
    graph = services.chain_pass(
        base, 2048, denoise, prefix, prompt=(positive, negative))
    prompt_id = services.comfyui.submit(graph)
    services.emit(f"{prefix} {prompt_id}")
    image = services.comfyui.wait_for(prompt_id)[-1]
    raw = services.comfyui.fetch(image)
    delivered, tag = services.deliver(raw)
    services.output_root.mkdir(parents=True, exist_ok=True)
    stem = Path(image["filename"]).stem
    delivered_name = f"{stem}-{tag}-delivered.png"
    (services.output_root / image["filename"]).write_bytes(raw)
    (services.output_root / delivered_name).write_bytes(delivered)

    git = services.git_metadata()
    batch = services.management.request("POST", "/api/v1/batches", {
        "idempotency_key": str(uuid.uuid4()),
        "raw_instruction": (f"{generation_id} を高解像度化"
                            + ("・手書き風の仕上げ" if handdrawn else "")),
        "recipe": "yukari",
        "parameters": {"kind": "hires-chain",
                       "base_generation": generation_id,
                       "size": 2048, "denoise": denoise,
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
        {"idempotency_key": str(uuid.uuid4()), "seed": seed, "index": 0})
    services.management.request(
        "PATCH", f"/api/v1/jobs/{job['id']}",
        {"status": "queued", "comfy_prompt_id": prompt_id, "graph": graph})
    services.management.request(
        "PATCH", f"/api/v1/jobs/{job['id']}", {"status": "completed"})
    urls = []
    for index, (name, data) in enumerate(
            [(image["filename"], raw), (delivered_name, delivered)]):
        rendered = services.management.request(
            "POST", f"/api/v1/jobs/{job['id']}/generations",
            multipart=({"seed": seed, "original_filename": name,
                        "comfy_output_index": index},
                       "image", name, data, "image/png"))
        urls.append(rendered["canonical_url"])
        services.emit(f"{name} -> {rendered['canonical_url']}")
    services.management.request(
        "PATCH", f"/api/v1/jobs/{job['id']}", {"status": "ingested"})
    services.management.request(
        "PATCH", f"/api/v1/batches/{batch['id']}", {"status": "completed"})
    services.notifier.send(
        f"**finalize** `{generation_id}`\n"
        f"**file** `{delivered_name}`\n"
        f"**chimera** {urls[1]}", delivered_name, delivered)
    services.emit(f"batch {batch.get('short_id', batch['id'])} done")
