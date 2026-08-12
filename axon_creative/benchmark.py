from __future__ import annotations

import json
import statistics
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from .errors import ConfigurationError


def _validate_suite(suite: dict[str, Any]) -> None:
    placeholders = [
        key
        for key, value in suite.get("environment", {}).items()
        if isinstance(value, str) and "FILL_AFTER_MEASUREMENT" in value
    ]
    if placeholders:
        raise ConfigurationError(
            "Fill benchmark environment values before running: "
            + ", ".join(placeholders)
        )
    if int(suite.get("measuredRuns", 0)) < 1:
        raise ConfigurationError("measuredRuns must be at least 1")


def run_suite(
    suite_path: Path,
    execute_case: Callable[[dict[str, Any]], dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    _validate_suite(suite)
    results: list[dict[str, Any]] = []
    for case in suite["cases"]:
        for variant in case["variants"]:
            execute_case({**case, "variant": variant, "phase": "warmup"})
            runs = [
                execute_case({**case, "variant": variant, "phase": "measured"})
                for _ in range(suite.get("measuredRuns", 3))
            ]
            elapsed = [float(run["elapsedSeconds"]) for run in runs]
            results.append(
                {
                    "workflowId": case["workflowId"],
                    "variant": variant,
                    "runs": runs,
                    "medianSeconds": statistics.median(elapsed),
                    "minSeconds": min(elapsed),
                    "maxSeconds": max(elapsed),
                }
            )
    report = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(UTC).isoformat(),
        "environment": suite["environment"],
        "results": results,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    lines = ["# RTX 5090 benchmark", "", "Measured results; lower is faster.", "", "| Workflow | Variant | Median | Min | Max |", "| --- | --- | ---: | ---: | ---: |"]
    for item in results:
        lines.append(
            f"| {item['workflowId']} | {item['variant']} | {item['medianSeconds']:.1f}s | "
            f"{item['minSeconds']:.1f}s | {item['maxSeconds']:.1f}s |"
        )
    (output_dir / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
