#!/usr/bin/env python3
"""Hold the costume to a contract, and say which pose broke it.

The costume does not survive a change of pose on its own. Every pose in
`yukari_recipe.py` has needed splices to keep the same clothes -- `boss` five,
`nape` two, `prone` four -- because tags are one argument about the whole
picture and a new pose re-weights all of them. A LoRA would end that; nothing on
the worker can load one yet (`LoraLoader` returns an empty list). Until then the
next best thing is not to prevent drift but to **fail on it**.

    uv run scripts/costume_check.py                     # every pose, prompt side
    uv run scripts/costume_check.py --pose prone
    uv run scripts/costume_check.py --palette out/*.png # render side

**Prompt side.** Each pose's prompt is rebuilt from the shared blocks and
compared, tag by tag, against what `positive()` actually returns. Every
difference has to be named in `EXCEPTIONS` below with a reason. An undeclared
one is an error -- which is the whole point: `positive()` is a stack of
`.replace()` calls that have grown one session at a time and do not know about
each other, and this is the only place they are written down together.

Adding an exception is cheap and deliberate. Silently changing a garment is not.

**Render side.** `--palette` measures how much of the figure each costume colour
covers and compares it against a baseline recorded from an approved render of
the same pose.

Absolute floors were tried first and are useless: with tolerances wide enough to
catch a shaded garment, hair satisfies "pale sock" and shading satisfies
"legwear grey", and three renders this project had already rejected all passed.
What separates them is the *share* against a render that was accepted -- the
bare-legged one has 9% pale sock against the accepted 31%, a third. So the check
is relative, per pose, and a baseline is part of accepting a render.

It measures colour presence, not garment identity. A grey sock would pass as
grey tights. It is a smoke alarm, not an inspector.

Exit status is 1 if anything fails, so this can gate a commit.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import hashlib
import json

import numpy as np
from PIL import Image

import yukari_recipe as yk

HEAD = "best quality, absurdres, 1girl, solo"

# The costume itself, fingerprinted. Per-pose drift is only half the problem:
# editing CHARACTER or LEGWEAR changes the clothes in every pose at once, and
# comparing poses against the blocks cannot see that, because the blocks are
# what it compares against. So the blocks are hashed here.
#
# When this fails, nothing is broken -- something was changed. Re-run with
# `--accept` to print the new value, paste it in, and write down in
# docs/render-notes.md what the costume is now. That is the whole mechanism:
# it does not stop a change, it stops an *unrecorded* one.
COSTUME_BLOCKS = ("character", "legwear", "body", "face", "surface", "hood", "thin")
COSTUME_FINGERPRINT = "ccf785bcfa21dbdc"


def tags(text: str) -> list[str]:
    return [t.strip() for t in text.split(",") if t.strip()]


def canonical(pose: str) -> list[str]:
    """The costume as the shared blocks define it, before any pose splices."""
    return (tags(HEAD) + tags(yk.CHARACTER) + tags(yk.POSES[pose])
            + tags(yk.LEGWEAR) + tags(yk.FACE) + tags(yk.SURFACE)
            + tags(yk.BODY) + tags(yk.HOOD) + tags(yk.THIN))


# Every declared departure from the shared blocks, with the reason it was paid
# for. `added` and `removed` are exact tags. The reasons are one line each; the
# measurements behind them are in docs/render-notes.md.
EXCEPTIONS: dict[str, list[dict]] = {
    "boss": [
        {"removed": ["(petite:1.2)"], "added": ["(mature female:1.35)"],
         "why": "the pose exists to read grown up; one substitution in one slot"},
        {"added": ["(small breasts:1.35)"],
         "why": "`mature female` brings a chest with it and the negative could "
                "not finish the job alone"},
        {"removed": ["(oversized shirt:1.3)"],
         "why": "`mature female` recruits it into a pale button-front shirt "
                "dress; dropping it restores the purple bodice"},
        {"removed": ["(frills:0.85)"], "added": ["(frills:1.25)"],
         "why": "below 1 in a prompt where everything is 1.3+ means absent"},
        {"added": ["(off shoulder:1.3)"],
         "why": "the approved render has the coat off her shoulders; it costs "
                "the rabbit hood, deliberately"},
        {"added": ["(criss-cross halter:1.45)"],
         "why": "the dress's own straps, affordable here because the coat is "
                "already off the shoulders"},
        {"added": ["(ribbed legwear:1.35)"],
         "why": "the rib is what her thighhighs are; ADDED, not substituted -- "
                "substituting it removed the tights on every seed"},
    ],
    "nape": [
        {"added": ["(halterneck:1.45)", "(black straps:1.35)"],
         "why": "the bow this pose is looking at; documented as costing every "
                "other pose its coat, which is why it is spliced"},
        {"added": ["(off shoulder:1.25)"],
         "why": "what uncovers the nape; rides with HOOD rather than joining "
                "the pose block, which is already at eight tags"},
        {"removed": ["looking at viewer"],
         "why": "she is turned away; the instruction has no referent and either "
                "argues with the pose or spins her around"},
    ],
    "prone": [
        {"removed": ["(grey pantyhose:1.45)"], "added": ["(pale purple pantyhose:1.45)"],
         "why": "one legwear garment seen from behind; the colour has to travel "
                "with the surviving one or the legs come out taupe"},
        {"removed": ["(opaque pantyhose:1.3)"], "added": ["(opaque pantyhose:1.5)"],
         "why": "the smooth face belongs to the tights alone now"},
        {"removed": ["(very pale purple thighhighs:1.5)"], "added": ["(white kneehighs:1.45)"],
         "why": "the sock is drawn by region instead; this slot keeps the token "
                "count the composition is holding on to"},
        {"removed": ["(white thighhighs:1.2)"], "added": ["(kneehighs:1.25)"],
         "why": "same slot-keeping. See scripts/yk_prone_legwear.py"},
        {"removed": ["(thighhighs over pantyhose:1.55)"], "added": ["(thighhighs over pantyhose:0.6)"],
         "why": "two layers from behind read as shorts over stockings"},
        {"removed": ["(wide hips:1.3)", "(thick thighs:1.35)"],
         "added": ["(wide hips:1.0)", "(thick thighs:1.05)"],
         "why": "BODY was settled on poses seen from the front or the side; "
                "from behind and foreshortened the same tags read as bulk"},
    ],
    "portrait": [
        # `(pale skin:1.25)` is the one tag of BODY that stays -- the crop is
        # above the legs and the hips but not above her skin -- so it is not
        # listed as removed and not listed as added either.
        {"removed": (tags(yk.LEGWEAR)
                     + [t for t in tags(yk.BODY) if t != "(pale skin:1.25)"]
                     + tags(yk.THIN)),
         "why": "the crop is above all of it, and naming what is out of frame "
                "is what invites it back in"},
    ],
    "yawn": [
        {"removed": ["closed mouth"], "why": "a yawn needs the mouth open"},
    ],
    "fall": [
        {"removed": ["closed mouth"], "why": "she is shouting"},
    ],
}

# Every colour the costume is made of, measured off approved renders, with the
# per-channel tolerance that isolates it.
PALETTE = [
    ("dress purple", (183, 149, 211), 34),
    ("coat black", (62, 56, 66), 30),
    ("hood lining pink", (188, 97, 106), 45),
    ("skin", (253, 242, 232), 16),
    ("hair light purple", (222, 214, 238), 22),
    ("legwear grey", (135, 127, 128), 26),
    ("pale sock", (243, 236, 250), 16),
]

BASELINE = REPO_ASSETS = Path(__file__).resolve().parent.parent / "assets/costume-baseline.json"

# How far a share may move from its baseline before it is a different costume.
# Loose on purpose, and measured that way: two renders this project accepted for
# the same pose differ by 0.49x on skin alone, because one has the dress
# covering more of her. The failures worth catching are garments disappearing --
# the bare-legged arm reads 0.30x on the pale sock -- so the band is set below
# the disagreement between accepted renders and above nothing else.
LOW, HIGH = 0.4, 2.5


def fingerprint() -> str:
    """A hash of the shared blocks, in a fixed order."""
    blocks = [getattr(yk, name.upper()) for name in COSTUME_BLOCKS]
    return hashlib.sha256("\n".join(blocks).encode()).hexdigest()[:16]


def check_prompt(pose: str) -> list[str]:
    """Undeclared differences between the contract and what the recipe builds."""
    canon, actual = canonical(pose), tags(yk.positive(pose))
    added = [t for t in actual if t not in canon]
    removed = [t for t in canon if t not in actual]

    declared_added, declared_removed = [], []
    for exc in EXCEPTIONS.get(pose, []):
        declared_added += exc.get("added", [])
        declared_removed += exc.get("removed", [])

    problems = []
    for tag in added:
        if tag not in declared_added:
            problems.append(f"undeclared addition: {tag}")
    for tag in removed:
        if tag not in declared_removed:
            problems.append(f"undeclared removal: {tag}")
    # A declaration that no longer describes the code is just as wrong: it means
    # the reason written down belongs to a prompt that is no longer built.
    for tag in declared_added:
        if tag not in added:
            problems.append(f"declared addition not present: {tag}")
    for tag in declared_removed:
        if tag not in removed:
            problems.append(f"declared removal not applied: {tag}")
    return problems


def profile(path: Path) -> dict[str, float]:
    """What share of the figure each costume colour covers."""
    img = np.asarray(Image.open(path).convert("RGB"), np.int16)
    # The backdrop is whatever fills the corners; the recipe does not control it
    # and it moves between renders, so it is measured rather than assumed.
    corners = np.concatenate([img[:24, :24].reshape(-1, 3), img[:24, -24:].reshape(-1, 3),
                              img[-24:, :24].reshape(-1, 3), img[-24:, -24:].reshape(-1, 3)])
    backdrop = np.median(corners, axis=0)
    figure = np.abs(img - backdrop).max(axis=2) > 20
    total = max(int(figure.sum()), 1)

    return {name: float(((np.abs(img - np.array(colour)).max(axis=2) < tol)
                         & figure).sum()) / total
            for name, colour, tol in PALETTE}


def check_palette(path: Path, pose: str, base: dict) -> list[str]:
    got = profile(path)
    if pose not in base:
        print(f"  no baseline for {pose}; --record it from an accepted render")
        for name, share in got.items():
            print(f"      {name:18s} {share:6.2%}")
        return []

    problems = []
    for name, share in got.items():
        want = base[pose].get(name)
        if want is None or want == 0:
            continue
        ratio = share / want
        ok = LOW <= ratio <= HIGH
        print(f"  {'ok ' if ok else 'FAIL'} {name:18s} {share:6.2%} "
              f"({ratio:4.2f}x of {want:.2%})")
        if not ok:
            problems.append(f"{name} is {ratio:.2f}x its baseline")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pose", action="append", default=[],
                    help="check one pose instead of all of them")
    ap.add_argument("--palette", type=Path, nargs="*", default=None,
                    help="check rendered images against the costume's colours")
    ap.add_argument("--record", action="store_true",
                    help="write the given images' profiles into the baseline as "
                         "the accepted look for --pose")
    ap.add_argument("--accept", action="store_true",
                    help="print the current fingerprint, for a change that is "
                         "meant and written down")
    args = ap.parse_args()

    if args.accept:
        print(fingerprint())
        return

    failed = False

    if args.palette is not None:
        base = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
        if args.record:
            if len(args.pose) != 1:
                raise SystemExit("--record needs exactly one --pose")
            base[args.pose[0]] = profile(args.palette[0])
            BASELINE.write_text(json.dumps(base, indent=1, sort_keys=True) + "\n")
            print(f"recorded {args.pose[0]} from {args.palette[0].name}")
            return
        pose = args.pose[0] if args.pose else "prone"
        for path in args.palette:
            print(f"{path.name}  [{pose}]")
            problems = check_palette(path, pose, base)
            failed |= bool(problems)
        raise SystemExit(1 if failed else 0)

    got = fingerprint()
    if got != COSTUME_FINGERPRINT:
        failed = True
        print(f"FAIL the costume blocks themselves changed\n"
              f"     contract {COSTUME_FINGERPRINT}, built {got}\n"
              f"     every pose wears this; see --accept")
    else:
        print(f"ok   costume blocks  ({got})")

    for pose in args.pose or sorted(yk.POSES):
        problems = check_prompt(pose)
        count = len(EXCEPTIONS.get(pose, []))
        if problems:
            failed = True
            print(f"FAIL {pose}  ({count} declared)")
            for p in problems:
                print(f"     {p}")
        else:
            print(f"ok   {pose}  ({count} declared)")

    if failed:
        print("\nAn undeclared change is a costume change nobody wrote down.",
              file=sys.stderr)
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
