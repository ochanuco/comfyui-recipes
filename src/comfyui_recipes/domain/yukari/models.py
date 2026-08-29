"""Yukari domain models: one pose is one record, one change is one Edit.

The recipe's domain logic is token order -- a mid-prompt insertion re-rolls
every token after it, and the interpreter in `recipe.py` applies edits in a
fixed global sequence for that reason. Nothing here is allowed to hide that
order: an Edit says which operation, on which needle, at which slot, and the
record it sits in says why.
"""

from __future__ import annotations

from dataclasses import dataclass

# Where an Edit lands in the negative's build sequence. Pose edits and costume
# edits interleave (a fitness `hoops` runs pose guard, knot, pose limbs, seam,
# in that order), so the slot is part of the contract: it is the order the
# picked renders were drawn in, and moving an edit to another slot re-rolls
# the tokens after it. Positive-side edits ignore the stage -- each targets
# its own block, and the blocks are joined in one fixed order by `positive()`.
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


@dataclass(frozen=True)
class Edit:
    """One explicit string operation against one block.

    `replace`/`remove` assert the needle is present -- a replacement that
    matches nothing does nothing AND SAYS NOTHING, and this recipe has paid
    for that twice. `replace_if_present` is the one deliberate exception
    (see fitness x swelter's midriff release). `gate` skips the edit for
    costumes it does not apply to, which is the honest way to say "this
    costume has no such garment".
    """

    op: str                  # replace | remove | prepend | append | replace_if_present
    old: str = ""
    new: str = ""
    gate: str | None = None  # dressed | shod | default_or_roomwear
    stage: int = 0           # negative-pipeline slot; 0 for positive-side edits
    why: str = ""            # one line; the story lives in docs/render-notes.md


@dataclass(frozen=True)
class Pose:
    """Everything one pose owns, in one place.

    `prompt` is the pose block (verbatim from POSES). The edit tuples are the
    pose's declared departures from the shared blocks, applied by `recipe.py`
    in its fixed order. Everything a pose does NOT declare comes from the
    shared style and costume blocks unchanged.
    """

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
