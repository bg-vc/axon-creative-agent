# Axon Creative Agent

[English](README.md) · [简体中文](README.zh-CN.md)

![Axon Signal — original, copyright-safe reference frame](docs/assets/axon-signal-reference.png)

> **DIRECT — Codex directs. ComfyUI executes. Cloud GPUs render.**

Codex runs on your computer as the creative lead. It chooses and explains a
reviewed workflow, helps you prepare ComfyUI, sends references to your cloud GPU,
waits for the render, and brings the result back for inspection. The first
release focuses on MiniMax H3 video with synchronized stereo audio.

This is not a GPU provider, hosted ComfyUI service, installer, or production UI.
It never downloads weights automatically or exposes ComfyUI to the public web.

## The core flow

```text
Local computer                         Cloud RTX 5090
Codex creative lead
  → understand the brief
  → choose a UI/API workflow
  → upload references over SSH   ───→  ComfyUI renders
  → download and inspect result  ←───  video + run manifest
```

The UI JSON is the first-run and learning surface. The matching API JSON powers
repeatable automation after that workflow works in ComfyUI.

## First run: drag the workflow into ComfyUI

1. Ask Codex to choose T2V, I2V, or R2V. Accelerated is the default RTX 5090
   demonstration; it requires H3 Turbo and Sol-Attn.
2. Print the exact workflow and dependencies:

```bash
axon-creative inspect minimax-h3-t2v --variant accelerated
```

3. Reach the cloud ComfyUI through an SSH tunnel, then drag the reported
   `workflow.ui.json` directly into the page.

```bash
ssh -N -L 8188:127.0.0.1:8188 axon-5090
```

Open `http://127.0.0.1:8188` locally while the tunnel is running.

4. Install missing custom nodes reported by ComfyUI Manager. Update ComfyUI when
   a core node is missing. Install every model printed by `inspect` in the shown
   `ComfyUI/models/<folder>` directory.
5. Restart ComfyUI, reload the JSON, and run a 5–10 second test before automation.

All nine drag-and-drop files are linked in the [workflow index](docs/workflows.md).
The Manifest is the dependency source of truth when ComfyUI does not offer a
model prompt.

## One-time cloud setup

The cloud host is Linux and available through an alias in `~/.ssh/config`.
Clone the same commit on the cloud host, create `.venv`, install this package,
and keep ComfyUI listening on cloud loopback `127.0.0.1:8188`.

```bash
ssh axon-5090
git clone https://github.com/bg-vc/axon-creative-agent.git /workspace/axon-creative-agent
cd /workspace/axon-creative-agent
python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
```

On the local computer, save a profile and test SSH:

```bash
axon-creative cloud init --profile cloud5090 --ssh-host axon-5090 \
  --remote-repo /workspace/axon-creative-agent \
  --comfy-input-dir /workspace/ComfyUI/input

axon-creative cloud doctor --profile cloud5090 --variant accelerated
```

The ignored `.axon-creative/profiles.toml` stores only the SSH alias and remote
paths. Passwords and keys remain in the operating system SSH configuration.
`cloud doctor` checks SSH, repository versions, cloud paths, ComfyUI, nodes, and
models. Fix every reported item; it never installs or silently changes models.

## Generate from local Codex

```bash
axon-creative cloud run --profile cloud5090 \
  minimax-h3-t2v --variant accelerated \
  --prompt-file prompts/axon-signal-t2v.txt --seed 20260812

axon-creative cloud run --profile cloud5090 \
  minimax-h3-i2v --variant accelerated \
  --input first-frame=docs/assets/axon-signal-reference.png --seed 20260812

axon-creative cloud run --profile cloud5090 \
  minimax-h3-r2v --variant accelerated \
  --input picture=docs/assets/axon-signal-reference.png \
  --input video=/private/path/motion.mp4 \
  --input audio=/private/path/voice.wav
```

The command uploads only this run's inputs, executes the same API runner on the
cloud host, and downloads `runs/<run-id>/` with the video and manifest. Temporary
uploads are removed only after a successful download. Failures also produce a
local manifest with an actionable error.

## Workflows and variants

| Workflow | Purpose | Input |
| --- | --- | --- |
| `minimax-h3-t2v` | Create a shot from a brief | prompt |
| `minimax-h3-i2v` | Preserve a subject or composition | first-frame image |
| `minimax-h3-r2v` | Reference identity, motion, camera, or voice | image; optional video/audio |

| Variant | Configuration | Use |
| --- | --- | --- |
| `official` | `res_multistep`, 20 steps | quality/speed baseline |
| `turbo` | H3 Turbo, 8 steps | faster sampling |
| `accelerated` | H3 Turbo + Sol-Attn, 8 steps | experimental RTX 5090 path |

Each mode/variant contains `workflow.ui.json`, `workflow.api.json`, and a shared
Manifest. Validation keeps their model names and acceleration nodes aligned.

## Benchmark honestly

**Status: protocol ready; no public RTX 5090 result yet.** Fill the cloud
provider, instance type, OS, driver, CUDA, PyTorch, and commit placeholders in
`benchmarks/rtx5090.json`, then run the fixed suite on the cloud host:

```bash
axon-creative benchmark --suite benchmarks/rtx5090.json
```

It performs one warmup and three measured runs per workflow and variant. Publish
median/min/max, exact environment, peak VRAM, and matching quality frames
together. Placeholder benchmark data is rejected.

## Boundaries, licenses, and extension

- Repository code and original workflow adaptations: Apache-2.0.
- ComfyUI templates: MIT. Models and LoRAs retain their own terms.
- Sol-Attn is experimental and currently has no declared repository license;
  this project links to it and redistributes none of its code.
- SSH host-key verification remains enabled. Do not expose ComfyUI publicly or
  commit weights, private references, generated media, profiles, or secrets.
- New image, audio, video, or 3D support must add UI/API JSON, a Manifest,
  copyright-safe samples, dependency links, and tests—not model branches in the
  runner. FLUX.3 is not listed as supported until release, license, and tests exist.

Local GPU execution remains compatible through `axon-creative run`; cloud GPU is
the documented primary path. See [THIRD_PARTY.md](THIRD_PARTY.md),
[SECURITY.md](SECURITY.md), and [launch post drafts](docs/launch-posts.md).
