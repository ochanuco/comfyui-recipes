"""Make socks-over-tights hold, and judge it across seeds rather than on one.

Seven renders of the current recipe put the left/right leg difference anywhere
from 1.8 to 24.7 and the visible tights band from 7.7% to 34.8%. Every legwear
conclusion drawn earlier in this session came from comparing two single-seed
renders, and differences of that size are inside this spread -- so those
comparisons could not tell a tag's effect from the draw. Three arms, four seeds
each, same four seeds throughout.

The candidate cause is a deletion of mine. gl-lounge-555666777 -- the reference
this design came from -- carried four asymmetry guards:

    (mismatched legwear:1.5), (single thighhigh:1.5),
    (asymmetrical legwear:1.45), (uneven legwear:1.4)

Rebuilding the legwear block left only the first. Restoring the other three is a
revert, not a new guard block, which matters: piling guards into the negative
wrecked the palette once before, but these three were in the render whose
palette is the target.

    A  current recipe, unchanged -- the baseline the other two are read against
    B  A + the three restored guards
    C  B without (over-kneehighs:1.4), which asks for a length the thighhighs
       tags contradict; a per-leg coin flip between two lengths is one way to
       get one sock long and one short

Scored on both legs at once: symmetry (|left-right| value in the calf boxes) and
how much dark tights show in the upper-thigh band. Neither alone is the ask --
two bare legs are perfectly symmetric.
"""
import json
import sys
import urllib.request

sys.path.insert(0, "/Users/chanu/ghq/github.com/ochanuco/ai-comfyui-env/scripts")
import yukari_recipe as r  # noqa: E402

SEEDS = [555666777, 111222333, 737373737, 3409564303]

GUARDS = ("(single thighhigh:1.5), (asymmetrical legwear:1.45), "
          "(uneven legwear:1.4), ")
assert "(mismatched legwear:1.5), " in r.NEGATIVE
NEG_GUARDED = r.NEGATIVE.replace(
    "(mismatched legwear:1.5), ", "(mismatched legwear:1.5), " + GUARDS
)
assert "single thighhigh" not in r.NEGATIVE and "single thighhigh" in NEG_GUARDED

assert "(over-kneehighs:1.4), " in r.LEGWEAR
LEG_NO_OKH = r.LEGWEAR.replace("(over-kneehighs:1.4), ", "")

ARMS = [
    ("A", r.LEGWEAR, r.NEGATIVE),
    ("B", r.LEGWEAR, NEG_GUARDED),
    ("C", LEG_NO_OKH, NEG_GUARDED),
]

for name, legwear, negative in ARMS:
    positive = r.positive("peace").replace(r.LEGWEAR, legwear)
    assert legwear in positive
    for seed in SEEDS:
        graph = r.build("peace", seed, "tmp")
        graph["6"]["inputs"]["text"] = positive
        graph["7"]["inputs"]["text"] = negative
        graph["9"]["inputs"]["filename_prefix"] = f"ly{name}-{seed}"
        req = urllib.request.Request(
            "http://127.0.0.1:8188/prompt",
            data=json.dumps({"prompt": graph}).encode(),
            headers={"Content-Type": "application/json"},
        )
        print(name, seed, json.load(urllib.request.urlopen(req))["prompt_id"], flush=True)
