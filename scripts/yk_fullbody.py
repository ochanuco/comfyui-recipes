"""Keep pt-b's line thinness at full body. Resolution against thin-line tags.

Measured first, because the obvious story was wrong: median stroke width is
1.91px in pt-b (1024x1024 portrait), 1.91px in rc-c (1024x1280) and 1.91px in
gl-lounge (1024x1536 full body). The line is not getting thicker. It is drawn at
a fixed pixel width regardless of framing, so at full body a ~230px head carries
the same 1.9px stroke that a ~700px head carries in the portrait, and reads
about three times heavier.

Parity by resolution alone is out of reach -- matching the ratio would need a
frame around 4000px tall, and 1536x2304 already kills VAEEncode on this machine.
1280x1920 is the documented ceiling and buys 1.25x.

The other lever is drawing the line thinner in absolute pixels, which has never
been tested in this configuration. (thin lineart:1.45) cancelled
(black lineart:1.4) once, but the restored prompt has no black lineart tag for
it to fight, so that result does not transfer.

Crossed, one seed, the reference's own pose and legwear so this is her full
design and not a portrait stretched downward:

  fb-a  1024x1536  plain
  fb-b  1024x1536  + (thin lineart:1.3), (fine lines:1.25), (delicate lines:1.2)
  fb-c  1280x1920  plain
  fb-d  1280x1920  + thin-line tags

Read with the same stroke-width measure, plus head height, since the number that
matters is stroke over head and neither term is fixed across these four.
"""
import json
import urllib.request

SEED = 555666777

YK = ("yuzuki yukari, (light purple hair:1.25), (short hair with long locks:1.45), "
      "(very long sidelocks:1.3), sidelocks, (purple eyes:1.25), hair between eyes, "
      "hair ornament, (black hoodie:1.35), open hoodie, (rabbit hood:1.55), "
      "animal hood, long sleeves, drawstring, (purple dress:1.2), short dress, "
      "frills, vocaloid, voiceroid")

# gl-lounge's own pose and legwear, so the comparison is against the render the
# thinness target was taken from rather than a new composition.
POSE = ("(solo:1.5), (yokozuwari:1.35), sitting on floor, legs to the side, "
        "(arms behind head:1.3), (smug:1.35), (half-closed eyes:1.3), full body")
LEGWEAR = ("(sheer black pantyhose:1.5), (see-through pantyhose:1.45), "
           "(skin visible through pantyhose:1.4), (charcoal pantyhose:1.35), "
           "(glossy pantyhose:1.3), (very pale purple thighhighs:1.5), "
           "(white thighhighs:1.2), (lavender tint:1.3), "
           "(thighhighs over pantyhose:1.55)")

BASE = (
    f"best quality, absurdres, 1girl, solo, {YK}, {POSE}, {LEGWEAR}, "
    "(tareme:1.3), (large eyes:1.3), 2000s (style), eyelashes, "
    "(large iris:1.25), thin eyebrows, closed mouth, small mouth, "
    "looking at viewer, "
    "(flat color:1.3), (simple background:1.3), (grey background:1.2), "
    "(white outline:1.6), outline, sticker, "
    "(soft shading:1.3), smooth shading, "
    "(toned legs:1.2), (wide hips:1.3), (thick thighs:1.35), (narrow waist:1.25), "
    "(petite:1.2), (pale skin:1.25), "
    "(hood down:1.5), (hood behind head:1.3), (visible hair:1.2), (purple eyes:1.2)"
)
THIN = "(thin lineart:1.3), (fine lines:1.25), (delicate lines:1.2)"
assert "black lineart" not in BASE  # nothing for THIN to cancel

NEGATIVE = (
    "worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, "
    "extra fingers, extra limbs, watermark, signature, text, (disembodied eye:1.4), "
    "(brown legwear:1.5), brown thighhighs, brown pantyhose, (fishnet:1.4), "
    "(latex:1.45), (rubber:1.45), (leather legwear:1.45), "
    "(upskirt:1.4), panties, (from below:1.35), "
    "(blue legwear:1.5), (blue background:1.5), (blue tint:1.4), "
    "(opaque pantyhose:1.5), (mismatched legwear:1.5), (single thighhigh:1.5), "
    "(hood up:1.5), (hood over head:1.4), "
    "(impasto:1.25), (painterly:1.25), (oil painting (medium):1.2), "
    "(heavy shading:1.2), (detailed shading:1.2), (realistic:1.1), "
    "(huge breasts:1.4), (large breasts:1.25), cleavage"
)

RUNS = [
    ("fb-a", 1024, 1536, BASE),
    ("fb-b", 1024, 1536, f"{BASE}, {THIN}"),
    ("fb-c", 1280, 1920, BASE),
    ("fb-d", 1280, 1920, f"{BASE}, {THIN}"),
]

for name, w, h, positive in RUNS:
    graph = {
        "4": {"class_type": "DiffusersLoader",
              "inputs": {"model_path": "hassaku-il-v22"}},
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"batch_size": 1, "width": w, "height": h}},
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
        "http://127.0.0.1:8188/prompt",
        data=json.dumps({"prompt": graph}).encode(),
        headers={"Content-Type": "application/json"},
    )
    print(name, f"{w}x{h}", json.load(urllib.request.urlopen(req))["prompt_id"], flush=True)
