from __future__ import annotations

import json
import unittest
from pathlib import Path

import costume_check
import yukari_recipe
from yukari_snapshot import snapshot


FIXTURE = Path(__file__).parent / "fixtures/yukari-contract-v1.json"


class YukariContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.expected = json.loads(FIXTURE.read_text())
        cls.actual = snapshot(
            yukari_recipe,
            costume_check.fingerprint(),
            costume_check.delivery_fingerprint(),
            seed=cls.expected["seed"],
            prefix=cls.expected["prefix"],
        )

    def test_inventory_and_records(self) -> None:
        for field in (
            "pose_count",
            "poses",
            "costumes",
            "pose_records_sha256",
            "costume_records_sha256",
        ):
            with self.subTest(field=field):
                self.assertEqual(self.actual[field], self.expected[field])

    def test_prompt_and_delivery_fingerprints(self) -> None:
        for field in ("costume_fingerprint", "delivery_fingerprint"):
            with self.subTest(field=field):
                self.assertEqual(self.actual[field], self.expected[field])

    def test_every_pose_and_costume_graph_contract(self) -> None:
        for costume, expected in self.expected["by_costume"].items():
            for field, digest in expected.items():
                with self.subTest(costume=costume, field=field):
                    self.assertEqual(
                        self.actual["by_costume"][costume][field],
                        digest,
                    )


if __name__ == "__main__":
    unittest.main()
