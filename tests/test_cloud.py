import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from axon_creative.cloud import (
    CloudProfile,
    SSHTransport,
    cloud_doctor,
    cloud_run,
    load_profiles,
    save_profile,
    validate_profile,
)
from axon_creative.errors import ConfigurationError


class CloudTests(unittest.TestCase):
    @patch("axon_creative.cloud.shutil.which", side_effect=lambda name: f"/usr/bin/{name}")
    @patch("axon_creative.cloud.subprocess.run")
    def test_ssh_keeps_host_checking_and_uses_batch_timeout(self, run, _):
        run.return_value = Mock(returncode=0, stdout="", stderr="")
        SSHTransport("cloud-host").ssh(["true"])
        command = run.call_args.args[0]
        self.assertIn("BatchMode=yes", command)
        self.assertIn("ConnectTimeout=10", command)
        self.assertNotIn("StrictHostKeyChecking=no", command)

    def test_profile_round_trip_and_invalid_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = CloudProfile("cloud5090", "axon-5090", "/workspace/repo", "/workspace/input")
            save_profile(root, profile)
            self.assertEqual(load_profiles(root)["cloud5090"], profile)
            self.assertTrue((root / ".axon-creative/profiles.toml").is_file())
        for profile in (
            CloudProfile("bad.name", "host", "/repo", "/input"),
            CloudProfile("valid", "host;command", "/repo", "/input"),
            CloudProfile("valid", "host", "relative", "/input"),
            CloudProfile("valid", "host", "/repo/../escape", "/input"),
        ):
            with self.assertRaises(ConfigurationError):
                validate_profile(profile)

    @patch("axon_creative.cloud.subprocess.run")
    @patch("axon_creative.cloud.SSHTransport")
    def test_cloud_doctor_reports_version_mismatch(self, transport_class, run):
        root = Path("/repo")
        profile = CloudProfile("cloud", "host", "/remote/repo", "/remote/input")
        run.return_value = Mock(stdout="local-sha\n")
        transport = transport_class.return_value
        transport.ssh.side_effect = [
            Mock(stdout="remote-sha\n", returncode=0),
            Mock(stdout=json.dumps({"ok": True}), stderr="", returncode=0),
        ]
        report = cloud_doctor(root, profile, "accelerated", "minimax-h3-t2v")
        self.assertFalse(report["ok"])
        self.assertFalse(report["version"]["ok"])

    @patch("axon_creative.cloud.create_run_id", return_value="20260812T120000Z-abcdef12")
    @patch("axon_creative.cloud.SSHTransport")
    def test_cloud_run_uploads_downloads_and_cleans_current_upload(self, transport_class, _):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt = root / "prompt.txt"
            image = root / "frame.png"
            prompt.write_text("prompt", encoding="utf-8")
            image.write_bytes(b"png")
            profile = CloudProfile("cloud", "host", "/remote/repo", "/remote/input")
            transport = transport_class.return_value

            def ssh(arguments, check=True):
                if arguments[:2] == ["test", "-d"]:
                    return Mock(returncode=0, stdout="", stderr="")
                if "axon_creative" in arguments:
                    return Mock(returncode=0, stdout="{}", stderr="")
                return Mock(returncode=0, stdout="", stderr="")

            def download(remote, parent):
                run_dir = parent / "20260812T120000Z-abcdef12"
                run_dir.mkdir(parents=True)
                (run_dir / "manifest.json").write_text(
                    json.dumps({"status": "completed", "runId": run_dir.name}),
                    encoding="utf-8",
                )

            transport.ssh.side_effect = ssh
            transport.download_directory.side_effect = download
            record = cloud_run(
                root=root,
                profile=profile,
                workflow_id="minimax-h3-i2v",
                variant="accelerated",
                prompt_file=prompt,
                inputs={"first-frame": image},
                seed=7,
                timeout=60,
            )
            self.assertEqual(record["status"], "completed")
            self.assertEqual(transport.upload.call_count, 2)
            cleanup = [call.args[0] for call in transport.ssh.call_args_list if call.args[0][:2] == ["rm", "-rf"]]
            self.assertEqual(
                cleanup,
                [
                    ["rm", "-rf", "/remote/repo/runs/uploads/20260812T120000Z-abcdef12"],
                    ["rm", "-rf", "/remote/input/axon-creative/20260812T120000Z-abcdef12"],
                ],
            )
            for call in transport.ssh.call_args_list:
                if call.args[0][:2] == ["rm", "-rf"]:
                    self.assertFalse(call.kwargs["check"])

    @patch("axon_creative.cloud.create_run_id", return_value="20260812T120000Z-deadbeef")
    @patch("axon_creative.cloud.SSHTransport")
    def test_cloud_run_writes_manifest_when_remote_preflight_fails(self, transport_class, _):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt = root / "prompt.txt"
            prompt.write_text("prompt", encoding="utf-8")
            transport = transport_class.return_value

            def ssh(arguments, check=True):
                if arguments[:2] == ["test", "-d"]:
                    return Mock(returncode=1, stdout="", stderr="")
                if "axon_creative" in arguments:
                    return Mock(returncode=1, stdout="", stderr="missing model")
                return Mock(returncode=0, stdout="", stderr="")

            transport.ssh.side_effect = ssh
            with self.assertRaises(ConfigurationError):
                cloud_run(
                    root=root,
                    profile=CloudProfile("cloud", "host", "/remote/repo", "/remote/input"),
                    workflow_id="minimax-h3-t2v",
                    variant="accelerated",
                    prompt_file=prompt,
                    inputs={},
                    seed=None,
                    timeout=60,
                )
            record = json.loads(
                (root / "runs/20260812T120000Z-deadbeef/manifest.json").read_text()
            )
            self.assertEqual(record["status"], "failed")
            self.assertNotIn(str(root), json.dumps(record))

    @patch("axon_creative.cloud.create_run_id", return_value="20260812T120000Z-feedface")
    @patch("axon_creative.cloud.SSHTransport")
    def test_cloud_run_writes_manifest_when_upload_fails(self, transport_class, _):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt = root / "prompt.txt"
            prompt.write_text("prompt", encoding="utf-8")
            transport = transport_class.return_value
            transport.ssh.return_value = Mock(returncode=0, stdout="", stderr="")
            transport.upload.side_effect = ConfigurationError(
                f"SCP upload failed from {root} to host:/remote/repo"
            )
            with self.assertRaises(ConfigurationError):
                cloud_run(
                    root=root,
                    profile=CloudProfile("cloud", "host", "/remote/repo", "/remote/input"),
                    workflow_id="minimax-h3-t2v",
                    variant="accelerated",
                    prompt_file=prompt,
                    inputs={},
                    seed=None,
                    timeout=60,
                )
            record = json.loads(
                (root / "runs/20260812T120000Z-feedface/manifest.json").read_text()
            )
            self.assertEqual(record["status"], "failed")
            self.assertNotIn(str(root), record["error"])
            self.assertNotIn("to host:", record["error"])
            self.assertNotIn("/remote/repo", record["error"])


if __name__ == "__main__":
    unittest.main()
