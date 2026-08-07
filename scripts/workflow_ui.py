#!/usr/bin/env python3
"""Convert an API-format ComfyUI graph into the litegraph ("UI") format.

The API format (`{node_id: {"class_type": ..., "inputs": {...}}}`) is what
`/prompt` accepts, but it carries no layout or widget/socket distinction, so
the web UI cannot open it and a PNG saved from it has no `workflow` chunk to
drop back onto the canvas. `/object_info` is the only place that distinction
lives -- it says which of a node's declared inputs are link sockets (MODEL,
CLIP, IMAGE, ...) versus widgets (INT, FLOAT, STRING, BOOLEAN, or a combo) --
so the converter needs a copy of it to do its job.
"""

from __future__ import annotations

import json
import urllib.request

# Primitive widget types. Everything else that is a plain string (MODEL,
# CLIP, VAE, CONDITIONING, LATENT, IMAGE, MASK, CONTROL_NET, IPADAPTER, ...)
# is a link socket. A combo is a widget too, and object_info spells it two
# different ways: either the type slot holds the choice list directly, or it
# holds the literal string "COMBO" with the choices under opts["options"].
_WIDGET_PRIMITIVES = {"INT", "FLOAT", "STRING", "BOOLEAN"}


def fetch_object_info(host: str, port: int) -> dict:
    """GET /object_info once. It runs to a few MB, hence the timeout -- a
    stuck ComfyUI should fail the fetch quickly rather than hang the queue."""
    url = f"http://{host}:{port}/object_info"
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read())


def _is_link_type(type_val) -> bool:
    if isinstance(type_val, list):
        return False
    if type_val == "COMBO":
        return False
    return type_val not in _WIDGET_PRIMITIVES


def _merged_inputs(class_info: dict) -> dict[str, tuple]:
    """name -> (type, opts) in declared order, required before optional."""
    inp = class_info.get("input", {})
    merged: dict[str, tuple] = {}
    for bucket in ("required", "optional"):
        for name, spec in (inp.get(bucket) or {}).items():
            type_val = spec[0]
            opts = spec[1] if len(spec) > 1 else {}
            merged[name] = (type_val, opts)
    return merged


def _default_for(type_val, opts: dict):
    if "default" in opts:
        return opts["default"]
    if isinstance(type_val, list) and type_val:
        return type_val[0]
    if type_val == "COMBO":
        options = opts.get("options") or []
        return options[0] if options else None
    if type_val == "BOOLEAN":
        return False
    if type_val == "INT":
        return 0
    if type_val == "FLOAT":
        return 0.0
    if type_val == "STRING":
        return ""
    return None


def _looks_like_link(value, prompt: dict) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[1], int)
        and str(value[0]) in prompt
    )


