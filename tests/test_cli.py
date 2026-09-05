from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import Mock, patch

from comfyui_recipes.interfaces import cli


class CliTest(unittest.TestCase):
    @patch.object(cli, "generate")
    @patch.object(cli, "ChimeraClient")
    def test_generate_dispatches_without_network(self, chimera_class, run_generate):
        cli.main(["generate", "--request", "request.json", "--dry-run", "--force"])
        services = run_generate.call_args.args[1]
        self.assertIs(services.management, chimera_class.return_value)
        self.assertEqual(str(run_generate.call_args.args[0]), "request.json")
        self.assertEqual(run_generate.call_args.kwargs,
                         {"dry_run": True, "force": True})

    @patch.object(cli, "watch")
    @patch.object(cli, "ChimeraClient")
    def test_watch_dispatches_without_network(self, chimera_class, run_watch):
        cli.main(["watch", "--interval", "5", "--once", "--dry-run"])
        watch_services = run_watch.call_args.args[0]
        self.assertIs(watch_services.management, chimera_class.return_value)
        self.assertIs(
            watch_services.generate_services.management, chimera_class.return_value)
        self.assertEqual(run_watch.call_args.kwargs,
                         {"interval": 5.0, "once": True, "dry_run": True})

    @patch.object(cli, "work")
    @patch.object(cli, "ChimeraClient")
    def test_work_dispatches_without_network(self, chimera_class, run_work):
        cli.main(["work", "--interval", "5", "--once", "--dry-run",
                  "--worker-id", "worker-1", "--kinds", "generate"])
        work_services = run_work.call_args.args[0]
        self.assertIs(work_services.management, chimera_class.return_value)
        self.assertIs(
            work_services.generate_services.management, chimera_class.return_value)
        self.assertEqual(work_services.worker_id, "worker-1")
        self.assertEqual(work_services.kinds, ("generate",))
        self.assertEqual(run_work.call_args.kwargs,
                         {"interval": 5.0, "once": True, "dry_run": True})

    @patch.object(cli.metadata, "add_tag")
    @patch.object(cli, "ChimeraClient")
    def test_metadata_tag_dispatches_without_network(self, chimera_class, add_tag):
        with redirect_stdout(io.StringIO()):
            cli.main(["metadata", "tag", "generation", "approved"])
        add_tag.assert_called_once_with(
            chimera_class.return_value, "generation", "approved")

    def test_yukari_prompt_json_needs_no_clients(self):
        output = io.StringIO()
        with patch.object(cli, "ChimeraClient") as chimera_class, \
                redirect_stdout(output):
            cli.main(["yukari", "prompt", "--pose", "lounge", "--json"])
        chimera_class.assert_not_called()
        self.assertIn('"positive"', output.getvalue())
        self.assertIn('"negative"', output.getvalue())


class WatchIntervalTest(unittest.TestCase):
    def _parse(self, interval: str):
        with redirect_stderr(io.StringIO()):
            return cli.parser().parse_args(["watch", "--interval", interval])

    def test_zero_is_rejected(self):
        with self.assertRaises(SystemExit):
            self._parse("0")

    def test_negative_is_rejected(self):
        with self.assertRaises(SystemExit):
            self._parse("-1")

    def test_nan_is_rejected(self):
        with self.assertRaises(SystemExit):
            self._parse("nan")

    def test_infinity_is_rejected(self):
        with self.assertRaises(SystemExit):
            self._parse("inf")

    def test_non_numeric_is_rejected(self):
        with self.assertRaises(SystemExit):
            self._parse("soon")

    def test_valid_value_is_accepted(self):
        args = self._parse("2.5")
        self.assertEqual(args.interval, 2.5)

    @patch.object(cli, "watch")
    @patch.object(cli, "ChimeraClient")
    def test_valid_value_reaches_watch(self, chimera_class, run_watch):
        cli.main(["watch", "--interval", "2.5", "--once"])
        self.assertEqual(run_watch.call_args.kwargs["interval"], 2.5)


if __name__ == "__main__":
    unittest.main()
