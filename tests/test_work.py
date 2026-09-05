"""Tests for the resident requests-queue worker.

All collaborators are fakes: this suite never opens a network socket and
never calls the real generate()/finalize() use cases (those are covered
separately in test_generate_application.py and test_finalize_application.py).
"""

from __future__ import annotations

import dataclasses
import tempfile
import threading
import time
import unittest
from pathlib import Path

from comfyui_recipes.application.generate import GenerateServices
from comfyui_recipes.application.work import (
    Heartbeat,
    HubListener,
    ProgressRelay,
    WorkServices,
    execute,
    finalize_arguments,
    work,
    work_once,
)
from comfyui_recipes.domain.yukari.recipe import TOE_GUARD


class ManagementFake:
    def __init__(self, claim_responses=None, dry_run_items=None):
        self.calls = []
        self.claim_responses = list(claim_responses or [])
        self.claim_error = None
        self.dry_run_items = dry_run_items or []

    def request(self, method, path, payload=None, multipart=None):
        self.calls.append((method, path, payload, multipart))
        if method == "POST" and path == "/api/v1/requests/claim":
            if self.claim_error is not None:
                raise self.claim_error
            if self.claim_responses:
                next_item = self.claim_responses.pop(0)
                if isinstance(next_item, BaseException):
                    raise next_item
                return next_item
            return None
        if method == "GET" and path.startswith("/api/v1/requests?status=queued"):
            return {"items": self.dry_run_items}
        if method == "PATCH" and path.startswith("/api/v1/requests/"):
            return {}
        raise AssertionError(f"unexpected management call: {method} {path}")


class FakeHubConnection:
    """A scripted Connection: pops dicts/exceptions from `script`, else idles.

    An empty script makes recv() behave like a real timeout -- it sleeps a
    short, bounded time and returns None -- so a listener with nothing left
    to read does not busy-loop.
    """

    def __init__(self, script=None, idle_timeout_cap=0.05):
        self.script = list(script or [])
        self.sent = []
        self.closed = False
        self.idle_timeout_cap = idle_timeout_cap

    def send(self, message):
        self.sent.append(message)

    def recv(self, timeout):
        if self.closed:
            raise ConnectionError("closed")
        if self.script:
            item = self.script.pop(0)
            if isinstance(item, BaseException):
                raise item
            return item
        time.sleep(min(timeout, self.idle_timeout_cap) if timeout else self.idle_timeout_cap)
        return None

    def close(self):
        self.closed = True


class GatedHubConnection:
    """Like FakeHubConnection, but the message after `pre_script` is held back
    until the test calls `release.set()` -- lets a test synchronize with an
    in-progress `wake.wait()` before delivering the message that ends it.
    """

    def __init__(self, pre_script, gated_message):
        self.pre_script = list(pre_script)
        self.gated_message = gated_message
        self.release = threading.Event()
        self.sent = []
        self.closed = False

    def send(self, message):
        self.sent.append(message)

    def recv(self, timeout):
        if self.pre_script:
            item = self.pre_script.pop(0)
            if isinstance(item, BaseException):
                raise item
            return item
        if self.release.wait(timeout=min(timeout, 2) if timeout else 2):
            self.release.clear()
            return self.gated_message
        return None

    def close(self):
        self.closed = True


class HubFactory:
    """A `services.hub`/`services.progress_feed` factory: one connection (or
    exception) per call, consumed in order.
    """

    def __init__(self, connections):
        self.connections = list(connections)

    def __call__(self):
        next_item = self.connections.pop(0)
        if isinstance(next_item, BaseException):
            raise next_item
        return next_item


class RecordingHeartbeat:
    def __init__(self, management, row_id, worker_id, *, interval=30, emit=print):
        self.management = management
        self.row_id = row_id
        self.worker_id = worker_id
        self.interval = interval
        self.emit = emit
        self.events = []

    def __enter__(self):
        self.events.append("start")
        return self

    def __exit__(self, *exc_info):
        self.events.append("stop")
        return False


