"""Yukari-anima's fixed prompt blocks and render constants.

Every block that is concatenated mid-prompt ends with its own ", " -- the
assembly in `recipe.py` only ever joins strings end to end, never inserts a
separator of its own. `STYLE` is the exception: it is always the tail of the
positive prompt, so it carries no trailing comma.
"""

from __future__ import annotations

QUALITY = "masterpiece, best quality, score_7, 1girl, solo, "
CHARACTER = "yuzuki yukari, vocaloid, voiceroid, (@ixy:0.7), "
IDENTITY = ("light purple hair, short hair with long locks, very long "
            "sidelocks, purple eyes, hair ornament, ")
BODY = ("(wide hips:1.4), (thick thighs:1.4), (plump thighs:1.2), "
        "(curvy:1.15), (narrow waist:1.2), ")
BACKGROUND = "simple background, grey background, "
FACE = ("(large eyes:1.4), (round face:1.3), (tareme:1.2), "
        "(thick eyelashes:1.3), ")
STYLE = ("(flat color:1.7), (anime coloring:1.4), (cel shading:1.2), "
         "(limited palette:1.6), (few colors:1.3), "
         "(matte:1.5), (minimal shading:1.2), (flat shadow:1.2), "
         "(thin lineart:1.3), (simple lines:1.3), "
         "(minimal lines:1.2), (black lineart:1.35), (black outline:1.2)")

DIGIT_BAN = "(extra digits:1.5), bad anatomy, bad hands, "
DETAIL_BAN = ("(detailed:1.3), (intricate:1.3), (highly detailed:1.3), "
              "(fine details:1.2), ")
COLORED_LINE_BAN = ("(colored lineart:1.4), (colored outline:1.3), "
                     "(purple lineart:1.2), ")
THIN_BODY_BAN = ("(skinny:1.3), (thin legs:1.3), (slender legs:1.2), "
                  "(slender:1.1), ")
SHINE_BAN = ("(shiny:1.4), (glossy:1.3), (shiny hair:1.4), "
             "(shiny clothes:1.3), (specular highlights:1.3), "
             "(reflection:1.2), (hair highlights:1.2), (watercolor:1.3), "
             "(ink wash:1.3), (painterly:1.3), ")
HATCH_BAN = ("(hatching:1.5), (crosshatching:1.4), (pencil shading:1.3), "
             "(sketch shading:1.2), ")
GRADIENT_BAN = "(gradient:1.5), (soft shading:1.5), "
NEGATIVE_TAIL = ("(sparkling eyes:1.4), (glitter:1.3), "
                  "(multiple highlights:1.3), (gradient eyes:1.2), "
                  "(speed lines:1.45), (motion lines:1.4), "
                  "(emphasis lines:1.4), (hood:1.3), (cardigan:1.3), "
                  "score_1, score_2, score_3")

MODEL = "hassakuAnima_v13.safetensors"
WIDTH, HEIGHT = 1536, 1920
STEPS = 25
CFG = 3.5
SAMPLER = "er_sde"
SCHEDULER = "normal"
