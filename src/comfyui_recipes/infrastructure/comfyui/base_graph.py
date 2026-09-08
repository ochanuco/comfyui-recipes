"""Structural resolution of a base graph's semantic roles.

A base graph's node IDs are whatever the recipe or prior pass that produced
it happened to number them: a plain yukari base samples through KSampler
"3", a masked_redraw base through "19". Nothing here assumes a fixed ID --
every role is found by walking the graph's own edges.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

# Nodes a finished picture can pass through, unmodified, between its decode
# and its SaveImage. A finalize base's own matte (RemoveBackground ->
# MaskToImage) and delivered (YukariDeliver) branches are deliberately not
# here, so a finalize-of-a-finalize still resolves to the raw picture's save.
PASSTHROUGH = ("JoinImageWithAlpha", "LayeredDiffusionDecode", "InpaintStitchImproved")


def is_ref(value: object) -> bool:
    return isinstance(value, list) and len(value) == 2


def consumers(graph: Mapping) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {key: [] for key in graph}
    for key, node in graph.items():
        for value in node.get("inputs", {}).values():
            if is_ref(value) and value[0] in graph:
                result[value[0]].append(key)
    return result


def reaches(graph: Mapping, consumers_map: Mapping[str, list[str]], start: str,
           class_type: str) -> bool:
    stack = list(consumers_map.get(start, []))
    seen: set[str] = set()
    while stack:
        node_id = stack.pop()
        if node_id in seen:
            continue
        seen.add(node_id)
        if graph[node_id].get("class_type") == class_type:
            return True
        stack.extend(consumers_map.get(node_id, []))
    return False


def find_decode(graph: Mapping) -> str:
    """The one VAEDecode that is the source's finished picture.

    A base graph can carry a dangling first-pass VAEDecode (no consumer) and
    a redraw VAEDecode that a later pass re-encodes -- neither is it.
    """
    consumers_map = consumers(graph)
    candidates = [
        key for key, node in graph.items()
        if node.get("class_type") == "VAEDecode" and consumers_map.get(key)
        and not reaches(graph, consumers_map, key, "VAEEncode")]
    if len(candidates) != 1:
        raise ValueError(
            "expected exactly one final VAEDecode reachable without a "
            f"re-sample, found {len(candidates)}: {sorted(candidates)}")
    return candidates[0]


def find_sampler(graph: Mapping, decode_id: str) -> str:
    """The KSampler feeding `decode_id`, through any Latent*/SetLatentNoiseMask hop."""
    node_id = graph[decode_id]["inputs"]["samples"][0]
    seen: set[str] = set()
    while graph[node_id].get("class_type") != "KSampler":
        if node_id in seen:
            raise ValueError(
                f"could not trace a KSampler upstream of VAEDecode {decode_id!r}")
        seen.add(node_id)
        inputs = graph[node_id].get("inputs", {})
        if "samples" not in inputs:
            raise ValueError(
                f"could not trace a KSampler upstream of VAEDecode {decode_id!r}")
        node_id = inputs["samples"][0]
    return node_id


def source_prompts(graph: Mapping) -> tuple[str, str]:
    """The source's own final positive/negative CLIPTextEncode text."""
    decode_id = find_decode(graph)
    sampler_id = find_sampler(graph, decode_id)
    inputs = graph[sampler_id]["inputs"]
    positive = graph[inputs["positive"][0]]["inputs"]["text"]
    negative = graph[inputs["negative"][0]]["inputs"]["text"]
    return positive, negative


@dataclass(frozen=True)
class BaseRoles:
    save_id: str
    decode_id: str
    sampler_id: str
    positive_id: str
    negative_id: str
    stitched: bool


def _saves_downstream(graph: Mapping, consumers_map: Mapping[str, list[str]],
                      node_id: str) -> list[tuple[str, bool]]:
    """SaveImage nodes reachable from `node_id` through PASSTHROUGH only.

    Each result carries whether the walk to it crossed an
    InpaintStitchImproved -- the sampler's latent is then the inpaint crop,
    not the whole canvas.
    """
    found: list[tuple[str, bool]] = []
    for consumer_id in consumers_map.get(node_id, []):
        class_type = graph[consumer_id].get("class_type")
        if class_type == "SaveImage":
            found.append((consumer_id, False))
        elif class_type in PASSTHROUGH:
            found.extend(
                (save_id, crossed or class_type == "InpaintStitchImproved")
                for save_id, crossed in _saves_downstream(graph, consumers_map, consumer_id))
    return found


def base_roles(graph: Mapping) -> BaseRoles:
    """Resolve a base graph's sampler, decode, save and prompt roles.

    A finalize base can itself be a prior finalize's output: its decode also
    feeds a matte SaveImage (through RemoveBackground/MaskToImage) and a
    delivered SaveImage (through YukariDeliver). Neither class is
    PASSTHROUGH, so the forward walk to the raw picture's SaveImage ignores
    both and a finalize-of-a-finalize still picks the raw picture.
    """
    try:
        decode_id = find_decode(graph)
    except ValueError as exc:
        raise ValueError(
            f"base graph's SaveImage must be fed by a VAEDecode: {exc}") from exc
    consumers_map = consumers(graph)
    saves = _saves_downstream(graph, consumers_map, decode_id)
    if len(saves) != 1:
        raise ValueError(
            "expected exactly one SaveImage reachable from the decode "
            f"through {PASSTHROUGH}, found {len(saves)}: "
            f"{sorted(save_id for save_id, _ in saves)}")
    save_id, stitched = saves[0]
    sampler_id = find_sampler(graph, decode_id)
    sampler_inputs = graph[sampler_id].get("inputs", {})
    if "positive" not in sampler_inputs or "negative" not in sampler_inputs:
        raise ValueError(
            f"KSampler {sampler_id!r} has no positive/negative prompt refs")
    return BaseRoles(
        save_id=save_id, decode_id=decode_id, sampler_id=sampler_id,
        positive_id=sampler_inputs["positive"][0],
        negative_id=sampler_inputs["negative"][0], stitched=stitched)
