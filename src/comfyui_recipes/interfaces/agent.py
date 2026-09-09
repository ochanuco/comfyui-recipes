"""The worker's composition root: wires a `WorkServices` from concrete adapters.

`interfaces/cli.py`'s `work` command and `comfy_nodes/yukari_worker` (hosting
the same claim loop inside ComfyUI's own process) both end up here, so the
wiring -- which sub-service does what, the hub/progress sockets, the drain
sentinel -- is written once.
"""

from __future__ import annotations

import socket
from collections.abc import Callable
from pathlib import Path

from ..application.finalize import FinalizeServices
from ..application.generate import GenerateServices, request_graph
from ..application.masked_redraw import MaskedRedrawServices
from ..application.repair import RepairServices
from ..application.work import WorkServices, work
from ..domain.generation.fingerprint import prompt_fingerprint
from ..domain.generation.prompt_lint import conflicts
from ..domain.yukari.recipe import render_spec as yukari_render_spec
from ..domain.yukari_anima.recipe import render_spec as anima_render_spec
from ..domain.yukari_sketch.recipe import render_spec as sketch_render_spec
from ..infrastructure.chimera.client import USER_AGENT, ChimeraClient
from ..infrastructure.comfyui.anima_graph import build_graph as anima_build_graph
from ..infrastructure.comfyui.client import ComfyUIClient
from ..infrastructure.comfyui.refinement_graph import chain_pass
from ..infrastructure.comfyui.yukari_graph import build_graph as yukari_build_graph
from ..infrastructure.imaging.delivery import graph_from_png, image_size
from ..infrastructure.imaging.palette import summarize
from ..infrastructure.notifications.discord import DiscordNotifier
from ..infrastructure.persistence.run_state import JsonRunState
from ..infrastructure.repository import discover_repository, git_metadata

# deploy writes this file to ask for a drain and waits for it to go; the
# worker removes it as its last act, so the wait ends on the worker's own
# acknowledgement rather than on a clock.
DRAIN_FILE = ".local/_nogit/worker/drain"

# Must track the `work` subparser's own defaults in interfaces/cli.py --
# there is no single source both can read, so a change to one without the
# other silently drifts.
DEFAULT_KINDS = ("generate", "finalize", "repair", "masked_redraw")

# `generation.recipe` -> (RenderSpec builder, ComfyUI graph builder).
RECIPES = {
    "yukari": (yukari_render_spec, yukari_build_graph),
    "yukari-anima": (anima_render_spec, anima_build_graph),
    "yukari-sketch": (sketch_render_spec, yukari_build_graph),
}


def _build_generation_graph(generation: dict, seed: int, prefix: str) -> dict:
    if generation.get("graph"):
        return request_graph(generation, seed, prefix, None, None)
    spec_builder, encode = RECIPES[generation["recipe"]]
    return request_graph(generation, seed, prefix, spec_builder, encode)


def _pose_fingerprint(recipe: str, pose: str) -> str | None:
    if recipe not in RECIPES:
        return None
    spec_builder, _ = RECIPES[recipe]
    # Fixed at the default costume: an override is a legitimate request-time
    # choice, so folding it in would make it indistinguishable from drift.
    spec = spec_builder(pose, 0, "fingerprint")
    return prompt_fingerprint(recipe, pose, spec.prompts.positive, spec.prompts.negative)


def build_generate_services(chimera: ChimeraClient, comfyui: ComfyUIClient, notifier: object,
                       repository: Path, repository_metadata) -> GenerateServices:
    return GenerateServices(
        management=chimera,
        comfyui=comfyui,
        state=JsonRunState(),
        notifier=notifier,
        graph_builder=_build_generation_graph,
        git_metadata=repository_metadata,
        conflicts=conflicts,
        output_root=repository / ".local/_nogit/chimera",
        measure=summarize,
        presets=chimera.get_preset,
        pose_fingerprint=_pose_fingerprint,
    )


def build_finalize_services(chimera: ChimeraClient, comfyui: ComfyUIClient, notifier: object,
                       repository: Path, repository_metadata) -> FinalizeServices:
    return FinalizeServices(
        management=chimera,
        comfyui=comfyui,
        graph_from_png=graph_from_png,
        chain_pass=chain_pass,
        git_metadata=repository_metadata,
        notifier=notifier,
        output_root=repository / ".local/_nogit/finalize",
        measure=summarize,
    )


