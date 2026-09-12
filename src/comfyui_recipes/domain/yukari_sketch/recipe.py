"""The interpreter: pose and costume records into a prompt pair.

Sketch has no second pass of its own -- like `yukari_anima.recipe`,
`render_spec` refuses `hires`/`denoise` outright rather than silently
ignoring them. The delivery redraw reuses the base prompt verbatim; the
LoRA that gives the base pass its look rides into the redraw through the
graph (see `infrastructure/comfyui/yukari_graph.py`), not through the
prompt.

A pose's face is a declared diff over `FACE` (`face_block`), not a copied
string; `departures`/`lineage` read a pose's edits and `parent` back out as
a tag-level report of what changed and against what.
"""

from __future__ import annotations

import difflib

from ..generation.models import PromptPair, RenderSpec
from ..generation.prompt_lint import tags as prompt_tags
from .costumes import COSTUMES, LEGWEAR_BY_COSTUME, NEGATIVE_BY_COSTUME
from .models import Edit
from .poses import POSES
from .prompt_style import (
    BACKGROUND,
    BODY,
    CFG,
    CHARACTER,
    FACE,
    FINISH,
    GLOSS_BAN,
    HEIGHT,
    IDENTITY,
    LEGWEAR,
    LORA,
    MODEL,
    NEGATIVE,
    PROPORTION,
    QUALITY,
    SAMPLER,
    SCHEDULER,
    STEPS,
    TRIGGER,
    WIDTH,
)


# The order `positive()` joins its blocks in. `patches.py` resolves
# `prompt.positive.<part>` against these names; concatenating the texts of
# `positive_parts()` in order reproduces `positive()` byte for byte.
PART_NAMES = ("quality", "identity", "costume", "pose", "proportion",
              "background", "legwear", "face", "body", "finish")

# The identity vocabulary this recipe can carry, at bare-tag level: hair
# colour/length, sidelocks, eye colour, hair ornament, eye-shape identity and
# the costume's cardigan/hood. `identity_tags()` intersects this with what a
# given pose/costume actually renders, so a costume without a hood (none,
# here) or a pose without `jitome` simply contributes nothing for that slot.
IDENTITY_TAG_NAMES = frozenset({
    "light purple hair", "short hair with long locks", "very long sidelocks",
    "purple eyes", "hair ornament", "tareme", "jitome",
    "black hooded cardigan", "rabbit hood",
})


def _splice(text: str, old: str, new: str) -> str:
    """`str.replace`, except that a needle which is not there is an error.

    A replacement that matches nothing does nothing AND SAYS NOTHING;
    mirrors `domain/yukari/recipe.py::_splice`.
    """
    assert old in text, f"splice needle absent: {old!r}"
    return text.replace(old, new)


def _apply(text: str, edits: tuple[Edit, ...]) -> str:
    for e in edits:
        if e.op == "replace":
            text = _splice(text, e.old, e.new)
        elif e.op == "remove":
            text = _splice(text, e.old, "")
        elif e.op == "prepend":
            text = e.new + text
        elif e.op == "append":
            text = text + e.new
        else:
            raise ValueError(f"unknown op: {e.op!r}")
    return text


def face_block(pose: str) -> str:
    p = POSES[pose]
    if p.face is not None:
        return p.face
    return _apply(FACE, p.face_edits)


def resolved_face(pose: str) -> str | None:
    """The face text a pose actually renders with, or None when it is
    `FACE` unchanged -- what the catalog publishes.
    """
    text = face_block(pose)
    return None if text == FACE else text


def _parts(action: str, costume: str, face: str,
           overrides: dict[str, str]) -> tuple[tuple[str, str], ...]:
    unknown = set(overrides) - set(PART_NAMES)
    assert not unknown, f"part_overrides name no part: {sorted(unknown)}"
    costume_block = COSTUMES[costume]
    legwear = LEGWEAR_BY_COSTUME.get(costume, LEGWEAR)
    values = (QUALITY + TRIGGER, CHARACTER + IDENTITY, costume_block,
              action, PROPORTION, BACKGROUND, legwear, face, BODY, FINISH)
    return tuple((name, overrides.get(name, text))
                 for name, text in zip(PART_NAMES, values))


def positive_parts(pose: str, costume: str | None = None) -> tuple[tuple[str, str], ...]:
    p = POSES[pose]
    name = costume if costume is not None else p.costume
    return _parts(p.action, name, face_block(pose), p.part_overrides)


def positive(pose: str, costume: str | None = None) -> str:
    return "".join(text for _, text in positive_parts(pose, costume))


def identity_tags(pose: str, costume: str | None = None) -> frozenset[str]:
    bare = set(prompt_tags(positive(pose, costume)))
    return frozenset(IDENTITY_TAG_NAMES & bare)


def negative(pose: str, costume: str | None = None) -> str:
    p = POSES[pose]
    name = costume if costume is not None else p.costume
    _ = COSTUMES[name]
    return NEGATIVE + NEGATIVE_BY_COSTUME.get(name, "") + GLOSS_BAN


def refinement_prompt(base: PromptPair) -> PromptPair:
    """The redraw uses the same prompt as the base pass."""
    return base