def make_generate_services(directory: Path, **overrides) -> GenerateServices:
    defaults = dict(
        management=None, comfyui=None, state=None, notifier=None,
        graph_builder=lambda generation, seed, prefix: {},
        git_metadata=lambda: {"commit": "c", "dirty": False},
        conflicts=lambda *_: [], output_root=directory, measure=None,
        emit=lambda message: None,
    )
    defaults.update(overrides)
    return GenerateServices(**defaults)


def make_services(directory: Path, management, *, heartbeats=None,
                  generate=None, finalize=None, finalize_services=None,
                  branch="dev/requests-worker", emit=None, sleep=None,
                  kinds=("generate", "finalize")) -> WorkServices:
    kwargs = dict(
        management=management,
        generate_services=make_generate_services(Path(directory)),
        finalize_services=finalize_services or (lambda arguments: arguments),
        git_metadata=lambda: {"branch": branch},
        worker_id="test-worker",
        emit=(emit or (lambda message: None)),
        kinds=kinds,
    )
    if heartbeats is not None:
        def factory(management, row_id, worker_id, *, interval=30, emit=print):
            instance = RecordingHeartbeat(
                management, row_id, worker_id, interval=interval, emit=emit)
            heartbeats.append(instance)
            return instance
        kwargs["heartbeat"] = factory
    if generate is not None:
        kwargs["generate"] = generate
    if finalize is not None:
        kwargs["finalize"] = finalize
    if sleep is not None:
        kwargs["sleep"] = sleep
    return WorkServices(**kwargs)


def make_hub_services(directory: Path, *, hub=None, progress_feed=None,
                      sleep=None, emit=None, ping_interval=0.05, backoff_max=1,
                      clock=None, kinds=("generate", "finalize")) -> WorkServices:
    kwargs = dict(
        management=ManagementFake(),
        generate_services=make_generate_services(Path(directory)),
        finalize_services=lambda arguments: arguments,
        git_metadata=lambda: {"branch": "dev/requests-worker"},
        worker_id="test-worker",
        emit=(emit or (lambda message: None)),
        kinds=kinds,
        hub=hub,
        progress_feed=progress_feed,
        ping_interval=ping_interval,
        backoff_max=backoff_max,
    )
    if sleep is not None:
        kwargs["sleep"] = sleep
    if clock is not None:
        kwargs["clock"] = clock
    return WorkServices(**kwargs)


def generate_row(**overrides):
    row = {
        "id": "req-1", "kind": "generate", "status": "running",
        "recipe_ref": "dev/requests-worker", "run_id": None, "attempt": 1,
        "payload": {"schema_version": 1, "request": {"count": 1},
                    "generation": {"recipe": "yukari"}, "semantic": {}},
    }
    row.update(overrides)
    return row


def finalize_row(**overrides):
    row = {
        "id": "req-2", "kind": "finalize", "status": "running",
        "recipe_ref": "dev/requests-worker", "run_id": None, "attempt": 1,
        "payload": {"generation_id": "gen-1", "options": {}},
    }
    row.update(overrides)
    return row


