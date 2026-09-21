"""Unit tests for the shared classify/record/upload/attach ingest helpers."""

from __future__ import annotations

import unittest

from comfyui_recipes.application.ingest import (
    attach_asset,
    classify_outputs,
    record_job,
)


class ManagementFake:
    def __init__(self):
        self.calls = []
        self._job_counter = 0

    def request(self, method, path, payload=None, multipart=None):
        self.calls.append((method, path, payload, multipart))
        if method == "POST" and path.endswith("/jobs"):
            self._job_counter += 1
            return {"id": f"job-{self._job_counter}"}
        return {}


class ClassifyOutputsTests(unittest.TestCase):
    def test_splits_raw_matte_and_delivered_by_filename(self):
        outputs = [
            {"filename": "a-matte.png"},
            {"filename": "a-delivered.png"},
            {"filename": "a.png"},
        ]
        pictures, delivereds, mattes = classify_outputs(outputs)
        self.assertEqual(pictures, [{"filename": "a.png"}])
        self.assertEqual(delivereds, [{"filename": "a-delivered.png"}])
        self.assertEqual(mattes, [{"filename": "a-matte.png"}])

    def test_no_matte_or_delivered(self):
        outputs = [{"filename": "only.png"}]
        pictures, delivereds, mattes = classify_outputs(outputs)
        self.assertEqual(pictures, outputs)
        self.assertEqual(delivereds, [])
        self.assertEqual(mattes, [])


class RecordJobTests(unittest.TestCase):
    def test_call_order_and_payloads(self):
        management = ManagementFake()
        job = record_job(management, "batch-1", key_prefix=None, index=0,
                         seed=7, prompt_id="prompt-1", graph={"n": 1})
        self.assertEqual(job, {"id": "job-1"})
        self.assertEqual(management.calls, [
            ("POST", "/api/v1/batches/batch-1/jobs",
             {"idempotency_key": management.calls[0][2]["idempotency_key"],
              "seed": 7, "index": 0}, None),
            ("PATCH", "/api/v1/jobs/job-1",
             {"status": "queued", "comfy_prompt_id": "prompt-1",
              "graph": {"n": 1}}, None),
            ("PATCH", "/api/v1/jobs/job-1", {"status": "completed"}, None),
        ])

    def test_idempotency_key_with_prefix(self):
        management = ManagementFake()
        record_job(management, "batch-1", key_prefix="run-x", index=2,
                  seed=1, prompt_id="p", graph={})
        self.assertEqual(management.calls[0][2]["idempotency_key"], "run-x:job:2")

    def test_idempotency_key_without_prefix_is_a_uuid(self):
        management = ManagementFake()
        record_job(management, "batch-1", key_prefix=None, index=0,
                  seed=1, prompt_id="p", graph={})
        key = management.calls[0][2]["idempotency_key"]
        self.assertNotIn(":job:", key)
        self.assertEqual(len(key), 36)


class AttachAssetTests(unittest.TestCase):
    def test_posts_multipart_asset(self):
        management = ManagementFake()
        attach_asset(management, "gen-1", role="mask", name="a.png", data=b"x")
        self.assertEqual(management.calls, [
            ("POST", "/api/v1/generations/gen-1/assets", None,
             ({"role": "mask"}, "file", "a.png", b"x", "image/png")),
        ])


if __name__ == "__main__":
    unittest.main()
