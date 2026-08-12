# Security

- Keep ComfyUI bound to loopback. Prefer an SSH tunnel for remote access.
- `--allow-remote` removes only the runner's loopback guard; it does not add
  authentication or transport security.
- Do not commit `.env`, model weights, private references, generated media or
  run manifests.
- Review third-party node source and licenses before updating pinned commits.
- Report vulnerabilities privately through GitHub's security advisory feature.
