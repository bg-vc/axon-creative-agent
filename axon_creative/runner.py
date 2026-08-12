from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
import os
import shutil
import socket
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .client import ComfyUIClient
from .errors import ComfyUIError, ConfigurationError, WorkflowError
from .manifest import WorkflowManifest, load_api_workflow


def ensure_safe_server(url: str, allow_remote: bool) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ConfigurationError(f"Invalid ComfyUI URL: {url}")
    if parsed.username or parsed.password:
        raise ConfigurationError("Do not put credentials in the ComfyUI URL")
    if allow_remote:
        return
    host = parsed.hostname
    if host == "localhost":
        return
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port)}
    except socket.gaierror as exc:
        raise ConfigurationError(f"Cannot resolve ComfyUI host {host!r}") from exc
    if not addresses or any(not ipaddress.ip_address(address).is_loopback for address in addresses):
        raise ConfigurationError(
            "Remote ComfyUI URLs require --allow-remote; prefer an SSH tunnel to a public listener"
        )


def set_node_input(workflow: dict[str, Any], node_id: str, name: str, value: Any) -> None:
    try:
        workflow[str(node_id)]["inputs"][name] = value
    except KeyError as exc:
        raise WorkflowError(f"Cannot map {name!r}: node {node_id!r} is missing") from exc


