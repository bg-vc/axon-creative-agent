import unittest
from pathlib import Path

from axon_creative.inspection import inspect_workflow
from axon_creative.manifest import discover_manifests


ROOT = Path(__file__).resolve().parents[1]


class InspectionTests(unittest.TestCase):
    def test_all_workflow_variants_have_ui_and_exact_dependencies(self):
        for manifest in discover_manifests(ROOT).values():
            for variant in manifest.variants:
                report = inspect_workflow(manifest, variant)
                self.assertTrue(Path(report["uiWorkflow"]).is_file())
                self.assertTrue(report["models"])
                node_types = {item["classType"] for item in report["nodes"]}
                self.assertEqual(
                    "MiniMaxH3TurboLoRA" in node_types,
                    variant in {"turbo", "accelerated"},
                )
                self.assertEqual("SolAttnPatch" in node_types, variant == "accelerated")

    def test_image_workflow_explains_first_ui_asset(self):
        manifest = discover_manifests(ROOT)["minimax-h3-i2v"]
        report = inspect_workflow(manifest, "accelerated")
        self.assertTrue(any("ComfyUI/input" in step for step in report["nextSteps"]))


if __name__ == "__main__":
    unittest.main()
