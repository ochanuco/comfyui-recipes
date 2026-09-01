from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
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


if __name__ == "__main__":
    unittest.main()
