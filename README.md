# Axon Creative Agent

[English](README.md) · [简体中文](README.zh-CN.md)

![Axon Signal — original, copyright-safe reference frame](docs/assets/axon-signal-reference.png)

> **DIRECT — Codex directs. ComfyUI executes. Your GPU renders.**

Give Codex a creative brief. It selects a reviewed workflow, explains the run,
checks the local environment, and asks ComfyUI to render it on your GPU. The
first release focuses on MiniMax H3 video with synchronized stereo audio.

This is a local workflow workspace, not a ComfyUI installer, cloud service, or
production UI. It does not download model weights, expose ComfyUI publicly, or
publish performance claims without a repeatable benchmark.

## The core flow

```text
1. Brief        Codex reads the prompt and references
       ↓
2. Direct       the Skill selects a Manifest and variant
       ↓
3. Render       ComfyUI executes; the local GPU generates
       ↓
4. Verify       the runner checks the media and records the run
```

The Manifest is the small contract between Codex and ComfyUI. It maps prompt,
seed, inputs, dependencies, workflow files, and outputs. New image, audio,
video, or 3D workflows can adopt the same contract without changing the runner.

## Three MiniMax H3 workflows

| Workflow | Purpose | Input |
| --- | --- | --- |
| `minimax-h3-t2v` | Create a shot from a brief | prompt |
| `minimax-h3-i2v` | Preserve a subject or composition | first-frame image |
| `minimax-h3-r2v` | Reference identity, motion, camera, or voice | image; optional video/audio |

Each workflow provides an editable `workflow.ui.json`, an executable
`workflow.api.json`, and a `manifest.json`.

| Variant | Configuration | Use |
| --- | --- | --- |
| `official` | `res_multistep`, 20 steps | quality/speed baseline |
| `turbo` | H3 Turbo, 8 steps | faster sampling |
| `accelerated` | H3 Turbo + Sol-Attn, 8 steps | experimental RTX 5090 path |

## Run in three steps

Prerequisites: Python 3.11+, ComfyUI 0.30.0+, FFmpeg, a compatible NVIDIA
environment, and the models/nodes declared in each Manifest. ComfyUI should
listen on `127.0.0.1:8188`.

**1. Prepare ComfyUI.** Install it from the upstream project, place the H3
weights in its model folders, and install Turbo/Sol-Attn only when using those
variants. This repository links to dependencies; it does not install them.

**2. Install and check.**

Linux:

```bash
git clone https://github.com/bg-vc/axon-creative-agent.git
cd axon-creative-agent
python3.11 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
export COMFYUI_INPUT_DIR=/opt/ComfyUI/input
axon-creative doctor --variant accelerated
```

Windows PowerShell:

```powershell
git clone https://github.com/bg-vc/axon-creative-agent.git
cd axon-creative-agent
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
$env:COMFYUI_INPUT_DIR = "C:\ComfyUI_windows_portable\ComfyUI\input"
axon-creative doctor --variant accelerated
```

**3. Generate one short test.**

```bash
axon-creative run minimax-h3-t2v --variant accelerated \
  --prompt-file prompts/axon-signal-t2v.txt --seed 20260812

axon-creative run minimax-h3-i2v --variant accelerated \
  --input first-frame=docs/assets/axon-signal-reference.png --seed 20260812

axon-creative run minimax-h3-r2v --variant accelerated \
  --input picture=docs/assets/axon-signal-reference.png \
  --input video=/private/path/motion.mp4 \
  --input audio=/private/path/voice.wav
```

Start with 5–10 seconds. Every run writes an ignored
`runs/<run-id>/manifest.json` containing the workflow hash, seed, timing,
outputs, media inspection, and any error. For manual ComfyUI use, copy the
reference asset into its input folder before loading a UI workflow.

## Benchmark honestly

**Status: protocol ready; no public RTX 5090 result yet.**

Edit every `FILL_AFTER_MEASUREMENT` value in `benchmarks/rtx5090.json`, then run:

```bash
axon-creative benchmark --suite benchmarks/rtx5090.json
```

The suite performs one warmup and three measured runs for every workflow and
variant. Publish median/min/max, exact system versions, peak VRAM, and matching
quality frames together. The CLI refuses to run a benchmark that still contains
placeholder environment data.

## Add another workflow or Skill

Add one directory with `manifest.json` and UI/API workflow files, declare every
input and dependency, then add a public sample and tests. Do not add model logic
to the runner. The repository Skill at
`.agents/skills/run-creative-workflows/SKILL.md` follows the same four-stage
flow: inspect, direct, render, verify.

## Boundaries, licenses, and safety

- Repository code and original workflow adaptations: Apache-2.0.
- ComfyUI templates: MIT. Model weights and LoRAs keep their own terms.
- Sol-Attn is experimental and has no declared repository license; this project
  links to it and redistributes none of its code.
- Non-loopback ComfyUI servers require explicit `--allow-remote`; prefer an SSH
  tunnel. Never commit weights, private references, generated media, or secrets.
- FLUX.3 is not advertised as supported until an official release, workflow,
  license review, and real test all exist.

See [THIRD_PARTY.md](THIRD_PARTY.md), [SECURITY.md](SECURITY.md), and the
[launch post drafts](docs/launch-posts.md). The private `0812.mov` development
recording is intentionally excluded from this repository.
