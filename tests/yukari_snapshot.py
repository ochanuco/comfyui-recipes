"""Canonical Yukari recipe snapshot used across package moves."""

from __future__ import annotations

import dataclasses
import hashlib
import json


def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def snapshot(recipe, costume_fingerprint: str, delivery_fingerprint: str,
             *, seed: int, prefix: str) -> dict:
    """Hash every public prompt and complete base/hires graph.

    ``recipe`` is intentionally structural rather than imported here. During
    the migration the implementation moves from ``scripts/yukari_recipe.py``
    into the package, while this contract and its canonicalization stay fixed.
    """
    poses = sorted(recipe.POSES)
    costumes = sorted(recipe.COSTUMES)
    result = {
        "pose_count": len(poses),
        "poses": poses,
        "costumes": costumes,
        "costume_fingerprint": costume_fingerprint,
        "delivery_fingerprint": delivery_fingerprint,
        "pose_records_sha256": _digest({
            name: dataclasses.asdict(recipe.POSE_RECORDS[name])
            for name in poses
        }),
        "costume_records_sha256": _digest({
            name: recipe.COSTUMES[name]
            for name in costumes
        }),
        "by_costume": {},
    }
    for costume in costumes:
        positive = []
        negative = []
        base_graphs = []
        hires_graphs = []
        graph_prefix = f"{prefix}-{costume}"
        for pose in poses:
            positive.append([pose, recipe.positive(pose, costume)])
            negative.append([pose, recipe.negative(pose, costume)])
            base_graphs.append([
                pose,
                recipe.build(pose, seed, graph_prefix, 0, None, costume),
            ])
            hires_graphs.append([
                pose,
                recipe.build(pose, seed, graph_prefix, 2048, None, costume),
            ])
        result["by_costume"][costume] = {
            "positive_sha256": _digest(positive),
            "negative_sha256": _digest(negative),
            "base_graph_sha256": _digest(base_graphs),
            "hires_2048_graph_sha256": _digest(hires_graphs),
        }
    return result
