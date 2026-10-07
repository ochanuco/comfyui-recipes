"""ComfyUI graph for the delivery of a picture Generation: cut, decorate, save."""

from __future__ import annotations

from ...domain.yukari.delivery_style import STROKE_CHOICES, Dof
from ..imaging import backdrops
from .refinement_graph import (
    _depth_nodes,
    _matte_nodes,
    delivery_tail,
    foreground_node,
    matting_node,
    save_mask,
)

ALPHA_SUFFIX = "-alpha"
DEPTH_SUFFIX = "-depth"


def deliver_graph(source_image: str, matte_model: str, prefix: str, *,
                  alpha_image: str | None = None,
                  depth_image: str | None = None,
                  skin: bool, repin: bool, recolor: bool,
                  keep_legwear: float | None, keep_scene: bool,
                  transparent: bool, backdrop: str | None,
                  stroke_light: str | None, deliver_size: int | None,
                  canvas: tuple[int, int], dof: Dof | None,
                  light_scene: str | None, light_from: str | None) -> dict:
    """The deliver graph over the uploaded `source_image`.

    `alpha_image` and `depth_image` are uploaded cut assets to load instead of
    computing; without them the graph cuts the unrepinned source itself and
    saves the result under `prefix` + ALPHA_SUFFIX / DEPTH_SUFFIX. Depth is
    only built when `dof` is set.
    """
    if stroke_light is not None and stroke_light not in STROKE_CHOICES:
        valid = ", ".join(repr(key) for key in STROKE_CHOICES)
        raise ValueError(f"stroke_light must be null or one of {valid}, got {stroke_light!r}")
    if backdrop is not None and not backdrops.is_backdrop(backdrop):
        valid = ", ".join(repr(key) for key in sorted(backdrops.PATTERNS))
        raise ValueError(
            f"backdrop must be null, a #RRGGBB colour or one of {valid}, got {backdrop!r}")
    graph: dict = {}
    cursor = 1

    def allocate() -> str:
        nonlocal cursor
        node_id = str(cursor)
        cursor += 1
        return node_id

    load_id = allocate()
    graph[load_id] = {"class_type": "LoadImage", "inputs": {"image": source_image}}
    source_ref = [load_id, 0]

    if alpha_image is not None:
        load_alpha = allocate()
        graph[load_alpha] = {"class_type": "LoadImage", "inputs": {
            "image": alpha_image}}
        to_mask = allocate()
        graph[to_mask] = {"class_type": "ImageToMask", "inputs": {
            "image": [load_alpha, 0], "channel": "red"}}
        alpha_ref = [to_mask, 0]
    else:
        coarse_ref = _matte_nodes(graph, allocate, source_ref, matte_model)
        alpha_ref = matting_node(graph, allocate, source_ref, coarse_ref)
        save_mask(graph, allocate, alpha_ref, prefix + ALPHA_SUFFIX)

    depth_ref = None
    if dof is not None:
        if depth_image is not None:
            load_depth = allocate()
            graph[load_depth] = {"class_type": "LoadImage", "inputs": {
                "image": depth_image}}
            depth_ref = [load_depth, 0]
        else:
            depth_ref = _depth_nodes(graph, allocate, source_ref)
            save_depth = allocate()
            graph[save_depth] = {"class_type": "SaveImage", "inputs": {
                "images": depth_ref, "filename_prefix": prefix + DEPTH_SUFFIX}}

    image_ref = source_ref
    if skin:
        repin_skin_id = allocate()
        graph[repin_skin_id] = {"class_type": "YukariRepinSkin", "inputs": {
            "image": image_ref, "source": source_ref}}
        image_ref = [repin_skin_id, 0]
    if recolor:
        recolor_id = allocate()
        graph[recolor_id] = {"class_type": "YukariRecolor", "inputs": {
            "image": image_ref}}
        image_ref = [recolor_id, 0]
    elif repin:
        repin_id = allocate()
        graph[repin_id] = {"class_type": "YukariRepin", "inputs": {
            "image": image_ref,
            "keep_legwear": keep_legwear is not None,
            "keep_legwear_cut": keep_legwear if keep_legwear is not None else 0.62}}
        image_ref = [repin_id, 0]
    if not keep_scene:
        image_ref = foreground_node(graph, allocate, image_ref, alpha_ref)

    delivery_tail(
        graph, allocate, image_ref, alpha_ref, depth_ref, prefix,
        keep_scene=keep_scene, transparent=transparent, backdrop=backdrop,
        stroke_light=stroke_light, deliver_size=deliver_size, canvas=canvas,
        dof=dof, light_scene=light_scene, light_from=light_from)
    return graph
