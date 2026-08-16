"""Draw the strand line back in, on the restored design rather than the port.

The earlier attempt (hl-a/b/c) raised the same weights and made the hair flatter,
but it ran at ControlNet 0.35 over a Hamakaze lineart, which was holding the hair
whatever the prompt said. This is a different regime: plain KSampler, flat
colour, no ControlNet, and the design is now the reference's. Whether the tags
work here is genuinely untested -- the previous null result does not carry over.

Built on pt-b, the 1024x1024 cell that framed correctly.

  hs-a  + (detailed hair:1.4), (defined hair strands:1.5), (hair strand outline:1.4)
  hs-b  hs-a + (black lineart:1.4), (defined lines:1.3), (crisp lines:1.25)
  hs-c  hs-b + (hair strands:1.4), (clumped hair strands:1.3)

(flat color:1.3), (soft shading:1.3), smooth shading stay, and (heavy shading),
(detailed shading) stay negative. The ask is line, not tonal modelling -- if the
hair only gains depth through shading, that is a failure of this round, not a
partial success.

rabbit print comes out. It put a rabbit decal on her cheek in pt-b by pairing
with sticker, which is there for the white outline idiom and is worth keeping.
"""
import json
import urllib.request

from comfy_host import base_url

SEED = 555666777
W = H = 1024

YK = ("yuzuki yukari, (light purple hair:1.25), (short hair with long locks:1.45), "
      "(very long sidelocks:1.3), sidelocks, (purple eyes:1.25), hair between eyes, "
      "hair ornament, (black hoodie:1.35), open hoodie, (rabbit hood:1.55), "
      "animal hood, long sleeves, drawstring, (purple dress:1.2), short dress, "
      "frills, vocaloid, voiceroid")
assert "rabbit print" not in YK

BASE = (
    "best quality, absurdres, 1girl, solo, "
    f"{YK}, "
    "(solo:1.5), (portrait:1.5), (head and shoulders:1.4), (close-up:1.2), "
    "(face focus:1.3), looking at viewer, "
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

STRAND = "(detailed hair:1.4), (defined hair strands:1.5), (hair strand outline:1.4)"
LINE = "(black lineart:1.4), (defined lines:1.3), (crisp lines:1.25)"
CLUMP = "(hair strands:1.4), (clumped hair strands:1.3)"

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

RUNS = [
    ("hs-a", f"{BASE}, {STRAND}"),
    ("hs-b", f"{BASE}, {STRAND}, {LINE}"),
    ("hs-c", f"{BASE}, {STRAND}, {LINE}, {CLUMP}"),
]

for name, positive in RUNS:
    graph = {
        "4": {"class_type": "DiffusersLoader",
              "inputs": {"model_path": "hassaku-il-v22"}},
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"batch_size": 1, "width": W, "height": H}},
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["4", 1], "text": positive}},
        "7": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["4", 1], "text": NEGATIVE}},
        "3": {"class_type": "KSampler", "inputs": {
            "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["5", 0], "seed": SEED, "steps": 30, "cfg": 5.0,
            "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode",
              "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0], "filename_prefix": f"{name}-{SEED}"}},
    }
    req = urllib.request.Request(
        f"{base_url()}/prompt",
        data=json.dumps({"prompt": graph}).encode(),
        headers={"Content-Type": "application/json"},
    )
    print(name, json.load(urllib.request.urlopen(req))["prompt_id"], flush=True)
