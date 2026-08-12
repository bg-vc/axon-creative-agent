import json
import tempfile
import unittest
from pathlib import Path

from axon_creative.benchmark import run_suite
from axon_creative.errors import ConfigurationError


class BenchmarkTests(unittest.TestCase):
    def test_warmup_and_three_runs_generate_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            suite = root / "suite.json"
            suite.write_text(
                json.dumps(
                    {
                        "environment": {"gpu": "test"},
                        "measuredRuns": 3,
                        "cases": [{"workflowId": "w", "variants": ["official"]}],
                    }
                ),
                encoding="utf-8",
            )
            calls = []
            def execute(case):
                calls.append(case["phase"])
                return {"elapsedSeconds": float(len(calls))}
            report = run_suite(suite, execute, root / "out")
            self.assertEqual(calls, ["warmup", "measured", "measured", "measured"])
            self.assertEqual(report["results"][0]["medianSeconds"], 3.0)
            self.assertTrue((root / "out/results.json").is_file())
            self.assertTrue((root / "out/results.md").is_file())

    def test_refuses_placeholder_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            suite = root / "suite.json"
            suite.write_text(
                json.dumps(
                    {
                        "environment": {"driver": "FILL_AFTER_MEASUREMENT"},
                        "measuredRuns": 3,
                        "cases": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigurationError):
                run_suite(suite, lambda case: case, root / "out")


if __name__ == "__main__":
    unittest.main()
