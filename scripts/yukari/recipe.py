"""The interpreter: pose records + style blocks -> the settled prompts and graph.

This file owns the ORDER and nothing else. Token order changes the encoding
-- a mid-prompt insertion re-rolls every token after it, and this recipe has
caught a one-line drift by checking it -- so the sequence in which blocks are
joined and edits are applied is fixed here, in the open, and the data lives
in `poses.py` / `costumes.py` / `prompt_style.py`. A new pose should need a
record and no changes to this file.
"""

from __future__ import annotations

from .costumes import COSTUME_NEGATIVE_EDITS, COSTUMES, SHOD
from .model import S_MIDRIFF, Edit
from .poses import POSE_RECORDS, POSES
from .prompt_style import (
    BODY,
    FACE,
    HIRES_DENOISE,
    NEGATIVE,
    RESTING_EYES,
    SHADE_BAN,
    SURFACE,
    THIN,
)
from .costumes import LEGWEAR_BAN

# Fixed list rather than random: a sweep that cannot be repeated cannot be
# used to show that a later change did or did not break something.
SWEEP_SEEDS = [555666777, 111222333, 1886970040, 737373737, 2557902837,
               3409564303]


def _splice(text: str, old: str, new: str, when: bool = True) -> str:
    """`str.replace`, except that a needle which is not there is an error.

    A replacement that matches nothing does nothing AND SAYS NOTHING; this
    recipe has paid for that failure twice, so the quiet version is gone.
    `when=False` skips the splice outright, which is the honest way to say
    "this costume has no such garment" -- as against letting the replacement
    run and match nothing, which looks identical in the output and means the
    opposite.
    """
    if not when:
        return text
    assert old in text, f"splice needle absent: {old!r}"
    return text.replace(old, new)


def _gate_open(edit: Edit, costume: str) -> bool:
    if edit.gate is None:
        return True
    if edit.gate == "dressed":
        return costume == "default"
    if edit.gate == "shod":
        return costume in SHOD
    if edit.gate == "default_or_roomwear":
        return costume in ("default", "roomwear")
    raise ValueError(f"unknown gate: {edit.gate!r}")


def _apply(text: str, edits: tuple[Edit, ...], costume: str) -> str:
    for e in edits:
        if not _gate_open(e, costume):
            continue
        if e.op == "replace":
            text = _splice(text, e.old, e.new)
        elif e.op == "remove":
            text = _splice(text, e.old, "")
        elif e.op == "prepend":
            text = e.new + text
        elif e.op == "append":
            text = text + e.new
        elif e.op == "replace_if_present":
            # The one deliberately quiet op: used where the needle's absence
            # is a legitimate state another edit created on purpose (see the
            # fitness midriff rewrite vs `swelter`'s release).
            text = text.replace(e.old, e.new)
        else:
            raise ValueError(f"unknown op: {e.op!r}")
    return text


def pose_block(pose: str, costume: str = "default") -> str:
    """The pose's own tags, after the costume has had its say about them.

    `build()` goes through here too: the second pass is spliced in by
    matching the pose block inside the finished prompt, so both callers have
    to be looking at the same text or that splice matches nothing.
    """
    return _apply(POSES[pose], POSE_RECORDS[pose].pose_block_edits, costume)


def positive(pose: str, costume: str = "default") -> str:
    rec = POSE_RECORDS[pose]
    blocks = COSTUMES[costume]
    # The legwear, body and thin-line blocks belong to whole-figure framings;
    # the portrait crops above them and naming what is out of frame is what
    # invites it back in.
    full_figure = rec.framing != "head"
    face = FACE.replace("closed mouth, ", "") if rec.open_mouth else FACE
    if rec.own_eyes:
        face = face.replace(RESTING_EYES, "")
    face = _apply(face, rec.face_edits, costume)
    body = _apply(BODY, rec.body_edits, costume)
    character = blocks["character"]
    if not full_figure:
        # The shoes are not in the blocks the crop drops -- a shod costume
        # carries them in CHARACTER -- and c08034a0 drew a sneaker floating
        # in the backdrop beside her head to prove it. Removed, not
        # substituted: there is no foot in frame to name anything onto.
        character = _splice(
            character,
            ", (white footwear:1.4), (sneakers:1.45), (high tops:1.3)", "",
            costume in SHOD)
    character = _apply(character, rec.character_edits, costume)
    legwear = _apply(blocks["legwear"], rec.legwear_edits, costume)
    surface = _apply(SURFACE, rec.surface_edits, costume)
    parts = ["best quality, absurdres, 1girl, solo", character,
             pose_block(pose, costume)]
    if full_figure:
        parts.append(legwear)
    parts += [face, surface]
    parts.append(body if full_figure else "(pale skin:1.25)")
    parts.append(blocks["hood"] + rec.hood_suffix)
    if full_figure and not rec.paint_finish:
        # `paint_finish` drops THIN, and it is a PALETTE decision rather than
        # a line one: measured on `portrait`, THIN alone took the figure from
        # 150 distinct flats to 190, the pass-2 paint guard alone to 168, and
        # the two together to 225 -- superadditive, and neither half predicts
        # it. A finish pose carries the guard (its `hires_negative`), so it
        # cannot also carry THIN without rebuilding the arm that drew
        # 「色がおかしい」.
        parts.append(THIN)
    return _apply(", ".join(parts), rec.tail_edits, costume)