def api_to_ui(prompt: dict[str, dict], object_info: dict) -> dict:
    node_ids = sorted(prompt, key=int)

    # Pass 1: resolve each class's declared shape and, per node, which of its
    # connected inputs are links -- in spec order, since that order becomes
    # both widgets_values order and each input's slot index.
    merged_by_node: dict[str, tuple[dict, dict]] = {}
    link_names_by_node: dict[str, list[str]] = {}
    for nid in node_ids:
        class_type = prompt[nid]["class_type"]
        info = object_info.get(class_type)
        if info is None:
            raise RuntimeError(
                f"/object_info has no entry for class {class_type!r} (node {nid})"
            )
        merged = _merged_inputs(info)
        merged_by_node[nid] = (info, merged)
        api_inputs = prompt[nid].get("inputs", {})
        link_names_by_node[nid] = [
            name
            for name, (type_val, _opts) in merged.items()
            if _is_link_type(type_val)
            and name in api_inputs
            and _looks_like_link(api_inputs[name], prompt)
        ]

    # Pass 2: assign link ids and record outgoing links per (node, out slot).
    links: list[list] = []
    link_id_for: dict[tuple[str, str], int] = {}
    outgoing: dict[str, dict[int, list[int]]] = {nid: {} for nid in node_ids}
    for nid in node_ids:
        api_inputs = prompt[nid]["inputs"]
        for slot_index, name in enumerate(link_names_by_node[nid]):
            src_node, src_slot = api_inputs[name]
            src_node, src_slot = str(src_node), int(src_slot)
            src_outputs = merged_by_node.get(src_node, (object_info.get(prompt[src_node]["class_type"], {}),))[0].get("output", [])
            declared_type = merged_by_node[nid][1][name][0]
            link_type = src_outputs[src_slot] if src_slot < len(src_outputs) else declared_type
            link_id = len(links) + 1
            links.append([link_id, int(src_node), src_slot, int(nid), slot_index, link_type])
            link_id_for[(nid, name)] = link_id
            outgoing[src_node].setdefault(src_slot, []).append(link_id)

    # Pass 3: topological order (Kahn's algorithm) plus a longest-path depth
    # for column layout. Ties broken by numeric node id for determinism.
    preds: dict[str, set] = {nid: set() for nid in node_ids}
    succs: dict[str, set] = {nid: set() for nid in node_ids}
    for _link_id, src, _src_slot, dst, _dst_slot, _type in links:
        preds[str(dst)].add(str(src))
        succs[str(src)].add(str(dst))

    remaining_indegree = {nid: len(preds[nid]) for nid in node_ids}
    order_of: dict[str, int] = {}
    depth_of: dict[str, int] = {}
    ready = sorted((nid for nid in node_ids if remaining_indegree[nid] == 0), key=int)
    order_counter = 0
    while ready:
        ready.sort(key=int)
        nid = ready.pop(0)
        order_of[nid] = order_counter
        order_counter += 1
        depth_of[nid] = max((depth_of[p] + 1 for p in preds[nid]), default=0)
        for s in succs[nid]:
            remaining_indegree[s] -= 1
            if remaining_indegree[s] == 0:
                ready.append(s)
    # A cycle would leave nodes unvisited; ComfyUI would have rejected such a
    # graph at /prompt already, but fall back to id order rather than crash.
    for nid in node_ids:
        if nid not in order_of:
            order_of[nid] = order_counter
            order_counter += 1
            depth_of[nid] = max((depth_of.get(p, 0) + 1 for p in preds[nid]), default=0)

    depth_row = {}
    nodes_json = []
    for nid in node_ids:
        node = prompt[nid]
        class_type = node["class_type"]
        info, merged = merged_by_node[nid]
        api_inputs = node.get("inputs", {})

        widgets_values = []
        for name, (type_val, opts) in merged.items():
            if _is_link_type(type_val):
                continue
            value = api_inputs[name] if name in api_inputs else _default_for(type_val, opts)
            widgets_values.append(value)
            if opts.get("control_after_generate"):
                widgets_values.append("fixed")

        inputs_json = [
            {
                "name": name,
                "type": merged[name][0],
                "link": link_id_for[(nid, name)],
            }
            for name in link_names_by_node[nid]
        ]

        out_types = info.get("output", [])
        out_names = info.get("output_name", out_types)
        outputs_json = [
            {
                "name": out_names[slot] if slot < len(out_names) else out_type,
                "type": out_type,
                "links": outgoing[nid].get(slot) or None,
                "slot_index": slot,
            }
            for slot, out_type in enumerate(out_types)
        ]

        depth = depth_of[nid]
        row = depth_row.get(depth, 0)
        depth_row[depth] = row + 1

        nodes_json.append(
            {
                "id": int(nid),
                "type": class_type,
                "pos": [depth * 420, row * 220],
                "size": [400, 200],
                "flags": {},
                "order": order_of[nid],
                "mode": 0,
                "inputs": inputs_json,
                "outputs": outputs_json,
                "properties": {"Node name for S&R": class_type},
                "widgets_values": widgets_values,
            }
        )

    return {
        "last_node_id": max(int(nid) for nid in node_ids),
        "last_link_id": len(links),
        "nodes": nodes_json,
        "links": links,
        "groups": [],
        "config": {},
        "extra": {},
        "version": 0.4,
    }
