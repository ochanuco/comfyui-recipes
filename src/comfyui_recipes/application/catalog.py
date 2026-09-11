"""The recipe catalog: every pose, costume and patch target this checkout
serves, published to chimera under the worker's branch.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from ..domain.generation.patches import (
    LAYERDIFFUSE_CONFIGS,
    NUMBER_CONSTRAINTS,
    NUMBER_TARGETS,
    STRING_TARGETS,
    TEXT_OPS,
    TEXT_TARGETS,
)
from ..domain.yukari.costumes import COSTUMES as YUKARI_COSTUMES
from ..domain.yukari.dials import DIALS as YUKARI_DIALS
from ..domain.yukari.poses import POSE_RECORDS
from ..domain.yukari.recipe import identity_tags as yukari_identity_tags
from ..domain.yukari.recipe import render_spec as yukari_render_spec
from ..domain.yukari_anima.costumes import COSTUMES as ANIMA_COSTUMES
from ..domain.yukari_anima.dials import DIALS as ANIMA_DIALS
from ..domain.yukari_anima.expressions import EXPRESSIONS as ANIMA_EXPRESSIONS
from ..domain.yukari_anima.poses import POSES as ANIMA_POSES
from ..domain.yukari_anima.recipe import identity_tags as anima_identity_tags
from ..domain.yukari_anima.recipe import render_spec as anima_render_spec
from ..domain.yukari_sketch.costumes import COSTUMES as SKETCH_COSTUMES
from ..domain.yukari_sketch.dials import DIALS as SKETCH_DIALS
from ..domain.yukari_sketch.poses import POSES as SKETCH_POSES
from ..domain.yukari_sketch.recipe import departures as sketch_departures
from ..domain.yukari_sketch.recipe import identity_tags as sketch_identity_tags
from ..domain.yukari_sketch.recipe import render_spec as sketch_render_spec
from ..domain.yukari_sketch.recipe import resolved_face as sketch_resolved_face
from .generate import KNOWN_PARAMETERS, RECIPE_REJECTED_PARAMETERS

SCHEMA_VERSION = 1
_SEED, _PREFIX = 0, "catalog"


class Management(Protocol):
    def put_catalog(self, recipe_ref: str, catalog: dict) -> dict: ...


def _parameters(recipe: str) -> dict:
    rejected = RECIPE_REJECTED_PARAMETERS.get(recipe, frozenset())
    return {
        "allowed": sorted(KNOWN_PARAMETERS - rejected),
        "rejected": sorted(rejected),
    }


def _yukari_recipe() -> dict:
    poses = []
    model = None
    for name in sorted(POSE_RECORDS):
        spec = yukari_render_spec(name, _SEED, _PREFIX)
        model = spec.model_path
        poses.append({
            "name": name,
            "costume": "default",
            "face": None,
            "canvas": [spec.width, spec.height],
            "positive": spec.prompts.positive,
            "negative": spec.prompts.negative,
        })
    return {
        "name": "yukari",
        "model": model,
        "parameters": _parameters("yukari"),
        "costumes": sorted(YUKARI_COSTUMES),
        "poses": poses,
        "parts": [],
        "identity_tags": sorted(yukari_identity_tags(sorted(POSE_RECORDS)[0], "default")),
        "dials": YUKARI_DIALS,
    }


def _sketch_recipe() -> dict:
    poses = []
    model = None
    for name in sorted(SKETCH_POSES):
        pose = SKETCH_POSES[name]
        spec = sketch_render_spec(name, _SEED, _PREFIX)
        model = spec.model_path
        poses.append({
            "name": name,
            "costume": pose.costume,
            "face": sketch_resolved_face(name),
            "parent": pose.parent,
            "departures": sketch_departures(name),
            "canvas": [spec.width, spec.height],
            "positive": spec.prompts.positive,
            "negative": spec.prompts.negative,
            "parts": [{"name": part_name, "text": text}
                     for part_name, text in spec.positive_parts],
        })
    return {
        "name": "yukari-sketch",
        "model": model,
        "parameters": _parameters("yukari-sketch"),
        "costumes": sorted(SKETCH_COSTUMES),
        "poses": poses,
        "parts": [name for name, _ in
                 sketch_render_spec(sorted(SKETCH_POSES)[0], _SEED, _PREFIX).positive_parts],
        "identity_tags": sorted(sketch_identity_tags(sorted(SKETCH_POSES)[0], "default")),
        "dials": SKETCH_DIALS,
    }


def _anima_recipe() -> dict:
    poses = []
    model = None
    for name in sorted(ANIMA_POSES):
        pose = ANIMA_POSES[name]
        spec = anima_render_spec(name, _SEED, _PREFIX)
        model = spec.model_path
        poses.append({
            "name": name,
            "costume": pose.costume,
            "face": None,
            "expression": pose.expression,
            "canvas": [spec.width, spec.height],
            "positive": spec.prompts.positive,
            "negative": spec.prompts.negative,
            "parts": [{"name": part_name, "text": text}
                     for part_name, text in spec.positive_parts],
        })
    return {
        "name": "yukari-anima",
        "model": model,
        "parameters": _parameters("yukari-anima"),
        "costumes": sorted(ANIMA_COSTUMES),
        "expressions": sorted(ANIMA_EXPRESSIONS),
        "poses": poses,
        "parts": [name for name, _ in
                 anima_render_spec(sorted(ANIMA_POSES)[0], _SEED, _PREFIX).positive_parts],
        "identity_tags": sorted(anima_identity_tags(sorted(ANIMA_POSES)[0])),
        "dials": ANIMA_DIALS,
    }


_TEXT_OP_KEYS = {
    "append": ["value"], "prepend": ["value"],
    "replace": ["old", "value"], "remove": ["old"],
}


def _patches_block() -> dict:
    return {
        "keys": ["target", "op", "value", "old", "reason"],
        "text": {
            "targets": list(TEXT_TARGETS),
            "part_target": "prompt.positive.<part>",
            "ops": {op: _TEXT_OP_KEYS[op] for op in TEXT_OPS},
        },
        "number": {
            target: {"op": "set", "constraints": NUMBER_CONSTRAINTS[target]}
            for target in NUMBER_TARGETS
        },
        "string": {
            target: {
                "op": "set",
                "values": (list(LAYERDIFFUSE_CONFIGS)
                          if target == "render.layerdiffuse_config" else None),
            }
            for target in STRING_TARGETS
        },
        "overrides": {
            "identity_override": (
                "non-empty reason string; required when patches or a prompt "
                "override remove identity_tags"),
        },
    }


def build_catalog(git: dict) -> dict:
    """The catalog document for this worker checkout. Pure -- no I/O."""
    return {
        "schema_version": SCHEMA_VERSION,
        "git_commit": git.get("commit"),
        "git_branch": git.get("branch"),
        "git_dirty": bool(git.get("dirty")),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "recipes": [_yukari_recipe(), _anima_recipe(), _sketch_recipe()],
        "patches": _patches_block(),
    }


def publish_catalog(client: Management, git: dict, catalog: dict | None = None) -> dict:
    """PUT the catalog document to chimera, upserting on the worker's branch."""
    document = catalog if catalog is not None else build_catalog(git)
    return client.put_catalog(git.get("branch"), document)
