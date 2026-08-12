from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .manifest import discover_manifests, load_api_workflow


BANNED = ("蜘蛛侠", "spider-man", "exec-", "/Users/", "C:\\Users\\")


def _headings(path: Path) -> list[str]:
    return [re.sub(r"^#+\s+", "", line).strip() for line in path.read_text(encoding="utf-8").splitlines() if re.match(r"^#{1,3}\s+", line)]


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []
    manifests = discover_manifests(root)
    if not manifests:
        errors.append("No workflow manifests found")
    for manifest in manifests.values():
        for variant in manifest.variants:
            for kind in ("ui", "api"):
                try:
                    path = manifest.workflow_path(variant, kind)
                    text = path.read_text(encoding="utf-8")
                    json.loads(text)
                    lowered = text.lower()
                    for banned in BANNED:
                        if banned.lower() in lowered:
                            errors.append(f"{path}: contains banned private/copyright marker {banned!r}")
                except Exception as exc:
                    errors.append(str(exc))
            try:
                workflow = load_api_workflow(manifest, variant)
                for mapping in list(manifest.data.get("parameters", {}).values()) + list(manifest.data.get("assets", {}).values()):
                    node = workflow.get(str(mapping["nodeId"]))
                    if not node or mapping["input"] not in node["inputs"]:
                        errors.append(
                            f"{manifest.id}/{variant}: mapping {mapping['nodeId']}.{mapping['input']} missing"
                        )
            except Exception as exc:
                errors.append(str(exc))
    english = _headings(root / "README.md")
    chinese = _headings(root / "README.zh-CN.md")
    if len(english) != len(chinese):
        errors.append("English and Chinese README heading counts differ")
    return errors
