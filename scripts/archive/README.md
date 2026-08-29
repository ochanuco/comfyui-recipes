# Ran once, kept as a record

Scripts here each answered one question and were never meant to answer
another. They are not tools and nothing imports them; they are here so the
render they produced can be reproduced, and so the tag weights they tried are
not retried.

They were in `scripts/` and they cost something there. Not disk — attention.
Anything looking for the script that does a thing had thirty-three entry points
to sort through, and half of them were exhausted probes. Moving them out is the
cheapest thing that makes the live surface readable.

Two families:

- `yk_*.py` and `lap_invite.py` — Yukari's design being rebuilt one block at a time, back when it
  lived in the `queue_dq3.py` pipeline. Superseded by `scripts/yukari_recipe.py`,
  which is where the settled answers ended up.
- `style_sweep2.py` … `style_sweep6.py` — the Hamakaze art-style sweeps, one
  variable per file, in order. `docs/render-notes.md` carries what each found.

They import from `scripts/`, so run them from the repo root with that on the
path:

```bash
PYTHONPATH=scripts uv run scripts/archive/yk_layer.py
```

Nothing here is maintained. If one of them is worth running again, that is a
reason to move it back and give it flags, not a reason to fix it in place.
