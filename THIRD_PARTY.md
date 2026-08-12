# Third-party software and model materials

This repository redistributes no model weights and no third-party custom-node
source. Links are installation and provenance references, not license grants.

| Component | Upstream | Version used to prepare v0.1.0 | License/status | Distribution here |
| --- | --- | --- | --- | --- |
| ComfyUI | https://github.com/Comfy-Org/ComfyUI | `bd34f338ac505ea79e43968753968a464060e609` | GPL-3.0 repository; official workflow templates are MIT | API contract references only |
| ComfyUI workflow templates | https://github.com/Comfy-Org/workflow_templates | current templates reviewed 2026-08-12 | MIT | Adapted UI workflow JSON with attribution |
| MiniMax H3 | https://github.com/MiniMax-AI/MiniMax-H3 | open-weight release reviewed 2026-08-12 | MiniMax model terms; check upstream before use | names and download links only |
| Comfy-Org H3 files | https://huggingface.co/Comfy-Org/MiniMax-H3 | reviewed 2026-08-12 | follows individual model-file terms | no files |
| H3 Turbo nodes | https://github.com/Larryvrh/ComfyUI-MiniMax-H3-Turbo | `55fee864dd7b2976b1c4ce3c3d5f7968f181409f` | Apache-2.0 | class names and install link only |
| H3 Turbo LoRA | https://huggingface.co/larryvrh/MiniMax-H3-Turbo-Lora | `minimax_h3_turbo_v4_step600_ema.safetensors` | check model card at download time | no files |
| Sol-Attn ComfyUI integration | https://github.com/kijai/ComfyUI-SolAttn_triton | `842c4eaa7d91dbaef3fee3ccdbf36a39521e82fc` | no declared repository license at review time; experimental | class name and install link only |
| Sol-Attn research | https://arxiv.org/abs/2607.24027 | paper revision available 2026-08-12 | paper terms | citation/link only |

The `official` UI workflows derive from Comfy-Org's MIT-licensed templates. The
`turbo` and `accelerated` UI workflows are copyright-safe adaptations of graphs
prepared by this project's maintainer from those templates. Repository-authored
Python, manifests, prompts, documentation and adaptations are Apache-2.0.

Licenses and model terms can change. Users are responsible for reviewing the
upstream terms that apply to their download, output, redistribution and
commercial use.
