---
name: run-creative-workflows
description: Direct MiniMax H3 video creation from a user's computer to ComfyUI on a cloud GPU. Use when Codex needs to choose and explain a drag-and-drop text-to-video, image-to-video, or reference-to-video workflow; diagnose its models and nodes; configure an SSH cloud profile; run the workflow; download results; or inspect generated media.
---

# Run Creative Workflows

Act as the creative lead on the user's computer. Prefer one deliberate short
generation before batches or benchmarks.

## Execute

1. Identify the requested shot, duration, aspect ratio, invariants, references,
   and audio requirements. Inspect every supplied reference.
2. Choose `minimax-h3-t2v`, `minimax-h3-i2v`, or `minimax-h3-r2v`. Default to
   `accelerated` for the RTX 5090 demonstration; explain its Turbo and Sol-Attn
   requirements. Never silently switch variants.
3. Run `axon-creative inspect <workflow-id> --variant accelerated`. Tell the user
   the exact `workflow.ui.json` to drag into cloud ComfyUI.
4. Help resolve the UI once: use ComfyUI Manager for missing custom nodes,
   update ComfyUI for missing core nodes, and use the inspect/Manifest model
   list when the UI does not provide a download prompt. Restart and reload.
5. Have the user complete one 5–10 second UI test. Do not automate a workflow
   that has not worked in the UI.
6. Run `axon-creative cloud doctor --profile <name> --variant <variant>`. Stop on
   SSH, version, path, model, node, or server errors.
7. Present a short summary, then run `axon-creative cloud run`. One explicitly
   requested generation is authorized; ask before batches, benchmarks, longer
   duration, or higher resolution.
8. Inspect the downloaded run manifest and media. Verify duration, resolution,
   frame rate, video codec, and audio stream when `ffprobe` is available. Report
   the local output path, elapsed time, seed, and caveats.

## Safety boundaries

- Keep ComfyUI on cloud loopback and use an SSH tunnel for its UI. Never disable
  host-key checking or expose ComfyUI automatically.
- Do not install CUDA, download weights, or install custom nodes automatically.
- Do not copy references, outputs, profiles, or credentials into Git.
- Treat Sol-Attn as experimental and `official` as the quality baseline.
- Never publish benchmark numbers until the fixed suite and visual/audio review
  complete on the stated cloud instance.
