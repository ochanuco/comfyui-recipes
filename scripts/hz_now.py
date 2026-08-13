"""Hamakaze through Yukari's settled recipe -- the earlier port, run backwards.

Putting Yukari onto Hamakaze's ControlNet graph moved her class block and left
her identity behind: the look lived in tags nobody had written down as hers
((realistic) negative, flat colour, the sticker outline, 2000s (style), the eye
block). This is the same move in the other direction, so the interesting part is
what of Yukari stays behind in Hamakaze.

Swapped: the character block, the eye colour in the HOOD tail, and the hood tags
themselves -- she has no hood to put down. Deliberately NOT swapped, because they
are what the question is about:

  LEGWEAR   pale purple thighhighs over black tights, with (lavender tint:1.3).
            Hers is plain black pantyhose. The pale socks and the lavender cast
            are Yukari's and they are also what carries this palette.
  SURFACE   flat colour, white outline, sticker.
  FACE      tareme, large iris, 2000s (style).
  POSE      the double-V, which is not hers either.

Two seeds, since one render has proven repeatedly unable to tell a recipe's
behaviour from a draw.
"""
import json
import sys
import urllib.request

sys.path.insert(0, "/Users/chanu/ghq/github.com/ochanuco/ai-comfyui-env/scripts")
import queue_dq3 as q  # noqa: E402
import yukari_recipe as r  # noqa: E402

HZ = f'{q.CLASSES["hamakaze"]}, {q.FRANCHISE["hamakaze"]}'
assert "hamakaze (kancolle)" in HZ

positive = r.positive("peace")
assert r.CHARACTER in positive and r.HOOD in positive
positive = positive.replace(r.CHARACTER, HZ)
# Her eyes are blue, and the hood tags have nothing to act on.
positive = positive.replace(r.HOOD, "(visible hair:1.2), (blue eyes:1.2)")
assert "yuzuki yukari" not in positive and "rabbit hood" not in positive
assert "purple eyes" not in positive

for seed in (555666777, 111222333):
    graph = r.build("peace", seed, "tmp")
    graph["6"]["inputs"]["text"] = positive
    graph["9"]["inputs"]["filename_prefix"] = f"hznow-{seed}"
    req = urllib.request.Request(
        "http://127.0.0.1:8188/prompt",
        data=json.dumps({"prompt": graph}).encode(),
        headers={"Content-Type": "application/json"},
    )
    print(seed, json.load(urllib.request.urlopen(req))["prompt_id"], flush=True)
