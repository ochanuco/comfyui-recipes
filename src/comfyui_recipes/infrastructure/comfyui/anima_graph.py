"""Translate a pure Yukari-anima render specification into a ComfyUI graph."""

from __future__ import annotations

from ...domain.generation.models import RenderSpec

CLIP_NAME = "qwen_3_06b_base.safetensors"
VAE_NAME = "qwen_image_vae.safetensors"


def build_graph(spec: RenderSpec) -> dict[str, dict]:
    if spec.hires is not None:
        raise ValueError("yukari-anima has no second pass -- spec.hires must be None")
    return {
        "1": {"class_type": "UNETLoader", "inputs": {
            "unet_name": spec.model_path, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": CLIP_NAME, "type": "qwen_image"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": VAE_NAME}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {
            "width": spec.width, "height": spec.height, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["2", 0], "text": spec.prompts.positive}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["2", 0], "text": spec.prompts.negative}},
        "3": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["5", 0], "seed": spec.seed, "steps": spec.steps,
            "cfg": spec.cfg, "sampler_name": spec.sampler_name,
            "scheduler": spec.scheduler, "denoise": spec.denoise}},
        "8": {"class_type": "VAEDecode", "inputs": {
            "samples": ["3", 0], "vae": ["4", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {
            "images": ["8", 0], "filename_prefix": spec.filename_prefix}},
    }
