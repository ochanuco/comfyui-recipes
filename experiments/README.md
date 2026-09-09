# Experiment records

Machine-readable observations extracted from the historical comment blocks of
the pose recipes. One JSON object per line (JSONL), one observation per
record, under `experiments/<character>/<pose>.jsonl`.

## Schema

```json
{
  "character": "yukari",
  "pose": "<pose key>",
  "seed": 737373737,
  "render_id": "b393e171",
  "prompt_id": "3394c4bb",
  "parameter": "<the tag/weight/setting that was varied>",
  "value": "<what was tried: number, string, or tag string>",
  "outcome": "accepted",
  "reason": "<what was observed, one sentence>",
  "recipe": "queue_dq3",
  "created_at": "2026-08-19"
}
```

Every key other than `character`, `pose`, `parameter`, `value`, `outcome` and
`reason` is optional and appears only when the source comment actually states
it. Nothing here is guessed, backfilled, or inferred: no null placeholders,
no invented seeds or dates, no model field unless a checkpoint was named.

`recipe` is present only on records attributed to the older `queue_dq3`
recipe; its absence means the current recipe.

## Outcome vocabulary

- `accepted` -- the tried value was picked, settled on, kept, or won a
  head-to-head comparison.
- `rejected` -- the tried value failed, drew a defect, lost a sweep, or was
  withdrawn.
- `inconclusive` -- a null or unchanged measurement, "measured the same",
  a retracted hypothesis, or a result whose earlier conclusion did not
  survive being re-measured.

## Scoping caveat

Every `reason` describes an observation made under the stated pose, seed,
tag block and canvas -- not a universal claim about a tag. A finding like
"under `boss`'s block, `smug` at 1.4 read as gloating" says nothing about
`smug` at 1.4 anywhere else in this project. Treat these records as data
points for a specific past experiment, not as standing rules; the pose
recipe's own comments are the current-state rules.

## Append-only policy

Research logs are append-only: once a record is written it is not edited or
deleted, even when a later experiment contradicts or retracts it -- the
retraction becomes its own record instead (see the `inconclusive` entries
that reference an earlier `accepted`/`rejected` record on the same
parameter). Code comments, by contrast, are current-state-only: they
describe the prompt as it stands today, not its history. This directory is
the history; the source files are the present tense.

## chimera sync

An A/B round with arms and a chimera Batch is recorded as a chimera
Experiment/Run rather than a JSONL record here; a plain observation still
appends to the JSONL as above. This directory stays the source of truth --
chimera holds a derived, queryable index kept in sync by
`scripts/observation_sync.py`. The chimera-side contract is
`docs/domain-model.md` "Observation" and `docs/api.md` "Observation" in the
chimera repository.

`choza.jsonl` predates that split and holds arms rather than observations.
Its 13 arms with a Batch are now chimera Experiment `7q1hnr`'s Runs, and its
4 cross-render analyses are Observations under `repin` and `delivery`. The
file stays as written -- the append-only policy applies to it as much as to
any other, and the round's reasoning only reads in order. The sync skips it,
so those 17 records reach chimera through the Experiment, not through
`observation_sync.py`.

## Module-level records

Not every history is a pose's history. `costumes.py`, `prompt_style.py`,
`delivery_style.py` and `recipe.py` hold module-wide observations --
sweeps, weights, and measurements that apply across poses rather than to
one of them. Their records use `"component": "<module name>"` in place of
(or alongside, when a record also names the pose it was measured under)
`"pose"`, everything else following the same schema. Added under this
scheme: `costumes.jsonl`, `prompt_style.jsonl`, `delivery_style.jsonl` and
`recipe.jsonl`. The narrative reasoning for each of these modules lives in
`docs/yukari/<module>.md`, matching `docs/poses/yukari/<pose>.md`.
