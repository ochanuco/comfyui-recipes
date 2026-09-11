"""Adapter-level tests for the repair use case, all collaborators faked."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from comfyui_recipes.application.repair import RepairServices, repair

SOURCE_GRAPH = {
    "3": {"class_type": "KSampler", "inputs": {
        "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
        "latent_image": ["5", 0], "seed": 1, "steps": 20, "cfg": 5,
        "sampler_name": "euler", "scheduler": "normal", "denoise": 1}},
    "4": {"class_type": "DiffusersLoader", "inputs": {"model_path": "m"}},
    "5": {"class_type": "EmptyLatentImage", "inputs": {}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {
        "clip": ["4", 1], "text": "masterpiece, (pantyhose feet:1.2)"}},
    "7": {"class_type": "CLIPTextEncode", "inputs": {
        "clip": ["4", 1], "text": "worst quality"}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
    "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "x"}},
}


def _pose_outputs() -> dict:
    """A minimal DWPreprocessor outputs dict with one detected right foot."""
    body = [0.0, 0.0, 0.0] * 18
    body[9 * 3:9 * 3 + 3] = [100.0, 300.0, 1.0]  # Rknee
    body[10 * 3:10 * 3 + 3] = [100.0, 500.0, 1.0]  # Rank
    frame = {
        "people": [{
            "pose_keypoints_2d": body, "face_keypoints_2d": None,
            "hand_left_keypoints_2d": None, "hand_right_keypoints_2d": None,
        }],
        "canvas_width": 800, "canvas_height": 1000,
    }
    return {"2": {"openpose_json": [json.dumps([frame])]}}


class ManagementFake:
    def __init__(self, *, batch_parameters=None, generations=None,
                batch_recipe="yukari"):
        self.calls = []
        self.context = {"batch": {"id": "source-batch"}}
        self.batch = {
            "id": "source-batch", "short_id": "srcbatch",
            "recipe": batch_recipe,
            "parameters": batch_parameters or {},
            "generations": generations or [],
        }
        self._job_counter = 0
        self.job_graph = None

    def request(self, method, path, payload=None, multipart=None):
        self.calls.append((method, path, payload, multipart))
        if path.endswith("/context"):
            return self.context
        if method == "GET" and path.startswith("/api/v1/generations/") \
                and path.count("/") == 4:
            return {"id": path.rsplit("/", 1)[1], "comfy_job": self.job_graph}
        if method == "GET" and path == f"/api/v1/batches/{self.batch['id']}":
            return self.batch
        if method == "POST" and path == "/api/v1/batches":
            return {"id": "repair-batch-id", "short_id": "repbatch"}
        if method == "POST" and path.endswith("/jobs"):
            self._job_counter += 1
            return {"id": f"job-{self._job_counter}"}
        if path.endswith("/generations"):
            seed = multipart[0]["seed"]
            index = multipart[0]["comfy_output_index"]
            gen_id = f"gen-{seed}-{index}"
            return {"id": gen_id, "short_id": gen_id,
                    "canonical_url": f"https://example/{gen_id}"}
        if path.endswith("/assets"):
            return {}
        return {}

    def fetch_generation_image(self, generation_id):
        return b"picked"


class ComfyFake:
    def __init__(self, *, outputs_per_job=None, pose_outputs=None):
        self.uploaded = []
        self.submitted = []
        self.outputs_per_job = outputs_per_job
        self.pose_outputs = pose_outputs if pose_outputs is not None else _pose_outputs()

    def upload_image(self, name, data):
        self.uploaded.append((name, data))
        return f"uploaded-{name}"

    def submit(self, graph):
        self.submitted.append(graph)
        return f"prompt-{len(self.submitted)}"

    def wait_for_outputs(self, prompt_id):
        return self.pose_outputs

    def wait_for(self, prompt_id):
        if self.outputs_per_job is not None:
            return self.outputs_per_job
        return [{"filename": f"{prompt_id}-out.png"}]

    def fetch(self, image):
        name = image["filename"]
        if "-matte" in name:
            return b"matte-bytes"
        if "-delivered" in name:
            return b"delivered-bytes"
        return b"raw-bytes"


class RecordingNotifier:
    def __init__(self):
        self.calls = []

    def send(self, *args):
        self.calls.append(args)


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
        pose_graph=lambda image_name, prefix="pose": {"pose-graph-for": image_name},
        repair_graph=lambda source, **kw: {"repair-graph": kw.get("seed")},
    )
    kwargs.update(overrides)
    return RepairServices(**kwargs)


def batch_call(services):
    return next(
        call for call in services.management.calls
        if call[0] == "POST" and call[1] == "/api/v1/batches")


class RepairApplicationTest(unittest.TestCase):
    def test_hires_chain_batch_picks_the_largest_sibling(self):
        with tempfile.TemporaryDirectory() as directory:
            fetched = []
            management = ManagementFake(
                batch_parameters={"kind": "hires-chain"},
                generations=[
                    {"id": "raw-gen", "short_id": "rawshort",
                     "image_width": 1280, "image_height": 2560},
                    {"id": "delivered-gen", "short_id": "delshort",
                     "image_width": 768, "image_height": 1536},
                ])
            management.fetch_generation_image = lambda gid: (
                fetched.append(gid) or b"picked")
            services = base_services(directory, management=management)
            repair("delivered-gen", services,
                  parts=[], regions=[[0.0, 0.0, 0.1, 0.1]])
            self.assertEqual(fetched, ["raw-gen"])

    def test_non_hires_chain_batch_uses_the_given_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            fetched = []
            management = ManagementFake(batch_parameters={"kind": "generate"})
            management.fetch_generation_image = lambda gid: (
                fetched.append(gid) or b"picked")
            services = base_services(directory, management=management)
            repair("gen-1", services, parts=[], regions=[[0.0, 0.0, 0.1, 0.1]])
            self.assertEqual(fetched, ["gen-1"])

    def test_a_given_context_and_batch_skip_their_fetch(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            repair("gen-1", services, parts=[], regions=[[0.0, 0.0, 0.1, 0.1]],
                  context={"batch": {"id": "source-batch"}},
                  batch=services.management.batch)
            fetch_calls = [
                call for call in services.management.calls
                if call[0] == "GET" and (
                    call[1].endswith("/context")
                    or call[1] == f"/api/v1/batches/{services.management.batch['id']}")]
            self.assertEqual(fetch_calls, [])

    def test_no_regions_found_raises_system_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            with self.assertRaises(SystemExit):
                repair("gen-1", services, parts=[], regions=[])

    def test_parts_empty_skips_the_pose_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = ComfyFake()
            services = base_services(directory, comfyui=comfy)
            repair("gen-1", services, parts=[], regions=[[0.0, 0.0, 0.1, 0.1]])
            pose_submissions = [g for g in comfy.submitted if "pose-graph-for" in g]
            self.assertEqual(pose_submissions, [])

    def test_parts_present_submits_the_pose_graph_first(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = ComfyFake()
            services = base_services(directory, comfyui=comfy)
            repair("gen-1", services, parts=["feet"])
            self.assertIn("pose-graph-for", comfy.submitted[0])

    def test_one_job_per_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = ComfyFake()
            services = base_services(directory, comfyui=comfy)
            result = repair("gen-1", services, parts=["feet"], seeds=[10, 20, 30])
            job_posts = [call for call in services.management.calls
                        if call[0] == "POST" and call[1].endswith("/jobs")]
            self.assertEqual(len(job_posts), 3)
            self.assertEqual(len(result["generation_ids"]), 3)

    def test_raw_output_uploaded_as_a_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = ComfyFake(outputs_per_job=[{"filename": "rep-out.png"}])
            services = base_services(directory, comfyui=comfy)
            repair("gen-1", services, parts=["feet"], seeds=[7])
            generation_posts = [call for call in services.management.calls
                                if call[0] == "POST" and call[1].endswith("/generations")]
            self.assertEqual(len(generation_posts), 1)
            metadata, field, filename, data, content_type = generation_posts[0][3]
            self.assertEqual(filename, "rep-out.png")
            self.assertEqual(data, b"raw-bytes")

    def test_matte_output_uploaded_as_a_mask_asset_on_the_raw_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = ComfyFake(outputs_per_job=[
                {"filename": "rep-out.png"}, {"filename": "rep-out-matte.png"}])
            services = base_services(directory, comfyui=comfy)
            repair("gen-1", services, parts=["feet"], seeds=[7])
            asset_posts = [call for call in services.management.calls
                          if call[0] == "POST" and call[1].endswith("/assets")]
            mask_posts = [call for call in asset_posts if call[3][0] == {"role": "mask"}]
            self.assertEqual(len(mask_posts), 1)
            self.assertEqual(mask_posts[0][3][2], "rep-out-matte.png")
            self.assertEqual(mask_posts[0][3][3], b"matte-bytes")

    def test_delivered_output_recorded_as_a_second_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = ComfyFake(outputs_per_job=[
                {"filename": "rep-out.png"}, {"filename": "rep-out-delivered.png"}])
            services = base_services(directory, comfyui=comfy)
            result = repair("gen-1", services, parts=["feet"], seeds=[7])
            generation_posts = [call for call in services.management.calls
                                if call[0] == "POST" and call[1].endswith("/generations")]
            self.assertEqual(len(generation_posts), 2)
            self.assertEqual(len(result["generation_ids"]), 2)

    def test_region_mask_uploaded_with_repair_mask_role(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = ComfyFake()
            services = base_services(directory, comfyui=comfy)
            repair("gen-1", services, parts=["feet"], seeds=[7])
            asset_posts = [call for call in services.management.calls
                          if call[0] == "POST" and call[1].endswith("/assets")]
            repair_mask_posts = [
                call for call in asset_posts if call[3][0] == {"role": "repair-mask"}]
            self.assertEqual(len(repair_mask_posts), 1)

    def test_no_raw_output_raises_system_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            comfy = ComfyFake(outputs_per_job=[])
            services = base_services(directory, comfyui=comfy)
            with self.assertRaises(SystemExit):
                repair("gen-1", services, parts=["feet"], seeds=[7])

    def test_batch_parameters_record_the_request(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            repair("gen-1", services, parts=["feet"], regions=[[0.1, 0.2, 0.3, 0.4]],
                  denoise=0.7, seeds=[5], size=768, pad=1.5)
            parameters = batch_call(services)[2]["parameters"]
            self.assertEqual(parameters["kind"], "repair")
            self.assertEqual(parameters["base_generation"], "gen-1")
            self.assertEqual(parameters["requested_generation"], "gen-1")
            self.assertEqual(parameters["parts"], ["feet"])
            self.assertEqual(parameters["regions"], [[0.1, 0.2, 0.3, 0.4]])
            self.assertEqual(parameters["denoise"], 0.7)
            self.assertEqual(parameters["size"], 768)
            self.assertEqual(parameters["pad"], 1.5)
            self.assertEqual(parameters["seeds"], [5])
            self.assertIn("mask_bbox", parameters)

    def test_key_prefix_derives_batch_and_job_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            repair("gen-1", services, parts=["feet"], seeds=[1], key_prefix="request:r1")
            posts = {call[1]: call[2] for call in services.management.calls
                     if call[0] == "POST" and call[2]}
            self.assertEqual(posts["/api/v1/batches"]["idempotency_key"], "request:r1")
            self.assertEqual(
                posts["/api/v1/batches/repair-batch-id/jobs"]["idempotency_key"],
                "request:r1:job:0")

    def test_returns_batch_id_and_generation_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            result = repair("gen-1", services, parts=["feet"], seeds=[1, 2])
            self.assertEqual(result["batch_id"], "repair-batch-id")
            self.assertEqual(len(result["generation_ids"]), 2)

    def test_lora_reaches_the_graph_builder(self):
        with tempfile.TemporaryDirectory() as directory:
            seen = {}

            def fake_repair_graph(source, **kwargs):
                seen["loras"] = kwargs.get("loras")
                return {"repair-graph": kwargs.get("seed")}

            services = base_services(directory, repair_graph=fake_repair_graph)
            repair("gen-1", services, parts=["feet"], seeds=[1], lora=0.8)
            self.assertEqual(seen["loras"], (("feet-xl-ill.safetensors", 0.8),))

    def test_no_lora_reaches_the_graph_builder_as_an_empty_tuple(self):
        with tempfile.TemporaryDirectory() as directory:
            seen = {}

            def fake_repair_graph(source, **kwargs):
                seen["loras"] = kwargs.get("loras")
                return {"repair-graph": kwargs.get("seed")}

            services = base_services(directory, repair_graph=fake_repair_graph)
            repair("gen-1", services, parts=["feet"], seeds=[1])
            self.assertEqual(seen["loras"], ())

    def test_lora_is_recorded_in_batch_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            repair("gen-1", services, parts=["feet"], seeds=[1], lora=0.8)
            parameters = batch_call(services)[2]["parameters"]
            self.assertEqual(parameters["lora"], 0.8)

    def test_lora_defaults_to_none_in_batch_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            repair("gen-1", services, parts=["feet"], seeds=[1])
            parameters = batch_call(services)[2]["parameters"]
            self.assertIsNone(parameters["lora"])

    def test_notifier_is_sent_once_after_the_batch_completes(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            repair("gen-1", services, parts=["feet"], seeds=[1, 2])
            self.assertEqual(len(services.notifier.calls), 1)

    def test_batch_marked_completed_after_all_jobs(self):
        with tempfile.TemporaryDirectory() as directory:
            services = base_services(directory)
            repair("gen-1", services, parts=["feet"], seeds=[1, 2])
            completed = [call for call in services.management.calls
                        if call[0] == "PATCH"
                        and call[1] == "/api/v1/batches/repair-batch-id"
                        and call[2] == {"status": "completed"}]
            self.assertEqual(len(completed), 1)


if __name__ == "__main__":
    unittest.main()


class SourceGraphFromJobTest(unittest.TestCase):
    def test_the_job_graph_wins_over_the_png_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            management = ManagementFake()
            job_graph = dict(SOURCE_GRAPH)
            management.job_graph = {"graph": job_graph}
            seen = {}

            def fake_repair_graph(source, **kwargs):
                seen["source"] = source
                return {"repair-graph": kwargs.get("seed")}

            services = base_services(
                directory, management=management,
                graph_from_png=lambda data: {"png": "stale"},
                repair_graph=fake_repair_graph)
            repair("gen-1", services, parts=(),
                   regions=((0.1, 0.1, 0.5, 0.5),), seeds=(1,))
            self.assertIs(seen["source"], job_graph)

    def test_a_record_without_a_job_graph_falls_back_to_the_png(self):
        with tempfile.TemporaryDirectory() as directory:
            seen = {}

            def fake_repair_graph(source, **kwargs):
                seen["source"] = source
                return {"repair-graph": kwargs.get("seed")}

            services = base_services(directory, repair_graph=fake_repair_graph)
            repair("gen-1", services, parts=(),
                   regions=((0.1, 0.1, 0.5, 0.5),), seeds=(1,))
            self.assertIs(seen["source"], SOURCE_GRAPH)
