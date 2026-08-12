from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .benchmark import run_suite
from .client import ComfyUIClient
from .cloud import (
    CloudProfile,
    cloud_doctor,
    cloud_run,
    get_profile,
    initialize_profile,
)
from .doctor import doctor_failure, run_doctor
from .errors import AxonCreativeError, ConfigurationError
from .inspection import inspect_workflow
from .manifest import discover_manifests
from .runner import ensure_safe_server, execute, parse_inputs
from .validation import validate_repository


def repository_root() -> Path:
    candidates = []
    if os.environ.get("AXON_CREATIVE_ROOT"):
        candidates.append(Path(os.environ["AXON_CREATIVE_ROOT"]).expanduser())
    candidates.extend((Path.cwd(), Path(__file__).resolve().parents[1]))
    for candidate in candidates:
        resolved = candidate.resolve()
        if (resolved / "workflows").is_dir() and (resolved / "README.md").is_file():
            return resolved
    raise ConfigurationError(
        "Cannot find the Axon Creative Agent repository. Run inside its clone or set "
        "AXON_CREATIVE_ROOT to the clone path."
    )


def add_server_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--server", default=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188"))
    parser.add_argument("--allow-remote", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="axon-creative", description="DIRECT creative workflows")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("workflows", help="list installed workflow manifests")
    inspect = sub.add_parser("inspect", help="show the UI workflow and exact dependencies")
    inspect.add_argument("workflow_id")
    inspect.add_argument("--variant", choices=("official", "turbo", "accelerated"), default="accelerated")
    doctor = sub.add_parser("doctor", help="check ComfyUI, nodes, and models")
    doctor.add_argument("--variant", choices=("official", "turbo", "accelerated"), default="accelerated")
    doctor.add_argument("--workflow-id", help="check one workflow instead of every workflow")
    add_server_arguments(doctor)
    run = sub.add_parser("run", help="submit one workflow to ComfyUI")
    run.add_argument("workflow_id")
    run.add_argument("--variant", choices=("official", "turbo", "accelerated"), default="accelerated")
    run.add_argument("--prompt-file", type=Path)
    run.add_argument("--input", action="append", default=[], metavar="NAME=PATH")
    run.add_argument("--seed", type=int)
    run.add_argument("--comfy-input-dir", type=Path, default=os.environ.get("COMFYUI_INPUT_DIR"))
    run.add_argument("--timeout", type=float, default=3600.0)
    run.add_argument("--poll-interval", type=float, default=2.0)
    run.add_argument("--run-id")
    add_server_arguments(run)
    benchmark = sub.add_parser("benchmark", help="run a warmup plus measured RTX 5090 suite")
    benchmark.add_argument("--suite", type=Path, default=Path("benchmarks/rtx5090.json"))
    benchmark.add_argument("--comfy-input-dir", type=Path, default=os.environ.get("COMFYUI_INPUT_DIR"))
    benchmark.add_argument("--timeout", type=float, default=3600.0)
    add_server_arguments(benchmark)

    cloud = sub.add_parser("cloud", help="control a cloud GPU over SSH")
    cloud_sub = cloud.add_subparsers(dest="cloud_command", required=True)
    cloud_init = cloud_sub.add_parser("init", help="save a cloud profile and test SSH")
    cloud_init.add_argument("--profile", required=True)
    cloud_init.add_argument("--ssh-host", help="SSH config alias; defaults to the profile name")
    cloud_init.add_argument("--remote-repo", default="/workspace/axon-creative-agent")
    cloud_init.add_argument("--comfy-input-dir", default="/workspace/ComfyUI/input")
    cloud_check = cloud_sub.add_parser("doctor", help="check SSH, versions, and cloud ComfyUI")
    cloud_check.add_argument("--profile", required=True)
    cloud_check.add_argument("--variant", choices=("official", "turbo", "accelerated"), default="accelerated")
    cloud_check.add_argument("--workflow-id", default="minimax-h3-t2v")
    cloud_execute = cloud_sub.add_parser("run", help="upload inputs, generate, and download results")
    cloud_execute.add_argument("--profile", required=True)
    cloud_execute.add_argument("workflow_id")
    cloud_execute.add_argument("--variant", choices=("official", "turbo", "accelerated"), default="accelerated")
    cloud_execute.add_argument("--prompt-file", type=Path)
    cloud_execute.add_argument("--input", action="append", default=[], metavar="NAME=PATH")
    cloud_execute.add_argument("--seed", type=int)
    cloud_execute.add_argument("--timeout", type=float, default=3600.0)
    sub.add_parser("validate", help="validate manifests, workflows, and bilingual docs")
    return parser


