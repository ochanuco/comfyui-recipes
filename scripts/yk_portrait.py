"""Crop in to above the chest. The framing tag lost last round.

rc-a/b/c restored the design but all three came out down to the thighs with
(upper body:1.4) in the positive. So the tag alone does not hold the framing on
this recipe, and there are two other levers: stronger framing tags with a
negative that names what to exclude, and the canvas itself, which decides how
much room there is to fill.

ControlNet is off in all three. rc-a at 0.35 put a spare arm up -- the Hamakaze
lineart drags the pose even when the character reads correctly -- and rc-b
(ControlNet off, Detail Daemon on) matched rc-c (plain) closely enough that
neither is worth spending a cell on here.

  pt-a  portrait tags, 1024x1280 -- the same canvas as before, tags only
  pt-b  portrait tags, 1024x1024 -- squarer, so there is less frame to fill
  pt-c  portrait tags, 896x1152 with Detail Daemon on, since if the crop is
        tighter the finish has fewer pixels of face to work with and that is
        worth seeing once

Prompt otherwise identical to the restored design, so the only thing moving is
the framing.
"""
import copy
import json
import sys
import urllib.request

sys.path.insert(0, "/Users/chanu/ghq/github.com/ochanuco/ai-comfyui-env/scripts")
import queue_dq3 as q  # noqa: E402
from comfy_host import base_url

JOB = "7219d431-c44f-4c05-be94-c8330b7d0eef"
SEED = 555666777

hist = json.load(urllib.request.urlopen(f"{base_url()}/history/{JOB}"))
graph = hist[JOB]["prompt"][2]

YK = f'{q.CLASSES["yukari"]}, {q.FRANCHISE["yukari"]}'

FRAMING = ("(portrait:1.5), (head and shoulders:1.4), (close-up:1.2), "
           "(face focus:1.3)")

POSITIVE = (
    "best quality, absurdres, 1girl, solo, "
    f"{YK}, "
    f"(solo:1.5), {FRAMING}, looking at viewer, "
    "(smug:1.35), (half-closed eyes:1.3), "
    "(tareme:1.3), (large eyes:1.3), 2000s (style), eyelashes, "
    "(large iris:1.25), thin eyebrows, closed mouth, small mouth, "
    "(flat color:1.3), (simple background:1.3), (grey background:1.2), "
    "(white outline:1.6), outline, sticker, "
    "(soft shading:1.3), smooth shading, "
    "(pale skin:1.25), "
    "(hood down:1.5), (hood behind head:1.3), (visible hair:1.2), "
    "(purple eyes:1.2)"
)

# The body block goes out: (wide hips), (thick thighs), (narrow waist), (petite)
# all describe things that are no longer in frame, and naming a part is what
# raises its salience -- keeping them is an invitation to draw them.
assert "thick thighs" not in POSITIVE and "wide hips" not in POSITIVE

NEGATIVE = (
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text, "
    "(disembodied eye:1.4), "
    "(full body:1.5), (cowboy shot:1.45), (upper body:1.2), "
    "(hood up:1.5), (hood over head:1.4), "
    "(impasto:1.25), (painterly:1.25), (oil painting (medium):1.2), "
    "(heavy shading:1.2), (detailed shading:1.2), (realistic:1.1), "
    "(huge breasts:1.4), (large breasts:1.25), cleavage"
)

REGION = ("(short hair with long locks:1.45), (very long sidelocks:1.35), "
          "sidelocks, (hair between eyes:1.3), hair ornament")


def queue(g: dict, name: str) -> None:
    for node in g.values():
        if node["class_type"] == "SaveImage":
            node["inputs"]["filename_prefix"] = name
    req = urllib.request.Request(
        f"{base_url()}/prompt",
        data=json.dumps({"prompt": g}).encode(),
        headers={"Content-Type": "application/json"},
    )
    print(name, json.load(urllib.request.urlopen(req))["prompt_id"], flush=True)


def plain(w: int, h: int) -> dict:
    return {
        "4": {"class_type": "DiffusersLoader",
              "inputs": {"model_path": "hassaku-il-v22"}},
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"batch_size": 1, "width": w, "height": h}},
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["4", 1], "text": POSITIVE}},
        "7": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["4", 1], "text": NEGATIVE}},
        "3": {"class_type": "KSampler", "inputs": {
            "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["5", 0], "seed": SEED, "steps": 30, "cfg": 5.0,
            "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode",
              "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0], "filename_prefix": "pt"}},
    }


queue(plain(1024, 1280), f"pt-a-{SEED}")
queue(plain(1024, 1024), f"pt-b-{SEED}")

# pt-c keeps the port's sampler chain (Detail Daemon) with ControlNet off.
g = copy.deepcopy(graph)
g["6"]["inputs"]["text"] = POSITIVE
g["7"]["inputs"]["text"] = NEGATIVE
g["30"]["inputs"]["text"] = REGION
g["12"]["inputs"]["strength"] = 0.0
g["5"]["inputs"]["width"], g["5"]["inputs"]["height"] = 896, 1152
for node in g.values():
    if "noise_seed" in node.get("inputs", {}):
        node["inputs"]["noise_seed"] = SEED
    if "seed" in node.get("inputs", {}):
        node["inputs"]["seed"] = SEED
queue(g, f"pt-c-{SEED}")
