#!/usr/bin/env python3
"""Hold the costume to a contract, and say which pose broke it.

The costume does not survive a change of pose on its own. Every pose in
`yukari_recipe.py` has needed splices to keep the same clothes -- `boss` five,
`nape` two, `prone` four -- because tags are one argument about the whole
picture and a new pose re-weights all of them. A LoRA would end that; nothing on
the worker can load one yet (`LoraLoader` returns an empty list). Until then the
next best thing is not to prevent drift but to **fail on it**.

    uv run scripts/costume_check.py                     # every pose, prompt side
    uv run scripts/costume_check.py --pose prone
    uv run scripts/costume_check.py --palette out/*.png # render side

**Prompt side.** Each pose's prompt is rebuilt from the shared blocks and
compared, tag by tag, against what `positive()` actually returns. Every
difference has to be named in `EXCEPTIONS` below with a reason. An undeclared
one is an error -- which is the whole point: `positive()` is a stack of
`.replace()` calls that have grown one session at a time and do not know about
each other, and this is the only place they are written down together.

Adding an exception is cheap and deliberate. Silently changing a garment is not.

**Render side.** `--palette` measures how much of the figure each costume colour
covers and compares it against a baseline recorded from an approved render of
the same pose.

Absolute floors were tried first and are useless: with tolerances wide enough to
catch a shaded garment, hair satisfies "pale sock" and shading satisfies
"legwear grey", and three renders this project had already rejected all passed.
What separates them is the *share* against a render that was accepted -- the
bare-legged one has 9% pale sock against the accepted 31%, a third. So the check
is relative, per pose, and a baseline is part of accepting a render.

It measures colour presence, not garment identity. A grey sock would pass as
grey tights. It is a smoke alarm, not an inspector.

Exit status is 1 if anything fails, so this can gate a commit.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import hashlib
import json

import numpy as np
from PIL import Image

import yukari_recipe as yk

HEAD = "best quality, absurdres, 1girl, solo"

# The costume itself, fingerprinted. Per-pose drift is only half the problem:
# editing CHARACTER or LEGWEAR changes the clothes in every pose at once, and
# comparing poses against the blocks cannot see that, because the blocks are
# what it compares against. So the blocks are hashed here.
#
# When this fails, nothing is broken -- something was changed. Re-run with
# `--accept` to print the new value, paste it in, and write down in
# docs/render-notes.md what the costume is now. That is the whole mechanism:
# it does not stop a change, it stops an *unrecorded* one.
COSTUME_BLOCKS = ("character", "legwear", "body", "face", "surface", "hood", "thin",
                  # The second costume is under the same contract as the first.
                  # It has no approved render behind it yet, which is a reason
                  # to hash it rather than a reason not to: the fingerprint is
                  # what makes a later edit to it visible.
                  "sporty", "sporty_legwear", "sporty_hood",
                  # And the third, for the same reason the second is here.
                  "fitness", "fitness_legwear", "fitness_hood")
# 47b0d089d5a5ec77 -> aa86759a39ffca43 on 2026-08-20. The settled blocks did not
# change a character: what moved the hash is the second costume joining the list
# above. The proof it is only that is in the notes -- every pose's prompt and
# graph under `--costume default` was compared against the previous commit and
# came back byte-identical.
# aa86759a39ffca43 -> 2940a4b4552ad646 on 2026-08-24. FACE's lashes: a bare
# unweighted `eyelashes`, never swept since the block was written, becomes
# `(eyelashes:1.3), (thick eyelashes:1.35)`. Every pose wears it.
# 2940a4b4552ad646 -> 9c4d0da38fc1378f on 2026-08-25. A THIRD costume joins the
# list above -- `fitness`, the summer gym kit. The settled blocks are untouched
# again, and the same proof applies: every pose under `--costume default` and
# `--costume sporty` was compared against the previous commit.
# 9c4d0da38fc1378f -> 910a022f1d495234 on 2026-08-25. `fitness` drops
# `(ribbed shirt:1.35)` -- 「スポーツ着としては合ってない」 -- and its
# `oversized shirt` goes 1.4 -> 1.45. The two moved together and had to: the rib
# was what made the hem unsettleable, and with it gone the length went LONGER
# than the value that had already been rejected as too long.
#
# An intermediate cb2de6f211d944dd (rib kept, hem 1.3) existed for one round and
# is not in the file: that was the arm 「服を中に入れるのは違う」 rejected.
#
# Only this costume's character block moved. `default` and `sporty` were rebuilt
# against the previous commit across every pose and both passes, and did not.
# 910a022f1d495234 -> 73ee99e0962defe1 on 2026-08-25. `fitness`'s
# `oversized shirt` goes 1.45 -> 1.55: 「股を出さずに服で隠すこと」. Third and last
# value on that dial. Only this costume's character block moved; 32 poses under
# `default` and `sporty` were rebuilt across both passes and did not.
COSTUME_FINGERPRINT = "6baf3a49c68abd92"

# The delivery half of the identity -- backdrop, purple stroke, acceptance
# band -- fingerprinted from `yukari/delivery_style.py`. A SEPARATE hash on
# purpose: a backdrop change is not a costume change, and a fingerprint that
# mixes them tells the reader the wrong thing moved. Hashed from an explicit
# canonical payload (not from the module source), so a comment edit does not
# move it and a value edit always does.
DELIVERY_FINGERPRINT = "29ca465d3ac86bc9"
FINGERPRINT_SCHEMA = 1


def tags(text: str) -> list[str]:
    return [t.strip() for t in text.split(",") if t.strip()]


def canonical(pose: str, costume: str = "default") -> list[str]:
    """The costume as the shared blocks define it, before any pose splices.

    `POSES[pose]` raw, NOT `yk.pose_block(pose, costume)`. A costume is allowed
    to edit the pose's own tags -- `sporty` takes `stand`'s black high tops out
    because it brings shoes of its own -- and going through `pose_block` here
    would compare that edit against itself and see nothing. Raw, it reads as a
    departure and has to be declared like any other.
    """
    blocks = yk.COSTUMES[costume]
    return (tags(HEAD) + tags(blocks["character"]) + tags(yk.POSES[pose])
            + tags(blocks["legwear"]) + tags(yk.FACE) + tags(yk.SURFACE)
            + tags(yk.BODY) + tags(blocks["hood"]) + tags(yk.THIN))


# Every declared departure from the shared blocks, with the reason it was paid
# for. `added` and `removed` are exact tags. The reasons are one line each; the
# measurements behind them are in docs/render-notes.md.
EXCEPTIONS: dict[str, list[dict]] = {
    "stand": [
        {"added": ["(long legs:1.35)"],
         "why": "a standing figure reads its own proportions; 40.1% of height "
                "below the hem to 55.7%"},
        {"removed": ["(eyelashes:1.3)", "(thick eyelashes:1.35)"],
         "added": ["eyelashes"],
         "why": "the 08-24 lash pair melts this pose into foil noise; isolated "
                "tag-by-tag, and the negative's guard is innocent and stays"},
    ],
    "boss": [
        {"removed": ["(petite:1.2)"], "added": ["(mature female:1.35)"],
         "why": "the pose exists to read grown up; one substitution in one slot"},
        {"added": ["(small breasts:1.35)"],
         "why": "`mature female` brings a chest with it and the negative could "
                "not finish the job alone"},
    ],
    "nape": [
        {"added": ["(off shoulder:1.25)"],
         "why": "what uncovers the nape; rides with HOOD rather than joining "
                "the pose block, which is already at eight tags"},
        {"removed": ["looking at viewer"],
         "why": "she is turned away; the instruction has no referent and either "
                "argues with the pose or spins her around"},
    ],
    "winded": [
        {"removed": ["closed mouth"],
         "why": "\u3042\u309b\u301c\u301c\u301c is an open mouth and FACE "
                "closes it"},
        {"removed": ["small mouth"],
         "why": "the groan makes the mouth the largest thing in the face; "
                "`swelter` removed it for the same sentence"},
        {"removed": ["looking at viewer"],
         "why": "shot from the side with her head back, the instruction has no "
                "referent -- `nape`'s reason"},
    ],
    "hoops": [
        {"removed": ["closed mouth"],
         "why": "\u301c\u301c\u301c is a drawn-out complaint and FACE closes "
                "the mouth"},
    ],
    "hige": [
        {"added": ["(covered mouth:1.35)"],
         "why": "the held tips hide the mouth; means-agnostic so the hair, "
                "not a hand, gets to do it"},
        {"added": ["(tareme:1.5)", "(large eyes:1.4)"],
         "why": "`smelling hair` narrows the eyes into a smirk; FACE's own "
                "pair restated at the weights that outvoted it (kts2c3)"},
    ],
    "snack": [
        {"removed": ["closed mouth"],
         "why": "a bite. `straw` keeps it, because lips close around a straw "
                "and they do not close around a melon bread"},
        {"removed": ["(thin lineart:1.3)", "(fine lines:1.25)",
                     "(delicate lines:1.2)"],
         "why": "`straw`'s finish, carried onto its sibling in the same "
                "costume rather than re-measured; the two halves move together "
                "through PAINT_FINISH"},
    ],
    "straw": [
        {"removed": ["(thin lineart:1.3)", "(fine lines:1.25)",
                     "(delicate lines:1.2)"],
         "why": "a palette decision, not a line one: THIN and this pose's "
                "pass-2 paint guard measured superadditive on the flat count "
                "(150 -> 190 -> 225), and the guard is what the picked render "
                "wanted"},
    ],
    "prone": [
        # Five legwear entries used to sit here, shortening and recolouring the
        # second garment. They are gone because the second garment is gone: the
        # one-pantyhose leg is in LEGWEAR itself, so it is not a departure from
        # the shared blocks and there is nothing for this pose to declare.
        {"removed": ["(wide hips:1.3)", "(thick thighs:1.35)"],
         "added": ["(wide hips:1.0)", "(thick thighs:1.05)"],
         "why": "BODY was settled on poses seen from the front or the side; "
                "from behind and foreshortened the same tags read as bulk"},
    ],
    # `portrait`, `allnighter` and `dizzy` used to carry a hand-written copy of
    # the crop removal each. It is generated by `_cropped()` now, because the
    # legwear it names belongs to the costume and there is more than one.
    # `(pale skin:1.25)` is the one tag of BODY that stays -- the crop is above
    # the legs and the hips but not above her skin -- so it is neither removed
    # nor added.
    # The same crop as `portrait`, so the same departure, for the same reason.
    "allnighter": [
        {"removed": ["closed mouth"],
         "why": "\u653e\u5fc3\u72b6\u614b: the mouth hangs open. `small mouth` was "
                "briefly removed too, for a wider mouth that is no longer asked for"},
    ],
    # `allnighter`'s crop and `allnighter`'s two departures, unchanged: what
    # differs between them is inside the pose block, not against the costume.
    "dizzy": [
        {"removed": ["closed mouth"],
         "why": "\u5bdd\u4e0d\u8db3: the mouth hangs open"},
    ],
    # \u30c6\u30d8\u30da\u30ed had a `closed mouth` removal here while `;p` was
    # drawing a tongue through it. 「\u820c\u51fa\u3057\u6b62\u3081\u3066」 took
    # the tongue and the emoticon together, so the mouth is shut like every
    # other pose and the departure is gone rather than left lying -- an
    # undeclared exception and a stale declaration fail this file the same way.
    # Full body, so unlike `allnighter` it wears the whole costume; the mouth is
    # its only departure.
    "allnighter_full": [
        {"removed": ["closed mouth"],
         "why": "\u653e\u5fc3\u72b6\u614b: the mouth hangs open"},
    ],
    # One departure, and it is no longer a facial one. 「いつもの表情に戻して」
    # took the exhaustion off, so both the `closed mouth` removal (open mouth)
    # and, before it, the `looking at viewer` removal (face in the floor) have
    # come and gone from this entry. That churn is the point: this file is
    # what catches a pose flipped between its three face states without its
    # declaration flipped too -- it failed on exactly that, twice, today.
    #
    # It briefly carried `prone`'s hip/thigh easing too, on the argument that
    # it shared `prone`'s from-above geometry; that tag left the pose when the
    # dive was asked for, and the splice left with it.
    # `kick`'s expression moved into the pose block, which put the pose into
    # `open_mouthed`. A ドヤ顔 with the mouth shut is composure, and that is
    # what four rounds of this kept producing.
    "kick": [
        {"removed": ["closed mouth"],
         "why": "(open mouth:1.35) is most of the difference between a smirk "
                "and a ドヤ顔; the two cannot both be in the prompt"},
    ],
    # Brushing teeth: the brush is in the mouth, so the mouth is open. The
    # straw rule cuts the other way here -- lips close around a straw, not
    # around a moving brush.
    "brush": [
        {"removed": ["closed mouth"],
         "why": "the brush is in the mouth; lips close around a straw, not "
                "around a moving brush"},
    ],
    # A failed sit-up: gritted teeth, and teeth are drawn with the mouth open.
    "situp": [
        {"removed": ["closed mouth"],
         "why": "(clenched teeth:1.35) is the strain, and a shut mouth turns "
                "the failure back into a rest"},
    ],
    "flop": [
        {"added": ["(long legs:1.40)"],
         "why": "bracketed: no tag reads \u80f4\u4f53\u304c\u9577\u3044, "
                "1.45 reads \u811a\u304c\u9577\u3059\u304e\u308b; 1.40 is the midpoint"},
    ],
    "yawn": [
        {"removed": ["closed mouth"], "why": "a yawn needs the mouth open"},
    ],
    # A grin is drawn with the teeth showing, and a shut mouth turns it into the
    # smirk every other pose in this file already has.
    "hype": [
        {"removed": ["closed mouth"], "why": "(grin:1.4) shows teeth"},
    ],
    "roar": [
        {"removed": ["closed mouth"], "why": "がおー is an open mouth or it is a shrug"},
    ],
    # The rest of the がおー family, and all for `roar`'s reason: `GAO_FACE`
    # carries `(open mouth:1.4)` and FACE's `closed mouth` is its direct
    # opposite. If this list and `open_mouthed` ever disagree, this is the file
    # that says so.
    "pounce": [
        {"removed": ["closed mouth"], "why": "wears GAO_FACE"},
    ],
    "loom": [
        {"removed": ["closed mouth"], "why": "wears GAO_FACE"},
    ],
    "snarl": [
        {"removed": ["closed mouth"], "why": "wears GAO_FACE"},
    ],
    # Not GAO_FACE -- this one asks for the open mouth itself, as panting.
    # Three FACE removals, all on the same argument: this block was settled on a
    # composed girl and the pose is a tantrum.
    "swelter": [
        {"removed": ["closed mouth"],
         "why": "she is screaming; a shut mouth is a girl having a nice lie down"},
        {"removed": ["small mouth"],
         "why": "the reference's mouth is the biggest thing in the face. "
                "`allnighter` made this exact removal once and gave it back"},
        {"removed": ["looking at viewer"],
         "why": "`nape`'s reason, different cause: with the eyes clamped shut "
                "the instruction has no referent"},
        {"removed": ["(petite:1.2)"], "added": ["(petite:1.4)"],
         "why": "`prone`'s from-above easing, pointed at length instead of "
                "bulk: the overhead camera was making the legs read long"},
    ],
    "fall": [
        {"removed": ["closed mouth"], "why": "she is shouting"},
    ],
    "doze": [
        {"removed": ["looking at viewer"],
         "why": "`nape`'s reason at the eyes: she is asleep, so the "
                "instruction has no referent and either argues with the pose "
                "or opens them"},
        # The only pose in the file that replaces the backdrop half of SURFACE.
        # It is a break of the contract `ride` and `hoops` keep, and it is
        # declared here rather than argued: both arms were swept at 1152 on the
        # same four seeds and the picked render, b393e171, is the carriage one.
        # The rest of SURFACE -- flat colour, white outline, the shading pair --
        # is untouched, which is what keeps the train drawn rather than
        # photographed.
        {"removed": ["(simple background:1.3)", "(grey background:1.2)"],
         "added": ["(train interior:1.4)", "(vehicle interior:1.3)",
                   "(window:1.2)"],
         "why": "she is asleep ON A TRAIN, and the user picked the arm that "
                "draws one; SURFACE's backdrop is the half a scene replaces"},
    ],
}

# Departures that exist only because a particular costume has the garment being
# spliced. Under another costume the splice does not run at all -- `positive()`
# gates them -- so declaring them globally would fail the other way: a
# declaration that does not describe the built prompt is as wrong as an
# undeclared change, and this file already fails on both.
COSTUME_ONLY: dict[str, dict[str, list[dict]]] = {
    "default": {
        "hige": [
            {"removed": ["(frills:1.25)"],
             "why": "the dress collar it describes is out of frame and the "
                    "tag was landing on the cardigan hem instead (dm5e2v); "
                    "only this costume's CHARACTER carries the tag"},
        ],
        "stand": [
            {"added": ["(criss-cross halter:1.45)"],
             "why": "the dress's own crossed straps, taken with the backdrop "
                    "cost known and accepted"},
        ],
        "boss": [
            {"removed": ["(oversized shirt:1.3)"],
             "why": "`mature female` recruits it into a pale button-front shirt "
                    "dress; dropping it restores the purple bodice"},
            {"added": ["(off shoulder:1.3)"],
             "why": "the approved render has the coat off her shoulders; it "
                    "costs the rabbit hood, deliberately"},
            {"added": ["(criss-cross halter:1.45)"],
             "why": "the dress's own straps, affordable here because the coat "
                    "is already off the shoulders"},
            {"added": ["(ribbed legwear:1.35)"],
             "why": "the rib outlived the thighhighs it belonged to; ADDED, "
                    "not substituted -- substituting it removed the tights"},
        ],
        "portrait": [
            {"added": ["(criss-cross halter:1.45)"],
             "why": "\u80a9\u7d10\u304c\u306a\u3044\u306d: the dress's own "
                    "straps, in frame on a head-and-shoulders crop; the backdrop "
                    "cost is repainted at delivery on this framing"},
        ],
        "nape": [
            {"added": ["(halterneck:1.45)", "(black straps:1.35)"],
             "why": "the bow this pose is looking at; documented as costing "
                    "every other pose its coat, which is why it is spliced"},
        ],
        "kick": [
            {"removed": ["(pale purple pantyhose:1.35)"],
             "added": ["(purple pantyhose:1.15)"],
             "why": "the gradient's light end bleaches to white and this pose "
                    "has the soles at the camera; full colour at reduced "
                    "weight won the bracket"},
        ],
    },
    # The same two departures as `sporty`, because they follow from the same
    # fact: this costume also names shoes. They are written out rather than
    # aliased to that entry -- a costume declaring another costume's exceptions
    # by reference is a line nobody re-reads when one of the two changes.
    "fitness": {
        "swelter": [
            {"removed": ["(white footwear:1.4)", "(sneakers:1.45)",
                         "(high tops:1.3)"],
             "added": ["(no shoes:1.35)"],
             "why": "\u90e8\u5c4b\u3067\u30b8\u30bf\u30d0\u30bf: indoors, and this "
                    "costume's high tops are outdoor shoes"},
        ],
        "stand": [
            {"removed": ["(black footwear:1.35)", "(high tops:1.35)"],
             "why": "this costume names its own shoes; the pose's pair would "
                    "be a second one in the same prompt"},
        ],
    },
    "sporty": {
        "swelter": [
            {"removed": ["(white footwear:1.4)", "(sneakers:1.45)",
                         "(high tops:1.3)"],
             "added": ["(no shoes:1.35)"],
             "why": "\u90e8\u5c4b\u3067\u30b8\u30bf\u30d0\u30bf: the floor is "
                    "indoors and this costume's high tops are outdoor shoes; one "
                    "substitution in the slot the costume reads for her feet"},
        ],
        "stand": [
            {"removed": ["(black footwear:1.35)", "(high tops:1.35)"],
             "why": "this costume names its own shoes; the pose's pair would "
                    "be a second one in the same prompt"},
        ],
    },
}


# Footwear a costume names in its CHARACTER block, which no crop touches. The
# head framings have to take it out themselves; `sporty` is the only costume
# that has any, and `stand` is the only pose that names shoes of its own.
COSTUME_FOOTWEAR = {
    "sporty": ["(white footwear:1.4)", "(sneakers:1.45)", "(high tops:1.3)"],
    "fitness": ["(white footwear:1.4)", "(sneakers:1.45)", "(high tops:1.3)"],
}


def _cropped(costume: str) -> dict:
    """The head framings' one departure: everything below the crop, removed."""
    return {"removed": (tags(yk.COSTUMES[costume]["legwear"])
                        + [t for t in tags(yk.BODY) if t != "(pale skin:1.25)"]
                        + tags(yk.THIN)
                        + COSTUME_FOOTWEAR.get(costume, [])),
            "why": "the crop is above all of it, and naming what is out of "
                   "frame is what invites it back in -- the shoes are on this "
                   "list because c08034a0 drew one floating in the backdrop"}


