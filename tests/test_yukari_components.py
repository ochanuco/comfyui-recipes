"""Component-model invariants: Section/Priority ordering, GENERAL-only
Priority use in stage 1, part-mapping coverage/contiguity, and every pose's
Framing."""

from __future__ import annotations

import unittest

from comfyui_recipes.domain.yukari.components import (
    PART_OF,
    Component,
    Framing,
    Priority,
    Section,
    assemble,
)
from comfyui_recipes.domain.yukari.poses import POSES
from comfyui_recipes.domain.yukari.recipe import PART_NAMES, _components


class AssembleOrderTest(unittest.TestCase):
    def test_sorts_by_section_then_priority(self):
        components = (
            Component("b", Section.GENERAL, Priority.TAIL, "b"),
            Component("a", Section.COUNT, Priority.MAIN, "a"),
            Component("c", Section.GENERAL, Priority.LEAD, "c"),
            Component("d", Section.QUALITY, Priority.MAIN, "d"),
            Component("e", Section.GENERAL, Priority.LEAD, "e"),
        )
        self.assertEqual([c.name for c in assemble(components)],
                         ["d", "a", "c", "e", "b"])

    def test_equal_keys_keep_declaration_order(self):
        components = (
            Component("first", Section.GENERAL, Priority.MAIN, "1"),
            Component("second", Section.GENERAL, Priority.MAIN, "2"),
            Component("third", Section.GENERAL, Priority.MAIN, "3"),
        )
        self.assertEqual([c.name for c in assemble(components)],
                         ["first", "second", "third"])


class StageOnePriorityTest(unittest.TestCase):
    def test_every_general_component_is_main(self):
        for pose in POSES:
            with self.subTest(pose=pose):
                for component in _components(pose):
                    if component.section == Section.GENERAL:
                        self.assertEqual(component.priority, Priority.MAIN,
                                         component.name)


class PartMappingTest(unittest.TestCase):
    def test_every_part_name_is_covered(self):
        self.assertEqual(set(PART_OF.values()), set(PART_NAMES))

    def test_every_declared_component_maps_to_a_known_part(self):
        for pose in POSES:
            for component in _components(pose):
                self.assertIn(component.name, PART_OF, component.name)

    def test_a_parts_components_stay_contiguous(self):
        for pose in POSES:
            with self.subTest(pose=pose):
                parts = [PART_OF[c.name] for c in _components(pose)]
                seen = []
                for part in parts:
                    if not seen or seen[-1] != part:
                        self.assertNotIn(part, seen,
                                         f"{part} split into two runs")
                        seen.append(part)
                self.assertEqual(seen, list(PART_NAMES))


class FramingTest(unittest.TestCase):
    def test_every_pose_has_a_framing(self):
        for pose, spec in POSES.items():
            with self.subTest(pose=pose):
                self.assertIsInstance(spec.framing, Framing)

    def test_framing_assignments(self):
        expected = {
            "cinema": Framing.COWBOY, "coffee": Framing.COWBOY,
            "amae": Framing.COWBOY, "gao": Framing.COWBOY,
            "step": Framing.FULL, "stand": Framing.FULL, "dance": Framing.FULL,
            "bust": Framing.BUST,
        }
        self.assertEqual({pose: spec.framing for pose, spec in POSES.items()},
                         expected)

    def test_place_framing_tags_and_leg_display_are_disjoint_strings(self):
        for pose, spec in POSES.items():
            with self.subTest(pose=pose):
                self.assertIsInstance(spec.scene, str)
                self.assertIsInstance(spec.framing_tags, str)
                self.assertIsInstance(spec.leg_display, str)


if __name__ == "__main__":
    unittest.main()
