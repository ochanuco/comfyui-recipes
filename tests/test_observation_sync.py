from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import observation_sync

REPO_ROOT = Path(__file__).resolve().parent.parent


class ObservationSyncTest(unittest.TestCase):
    def test_build_files_matches_the_real_tree(self):
        files = observation_sync.build_files(REPO_ROOT)

        jsonl_paths = sorted(REPO_ROOT.glob("experiments/**/*.jsonl"))
        self.assertEqual(len(files), len(jsonl_paths))

        non_blank_lines = 0
        for path in jsonl_paths:
            non_blank_lines += sum(
                1 for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip())
        total_records = sum(len(file["records"]) for file in files)
        self.assertEqual(total_records, non_blank_lines)
        self.assertEqual(
            total_records, sum(len(file["records"]) for file in files))

    def test_line_numbers_are_physical(self):
        files = observation_sync.build_files(REPO_ROOT)
        target = next(
            file for file in files
            if file["path"] == "experiments/yukari/prompt_style.jsonl")
        raw_lines = (REPO_ROOT / target["path"]).read_text(
            encoding="utf-8").splitlines()

        for entry in target["records"]:
            self.assertEqual(
                json.loads(raw_lines[entry["line"] - 1]), entry["record"])

    def test_override_records_get_prompt_style_component(self):
        files = observation_sync.build_files(REPO_ROOT)
        by_path = {file["path"]: file for file in files}

        overridden = {
            ("experiments/yukari/prompt_style.jsonl", 33),
            ("experiments/yukari/prompt_style.jsonl", 34),
            ("experiments/yukari/prompt_style.jsonl", 35),
            ("experiments/yukari/prompt_style.jsonl", 36),
            ("experiments/yukari/delivery_style.jsonl", 48),
        }

        added_components = set()
        for file in files:
            for entry in file["records"]:
                if "component" in entry:
                    added_components.add((file["path"], entry["line"]))
                    self.assertEqual(entry["component"], "prompt_style")

        self.assertEqual(added_components, overridden)

        for path, line in overridden:
            record = by_path[path]["records"][
                [entry["line"] for entry in by_path[path]["records"]].index(line)]
            self.assertNotIn("pose", record["record"])
            self.assertNotIn("component", record["record"])

    def test_unlabelled_matches_an_independent_corpus_scan(self):
        files = observation_sync.build_files(REPO_ROOT)
        missing = observation_sync.unlabelled(files)

        expected = []
        for path in sorted(REPO_ROOT.glob("experiments/**/*.jsonl")):
            rel = path.relative_to(REPO_ROOT).as_posix()
            for line_no, raw in enumerate(
                    path.read_text(encoding="utf-8").splitlines(), start=1):
                if not raw.strip():
                    continue
                record = json.loads(raw)
                if "pose" in record or "component" in record:
                    continue
                if (rel, line_no) in observation_sync.COMPONENT_OVERRIDES:
                    continue
                expected.append((rel, line_no))
        self.assertEqual(missing, expected)

        repin_graph_rows = [
            item for item in missing
            if item[0] == "experiments/yukari/repin-graph.jsonl"]
        self.assertEqual(
            repin_graph_rows,
            [("experiments/yukari/repin-graph.jsonl", line)
             for line in range(1, 7)])

    def test_malformed_json_line_raises_system_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            broken = root / "experiments" / "yukari"
            broken.mkdir(parents=True)
            (broken / "broken.jsonl").write_text(
                '{"pose": "stand", "outcome": "accepted"}\nnot json\n',
                encoding="utf-8")

            with self.assertRaises(SystemExit) as raised:
                observation_sync.build_files(root)
            self.assertIn("broken.jsonl:2", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
