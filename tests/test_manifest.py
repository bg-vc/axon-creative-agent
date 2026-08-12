import json
import tempfile
import unittest
from pathlib import Path

from axon_creative.errors import WorkflowError
from axon_creative.manifest import discover_manifests, load_api_workflow, load_manifest


ROOT = Path(__file__).resolve().parents[1]


class ManifestTests(unittest.TestCase):
    def test_discovers_three_workflows_and_variants(self):
        manifests = discover_manifests(ROOT)
        self.assertEqual(
            set(manifests),
            {"minimax-h3-t2v", "minimax-h3-i2v", "minimax-h3-r2v"},
        )
        for manifest in manifests.values():
            self.assertEqual(set(manifest.variants), {"official", "turbo", "accelerated"})
            for variant in manifest.variants:
                self.assertTrue(load_api_workflow(manifest, variant))

    def test_rejects_missing_contract_field(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps({"schemaVersion": 1}), encoding="utf-8")
            with self.assertRaises(WorkflowError):
                load_manifest(path)

    def test_rejects_workflow_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "manifest.json"
            data = {
                "schemaVersion": 1,
                "id": "bad",
                "mediaType": "video",
                "engine": "comfyui",
                "variants": {"official": {"api": "../outside.json"}},
                "requirements": {},
            }
            path.write_text(json.dumps(data), encoding="utf-8")
            (root.parent / "outside.json").write_text("{}", encoding="utf-8")
            try:
                with self.assertRaises(WorkflowError):
                    load_manifest(path).workflow_path("official")
            finally:
                (root.parent / "outside.json").unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
