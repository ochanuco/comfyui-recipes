"""Torch tensor <-> PNG byte conversions for the finalize node pack.

The array-level functions have no torch dependency, so the bridge's numpy
core can be tested without it; the tensor wrappers import torch lazily so the
package still imports on a Python that has no ComfyUI/torch installed.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image


def array_to_png(array: np.ndarray, mode: str) -> bytes:
    output = io.BytesIO()
    Image.fromarray(array, mode).save(output, "PNG")
    return output.getvalue()


def png_to_array(data: bytes, mode: str) -> np.ndarray:
    return np.array(Image.open(io.BytesIO(data)).convert(mode))


def image_to_png(tensor) -> bytes:
    """First batch item of an IMAGE tensor ([B, H, W, C] float32 0..1).

    RGB for 3 channels, RGBA for 4 -- a layerdiffuse compose's own alpha
    rides through this same tensor shape.
    """
    array = np.clip(tensor[0].cpu().numpy() * 255.0, 0, 255).astype(np.uint8)
    mode = "RGBA" if array.shape[-1] == 4 else "RGB"
    return array_to_png(array, mode)


def png_to_image(data: bytes, mode: str = "RGB"):
    """A PNG as a [1, H, W, C] float32 0..1 IMAGE tensor; mode="RGBA" for 4 channels."""
    import torch
    array = png_to_array(data, mode).astype(np.float32) / 255.0
    return torch.from_numpy(array)[None, ...]


def mask_to_png(tensor) -> bytes:
    """First batch item of a MASK tensor ([B, H, W] float32 0..1) as L."""
    array = np.clip(tensor[0].cpu().numpy() * 255.0, 0, 255).astype(np.uint8)
    return array_to_png(array, "L")


def png_to_mask(data: bytes):
    """An L-mode PNG as a [1, H, W] float32 0..1 MASK tensor."""
    import torch
    array = png_to_array(data, "L").astype(np.float32) / 255.0
    return torch.from_numpy(array)[None, ...]
