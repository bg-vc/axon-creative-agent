from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .benchmark import run_suite
from .client import ComfyUIClient
from .doctor import run_doctor
from .errors import AxonCreativeError, ConfigurationError
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
    parser = argparse.ArgumentParser(prog="axon-creative", description="DIRECT local creative workflows")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("workflows", help="list installed workflow manifests")
    doctor = sub.add_parser("doctor", help="check ComfyUI, nodes, and models")
    add_server_arguments(doctor)
    run = sub.add_parser("run", help="submit one workflow to local ComfyUI")
    run.add_argument("workflow_id")
    run.add_argument("--variant", choices=("official", "turbo", "accelerated"), default="accelerated")
    run.add_argument("--prompt-file", type=Path)
    run.add_argument("--input", action="append", default=[], metavar="NAME=PATH")
    run.add_argument("--seed", type=int)
    run.add_argument("--comfy-input-dir", type=Path, default=os.environ.get("COMFYUI_INPUT_DIR"))
    run.add_argument("--timeout", type=float, default=3600.0)
    run.add_argument("--poll-interval", type=float, default=2.0)
    add_server_arguments(run)
    benchmark = sub.add_parser("benchmark", help="run a warmup plus measured RTX 5090 suite")
    benchmark.add_argument("--suite", type=Path, default=repository_root() / "benchmarks" / "rtx5090.json")
    benchmark.add_argument("--comfy-input-dir", type=Path, default=os.environ.get("COMFYUI_INPUT_DIR"))
    benchmark.add_argument("--timeout", type=float, default=3600.0)
    add_server_arguments(benchmark)
    sub.add_parser("validate", help="validate manifests, workflows, and bilingual docs")
    return parser


def _prompt(manifest, prompt_file: Path | None) -> str:
    path = prompt_file or (manifest.path.parent / manifest.data["defaultPrompt"])
    if not path.is_file():
        raise ConfigurationError(f"Prompt file does not exist: {path}")
    return path.read_text(encoding="utf-8").strip()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repository_root()
    try:
        manifests = discover_manifests(root)
        if args.command == "workflows":
            for manifest in manifests.values():
                print(f"{manifest.id}\t{manifest.title}\t{','.join(manifest.variants)}")
            return 0
        if args.command == "validate":
            errors = validate_repository(root)
            if errors:
                for item in errors:
                    print(f"ERROR: {item}", file=sys.stderr)
                return 1
            print(f"Validated {len(manifests)} workflows")
            return 0
        ensure_safe_server(args.server, args.allow_remote)
        client = ComfyUIClient(args.server)
        if args.command == "doctor":
            report = run_doctor(client, manifests)
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0 if report["ok"] else 1
        if args.command == "run":
            if args.workflow_id not in manifests:
                raise ConfigurationError(f"Unknown workflow: {args.workflow_id}")
            manifest = manifests[args.workflow_id]
            record = execute(
                root=root, manifest=manifest, variant=args.variant,
                prompt=_prompt(manifest, args.prompt_file), seed=args.seed,
                inputs=parse_inputs(args.input), client=client,
                comfy_input_dir=args.comfy_input_dir,
                poll_interval=args.poll_interval, timeout=args.timeout,
            )
            print(json.dumps(record, indent=2, ensure_ascii=False))
            return 0
        if args.command == "benchmark":
            suite = json.loads(args.suite.read_text(encoding="utf-8"))
            def execute_case(case):
                manifest = manifests[case["workflowId"]]
                case_inputs = parse_inputs(
                    [f"{name}={(args.suite.parent / path).resolve()}" for name, path in case.get("inputs", {}).items()]
                )
                return execute(
                    root=root, manifest=manifest, variant=case["variant"],
                    prompt=(args.suite.parent / case["promptFile"]).read_text(encoding="utf-8"),
                    seed=case["seed"], inputs=case_inputs, client=client,
                    comfy_input_dir=args.comfy_input_dir, poll_interval=2.0, timeout=args.timeout,
                )
            output = root / "runs" / "benchmarks" / args.suite.stem
            report = run_suite(args.suite, execute_case, output)
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0
    except (AxonCreativeError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
