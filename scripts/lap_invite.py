"""Inviting a lap pillow, one girl, patting her thigh. Diagnosis then patterns.

`lap pillow` was the wrong tag. Its wiki says so in as many words: it is for a
head already resting on someone, and "if a character is merely inviting someone
to rest on their lap, use lap pillow invitation". That tag's own wiki then
describes the exact ask -- "sitting in seiza position while patting their thighs
in a beckoning manner" -- and, because nobody is on her lap, there is no second
person for the model to draw. Two of three `lap pillow` renders had one.

Those three also came out in blown neon: green backdrop, orange skin, posterised
purple. pick/momiji-lap dropped (flat color:1.3), (simple background:1.3),
(grey background:1.2) for its lap render and I kept them, flagged the risk, and
that is the risk. Phase 1 tests it rather than assuming it, because "the old
note said so" is not the same as knowing which of the three did it.

  Phase 1, 4 renders: invitation pose x {flat surface kept, flat surface dropped}
                      x 2 seeds. Whichever holds its colour decides the surface.
  Phase 2, 12 renders: six readings of the invitation on the winning surface,
                      two seeds each.

Verified tags used here: lap pillow invitation, beckoning, hand on own thigh,
patting, seiza, smug, come hither, head tilt, one eye closed, blush, smile.
"""
import json
import sys
import urllib.request

sys.path.insert(0, "/Users/chanu/ghq/github.com/ochanuco/ai-comfyui-env/scripts")
import yukari_recipe as r  # noqa: E402
from comfy_host import base_url

HOST = base_url() + "/prompt"
FLAT = "(flat color:1.3), (simple background:1.3), (grey background:1.2), "
assert FLAT in r.SURFACE
SURFACE_NO_FLAT = r.SURFACE.replace(FLAT, "")

# Nobody is on her lap, so the crowd guards stay and (from below) still goes:
# an invitation is offered downward to someone about to lie down.
NEG = r.NEGATIVE.replace("(from below:1.35), ", "")
NEG += ", (2girls:1.6), (multiple girls:1.6), (duplicate:1.55), (another person:1.5)"
assert "from below" not in NEG


def queue(pose_text: str, seed: int, prefix: str, flat: bool) -> str:
    positive = r.positive("lap").replace(r.POSES["lap"], pose_text)
    if not flat:
        positive = positive.replace(r.SURFACE, SURFACE_NO_FLAT)
    assert "lap pillow invitation" in positive
    assert "head on lap" not in positive  # names a second person; drew her twice
    graph = r.build("lap", seed, "tmp")
    graph["6"]["inputs"]["text"] = positive
    graph["7"]["inputs"]["text"] = NEG
    graph["9"]["inputs"]["filename_prefix"] = f"{prefix}-{seed}"
    req = urllib.request.Request(
        HOST, data=json.dumps({"prompt": graph}).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req))["prompt_id"]


BASE = ("(solo:1.5), (lap pillow invitation:1.5), (seiza:1.3), "
        "(hand on own thigh:1.35), (beckoning:1.3), (smug:1.4), "
        "(looking down:1.35), cowboy shot")

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "phase1"
    if which == "phase1":
        for flat in (True, False):
            tag = "flat" if flat else "noflat"
            for seed in (737373737, 1886970040):
                print(tag, seed, queue(BASE, seed, f"li-{tag}", flat), flush=True)

# Phase 1 said the surface is not the cause: mean saturation came out 138/105
# with the flat tags kept and 163/127 without them, against 26 on a healthy
# render. Dropping them made it worse, so pick/momiji-lap's advice was not the
# fix here.
#
# The other thing changed for this pose is the negative, and this repo already
# has the precedent: five duplicate-guard tags once took clones from 5-of-8 to
# 7-of-8 AND wrecked the palette. Four guards at 1.5-1.6 went in here.
#
#   noguard   recipe negative untouched
#   nofb      recipe negative with only (from below:1.35) removed
NEG_PLAIN = r.NEGATIVE
NEG_NOFB = r.NEGATIVE.replace("(from below:1.35), ", "")


def queue_neg(negative, seed, prefix):
    positive = r.positive("lap").replace(r.POSES["lap"], BASE)
    graph = r.build("lap", seed, "tmp")
    graph["6"]["inputs"]["text"] = positive
    graph["7"]["inputs"]["text"] = negative
    graph["9"]["inputs"]["filename_prefix"] = f"{prefix}-{seed}"
    req = urllib.request.Request(
        HOST, data=json.dumps({"prompt": graph}).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req))["prompt_id"]
