---
name: run-creative-workflows
description: Direct local MiniMax H3 video creation through the Axon Creative Agent repository. Use when Codex needs to turn a creative brief and optional image, video, or audio references into text-to-video, image-to-video, or multimodal reference-to-video; check a ComfyUI RTX 5090 environment; select an official, Turbo, or accelerated workflow; run it; or inspect and summarize its output.
---

# Run Creative Workflows

Direct one deliberate local generation from brief to verified output. Keep the
user informed before consuming substantial GPU time.

## Execute

1. Read the repository `AGENTS.md` and identify the requested output, duration,
   aspect ratio, subject invariants, references, and audio requirements.
2. Inspect every supplied reference. Never assume that a filename explains its
   identity, motion, style, camera, or voice role.
3. Run `axon-creative workflows`, then `axon-creative doctor`. Stop and report
   exact missing models, custom nodes, or server errors. Do not switch models.
4. Choose one workflow:
   - text only: `minimax-h3-t2v`
   - first-frame continuity: `minimax-h3-i2v`
   - identity/style/motion/voice references: `minimax-h3-r2v`
5. Prefer the user's installed MiniMax H3 prompt-writing Skill. Otherwise read
   [prompting.md](references/prompting.md) and create one prompt file under an
   ignored run directory.
6. Present a short run summary: workflow, variant, prompt intent, references,
   dimensions, duration, seed, and known experimental components.
7. Treat one explicitly requested generation as authorized. Ask before batches,
   benchmark suites, longer duration, or higher resolution because they multiply
   GPU cost.
8. Run the CLI. Use `--allow-remote` only when the user explicitly provided a
   trusted non-loopback ComfyUI server. Prefer an SSH tunnel.
9. Inspect the run manifest and media report. If `ffprobe` is available, verify
   duration, resolution, frame rate, video codec, and audio stream. Extract a
   small contact sheet when visual review is useful.
10. Report the output path, elapsed time, seed, and any visible or technical
    caveat. Never call an unmeasured run “faster” or “production-ready.”

## Commands

```bash
axon-creative doctor
axon-creative run minimax-h3-t2v --variant accelerated --prompt-file brief.txt
axon-creative run minimax-h3-i2v --input first-frame=frame.png
axon-creative run minimax-h3-r2v --input picture=character.png \
  --input video=motion.mp4 --input audio=voice.wav \
  --comfy-input-dir /path/to/ComfyUI/input
```

## Safety boundaries

- Do not download model weights, install CUDA, or expose ComfyUI automatically.
- Do not submit copyrighted character demonstrations as repository showcase
  material.
- Do not copy user references into Git. Run inputs and outputs stay ignored.
- Treat Sol-Attn as experimental. Keep `official` as the quality baseline.
- Do not publish benchmark numbers until the fixed suite completes on the stated
  machine and the visual/audio comparison is reviewed.
