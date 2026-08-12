from __future__ import annotations

from typing import Any

from .manifest import WorkflowManifest


def required_for(item: dict[str, Any], variant: str) -> bool:
    return bool(item.get("required")) or variant in item.get("requiredFor", [])


def inspect_workflow(manifest: WorkflowManifest, variant: str) -> dict[str, Any]:
    requirements = manifest.data.get("requirements", {})
    assets = manifest.data.get("assets", {})
    next_steps = ["Drag uiWorkflow into ComfyUI."]
    if any(spec.get("kind") == "image" for spec in assets.values()):
        next_steps.append(
            "Copy docs/assets/axon-signal-reference.png to ComfyUI/input, "
            "or choose your own image in the LoadImage node."
        )
    next_steps.extend(
        [
            "Install missing nodes shown by ComfyUI Manager; update ComfyUI when a core node is missing.",
            "Install every listed model in ComfyUI/models/<folder>, then restart ComfyUI.",
            "Run a 5-10 second test in the UI before API automation.",
        ]
    )
    return {
        "workflowId": manifest.id,
        "title": manifest.title,
        "variant": variant,
        "uiWorkflow": str(manifest.workflow_path(variant, "ui")),
        "apiWorkflow": str(manifest.workflow_path(variant, "api")),
        "inputs": [
            {
                "name": name,
                "kind": spec["kind"],
                "required": bool(spec.get("required")),
            }
            for name, spec in assets.items()
        ],
        "models": [
            {
                "folder": model["folder"],
                "name": model["name"],
                "url": model.get("url", ""),
            }
            for model in requirements.get("models", [])
            if required_for(model, variant)
        ],
        "nodes": [
            {
                "classType": node["classType"],
                "source": node.get("source", ""),
                "url": node.get("url", ""),
            }
            for node in requirements.get("nodes", [])
            if required_for(node, variant)
        ],
        "nextSteps": next_steps,
    }
