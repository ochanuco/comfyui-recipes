"""The component model inside the 13 external prompt parts.

`Section` orders the Anima model card's own tag sections; `Priority` orders
components within `Section.GENERAL` only. `assemble` stably sorts a
declaration-ordered component list by `(section, priority)` and joins the
texts; `group_by_part` folds that sorted sequence back into the external
parts named in `recipe.PART_NAMES`, which `patches.py` and the catalog
target. `Framing` names a pose's camera/shot kind.
"""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import NamedTuple


class Section(IntEnum):
    QUALITY = 0
    COUNT = 1
    CHARACTER = 2
    SERIES = 3
    ARTIST = 4
    GENERAL = 5


class Priority(IntEnum):
    LEAD = 0
    MAIN = 1
    TAIL = 2


class Framing(Enum):
    BUST = "bust"
    UPPER = "upper"
    COWBOY = "cowboy"
    FULL = "full"
    LYING = "lying"


class Component(NamedTuple):
    name: str
    section: Section
    priority: Priority
    text: str


# Which external part (a `recipe.PART_NAMES` entry) each component name
# belongs to. A part's components must stay contiguous once `assemble` sorts.
PART_OF: dict[str, str] = {
    "quality": "quality", "count": "quality",
    "character": "identity", "series": "identity", "artist": "identity",
    "identity": "identity",
    "action": "pose",
    "mouth": "mouth",
    "mood": "mood",
    "eye_base": "eyes", "eye_quality": "eyes",
    "gesture": "gesture",
    "costume": "costume", "legwear": "costume",
    "place": "scene", "framing_tags": "scene", "leg_display": "scene",
    "body_build": "body",
    "cutout": "background",
    "face": "face",
    "style": "style",
}


def assemble(components: tuple[Component, ...]) -> tuple[Component, ...]:
    return tuple(sorted(components, key=lambda c: (c.section, c.priority)))


def group_by_part(components: tuple[Component, ...],
                  part_names: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    by_part: dict[str, list[str]] = {name: [] for name in part_names}
    for component in components:
        by_part[PART_OF[component.name]].append(component.text)
    return tuple((name, "".join(by_part[name])) for name in part_names)
