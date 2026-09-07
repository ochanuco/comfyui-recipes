"""ComfyUI nodes wrapping this repo's imaging functions unchanged.

Each node's body is: tensors in, PNG bytes out, call the existing function,
PNG bytes back to tensors. The imaging logic itself lives in
``comfyui_recipes.infrastructure.imaging`` and is not duplicated here.
"""

from __future__ import annotations

from comfyui_recipes.infrastructure.imaging import delivery, palette, recolor

from . import bridge


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
        }}

    def run(self, image, matte, keep_scene, transparent=False, stroke_light="",
           backdrop=""):
        image_png, matte_png = bridge.image_to_png(image), bridge.mask_to_png(matte)
        light = stroke_light or None
        if keep_scene:
            data, tag = delivery.keep_scene(image_png, matte_png)
        elif transparent:
            data, tag = delivery.transparent(image_png, matte_png, light=light)
        else:
            data, tag = delivery.clean_background(
                image_png, matte_png, light=light, backdrop=backdrop or None)
        mode = "RGBA" if (transparent and not keep_scene) else "RGB"
        return (bridge.png_to_image(data, mode), tag)


class YukariCompose:
    CATEGORY = "yukari"
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "tag")
    FUNCTION = "run"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
        }, "optional": {
            "backdrop": ("STRING", {"default": ""}),
            "stroke_light": ("STRING", {"default": ""}),
        }}

    def run(self, image, backdrop="", stroke_light=""):
        data, tag = delivery.compose(
            bridge.image_to_png(image), backdrop or None, light=stroke_light or None)
        return (bridge.png_to_image(data, "RGB"), tag)


NODE_CLASS_MAPPINGS = {
    "YukariRepinSkin": YukariRepinSkin,
    "YukariRepin": YukariRepin,
    "YukariRecolor": YukariRecolor,
    "YukariDeliver": YukariDeliver,
    "YukariCompose": YukariCompose,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "YukariRepinSkin": "Yukari Repin Skin",
    "YukariRepin": "Yukari Repin",
    "YukariRecolor": "Yukari Recolor",
    "YukariDeliver": "Yukari Deliver",
    "YukariCompose": "Yukari Compose",
}