class FinalizeArgumentsTest(unittest.TestCase):
    def test_defaults_are_false_and_null(self):
        arguments = finalize_arguments({})
        self.assertEqual(arguments, {
            "denoise": None, "handdrawn": False, "apply_repin": False,
            "apply_skin": False, "apply_recolor": False, "keep_legwear": None,
            "toe_guard": None, "size": None, "latent_route": None,
            "finalizer": None, "keep_scene": False,
        })

    def test_keep_legwear_true_becomes_default_cut(self):
        self.assertEqual(finalize_arguments({"keep_legwear": True})["keep_legwear"], 0.62)

    def test_keep_legwear_number_passes_through(self):
        self.assertEqual(finalize_arguments({"keep_legwear": 0.4})["keep_legwear"], 0.4)

    def test_route_pixel_forces_latent_route_false(self):
        self.assertIs(finalize_arguments({"route": "pixel"})["latent_route"], False)

    def test_route_latent_forces_latent_route_true(self):
        self.assertIs(finalize_arguments({"route": "latent"})["latent_route"], True)

    def test_toe_guard_true_becomes_the_recipe_constant(self):
        self.assertEqual(finalize_arguments({"toe_guard": True})["toe_guard"], TOE_GUARD)

    def test_toe_guard_number_passes_through(self):
        self.assertEqual(finalize_arguments({"toe_guard": 1.2})["toe_guard"], 1.2)

    def test_booleans_and_size_and_finalizer_pass_through(self):
        arguments = finalize_arguments({
            "repin": True, "recolor": True, "handdrawn": True, "skin": True,
            "keep_scene": True, "size": 2048, "finalizer": "some-model",
            "denoise": 0.5,
        })
        self.assertEqual(arguments["apply_repin"], True)
        self.assertEqual(arguments["apply_recolor"], True)
        self.assertEqual(arguments["handdrawn"], True)
        self.assertEqual(arguments["apply_skin"], True)
        self.assertEqual(arguments["keep_scene"], True)
        self.assertEqual(arguments["size"], 2048)
        self.assertEqual(arguments["finalizer"], "some-model")
        self.assertEqual(arguments["denoise"], 0.5)

    def test_unknown_key_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            finalize_arguments({"nope": True})
        self.assertIn("nope", str(ctx.exception))

    def test_wrong_type_is_rejected_with_the_offending_key_named(self):
        cases = [
            {"repin": "yes"},
            {"denoise": "0.5"},
            {"keep_legwear": "wide"},
            {"route": "sideways"},
            {"finalizer": 123},
            {"size": 2048.5},
            {"toe_guard": "on"},
        ]
        for options in cases:
            with self.subTest(options=options), self.assertRaises(ValueError) as ctx:
                finalize_arguments(options)
            key = next(iter(options))
            self.assertIn(key, str(ctx.exception))

    def test_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            finalize_arguments([])


