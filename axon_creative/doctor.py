from __future__ import annotations

from typing import Any

from .client import ComfyUIClient
from .manifest import WorkflowManifest


def _required_for(item: dict[str, Any], variant: str) -> bool:
    return bool(item.get("required")) or variant in item.get("requiredFor", [])


def run_doctor(
    client: ComfyUIClient,
    manifests: dict[str, WorkflowManifest],
    variant: str,
) -> dict[str, Any]:
    report: dict[str, Any] = {"ok": True, "variant": variant, "checks": []}
    try:
        stats = client.get("/system_stats")
        report["checks"].append({"name": "server", "ok": True, "details": stats})
        object_info = client.get("/object_info")
    except Exception as exc:
        return {
            "ok": False,
            "variant": variant,
            "checks": [{"name": "server", "ok": False, "error": str(exc)}],
        }

    required_nodes: dict[str, dict[str, Any]] = {}
    for manifest in manifests.values():
        for node in manifest.data.get("requirements", {}).get("nodes", []):
            if _required_for(node, variant):
                required_nodes[node["classType"]] = node
    missing_nodes = sorted(name for name in required_nodes if name not in object_info)
    report["checks"].append(
        {
            "name": "nodes",
            "ok": not missing_nodes,
            "missing": [{"classType": name, "install": required_nodes[name].get("url", ""),
                         "requiredFor": required_nodes[name].get("requiredFor", ["all"])}
                        for name in missing_nodes],
        }
    )
    report["ok"] = report["ok"] and not missing_nodes

    model_checks = []
    seen: set[tuple[str, str]] = set()
    for manifest in manifests.values():
        for model in manifest.data.get("requirements", {}).get("models", []):
            if not _required_for(model, variant):
                continue
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
                 "requiredFor": model.get("requiredFor", ["all"]),
                 "download": model.get("url", ""), "details": available if not ok else None}
            )
    models_ok = all(item["ok"] for item in model_checks)
    report["checks"].append({"name": "models", "ok": models_ok, "items": model_checks})
    report["ok"] = report["ok"] and models_ok
    return report


def doctor_failure(report: dict[str, Any]) -> str:
    missing: list[str] = []
    for check in report.get("checks", []):
        if check.get("name") == "server" and not check.get("ok"):
            missing.append(f"ComfyUI: {check.get('error', 'unreachable')}")
        if check.get("name") == "nodes":
            missing.extend(item["classType"] for item in check.get("missing", []))
        if check.get("name") == "models":
            missing.extend(
                f"{item['folder']}/{item['name']}"
                for item in check.get("items", [])
                if not item.get("ok")
            )
    return "Environment is not ready: " + ", ".join(missing)
