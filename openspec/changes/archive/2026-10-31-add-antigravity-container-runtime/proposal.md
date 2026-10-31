# Proposal

## Why

This repository currently contains only the license and OpenSpec configuration: it provides no way to run Google Antigravity CLI in a container. It needs the same operating model as `yarilc/claude-container` and `yarilc/codex-container`, with explicit filesystem boundaries and configurable permissions.

## What Changes

- Add a Linux image for the official Google CLI `agy`, including its official dependencies, the development tools from the reference projects, and OpenSpec.
- Add a Bash wrapper for rootless Podman with build, shell, help, argument forwarding, and caller identity preservation.
- Expose only the physical current directory as the workspace; `--container-git-worktree` exposes its immediate parent instead, preserving the working directory and absolute paths.
- Make YOLO and access to the host Podman service independent environment options, both disabled by default.
- Persist Antigravity state in a dedicated home and support authentication without a desktop, without mounting the host home, keyring, or bus.
- Document installation, dependencies, updates, authentication, and isolation limits, with automated wrapper checks and real container tests.

## Capabilities

### New Capabilities

- `runtime-image`: official Antigravity CLI distribution, Linux base, dependencies, and update lifecycle.
- `container-launcher`: wrapper interface, Podman lifecycle, and process identity.
- `workspace-mounts`: mount boundaries, worktree mode, and dedicated persistence.
- `agent-permissions`: independent options for YOLO and access to the Podman service.
- `container-authentication`: authentication and state retention without host desktop services.

### Modified Capabilities

None: the repository has no main specifications.

## Impact

New `Containerfile`, `antigravity-container.sh`, a possible entrypoint for the local D-Bus session, `README.md`, and wrapper/runtime checks. Requires Bash and Podman on a Linux host, the official Google distribution during the build, and network access for authentication and models. The optional Podman socket grants control over the resources of its host user and exceeds the workspace mount boundary. Docker, Podman Machine, the graphical IDE, browser automation, and automatic access to host credentials are out of scope.
