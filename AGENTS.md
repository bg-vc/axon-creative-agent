# Axon Creative Agent

This repository is a small, local-first Codex workspace for directing creative
workflows through ComfyUI. Keep it readable and executable.

## Contribution rules

- Put workflow differences in `manifest.json`; do not hard-code model-specific
  branches in the runner.
- Prefer modifying existing modules. Add an abstraction only after real
  duplication appears.
- Never download model weights automatically or expose ComfyUI to a public
  network interface.
- Keep `README.md` and `README.zh-CN.md` in the same section order.
- Every new workflow must include a dependency declaration, parameter and input
  mappings, an API workflow, a UI workflow, tests, and a copyright-safe example.
- Do not commit weights, user inputs, generated media, run manifests, secrets,
  absolute local paths, or private ComfyUI data.
- Treat model-weight licenses separately from this repository's Apache-2.0
  source license.
- Never publish performance claims without a reproducible benchmark artifact.

## Validation

Run before committing:

```bash
python -m compileall -q axon_creative tests
python -m unittest discover -s tests -v
python -m axon_creative validate
python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  .agents/skills/run-creative-workflows
```
