"""Yukari-sketch's fixed prompt blocks and render constants.

Every block ends with its own ", " so `recipe.py` can join them end to end
with no separator of its own -- `BODY` is the exception, since it is always
the tail of the positive prompt and carries no trailing comma.
"""

from __future__ import annotations

QUALITY = "masterpiece, best quality, "
TRIGGER = "sketch, traditional media, "
CHARACTER = "1girl, solo, yuzuki yukari, vocaloid, voiceroid, "
IDENTITY = ("(light purple hair:1.15), (short hair with long locks:1.25), "
            "(very long sidelocks:1.2), (purple eyes:1.15), "
            "(hair ornament:1.2), ")
PROPORTION = "(long legs:1.2), (tall:1.1), adult, "
BACKGROUND = "(simple background:1.3), (grey background:1.2), "
LEGWEAR = ("(black pantyhose:1.3), (pale purple pantyhose:1.15), "
           "(gradient legwear:1.2), ")
FACE = ("(tareme:1.2), (half-closed eyes:1.2), (unamused:1.1), "
        "closed mouth, looking at viewer, ")
BODY = ("(wide hips:1.2), (thick thighs:1.3), (soft thighs:1.2), "
        "narrow waist, pale skin")

NEGATIVE = (
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad "
    "hands, extra fingers, extra limbs, watermark, signature, text, (brown "
    "legwear:1.4), brown pantyhose, (fishnet:1.3), (upskirt:1.3), panties, "
    "(from below:1.2), (blue legwear:1.4), (mismatched legwear:1.4), "
    "(skirt:1.2), (see-through dress:1.3), (hood up:1.4), (huge "
    "breasts:1.3), (large breasts:1.2), cleavage, (cropped jacket:1.3), "
    "midriff, navel, (thighhighs:1.4), (kneehighs:1.4), (socks:1.3), "
    "(multiple girls:1.3), (3d:1.3), (realistic:1.2), (child:1.2), "
    "(loli:1.2), (chibi:1.25), (short legs:1.15), (blue background:1.5), "
    "(blue tint:1.4)"
)

MODEL = "hassaku-il-v22"
LORA = ("sketch-style-xl-linaqruf.safetensors", 0.8)
WIDTH, HEIGHT = 832, 1664
STEPS = 30
CFG = 5.0
SAMPLER = "dpmpp_2m"
SCHEDULER = "karras"