def parse_inputs(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ConfigurationError(f"Input must use NAME=PATH: {value}")
        name, raw_path = value.split("=", 1)
        if not name or name in result:
            raise ConfigurationError(f"Duplicate or empty input name: {name!r}")
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file():
            raise ConfigurationError(f"Input file does not exist: {path}")
        result[name] = path
    return result


def _safe_copy(source: Path, input_root: Path, run_id: str) -> str:
    root = input_root.expanduser().resolve()
    if not root.is_dir():
        raise ConfigurationError(f"ComfyUI input directory does not exist: {root}")
    target_dir = (root / "axon-creative" / run_id).resolve()
    if root not in target_dir.parents:
        raise ConfigurationError("Computed ComfyUI input path escaped its root")
    target_dir.mkdir(parents=True, exist_ok=False)
    target = target_dir / source.name
    if target.exists():
        raise ConfigurationError(f"Refusing to overwrite ComfyUI input: {target}")
    shutil.copy2(source, target)
    return str(Path("axon-creative") / run_id / source.name).replace("\\", "/")


def prepare_workflow(
    manifest: WorkflowManifest,
    variant: str,
    prompt: str,
    seed: int | None,
    supplied_inputs: dict[str, Path],
    client: ComfyUIClient,
    run_id: str,
    comfy_input_dir: Path | None,
) -> dict[str, Any]:
    workflow = copy.deepcopy(load_api_workflow(manifest, variant))
    parameters = manifest.data.get("parameters", {})
    if "prompt" in parameters:
        mapping = parameters["prompt"]
        set_node_input(workflow, mapping["nodeId"], mapping["input"], prompt)
    if seed is not None and "seed" in parameters:
        mapping = parameters["seed"]
        set_node_input(workflow, mapping["nodeId"], mapping["input"], seed)

    declared = manifest.data.get("assets", {})
    unknown = sorted(set(supplied_inputs) - set(declared))
    if unknown:
        raise ConfigurationError(f"Unknown input(s): {', '.join(unknown)}")
    missing = [name for name, spec in declared.items() if spec.get("required") and name not in supplied_inputs]
    if missing:
        raise ConfigurationError(f"Missing required input(s): {', '.join(missing)}")

    prune_ids: set[str] = set()
    for name, spec in declared.items():
        if name not in supplied_inputs:
            prune_ids.update(str(node_id) for node_id in spec.get("pruneNodes", []))
    if prune_ids:
        for node_id in prune_ids:
            workflow.pop(node_id, None)
        for node in workflow.values():
            node["inputs"] = {
                key: value
                for key, value in node["inputs"].items()
                if not (
                    isinstance(value, list)
                    and len(value) == 2
                    and str(value[0]) in prune_ids
                )
            }

    copied_dir_created = False
    for name, path in supplied_inputs.items():
        spec = declared[name]
        kind = spec["kind"]
        if kind == "image":
            uploaded = client.upload_image(path, f"axon-creative/{run_id}")
            remote_name = "/".join(
                part for part in (uploaded.get("subfolder", ""), uploaded.get("name", path.name)) if part
            )
        elif kind in {"video", "audio"}:
            if comfy_input_dir is None:
                raise ConfigurationError(
                    f"--comfy-input-dir is required for {kind} input {name!r}"
                )
            if copied_dir_created:
                target_dir = comfy_input_dir.resolve() / "axon-creative" / run_id
                target = target_dir / path.name
                if target.exists():
                    raise ConfigurationError(f"Refusing to overwrite ComfyUI input: {target}")
                shutil.copy2(path, target)
                remote_name = str(Path("axon-creative") / run_id / path.name).replace("\\", "/")
            else:
                remote_name = _safe_copy(path, comfy_input_dir, run_id)
                copied_dir_created = True
        else:
            raise WorkflowError(f"Unsupported asset kind: {kind}")
        set_node_input(workflow, spec["nodeId"], spec["input"], remote_name)
    return workflow


def _find_output_files(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if "filename" in value and isinstance(value["filename"], str):
            found.append(value)
        for nested in value.values():
            found.extend(_find_output_files(nested))
    elif isinstance(value, list):
        for nested in value:
            found.extend(_find_output_files(nested))
    return found


def inspect_media(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,size:stream=index,codec_type,codec_name,width,height,r_frame_rate,channels",
        "-of", "json", str(path),
    ]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        return json.loads(completed.stdout)
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        return {"warning": f"ffprobe inspection unavailable: {exc}"}


def execute(
    *,
    root: Path,
    manifest: WorkflowManifest,
    variant: str,
    prompt: str,
    seed: int | None,
    inputs: dict[str, Path],
    client: ComfyUIClient,
    comfy_input_dir: Path | None,
    poll_interval: float,
    timeout: float,
) -> dict[str, Any]:
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    run_dir = root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    record: dict[str, Any] = {
        "schemaVersion": 1,
        "runId": run_id,
        "workflowId": manifest.id,
        "variant": variant,
        "startedAt": datetime.now(UTC).isoformat(),
        "status": "preparing",
        "seed": seed,
        "inputs": {name: path.name for name, path in inputs.items()},
    }
    record_path = run_dir / "manifest.json"
    try:
        workflow = prepare_workflow(
            manifest, variant, prompt, seed, inputs, client, run_id, comfy_input_dir
        )
        encoded = json.dumps(workflow, sort_keys=True, separators=(",", ":")).encode()
        record["workflowSha256"] = hashlib.sha256(encoded).hexdigest()
        prompt_id = client.submit(workflow, client_id=uuid.uuid4().hex)
        record.update({"promptId": prompt_id, "status": "running"})
        deadline = time.monotonic() + timeout
        history_entry: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            history = client.get(f"/history/{prompt_id}")
            if isinstance(history, dict) and prompt_id in history:
                history_entry = history[prompt_id]
                break
            time.sleep(poll_interval)
        if history_entry is None:
            raise ComfyUIError(f"Timed out after {timeout:.0f}s waiting for {prompt_id}")
        status = history_entry.get("status", {})
        if status.get("status_str") not in {None, "success"} or status.get("completed") is False:
            raise ComfyUIError(f"ComfyUI execution failed: {status}")
        outputs = []
        for item in _find_output_files(history_entry.get("outputs", {})):
            safe_name = Path(item["filename"]).name
            destination = run_dir / safe_name
            client.download_view(item, destination)
            outputs.append(
                {"file": safe_name, "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                 "media": inspect_media(destination)}
            )
        if not outputs:
            raise ComfyUIError("Execution completed but no downloadable output was reported")
        record.update({"status": "completed", "outputs": outputs})
    except Exception as exc:
        record.update({"status": "failed", "error": str(exc)})
        raise
    finally:
        record["elapsedSeconds"] = round(time.monotonic() - started, 3)
        record["finishedAt"] = datetime.now(UTC).isoformat()
        record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record
