"""Adapter-level tests for the masked redraw use case, all collaborators faked."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from comfyui_recipes.application.masked_redraw import (
    MaskedRedrawServices,
    masked_redraw,
)
from test_repair_application import (
    SOURCE_GRAPH,
    ComfyFake,
    ManagementFake,
    RecordingNotifier,
)

REGIONS = [[0.1, 0.1, 0.5, 0.5]]


def base_services(directory, **overrides):
    kwargs = dict(
        management=ManagementFake(),
        comfyui=ComfyFake(),
        graph_from_png=lambda data: SOURCE_GRAPH,
        image_size=lambda data: (800, 1000),
        git_metadata=lambda: {"commit": "commit", "dirty": False},
        notifier=RecordingNotifier(),
        output_root=Path(directory),
        emit=lambda message: None,
        masked_redraw_graph=lambda source, **kw: {"graph": kw.get("seed")},
    )
    kwargs.update(overrides)
    return MaskedRedrawServices(**kwargs)


class MaskedRedrawApplicationTest(unittest.TestCase):
    def test_worker_request_reports_resolution_and_jobs_source_the_redraw(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake(
                request_parameters={"kind": "hires-chain"},
                generations=[
                    {"id": "raw-gen", "short_id": "rawshort",
                     "image_width": 1280, "image_height": 2560},
                    {"id": "delivered-gen", "short_id": "delshort",
                     "image_width": 768, "image_height": 1536}])
            services = base_services(directory, management=management)
            result = masked_redraw(
                "delivered-gen", services, regions=REGIONS, prompt_patch="a dress",
                seeds=[1, 2], key_prefix="request:r1", request_id="r1")
            calls = management.calls
            self.assertFalse(any(call[1] == "/api/v1/requests" for call in calls))
            resolution = next(
                call for call in calls if call[1] == "/api/v1/requests/r1/resolution")
            self.assertEqual(resolution[0], "PUT")
            self.assertEqual(resolution[2]["raw_instruction"], "a dress")
            self.assertEqual(
                resolution[2]["references"][0]["source_generation_id"], "raw-gen")
            jobs = [call for call in calls if call[1].endswith("/jobs")]
            self.assertEqual(len(jobs), 2)
            for job in jobs:
                self.assertEqual(job[1], "/api/v1/requests/repair-request-id/jobs")
                self.assertEqual(job[2]["source_generation_id"], "raw-gen")
            self.assertNotIn("batch_id", result)
            self.assertEqual(len(result["generation_ids"]), 2)

    def test_standalone_run_imports_and_jobs_carry_no_source(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            masked_redraw("gen-1", services, regions=REGIONS,
                          prompt_patch="a dress", seeds=[1])
            calls = services.management.calls
            create = next(call for call in calls if call[1] == "/api/v1/requests")
            self.assertEqual(create[2]["kind"], "import")
            self.assertEqual(create[2]["parameters"]["kind"], "masked_redraw")
            job_call = next(call for call in calls if call[1].endswith("/jobs"))
            self.assertNotIn("source_generation_id", job_call[2])
            self.assertFalse(any(
                call[0] == "PATCH" and call[1].startswith("/api/v1/requests/")
                for call in calls))


if __name__ == "__main__":
    unittest.main()
