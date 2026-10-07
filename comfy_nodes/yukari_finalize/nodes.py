"""ComfyUI nodes wrapping this repo's imaging functions unchanged.

Each node's body is: tensors in, PNG bytes out, call the existing function,
PNG bytes back to tensors. The imaging logic itself lives in
``comfyui_recipes.infrastructure.imaging`` and is not duplicated here.
"""

from __future__ import annotations

from comfyui_recipes.infrastructure.imaging import (
    delivery, depth_blur, matting, palette, recolor, viewfinder)
from comfyui_recipes.infrastructure.imaging import light as lighting

from . import bridge, vitmatte


class YukariRepinSkin:
    CATEGORY = "yukari"
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "report")
    FUNCTION = "run"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
            "source": ("IMAGE",),
        }}

    def run(self, image, source):
        data, report = palette.repin_skin_png(
            bridge.image_to_png(source), bridge.image_to_png(image))
        return (bridge.png_to_image(data), "\n".join(report))


class YukariRepin:
    CATEGORY = "yukari"
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "report")
    FUNCTION = "run"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
            "keep_legwear": ("BOOLEAN", {"default": False}),
            "keep_legwear_cut": ("FLOAT", {"default": 0.62, "min": 0.0,
                                            "max": 1.0, "step": 0.01}),
        }}

    def run(self, image, keep_legwear, keep_legwear_cut):
        data, report = palette.repin_png(
            bridge.image_to_png(image),
            keep_legwear=keep_legwear_cut if keep_legwear else None)
        return (bridge.png_to_image(data), "\n".join(report))


class YukariRecolor:
    CATEGORY = "yukari"
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "report")
    FUNCTION = "run"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"image": ("IMAGE",)}}

    def run(self, image):
        data, report = recolor.recolor_png(bridge.image_to_png(image))
        return (bridge.png_to_image(data), "\n".join(report))


class YukariMatting:
    CATEGORY = "yukari"
    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "alpha")
    FUNCTION = "run"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"image": ("IMAGE",), "matte": ("MASK",)}}

    def run(self, image, matte):
        try:
            data, alpha = matting.matte_png(
                bridge.image_to_png(image), bridge.mask_to_png(matte),
                vitmatte.predict, vitmatte.foreground)
        finally:
            vitmatte.release()
        return (bridge.png_to_image(data), bridge.png_to_mask(alpha))


class YukariDeliver:
    CATEGORY = "yukari"
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "tag")
    FUNCTION = "run"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
            "matte": ("MASK",),
            "keep_scene": ("BOOLEAN", {"default": False}),
        }, "optional": {
            "transparent": ("BOOLEAN", {"default": False}),
            "stroke_light": ("STRING", {"default": ""}),
            "backdrop": ("STRING", {"default": ""}),
            "light_scene": ("STRING", {"default": ""}),
            "light_from": ("STRING", {"default": ""}),
            "matted": ("BOOLEAN", {"default": False}),
        }}

    def run(self, image, matte, keep_scene, transparent=False, stroke_light="",
           backdrop="", light_scene="", light_from="", matted=False):
        image_png, matte_png = bridge.image_to_png(image), bridge.mask_to_png(matte)
        light = stroke_light or None
        if keep_scene:
            data, tag = delivery.keep_scene(image_png, matte_png)
        elif transparent:
            data, tag = delivery.transparent(image_png, matte_png, light=light,
                                             matted=matted)
        else:
            data, tag = delivery.clean_background(
                image_png, matte_png, light=light, backdrop=backdrop or None,
                scene=light_scene or None, light_from=light_from or None,
                matted=matted)
        mode = "RGBA" if (transparent and not keep_scene) else "RGB"
        return (bridge.png_to_image(data, mode), tag)


class YukariDepthBlur:
    CATEGORY = "yukari"
    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "matte")
    FUNCTION = "run"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
            "depth": ("IMAGE",),
            "matte": ("MASK",),
            "focus_x": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0,
                                  "step": 0.001}),
            "focus_y": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0,
                                  "step": 0.001}),
            "f_number": ("FLOAT", {"default": 2.8, "min": 0.7, "max": 22.0,
                                   "step": 0.1}),
        }}

    def run(self, image, depth, matte, focus_x, focus_y, f_number):
        data, widened = depth_blur.depth_blur_png(
            bridge.image_to_png(image), bridge.image_to_png(depth),
            bridge.mask_to_png(matte), focus_x, focus_y, f_number)
        return (bridge.png_to_image(data), bridge.png_to_mask(widened))


