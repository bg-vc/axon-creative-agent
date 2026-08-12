import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from axon_creative.errors import ConfigurationError
from axon_creative.manifest import discover_manifests
from axon_creative.runner import (
    ensure_safe_server,
    parse_inputs,
    prepare_workflow,
    validate_run_id,
)


ROOT = Path(__file__).resolve().parents[1]


class RunnerTests(unittest.TestCase):
    def test_run_id_rejects_path_or_shell_characters(self):
        self.assertEqual(validate_run_id("20260812T120000Z-abcdef12"), "20260812T120000Z-abcdef12")
        for value in ("../escape", "short", "run;command", "run/child"):
            with self.assertRaises(ConfigurationError):
                validate_run_id(value)

    def test_loopback_allowed_and_remote_requires_flag(self):
        ensure_safe_server("http://127.0.0.1:8188", False)
        ensure_safe_server("http://localhost:8188", False)
        with self.assertRaises(ConfigurationError):
            ensure_safe_server("https://example.com", False)
        ensure_safe_server("https://example.com", True)

    def test_credentials_in_url_are_rejected(self):
        with self.assertRaises(ConfigurationError):
            ensure_safe_server("http://user:secret@127.0.0.1:8188", False)

    def test_parse_inputs_rejects_duplicates_and_missing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frame.png"
            path.write_bytes(b"png")
            self.assertEqual(parse_inputs([f"frame={path}"])["frame"], path.resolve())
            with self.assertRaises(ConfigurationError):
                parse_inputs([f"frame={path}", f"frame={path}"])
            with self.assertRaises(ConfigurationError):
                parse_inputs(["frame=/does/not/exist"])

    def test_prompt_seed_and_uploaded_image_are_mapped(self):
        manifest = discover_manifests(ROOT)["minimax-h3-i2v"]
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "frame.png"
            image.write_bytes(b"png")
            client = Mock()
            client.upload_image.return_value = {
                "name": "frame.png",
                "subfolder": "axon-creative/run",
                "type": "input",
            }
            workflow = prepare_workflow(
                manifest,
                "accelerated",
                "new prompt",
                42,
                {"first-frame": image},
                client,
                "run",
                None,
            )
            self.assertEqual(workflow["9"]["inputs"]["prompt"], "new prompt")
            self.assertEqual(workflow["10"]["inputs"]["noise_seed"], 42)
            self.assertEqual(
                workflow["20"]["inputs"]["image"], "axon-creative/run/frame.png"
            )

    def test_optional_reference_nodes_are_pruned(self):
        manifest = discover_manifests(ROOT)["minimax-h3-r2v"]
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "character.png"
            image.write_bytes(b"png")
            client = Mock()
            client.upload_image.return_value = {
                "name": image.name,
                "subfolder": "axon-creative/run",
            }
            workflow = prepare_workflow(
                manifest, "official", "prompt", 7, {"picture": image}, client, "run", None
            )
            self.assertNotIn("21", workflow)
            self.assertNotIn("22", workflow)
            self.assertNotIn("23", workflow)
            self.assertNotIn("ref_videos.ref_video_0", workflow["9"]["inputs"])
            self.assertNotIn("ref_audios.ref_audio_0", workflow["9"]["inputs"])


if __name__ == "__main__":
    unittest.main()
