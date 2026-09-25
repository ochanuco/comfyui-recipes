# Archive

`render-notes/` is the measurement log as it stood when it was split, cut at
section boundaries into six files by date. The text is unchanged apart from
one relative link, and `tests/test_docs_budget.py` pins each file's hash.

It covers retired characters, retired checkpoints and retired tooling
alongside what still holds. What still holds is in `docs/findings/`, each
line pointing back here as `(a<n> §<heading prefix>)`.

Do not open these files whole (~150k tokens together). Search them:

```bash
uv run scripts/atlas.py find "<regex>"     # matching lines, with file:line and heading
uv run scripts/atlas.py notes "<regex>"    # whole sections whose heading matches
```
