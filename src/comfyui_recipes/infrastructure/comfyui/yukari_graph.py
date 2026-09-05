"""Translate a pure Yukari render specification into a ComfyUI graph."""

from __future__ import annotations

from ...domain.generation.models import RenderSpec
from ...domain.yukari.recipe import render_spec


def build_graph(spec: RenderSpec) -> dict[str, dict]:
    graph = {
        "4": {"class_type": "DiffusersLoader",
              "inputs": {"model_path": spec.model_path}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {
            "batch_size": 1, "width": spec.width, "height": spec.height}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["4", 1], "text": spec.prompts.positive}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["4", 1], "text": spec.prompts.negative}},
        "3": {"class_type": "KSampler", "inputs": {
            "model": ["4", 0], "positive": ["6", 0],
            "negative": ["7", 0], "latent_image": ["5", 0],
            "seed": spec.seed, "steps": spec.steps, "cfg": spec.cfg,
            "sampler_name": spec.sampler_name, "scheduler": spec.scheduler,
            "denoise": spec.denoise}},
        "8": {"class_type": "VAEDecode", "inputs": {
            "samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {
            "images": ["8", 0], "filename_prefix": spec.filename_prefix}},
    }
    if spec.loras:
        if spec.hires is not None:
            raise ValueError(
                "yukari_graph.build_graph cannot combine spec.loras with "
                "spec.hires -- the hires pass ids would collide with the "
                "LoraLoader chain")
        model_ref, clip_ref = ["4", 0], ["4", 1]
        loader_id = 10
        for lora_name, weight in spec.loras:
            node_id = str(loader_id)
            graph[node_id] = {"class_type": "LoraLoader", "inputs": {
                "model": model_ref, "clip": clip_ref, "lora_name": lora_name,
                "strength_model": weight, "strength_clip": weight}}
            model_ref, clip_ref = [node_id, 0], [node_id, 1]
            loader_id += 1
        graph["3"]["inputs"]["model"] = model_ref
        graph["6"]["inputs"]["clip"] = clip_ref
        graph["7"]["inputs"]["clip"] = clip_ref
    if spec.hires is None:
        return graph

    graph["10"] = {"class_type": "LatentUpscale", "inputs": {
        "samples": ["3", 0], "upscale_method": "bicubic",
        "width": spec.hires.width, "height": spec.hires.height,
        "crop": "disabled"}}
    graph["11"] = {"class_type": "KSampler", "inputs": {
        "model": ["4", 0], "positive": ["6", 0],
        "negative": ["7", 0], "latent_image": ["10", 0],
        "seed": spec.seed, "steps": spec.steps, "cfg": spec.cfg,
        "sampler_name": spec.sampler_name, "scheduler": spec.scheduler,
        "denoise": spec.hires.denoise}}
    if spec.hires.positive is not None:
        graph["6b"] = {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["4", 1], "text": spec.hires.positive}}
        graph["11"]["inputs"]["positive"] = ["6b", 0]
    graph["7b"] = {"class_type": "CLIPTextEncode", "inputs": {
        "clip": ["4", 1], "text": spec.hires.negative}}
    graph["11"]["inputs"]["negative"] = ["7b", 0]
    graph["8"]["inputs"]["samples"] = ["11", 0]
    return graph


def build(pose: str, seed: int, prefix: str, hires: int = 0,
          denoise: float | None = None, costume: str = "default") -> dict:
    """Compatibility builder with the legacy recipe signature."""
    return build_graph(render_spec(
        pose, seed, prefix, hires=hires, denoise=denoise, costume=costume))
