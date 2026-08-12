# Axon Creative Agent

[English](README.md) · [简体中文](README.zh-CN.md)

![Axon Signal — original, copyright-safe reference frame](docs/assets/axon-signal-reference.png)

> **DIRECT — Codex directs. ComfyUI executes. Your GPU renders.**

Axon Creative Agent is a small, local-first open-source workspace that turns a
creative brief into a reproducible ComfyUI run. Codex inspects references,
chooses a versioned workflow, explains the run, submits it to local ComfyUI, and
checks the generated media. The first release focuses on MiniMax H3 video with
native synchronized stereo audio on an NVIDIA RTX 5090.

No benchmark number is published until the fixed suite has run. No model weight,
private input, or generated video belongs in this repository.

## What it is / What it is not

It is:

- a repository-scoped Codex Skill plus a small Python 3.11+ runner;
- three reviewed H3 workflows: text, first-frame, and multimodal reference video;
- three comparable variants: `official`, `turbo`, and experimental `accelerated`;
- a manifest contract that future image, audio, video, or 3D Skills can adopt.

It is not:

- a ComfyUI/CUDA/model installer, hosted service, task queue, or production UI;
- a replacement for Axon Imagine, which is a separate consumer product;
- a claim that every GPU or operating system matches RTX 5090 results;
- a FLUX.3 integration. It will be added only after an official release is
  licensed, implemented, and tested.

## How DIRECT works

```text
Creative brief
     ↓
Codex Skill — inspect references, choose and explain a workflow
     ↓
Manifest — map prompt, seed, assets, dependencies and output
     ↓
ComfyUI local API — validate, queue, execute and report history
     ↓
RTX 5090 — render locally
     ↓
Video + stereo audio + ignored run manifest
```

ComfyUI's local routes provide the integration surface: `/system_stats`,
`/object_info`, `/models/*`, `/upload/image`, `/prompt`, `/history/{prompt_id}`,
and `/view`. The runner refuses non-loopback servers unless
`--allow-remote` is explicit.

## Three MiniMax H3 workflows

| Workflow | Use it for | Required input |
| --- | --- | --- |
| `minimax-h3-t2v` | Build a shot directly from a structured brief | prompt |
| `minimax-h3-i2v` | Preserve a composition or subject from a first frame | image |
| `minimax-h3-r2v` | Assign identity, motion/camera and voice to references | image; optional video/audio |

Each workflow contains draggable `workflow.ui.json`, executable
`workflow.api.json`, and a `manifest.json`. Variants are deliberately explicit:

| Variant | Sampler | Steps | Sol-Attn | Role |
| --- | --- | ---: | --- | --- |
| `official` | `res_multistep` | 20 | no | quality and speed baseline |
| `turbo` | H3 Turbo | 8 | no | accelerated sampling |
| `accelerated` | H3 Turbo | 8 | yes | experimental RTX 5090 speed path |

The public “Axon Signal” example is an original character and environment made
for this repository. It replaces private development prompts that used existing
characters.

## Quick start: Windows

Prerequisites: NVIDIA RTX 5090, current driver/CUDA-compatible PyTorch, ComfyUI
0.30.0+, Git, Python 3.11+, and FFmpeg for post-run inspection.

1. Install ComfyUI and the two optional acceleration nodes using their own
   instructions. Put model files in the folders printed by `doctor`; the runner
   never downloads weights.
2. In PowerShell:

```powershell
git clone https://github.com/bg-vc/axon-creative-agent.git
cd axon-creative-agent
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
$env:COMFYUI_INPUT_DIR = "C:\ComfyUI_windows_portable\ComfyUI\input"
axon-creative doctor
```

3. Start with a five-to-ten-second test before attempting the full benchmark.

## Quick start: Linux

Prerequisites are the same; this project maintains CLI compatibility on Linux,
but any performance table stays tied to the operating system that produced it.

```bash
git clone https://github.com/bg-vc/axon-creative-agent.git
cd axon-creative-agent
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
export COMFYUI_INPUT_DIR=/opt/ComfyUI/input
axon-creative doctor
```

ComfyUI should remain on `127.0.0.1:8188`. Use an SSH tunnel instead of exposing
it publicly.

## Complete commands

```bash
axon-creative workflows
axon-creative doctor

axon-creative run minimax-h3-t2v --variant accelerated \
  --prompt-file prompts/axon-signal-t2v.txt --seed 20260812

axon-creative run minimax-h3-i2v --variant accelerated \
  --input first-frame=docs/assets/axon-signal-reference.png --seed 20260812

axon-creative run minimax-h3-r2v --variant accelerated \
  --input picture=docs/assets/axon-signal-reference.png \
  --input video=/private/path/motion.mp4 \
  --input audio=/private/path/voice.wav
```

Every run writes `runs/<run-id>/manifest.json` with workflow hash, seed, timing,
output hashes, media metadata, and failure details. `runs/` is ignored by Git.
The CLI is repository-scoped: run it inside the clone or set
`AXON_CREATIVE_ROOT` to the clone path.

## RTX 5090 benchmark

**Status: protocol ready; results not yet measured in this repository.**

The suite fixes prompt, references, seed, dimensions, frame count and output.
It performs one warmup and three measured runs per workflow and variant, then
writes JSON and Markdown under ignored `runs/benchmarks/`. Fill the exact OS,
driver, CUDA, PyTorch and node commits before running:

```bash
axon-creative benchmark --suite benchmarks/rtx5090.json
```

Publish median/min/max, cold Triton compile time, warm end-to-end time, peak
VRAM and matching-frame quality review together. Until that evidence exists,
“about twenty minutes to a few minutes” remains a private observation, not a
project claim.

## Add a Creative Skill

Do not modify the runner for each model. Add a directory containing:

```text
workflows/<family>/<mode>/
├── manifest.json
├── official/workflow.ui.json
├── official/workflow.api.json
├── turbo/workflow.ui.json
└── turbo/workflow.api.json
```

Use schema version `1`, declare prompt/seed/asset mappings, dependencies and
outputs, add copyright-safe inputs, then update validation tests. A separate
repository Skill may call the same CLI contract. The included Codex Skill lives
at `.agents/skills/run-creative-workflows/` and follows the repository-level
Skills convention.

## Dependencies, licenses and safety

- Repository code, manifests and original workflow adaptations: Apache-2.0.
- ComfyUI official templates: MIT; source attribution is retained.
- MiniMax H3 weights and Turbo LoRA have their own terms. “Open weights” does
  not mean unrestricted commercial use.
- H3 Turbo custom nodes: Apache-2.0.
- Sol-Attn integration is experimental and currently has no declared repository
  license, so this project links to it but redistributes none of its code.
- Never commit personal references, weights, secrets, outputs, or absolute local
  paths. Review generated media before publication.

See [THIRD_PARTY.md](THIRD_PARTY.md) and [SECURITY.md](SECURITY.md).

## Non-goals and roadmap

The project intentionally avoids installers, model managers, web UI, cloud
accounts, billing, Kubernetes and remote GPU scheduling. The next additions must
earn their place through a working manifest, a tested workflow and clear
licensing. Image generation—possibly a future official FLUX release—comes after
that evidence, followed by audio or 3D only if contributors bring reproducible
workflows.

## Launch note

> Codex writes code. Here it directs a 5090.

The launch video will be an original 25–40 second comparison produced from the
three Axon Signal workflows and uploaded as a GitHub Release asset. The private
`0812.mov` development recording is intentionally excluded. Draft English and
Chinese posts are in [docs/launch-posts.md](docs/launch-posts.md).