def build_repair_services(chimera: ChimeraClient, comfyui: ComfyUIClient, notifier: object,
                     repository: Path, repository_metadata) -> RepairServices:
    return RepairServices(
        management=chimera,
        comfyui=comfyui,
        graph_from_png=graph_from_png,
        image_size=image_size,
        git_metadata=repository_metadata,
        notifier=notifier,
        output_root=repository / ".local/_nogit/repair",
    )


def build_masked_redraw_services(chimera: ChimeraClient, comfyui: ComfyUIClient, notifier: object,
                            repository: Path, repository_metadata) -> MaskedRedrawServices:
    return MaskedRedrawServices(
        management=chimera,
        comfyui=comfyui,
        graph_from_png=graph_from_png,
        image_size=image_size,
        git_metadata=repository_metadata,
        notifier=notifier,
        output_root=repository / ".local/_nogit/masked-redraw",
    )


def wire_work_services(chimera: ChimeraClient, comfyui: ComfyUIClient, notifier: object,
                        repository: Path, repository_metadata, *, worker_id: str,
                        kinds: tuple[str, ...], hub: bool = True,
                        emit: Callable[[str], None] = print) -> WorkServices:
    """Assemble a `WorkServices` from already-built adapters.

    Shared by `build_work_services` (which builds the adapters fresh) and
    `interfaces/cli.py` (which already has them, so its `ChimeraClient` stays
    the one it was constructed with).
    """
    hub_factory = None
    progress_factory = None
    if hub:
        from ..infrastructure.chimera.hub import HubConnection, hub_url
        from ..infrastructure.comfyui.progress import ProgressFeed

        def hub_factory() -> HubConnection:
            headers = {**chimera.credentials(), "User-Agent": USER_AGENT}
            return HubConnection(hub_url(chimera.base_url), headers).open()

        def progress_factory() -> ProgressFeed:
            return ProgressFeed(comfyui.base_url).open()

    drain_file = repository / DRAIN_FILE
    return WorkServices(
        management=chimera,
        generate_services=build_generate_services(
            chimera, comfyui, notifier, repository, repository_metadata),
        finalize_services=build_finalize_services(
            chimera, comfyui, notifier, repository, repository_metadata),
        repair_services=build_repair_services(
            chimera, comfyui, notifier, repository, repository_metadata),
        masked_redraw_services=build_masked_redraw_services(
            chimera, comfyui, notifier, repository, repository_metadata),
        git_metadata=repository_metadata,
        worker_id=worker_id,
        kinds=kinds,
        hub=hub_factory,
        progress_feed=progress_factory,
        draining=drain_file.exists,
        drained=lambda: drain_file.unlink(missing_ok=True),
        emit=emit,
    )


def build_work_services(repository: Path, *, worker_id: str,
                        kinds: tuple[str, ...], hub: bool = True,
                        emit: Callable[[str], None] = print) -> WorkServices:
    """Build a complete `WorkServices` from just a repository checkout.

    This is the entry point a host with no adapters of its own -- such as
    `comfy_nodes/yukari_worker` running inside ComfyUI's process -- uses to
    get a working claim loop.
    """
    chimera = ChimeraClient(repository)
    comfyui = ComfyUIClient()
    notifier = DiscordNotifier(repository)

    def repository_metadata() -> dict:
        return git_metadata(repository)

    return wire_work_services(
        chimera, comfyui, notifier, repository, repository_metadata,
        worker_id=worker_id, kinds=kinds, hub=hub, emit=emit)


def run(repository: Path | None = None, *, worker_id: str | None = None,
        kinds: tuple[str, ...] | None = None, interval: float = 30,
        hub: bool = True, publish_catalog: bool = True,
        once: bool = False, emit: Callable[[str], None] = print) -> None:
    """Build a `WorkServices` and run the claim loop until stopped."""
    repository = repository or discover_repository()
    services = build_work_services(
        repository,
        worker_id=worker_id or socket.gethostname(),
        kinds=kinds or DEFAULT_KINDS,
        hub=hub,
        emit=emit,
    )
    work(services, interval=interval, once=once, publish_catalog=publish_catalog)
