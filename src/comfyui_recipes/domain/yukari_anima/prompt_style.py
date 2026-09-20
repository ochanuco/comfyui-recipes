"""Yukari-anima's fixed prompt blocks and render constants.

Every block that is concatenated mid-prompt ends with its own ", " -- the
assembly in `recipe.py` only ever joins strings end to end, never inserts a
separator of its own. `STYLE` is the exception: it is always the tail of the
positive prompt, so it carries no trailing comma.
"""

from __future__ import annotations

QUALITY = "masterpiece, best quality, score_7, 1girl, solo, "
CHARACTER = ("yuzuki yukari, vocaloid, voiceroid, (@oshiki hitoshi:0.85), "
             "(@yoshikawa hideaki:0.5), ")
IDENTITY = ("light purple hair, short hair with long locks, very long "
            "sidelocks, purple eyes, hair ornament, ")
BODY = ("(mature female:1.3), (adult:1.2), (wide hips:1.2), (thick thighs:1.2), "
        "(soft thighs:1.3), (long legs:1.35), (narrow waist:1.25), "
        "adult proportions, long torso, seven heads tall, ")
BACKGROUND = "simple background, (green background:1.3), "
FACE = ("(large eyes:1.6), (big eyes:1.3), (round face:1.3), (tareme:1.2), "
        "(thick eyelashes:1.3), ")
STYLE = "(flat color:1.3), (sketch:1.3), (traditional media:1.2)"

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
GRADIENT_BAN = "(gradient:1.5), (soft shading:1.5), "
NEGATIVE_TAIL = ("(sparkling eyes:1.4), (glitter:1.3), "
                  "(multiple highlights:1.3), (gradient eyes:1.2), "
                  "(speed lines:1.45), (motion lines:1.4), "
                  "(emphasis lines:1.4), ")
HOOD_BAN = "(hood:1.3), (cardigan:1.3), "
GARMENT_BLACK_BAN = "(black jacket:1.35), (black clothes:1.3), (black hoodie:1.35), "
VIVID_BAN = ("(magenta:1.45), (pink legwear:1.45), (bright purple:1.35), "
             "(vivid colors:1.3), (neon:1.3), (red:1.3), (maroon:1.35), "
             "(wine red:1.3), ")
SCORE_BAN = "score_1, score_2, score_3"
PROPORTION_BAN = (", (fat:1.35), (chubby:1.35), (short legs:1.35), (muscular:1.3), "
                  "(toned:1.2), (child:1.3), (loli:1.3), (chibi:1.3), (aged down:1.2)")

MODEL = "anima-turbo-v1.1.safetensors"
WIDTH, HEIGHT = 1024, 1640
STEPS = 10
CFG = 2.0
SAMPLER = "euler"
SCHEDULER = "normal"
HIRES_DENOISE = 0.4
