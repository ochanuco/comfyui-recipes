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
                         {"interval": 5.0, "once": True, "dry_run": True,
                          "publish_catalog": True})

    @patch.object(cli, "repair")
    @patch.object(cli, "ChimeraClient")
    def test_repair_dispatches_without_network(self, chimera_class, run_repair):
        cli.main(["repair", "gen-1", "--parts", "hands, feet",
                  "--region", "0.1,0.2,0.3,0.4", "--region", "0.5,0.5,0.9,0.9",
                  "--denoise", "0.7", "--seeds", "1,2,3", "--size", "768",
                  "--pad", "1.5"])
        args, kwargs = run_repair.call_args
        self.assertEqual(args[0], "gen-1")
        self.assertIs(args[1].management, chimera_class.return_value)
        self.assertEqual(kwargs["parts"], ["hands", "feet"])
        self.assertEqual(kwargs["regions"], [[0.1, 0.2, 0.3, 0.4], [0.5, 0.5, 0.9, 0.9]])
        self.assertEqual(kwargs["denoise"], 0.7)
        self.assertEqual(kwargs["seeds"], [1, 2, 3])
        self.assertEqual(kwargs["size"], 768)
        self.assertEqual(kwargs["pad"], 1.5)

    @patch.object(cli, "repair")
    @patch.object(cli, "ChimeraClient")
    def test_repair_defaults_need_no_flags(self, chimera_class, run_repair):
        cli.main(["repair", "gen-1"])
        args, kwargs = run_repair.call_args
        self.assertEqual(kwargs["parts"], ["hands", "feet"])
        self.assertEqual(kwargs["regions"], [])
        self.assertEqual(kwargs["denoise"], 0.6)
        self.assertEqual(kwargs["seeds"], [1, 2, 3, 4])
        self.assertEqual(kwargs["size"], 1024)
        self.assertEqual(kwargs["pad"], 1.0)
        self.assertIsNone(kwargs["model"])

    @patch.object(cli, "repair")
    @patch.object(cli, "ChimeraClient")
    def test_repair_model_flag_dispatches_without_network(
            self, chimera_class, run_repair):
        cli.main(["repair", "gen-1", "--model", "anima"])
        kwargs = run_repair.call_args.kwargs
        self.assertEqual(kwargs["model"], "anima")

    def test_repair_unknown_model_is_rejected_by_argparse(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                cli.main(["repair", "gen-1", "--model", "nope"])

    @patch.object(cli, "finalize")
    @patch.object(cli, "ChimeraClient")
    def test_finalize_repair_flags_dispatch_without_network(
            self, chimera_class, run_finalize):
        cli.main(["finalize", "gen-1", "--repair", "hands, feet",
                  "--repair-region", "0.1,0.2,0.3,0.4",
                  "--repair-denoise", "0.7", "--repair-pad", "1.5",
                  "--repair-size", "768"])
        args, kwargs = run_finalize.call_args
        self.assertEqual(args[0], "gen-1")
        self.assertEqual(kwargs["repair"], ["hands", "feet"])
        self.assertEqual(kwargs["repair_regions"], [[0.1, 0.2, 0.3, 0.4]])
        self.assertEqual(kwargs["repair_denoise"], 0.7)
        self.assertEqual(kwargs["repair_pad"], 1.5)
        self.assertEqual(kwargs["repair_size"], 768)

    @patch.object(cli, "finalize")
    @patch.object(cli, "ChimeraClient")
    def test_finalize_repair_defaults_need_no_flags(self, chimera_class, run_finalize):
        cli.main(["finalize", "gen-1"])
        args, kwargs = run_finalize.call_args
        self.assertIsNone(kwargs["repair"])
        self.assertEqual(kwargs["repair_regions"], [])
        self.assertEqual(kwargs["repair_denoise"], 0.6)
        self.assertEqual(kwargs["repair_pad"], 1.0)
        self.assertEqual(kwargs["repair_size"], 1024)
        self.assertEqual(kwargs["keep_regions"], [])
        self.assertEqual(kwargs["keep_strength"], 0.25)

    @patch.object(cli, "finalize")
    @patch.object(cli, "ChimeraClient")
    def test_finalize_sketch_redraw_dispatches_without_network(
            self, chimera_class, run_finalize):
        cli.main(["finalize", "gen-1", "--sketch-redraw", "cinema"])
        args, kwargs = run_finalize.call_args
        self.assertEqual(kwargs["sketch_redraw"], "cinema")

    @patch.object(cli, "finalize")
    @patch.object(cli, "ChimeraClient")
    def test_finalize_sketch_redraw_defaults_to_none(self, chimera_class, run_finalize):
        cli.main(["finalize", "gen-1"])
        args, kwargs = run_finalize.call_args
        self.assertIsNone(kwargs["sketch_redraw"])

    @patch.object(cli, "finalize")
    @patch.object(cli, "ChimeraClient")
    def test_finalize_keep_region_flags_dispatch_without_network(
            self, chimera_class, run_finalize):
        cli.main(["finalize", "gen-1", "--keep-region", "0.3,0.58,0.85,0.8",
                  "--keep-region", "0.0,0.84,0.65,1.0", "--keep-strength", "0.45"])
        args, kwargs = run_finalize.call_args
        self.assertEqual(kwargs["keep_regions"],
                         [[0.3, 0.58, 0.85, 0.8], [0.0, 0.84, 0.65, 1.0]])
        self.assertEqual(kwargs["keep_strength"], 0.45)

    @patch.object(cli, "fetch_source")
    @patch.object(cli, "finalize")
    @patch.object(cli, "ChimeraClient")
    def test_finalize_denoise_word_resolves_through_the_source_recipe(
            self, chimera_class, run_finalize, fetch_source):
        context, batch = object(), object()
        fetch_source.return_value = (context, batch, "yukari-sketch")
        cli.main(["finalize", "gen-1", "--denoise", "tidy"])
        fetch_source.assert_called_once_with(chimera_class.return_value, "gen-1")
        args, kwargs = run_finalize.call_args
        self.assertEqual(kwargs["denoise"], 0.65)
        # The context fetch_source already made is passed through so
        # finalize() does not fetch it again.
        self.assertIs(kwargs["context"], context)

    @patch.object(cli, "fetch_source")
    @patch.object(cli, "finalize")
    @patch.object(cli, "ChimeraClient")
    def test_finalize_unknown_word_exits_before_finalizing(
            self, chimera_class, run_finalize, fetch_source):
        fetch_source.return_value = ({}, {}, "yukari")
        with self.assertRaises(SystemExit):
            cli.main(["finalize", "gen-1", "--denoise", "blurry"])
        run_finalize.assert_not_called()

    @patch.object(cli, "fetch_source")
    @patch.object(cli, "finalize")
    @patch.object(cli, "ChimeraClient")
    def test_finalize_numeric_denoise_never_looks_up_the_recipe(
            self, chimera_class, run_finalize, fetch_source):
        cli.main(["finalize", "gen-1", "--denoise", "0.7"])
        fetch_source.assert_not_called()
        kwargs = run_finalize.call_args.kwargs
        self.assertEqual(kwargs["denoise"], 0.7)
        self.assertIsNone(kwargs["context"])

    @patch.object(cli, "fetch_source")
    @patch.object(cli, "repair")
    @patch.object(cli, "ChimeraClient")
    def test_repair_denoise_and_lora_words_resolve_through_the_source_recipe(
            self, chimera_class, run_repair, fetch_source):
        context, batch = object(), object()
        fetch_source.return_value = (context, batch, "yukari-sketch")
        cli.main(["repair", "gen-1", "--denoise", "keep", "--lora", "on"])
        fetch_source.assert_called_once_with(chimera_class.return_value, "gen-1")
        args, kwargs = run_repair.call_args
        self.assertEqual(kwargs["denoise"], 0.6)
        self.assertEqual(kwargs["lora"], 0.8)
        # The context/batch fetch_source already made are passed through so
        # repair() does not fetch either again.
        self.assertIs(kwargs["context"], context)
        self.assertIs(kwargs["batch"], batch)

    @patch.object(cli, "fetch_source")
    @patch.object(cli, "repair")
    @patch.object(cli, "ChimeraClient")
    def test_repair_numeric_args_never_look_up_the_recipe(
            self, chimera_class, run_repair, fetch_source):
        cli.main(["repair", "gen-1", "--denoise", "0.7"])
        fetch_source.assert_not_called()
        kwargs = run_repair.call_args.kwargs
        self.assertEqual(kwargs["denoise"], 0.7)
        self.assertIsNone(kwargs["context"])
        self.assertIsNone(kwargs["batch"])

    @patch.object(cli, "work")
    @patch.object(cli, "ChimeraClient")
    def test_work_default_kinds_include_repair_and_masked_redraw(
            self, chimera_class, run_work):
        cli.main(["work", "--once"])
        work_services = run_work.call_args.args[0]
        self.assertEqual(
            work_services.kinds, ("generate", "finalize", "repair", "masked_redraw"))
        self.assertIs(
            work_services.repair_services.management, chimera_class.return_value)
        self.assertIs(
            work_services.masked_redraw_services.management, chimera_class.return_value)

    @patch.object(cli, "work")
    @patch.object(cli, "ChimeraClient")
    def test_work_no_catalog_flag_disables_publish(self, chimera_class, run_work):
        cli.main(["work", "--once", "--no-catalog"])
        self.assertFalse(run_work.call_args.kwargs["publish_catalog"])

    @patch.object(cli, "ChimeraClient")
    def test_catalog_prints_the_document_and_does_not_publish(self, chimera_class):
        output = io.StringIO()
        with redirect_stdout(output):
            cli.main(["catalog"])
        chimera_class.return_value.put_catalog.assert_not_called()
        document = cli.json.loads(output.getvalue())
        self.assertEqual(document["schema_version"], 1)
        self.assertEqual(
            {recipe["name"] for recipe in document["recipes"]},
            {"yukari", "yukari-anima", "yukari-sketch"})

    @patch.object(cli, "publish_catalog_document")
    @patch.object(cli, "ChimeraClient")
    def test_catalog_publish_flag_puts_and_prints_the_response(
            self, chimera_class, publish):
        publish.return_value = {"ok": True}
        output = io.StringIO()
        with redirect_stdout(output):
            cli.main(["catalog", "--publish"])
        args, kwargs = publish.call_args
        self.assertIs(args[0], chimera_class.return_value)
        self.assertIn('"ok": true', output.getvalue())

    @patch.object(cli.metadata, "add_tag")
    @patch.object(cli, "ChimeraClient")
    def test_metadata_tag_dispatches_without_network(self, chimera_class, add_tag):
        with redirect_stdout(io.StringIO()):
            cli.main(["metadata", "tag", "generation", "approved"])
        add_tag.assert_called_once_with(
            chimera_class.return_value, "generation", "approved")

    @patch.object(cli.metadata, "record_publication")
    @patch.object(cli, "ChimeraClient")
    def test_metadata_publish_dispatches_without_network(
            self, chimera_class, record_publication):
        output = io.StringIO()
        with redirect_stdout(output):
            cli.main(["metadata", "publish", "generation",
                      "--url", "https://x.com/post/1", "--idempotency-key", "pub-key"])
        record_publication.assert_called_once_with(
            chimera_class.return_value, "generation", url="https://x.com/post/1",
            idempotency_key="pub-key")
        self.assertIn("publish -> generation (https://x.com/post/1)", output.getvalue())

    @patch.object(cli.metadata, "record_publication")
    @patch.object(cli, "ChimeraClient")
    def test_metadata_publish_without_url_needs_no_flag(
            self, chimera_class, record_publication):
        with redirect_stdout(io.StringIO()):
            cli.main(["metadata", "publish", "generation"])
        record_publication.assert_called_once_with(
            chimera_class.return_value, "generation", url=None, idempotency_key=None)

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