class YukariLight:
    CATEGORY = "yukari"
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
            "depth": ("IMAGE",),
            "matte": ("MASK",),
            "direction": ("STRING", {"default": "nw"}),
            "scene": ("STRING", {"default": "sunset"}),
        }}

    def run(self, image, depth, matte, direction, scene):
        data = lighting.underpaint_png(
            bridge.image_to_png(image), bridge.image_to_png(depth),
            bridge.mask_to_png(matte), direction, scene)
        return (bridge.png_to_image(data),)


class YukariViewfinder:
    CATEGORY = "yukari"
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
            "focus_x": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0,
                                  "step": 0.001}),
            "focus_y": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0,
                                  "step": 0.001}),
            "f_number": ("FLOAT", {"default": 2.8, "min": 0.7, "max": 22.0,
                                   "step": 0.1}),
        }}

    def run(self, image, focus_x, focus_y, f_number):
        data = viewfinder.viewfinder_png(
            bridge.image_to_png(image), (focus_x, focus_y), f_number)
        return (bridge.png_to_image(data, "RGBA" if image.shape[-1] == 4 else "RGB"),)


class YukariDepthBlurLayered:
    CATEGORY = "yukari"
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
            "depth": ("IMAGE",),
            "matte": ("MASK",),
            "focus_x": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0,
                                  "step": 0.001}),
            "focus_y": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0,
                                  "step": 0.001}),
            "f_number": ("FLOAT", {"default": 2.8, "min": 0.7, "max": 22.0,
                                   "step": 0.1}),
            "backdrop": ("STRING", {"default": ""}),
        }}

    def run(self, image, depth, matte, focus_x, focus_y, f_number, backdrop):
        data = depth_blur.blur_layered_png(
            bridge.image_to_png(image), bridge.image_to_png(depth),
            bridge.mask_to_png(matte), focus_x, focus_y, f_number,
            backdrop or None)
        return (bridge.png_to_image(data),)


class YukariCompose:
    CATEGORY = "yukari"
    RETURN_TYPES = ("IMAGE", "STRING", "MASK")
    RETURN_NAMES = ("image", "tag", "mask")
    FUNCTION = "run"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
        }, "optional": {
            "backdrop": ("STRING", {"default": ""}),
            "stroke_light": ("STRING", {"default": ""}),
            "bands": ("BOOLEAN", {"default": True}),
        }}

    def run(self, image, backdrop="", stroke_light="", bands=True):
        image_png = bridge.image_to_png(image)
        data, tag = delivery.compose(
            image_png, backdrop or None, light=stroke_light or None, bands=bands)
        mask_png = delivery.compose_outside_mask(image_png, light=stroke_light or None)
        return (bridge.png_to_image(data, "RGB"), tag, bridge.png_to_mask(mask_png))


class YukariCutBackdrop:
    CATEGORY = "yukari"
    RETURN_TYPES = ("IMAGE", "MASK", "STRING")
    RETURN_NAMES = ("image", "matte", "tag")
    FUNCTION = "run"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
            "outside": ("MASK",),
        }, "optional": {
            "backdrop": ("STRING", {"default": ""}),
        }}

    def run(self, image, outside, backdrop=""):
        data, matte_png, tag = delivery.cut_backdrop(
            bridge.image_to_png(image), bridge.mask_to_png(outside), backdrop or None)
        return (bridge.png_to_image(data, "RGBA"), bridge.png_to_mask(matte_png), tag)


NODE_CLASS_MAPPINGS = {
    "YukariRepinSkin": YukariRepinSkin,
    "YukariRepin": YukariRepin,
    "YukariRecolor": YukariRecolor,
    "YukariMatting": YukariMatting,
    "YukariDeliver": YukariDeliver,
    "YukariDepthBlur": YukariDepthBlur,
    "YukariDepthBlurLayered": YukariDepthBlurLayered,
    "YukariLight": YukariLight,
    "YukariViewfinder": YukariViewfinder,
    "YukariCompose": YukariCompose,
    "YukariCutBackdrop": YukariCutBackdrop,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "YukariRepinSkin": "Yukari Repin Skin",
    "YukariRepin": "Yukari Repin",
    "YukariRecolor": "Yukari Recolor",
    "YukariMatting": "Yukari Matting",
    "YukariDeliver": "Yukari Deliver",
    "YukariDepthBlur": "Yukari Depth Blur",
    "YukariDepthBlurLayered": "Yukari Depth Blur Layered",
    "YukariLight": "Yukari Light",
    "YukariViewfinder": "Yukari Viewfinder",
    "YukariCompose": "Yukari Compose",
    "YukariCutBackdrop": "Yukari Cut Backdrop",
}
