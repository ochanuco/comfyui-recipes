# models

Yukari domain models: one pose is one record, one change is one Edit. The
recipe's domain logic is token order -- a mid-prompt insertion re-rolls
every token after it, and the interpreter in `recipe.py` applies edits in a
fixed global sequence for that reason. Nothing in this file is allowed to
hide that order: an `Edit` says which operation, on which needle, at which
slot, and the record it sits in says why.

## Stage slots

Where an `Edit` lands in the negative's build sequence. Pose edits and
costume edits interleave (a `fitness` `hoops` runs pose guard, knot, pose
limbs, seam, in that order), so the slot is part of the contract: it is the
order the picked renders were drawn in, and moving an edit to another slot
re-rolls the tokens after it. Positive-side edits ignore the stage -- each
targets its own block, and the blocks are joined in one fixed order by
`positive()`.

```python
S_TINT_RELEASE = 10   # sporty/fitness: the blue-tint guard comes out
S_POSE_GUARDS = 20    # pose guard prepends/releases (swelter, tehe, kick...)
S_KNOT = 30           # fitness: tied-shirt guard
S_POSE_LIMBS = 40     # hoops: the extra-limb trio (after the knot -- drawn so)
S_SEAM = 50           # fitness: cameltoe guard
S_POSE_LATE = 60      # winded's prepends (after the seam -- drawn so)
S_MIDRIFF = 70        # fitness: the midriff tail rewrite
# -- head framings stop here; everything below follows the legwear ban --
S_BARE_LEGS = 80      # roomwear: the settled costume's pantyhose, banned
S_FABRIC = 90         # fitness: stripe and taut-cloth guards
S_POSE_SCENE = 100    # situp's wardrobe/posture guards
S_POSE_SHOES = 110    # stand's footwear-colour tail
S_CROWD = 120         # doze: the crowd ban, in front of everything
```

Each comment names the costume or pose that owns the slot and, where
relevant, why it must run before or after a neighbouring slot ("after the
knot -- drawn so", "after the seam -- drawn so") -- the ordering itself was
fixed by the sequence the picked renders were actually drawn in, not chosen
abstractly.

## Edit

One explicit string operation against one block.

```python
@dataclass(frozen=True)
class Edit:
    op: str                  # replace | remove | prepend | append | replace_if_present
    old: str = ""
    new: str = ""
    gate: str | None = None  # dressed | shod | default_or_roomwear
    stage: int = 0           # negative-pipeline slot; 0 for positive-side edits
    why: str = ""            # one line; the story lives in docs/render-notes.md
```

`replace`/`remove` assert the needle is present -- a replacement that
matches nothing does nothing AND SAYS NOTHING, and this recipe has paid for
that twice (see `costumes.md`'s skirt-guard history and `prompt_style.md`'s
negative-tail history for two of the times). `replace_if_present` is the
one deliberate exception (see the fitness x swelter midriff release in
`costumes.md`). `gate` skips the edit for costumes it does not apply to,
which is the honest way to say "this costume has no such garment".

## Pose

Everything one pose owns, in one place.

```python
@dataclass(frozen=True)
class Pose:
    prompt: str
    size: tuple[int, int]
    framing: str = "full"             # full | head (head crops above the legs)
    open_mouth: bool = False          # drop FACE's `closed mouth`
    own_eyes: bool = False            # drop FACE's RESTING_EYES pair
    face_edits: tuple[Edit, ...] = ()
    body_edits: tuple[Edit, ...] = ()
    character_edits: tuple[Edit, ...] = ()
    legwear_edits: tuple[Edit, ...] = ()
    pose_block_edits: tuple[Edit, ...] = ()
    surface_edits: tuple[Edit, ...] = ()
    hood_suffix: str = ""             # appended to the costume's hood block
    tail_edits: tuple[Edit, ...] = () # against the fully joined positive
    negative_base: tuple[Edit, ...] = ()   # against NEGATIVE itself
    negative_edits: tuple[Edit, ...] = ()  # staged; merged with the costume's
    paint_finish: bool = False        # 174ce1dc's finish: no THIN + paint guard
    hires_negative: str = ""          # prepended to the pass-2 negative
    hires_positive: str = ""          # spliced after the pose block, pass 2 only
    hires_finish: str = ""            # appended at the very end, pass 2 only
    hires_print: tuple[int, float] | None = None  # (size, denoise) for --hires
    settled_seed: int | None = None
```

`prompt` is the pose block, verbatim from `POSES` -- the strings the picked
renders were drawn with, byte for byte. The edit tuples are each pose's
declared departures from the shared blocks, applied by `recipe.py` in its
fixed order; everything a pose does NOT declare comes from the shared style
and costume blocks unchanged. `paint_finish`'s reference to `174ce1dc` and
the note on `SHADE_BAN`/paint guards is the same finish documented in
`prompt_style.md` under `HIRES_NEGATIVE_PAINT` and in the per-pose docs
under `swelter`/`straw`.
