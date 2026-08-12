import unittest
from pathlib import Path

from axon_creative.doctor import doctor_failure, run_doctor
from axon_creative.manifest import discover_manifests


ROOT = Path(__file__).resolve().parents[1]


class FakeClient:
    def __init__(self, include_acceleration: bool):
        self.include_acceleration = include_acceleration

    def get(self, path):
        if path == "/system_stats":
            return {"system": "test"}
        if path == "/object_info":
            nodes = {"MiniMaxH3ImageToVideo": {}}
            if self.include_acceleration:
                nodes.update({"MiniMaxH3TurboLoRA": {}, "SolAttnPatch": {}})
            return nodes
        if path == "/models/diffusion_models":
            return ["minimax_h3_fl2va_pruned_int8_convrot.safetensors"]
        if path == "/models/text_encoders":
            return ["qwen3vl_32b_minimax_h3_int8_convrot.safetensors"]
        if path == "/models/vae":
            return [
                "minimax_h3_video_vae_fp16.safetensors",
                "minimax_h3_audio_vae_fp32.safetensors",
            ]
        if path == "/models/loras":
            return (
                ["minimax_h3_turbo_v4_step600_ema.safetensors"]
                if self.include_acceleration
                else []
            )
        raise AssertionError(path)


class DoctorTests(unittest.TestCase):
    def test_official_does_not_require_acceleration(self):
        manifest = discover_manifests(ROOT)["minimax-h3-t2v"]
        report = run_doctor(FakeClient(False), {manifest.id: manifest}, "official")
        self.assertTrue(report["ok"])

    def test_accelerated_reports_exact_missing_dependencies(self):
        manifest = discover_manifests(ROOT)["minimax-h3-t2v"]
        report = run_doctor(FakeClient(False), {manifest.id: manifest}, "accelerated")
        self.assertFalse(report["ok"])
        message = doctor_failure(report)
        self.assertIn("MiniMaxH3TurboLoRA", message)
        self.assertIn("SolAttnPatch", message)
        self.assertIn("loras/minimax_h3_turbo", message)


if __name__ == "__main__":
    unittest.main()
