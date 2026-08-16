"""Yukari's face on the 7219d431 pipeline, by swapping one span of one node.

That job is Hamakaze on a graph nothing else here has used: a lineart ControlNet
driven by br-src-lb-parted.png, regional conditioning aiming a hair-detail prompt
at the hair only, and a Detail Daemon sampler at 0.1. Rebuilding that by hand
would drift, so the graph is fetched from /history and only the character span of
node 6 is replaced -- everything else, including the ControlNet source, the mask
nodes, the sampler settings and the seed, stays byte-identical.

What is swapped is the run of tags from the character name up to the franchise:

    hamakaze (kancolle) ... kantai collection
    ->  yuzuki yukari ... vocaloid, voiceroid

Her class block comes from CLASSES so it agrees with every other Yukari render
here. The hair-region prompt on node 30 is left alone: it names hair strands and
parted bangs, neither of which is character-specific, and it is the thing the
last few commits were tuning.

Three seeds. The source seed is kept as one of them so the pipeline's own result
is directly comparable; the ControlNet holds the composition either way.
"""
import json
import sys
from pathlib import Path
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import queue_dq3 as q
from comfy_host import base_url

SRC = "7219d431-c44f-4c05-be94-c8330b7d0eef"
HOST = base_url()

hist = json.load(urllib.request.urlopen(f"{HOST}/history/{SRC}"))
graph = list(hist.values())[0]["prompt"][2]

HZ_SPAN_START = "hamakaze (kancolle)"
HZ_SPAN_END = "kantai collection"
YK = f'{q.CLASSES["yukari"]}, {q.FRANCHISE["yukari"]}'

node6 = next(n for n in graph.values()
             if n.get("class_type") == "CLIPTextEncode"
             and HZ_SPAN_START in n["inputs"]["text"])
text = node6["inputs"]["text"]
i = text.index(HZ_SPAN_START)
j = text.index(HZ_SPAN_END) + len(HZ_SPAN_END)
new_text = text[:i] + YK + text[j:]
assert "hamakaze" not in new_text and "yuzuki yukari" in new_text
assert new_text.startswith("best quality") and new_text.endswith("(grey background:1.2)")
node6["inputs"]["text"] = new_text

sampler_node = next(n for n in graph.values()
                    if n.get("class_type") == "RandomNoise")
save = next(n for n in graph.values() if n.get("class_type") == "SaveImage")

for seed in (int(sampler_node["inputs"]["noise_seed"]), 555666777, 111222333):
    sampler_node["inputs"]["noise_seed"] = seed
    save["inputs"]["filename_prefix"] = f"ykf-{seed}"
    body = json.dumps({"prompt": graph}).encode()
    req = urllib.request.Request(f"{HOST}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    print(f"ykf-{seed}", json.load(urllib.request.urlopen(req)), flush=True)