def negative(pose: str, costume: str = "default") -> str:
    """The negative: base edits, then the staged sequence, ban in the middle.

    Pose edits and costume edits are merged and applied in stage order (the
    order the picked renders were drawn in -- see `model.py`). Head framings
    stop before the legwear ban: a guard against a garment that is out of
    frame is tokens spent on nothing.
    """
    rec = POSE_RECORDS[pose]
    text = _apply(NEGATIVE, rec.negative_base, costume)
    edits = sorted(rec.negative_edits + COSTUME_NEGATIVE_EDITS[costume],
                   key=lambda e: e.stage)
    text = _apply(text, tuple(e for e in edits if e.stage <= S_MIDRIFF),
                  costume)
    if rec.framing == "head":
        return text
    text = text + ", " + LEGWEAR_BAN
    return _apply(text, tuple(e for e in edits if e.stage > S_MIDRIFF),
                  costume)


def build(pose: str, seed: int, prefix: str, hires: int = 0,
          denoise: float | None = None, costume: str = "default") -> dict:
    """The settled graph. `hires` adds a second pass at that square size.

    The canvas of the first pass never changes, because that is the pass that
    decides the composition -- including how many people are in it. Raising the
    canvas itself is what drew a second figure at 1280x1920, and no card fixes
    that: it is the model leaving the sizes it was trained on. Upscaling the
    latent afterwards and redrawing it keeps that decision and buys the pixels
    anyway.
    """
    rec = POSE_RECORDS[pose]
    width, height = rec.size
    graph = {
        "4": {"class_type": "DiffusersLoader",
              "inputs": {"model_path": "hassaku-il-v22"}},
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"batch_size": 1, "width": width, "height": height}},
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["4", 1], "text": positive(pose, costume)}},
        "7": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["4", 1], "text": negative(pose, costume)}},
        "3": {"class_type": "KSampler", "inputs": {
            "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["5", 0], "seed": seed, "steps": 30, "cfg": 5.0,
            # dpmpp_2m, reset to b1258b0c. euler_ancestral took clean renders from
            # 4-of-7 to 7-of-7 and is the better sampler for clutter -- but it
            # re-injects noise each step, so every seed draws something else and
            # the picked render cannot be reproduced under it. Switch back if
            # clutter matters more than this particular image.
            "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode",
              "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0],
                         "filename_prefix": f"{prefix}-{pose}-{seed}"}},
    }

    if hires:
        longest = max(width, height)
        # bicubic, not bislerp. A latent pixel is an 8x8 patch of picture, so
        # how it is resampled decides what the edges look like -- and bislerp
        # steps them. At 1.5x that hid inside the linework; at 2x the diagonals
        # came back visibly stairstepped. Same size, same denoise, bicubic
        # instead, and they are smooth. Scaling in image space through a VAE
        # round trip fixes it too, and is not needed: the resampler was the
        # whole problem, not the fact that it ran on a latent.
        graph["10"] = {"class_type": "LatentUpscale", "inputs": {
            "samples": ["3", 0], "upscale_method": "bicubic",
            "width": round(hires * width / longest / 8) * 8,
            "height": round(hires * height / longest / 8) * 8,
            "crop": "disabled"}}
        graph["11"] = {"class_type": "KSampler", "inputs": {
            "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["10", 0], "seed": seed, "steps": 30, "cfg": 5.0,
            "sampler_name": "dpmpp_2m", "scheduler": "karras",
            "denoise": (rec.hires_print[1] if denoise is None
                                              and rec.hires_print
                        else HIRES_DENOISE if denoise is None else denoise)}}
        if rec.hires_finish:
            assert not rec.hires_positive, "one pass-2 positive, not two"
            text = positive(pose, costume)
            # Asserted rather than replaced blind: a `.replace` against a string
            # the prompt no longer contains does nothing and says nothing, which
            # is a mistake this file has paid for before.
            assert text.count(", " + THIN) == 1, pose
            text = text.replace(", " + THIN, "") + rec.hires_finish
            graph["6b"] = {"class_type": "CLIPTextEncode",
                           "inputs": {"clip": ["4", 1], "text": text}}
            graph["11"]["inputs"]["positive"] = ["6b", 0]
        if rec.hires_positive:
            # The mechanism the kick expression rounds proved out, kept even
            # while no pose uses it: a pass-2 positive reaches anything a late
            # pass can DRAW (an expression, at 0.60), and does not reach
            # anything pass 1 has already DECIDED (a leg's pose, a toe count).
            # `pose_block`, not `POSES[pose]`: a costume may have edited the
            # pose's tags, and this splice finds the pose block inside the
            # finished prompt by matching it.
            block = pose_block(pose, costume)
            text = positive(pose, costume).replace(
                block, block + ", " + rec.hires_positive)
            # A pass cannot say `closed mouth` and `(open mouth:1.35)` at
            # once, and FACE says the first for every pose without
            # `open_mouth` -- which applies to BOTH passes, not what a
            # pass-2-only expression wants. Resolved where the contradiction
            # arises. Asserted, per the `.replace` rule above.
            if "open mouth" in rec.hires_positive:
                assert "closed mouth, " in text, pose
                text = text.replace("closed mouth, ", "")
            graph["6b"] = {"class_type": "CLIPTextEncode",
                           "inputs": {"clip": ["4", 1], "text": text}}
            graph["11"]["inputs"]["positive"] = ["6b", 0]
        # Unconditional: SHADE_BAN applies to every pose -- the gloss is a
        # property of the redraw, not of any one pose -- so there is always a
        # second negative, and the record only decides what goes in FRONT of
        # it. (The architecture note above HAND_BAN in `prompt_style.py` is
        # why a subtractive guard belongs to the late pass.)
        graph["7b"] = {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["4", 1],
            "text": (SHADE_BAN + rec.hires_negative
                     + negative(pose, costume))}}
        graph["11"]["inputs"]["negative"] = ["7b", 0]
        graph["8"]["inputs"]["samples"] = ["11", 0]

    return graph


