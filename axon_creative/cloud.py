from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from .errors import ConfigurationError
from .runner import create_run_id, validate_run_id


SSH_HOST_PATTERN = re.compile(r"^[A-Za-z0-9_.@-]+$")
PROFILE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
REMOTE_PATH_PATTERN = re.compile(r"^/[A-Za-z0-9_./-]+$")


@dataclass(frozen=True)
class CloudProfile:
    name: str
    ssh_host: str
    remote_repo: str
    comfyui_input_dir: str


def profile_path(root: Path) -> Path:
    return root / ".axon-creative" / "profiles.toml"


def _remote_path(value: str, label: str) -> str:
    path = PurePosixPath(value)
    if (
        not path.is_absolute()
        or ".." in path.parts
        or not REMOTE_PATH_PATTERN.fullmatch(value)
    ):
        raise ConfigurationError(f"{label} must be a safe absolute Linux path")
    return str(path)


def validate_profile(profile: CloudProfile) -> CloudProfile:
    if not PROFILE_NAME_PATTERN.fullmatch(profile.name):
        raise ConfigurationError("profile name must be 1-32 safe characters")
    if not SSH_HOST_PATTERN.fullmatch(profile.ssh_host):
        raise ConfigurationError("ssh_host must be a safe SSH config alias")
    _remote_path(profile.remote_repo, "remote_repo")
    _remote_path(profile.comfyui_input_dir, "comfyui_input_dir")
    return profile


def load_profiles(root: Path) -> dict[str, CloudProfile]:
    path = profile_path(root)
    if not path.is_file():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigurationError(f"Cannot read cloud profiles: {exc}") from exc
    result: dict[str, CloudProfile] = {}
    for name, values in data.get("profiles", {}).items():
        try:
            profile = CloudProfile(
                name=name,
                ssh_host=str(values["ssh_host"]),
                remote_repo=str(values["remote_repo"]),
                comfyui_input_dir=str(values["comfyui_input_dir"]),
            )
        except (KeyError, TypeError) as exc:
            raise ConfigurationError(f"Profile {name!r} is incomplete") from exc
        result[name] = validate_profile(profile)
    return result