def render_spec(pose: str, seed: int, prefix: str, hires: int = 0,
                denoise: float | None = None,
                costume: str | None = None,
                layerdiffuse: bool = False) -> RenderSpec:
    if hires:
        raise ValueError("yukari-sketch has no second pass -- hires must be 0")
    if denoise is not None:
        raise ValueError(
            "yukari-sketch has no second pass -- denoise must be None")
    width, height = POSES[pose].canvas or (WIDTH, HEIGHT)
    parts = positive_parts(pose, costume)
    return RenderSpec(
        model_path=MODEL,
        prompts=PromptPair("".join(text for _, text in parts),
                           negative(pose, costume)),
        positive_parts=parts,
        width=width, height=height, seed=seed, steps=STEPS, cfg=CFG,
        sampler_name=SAMPLER, scheduler=SCHEDULER, denoise=1.0,
        filename_prefix=prefix, hires=None, loras=(LORA,),
        layerdiffuse=layerdiffuse)


def _parse_tags(text: str) -> list[tuple[str, str | None]]:
    """(bare name, weight-or-None) for each tag, in the text's own order.

    Kept separate from `prompt_lint.tags`, which strips weights -- a
    departure report needs them to tell a reweight from an untouched tag.
    """
    result = []
    for part in text.split(", "):
        part = part.strip().strip("()")
        if not part:
            continue
        name, sep, weight = part.rpartition(":")
        result.append((name, weight) if sep else (part, None))
    return result


# One diff entry: (kind, name, old weight, new weight). kind is "add",
# "drop", "reweight" or (after `_merge_moved`) "moved".
_DiffEntry = tuple[str, str, "str | None", "str | None"]


def _merge_moved(entries: list[_DiffEntry]) -> list[_DiffEntry]:
    """A tag both dropped and re-added under the same bare name did not
    change identity, only position -- collapse the pair into one `moved`
    entry (or a reweight, if its weight changed too) at the add's slot.
    """
    drop_queues: dict[str, list[int]] = {}
    for i, (kind, name, _old, _new) in enumerate(entries):
        if kind == "drop":
            drop_queues.setdefault(name, []).append(i)
    merged = list(entries)
    consumed: set[int] = set()
    for i, (kind, name, _old, new_w) in enumerate(entries):
        if kind != "add":
            continue
        queue = drop_queues.get(name)
        if not queue:
            continue
        drop_i = queue.pop(0)
        _, _, drop_old_w, _ = entries[drop_i]
        consumed.add(drop_i)
        if drop_old_w == new_w:
            merged[i] = ("moved", name, None, None)
        else:
            merged[i] = ("reweight", name, drop_old_w, new_w)
    return [entry for i, entry in enumerate(merged) if i not in consumed]


def _tag_diff(reference: str, own: str) -> list[str]:
    """One entry per tag that changed, in the order a walk from `reference`
    to `own` visits them: `+tag[:weight]` added, `-tag` dropped, `tag old ->
    new` reweighted, `tag moved` when the same tag was dropped and re-added
    unchanged elsewhere in the text.
    """
    ref_tags = _parse_tags(reference)
    own_tags = _parse_tags(own)
    ref_names = [name for name, _ in ref_tags]
    own_names = [name for name, _ in own_tags]
    matcher = difflib.SequenceMatcher(None, ref_names, own_names, autojunk=False)
    entries: list[_DiffEntry] = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            for (name, old_w), (_, new_w) in zip(ref_tags[i1:i2], own_tags[j1:j2]):
                if old_w != new_w:
                    entries.append(("reweight", name, old_w, new_w))
        else:
            if op in ("delete", "replace"):
                entries.extend(
                    ("drop", name, weight, None) for name, weight in ref_tags[i1:i2])
            if op in ("insert", "replace"):
                entries.extend(
                    ("add", name, None, weight) for name, weight in own_tags[j1:j2])
    changes = []
    for kind, name, old_w, new_w in _merge_moved(entries):
        if kind == "reweight":
            changes.append(f"{name} {old_w or '1.0'} -> {new_w or '1.0'}")
        elif kind == "moved":
            changes.append(f"{name} moved")
        elif kind == "add":
            changes.append(f"+{name}:{new_w}" if new_w else f"+{name}")
        elif kind == "drop":
            changes.append(f"-{name}")
    return changes


def departures(pose: str, costume: str | None = None) -> dict:
    """What `pose` changes relative to its `parent`, or relative to the
    shared blocks when it has none -- a tag-level report of the same edits
    `face_block`/`positive_parts` apply.
    """
    p = POSES[pose]
    own_parts = dict(positive_parts(pose, costume))
    if p.parent is not None:
        reference_parts = dict(positive_parts(p.parent))
    else:
        name = costume if costume is not None else p.costume
        reference_parts = dict(_parts("", name, FACE, {}))
    parts = {}
    for name in PART_NAMES:
        changes = _tag_diff(reference_parts[name], own_parts[name])
        if changes:
            parts[name] = changes
    return {
        "parent": p.parent,
        "face_override": p.face is not None,
        "parts": parts,
    }


def lineage() -> dict[str, dict]:
    return {name: departures(name) for name in POSES}


def plain_request(pose: str, seed: int, costume: str | None = None) -> dict:
    """A request.json v1 payload for `pose` at recipe defaults, no patches."""
    p = POSES[pose]
    resolved_costume = costume if costume is not None else p.costume
    return {
        "schema_version": 1,
        "request": {"count": 1, "instruction": f"plain {pose}",
                    "seeds": [seed]},
        "generation": {"recipe": "yukari-sketch",
                       "parameters": {"pose": pose,
                                      "costume": resolved_costume}},
        "semantic": {"summary": f"plain render of yukari-sketch {pose}: "
                     f"recipe defaults, no patches, seed {seed}"},
    }