def declared(pose: str, costume: str) -> list[dict]:
    """Everything this pose is allowed to differ by, in this costume."""
    entries = list(EXCEPTIONS.get(pose, []))
    entries += COSTUME_ONLY.get(costume, {}).get(pose, [])
    if pose in yk.HEAD_FRAMINGS:
        entries.append(_cropped(costume))
    if yk.POSE_RECORDS[pose].own_eyes:
        # Only the halves the strip actually removes: a smug pose's block
        # carries `(half-closed eyes:1.3)` itself, so that tag never leaves
        # the prompt and declaring it removed would be a stale declaration.
        gone = [t for t in tags(yk.RESTING_EYES)
                if t not in tags(yk.positive(pose, costume))]
        entries.append({"removed": gone,
                        "why": "own_eyes: the pose wears its own expression; "
                               "RESTING_EYES is the \u7d20\u9854 default"})
    return entries


# Every colour the costume is made of, measured off approved renders, with the
# per-channel tolerance that isolates it.
PALETTE = [
    ("dress purple", (183, 149, 211), 34),
    ("coat black", (62, 56, 66), 30),
    ("hood lining pink", (188, 97, 106), 45),
    ("skin", (253, 242, 232), 16),
    ("hair light purple", (222, 214, 238), 22),
    # STALE, and knowingly so. Both belong to the retired two-garment leg -- the
    # grey tights and the pale socks over them. The costume is one pantyhose
    # now, purple at the thigh running to black at the ankle, so neither colour
    # is a share of anything and the baselines recorded against them describe a
    # costume that is not built any more.
    #
    # Left in rather than guessed at: a gradient is not one RGB with a
    # tolerance, and the two entries that would replace it have to be measured
    # off an approved one-tights render, then every pose re-recorded with
    # --record. Until that happens, --palette is checking the old design.
    ("legwear grey", (135, 127, 128), 26),
    ("pale sock", (243, 236, 250), 16),
]

