"""Get Yukari's hairstyle out of the 7219d431 pipeline.

ykf-* swapped only node 6's character span and the hair came out as Hamakaze's
short parted bob. Two things were holding it there, and only one of them was
about ControlNet:

  node 30, the hair-region prompt, still said (parted bangs:1.4) -- a Hamakaze
  hairstyle instruction aimed at the hair mask at strength 1.0. That was left
  behind by the earlier swap.

  node 12 applies noob-lineart-anime at 0.6 over 0-80% of the sampling, with
  br-src-lb-parted.png as the source. Yukari's (short hair with long locks:1.45),
  (very long sidelocks:1.3) changes the silhouette, which is exactly what a
  lineart ControlNet is there to prevent.

Fix the prompt in all three, then sweep the strength, because the prompt fix
alone may be enough and the ControlNet is what makes the line quality good.

  hr-c60  0.60  strength unchanged -- isolates the prompt fix
  hr-c35  0.35
  hr-c00  0.00  no structural guidance; the cel block and Detail Daemon remain

Same seed across all three, so the only thing moving is the strength.
"""
import copy
import json
import sys
import urllib.request

sys.path.insert(0, "REPO_ROOT/scripts")
import queue_dq3 as q  # noqa: E402

JOB = "7219d431-c44f-4c05-be94-c8330b7d0eef"
SEED = 111222333

hist = json.load(urllib.request.urlopen(f"http://127.0.0.1:8188/history/{JOB}"))
graph = hist[JOB]["prompt"][2]

# --- node 6: character span, as ykf-* already did -------------------------
HZ_START, HZ_END = "hamakaze (kancolle)", "kantai collection"
YK = f'{q.CLASSES["yukari"]}, {q.FRANCHISE["yukari"]}'
text = graph["6"]["inputs"]["text"]
i = text.index(HZ_START)
j = text.index(HZ_END) + len(HZ_END)
graph["6"]["inputs"]["text"] = text[:i] + YK + text[j:]
assert "hamakaze" not in graph["6"]["inputs"]["text"]
assert "yuzuki yukari" in graph["6"]["inputs"]["text"]

# --- node 30: the hair-region prompt --------------------------------------
# Replace the one hairstyle tag; leave every detail/lineart tag alone, since
# those are what this pipeline's hair quality comes from.
region = graph["30"]["inputs"]["text"]
assert "(parted bangs:1.4)" in region
region = region.replace(
    "(parted bangs:1.4)",
    "(short hair with long locks:1.45), (very long sidelocks:1.35), sidelocks",
)
graph["30"]["inputs"]["text"] = region
assert "parted bangs" not in region

for node in graph.values():
    if node["class_type"] in ("KSampler", "RandomNoise", "KSamplerSelect"):
        if "noise_seed" in node["inputs"]:
            node["inputs"]["noise_seed"] = SEED
        if "seed" in node["inputs"]:
            node["inputs"]["seed"] = SEED

for name, strength in [("hr-c60", 0.60), ("hr-c35", 0.35), ("hr-c00", 0.00)]:
    g = copy.deepcopy(graph)
    g["12"]["inputs"]["strength"] = strength
    for node in g.values():
        if node["class_type"] == "SaveImage":
            node["inputs"]["filename_prefix"] = f"{name}-{SEED}"
    body = json.dumps({"prompt": g}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8188/prompt", data=body,
        headers={"Content-Type": "application/json"},
    )
    print(name, strength, json.load(urllib.request.urlopen(req))["prompt_id"], flush=True)
