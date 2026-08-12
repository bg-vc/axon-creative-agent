from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import WorkflowError


@dataclass(frozen=True)
class WorkflowManifest:
    path: Path
    data: dict[str, Any]

    @property
    def id(self) -> str:
        return str(self.data["id"])

    @property
    def title(self) -> str:
        return str(self.data.get("title", self.id))

    @property
    def variants(self) -> dict[str, dict[str, Any]]:
        return dict(self.data["variants"])

    def workflow_path(self, variant: str, kind: str = "api") -> Path:
        try:
            relative = self.variants[variant][kind]
        except KeyError as exc:
            raise WorkflowError(
                f"Workflow {self.id!r} has no {kind!r} file for variant {variant!r}"
            ) from exc
        path = (self.path.parent / relative).resolve()
        if self.path.parent.resolve() not in path.parents:
            raise WorkflowError(f"Workflow path escapes its directory: {relative}")
        if not path.is_file():
            raise WorkflowError(f"Workflow file does not exist: {path}")
        return path


def load_manifest(path: Path) -> WorkflowManifest:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"Cannot read manifest {path}: {exc}") from exc
    required = {"schemaVersion", "id", "mediaType", "engine", "variants", "requirements"}
    missing = sorted(required - data.keys())
    if missing:
        raise WorkflowError(f"Manifest {path} is missing: {', '.join(missing)}")
    if data["schemaVersion"] != 1 or data["engine"] != "comfyui":
        raise WorkflowError(f"Unsupported manifest contract in {path}")
    return WorkflowManifest(path=path.resolve(), data=data)


def discover_manifests(root: Path) -> dict[str, WorkflowManifest]:
    result: dict[str, WorkflowManifest] = {}
    for path in sorted((root / "workflows").glob("**/manifest.json")):
        manifest = load_manifest(path)
        if manifest.id in result:
            raise WorkflowError(f"Duplicate workflow id: {manifest.id}")
        result[manifest.id] = manifest
    return result


def load_api_workflow(manifest: WorkflowManifest, variant: str) -> dict[str, Any]:
    path = manifest.workflow_path(variant, "api")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"Cannot read API workflow {path}: {exc}") from exc
    if not isinstance(data, dict) or not data:
        raise WorkflowError(f"API workflow must be a non-empty object: {path}")
    for node_id, node in data.items():
        if not isinstance(node, dict) or "class_type" not in node or "inputs" not in node:
            raise WorkflowError(f"Invalid API node {node_id!r} in {path}")
    return data