def _prompt(manifest, prompt_file: Path | None) -> str:
    path = prompt_file or (manifest.path.parent / manifest.data["defaultPrompt"])
    if not path.is_file():
        raise ConfigurationError(f"Prompt file does not exist: {path}")
    return path.read_text(encoding="utf-8").strip()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = repository_root()
        manifests = discover_manifests(root)
        if args.command == "workflows":
            for manifest in manifests.values():
                print(f"{manifest.id}\t{manifest.title}\t{','.join(manifest.variants)}")
            return 0
        if args.command == "inspect":
            if args.workflow_id not in manifests:
                raise ConfigurationError(f"Unknown workflow: {args.workflow_id}")
            print(
                json.dumps(
                    inspect_workflow(manifests[args.workflow_id], args.variant),
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 0
        if args.command == "validate":
            errors = validate_repository(root)
            if errors:
                for item in errors:
                    print(f"ERROR: {item}", file=sys.stderr)
                return 1
            print(f"Validated {len(manifests)} workflows")
            return 0
        if args.command == "cloud":
            if args.cloud_command == "init":
                result = initialize_profile(
                    root,
                    CloudProfile(
                        name=args.profile,
                        ssh_host=args.ssh_host or args.profile,
                        remote_repo=args.remote_repo,
                        comfyui_input_dir=args.comfy_input_dir,
                    ),
                )
            elif args.cloud_command == "doctor":
                if args.workflow_id not in manifests:
                    raise ConfigurationError(f"Unknown workflow: {args.workflow_id}")
                result = cloud_doctor(
                    root,
                    get_profile(root, args.profile),
                    args.variant,
                    args.workflow_id,
                )
            else:
                if args.workflow_id not in manifests:
                    raise ConfigurationError(f"Unknown workflow: {args.workflow_id}")
                manifest = manifests[args.workflow_id]
                prompt_file = args.prompt_file or (manifest.path.parent / manifest.data["defaultPrompt"])
                if not prompt_file.is_file():
                    raise ConfigurationError(f"Prompt file does not exist: {prompt_file}")
                result = cloud_run(
                    root=root,
                    profile=get_profile(root, args.profile),
                    workflow_id=args.workflow_id,
                    variant=args.variant,
                    prompt_file=prompt_file,
                    inputs=parse_inputs(args.input),
                    seed=args.seed,
                    timeout=args.timeout,
                )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result.get("ok", result.get("status") == "completed") else 1
        ensure_safe_server(args.server, args.allow_remote)
        client = ComfyUIClient(args.server)
        if args.command == "doctor":
            selected = manifests
            if args.workflow_id:
                if args.workflow_id not in manifests:
                    raise ConfigurationError(f"Unknown workflow: {args.workflow_id}")
                selected = {args.workflow_id: manifests[args.workflow_id]}
            report = run_doctor(client, selected, args.variant)
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0 if report["ok"] else 1
        if args.command == "run":
            if args.workflow_id not in manifests:
                raise ConfigurationError(f"Unknown workflow: {args.workflow_id}")
            manifest = manifests[args.workflow_id]
            report = run_doctor(client, {manifest.id: manifest}, args.variant)
            if not report["ok"]:
                raise ConfigurationError(doctor_failure(report))
            record = execute(
                root=root, manifest=manifest, variant=args.variant,
                prompt=_prompt(manifest, args.prompt_file), seed=args.seed,
                inputs=parse_inputs(args.input), client=client,
                comfy_input_dir=args.comfy_input_dir,
                poll_interval=args.poll_interval, timeout=args.timeout, run_id=args.run_id,
            )
            print(json.dumps(record, indent=2, ensure_ascii=False))
            return 0
        if args.command == "benchmark":
            suite_path = args.suite if args.suite.is_absolute() else root / args.suite

            def execute_case(case):
                manifest = manifests[case["workflowId"]]
                case_inputs = parse_inputs(
                    [f"{name}={(suite_path.parent / path).resolve()}" for name, path in case.get("inputs", {}).items()]
                )
                return execute(
                    root=root, manifest=manifest, variant=case["variant"],
                    prompt=(suite_path.parent / case["promptFile"]).read_text(encoding="utf-8"),
                    seed=case["seed"], inputs=case_inputs, client=client,
                    comfy_input_dir=args.comfy_input_dir, poll_interval=2.0, timeout=args.timeout,
                )
            output = root / "runs" / "benchmarks" / suite_path.stem
            report = run_suite(suite_path, execute_case, output)
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0
    except (AxonCreativeError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