class ExecuteTest(unittest.TestCase):
    def test_recipe_ref_mismatch_fails_without_executing(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            services = make_services(
                directory, ManagementFake(),
                generate=lambda *a, **k: calls.append((a, k)))
            row = generate_row(recipe_ref="other-branch")
            with self.assertRaises(SystemExit) as ctx:
                execute(services, row)
            self.assertEqual(str(ctx.exception), "recipe_ref not served: other-branch")
            self.assertEqual(calls, [])

    def test_generate_kind_writes_the_request_file_and_derives_the_key_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                calls.append((path, key_prefix))
                return {"batch_id": "b1", "generation_ids": ["g1"]}

            services = make_services(directory, ManagementFake(), generate=fake_generate)
            result = execute(services, generate_row())
            self.assertEqual(result, {"batch_id": "b1", "generation_ids": ["g1"]})
            self.assertEqual(len(calls), 1)
            path, key_prefix = calls[0]
            self.assertEqual(path, Path(directory) / "requests" / "req-1.json")
            self.assertTrue(path.exists())
            self.assertEqual(key_prefix, "request:req-1")

    def test_finalize_kind_maps_options_and_builds_services_from_the_factory(self):
        with tempfile.TemporaryDirectory() as directory:
            factory_calls = []
            finalize_calls = []

            def factory(arguments):
                factory_calls.append(arguments)
                return "finalize-services-sentinel"

            def fake_finalize(generation_id, finalize_services, **kwargs):
                finalize_calls.append((generation_id, finalize_services, kwargs))
                return {"batch_id": "b2", "generation_ids": ["g2"]}

            services = make_services(
                directory, ManagementFake(), finalize=fake_finalize,
                finalize_services=factory)
            row = finalize_row(payload={
                "generation_id": "gen-1",
                "options": {"repin": True, "keep_legwear": True, "route": "pixel"},
            })
            result = execute(services, row)
            self.assertEqual(result, {"batch_id": "b2", "generation_ids": ["g2"]})
            self.assertEqual(finalize_calls[0][0], "gen-1")
            self.assertEqual(finalize_calls[0][1], "finalize-services-sentinel")
            self.assertEqual(finalize_calls[0][2]["apply_repin"], True)
            self.assertEqual(finalize_calls[0][2]["keep_legwear"], 0.62)
            self.assertIs(finalize_calls[0][2]["latent_route"], False)
            self.assertNotIn("keep_scene", finalize_calls[0][2])
            self.assertEqual(factory_calls[0]["keep_scene"], False)

    def test_finalize_kind_with_bad_options_fails_before_finalizing(self):
        with tempfile.TemporaryDirectory() as directory:
            finalize_calls = []
            services = make_services(
                directory, ManagementFake(),
                finalize=lambda *a, **k: finalize_calls.append((a, k)))
            row = finalize_row(payload={
                "generation_id": "gen-1", "options": {"nope": True}})
            with self.assertRaises(SystemExit) as ctx:
                execute(services, row)
            self.assertIn("nope", str(ctx.exception))
            self.assertEqual(finalize_calls, [])

    def test_finalize_kind_without_generation_id_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            services = make_services(directory, ManagementFake())
            row = finalize_row(payload={"options": {}})
            with self.assertRaises(SystemExit):
                execute(services, row)

    def test_unsupported_kind_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            services = make_services(directory, ManagementFake())
            with self.assertRaises(SystemExit):
                execute(services, generate_row(kind="probe"))


class WorkOnceTest(unittest.TestCase):
    def test_no_queued_row_returns_false_and_makes_no_further_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(claim_responses=[None])
            services = make_services(directory, management)
            self.assertFalse(work_once(services))
            self.assertEqual(management.calls, [
                ("POST", "/api/v1/requests/claim",
                 {"worker_id": "test-worker", "kinds": ["generate", "finalize"]}, None)])

    def test_done_row_patches_status_done_with_the_result(self):
        with tempfile.TemporaryDirectory() as directory:
            row = generate_row()
            management = ManagementFake(claim_responses=[row])

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                return {"batch_id": "b1", "generation_ids": ["g1"]}

            services = make_services(directory, management, generate=fake_generate)
            self.assertTrue(work_once(services))
            patch_call = next(
                call for call in management.calls
                if call[0] == "PATCH" and call[1] == "/api/v1/requests/req-1")
            self.assertEqual(
                patch_call[2],
                {"status": "done", "result": {"batch_id": "b1", "generation_ids": ["g1"]},
                 "worker_id": "test-worker"})

    def test_failed_row_patches_status_failed_with_the_error_message(self):
        with tempfile.TemporaryDirectory() as directory:
            row = generate_row()
            management = ManagementFake(claim_responses=[row])

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                raise RuntimeError("boom")

            services = make_services(directory, management, generate=fake_generate)
            self.assertTrue(work_once(services))
            patch_call = next(
                call for call in management.calls
                if call[0] == "PATCH" and call[1] == "/api/v1/requests/req-1")
            self.assertEqual(patch_call[2], {"status": "failed", "error": "boom",
                                             "worker_id": "test-worker"})

    def test_recipe_ref_mismatch_reports_failed_with_the_exact_message(self):
        with tempfile.TemporaryDirectory() as directory:
            row = generate_row(recipe_ref="other-branch")
            management = ManagementFake(claim_responses=[row])
            calls = []
            services = make_services(
                directory, management, generate=lambda *a, **k: calls.append((a, k)))
            self.assertTrue(work_once(services))
            self.assertEqual(calls, [])
            patch_call = next(
                call for call in management.calls
                if call[0] == "PATCH" and call[1] == "/api/v1/requests/req-1")
            self.assertEqual(
                patch_call[2],
                {"status": "failed", "error": "recipe_ref not served: other-branch",
                 "worker_id": "test-worker"})

    def test_heartbeat_is_started_and_stopped_around_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            row = generate_row()
            management = ManagementFake(claim_responses=[row])
            heartbeats = []

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                self.assertEqual(heartbeats[0].events, ["start"])
                return {"batch_id": "b1", "generation_ids": []}

            services = make_services(
                directory, management, heartbeats=heartbeats, generate=fake_generate)
            work_once(services)
            self.assertEqual(len(heartbeats), 1)
            self.assertEqual(heartbeats[0].row_id, "req-1")
            self.assertEqual(heartbeats[0].events, ["start", "stop"])

    def test_keyboard_interrupt_from_the_executor_propagates_and_marks_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            row = generate_row()
            management = ManagementFake(claim_responses=[row])
            heartbeats = []

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                raise KeyboardInterrupt

            services = make_services(
                directory, management, heartbeats=heartbeats, generate=fake_generate)
            with self.assertRaises(KeyboardInterrupt):
                work_once(services)
            self.assertFalse(any(call[0] == "PATCH" for call in management.calls))
            self.assertEqual(heartbeats[0].events, ["start", "stop"])

    def test_claim_failure_is_emitted_and_does_not_raise(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake()
            management.claim_error = SystemExit("403 forbidden")
            messages = []
            services = make_services(directory, management, emit=messages.append)
            self.assertFalse(work_once(services))
            self.assertTrue(any("403" in message for message in messages))

    def test_dry_run_does_not_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(dry_run_items=[generate_row()])
            services = make_services(directory, management)
            self.assertFalse(work_once(services, dry_run=True))
            self.assertFalse(
                any(call[1] == "/api/v1/requests/claim" for call in management.calls))
            self.assertTrue(
                any(call[1].startswith("/api/v1/requests?status=queued")
                    for call in management.calls))


class WorkLoopTest(unittest.TestCase):
    def test_once_claims_exactly_once_and_never_sleeps(self):
        with tempfile.TemporaryDirectory() as directory:
            row = generate_row()
            management = ManagementFake(claim_responses=[row])

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                return {"batch_id": "b1", "generation_ids": []}

            def no_sleep(seconds):
                raise AssertionError("must not sleep when --once")

            services = make_services(
                directory, management, generate=fake_generate, sleep=no_sleep)
            work(services, once=True)
            claim_calls = [call for call in management.calls
                          if call[1] == "/api/v1/requests/claim"]
            self.assertEqual(len(claim_calls), 1)

    def test_sleeps_only_when_nothing_was_claimed(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(claim_responses=[None])
            sleeps = []

            def sleep_then_stop(seconds):
                sleeps.append(seconds)
                raise KeyboardInterrupt

            services = make_services(directory, management, sleep=sleep_then_stop)
            work(services, once=False)  # must not raise
            self.assertEqual(sleeps, [30])

    def test_keyboard_interrupt_stops_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(claim_responses=[None])
            messages = []

            def interrupt(seconds):
                raise KeyboardInterrupt

            services = make_services(
                directory, management, sleep=interrupt, emit=messages.append)
            work(services, once=False)
            self.assertTrue(any("stopped" in message for message in messages))


class HeartbeatTest(unittest.TestCase):
    def test_sends_running_with_the_worker_id_until_stopped(self):
        import threading

        calls = []
        seen = threading.Event()

        class Management:
            def request(self, method, path, payload=None, multipart=None):
                calls.append((method, path, payload))
                seen.set()
                return {}

        heartbeat = Heartbeat(Management(), "req-1", "test-worker", interval=0.01)
        with heartbeat:
            self.assertTrue(seen.wait(2))
        self.assertEqual(calls[0], ("PATCH", "/api/v1/requests/req-1",
                                    {"status": "running", "worker_id": "test-worker"}))


class HubListenerTest(unittest.TestCase):
    def test_hello_sent_first_and_wake_set_after_connect(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = FakeHubConnection(script=[
                {"type": "hello_ack", "server_time": "t"},
            ])
            services = make_hub_services(
                directory, hub=HubFactory([connection]))
            wake = threading.Event()
            listener = HubListener(services, wake).start()
            try:
                self.assertTrue(wake.wait(2))
                self.assertEqual(connection.sent[0], {
                    "type": "hello", "worker_id": "test-worker",
                    "kinds": ["generate", "finalize"]})
            finally:
                listener.stop()
            self.assertTrue(connection.closed)

    def test_queued_message_sets_wake(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = FakeHubConnection(script=[
                {"type": "hello_ack", "server_time": "t"},
                {"type": "queued", "request_id": "r1", "kind": "generate",
                 "recipe_ref": "ref"},
            ])
            services = make_hub_services(directory, hub=HubFactory([connection]))
            wake = threading.Event()
            listener = HubListener(services, wake).start()
            try:
                self.assertTrue(wake.wait(2))
            finally:
                listener.stop()

    def test_unknown_message_types_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = FakeHubConnection(script=[
                {"type": "pong"}, {"type": "mystery", "foo": "bar"},
            ])
            services = make_hub_services(directory, hub=HubFactory([connection]))
            wake = threading.Event()
            listener = HubListener(services, wake).start()
            try:
                self.assertTrue(wake.wait(2))  # from the initial connect
                wake.clear()
                time.sleep(0.2)
                self.assertFalse(wake.is_set())
            finally:
                listener.stop()

    def test_ping_sent_on_recv_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = FakeHubConnection(script=[])
            services = make_hub_services(
                directory, hub=HubFactory([connection]), ping_interval=0.01)
            wake = threading.Event()
            listener = HubListener(services, wake).start()
            try:
                self.assertTrue(wake.wait(2))
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline and not any(
                        message.get("type") == "ping" for message in connection.sent):
                    time.sleep(0.01)
                self.assertTrue(
                    any(message.get("type") == "ping" for message in connection.sent))
            finally:
                listener.stop()

    def test_reconnect_backoff_doubles_up_to_backoff_max(self):
        with tempfile.TemporaryDirectory() as directory:
            # The factory itself fails (the Upgrade is refused) every time, so
            # backoff never gets the post-connect reset -- it grows monotonically.
            factory = HubFactory([ConnectionError("refused") for _ in range(6)])
            sleeps = []
            holder: dict = {}

            def fake_sleep(seconds):
                sleeps.append(seconds)
                if len(sleeps) >= 5:
                    holder["listener"]._stop.set()

            services = make_hub_services(
                directory, hub=factory, sleep=fake_sleep, backoff_max=8)
            listener = HubListener(services, threading.Event())
            holder["listener"] = listener
            listener.start()
            listener._thread.join(2)
            self.assertEqual(sleeps, [1, 2, 4, 8, 8])

    def test_wake_set_again_after_a_reconnect(self):
        with tempfile.TemporaryDirectory() as directory:
            first = FakeHubConnection(script=[])
            second = FakeHubConnection(script=[])
            # A real, short pause between the closed first connection and the
            # reconnect attempt gives the test time to observe and clear the
            # first wake before the second one fires -- an instant retry
            # could collapse the two into a single observed set().
            services = make_hub_services(
                directory, hub=HubFactory([first, second]),
                sleep=lambda seconds: time.sleep(0.2))
            wake = threading.Event()
            listener = HubListener(services, wake).start()
            try:
                self.assertTrue(wake.wait(2))
                wake.clear()
                first.close()  # simulate the server dropping the first socket
                self.assertTrue(wake.wait(2))
            finally:
                listener.stop()

    def test_send_progress_is_a_no_op_when_not_connected(self):
        with tempfile.TemporaryDirectory() as directory:
            services = make_hub_services(directory)
            listener = HubListener(services, threading.Event())
            listener.send_progress("r1", "submit")  # must not raise

    def test_send_progress_forwards_the_message_when_connected(self):
        with tempfile.TemporaryDirectory() as directory:
            services = make_hub_services(directory)
            listener = HubListener(services, threading.Event())
            connection = FakeHubConnection()
            listener._connection = connection
            listener.send_progress("r1", "sampling", step=3, total=10)
            self.assertEqual(connection.sent, [{
                "type": "progress", "request_id": "r1", "phase": "sampling",
                "step": 3, "total": 10}])

    def test_send_progress_omits_none_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            services = make_hub_services(directory)
            listener = HubListener(services, threading.Event())
            connection = FakeHubConnection()
            listener._connection = connection
            listener.send_progress("r1", "submit")
            self.assertEqual(connection.sent, [{
                "type": "progress", "request_id": "r1", "phase": "submit"}])


class ProgressRelayTest(unittest.TestCase):
    def test_forwards_progress_only_while_current_is_set_and_with_the_id(self):
        with tempfile.TemporaryDirectory() as directory:
            feed = GatedHubConnection(
                pre_script=[{"step": 1, "total": 5}], gated_message={"step": 2, "total": 5})
            services = make_hub_services(
                directory, progress_feed=lambda: feed, sleep=lambda seconds: None)
            sent = []

            class RecordingListener:
                def send_progress(self, request_id, phase, **fields):
                    sent.append((request_id, phase, fields))

            relay = ProgressRelay(services, RecordingListener())
            relay.current = None
            relay.start()
            try:
                # First event (step 1) is delivered with current still None --
                # give the background thread a moment to have dropped it.
                time.sleep(0.2)
                self.assertEqual(sent, [])
                relay.current = "req-9"
                feed.release.set()
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline and not sent:
                    time.sleep(0.01)
            finally:
                relay.stop()
            self.assertEqual(sent, [("req-9", "sampling", {"step": 2, "total": 5})])


class WorkWithHubTest(unittest.TestCase):
    def test_idle_wait_is_woken_by_a_queued_message_not_by_the_full_interval(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(claim_responses=[
                generate_row(), None, KeyboardInterrupt()])
            connection = GatedHubConnection(
                pre_script=[{"type": "hello_ack", "server_time": "t"}],
                gated_message={"type": "queued", "request_id": "req-1",
                              "kind": "generate", "recipe_ref": "dev/requests-worker"})
            claimed = []

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                claimed.append(1)
                return {"batch_id": "b1", "generation_ids": []}

            services = make_services(directory, management, generate=fake_generate)
            services = dataclasses.replace(
                services, hub=HubFactory([connection]), ping_interval=0.05,
                backoff_max=1)

            done = threading.Event()

            def run():
                work(services, interval=30, once=False)
                done.set()

            worker = threading.Thread(target=run, daemon=True)
            start = time.monotonic()
            worker.start()
            # let pass 1 (claim generate_row) and pass 2 (claim None, enter
            # the idle wait) happen, then deliver the queued message.
            time.sleep(0.3)
            connection.release.set()
            self.assertTrue(done.wait(5))
            elapsed = time.monotonic() - start
            self.assertLess(elapsed, 5)
            self.assertEqual(len(claimed), 1)


class WorkOnceHubTest(unittest.TestCase):
    def test_sends_submit_phase_for_a_generate_row_after_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            row = generate_row()
            management = ManagementFake(claim_responses=[row])
            sent = []

            class RecordingListener:
                def send_progress(self, request_id, phase, **fields):
                    sent.append((request_id, phase))

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                return {"batch_id": "b1", "generation_ids": []}

            services = make_services(directory, management, generate=fake_generate)
            work_once(services, listener=RecordingListener())
            self.assertIn(("req-1", "submit"), sent)

    def test_sends_finalize_phase_for_a_finalize_row_after_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            row = finalize_row()
            management = ManagementFake(claim_responses=[row])
            sent = []

            class RecordingListener:
                def send_progress(self, request_id, phase, **fields):
                    sent.append((request_id, phase))

            def fake_finalize(generation_id, finalize_services, **kwargs):
                return {"batch_id": "b2", "generation_ids": []}

            services = make_services(directory, management, finalize=fake_finalize)
            work_once(services, listener=RecordingListener())
            self.assertIn(("req-2", "finalize"), sent)

    def test_relay_current_is_set_during_execute_and_cleared_after(self):
        with tempfile.TemporaryDirectory() as directory:
            row = generate_row()
            management = ManagementFake(claim_responses=[row])
            observed = {}

            class FakeRelay:
                current = None

            relay = FakeRelay()

            def fake_generate(path, generate_services, *, key_prefix=None, **kwargs):
                observed["during"] = relay.current
                return {"batch_id": "b1", "generation_ids": []}

            services = make_services(directory, management, generate=fake_generate)
            work_once(services, relay=relay)
            self.assertEqual(observed["during"], "req-1")
            self.assertIsNone(relay.current)


if __name__ == "__main__":
    unittest.main()