BASELINE = REPO_ASSETS = Path(__file__).resolve().parent.parent / "assets/costume-baseline.json"

# How far a share may move from its baseline before it is a different costume.
# Loose on purpose, and measured that way: two renders this project accepted for
# the same pose differ by 0.49x on skin alone, because one has the dress
# covering more of her. The failures worth catching are garments disappearing --
# the bare-legged arm reads 0.30x on the pale sock -- so the band is set below
# the disagreement between accepted renders and above nothing else.
LOW, HIGH = 0.4, 2.5


def fingerprint() -> str:
    """A hash of the shared blocks, in a fixed order."""
    blocks = [getattr(yk, name.upper()) for name in COSTUME_BLOCKS]
    return hashlib.sha256("\n".join(blocks).encode()).hexdigest()[:16]


def delivery_fingerprint() -> str:
    """A hash of the delivery identity, from a canonical payload."""
    from yukari import delivery_style as d
    payload = json.dumps({
        "schema": FINGERPRINT_SCHEMA,
        "backdrop": d.BACKDROP,
        "stroke": d.STROKE,
        "stroke_width_band": d.STROKE_WIDTH_BAND,
        "stroke_width_pct": d.STROKE_WIDTH_PCT,
        "sat_band": list(d.SAT_BAND),
        "bg_sat_max": d.BG_SAT_MAX,
        "finalize_denoise": d.FINALIZE_DENOISE,
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def check_prompt(pose: str, costume: str = "default") -> list[str]:
    """Undeclared differences between the contract and what the recipe builds."""
    canon, actual = canonical(pose, costume), tags(yk.positive(pose, costume))
    added = [t for t in actual if t not in canon]
    removed = [t for t in canon if t not in actual]

    declared_added, declared_removed = [], []
    for exc in declared(pose, costume):
        declared_added += exc.get("added", [])
        declared_removed += exc.get("removed", [])

    problems = []
    for tag in added:
        if tag not in declared_added:
            problems.append(f"undeclared addition: {tag}")
    for tag in removed:
        if tag not in declared_removed:
            problems.append(f"undeclared removal: {tag}")
    # A declaration that no longer describes the code is just as wrong: it means
    # the reason written down belongs to a prompt that is no longer built.
    for tag in declared_added:
        if tag not in added:
            problems.append(f"declared addition not present: {tag}")
    for tag in declared_removed:
        if tag not in removed:
            problems.append(f"declared removal not applied: {tag}")
    return problems


def profile(path: Path) -> dict[str, float]:
    """What share of the figure each costume colour covers."""
    img = np.asarray(Image.open(path).convert("RGB"), np.int16)
    # The backdrop is whatever fills the corners; the recipe does not control it
    # and it moves between renders, so it is measured rather than assumed.
    corners = np.concatenate([img[:24, :24].reshape(-1, 3), img[:24, -24:].reshape(-1, 3),
                              img[-24:, :24].reshape(-1, 3), img[-24:, -24:].reshape(-1, 3)])
    backdrop = np.median(corners, axis=0)
    figure = np.abs(img - backdrop).max(axis=2) > 20
    total = max(int(figure.sum()), 1)

    return {name: float(((np.abs(img - np.array(colour)).max(axis=2) < tol)
                         & figure).sum()) / total
            for name, colour, tol in PALETTE}


def check_palette(path: Path, pose: str, base: dict) -> list[str]:
    got = profile(path)
    if pose not in base:
        print(f"  no baseline for {pose}; --record it from an accepted render")
        for name, share in got.items():
            print(f"      {name:18s} {share:6.2%}")
        return []

    problems = []
    for name, share in got.items():
        want = base[pose].get(name)
        if want is None or want == 0:
            continue
        ratio = share / want
        ok = LOW <= ratio <= HIGH
        print(f"  {'ok ' if ok else 'FAIL'} {name:18s} {share:6.2%} "
              f"({ratio:4.2f}x of {want:.2%})")
        if not ok:
            problems.append(f"{name} is {ratio:.2f}x its baseline")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pose", action="append", default=[],
                    help="check one pose instead of all of them")
    ap.add_argument("--costume", action="append", default=[],
                    help="check one costume instead of all of them")
    ap.add_argument("--palette", type=Path, nargs="*", default=None,
                    help="check rendered images against the costume's colours")
    ap.add_argument("--record", action="store_true",
                    help="write the given images' profiles into the baseline as "
                         "the accepted look for --pose")
    ap.add_argument("--accept", action="store_true",
                    help="print the current fingerprint, for a change that is "
                         "meant and written down")
    args = ap.parse_args()

    if args.accept:
        print(f"costume  {fingerprint()}   -> COSTUME_FINGERPRINT")
        print(f"delivery {delivery_fingerprint()}   -> DELIVERY_FINGERPRINT")
        print("paste the changed one above, and write in docs/render-notes.md "
              "what the look is now")
        return

    failed = False

    if args.palette is not None:
        base = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
        if args.record:
            if len(args.pose) != 1:
                raise SystemExit("--record needs exactly one --pose")
            base[args.pose[0]] = profile(args.palette[0])
            BASELINE.write_text(json.dumps(base, indent=1, sort_keys=True) + "\n")
            print(f"recorded {args.pose[0]} from {args.palette[0].name}")
            return
        pose = args.pose[0] if args.pose else "prone"
        for path in args.palette:
            print(f"{path.name}  [{pose}]")
            problems = check_palette(path, pose, base)
            failed |= bool(problems)
        raise SystemExit(1 if failed else 0)

    got = fingerprint()
    if got != COSTUME_FINGERPRINT:
        failed = True
        print(f"FAIL the costume blocks themselves changed\n"
              f"     contract {COSTUME_FINGERPRINT}, built {got}\n"
              f"     every pose wears this; see --accept")
    else:
        print(f"ok   costume blocks  ({got})")

    got_d = delivery_fingerprint()
    if got_d != DELIVERY_FINGERPRINT:
        failed = True
        print(f"FAIL the delivery identity changed (yukari/delivery_style.py)\n"
              f"     contract {DELIVERY_FINGERPRINT}, built {got_d}\n"
              f"     every delivered picture wears this; see --accept")
    else:
        print(f"ok   delivery style  ({got_d})")

    # Every costume, not just the settled one. A second set of clothes doubles
    # the number of prompts this file is the only record of, and the splices in
    # `positive()` do not all run under both.
    for costume in args.costume or sorted(yk.COSTUMES):
        label = "" if costume == "default" else f"  [{costume}]"
        for pose in args.pose or sorted(yk.POSES):
            problems = check_prompt(pose, costume)
            count = len(declared(pose, costume))
            if problems:
                failed = True
                print(f"FAIL {pose}{label}  ({count} declared)")
                for p in problems:
                    print(f"     {p}")
            else:
                print(f"ok   {pose}{label}  ({count} declared)")

    # THE CONTRACT ONLY EVER COVERED THE FIRST PASS. `check_prompt` reads
    # `yk.positive(pose)`, and `HIRES_POSITIVE` rewrites that text for the second
    # pass afterwards -- so a splice there could take a garment off, or nail a
    # mouth open, and every line above would still say ok. `kick` found this by
    # legitimately needing to drop `closed mouth` in pass 2 only; the same
    # mechanism could drop `(purple dress:1.45)` and nothing would notice.
    #
    # Reported rather than enforced, on purpose. A pass-2 departure is not the
    # same kind of thing as a costume change -- it is a correction applied to a
    # picture that has already been picked, and the file's whole argument for
    # `HIRES_POSITIVE` is that such corrections are cheap there. What is NOT
    # acceptable is that they be invisible.
    hires_poses = sorted(set(getattr(yk, "HIRES_POSITIVE", {}))
                         | set(getattr(yk, "HIRES_NEGATIVE", {})))
    for costume in args.costume or sorted(yk.COSTUMES):
        blocks = yk.COSTUMES[costume]
        worn = (set(tags(blocks["character"])) | set(tags(blocks["legwear"]))
                | set(tags(yk.BODY)) | set(tags(blocks["hood"])))
        suffix = "" if costume == "default" else f"  [{costume}]"
        for pose in hires_poses:
            if args.pose and pose not in args.pose:
                continue
            before = tags(yk.positive(pose, costume))
            g = yk.build(pose, 1, "tmp", 2048, costume=costume)
            after = tags(g["6b"]["inputs"]["text"]) if "6b" in g else before
            gained = [t for t in after if t not in before]
            lost = [t for t in before if t not in after]
            banned = tags(getattr(yk, "HIRES_NEGATIVE", {}).get(pose, ""))
            print(f"     pass 2  {pose}{suffix}")
            for label, items in (("+", gained), ("-", lost), ("ban", banned)):
                if items:
                    print(f"       {label:<3} {', '.join(items)}")
            worn_off = [t for t in lost if t in worn]
            if worn_off:
                failed = True
                print(f"FAIL {pose}{suffix}  pass 2 removes costume: "
                      f"{', '.join(worn_off)}")

    if failed:
        print("\nAn undeclared change is a costume change nobody wrote down.",
              file=sys.stderr)
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
