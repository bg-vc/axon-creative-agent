from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .manifest import discover_manifests, load_api_workflow
from .inspection import required_for


BANNED = ("蜘蛛侠", "spider-man", "exec-", "/Users/", "C:\\Users\\")
MODEL_LOADERS = {
    "UNETLoader": ("diffusion_models", "unet_name"),
    "CLIPLoader": ("text_encoders", "clip_name"),
    "VAELoader": ("vae", "vae_name"),
    "MiniMaxH3TurboLoRA": ("loras", "lora_name"),
}


def _headings(path: Path) -> list[str]:
    return [re.sub(r"^#+\s+", "", line).strip() for line in path.read_text(encoding="utf-8").splitlines() if re.match(r"^#{1,3}\s+", line)]


def _ui_nodes(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = list(workflow.get("nodes", []))
    for subgraph in workflow.get("definitions", {}).get("subgraphs", []):
        nodes.extend(subgraph.get("nodes", []))
    return nodes


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
                ui_path = manifest.workflow_path(variant, "ui")
                ui_workflow = json.loads(ui_path.read_text(encoding="utf-8"))
                if "anomalous_hashes" in ui_workflow.get("extra", {}):
                    errors.append(f"{manifest.id}/{variant}: UI contains stale model hashes")
                expected_models = {
                    (item["folder"], item["name"])
                    for item in manifest.data.get("requirements", {}).get("models", [])
                    if required_for(item, variant)
                }
                api_models = {
                    (folder, node["inputs"][input_name])
                    for node in workflow.values()
                    if node["class_type"] in MODEL_LOADERS
                    for folder, input_name in [MODEL_LOADERS[node["class_type"]]]
                }
                ui_models = {
                    (folder, node.get("widgets_values", [None])[0])
                    for node in _ui_nodes(ui_workflow)
                    if node.get("type") in MODEL_LOADERS and node.get("widgets_values")
                    for folder, _ in [MODEL_LOADERS[node["type"]]]
                }
                if api_models != expected_models:
                    errors.append(f"{manifest.id}/{variant}: API models differ from manifest")
                if ui_models != expected_models:
                    errors.append(f"{manifest.id}/{variant}: UI models differ from manifest")
                notes = "\n".join(
                    str(value)
                    for node in _ui_nodes(ui_workflow)
                    if node.get("title") == "Note: Model Links"
                    for value in node.get("widgets_values", [])
                )
                for _, model_name in expected_models:
                    if model_name not in notes:
                        errors.append(
                            f"{manifest.id}/{variant}: UI model note omits {model_name}"
                        )
                for mapping in list(manifest.data.get("parameters", {}).values()) + list(manifest.data.get("assets", {}).values()):
                    node = workflow.get(str(mapping["nodeId"]))
                    if not node or mapping["input"] not in node["inputs"]:
                        errors.append(
                            f"{manifest.id}/{variant}: mapping {mapping['nodeId']}.{mapping['input']} missing"
                        )
                for node_id, node in workflow.items():
                    for input_name, value in node["inputs"].items():
                        if (
                            isinstance(value, list)
                            and len(value) == 2
                            and isinstance(value[0], str)
                            and isinstance(value[1], int)
                            and value[0] not in workflow
                        ):
                            errors.append(
                                f"{manifest.id}/{variant}: {node_id}.{input_name} "
                                f"references missing node {value[0]}"
                            )
                classes = {node["class_type"] for node in workflow.values()}
                has_turbo = "MiniMaxH3TurboLoRA" in classes
                has_sol = "SolAttnPatch" in classes
                if has_turbo != (variant in {"turbo", "accelerated"}):
                    errors.append(f"{manifest.id}/{variant}: Turbo node does not match variant")
                if has_sol != (variant == "accelerated"):
                    errors.append(f"{manifest.id}/{variant}: Sol-Attn node does not match variant")
            except Exception as exc:
                errors.append(str(exc))
    english = _headings(root / "README.md")
    chinese = _headings(root / "README.zh-CN.md")
    if len(english) != len(chinese):
        errors.append("English and Chinese README heading counts differ")
    return errors
