#!/usr/bin/env python3
"""Hold the delivery identity to a contract.

The delivery identity -- backdrop, purple stroke, acceptance band -- in
`domain/yukari/delivery_style.py` is worn by every delivered picture.
Editing it changes every render this repo has ever approved, so this
fingerprints it from an explicit canonical payload (not from the module
source, so a comment edit does not move it and a value edit always does)
and fails on any change that was not told to `--accept`.

    uv run scripts/delivery_check.py            # check the fingerprint
    uv run scripts/delivery_check.py --accept   # record a change that is meant

When it fails, nothing is broken -- something was changed. Re-run with
--accept to record the new fingerprint into assets/delivery-fingerprint.json,
and write in docs/findings/delivery.md what the look is now.

Exit status is 1 if anything fails, so this can gate a commit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from comfyui_recipes.domain.yukari import delivery_style as d

BASELINE = Path(__file__).resolve().parent.parent / "assets/delivery-fingerprint.json"

# Bumped whenever a field is added to or removed from the payload below --
# a schema change moves the hash even if no tracked value did.
FINGERPRINT_SCHEMA = 4


def delivery_fingerprint() -> str:
    """A hash of the delivery identity, from a canonical payload."""
    payload = json.dumps({
        "schema": FINGERPRINT_SCHEMA,
        "backdrop": d.BACKDROP,
        "stroke": d.STROKE,
        "stroke_width_band": d.STROKE_WIDTH_BAND,
        "white_width_pct": d.WHITE_WIDTH_PCT,
        "sat_band": list(d.SAT_BAND),
        "bg_sat_max": d.BG_SAT_MAX,
        "figure_midtone_v": d.FIGURE_MIDTONE_V,
        "figure_sat_mean_max": d.FIGURE_SAT_MEAN_MAX,
        "figure_sat_p90_max": d.FIGURE_SAT_P90_MAX,
        "figure_light_v": d.FIGURE_LIGHT_V,
        "figure_light_sat_target": d.FIGURE_LIGHT_SAT_TARGET,
        "stroke_cut_eps_pct": d.STROKE_CUT_EPS_PCT,
        "backdrop_spread_max": d.BACKDROP_SPREAD_MAX,
        "palette_windows": [dict(sorted(w.items())) for w in d.PALETTE_WINDOWS],
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def accepted_fingerprint() -> str | None:
    if not BASELINE.exists():
        return None
    return json.loads(BASELINE.read_text(encoding="utf-8")).get("delivery_fingerprint")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--accept", action="store_true",
                    help="record the current fingerprint as accepted, for a "
                         "change that is meant and written down")
    args = ap.parse_args()

    got = delivery_fingerprint()

    if args.accept:
        BASELINE.write_text(
            json.dumps({"delivery_fingerprint": got}, indent=1) + "\n",
            encoding="utf-8")
        print(f"delivery {got}   -> assets/delivery-fingerprint.json")
        print("write in docs/findings/delivery.md what the look is now")
        return

    accepted = accepted_fingerprint()
    if got != accepted:
        print(f"FAIL the delivery identity changed (yukari/delivery_style.py)\n"
              f"     accepted {accepted}, built {got}\n"
              f"     every delivered picture wears this; see --accept",
              file=sys.stderr)
        raise SystemExit(1)
    print(f"ok   delivery style  ({got})")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
