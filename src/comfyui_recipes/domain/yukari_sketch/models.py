"""Yukari-sketch domain models: a pose's face is a declared diff over FACE.

`Edit` mirrors `domain/yukari/models.py` -- `replace`/`remove` assert their
needle is present, so a departure that stops applying says so instead of
silently vanishing. `Pose.parent` names the pose this one was derived from;
`recipe.departures` reads it to report what changed and against what.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Edit:
    op: str          # replace | remove | prepend | append
    old: str = ""
    new: str = ""


@dataclass(frozen=True)
class Pose:
    action: str
    costume: str = "default"
    face_edits: tuple[Edit, ...] = ()
    face: str | None = None      # full override; mutually exclusive with face_edits
    parent: str | None = None    # the pose this one was derived from
    canvas: tuple[int, int] | None = None
    # Shared blocks this pose renders with its own text instead, by part
    # name (`recipe.PART_NAMES`); "" leaves the part empty.
    part_overrides: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.face is not None and self.face_edits:
            raise ValueError(
                "Pose.face (full override) and Pose.face_edits are mutually "
                "exclusive")
        if {"pose", "face"} & set(self.part_overrides):
            raise ValueError(
                "Pose.part_overrides cannot name pose or face -- those are "
                "Pose.action and Pose.face_edits")