def save_profile(root: Path, profile: CloudProfile) -> Path:
    validate_profile(profile)
    profiles = load_profiles(root)
    profiles[profile.name] = profile
    path = profile_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# SSH credentials stay in ~/.ssh/config.", ""]
    for name in sorted(profiles):
        item = profiles[name]
        lines.extend(
            [
                f"[profiles.{name}]",
                f"ssh_host = {json.dumps(item.ssh_host)}",
                f"remote_repo = {json.dumps(item.remote_repo)}",
                f"comfyui_input_dir = {json.dumps(item.comfyui_input_dir)}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def get_profile(root: Path, name: str) -> CloudProfile:
    try:
        return load_profiles(root)[name]
    except KeyError as exc:
        raise ConfigurationError(
            f"Unknown cloud profile {name!r}; run 'axon-creative cloud init' first"
        ) from exc


def _redact_error(message: str, root: Path, profile: CloudProfile) -> str:
    redacted = message
    for value, replacement in (
        (str(root), "<local-repository>"),
        (str(root.resolve()), "<local-repository>"),
        (profile.ssh_host, "<ssh-host>"),
        (profile.remote_repo, "<remote-repository>"),
        (profile.comfyui_input_dir, "<comfyui-input>"),
    ):
        redacted = redacted.replace(value, replacement)
    return redacted


class SSHTransport:
    def __init__(self, host: str):
        self.host = host

    def _tool(self, name: str) -> str:
        executable = shutil.which(name)
        if not executable:
            raise ConfigurationError(f"Required command is not installed: {name}")
        return executable

    def ssh(self, arguments: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        remote_command = shlex.join(arguments)
        completed = subprocess.run(
            [
                self._tool("ssh"),
                "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=10",
                self.host,
                remote_command,
            ],
            capture_output=True,
            text=True,
        )
        if check and completed.returncode:
            detail = completed.stderr.strip() or "remote command failed"
            raise ConfigurationError(f"SSH failed: {detail}")
        return completed

    def upload(self, source: Path, remote_path: str) -> None:
        completed = subprocess.run(
            [
                self._tool("scp"),
                "-q",
                "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=10",
                str(source),
                f"{self.host}:{remote_path}",
            ],
            capture_output=True,
            text=True,
        )
        if completed.returncode:
            raise ConfigurationError("SCP upload failed")

    def download_directory(self, remote_path: str, local_parent: Path) -> None:
        completed = subprocess.run(
            [
                self._tool("scp"),
                "-q",
                "-r",
                "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=10",
                f"{self.host}:{remote_path}",
                str(local_parent),
            ],
            capture_output=True,
            text=True,
        )
        if completed.returncode:
            raise ConfigurationError("SCP result download failed")


def initialize_profile(root: Path, profile: CloudProfile) -> dict[str, Any]:
    validate_profile(profile)
    transport = SSHTransport(profile.ssh_host)
    transport.ssh(["true"])
    path = save_profile(root, profile)
    return {"ok": True, "profile": profile.name, "config": str(path)}


def cloud_doctor(root: Path, profile: CloudProfile, variant: str) -> dict[str, Any]:
    transport = SSHTransport(profile.ssh_host)
    remote_python = str(PurePosixPath(profile.remote_repo) / ".venv/bin/python")
    try:
        local_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise ConfigurationError("Cannot read the local Git commit") from exc
    probe = transport.ssh(
        [
            "bash",
            "-lc",
            " && ".join(
                [
                    f"test -x {shlex.quote(remote_python)}",
                    f"test -d {shlex.quote(profile.comfyui_input_dir)}",
                    f"git -C {shlex.quote(profile.remote_repo)} rev-parse HEAD",
                ]
            ),
        ]
    )
    remote_lines = probe.stdout.strip().splitlines()
    if not remote_lines:
        raise ConfigurationError("Cloud repository did not report a Git commit")
    remote_sha = remote_lines[-1]
    doctor = transport.ssh(
        [
            remote_python,
            "-m",
            "axon_creative",
            "doctor",
            "--variant",
            variant,
        ],
        check=False,
    )
    try:
        doctor_report = json.loads(doctor.stdout)
    except json.JSONDecodeError:
        doctor_report = {"ok": False, "error": doctor.stderr.strip() or "invalid doctor output"}
    return {
        "ok": local_sha == remote_sha and bool(doctor_report.get("ok")),
        "profile": profile.name,
        "version": {"ok": local_sha == remote_sha, "local": local_sha, "remote": remote_sha},
        "comfyui": doctor_report,
    }


def _execute_cloud_run(
    *,
    root: Path,
    profile: CloudProfile,
    run_id: str,
    workflow_id: str,
    variant: str,
    prompt_file: Path,
    inputs: dict[str, Path],
    seed: int | None,
    timeout: float,
) -> dict[str, Any]:
    transport = SSHTransport(profile.ssh_host)
    remote_repo = PurePosixPath(profile.remote_repo)
    remote_upload = remote_repo / "runs/uploads" / run_id
    remote_run = remote_repo / "runs" / run_id
    remote_python = remote_repo / ".venv/bin/python"
    local_run = root / "runs" / run_id
    if local_run.exists():
        raise ConfigurationError(f"Local run already exists: {run_id}")

    transport.ssh(["mkdir", "-p", str(remote_upload)])
    uploaded_prompt = remote_upload / "prompt.txt"
    transport.upload(prompt_file, str(uploaded_prompt))
    remote_inputs: list[str] = []
    for index, (name, path) in enumerate(inputs.items()):
        suffix = path.suffix.lower()
        if not re.fullmatch(r"\.[a-z0-9]{1,10}", suffix):
            suffix = ".bin"
        remote_file = remote_upload / f"input-{index}{suffix}"
        transport.upload(path, str(remote_file))
        remote_inputs.extend(["--input", f"{name}={remote_file}"])

    command = [
        str(remote_python),
        "-m",
        "axon_creative",
        "run",
        workflow_id,
        "--variant",
        variant,
        "--run-id",
        run_id,
        "--prompt-file",
        str(uploaded_prompt),
        "--comfy-input-dir",
        profile.comfyui_input_dir,
        "--timeout",
        str(timeout),
        *remote_inputs,
    ]
    if seed is not None:
        command.extend(["--seed", str(seed)])
    result = transport.ssh(command, check=False)

    exists = transport.ssh(["test", "-d", str(remote_run)], check=False).returncode == 0
    download_error: ConfigurationError | None = None
    if exists:
        (root / "runs").mkdir(parents=True, exist_ok=True)
        try:
            transport.download_directory(str(remote_run), root / "runs")
        except ConfigurationError as exc:
            download_error = exc
        else:
            transport.ssh(["rm", "-rf", str(remote_upload)])

    if download_error:
        raise download_error

    if not local_run.is_dir():
        detail = result.stderr.strip() or "remote run did not create a manifest"
        local_run.mkdir(parents=True)
        (local_run / "manifest.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "runId": run_id,
                    "workflowId": workflow_id,
                    "variant": variant,
                    "status": "failed",
                    "finishedAt": datetime.now(UTC).isoformat(),
                    "error": detail,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        raise ConfigurationError(f"Cloud run failed; inspect runs/{run_id}/manifest.json")
    manifest_path = local_run / "manifest.json"
    if not manifest_path.is_file():
        raise ConfigurationError("Downloaded cloud run has no manifest.json")
    record = json.loads(manifest_path.read_text(encoding="utf-8"))
    if result.returncode or record.get("status") != "completed":
        raise ConfigurationError(f"Cloud run failed; inspect runs/{run_id}/manifest.json")
    return record


def cloud_run(
    *,
    root: Path,
    profile: CloudProfile,
    workflow_id: str,
    variant: str,
    prompt_file: Path,
    inputs: dict[str, Path],
    seed: int | None,
    timeout: float,
) -> dict[str, Any]:
    run_id = validate_run_id(create_run_id())
    manifest_path = root / "runs" / run_id / "manifest.json"
    try:
        return _execute_cloud_run(
            root=root,
            profile=profile,
            run_id=run_id,
            workflow_id=workflow_id,
            variant=variant,
            prompt_file=prompt_file,
            inputs=inputs,
            seed=seed,
            timeout=timeout,
        )
    except ConfigurationError as exc:
        if not manifest_path.is_file():
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "runId": run_id,
                        "workflowId": workflow_id,
                        "variant": variant,
                        "status": "failed",
                        "finishedAt": datetime.now(UTC).isoformat(),
                        "error": _redact_error(str(exc), root, profile),
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
        raise
