"""More drawn strand line in the hair, and no colour blending doing the shading.

At ControlNet 0.35 the hairstyle is Yukari's but the strand line is gone -- edge
density in the head box fell 15.1 -> 12.5 as the strength came down, because the
strand lines at 0.6 were being copied out of the donor lineart, not written by
the prompt. What filled the gap was a colour gradient: smooth tonal blending
inside the hair instead of drawn clumps.

So the two halves are separate asks, and the negative is empty on the second
one. Nothing in node 7 forbids gradient shading; (cel shading), (sharp shadow
edges), (two-tone shading) in node 6 are pushing the other way but unopposed.

Three rungs, one change each, strength 0.35 and one seed throughout:

  hl-a  hair region: strand-line weights up, plus (flat color) inside the mask
        so the region's own shading has to be line. Negative untouched.
  hl-b  hl-a + gradient/blend guards in the negative.
  hl-c  hl-b + strand *clumps* rather than more line weight, which is a
        different thing to ask for: (hair strands), (clumped hair strands).

Deliberately not included: any thinning tag. (thin lineart:1.45) cancelled
(black lineart:1.4) outright once already. And the negative guards are on their
own rung because five duplicate-guard tags previously made the failure worse and
wrecked the palette -- if that happens again it has to be attributable.
"""
import copy
import json
import sys
import urllib.request

sys.path.insert(0, "/Users/chanu/ghq/github.com/ochanuco/ai-comfyui-env/scripts")
import queue_dq3 as q  # noqa: E402
from comfy_host import base_url

JOB = "7219d431-c44f-4c05-be94-c8330b7d0eef"
SEED = 111222333
STRENGTH = 0.35

hist = json.load(urllib.request.urlopen(f"{base_url()}/history/{JOB}"))
graph = hist[JOB]["prompt"][2]

# --- character swap, as before --------------------------------------------
HZ_START, HZ_END = "hamakaze (kancolle)", "kantai collection"
text = graph["6"]["inputs"]["text"]
i, j = text.index(HZ_START), text.index(HZ_END) + len(HZ_END)
graph["6"]["inputs"]["text"] = (
    text[:i] + f'{q.CLASSES["yukari"]}, {q.FRANCHISE["yukari"]}' + text[j:]
)
assert "hamakaze" not in graph["6"]["inputs"]["text"]

graph["12"]["inputs"]["strength"] = STRENGTH
for node in graph.values():
    if "noise_seed" in node.get("inputs", {}):
        node["inputs"]["noise_seed"] = SEED
    if "seed" in node.get("inputs", {}):
        node["inputs"]["seed"] = SEED

BASE_REGION = graph["30"]["inputs"]["text"]
assert "(parted bangs:1.4)" in BASE_REGION
YK_LOCKS = "(short hair with long locks:1.45), (very long sidelocks:1.35), sidelocks"

# Line up, and the region's own shading forced flat so it cannot blend.
REGION_A = (
    "(detailed hair:1.7), (defined hair strands:1.9), (hair strand outline:1.7), "
    f"{YK_LOCKS}, (hair between eyes:1.3), (black lineart:1.55), "
    "(defined lines:1.45), (crisp lines:1.35), (flat color:1.3), "
    "(cel shading:1.3), (sharp shadow edges:1.3)"
)
REGION_C = REGION_A + ", (hair strands:1.5), (clumped hair strands:1.4)"

NEG_BASE = graph["7"]["inputs"]["text"]
NEG_GRAD = NEG_BASE + (
    ", (gradient:1.35), (soft shading:1.35), (airbrush:1.3), "
    "(smooth shading:1.3), (blurry hair:1.25), (glossy hair:1.2)"
)

RUNS = [
    ("hl-a", REGION_A, NEG_BASE),
    ("hl-b", REGION_A, NEG_GRAD),
    ("hl-c", REGION_C, NEG_GRAD),
]

for name, region, neg in RUNS:
    g = copy.deepcopy(graph)
    g["30"]["inputs"]["text"] = region
    g["7"]["inputs"]["text"] = neg
    assert "parted bangs" not in region
    for node in g.values():
        if node["class_type"] == "SaveImage":
            node["inputs"]["filename_prefix"] = f"{name}-{SEED}"
    req = urllib.request.Request(
        f"{base_url()}/prompt",
        data=json.dumps({"prompt": g}).encode(),
        headers={"Content-Type": "application/json"},
    )
    print(name, json.load(urllib.request.urlopen(req))["prompt_id"], flush=True)
