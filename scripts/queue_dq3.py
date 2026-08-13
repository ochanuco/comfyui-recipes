#!/usr/bin/env python3
"""Queue Dragon Quest III class portraits through the local ComfyUI API.

Wraps the novaAnimeXL recipe that was tuned interactively: black pantyhose with
a sheer/shiny finish, calves weighted up without widening the hips, and negative
prompts that keep the model from adding horned helmets, swords or glossy skin.
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import workflow_ui

REPO_ROOT = Path(__file__).resolve().parent.parent

# Body and legwear. Tuned so "thick" reads as soft tissue rather than muscle:
# muscular* in the negatives is what stops calves from turning sinewy, and the
# hip/ass negatives keep the extra volume in the legs instead of the pelvis.
LEGS = (
    "young woman, long legs, (thick thighs:1.6), (thick calves:1.4), (thick legs:1.15), "
    "soft calves, soft legs, smooth legs, "
    "(black pantyhose:1.75), (opaque legwear:1.45), (black legwear:1.3), nylon legwear, (taut clothes:1.35), (stretched fabric:1.25), (shiny legwear:1.4), (specular highlights:1.25), light streaks"
)

# Per class, because the weighted thighs above are a Dragon Quest choice and the
# legs negatives that support them rule out thighhighs entirely.
LEGS_BY_JOB = {
    "yukari": (
        "young woman, long legs, slender legs, "
        "(purple thighhighs:1.3), (zettai ryouiki:1.2), thighhighs"
    ),
    # Takao's flesh dose lives in EXTRA_BY_JOB, not here: the same four tags
    # baked into this block darkened the whole palette and flattened the
    # staging — at the end of the prompt they do neither. Canon legwear is
    # thighhighs with garter straps, not the pantyhose block.
    "takao": (
        "young woman, (long legs:1.3), "
        "soft legs, smooth legs, "
        "(black thighhighs:1.4), thighhighs, (garter straps:1.3), "
        "(opaque legwear:1.3), (shiny legwear:1.3)"
    ),
}


QUALITY = "masterpiece, best quality, amazing quality, very aesthetic, absurdres"
# masterpiece and very aesthetic are Illustrious aesthetic-score tags: they buy
# polish at the cost of pulling every face toward the same averaged one.
QUALITY_PLAIN = "best quality, absurdres"

# Left unset the model emits its default face, which is what reads as generic.
# Eyebrows and eye size matter more than they look -- they are the parts the
# averaged face flattens hardest.
FACES = {
    "default": "",
    "sharp": (
        "(tsurime:1.2), narrow eyes, small eyes, (thick eyebrows:1.15), "
        "sharp chin, high cheekbones, small mouth, expressionless"
    ),
    "soft": (
        "(tareme:1.2), hooded eyes, round face, soft jawline, thin eyebrows, "
        "small mouth, light smile, (mole under eye:1.2)"
    ),
    "retro": (
        "retro artstyle, 1980s (style), (small eyes:1.2), thin eyebrows, "
        "sharp chin, narrow eyes, flat color"
    ),
    "freckled": (
        "(freckles:1.3), round face, (thick eyebrows:1.2), small eyes, "
        "wide nose, light smile, (mole under mouth:1.1)"
    ),
    # Rebuilt against ref-eye1 and ref-face2: tall round eyes with the outer
    # corner dropped, a deep blue iris, and lashes kept to a plain dark upper
    # line. The long/thick lash tags that used to be here drew fans of separate
    # hairs, which is busier than either reference. tareme and large eyes both
    # need weights -- unweighted they lose to the eye LoRA's own shape.
    "moe": (
        # The state that produced the preferred result. Later passes rebuilt it
        # against newer references -- round face, 2010s era, a reworked iris --
        # and every one of them drifted away from it; reverted wholesale.
        "(tareme:1.5), (large eyes:1.65), round eyes, "
        "2000s (style), eyelashes, (dark blue eyes:1.3), (large iris:1.6), "
        "thin eyebrows, (light smile:1.2), closed mouth, small mouth, "
        "soft expression, looking at viewer"
    ),
    # moe's weights assume the face fills a good part of the frame. In a
    # full-body standing shot it does not, and demanding a huge iris on a small
    # face has no solution -- the render comes back as coloured blocks. This is
    # the same intent at weights the distance can carry.
    "moe-far": (
        "(tareme:1.3), (large eyes:1.3), round eyes, "
        "2000s (style), eyelashes, (dark blue eyes:1.2), (large iris:1.25), "
        "thin eyebrows, light smile, closed mouth, small mouth, "
        "soft expression, looking at viewer"
    ),
    # moe-far without the spelled colour, for the minimal path, where the colour
    # comes from EYES_BY_JOB instead.
    #
    # This rung is what the backdrop eye actually responds to. Bisected one tag
    # at a time against moe-mid-noeye on the two seeds that reliably grew it:
    # dropping (large iris:1.4) alone made it WORSE both times (eyes drawn onto
    # her thigh), dropping (large eyes:1.45) alone cleared both. So the driver is
    # eye AREA, not iris size, and the defect is that demand overflowing onto
    # empty canvas -- the floating eye, the chibi clone and the eyed grey object
    # are the same overflow landing differently, and the same seed slides between
    # the three as the prompt is perturbed. At this rung: 2/2 of the dirty seeds
    # clean, 4/4 previously-clean seeds still clean, and the face still reads.
    "moe-far-noeye": (
        "(tareme:1.3), (large eyes:1.3), round eyes, "
        "2000s (style), eyelashes, (large iris:1.25), "
        "thin eyebrows, light smile, closed mouth, small mouth, "
        "soft expression, looking at viewer"
    ),
    # Probe for the collapse threshold between moe-far (clean at standing)
    # and moe (collapses there).
    "moe-mid": (
        "(tareme:1.4), (large eyes:1.45), round eyes, "
        "2000s (style), eyelashes, (dark blue eyes:1.25), (large iris:1.4), "
        "thin eyebrows, (light smile:1.1), closed mouth, small mouth, "
        "soft expression, looking at viewer"
    ),
    # moe-mid with the eye colour left out, for characters whose own tag
    # carries it (Takao's red). Adding an eye colour on top of a character
    # tag is spare eye pressure — it fed the backdrop intruder.
    "moe-mid-noeye": (
        "(tareme:1.4), (large eyes:1.45), round eyes, "
        "2000s (style), eyelashes, (large iris:1.4), "
        "thin eyebrows, (light smile:1.1), closed mouth, small mouth, "
        "soft expression, looking at viewer"
    ),
    "halflid": (
        "(half-closed eyes:1.15), hooded eyes, tareme, eyeliner, thin eyebrows, "
        "swept bangs, side locks, "
        "sharp chin, small mouth, closed mouth, expressionless, "
        "(blush:1.25), nose blush"
    ),
}

# Per-class outfits follow the original Toriyama artwork: bare shoulders with
# elbow-length gloves, not the sleeved robe the bare class tag tends to produce.
CLASSES = {
    "sage": (
        # Eye colour is left to the face preset now, so the two cannot argue.
        "sage (dq3), (dark blue hair:1.5), (black hair:1.2), black tinted shadows, (medium hair:1.3), straight hair, "
        "(gold headband:1.3), blue gem, (tube top:1.35), strapless, bare shoulders, "
        "(plain white dress:1.35), white dress, (thigh length dress:1.3), (no pattern:1.2), brown belt, (yellow elbow gloves:1.3), "
        "teal cape, teal scarf, (yellow boots:1.2), (quarterstaff:1.35), plain wooden pole, holding pole"
    ),
    # (mini robe:1.3) is load-bearing: at full length the robe drapes over the
    # legs and the pantyhose comes out blotched with stray dark or light patches.
    "priest": (
        "priest (dq3), (light blue hair:1.2), (medium hair:1.3), red eyes, "
        "blue robe, (mini robe:1.3), thigh length robe, yellow cross, tall hat, "
        "yellow gloves, yellow boots, (holding staff:1.2), wooden staff"
    ),
    # Yukari's own tag carries her colouring; what needs spelling out is the
    # hooded outfit, since the tag alone returns her default costume.
    "yukari": (
        "yuzuki yukari, (light purple hair:1.25), (short hair with long locks:1.45), (very long sidelocks:1.3), sidelocks, "
        "(purple eyes:1.25), hair between eyes, hair ornament, "
        # No ear tag on purpose. (pink rabbit ears:1.3), fake animal ears used to
        # sit here and she grew a real pair on her head on top of the hood's --
        # "fake" does not stop the model drawing them for real. Deleting the ear
        # tag is not enough either: on the seed this started from the extra pair
        # survived both the deletion and a reword to (fake rabbit ears),
        # (ears on hood), and taking "fake animal ears" with it brought
        # duplicates and floating objects. Raising the hood instead gives the
        # ear demand one place to land. 5 of 6 seeds clean; the sixth is
        # 3409564303, which has been Yukari's bad seed since the backdrop eyes.
        "(black hoodie:1.35), open hoodie, (rabbit hood:1.55), animal hood, "
        "rabbit print, "
        "long sleeves, drawstring, (purple dress:1.2), short dress, frills"
    ),
    # Taken from the danbooru wiki rather than from memory, after the two wrong
    # guesses that cost Takao a round each. Sword and shield are canon and are
    # deliberately absent: held objects are the tag most likely to fight the
    # pose, and this block is already long.
    "momiji": (
        "inubashiri momiji, (white hair:1.25), short hair, (red eyes:1.25), "
        "(wolf ears:1.35), animal ear fluff, (wolf tail:1.3), tail, "
        "(red tokin:1.35), tokin hat, pom pom (clothes), "
        "(white sleeveless turtleneck:1.3), sleeveless, "
        "(detached sleeves:1.3), white detached sleeves, "
        "(black and red skirt:1.3), (maple leaf print:1.25), short skirt"
    ),
    # From the danbooru wiki and her co-tag frequencies, not from memory -- the
    # rule Takao's two wasted rounds bought.
    #
    # (hair over one eye:1.35) is the one weight that has to be up: it is the
    # single thing that distinguishes her from every other grey-haired destroyer,
    # and at 1.0 it comes and goes by seed.
    #
    # Canon legwear is brown pantyhose, and LEGWEAR_GUARD bans brown pantyhose by
    # name -- it exists because Hassaku renders black legwear as dark brown, so
    # the ban and her design want the same pixels for opposite reasons. She gets
    # black here, which is also what most of her fan art draws. Asking for canon
    # brown means dropping those three terms from the guard first, and then
    # nothing stops any other black legwear in the frame going brown.
    "hamakaze": (
        "hamakaze (kancolle), (grey hair:1.3), short hair, "
        "(hair over one eye:1.35), (eyes visible through hair:1.2), "
        "(blue eyes:1.25), (hairclip:1.25), hair ornament, "
        "(serafuku:1.3), (white shirt:1.25), (blue sailor collar:1.35), "
        "(yellow neckerchief:1.3), (white gloves:1.3), "
        "(black pleated skirt:1.3), pleated skirt"
    ),
    "mage": (
        "mage (dq3), (purple hair:1.2), (medium hair:1.3), "
        "(blue wizard hat:1.2), pointy hat, (yellow robe:1.2), short robe, blue cape, "
        "white belt, orange gloves, orange boots, (holding staff:1.2), wooden staff"
    ),
    # Like Yukari, the character tag carries her colouring. The uniform is
    # spelled out because the default negatives lean against military dress;
    # no rigging — the ship equipment stays out unless asked for. tall is
    # canon for her, and it is also what balances the leg volume at standing.
    "takao": (
        # Rewritten from the danbooru wiki after two wrong guesses (red
        # jacket, then black; brown hair; pantyhose; white gloves — all
        # invented). Canon: black bob, red eyes, blue beret, blue dress
        # shirt with white ascot, blue miniskirt, black thighhighs with
        # garter straps, black gloves.
        "takao (kancolle), (short hair:1.15), black hair, black tinted shadows, tall, "
        "(blue beret:1.3), beret, (blue shirt:1.25), dress shirt, (white ascot:1.2), "
        "(blue miniskirt:1.25), miniskirt, "
        "(black gloves:1.2), black footwear, boots"
    ),
}

# Applied when --lora is not passed at all. Each entry carries the trigger word
# its LoRA expects, so callers do not have to remember them.
# Checkpoints that need ModelSamplingDiscrete. DiffusersLoader does not read the
# scheduler config, so this has to be stated somewhere, and the checkpoint knows
# it better than the caller does.
V_PRED_MODELS = {"moe-vpred-v2"}

# Each trace mode pairs a preprocessor with a ControlNet trained on that signal;
# the two cannot be swapped independently. Canny reproduces every outline, so it
# carries the reference's costume, proportions and framing along with its pose.
# OpenPose carries joint positions and nothing else, which is what borrowing a
# pose actually means -- the reference's art style never reaches the output.
TRACE_MODES = {
    "canny": "noob-canny-fp16.safetensors",
    "openpose": "noob-openpose-fp16.safetensors",
    "softedge": "ill-softedge-fp16.safetensors",
}

# openpose is the mode that borrows a pose without borrowing anything else, and
# it only works when a body is detected -- which, on illustrations, it usually
# is not. Six references were tried and one traced. softedge does not detect
# anything: it is an edge filter, so it always produces a hint. The cost is that
# the reference's silhouette comes with the pose, so the costume has to be
# pushed back by releasing the hint early (--trace-end).
SOFT_MODES = {"softedge"}

DEFAULT_LORAS = [
    ("perfect-eyes-ill.safetensors", 0.7, "perfect eyes"),
    ("detailed-perfection-ill.safetensors", 0.5, "detailed"),
]

# Rendering, as opposed to FACES (features) and POSES (framing). Illustrious
# carries style mostly on artist tags, so these only approximate a look -- they
# get the gloss and the light right and leave the linework to the checkpoint.
STYLES = {
    "default": "",
    "glossy": (
        "(shiny hair:1.2), glossy hair, detailed hair, soft shading, "
        "smooth shading, detailed skin, sharp lineart, "
        "depth of field, blurry background, bokeh, soft lighting, "
        "warm lighting, backlighting, rim light"
    ),
    # Thin lines and gradients instead of sharp lineart. "subsurface scattering"
    # and "ambient occlusion" used to be here: they are 3D-render vocabulary this
    # model has no grounding for, and combined with a masked IPAdapter pass they
    # filled the unconstrained area with a rendered-looking panel.
    "painterly": (
        "(thin lineart:1.2), delicate lines, fine linework, "
        "(soft shading:1.2), smooth shading, gradient shading, "
        "(shiny hair:1.15), detailed hair, detailed skin, "
        "depth of field, blurry background, soft lighting"
    ),
    # Bishoujo-game CG: bloom, particles and jewel eyes. The old advice to pair
    # it with --negative-preset light does not survive a trace: light drops the
    # monster/intruder protections and the backdrop grew a boulder. Keep full,
    # and flatten the paint with anti-impasto negatives instead:
    #   --negative-extra "(impasto:1.4), (painterly:1.4), (oil painting
    #   (medium):1.3), (heavy shading:1.3), (detailed shading:1.3),
    #   (realistic:1.2)"
    # (abc-I1; flattening the positive on top of that went further than the
    # galge look wants.)
    # "pastel colors" and a bare "gradient" used to be here and turned the
    # rendering chalky, like crayon. The light effects are weighted down too:
    # at 1.2 they spent themselves on the background instead of the figure.
    "rich": (
        "(detailed shading:1.35), volumetric lighting, rim light, "
        "(gradient shading:1.15), soft shadows, ambient light, "
        "(detailed skin:1.15), skin shading, (shiny hair:1.2), detailed hair, "
        "colorful, vivid colors, depth of field, "
        # Illustrious tints outlines to match the fill, which reads as soft and
        # machine-made; asking for thin black ink is what brings the drawn look.
        "(thin lineart:1.55), (fine linework:1.3), delicate lines, thin outlines, "
        "(black outline:1.4), (black lineart:1.3), (dark lineart:1.2), crisp lines, clean lineart, (defined hair strands:1.2), hair strand outline"
    ),
    # Flat colour with hard-edged shadow shapes, the opposite of "rich". Black
    # interior lines and cel shading reinforce each other; gradients fight them,
    # which is why mixing the two never looked right.
    "cel": (
        "(cel shading:1.5), (flat color:1.45), (limited palette:1.35), "
        "few colors, (anime screencap:1.15), "
        "(sharp shadow edges:1.45), (two-tone shading:1.35), "
        "(hard shadow edge:1.2), (dark shadows:1.3), deep shadow tone, "
        "(saturated colors:1.15), (shaded:1.25), "
        "(thin lineart:1.5), (black lineart:1.35), (simple lineart:1.2), "
        "simple clothes, (simple hair:1.2), hair as masses, "
        "clean lineart, crisp lines, simple shading, soft colors, "
        "(white outline:1.6), outline, sticker"
    ),
    # The flat-colour look those ~100-checkpoint comparison sheets render: what
    # Amanatsu and Hassaku draw on six tokens with nothing forcing them. It is
    # not "cel with the shadows turned down". cel wants black ink, hard shadow
    # shapes and saturation; this wants a thin tinted line, no shadow shape at
    # all, and the chroma pulled out of the skin. The two cannot be blended.
    #
    # Needs --negative-preset pastel. On the full preset three of the tags that
    # make this look — (washed out), (pale skin) and the pale/coloured lineart
    # run in NEG_TOON — sit in the negative, so no base can reach it.
    "pastel": (
        "(flat color:1.55), (pastel colors:1.4), (muted colors:1.3), "
        "(limited palette:1.35), few colors, (low contrast:1.3), "
        "(pale colors:1.25), soft colors, "
        "(minimal shading:1.35), flat shading, no shadow, "
        "(thin lineart:1.55), (colored lineart:1.4), (brown lineart:1.2), "
        "delicate lines, fine linework, "
        "simple clothes, (simple hair:1.2), hair as masses, soft lighting"
    ),
    "galge": (
        "(game cg:1.15), official art, visual novel cg, "
        "(detailed eyes:1.3), shiny eyes, "
        "(smooth shading:1.15), soft shading, cel shading, clean lineart, "
        "shiny hair, detailed skin, soft lighting, depth of field"
    ),
}

# cel without the sticker border. Derived rather than copied so the two cannot
# drift apart -- everything else about the look is meant to stay identical.
#
# Dropping the border does more than remove an outline: the cape spreads wider,
# the legwear gloss comes up, and the whole thing reads as an illustration
# rather than a die-cut sticker. On Hassaku that is the preferred result.
STYLES["cel-plain"] = STYLES["cel"].replace(", (white outline:1.6), outline, sticker", "")
assert STYLES["cel-plain"] != STYLES["cel"], "the border tags moved; fix this replacement"

# Kept beside CLASSES rather than hardcoded into the prompt: it anchors the
# palette for the Dragon Quest classes, and would poison anything else.
# The moe face carries weights pushed to their limit for the sage; stacked on
# another character's tag the prompt stops resolving and the render turns to
# noise. Classes can name a face that suits them instead.
FACE_BY_JOB = {"yukari": "default", "takao": "moe-mid-noeye"}

# Appended to the end of the positive, after the LoRA triggers. Position is
# the point: Takao's flesh dose (the fl3 rung) carried baked into the LEGS
# block darkened the palette and dropped the wall-shadow staging on the same
# seed; at the tail of the prompt it does neither (order-fl3).
EXTRA_BY_JOB = {
    "takao": "(thick thighs:1.45), (curvy:1.25), (plump:1.2), soft body",
}

# The base decides the face far more than the face preset does. Six bases were
# rendered on one seed with a byte-identical prompt: the same moe-mid-noeye tags
# — (large eyes:1.45), (tareme:1.4), (large iris:1.4) — come out as a long face
# with narrow eyes on hassaku, amanatsu, novaAnime and NoobAI, and as a small
# round face with large round irises on moe-vpred-v2. Held on four further
# seeds, so it is the base's reading of the tags, not seed luck. Chasing the
# face through tag weights has a low ceiling; swapping the base clears it.
#
# That is still true, and moe-vpred-v2 is still the base with the best face. It
# is not the base named here, because the face is not the only thing being
# chosen. The colouring work that followed settled on Hassaku: it and Amanatsu
# share the flat-colour palette the whole recipe is now aimed at, and
# moe-vpred-v2 is the one base that does not -- it wants a white ground and a
# heavy black line, and it refuses a coloured field outright. Every accepted
# render from that point on is Hassaku's.
#
# So this entry is a compromise recorded on purpose: the colouring wins, and the
# face is bought back through the face preset instead. If the face ever matters
# more than the palette, the two are swapped here and nowhere else.
BASE_BY_JOB = {"takao": "hassaku-il-v22", "sage": "hassaku-il-v22",
               "yukari": "hassaku-il-v22", "momiji": "hassaku-il-v22",
               "hamakaze": "hassaku-il-v22"}

# --minimal carries no legs block, so legwear is whatever the base felt like on
# the day -- bare on most seeds. These are the standing choices. Kept to the
# fewest words that name the garment, because on the minimal path every added
# tag is a thing the sampler now has to draw; the elaborate legs blocks in
# LEGS_BY_JOB belong to the full path and are not reused here.
LEGWEAR_BY_JOB = {
    "sage": "(black pantyhose:1.3), pantyhose, (shiny legwear:1.45), glossy legwear",
    "takao": "(black thighhighs:1.35), thighhighs, (shiny legwear:1.45), glossy legwear",
    # Yukari's own thighhighs are purple, so hers is the same garment in her own
    # colour rather than the black the other two were asked for.
    "yukari": "(purple thighhighs:1.35), thighhighs, (shiny legwear:1.45), glossy legwear",
    "momiji": "(black pantyhose:1.3), pantyhose, (shiny legwear:1.45), glossy legwear",
    # Black, not her canon brown -- see the note on her CLASSES entry.
    "hamakaze": "(black pantyhose:1.3), pantyhose, (shiny legwear:1.45), glossy legwear",
}

# A highlight band is a shading feature, so a palette that forbids shading
# forbids the gloss with it. Without this the only way to get any shine was to
# push (shiny legwear) past 1.5, and there the model stops lighting the fabric
# and starts replacing it -- latex on the tights, and the gloves and boots going
# glossy along with them. At 1.45 plus these two the band appears on cloth and
# nothing else in the frame turns shiny.
#
# Sits at the tail, immediately before --extra, because that is where it was
# measured (gs-s1 / gs-s2).
LEGWEAR_SHADING = "(soft shading:1.3), smooth shading"

# Healthy volume on the legs, asked for without naming a part.
#
# The obvious phrasings all work on the legs and then keep going: with
# (thick thighs:1.2), thighs the camera drops to the hips, the skirt rides up
# and the rear becomes the subject -- on both seeds, and worse with
# (wide hips:1.15). Putting the same words next to the garment instead of at
# the tail did not help. A body word plus "legs" gets the volume and leaves the
# framing alone; "thighs" and "hips" sit next to rear-focused compositions in
# the data and bring them along.
#
# Same tail slot as the shading, and gated on legwear for the same reason: that
# is the configuration it was measured in.
#
# "plump" was the first word here and it overshot: healthy thighs are wanted,
# chubby ones are not, and plump carries the second. Lowering it to 1.1 barely
# moved; adding "slim legs" alongside took the volume back off. Swapping the
# word for "toned" keeps the shape and drops the softness, without going
# muscular.
#
# "healthy body" is gone with it, and not by choice: the ablation dropped the
# old block with --drop and passed the new one through --extra, and --drop runs
# over the joined string, so it took "healthy body" out of the replacement too.
# The accepted renders therefore ran on (toned legs:1.2) alone, and that is what
# this says. Adding "healthy body" back is untested.
BODY_VOLUME = "(toned legs:1.2)"

# Three separate problems, all of which need the negative rather than the
# positive:
#   black   -- Hassaku renders (black thighhighs:1.3) as dark brown. Saying black
#              louder does not fix it; naming brown in the negative does.
#   fibre   -- a legwear tag left alone comes back knitted. These bans keep it a
#              flat shape carrying a highlight.
#   gloss   -- a gloss asked for without the last two terms turns to vinyl, which
#              is the crude version of what was wanted. latex/rubber are the
#              difference between a sheen and a shine.
# Named only when a face is asked for, and only on the minimal path. The face
# block demands large eyes and a large iris without ever saying what colour they
# are, and an instruction with no resolution gets resolved somewhere else on the
# canvas -- on the seeds that grew a backdrop eye, adding the colour here cleared
# it (3 of 4 for Takao) without touching the negative. It also fixes plain drift:
# Takao came out blue-eyed on one seed before this.
#
# Sits at the very tail, after --extra, because that is where it was measured.
EYES_BY_JOB = {
    "sage": "(blue eyes:1.2)",
    "takao": "(red eyes:1.2)",
    "yukari": "(purple eyes:1.2)",
    "momiji": "(red eyes:1.2)",
    "hamakaze": "(blue eyes:1.2)",
}

LEGWEAR_GUARD = (
    "(brown legwear:1.5), brown thighhighs, brown pantyhose, (grey legwear:1.3), "
    "(sheer legwear:1.3), see-through legwear, (fishnet:1.4), (ribbed legwear:1.3), "
    "knit, fabric texture, thread, (latex:1.45), (rubber:1.45), wet look, "
    # Scoped to the legs on purpose: a bare "leather" also takes the sage's belt.
    "(leather legwear:1.45), leather pants"
)
# Tried and rejected: (shiny skin:1.3), (shiny gloves:1.3), (shiny boots:1.3).
# Meant to keep the shine on the legs only, they flattened the legs too -- a
# negative "shiny X" pulls the whole shiny direction down, the positive with it.

# Framings where the face is too small to carry moe's weights. Verified on
# one seed both ways: full moe at standing collapses (duplicates, background
# eyes), moe-far at the same seed is clean and keeps the eye colour that
# face=default loses. A closer crop does not rescue full moe — the weights,
# not the face area, are the binding constraint outside seated framings.
# The cliff sits between 1.45 and 1.65: moe-mid held on the collapsing seed
# and on three random seeds, and keeps most of the look moe-far gives up.
FACE_BY_POSE: dict[str, str] = {"standing": "moe-mid"}

# A tag weight is only worth what the checkpoint makes of it, so the tuned
# numbers below belong to the checkpoint rather than to the recipe. The defaults
# throughout this file are Amanatsu's; anything listed here is substituted into
# the finished positive prompt when that checkpoint is selected.
#
# moe-vpred-v2 draws no white border and tints the backdrop at Amanatsu's
# weights, and it wants the halved face preset at every framing -- at full weight
# its eye and iris tags have no solution and the sampler returns coloured blocks.
CHECKPOINT_TUNING = {
    "moe-vpred-v2": {
        "face": "moe-far",
        "retune": {
            "(white outline:1.6)": "(white outline:2.4), (thick white outline:1.5)",
            "(simple background:1.4)": "(simple background:1.5)",
            "(grey background:1.35)": "(grey background:1.7)",
            "flat background": "(flat background:1.5)",
            "no scenery": "(no scenery:1.3)",
            "(outstretched arms:1.4)": "(outstretched arms:1.6)",
        },
    },
    # Hassaku draws the border and the eyes well at Amanatsu's weights, but it
    # loses the scarf under the cape, and it resolves the prompt's demand for
    # heavy shadow as a second figure -- a dark silhouette beside the sage, with
    # eyes drawn into it.
    #
    # Raising the anti-shadow and anti-monster negatives made that worse, the
    # same way naming a staff's parts produced a more ornate staff: at 1.7 the
    # disembodied eye grew instead of going away. The cause is on the positive
    # side, so that is where this cuts.
    "hassaku-il-v22": {
        "retune": {
            "teal scarf": "(teal scarf:1.35)",
            "(dark shadows:1.3), deep shadow tone": "dark shadows",
            # "black tinted shadows" was dropped here too, and on its own that
            # one removal washes the whole image out -- mean luminance 115 -> 220
            # at a stddev of 13, i.e. a nearly uniform white field. Bisected
            # against the graph recovered from a working run's PNG. Whatever it
            # anchors, Hassaku needs it.
        },
    },
}

FRANCHISE = {
    "sage": "dragon quest iii, dragon quest",
    "priest": "dragon quest iii, dragon quest",
    "mage": "dragon quest iii, dragon quest",
    "yukari": "vocaloid, voiceroid",
    "takao": "kantai collection",
    "momiji": "touhou",
    "hamakaze": "kantai collection",
}

# Individual terms a class has to remove from the assembled negative. Dropping a
# whole block was tried first and wrecked the render: the blocks carry more than
# their name suggests, and losing the rest of NEG_GEAR made the image melt.
NEG_DROP = {
    "yukari": ["(hood:1.4)", "headgear", "(headscarf:1.4)",
               "thighhighs", "skinny legs", "thin legs", "thin calves"],
    # Her uniform is military dress, not armour, but the two share
    # vocabulary. The beret needs headgear released, and the canon
    # thighhighs need the sage's legwear guards released, like Yukari's.
    "takao": ["armor", "warrior", "headgear", "thighhighs",
              "skinny legs", "thin legs", "thin calves"],
}

# Same idea for poses. bootoff puts the feet toward the camera on purpose, which
# the default framing negatives rule out; the upskirt terms stay in place.
# Class tags a pose has to give up. reaching wants both hands open and empty.
POSE_TAG_DROP = {"reaching": ["(quarterstaff:1.35)", "plain wooden pole", "holding pole"]}

POSE_NEG_DROP = {
    "bootoff": ["feet focus", "lower body"],
    "kneesup": ["feet focus", "lower body"],
}

# Appended to every pose. A scene gives the eye tags somewhere to put an extra
# eye -- a balcony backdrop grew a shadow creature with a fully drawn iris -- and
# a flat field leaves them nothing to latch onto.
# Weights are pitched for moe-vpred-v2, which needs more push than Amanatsu did
# before the backdrop goes properly flat.
BACKGROUND = (
    "(simple background:1.4), (grey background:1.35), plain background, "
    "flat background, no scenery"
)

POSES = {
    "standing": "standing, full body, looking at viewer",
    "sitting": (
        "sitting, knees up, one knee raised, from side, three quarter view, "
        "looking at viewer, full body"
    ),
    # Arms thrown out towards the camera, leaning in. The reference this came
    # from frames it from low enough to look up the skirt; the framing tags keep
    # the shot on the upper body instead.
    "reaching": (
        "(outstretched arms:1.4), reaching towards viewer, (leaning forward:1.25), "
        "open hands, spread fingers, looking at viewer, open mouth, smile, "
        "(upper body:1.2), (medium breasts:1.2), dutch angle"
    ),
    # Knees drawn up together with the feet toward the camera and a hand at the
    # legwear. Taken off ref-pose-kneesup.
    "kneesup": (
        "sitting, (knees up:1.4), knees together, legs together, legs raised, "
        "feet up, (soles:1.25), (foreshortening:1.3), perspective, (large feet:1.2), (adjusting legwear:1.3), hand on own leg, "
        "head tilt, looking at viewer, full body"
    ),
    # Sitting back with the knees up, one boot off and held. The reference this
    # came from shoots from low enough to put the crotch in frame; that half is
    # left out, and the framing negatives keep it out.
    "bootoff": (
        "sitting, leaning back, (knees up:1.3), legs raised, "
        "(holding boot:1.4), single boot removed, undressing, "
        "(soles:1.2), feet up, looking at viewer, "
        "(black pantyhose:1.35), full body"
    ),
    # Side-sitting with the torso turned away and the head looking back. The
    # balcony it came from is dropped along with every other backdrop.
    "lookback": (
        "(yokozuwari:1.35), sitting on floor, legs to the side, "
        "(looking back:1.4), looking at viewer, from behind, from side, "
        "full body, head tilt, (medium breasts:1.2)"
    ),
}

# Grouped so each block's purpose stays readable when tweaking one of them.
NEG_QUALITY = (
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text, "
    "(washed out:1.3), (overexposed:1.3), (pale skin:1.3)"
)
NEG_SHINE = "shiny skin, oily skin, sweat, (latex:1.3), (rubber:1.3)"
NEG_LEGS = (
    "bare legs, barefoot, thighhighs, thin legs, muscular legs, bony knees, "
    "(grey legwear:1.4), (sheer legwear:1.3), see-through legwear, pale legwear, "
    "obese, wide hips, huge ass, short legs"
)
NEG_GEAR = (
    "(sword:1.4), knife, axe, spear, shield, (horns:1.4), (helmet:1.4), "
    "armor, warrior, headgear, (hood:1.4), mitre"
)
NEG_DISTORT = ("(warped:1.3), melting, distorted, deformed, (bent staff:1.3), "
               "(thick staff:1.4), oversized staff, club, mace, "
               "(ornate staff:1.4), decorated staff")
NEG_FRAMING = (
    "cropped, head out of frame, close-up, lower body, feet focus, "
    "(upskirt:1.4), panties, (from below:1.2), (zoom layer:1.4), multiple views"
)
NEG_ARTIFACT = (
    "long robe, patterned legwear, spots, mottled, (torn clothes:1.2), "
    "(microskirt:1.4), exposed buttocks, (emblem:1.4), (logo:1.4), chest print, "
    "(wrinkled clothes:1.2), busy details"
)
NEG_TOON = (
    "(thick outlines:1.4), heavy lineart, (colored lineart:1.4), (light lineart:1.3), "
    "pale lineart, lineless, monochrome, sketch, (intricate:1.3), (highly detailed:1.3)"
)
NEG_SPARKLE = "(sparkle:1.25), (star (symbol):1.25), light particles, lens flare, glitter"
NEG_BLUSH = "blush, nose blush, embarrassed"
NEG_BREASTS = "(huge breasts:1.4), (large breasts:1.25), cleavage"
NEG_CROWD = (
    "(multiple girls:1.4), background character, crowd, (dark figure:1.3), "
    "(dark shape:1.3), stray object, (disembodied eye:1.4), (monster:1.4)"
)
NEG_EYECOLOR = (
    "(rainbow eyes:1.3), heterochromia, (tsurime:1.3), (small eyes:1.4), "
    "(sanpaku:1.5), (constricted pupils:1.4), (visible sclera:1.4)"
)
NEG_GREEN = ("(green hair:1.5), mint hair, (yellow-green:1.4), lime, (yellow background:1.4), "
             "(light blue hair:1.4), (purple hair:1.4), silver hair, white hair")
NEG_SHADOW = "(cast shadow:1.5), (shadow on ground:1.45), soft shadow, gradient shadow"
NEG_MISC = (
    "3d, cgi, render, photorealistic, loli, child, mature female, old, "
    "(gradient shading:1.4), airbrush, smooth shading, (many colors:1.3)"
)

# The two blocks the pastel style cannot live under. NEG_QUALITY ends on
# (washed out), (overexposed), (pale skin) and NEG_TOON bans coloured, light and
# pale lineart — between them that is the whole flat-colour look, banned by name.
# What is worth keeping from each is the part that guards against a heavy or
# absent line, so only the pale half is released.
NEG_QUALITY_PLAIN = (
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text"
)
NEG_TOON_HEAVY = (
    "(thick outlines:1.4), heavy lineart, lineless, monochrome, "
    "(intricate:1.3), (highly detailed:1.3)"
)

NEG_BLOCKS = {
    "quality": NEG_QUALITY, "shine": NEG_SHINE, "legs": NEG_LEGS, "gear": NEG_GEAR,
    "framing": NEG_FRAMING, "artifact": NEG_ARTIFACT, "toon": NEG_TOON,
    "distort": NEG_DISTORT,
    "sparkle": NEG_SPARKLE, "blush": NEG_BLUSH, "crowd": NEG_CROWD,
    "eyecolor": NEG_EYECOLOR, "green": NEG_GREEN,
    "shadow": NEG_SHADOW, "breasts": NEG_BREASTS,
    "misc": NEG_MISC,
    "quality-plain": NEG_QUALITY_PLAIN, "toon-heavy": NEG_TOON_HEAVY,
}
FULL_ORDER = ["quality", "shine", "legs", "gear", "distort", "framing", "artifact",
              "toon", "sparkle", "blush", "crowd", "eyecolor", "green",
              "shadow", "breasts", "misc"]
LIGHT_ORDER = [b for b in FULL_ORDER if b not in ("shine", "toon")]
# Same guards as full, with the two pale-hostile blocks swapped for their halves.
# The anti-gloss and anti-shadow blocks stay: the flat-colour look has no gloss
# and no cast shadow either, so they are pulling the same direction here.
PASTEL_ORDER = ["quality-plain" if b == "quality" else "toon-heavy" if b == "toon" else b
                for b in FULL_ORDER]
ORDERS = {"full": FULL_ORDER, "light": LIGHT_ORDER, "pastel": PASTEL_ORDER}


def build_negative(preset: str, job: str, pose: str = "") -> str:
    order = ORDERS.get(preset, FULL_ORDER)
    terms = [t.strip() for b in order for t in NEG_BLOCKS[b].split(",")]
    drop = set(NEG_DROP.get(job, [])) | set(POSE_NEG_DROP.get(pose, []))
    return ", ".join(t for t in terms if t and t not in drop)


DEFAULT_NEGATIVE = ", ".join(
    [NEG_QUALITY, NEG_SHINE, NEG_LEGS, NEG_GEAR, NEG_FRAMING, NEG_ARTIFACT,
     NEG_TOON, NEG_SPARKLE, NEG_BLUSH, NEG_CROWD, NEG_EYECOLOR, NEG_SHADOW, NEG_MISC]
)
# Drops NEG_SHINE and NEG_TOON: between them they suppress glossy skin, bloom
# and contrast, which is most of what makes a rendering read as game CG. Keeps
# the blocks that guard anatomy, the outfit and the framing.
LIGHT_NEGATIVE = ", ".join(
    [NEG_QUALITY, NEG_LEGS, NEG_GEAR, NEG_FRAMING, NEG_ARTIFACT, NEG_SPARKLE, NEG_BLUSH, NEG_CROWD, NEG_EYECOLOR, NEG_SHADOW, NEG_MISC]
)
PASTEL_NEGATIVE = ", ".join(
    [NEG_QUALITY_PLAIN, NEG_SHINE, NEG_LEGS, NEG_GEAR, NEG_FRAMING, NEG_ARTIFACT,
     NEG_TOON_HEAVY, NEG_SPARKLE, NEG_BLUSH, NEG_CROWD, NEG_EYECOLOR, NEG_SHADOW,
     NEG_MISC]
)
NEGATIVE_PRESETS = {
    "full": DEFAULT_NEGATIVE, "light": LIGHT_NEGATIVE, "pastel": PASTEL_NEGATIVE,
}

# The whole guard --minimal keeps, and only when a face was asked for: the face
# block is what puts eye pressure into a prompt that otherwise has none, and the
# accepted colouring (mn-h-grey) was rendered without one.
#
# One tag, because the other candidates were measured and missed. On the seed
# that grew a backdrop creature, dropping the franchise tags left it exactly as
# it was, and so did (monster:1.4) -- the model does not classify it as a
# monster. It is a cluster of disembodied eyes that happens to resolve as a
# Dragon Quest mascot, and only the tag that names that removes it. What takes
# its place is the staff's cast shadow: the empty area still gets filled, the
# filling is just benign now.
MINIMAL_FACE_GUARD = "(disembodied eye:1.4)"

# The minimal path carried no framing negatives at all, which was fine for the
# poses it was built on and not fine the moment a new one arrived: the chair
# pose put the camera under the skirt on its own. This is the smallest part of
# NEG_FRAMING that stops that -- the crowd-adjacent half of it (multiple views,
# zoom layer) is left out, since bundles of that shape have caused their own
# trouble here before.
#
# Consequence: renders accepted before this no longer reproduce from bare flags.
# The tags pin the commits they were made at.
MINIMAL_FRAMING_GUARD = "(upskirt:1.4), panties, (from below:1.35)"

# A scene replaces the flat field the minimal path otherwise draws. That field
# is not an option there -- build_minimal_positive writes
# "(flat color:1.3), (simple background:1.3), (<bg> background:1.2)" into every
# render -- so a room had to be reached by --drop'ing all three back out, which
# is a workaround rather than a setting. --scene substitutes instead.
#
# Each entry carries three things that have to arrive together: where she is,
# what is lighting her, and what the line does. Splitting them was tried and the
# room came out lit like a studio, because the light block is what makes a
# window at night read as a window at night.
#
# The line block belongs here for the same reason it belongs anywhere: Illustrious
# tints the outline to match the fill, and only asking for black ink brings the
# drawn line back. On a flat grey field that reads as a sticker and nothing needs
# it; in a room it is the difference between a drawing and a render.
SCENES = {
    "warm-room": (
        "(indoors:1.35), (bedroom:1.25), (window:1.2), (night:1.2), "
        "(city lights:1.2), (bokeh:1.3), (lamp:1.2), (depth of field:1.3), "
        "(blurry background:1.25), "
        "(warm lighting:1.4), (orange lighting:1.3), (soft lighting:1.35), "
        "(ambient light:1.25), (soft shading:1.35), (gradient shading:1.2), "
        "(backlighting:1.35), (rim light:1.3), (sunset:1.2), "
        "(thin lineart:1.45), (black lineart:1.4), (defined lines:1.2)"
    ),
}

# The anti-impasto bundle: negates the paint without touching the style.
# Found for galge (abc-I1), transfers to cel-plain (pt1/pt6). "mild" keeps
# a little gloss and depth — the level of the accepted sage renders; "full"
# flattens further and kills the legwear shine.
FLAT_PAINT = {
    "mild": (
        "(impasto:1.25), (painterly:1.25), (oil painting (medium):1.2), "
        "(heavy shading:1.2), (detailed shading:1.2), (realistic:1.1)"
    ),
    "full": (
        "(impasto:1.4), (painterly:1.4), (oil painting (medium):1.3), "
        "(heavy shading:1.3), (detailed shading:1.3), (realistic:1.2)"
    ),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Queue a Dragon Quest III class portrait through the local ComfyUI API."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8188)
    parser.add_argument("--job", choices=sorted(CLASSES), default="sage")
    parser.add_argument("--pose", choices=sorted(POSES), default="standing")
    # None rather than "moe" so that "the caller asked for this face" is
    # distinguishable from "nobody chose"; --minimal needs to tell them apart,
    # since a face is the one block it will accept being added back.
    parser.add_argument("--face", choices=sorted(FACES), default=None)
    parser.add_argument("--style", choices=sorted(STYLES), default="cel")
    parser.add_argument(
        "--scene",
        choices=sorted(SCENES),
        help="put her in a place instead of on a flat field. Minimal path only: "
        "it substitutes for the (flat color)/(simple background) block, which "
        "is not otherwise removable. --border is a cut-out device and does not "
        "belong with one",
    )
    parser.add_argument(
        "--plain-quality",
        action="store_true",
        help="drop the aesthetic-score tags that flatten faces toward one look",
    )
    parser.add_argument("--extra", default="", help="appended to the positive prompt")
    # A trace already states the pose, and POSES restates it in words the
    # skeleton may contradict. Pass "" to hand the pose entirely to the trace.
    parser.add_argument(
        "--pose-text",
        help="replace the POSES entry for --pose; empty string drops it",
    )
    # The legwear block is the one part of the prompt that is being tuned
    # against a stated spec (gloss, no fibre, black) rather than accepted from
    # the base, so it needs to be swappable without editing the table.
    parser.add_argument(
        "--legwear-text",
        help="replace the LEGWEAR_BY_JOB entry for --job; empty string drops it",
    )
    # --drop can take a tag out of the class block but cannot reword one, and
    # rewording is what an ownership problem needs: Yukari's ears belong to the
    # hood, and deleting the ear tag only leaves the demand unresolved.
    parser.add_argument(
        "--class-text",
        help="replace the CLASSES entry for --job",
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="six-token-style prompt: character, pose, flat field, nothing else",
    )
    parser.add_argument(
        "--border",
        action="store_true",
        help="draw the white sticker outline (--minimal only)",
    )
    parser.add_argument(
        "--bg-color",
        help="hue of the flat field, e.g. pink; replaces grey in place",
    )
    parser.add_argument("--negative")
    parser.add_argument(
        "--negative-preset", choices=sorted(NEGATIVE_PRESETS), default="full"
    )
    # The shadow negatives only work with a trace occupying the frame, so they
    # are appended per-run rather than added to the presets, which are also
    # used trace-less.
    parser.add_argument(
        "--negative-extra",
        action="append",
        default=[],
        help="appended to the negative prompt; repeatable",
    )
    parser.add_argument(
        "--flat-paint",
        choices=sorted(FLAT_PAINT),
        help="append the anti-impasto bundle; mild matches the accepted sage level",
    )
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--cfg", type=float, default=5.0)
    parser.add_argument("--sampler", default="dpmpp_2m")
    parser.add_argument("--scheduler", default="karras")
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--prefix")
    parser.add_argument("--ckpt-name", default="novaAnimeXL_ilV170.safetensors")
    # Many Civitai checkpoints are only mirrored in diffusers layout, which
    # CheckpointLoaderSimple cannot read. DiffusersLoader returns the same
    # MODEL/CLIP/VAE triple, so the rest of the graph is unchanged.
    # Default None rather than a base name, so "the caller chose Amanatsu" and
    # "the caller chose nothing" stay distinguishable; apply_defaults fills it.
    parser.add_argument(
        "--diffusers-path",
        default=None,
        help="subdirectory under assets/diffusers; pass '' to fall back to --ckpt-name",
    )
    # Structure, as opposed to IPAdapter's --ref-image, which carries style.
    parser.add_argument(
        "--trace-image",
        help="filename under input/ whose structure constrains the composition",
    )
    parser.add_argument(
        "--trace-mode",
        choices=sorted(TRACE_MODES),
        default="canny",
        help="what to extract from the reference; see TRACE_MODES",
    )
    parser.add_argument("--trace-strength", type=float, default=0.6)
    parser.add_argument("--trace-start", type=float, default=0.0)
    # Releasing it partway lets the trace set the structure and leaves the detail
    # to the prompt; held to the end it reproduces the reference outright.
    parser.add_argument("--trace-end", type=float, default=0.5)
    # canny only.
    parser.add_argument("--trace-low", type=float, default=0.2)
    parser.add_argument("--trace-high", type=float, default=0.6)
    # openpose only. Both detectors are off by default because each one pins a
    # feature the prompt is already tuned to produce: the hand keypoints hand the
    # sage a grip copied from whatever the reference was holding, and the face
    # keypoints override the face preset and CHECKPOINT_TUNING behind it.
    parser.add_argument("--trace-resolution", type=int, default=512)
    parser.add_argument("--trace-hands", action="store_true")
    parser.add_argument("--trace-face", action="store_true")
    # Without this the skeleton is invisible, and a pose that fails to transfer
    # looks identical to one the preprocessor never found.
    parser.add_argument(
        "--save-trace",
        action="store_true",
        help="also write the preprocessor's output as trace-<prefix>",
    )
    # DWPose finds nothing in this material. Its yolox person detector returns
    # zero boxes on every reference tried, under both its torchscript and its
    # onnx weights, so the skeleton comes out an empty black frame and the
    # ControlNet silently conditions on nothing. The older OpenPose estimator
    # does not go through yolox and does find bodies here.
    parser.add_argument(
        "--trace-backend", choices=["openpose", "dwpose"], default="openpose"
    )
    # The preprocessor emits IMAGE and POSE_KEYPOINT as separate outputs, and
    # the ControlNet reads the IMAGE. Editing the keypoints therefore changes
    # nothing on its own. Routing them back through RenderPeopleKps makes the
    # keypoints the thing that is actually drawn, so a hand-edited skeleton
    # reaches the sampler.
    parser.add_argument(
        "--trace-render-kps",
        action="store_true",
        help="draw the ControlNet hint from POSE_KEYPOINT so it can be edited",
    )
    # The skeleton's share of the frame is what sets the camera distance, so a
    # reference that fills its own frame renders as a close shot however loudly
    # the prompt says `full body`. Padding buys the distance back. It is not
    # free: the margin is also where the backdrop intruder gets drawn, and at
    # 0.35 one seed filled it with six spare eyes. 0.15 held on every seed
    # tried and still pulled the camera back.
    parser.add_argument("--trace-margin", type=float, default=0.15)
    # Optional second net over the same reference, applied after the first.
    # Meant for skeleton-first work: --trace-mode openpose carries the pose,
    # and a low-strength softedge here adds a whisper of costume and hair.
    parser.add_argument("--trace2-mode", choices=["softedge", "canny"])
    parser.add_argument("--trace2-strength", type=float, default=0.25)
    parser.add_argument("--trace2-start", type=float, default=0.0)
    parser.add_argument("--trace2-end", type=float, default=0.3)
    # The staff is the tag most likely to fight a borrowed pose: the reference's
    # hands are doing something else, and the prompt insists on a grip.
    parser.add_argument(
        "--drop",
        action="append",
        default=[],
        metavar="TAG",
        help="remove a tag from the class block; repeat for several",
    )
    parser.add_argument(
        "--controlnet-name",
        help="override the ControlNet that --trace-mode would select",
    )
    parser.add_argument(
        "--v-pred",
        action="store_true",
        help="checkpoint is v-prediction (NoobAI vpred and similar)",
    )
    # Repeatable: --lora a.safetensors --lora b.safetensors chains them.
    parser.add_argument(
        "--lora",
        action="append",
        default=[],
        metavar="NAME",
        help="LoRA filename under assets/loras; repeat to stack several",
    )
    parser.add_argument(
        "--lora-strength",
        action="append",
        type=float,
        default=[],
        help="strength for the matching --lora (default 0.8 each)",
    )
    parser.add_argument(
        "--ref-image",
        help="filename under .local/ComfyUI/input to steer the look through IPAdapter",
    )
    parser.add_argument("--ref-weight", type=float, default=1.0)
    # "style transfer" leaves composition alone; plain "linear" drags the
    # reference's subject and colours in with it.
    parser.add_argument("--ref-type", default="style transfer")
    parser.add_argument(
        "--ref-mask",
        help="greyscale image under input/ limiting where this reference applies",
    )
    # A second pass so one reference can steer the face while another steers the
    # legwear, instead of one reference repainting the whole outfit.
    parser.add_argument("--ref2-image")
    parser.add_argument("--ref2-mask")
    parser.add_argument("--ref2-weight", type=float, default=1.0)
    parser.add_argument("--ref2-type", default="style transfer")
    parser.add_argument("--ref2-start", type=float, default=0.0)
    parser.add_argument("--ref2-end", type=float, default=1.0)
    # "V only" is the strongest and the quickest to harden edges. The C penalty
    # variants trade some of the reference's influence for a softer result.
    parser.add_argument(
        "--ref-scaling",
        default="V only",
        choices=["V only", "K+V", "K+V w/ C penalty", "K+mean(V) w/ C penalty"],
    )
    # Sampling window. Releasing the reference partway (--ref-end 0.4) lets it
    # shape the rendering while the prompt's own colours reassert afterwards,
    # which is the way to apply it unmasked without the palette going warm.
    parser.add_argument("--ref-start", type=float, default=0.0)
    parser.add_argument("--ref-end", type=float, default=1.0)
    parser.add_argument("--ipadapter-file", default="ip-adapter-plus_sdxl_vit-h.safetensors")
    parser.add_argument(
        "--clip-vision-name", default="CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
    )
    parser.add_argument("--wait", action="store_true", help="poll until the images are written")
    parser.add_argument(
        "--export-workflow",
        help="write the first queued image's UI workflow here instead of the "
        "default path under .local/workflows",
    )
    parser.add_argument(
        "--no-export-workflow",
        action="store_true",
        help="skip the workflow export entirely",
    )
    return parser.parse_args(argv)


def repo_revision() -> str:
    """Stamp exports with the code that built them. --short=8 rather than git's
    default: plain --short grows when a prefix collides, so the name would not
    keep a stable length. A dirty tree is called out, because the hash on its
    own names a commit that never held these settings."""
    try:
        rev = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "nogit"
    return f"{rev}-dirty" if dirty else rev


def export_workflow_path(args: argparse.Namespace, prefix: str) -> str | None:
    if args.no_export_workflow:
        return None
    if args.export_workflow:
        return args.export_workflow
    # This exact directory, because it is the only one the GUI's workflow
    # browser reads -- anywhere else and the export exists but cannot be opened.
    # It also sits under the gitignored .local, so exporting on every run does
    # not dirty the working tree, which is what keeps the revision stamp honest.
    directory = REPO_ROOT / ".local" / "ComfyUI" / "user" / "default" / "workflows"
    directory.mkdir(parents=True, exist_ok=True)
    return str(directory / f"{prefix}-{repo_revision()}.json")


def parse_args_from(argv: list[str]) -> argparse.Namespace:
    """Same parser, for wrappers that forward a subset of flags."""
    return parse_args(argv)


# The comparison sheets this look is being judged against run on six tokens.
# Their simplicity is not a style, it is the absence of specification: every tag
# in the full recipe is one more thing the sampler is obliged to draw, so a style
# block can only ever subtract from a prompt built to add — and subtracting far
# enough stops it resolving at all (pa6 came back as noise). This path starts
# from nothing instead. No face preset, no legs block, no style block, no LoRA,
# and the short negative.
def build_minimal_positive(args: argparse.Namespace) -> str:
    class_text = getattr(args, "class_text", None)
    if class_text is None:
        class_text = CLASSES[args.job]
    parts = [QUALITY_PLAIN, "1girl, solo", class_text]
    franchise = FRANCHISE.get(args.job)
    if franchise:
        parts.append(franchise)
    pose_text = getattr(args, "pose_text", None)
    if pose_text is None:
        pose_text = POSES[args.pose]
    if pose_text:
        parts.append(pose_text)
    legwear = getattr(args, "legwear_text", None)
    if legwear is None:
        legwear = LEGWEAR_BY_JOB.get(args.job)
    if legwear:
        parts.append(legwear)
    # The one block that comes back on request. Everything else about the look
    # is the base's to decide here, but the face and the eyes are the part that
    # is being chosen rather than accepted, so --face is honoured. Without it
    # the base draws its own face, which is what the accepted render did.
    if getattr(args, "face_given", False):
        face = FACES[args.face]
        if face:
            parts.append(face)
    scene = getattr(args, "scene", None)
    if scene:
        # Substituted, not appended. Leaving the flat-colour field in place and
        # adding a room on top gives a room drawn in flat colour, which is the
        # one combination neither half wants.
        parts.append(SCENES[scene])
    else:
        bg = getattr(args, "bg_color", None) or "grey"
        parts.append(f"(flat color:1.3), (simple background:1.3), ({bg} background:1.2)")
    # The sticker border, at the weight the full recipe uses. Opt-in: the
    # accepted minimal renders were drawn without it, and it is a compositional
    # choice rather than part of the look.
    if getattr(args, "border", False):
        parts.append("(white outline:1.6), outline, sticker")
    if legwear:
        parts.append(LEGWEAR_SHADING)
        parts.append(BODY_VOLUME)
    if args.extra:
        parts.append(args.extra)
    if getattr(args, "face_given", False):
        eyes = EYES_BY_JOB.get(args.job)
        if eyes:
            parts.append(eyes)
    positive = ", ".join(parts)
    # This path used to return before build_positive's drop loop, so --drop was
    # accepted and silently did nothing here -- which is worse than rejecting it,
    # because an ablation run with --drop looked like it had been performed.
    for tag in list(getattr(args, "drop", []) or []):
        positive = positive.replace(tag + ", ", "").replace(", " + tag, "")
    return positive


def build_positive(args: argparse.Namespace) -> str:
    if getattr(args, "minimal", False):
        return build_minimal_positive(args)
    quality = QUALITY_PLAIN if getattr(args, "plain_quality", False) else QUALITY
    class_tags = CLASSES[args.job]
    for tag in POSE_TAG_DROP.get(args.pose, []):
        class_tags = class_tags.replace(tag + ", ", "").replace(", " + tag, "")
    parts = [quality, "1girl, solo", class_tags]
    franchise = FRANCHISE.get(args.job)
    if franchise:
        parts.append(franchise)
    pose_text = getattr(args, "pose_text", None)
    if pose_text is None:
        pose_text = POSES[args.pose]
    parts += [LEGS_BY_JOB.get(args.job, LEGS)]
    if pose_text:
        parts.append(pose_text)
    background = BACKGROUND
    bg_color = getattr(args, "bg_color", None)
    if bg_color:
        # Substituted in place rather than dropped-and-appended. The grey tag is
        # load-bearing twice over: it carries the flat-field weight that keeps a
        # second figure out of the frame, and its position in the block matters
        # as much as its weight (see the flesh-tag ordering finding). Removing it
        # and adding a colour at the tail duplicated the figure on both hassaku
        # runs; swapping the word keeps the anchor and only changes the hue.
        background = background.replace("grey background", f"{bg_color} background")
    parts.append(background)
    face = FACES[getattr(args, "face", "default")]
    if face:
        parts.append(face)
    style = STYLES[getattr(args, "style", "default")]
    if style:
        parts.append(style)
    if args.extra:
        parts.append(args.extra)
    positive = ", ".join(parts)
    # User drops act on the whole assembled prompt, so style and face tags can
    # be removed as well as class tags.
    for tag in list(getattr(args, "drop", []) or []):
        positive = positive.replace(tag + ", ", "").replace(", " + tag, "")
    tuning = CHECKPOINT_TUNING.get(getattr(args, "diffusers_path", None) or "", {})
    for old, new in tuning.get("retune", {}).items():
        # A retune keyed on the grey tag has to follow --bg-color's substitution,
        # since it is the weight that is being retuned, not the colour.
        if bg_color:
            old = old.replace("grey background", f"{bg_color} background")
            new = new.replace("grey background", f"{bg_color} background")
        positive = positive.replace(old, new)
    return positive


def build_prompt(args: argparse.Namespace, seed: int, prefix: str) -> dict[str, dict]:
    diffusers_path = getattr(args, "diffusers_path", None)
    loader = (
        {"class_type": "DiffusersLoader", "inputs": {"model_path": diffusers_path}}
        if diffusers_path
        else {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": args.ckpt_name}}
    )

    # LoRAs sit between the loader and everything downstream, so the rest of the
    # graph keeps pointing at one node id whether or not any are stacked.
    model_src, clip_src = ["4", 0], ["4", 1]

    # v-prediction checkpoints need saying so. DiffusersLoader does not read the
    # scheduler config, so without this the image comes out as noise or a flat
    # field -- which is at least an unmistakable failure.
    sampling_nodes: dict[str, dict] = {}
    if getattr(args, "v_pred", False):
        sampling_nodes["59"] = {
            "class_type": "ModelSamplingDiscrete",
            "inputs": {"model": model_src, "sampling": "v_prediction", "zsnr": True},
        }
        model_src = ["59", 0]

    lora_nodes: dict[str, dict] = {}
    for index, lora_name in enumerate(getattr(args, "lora", []) or []):
        strengths = getattr(args, "lora_strength", []) or []
        strength = strengths[index] if index < len(strengths) else 0.8
        node = str(60 + index)
        lora_nodes[node] = {
            "class_type": "LoraLoader",
            "inputs": {
                "model": model_src,
                "clip": clip_src,
                "lora_name": lora_name,
                "strength_model": strength,
                "strength_clip": strength,
            },
        }
        model_src, clip_src = [node, 0], [node, 1]

    positive_src, negative_src = ["6", 0], ["7", 0]
    trace_nodes: dict[str, dict] = {}
    trace_image = getattr(args, "trace_image", None)
    if trace_image:
        trace_nodes["70"] = {"class_type": "LoadImage", "inputs": {"image": trace_image}}
        # The skeleton is stretched to the canvas, not letterboxed, so a
        # reference of a different shape squashes the proportions it carries.
        # Centre-cropping to the render's aspect ratio here means a reference
        # can be dropped in at whatever size it happens to be.
        #
        # The margin is added to the *trace*, not the reference. Padding the
        # reference put a hard grey edge in front of the detector, HED kept
        # all four lines, and the sampler rendered them as a picture frame.
        # A preprocessor's output is white-on-black, so compositing it onto a
        # black canvas adds the same margin without creating any edge.
        pad_w = int(args.width * args.trace_margin / 2) // 8 * 8
        pad_h = int(args.height * args.trace_margin / 2) // 8 * 8
        inner_w, inner_h = args.width - 2 * pad_w, args.height - 2 * pad_h
        trace_nodes["74"] = {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["70", 0],
                "upscale_method": "lanczos",
                "width": inner_w,
                "height": inner_h,
                "crop": "center",
            },
        }
        if args.trace_mode == "openpose":
            pose_inputs = {
                "image": ["74", 0],
                "detect_body": "enable",
                "detect_hand": "enable" if args.trace_hands else "disable",
                "detect_face": "enable" if args.trace_face else "disable",
                "resolution": args.trace_resolution,
            }
            if args.trace_backend == "dwpose":
                pose_inputs |= {
                    "bbox_detector": "yolox_l.onnx",
                    "pose_estimator": "dw-ll_ucoco_384.onnx",
                }
            trace_nodes["71"] = {
                "class_type": (
                    "DWPreprocessor"
                    if args.trace_backend == "dwpose"
                    else "OpenposePreprocessor"
                ),
                "inputs": pose_inputs,
            }
        elif args.trace_mode == "softedge":
            trace_nodes["71"] = {
                "class_type": "HEDPreprocessor",
                "inputs": {
                    "image": ["74", 0],
                    "safe": "enable",
                    "resolution": args.trace_resolution,
                },
            }
        else:
            trace_nodes["71"] = {
                "class_type": "Canny",
                "inputs": {
                    "image": ["74", 0],
                    "low_threshold": args.trace_low,
                    "high_threshold": args.trace_high,
                },
            }
        hint_src = ["71", 0]
        if args.trace_render_kps and args.trace_mode == "openpose":
            trace_nodes["76"] = {
                "class_type": "RenderPeopleKps",
                "inputs": {
                    "kps": ["71", 1],
                    "render_body": True,
                    "render_hand": bool(args.trace_hands),
                    "render_face": bool(args.trace_face),
                },
            }
            hint_src = ["76", 0]
        if pad_w or pad_h:
            trace_nodes["77"] = {
                "class_type": "EmptyImage",
                "inputs": {
                    "width": args.width,
                    "height": args.height,
                    "batch_size": 1,
                    "color": 0,
                },
            }
            trace_nodes["78"] = {
                "class_type": "ImageScale",
                "inputs": {
                    "image": hint_src,
                    "upscale_method": "lanczos",
                    "width": inner_w,
                    "height": inner_h,
                    "crop": "disabled",
                },
            }
            trace_nodes["79"] = {
                "class_type": "ImageCompositeMasked",
                "inputs": {
                    "destination": ["77", 0],
                    "source": ["78", 0],
                    "x": pad_w,
                    "y": pad_h,
                    "resize_source": False,
                },
            }
            hint_src = ["79", 0]
        if args.save_trace:
            trace_nodes["75"] = {
                "class_type": "SaveImage",
                "inputs": {"images": hint_src, "filename_prefix": f"trace-{prefix}"},
            }
        trace_nodes["72"] = {
            "class_type": "ControlNetLoader",
            "inputs": {
                "control_net_name": args.controlnet_name
                or TRACE_MODES[args.trace_mode]
            },
        }
        trace_nodes["73"] = {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["6", 0],
                "negative": ["7", 0],
                "control_net": ["72", 0],
                "image": hint_src,
                "strength": args.trace_strength,
                "start_percent": args.trace_start,
                "end_percent": args.trace_end,
            },
        }
        positive_src, negative_src = ["73", 0], ["73", 1]

        # A second, weaker net over the same reference: the skeleton owns the
        # pose, and a faint outline pass whispers costume and hair without the
        # silhouette takeover a full-strength softedge causes.
        if args.trace2_mode:
            if args.trace2_mode == "softedge":
                trace_nodes["81"] = {
                    "class_type": "HEDPreprocessor",
                    "inputs": {
                        "image": ["74", 0],
                        "safe": "enable",
                        "resolution": args.trace_resolution,
                    },
                }
            else:
                trace_nodes["81"] = {
                    "class_type": "Canny",
                    "inputs": {
                        "image": ["74", 0],
                        "low_threshold": args.trace_low,
                        "high_threshold": args.trace_high,
                    },
                }
            hint2_src = ["81", 0]
            if pad_w or pad_h:
                trace_nodes["84"] = {
                    "class_type": "ImageScale",
                    "inputs": {
                        "image": hint2_src,
                        "upscale_method": "lanczos",
                        "width": inner_w,
                        "height": inner_h,
                        "crop": "disabled",
                    },
                }
                trace_nodes["85"] = {
                    "class_type": "ImageCompositeMasked",
                    "inputs": {
                        "destination": ["77", 0],
                        "source": ["84", 0],
                        "x": pad_w,
                        "y": pad_h,
                        "resize_source": False,
                    },
                }
                hint2_src = ["85", 0]
            trace_nodes["82"] = {
                "class_type": "ControlNetLoader",
                "inputs": {"control_net_name": TRACE_MODES[args.trace2_mode]},
            }
            trace_nodes["83"] = {
                "class_type": "ControlNetApplyAdvanced",
                "inputs": {
                    "positive": ["73", 0],
                    "negative": ["73", 1],
                    "control_net": ["82", 0],
                    "image": hint2_src,
                    "strength": args.trace2_strength,
                    "start_percent": args.trace2_start,
                    "end_percent": args.trace2_end,
                },
            }
            positive_src, negative_src = ["83", 0], ["83", 1]

    prompt = {
        "4": loader,
        **trace_nodes,
        **sampling_nodes,
        **lora_nodes,
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": clip_src, "text": build_positive(args)},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": clip_src, "text": args.negative},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"batch_size": 1, "width": args.width, "height": args.height},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "model": model_src,
                "positive": positive_src,
                "negative": negative_src,
                "latent_image": ["5", 0],
                "seed": seed,
                "steps": args.steps,
                "cfg": args.cfg,
                "sampler_name": args.sampler,
                "scheduler": args.scheduler,
                "denoise": 1,
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"images": ["8", 0], "filename_prefix": prefix},
        },
    }

    g = lambda name, default=None: getattr(args, name, default)
    passes = [
        {
            "image": g(f"{p}image"),
            "mask": g(f"{p}mask"),
            "weight": g(f"{p}weight", 1.0),
            "weight_type": g(f"{p}type", "style transfer"),
            "start_at": g(f"{p}start", 0.0),
            "end_at": g(f"{p}end", 1.0),
        }
        for p in ("ref_", "ref2_")
    ]
    passes = [p for p in passes if p["image"]]

    if passes:
        prompt["31"] = {
            "class_type": "IPAdapterModelLoader",
            "inputs": {"ipadapter_file": args.ipadapter_file},
        }
        prompt["32"] = {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": args.clip_vision_name},
        }

        # Passes chain model-to-model, so each one narrows what the next sees.
        model_ref = model_src
        node_id = 40
        for spec in passes:
            image_id, node_id = str(node_id), node_id + 1
            prompt[image_id] = {
                "class_type": "LoadImage",
                "inputs": {"image": spec["image"]},
            }

            inputs = {
                "model": model_ref,
                "ipadapter": ["31", 0],
                "image": [image_id, 0],
                "clip_vision": ["32", 0],
                "weight": spec["weight"],
                "weight_type": spec["weight_type"],
                "combine_embeds": "concat",
                "start_at": spec["start_at"],
                "end_at": spec["end_at"],
                "embeds_scaling": g("ref_scaling", "V only"),
            }

            mask = spec["mask"]
            if mask:
                mask_image_id, node_id = str(node_id), node_id + 1
                mask_id, node_id = str(node_id), node_id + 1
                prompt[mask_image_id] = {
                    "class_type": "LoadImage",
                    "inputs": {"image": mask},
                }
                prompt[mask_id] = {
                    "class_type": "ImageToMask",
                    "inputs": {"image": [mask_image_id, 0], "channel": "red"},
                }
                inputs["attn_mask"] = [mask_id, 0]

            ipadapter_id, node_id = str(node_id), node_id + 1
            prompt[ipadapter_id] = {"class_type": "IPAdapterAdvanced", "inputs": inputs}
            model_ref = [ipadapter_id, 0]

        prompt["3"]["inputs"]["model"] = model_ref

    return prompt


# /object_info is fetched once per process (it does not change while ComfyUI
# is running) and cached here rather than threaded through every call --
# --count can queue many images and each one would otherwise refetch it.
_OBJECT_INFO_FETCHED = False
_OBJECT_INFO: dict | None = None


def get_object_info(args: argparse.Namespace) -> dict | None:
    global _OBJECT_INFO_FETCHED, _OBJECT_INFO
    if not _OBJECT_INFO_FETCHED:
        _OBJECT_INFO_FETCHED = True
        try:
            _OBJECT_INFO = workflow_ui.fetch_object_info(args.host, args.port)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            print(f"warning: could not fetch /object_info, queuing without a UI workflow: {exc}", file=sys.stderr)
            _OBJECT_INFO = None
    return _OBJECT_INFO


def build_ui_workflow(args: argparse.Namespace, prompt: dict[str, dict]) -> dict | None:
    """Build the same graph queue_prompt is about to submit, so the two can
    never disagree. Returns None (rather than raising) on any failure --
    queuing the image is the primary job, the workflow is a convenience."""
    object_info = get_object_info(args)
    if object_info is None:
        return None
    try:
        return workflow_ui.api_to_ui(prompt, object_info)
    except Exception as exc:
        print(f"warning: could not build UI workflow: {exc}", file=sys.stderr)
        return None


def queue_prompt(args: argparse.Namespace, prompt: dict[str, dict]) -> dict:
    payload = {"prompt": prompt}
    ui_workflow = build_ui_workflow(args, prompt)
    if ui_workflow is not None:
        payload["extra_data"] = {"extra_pnginfo": {"workflow": ui_workflow}}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"http://{args.host}:{args.port}/prompt",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def wait_for(args: argparse.Namespace, prompt_ids: list[str]) -> None:
    pending = list(prompt_ids)
    while pending:
        time.sleep(10)
        for pid in list(pending):
            url = f"http://{args.host}:{args.port}/history/{pid}"
            with urllib.request.urlopen(url) as response:
                history = json.loads(response.read())
            if not history:
                continue
            pending.remove(pid)
            for entry in history.values():
                for output in entry.get("outputs", {}).values():
                    for image in output.get("images", []):
                        print(f"done {pid} -> {image['filename']}")


def apply_defaults(args: argparse.Namespace) -> None:
    """Fill in the settled recipe for anything the caller left alone."""
    # A job with a settled base claims it only when the caller did not choose one.
    #
    # This used to test `args.diffusers_path == "amanatsu-il-v11"`, taking the
    # parser default as proof that nobody had asked. That makes
    # `--diffusers-path amanatsu-il-v11` indistinguishable from passing nothing,
    # so an explicit request for Amanatsu was silently answered with the job's
    # base -- which is exactly the case a base comparison needs, and it would have
    # returned Hassaku labelled as Amanatsu with nothing to notice.
    args.base_given = args.diffusers_path is not None
    if not args.base_given:
        args.diffusers_path = BASE_BY_JOB.get(args.job, "amanatsu-il-v11")
    if getattr(args, "diffusers_path", None) in V_PRED_MODELS:
        args.v_pred = True
    tuning = CHECKPOINT_TUNING.get(getattr(args, "diffusers_path", None) or "", {})
    args.face_given = args.face is not None
    if args.face is None:
        if args.job in FACE_BY_JOB:
            args.face = FACE_BY_JOB[args.job]
        elif args.pose in FACE_BY_POSE:
            args.face = FACE_BY_POSE[args.pose]
        elif "face" in tuning:
            args.face = tuning["face"]
        else:
            args.face = "moe"
    minimal = getattr(args, "minimal", False)
    # The default LoRAs bring "detailed" with them, and the job extra is a flesh
    # dose -- both are additions, which is the one thing --minimal is refusing.
    if not args.lora and not minimal:
        args.lora = [name for name, _, _ in DEFAULT_LORAS]
        args.lora_strength = [strength for _, strength, _ in DEFAULT_LORAS]
        triggers = ", ".join(t for _, _, t in DEFAULT_LORAS if t)
        args.extra = ", ".join(p for p in (triggers, args.extra) if p)
    job_extra = EXTRA_BY_JOB.get(args.job)
    if job_extra and not minimal:
        args.extra = ", ".join(p for p in (args.extra, job_extra) if p)
    # --drop was accepted and silently did nothing on this path once, and an
    # ablation that looked performed and was not cost several rounds. --scene
    # only exists in build_minimal_positive, so say so rather than no-op.
    if getattr(args, "scene", None) and not minimal:
        raise SystemExit("--scene applies to --minimal only")
    if args.negative is None and minimal:
        args.negative = NEG_QUALITY_PLAIN
        if args.face_given:
            args.negative = f"{args.negative}, {MINIMAL_FACE_GUARD}"
        if args.job in LEGWEAR_BY_JOB:
            args.negative = f"{args.negative}, {LEGWEAR_GUARD}"
        args.negative = f"{args.negative}, {MINIMAL_FRAMING_GUARD}"
    elif args.negative is None:
        negative = build_negative(args.negative_preset, args.job, args.pose)
        for old, new in tuning.get("neg_retune", {}).items():
            negative = negative.replace(old, new)
        args.negative = negative
    if args.flat_paint:
        args.negative_extra = list(args.negative_extra) + [FLAT_PAINT[args.flat_paint]]
    for extra in args.negative_extra:
        args.negative = f"{args.negative}, {extra}"


def main() -> int:
    args = parse_args()
    apply_defaults(args)
    prefix = args.prefix or f"dq3-{args.job}-{args.pose}"
    prompt_ids = []

    for index in range(args.count):
        seed = args.seed if args.seed >= 0 else random.randint(0, 2**32 - 1)
        if args.seed >= 0 and args.count > 1:
            seed += index
        prompt = build_prompt(args, seed, prefix)
        export_path = export_workflow_path(args, prefix) if index == 0 else None
        if export_path:
            # Reuses the object_info cache queue_prompt is about to populate,
            # so this costs a conversion, not a second network round trip.
            ui_workflow = build_ui_workflow(args, prompt)
            if ui_workflow is None:
                raise SystemExit("--export-workflow requires /object_info; ComfyUI must be reachable")
            with open(export_path, "w") as f:
                json.dump(ui_workflow, f, indent=2)
            print(json.dumps({"workflow": export_path}))
        try:
            response = queue_prompt(args, prompt)
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"ComfyUI rejected the prompt: {exc.read().decode()}") from exc
        except urllib.error.URLError as exc:
            raise SystemExit(
                f"failed to reach ComfyUI at http://{args.host}:{args.port}: {exc}"
            ) from exc
        prompt_ids.append(response["prompt_id"])
        print(json.dumps({"seed": seed, **response}, ensure_ascii=True))

    if args.wait:
        wait_for(args, prompt_ids)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
