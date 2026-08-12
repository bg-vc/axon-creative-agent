# Security

- Keep cloud ComfyUI bound to cloud loopback. Reach its UI through an SSH tunnel
  and use the SSH cloud commands for automation.
- `--allow-remote` removes only the runner's loopback guard; it does not add
  authentication or transport security.
- Do not commit `.env`, model weights, private references, generated media or
  run manifests.
- Review third-party node source and licenses before updating pinned commits.
- Report vulnerabilities privately through GitHub's security advisory feature.
- Keep SSH host-key checking enabled. `.axon-creative/profiles.toml` may contain
  aliases and paths only—credentials belong in the operating system SSH setup.
