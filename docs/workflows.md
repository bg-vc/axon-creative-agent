# Workflow index

Start with a UI workflow: ask Codex to choose a mode, drag the JSON into
ComfyUI, install what ComfyUI Manager reports, and run a 5–10 second test.
`axon-creative inspect <workflow-id> --variant accelerated` prints the exact
path and the Manifest dependency list.

I2V and R2V expect `axon-signal-reference.png` on first load. Copy the bundled
`docs/assets/axon-signal-reference.png` to `ComfyUI/input/`, or select your own
image in the `LoadImage` node.

| Mode | Purpose | Required input | Official | Turbo | Accelerated |
| --- | --- | --- | --- | --- | --- |
| T2V | Generate from text | prompt | [`workflow.ui.json`](../workflows/minimax-h3/t2v/official/workflow.ui.json) | [`workflow.ui.json`](../workflows/minimax-h3/t2v/turbo/workflow.ui.json) | [`workflow.ui.json`](../workflows/minimax-h3/t2v/accelerated/workflow.ui.json) |
| I2V | Preserve a first frame | image | [`workflow.ui.json`](../workflows/minimax-h3/i2v/official/workflow.ui.json) | [`workflow.ui.json`](../workflows/minimax-h3/i2v/turbo/workflow.ui.json) | [`workflow.ui.json`](../workflows/minimax-h3/i2v/accelerated/workflow.ui.json) |
| R2V | Reference identity, motion, camera, or voice | image; video/audio optional | [`workflow.ui.json`](../workflows/minimax-h3/r2v/official/workflow.ui.json) | [`workflow.ui.json`](../workflows/minimax-h3/r2v/turbo/workflow.ui.json) | [`workflow.ui.json`](../workflows/minimax-h3/r2v/accelerated/workflow.ui.json) |

## Variants

- `official`: 20-step quality and speed baseline; no acceleration nodes.
- `turbo`: 8-step Turbo LoRA path.
- `accelerated`: 8-step Turbo LoRA plus experimental Sol-Attn; the recommended
  RTX 5090 demonstration after its dependencies are installed.

If a core node is missing, update ComfyUI. If a custom node is missing, use
ComfyUI Manager when available or follow the exact source URL printed by
`inspect`. Model prompts in ComfyUI are convenient but not guaranteed for every
derived workflow; the Manifest/`inspect` output is the source of truth for model
filename, target folder, and download link.
