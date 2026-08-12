from __future__ import annotations

from typing import Any

from .client import ComfyUIClient
from .manifest import WorkflowManifest


def run_doctor(client: ComfyUIClient, manifests: dict[str, WorkflowManifest]) -> dict[str, Any]:
    report: dict[str, Any] = {"ok": True, "checks": []}
    try:
        stats = client.get("/system_stats")
        report["checks"].append({"name": "server", "ok": True, "details": stats})
        object_info = client.get("/object_info")
    except Exception as exc:
        return {"ok": False, "checks": [{"name": "server", "ok": False, "error": str(exc)}]}

    required_nodes: dict[str, dict[str, Any]] = {}
    for manifest in manifests.values():
        for node in manifest.data.get("requirements", {}).get("nodes", []):
            required_nodes[node["classType"]] = node
    missing_nodes = sorted(name for name in required_nodes if name not in object_info)
    blocking_nodes = [
        name for name in missing_nodes if required_nodes[name].get("required", True)
    ]
    report["checks"].append(
        {
            "name": "nodes",
            "ok": not blocking_nodes,
            "missing": [{"classType": name, "install": required_nodes[name].get("url", ""),
                         "requiredFor": required_nodes[name].get("requiredFor", ["all"])}
                        for name in missing_nodes],
        }
    )
    report["ok"] = report["ok"] and not blocking_nodes

    model_checks = []
    seen: set[tuple[str, str]] = set()
    for manifest in manifests.values():
        for model in manifest.data.get("requirements", {}).get("models", []):
            key = (model["folder"], model["name"])
            if key in seen:
                continue
            seen.add(key)
            try:
                available = client.get(f"/models/{model['folder']}")
                ok = model["name"] in available
            except Exception as exc:
                ok = False
                available = {"error": str(exc)}
            model_checks.append(
                {"folder": model["folder"], "name": model["name"], "ok": ok,
                 "required": model.get("required", False),
                 "requiredFor": model.get("requiredFor", ["all"]),
                 "download": model.get("url", ""), "details": available if not ok else None}
            )
    models_ok = all(item["ok"] for item in model_checks if item["required"])
    report["checks"].append({"name": "models", "ok": models_ok, "items": model_checks})
    report["ok"] = report["ok"] and models_ok
    return report
