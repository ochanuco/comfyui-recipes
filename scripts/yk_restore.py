"""Put Yukari's design back to gl-lounge-555666777 (38918ed3) by prompt, not by reset.

The port onto the Hamakaze graph kept her class block and dropped everything
else, and "everything else" turned out to be where her look lived. Three tags
are outright sign-flipped against the reference:

    realistic     reference: NEGATIVE (realistic:1.1)   port: POSITIVE (realistic:1.3)
    shading       reference: (flat color:1.3), (soft shading:1.3), smooth shading,
                             with (heavy shading:1.2), (detailed shading:1.2) negative
                  port:      (cel shading:1.45), (sharp shadow edges:1.35),
                             (two-tone shading:1.3)
    hood          reference: (rabbit hood:1.55) KEPT, pushed down with
                             (hood down:1.5), (hood behind head:1.3), and
                             (hood up:1.5) negative
                  port:      hood up; and hd-yk deleted the rabbit hood entirely,
                             which was never what the reference does

Also missing from the port: 2000s (style), the sticker outline
((white outline:1.6), outline, sticker), the eye block, and the body block.

Restored here in full. Deliberately NOT restored: the hair-line tags
((defined hair strands), (hair strand outline), (black lineart)) that the port
added and the reference never had. Those are the next round's subject, and
leaving them out means the design result is not confounded by them.

Three renders separate prompt from machinery, one seed (the reference's own):

  rc-a  restored prompt, ControlNet 0.35, Detail Daemon on
  rc-b  restored prompt, ControlNet 0.00, Detail Daemon on
  rc-c  restored prompt, plain KSampler -- no ControlNet, no regional
        conditioning, no Detail Daemon. This is 38918ed3's own recipe at this
        framing, and it is the anchor the other two are read against.

Framing stays (upper body:1.4). The reference is a full-body yokozuwari, so this
is not a reproduction of it -- it is her design at the port's framing.
"""
import copy
import json
import sys
import urllib.request

sys.path.insert(0, "REPO_ROOT/scripts")
import queue_dq3 as q  # noqa: E402

JOB = "7219d431-c44f-4c05-be94-c8330b7d0eef"
SEED = 555666777
W, H = 1024, 1280

hist = json.load(urllib.request.urlopen(f"http://127.0.0.1:8188/history/{JOB}"))
graph = hist[JOB]["prompt"][2]

# Hood stays on her and goes down -- the reference's own construction.
YK = f'{q.CLASSES["yukari"]}, {q.FRANCHISE["yukari"]}'
assert "(rabbit hood:1.55)" in YK

POSITIVE = (
    "best quality, absurdres, 1girl, solo, "
    f"{YK}, "
    "(solo:1.5), (upper body:1.4), looking at viewer, "
    "(smug:1.35), (half-closed eyes:1.3), "
    # eye/style block from the reference, verbatim
    "(tareme:1.3), (large eyes:1.3), 2000s (style), eyelashes, "
    "(large iris:1.25), thin eyebrows, closed mouth, small mouth, "
    # flat paint, not cel-with-hard-edges
    "(flat color:1.3), (simple background:1.3), (grey background:1.2), "
    "(white outline:1.6), outline, sticker, "
    "(soft shading:1.3), smooth shading, "
    # body block
    "(wide hips:1.3), (thick thighs:1.35), (narrow waist:1.25), (petite:1.2), "
    "(pale skin:1.25), "
    # hood down, hood kept
    "(hood down:1.5), (hood behind head:1.3), (visible hair:1.2), "
    "(purple eyes:1.2)"
)

NEGATIVE = (
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text, "
    "(disembodied eye:1.4), "
    "(hood up:1.5), (hood over head:1.4), "
    "(impasto:1.25), (painterly:1.25), (oil painting (medium):1.2), "
    "(heavy shading:1.2), (detailed shading:1.2), (realistic:1.1), "
    "(huge breasts:1.4), (large breasts:1.25), cleavage"
)

assert "realistic" not in POSITIVE and "(realistic:1.1)" in NEGATIVE
assert "cel shading" not in POSITIVE and "sharp shadow edges" not in POSITIVE
assert "hair strand" not in POSITIVE and "black lineart" not in POSITIVE

# Hair region keeps only what identifies her hairstyle; no line push this round.
REGION = ("(short hair with long locks:1.45), (very long sidelocks:1.35), "
          "sidelocks, (hair between eyes:1.3), hair ornament")


def queue(g: dict, name: str) -> None:
    for node in g.values():
        if node["class_type"] == "SaveImage":
            node["inputs"]["filename_prefix"] = f"{name}-{SEED}"
    req = urllib.request.Request(
        "http://127.0.0.1:8188/prompt",
        data=json.dumps({"prompt": g}).encode(),
        headers={"Content-Type": "application/json"},
    )
    print(name, json.load(urllib.request.urlopen(req))["prompt_id"], flush=True)


for name, strength in [("rc-a", 0.35), ("rc-b", 0.0)]:
    g = copy.deepcopy(graph)
    g["6"]["inputs"]["text"] = POSITIVE
    g["7"]["inputs"]["text"] = NEGATIVE
    g["30"]["inputs"]["text"] = REGION
    g["12"]["inputs"]["strength"] = strength
    for node in g.values():
        if "noise_seed" in node.get("inputs", {}):
            node["inputs"]["noise_seed"] = SEED
        if "seed" in node.get("inputs", {}):
            node["inputs"]["seed"] = SEED
    queue(g, name)

# rc-c: the reference's own machinery, rebuilt rather than pruned out of the
# port -- fewer ways to leave a stray node attached.
plain = {
    "4": {"class_type": "DiffusersLoader",
          "inputs": {"model_path": "hassaku-il-v22"}},
    "5": {"class_type": "EmptyLatentImage",
          "inputs": {"batch_size": 1, "width": W, "height": H}},
    "6": {"class_type": "CLIPTextEncode",
          "inputs": {"clip": ["4", 1], "text": POSITIVE}},
    "7": {"class_type": "CLIPTextEncode",
          "inputs": {"clip": ["4", 1], "text": NEGATIVE}},
    "3": {"class_type": "KSampler", "inputs": {
        "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
        "latent_image": ["5", 0], "seed": SEED, "steps": 30, "cfg": 5.0,
        "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
    "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0],
                                                "filename_prefix": "rc-c"}},
}
queue(plain, "rc-c")
