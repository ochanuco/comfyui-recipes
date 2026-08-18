"""Hood off, and the same recipe with the character swapped back to Hamakaze.

Built on hl-c -- the fullest of the three hair-line rungs: strand-line weights
up, (flat color) inside the hair mask, gradient/blend guards in the negative,
and strand clumps. Whether hl-c is the best of the three is not known yet; it is
the furthest in the direction being pushed, which is what makes it the one worth
seeing off the hood.

  hd-yk  Yukari with (rabbit hood:1.55), animal hood replaced by hood down.
         The hood is what has been covering the hairstyle at low ControlNet
         strength, so this is also the first clean look at the hair itself.
  hd-hz  the same graph with Hamakaze back in it.

The hairstyle tags are character identity, not recipe, so they swap in both the
positive and the hair-region prompt. Everything that makes the line -- weights,
flat colour, negative guards, Detail Daemon, ControlNet strength 0.35 -- is
byte-identical between the two, which is the whole point of the pair.

One asymmetry that cannot be removed here: the ControlNet source is a Hamakaze
lineart. She is being drawn over her own silhouette and Yukari is not, so hd-hz
has an advantage that has nothing to do with the prompt.
"""
import copy
import json
import sys
from pathlib import Path
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import queue_dq3 as q  # noqa: E402
from comfy_host import base_url

JOB = "7219d431-c44f-4c05-be94-c8330b7d0eef"
SEED = 111222333
STRENGTH = 0.35

hist = json.load(urllib.request.urlopen(f"{base_url()}/history/{JOB}"))
graph = hist[JOB]["prompt"][2]

HZ_START, HZ_END = "hamakaze (kancolle)", "kantai collection"
text = graph["6"]["inputs"]["text"]
i, j = text.index(HZ_START), text.index(HZ_END) + len(HZ_END)
PREFIX, SUFFIX = text[:i], text[j:]
HZ_SPAN = text[i:j]

# Yukari, hood down. The hood is inside her class block, so taking it off is a
# substitution there rather than an extra tag fighting (rabbit hood:1.55).
YK_SPAN = f'{q.CLASSES["yukari"]}, {q.FRANCHISE["yukari"]}'
assert "(rabbit hood:1.55), animal hood" in YK_SPAN
YK_SPAN = YK_SPAN.replace("(rabbit hood:1.55), animal hood", "(hood down:1.45), hood down")
assert "rabbit hood" not in YK_SPAN

REGION_LINE = (
    "(detailed hair:1.7), (defined hair strands:1.9), (hair strand outline:1.7), "
    "{hairstyle}, (hair between eyes:1.3), (black lineart:1.55), "
    "(defined lines:1.45), (crisp lines:1.35), (flat color:1.3), "
    "(cel shading:1.3), (sharp shadow edges:1.3), "
    "(hair strands:1.5), (clumped hair strands:1.4)"
)
YK_HAIR = "(short hair with long locks:1.45), (very long sidelocks:1.35), sidelocks"
HZ_HAIR = "(parted bangs:1.4)"

NEG = graph["7"]["inputs"]["text"] + (
    ", (gradient:1.35), (soft shading:1.35), (airbrush:1.3), "
    "(smooth shading:1.3), (blurry hair:1.25), (glossy hair:1.2)"
)
# The hood only needs holding down on Yukari; Hamakaze has none to raise.
NEG_YK = NEG + ", (hood up:1.4), (animal hood:1.35), (rabbit hood:1.3)"

RUNS = [
    ("hd-yk", YK_SPAN, YK_HAIR, NEG_YK),
    ("hd-hz", HZ_SPAN, HZ_HAIR, NEG),
]

for name, span, hairstyle, neg in RUNS:
    g = copy.deepcopy(graph)
    g["6"]["inputs"]["text"] = PREFIX + span + SUFFIX
    g["7"]["inputs"]["text"] = neg
    g["30"]["inputs"]["text"] = REGION_LINE.format(hairstyle=hairstyle)
    g["12"]["inputs"]["strength"] = STRENGTH
    for node in g.values():
        if "noise_seed" in node.get("inputs", {}):
            node["inputs"]["noise_seed"] = SEED
        if "seed" in node.get("inputs", {}):
            node["inputs"]["seed"] = SEED
        if node["class_type"] == "SaveImage":
            node["inputs"]["filename_prefix"] = f"{name}-{SEED}"
    req = urllib.request.Request(
        f"{base_url()}/prompt",
        data=json.dumps({"prompt": g}).encode(),
        headers={"Content-Type": "application/json"},
    )
    print(name, json.load(urllib.request.urlopen(req))["prompt_id"], flush=True)