# ---- derived views ------------------------------------------------------
# The record is the source; these are the shapes the rest of the repo (and a
# decade of .local scripts) already read. Membership and lookups only -- do
# not write to them.

SIZES = {name: rec.size for name, rec in POSE_RECORDS.items()}
HEAD_FRAMINGS = tuple(n for n, r in POSE_RECORDS.items()
                      if r.framing == "head")
# The poses whose finish is 174ce1dc's. It is TWO things -- the pass-2 paint
# guard in the record's `hires_negative`, and `paint_finish` dropping THIN --
# and a pose that got one half without the other is precisely the failure the
# `straw` note warns about. One flag on the record makes it one decision.
PAINT_FINISH = tuple(n for n, r in POSE_RECORDS.items() if r.paint_finish)
# The seed each pose was settled on, where the pose has one. Not a default --
# `--seed` is still explicit -- but the number is otherwise only recoverable
# from a filename in a worker's history.
SETTLED_SEED = {n: r.settled_seed for n, r in POSE_RECORDS.items()
                if r.settled_seed is not None}
HIRES_NEGATIVE = {n: r.hires_negative for n, r in POSE_RECORDS.items()
                  if r.hires_negative}
HIRES_POSITIVE = {n: r.hires_positive for n, r in POSE_RECORDS.items()
                  if r.hires_positive}
HIRES_FINISH = {n: r.hires_finish for n, r in POSE_RECORDS.items()
                if r.hires_finish}
HIRES_PRINT = {n: r.hires_print for n, r in POSE_RECORDS.items()
               if r.hires_print is not None}
