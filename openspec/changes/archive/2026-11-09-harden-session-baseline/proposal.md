# Proposal: Harden the Antigravity session baseline

## Why

Antigravity sessions run with Podman's default capability set and without no-new-privileges or resource budgets. They can expose `/`, the home directory or system directories read/write, have no lifetime limit, and install OpenSpec unpinned. They also install `agy` from Google's "latest" release manifest, so every build may change the CLI version. `claude-container` closed these gaps in Wave 0 (tag `sandbox-ref-2`) and `codex-container` followed in Wave 2. This change brings Antigravity to the same baseline before the Wave 3 network port. It covers todo items B01–B05 and the agent-container part of C07.

## What Changes

- **BREAKING** Every agy and shell container runs with `--cap-drop=all` and `--security-opt=no-new-privileges`. This applies with or without Podman delegation and YOLO, in both account (private D-Bus and keyring) and Gemini API-key modes. Account login, keyring unlock and the delegated Podman client must keep working; capabilities are not added back.
- **BREAKING** Every session gets explicit, validated resource budgets:
  - `ANTIGRAVITY_CONTAINER_MEMORY_LIMIT`, default `4g`;
  - `ANTIGRAVITY_CONTAINER_CPU_LIMIT`, default `2`;
  - `ANTIGRAVITY_CONTAINER_PIDS_LIMIT`, default `512`.

  Invalid values stop before any engine query. Before start, the wrapper checks the budgets configured in the created container; runtime tests verify the effective cgroup v2 values.
- **BREAKING** The wrapper refuses a writable workspace that physically resolves to a sensitive root, including the `--container-git-worktree` parent. Sensitive roots are `/`, system directories, `/tmp`, the caller's physical home and WSL drive roots `/mnt/<letter>`. The refusal happens before engine queries or state creation. Only the exact `ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` overrides it, with a warning.
- New optional `ANTIGRAVITY_CONTAINER_RUN_TIMEOUT` sets the native container lifetime in whole seconds. When the lifetime limit stops a session, the wrapper prints a notice and keeps the client's exit status.
- **BREAKING** `Containerfile` pins the input versions:
  - `agy` to an exact release, fetched per architecture (amd64, arm64) from its immutable Google URL and verified against a recorded SHA-512;
  - OpenSpec to an exact version;
  - the base image by digest.

  `--container-build` reproduces the recorded inputs instead of fetching the latest release. Updates follow a documented maintenance procedure. The pinned `agy` release is 1.5.3, an upgrade from the 1.4.12 in the current image.
- Help, README, AGENTS.md and `docs/validation.md` document the controls and their defaults. They also state that budgets and tmpfs sizes do not bound workspace or state storage.

Semantics, defaults, formats and messages match Claude and Codex, with the `ANTIGRAVITY_CONTAINER_` prefix. The shared Python budget module, setup questions and qualification binding arrive with the Wave 3 network port.

## Capabilities

### New Capabilities

- `container-isolation`: privilege dropping, explicit and verified resource budgets, and documentation of these controls. The capability name is the one agreed for all five wrappers in Wave 1. Antigravity did not have this capability yet.

### Modified Capabilities

- `workspace-mounts`: refusal of sensitive workspace roots and the exact unsafe-workspace override.
- `container-launcher`: optional session lifetime limit with preserved exit status.
- `runtime-image`: pinned `agy`, OpenSpec and base image inputs. The refresh requirement changes from "recheck the Google distribution" to "rebuild the recorded inputs; update only through maintenance".

## Impact

- `antigravity-container.sh`:
  - validation of the new variables and the workspace guard, before engine queries;
  - new `podman create` arguments;
  - post-create budget inspection;
  - lifetime notice;
  - help text.
- `Containerfile`: pinned base digest, OpenSpec version, and `agy` URL and SHA-512 per architecture, replacing the remote installer script.
- Tests:
  - `tests/test_wrapper.py`: fake-engine support for the budget inspection, and new cases;
  - `tests/test_runtime.py`: effective hardening, budgets and lifetime, plus the existing keyring, D-Bus and delegation checks under hardening;
  - `tests/image-smoke.sh` if affected;
  - new `tests/test_image_pins.py`.
- Documentation: `README.md`, `AGENTS.md`, `docs/validation.md`.
- Users:
  - hosts without delegated cgroup v2 `cpu`/`memory`/`pids` controllers can no longer start sessions;
  - launching from a sensitive directory requires the override;
  - a rebuild installs `agy` 1.5.3 instead of the latest release.
