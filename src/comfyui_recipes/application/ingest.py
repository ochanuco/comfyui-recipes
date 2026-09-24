"""Classify a ComfyUI submission's outputs and record them into chimera."""

from __future__ import annotations

import uuid
from pathlib import Path

from ..infrastructure.comfyui.refinement_graph import DELIVERED_SUFFIX, MATTE_SUFFIX


def generation_key(key_prefix: str | None, job_index: int,
                   output_index: int) -> str:
    if key_prefix is not None:
        return f"{key_prefix}:job:{job_index}:gen:{output_index}"
    return str(uuid.uuid4())


def asset_key(key_prefix: str | None, job_index: int, role: str) -> str:
    if key_prefix is not None:
        return f"{key_prefix}:job:{job_index}:asset:{role}"
    return str(uuid.uuid4())


def classify_outputs(outputs: list) -> tuple[list, list, list]:
    mattes = [out for out in outputs if MATTE_SUFFIX in out["filename"]]
    delivereds = [out for out in outputs if DELIVERED_SUFFIX in out["filename"]]
    pictures = [out for out in outputs
                if MATTE_SUFFIX not in out["filename"]
                and DELIVERED_SUFFIX not in out["filename"]]
    return pictures, delivereds, mattes


def record_job(management, batch_id: str, *, key_prefix: str | None, index: int,
               seed: int, prompt_id: str, graph: dict) -> dict:
    job_key = (f"{key_prefix}:job:{index}"
               if key_prefix is not None else str(uuid.uuid4()))
    job = management.request(
        "POST", f"/api/v1/batches/{batch_id}/jobs",
        {"idempotency_key": job_key, "seed": seed, "index": index})
    management.request(
        "PATCH", f"/api/v1/jobs/{job['id']}",
        {"status": "queued", "comfy_prompt_id": prompt_id, "graph": graph})
    management.request(
        "PATCH", f"/api/v1/jobs/{job['id']}", {"status": "completed"})
    return job


def upload_generation(management, emit, job_id: str, *, seed: int, name: str,
                      data: bytes, index: int,
                      idempotency_key: str | None = None) -> dict:
    rendered = management.request(
        "POST", f"/api/v1/jobs/{job_id}/generations",
        multipart=({"seed": seed, "original_filename": name,
                    "comfy_output_index": index,
                    "idempotency_key": idempotency_key or str(uuid.uuid4())},
                   "image", name, data, "image/png"))
    emit(f"{name} -> {rendered['canonical_url']}")
    return rendered


def attach_asset(management, generation_id: str, *, role: str, name: str,
                 data: bytes, idempotency_key: str | None = None) -> None:
    management.request(
        "POST", f"/api/v1/generations/{generation_id}/assets",
        multipart=({"role": role,
                    "idempotency_key": idempotency_key or str(uuid.uuid4())},
                   "file", name, data, "image/png"))


def ingest_seed_render(*, comfyui, management, output_root: Path, emit,
                       batch_id: str, key_prefix: str | None, index: int,
                       seed: int, prompt_id: str, graph: dict, job_prefix: str,
                       mask_png: bytes) -> dict:
    outputs = comfyui.wait_for(prompt_id)
    pictures, delivereds, mattes = classify_outputs(outputs)
    if not pictures:
        raise SystemExit(f"{job_prefix} produced no raw output")
    raw_out = pictures[-1]
    raw = comfyui.fetch(raw_out)
    (output_root / raw_out["filename"]).write_bytes(raw)

    job = record_job(management, batch_id, key_prefix=key_prefix, index=index,
                     seed=seed, prompt_id=prompt_id, graph=graph)

    ids: list[str] = []
    urls: list[str] = []
    rendered = upload_generation(management, emit, job["id"], seed=seed,
                                 name=raw_out["filename"], data=raw, index=0,
                                 idempotency_key=generation_key(
                                     key_prefix, index, 0))
    raw_generation_id = rendered["id"]
    ids.append(raw_generation_id)
    urls.append(rendered["canonical_url"])

    if delivereds:
        delivered_out = delivereds[-1]
        delivered = comfyui.fetch(delivered_out)
        (output_root / delivered_out["filename"]).write_bytes(delivered)
        rendered = upload_generation(management, emit, job["id"], seed=seed,
                                     name=delivered_out["filename"],
                                     data=delivered, index=1,
                                     idempotency_key=generation_key(
                                         key_prefix, index, 1))
        ids.append(rendered["id"])
        urls.append(rendered["canonical_url"])

    if mattes:
        matte_out = mattes[-1]
        matte = comfyui.fetch(matte_out)
        (output_root / matte_out["filename"]).write_bytes(matte)
        attach_asset(management, raw_generation_id, role="mask",
                     name=matte_out["filename"], data=matte,
                     idempotency_key=asset_key(key_prefix, index, "mask"))
        emit(f"{matte_out['filename']} -> mask on {raw_generation_id}")

    attach_asset(management, raw_generation_id, role="repair-mask",
                 name=f"{job_prefix}-mask.png", data=mask_png,
                 idempotency_key=asset_key(key_prefix, index, "repair-mask"))

    management.request(
        "PATCH", f"/api/v1/jobs/{job['id']}", {"status": "ingested"})

    return {"generation_ids": ids, "generation_urls": urls,
            "raw_filename": raw_out["filename"], "raw": raw}
