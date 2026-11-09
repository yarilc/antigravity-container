# Design

## Context

`antigravity-container.sh` (333 lines) runs in this order:
1. parses options and validates `ANTIGRAVITY_YOLO`;
2. checks Podman and `timeout`;
3. verifies the launch engine and, when enabled, the delegation socket;
4. creates and validates the private state directory, which defaults to `~/.local/share/antigravity-container/home`;
5. inspects or builds the image;
6. reserves a name with `podman create` and attaches with `podman start`.

The image entrypoint uses one of two modes:
- **Gemini API-key mode** runs `agy` directly.
- **Account mode** runs it inside `keyring-session.sh`. That script starts a private `dbus-run-session` and unlocks `gnome-keyring-daemon` with a terminal passphrase.

`Containerfile` installs `agy` by running Google's `install.sh`. The script reads a "latest" manifest (`manifests/linux_<arch>.json`) and verifies the SHA-512 it contains. It also installs OpenSpec unpinned on an unpinned base. The references are `claude-container.sh` at tag `sandbox-ref-2` and the archived Codex change `2026-11-09-harden-session-baseline`.

## Goals / Non-Goals

**Goals:**
- Same observable semantics, defaults, formats and diagnostics as Claude and Codex, with the `ANTIGRAVITY_CONTAINER_` prefix.
- All new validation and the workspace guard before the first engine query or state creation.
- Real-engine evidence that the keyring, private D-Bus, API-key mode and delegation work without capabilities.
- Reproducible `agy` builds per architecture.

**Non-Goals:**
- Python budget normalization, setup questions, qualification binding and maintenance gate (Wave 3).
- Moving YOLO and persistent-state requirements into `container-isolation` and `persistent-state`. This relocation, noted in Wave 1, is a later change.
- Changing the keyring design or the documented remote login flow.

## Decisions

### D1: Port the reference Bash code
The budget and lifetime validation, the workspace guard, the `podman create` arguments, the post-create inspection and the lifetime notice are copied from the Codex implementation. Only the prefix and the program name change. Regular expressions, ranges and messages stay identical:
- memory: `k`/`m`/`g`, capped at 2^50;
- CPUs: at most 3 decimals, up to 1024;
- process limit: 1 to 4194304;
- lifetime: up to 10 digits;
- defaults: `${VAR-default}`, with `${VAR:-0}` for the lifetime.

### D2: Validation order
The new block runs immediately after option parsing and `ANTIGRAVITY_YOLO` validation, before `command -v podman`. `workspace` and `workspace_mount` are computed there, earlier than today, and reused later. Help still exits during parsing.

### D3: Container arguments
`container_args` gains, for every mode:
- `--cap-drop=all` and `--security-opt=no-new-privileges`;
- `--memory=<bytes>`, `--cpus=<text>` and `--pids-limit=<n>`;
- `--timeout <n>` when the lifetime is greater than zero.

The keep-id user, read-only root and tmpfs layout are unchanged.

### D4: Post-create budget check
After create and before start, the wrapper runs a bounded `podman inspect` on the owned full ID. It requires `{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}} {{.HostConfig.PidsLimit}}` to equal the selected budgets. A failure or mismatch dies with the cgroup v2 controller-delegation diagnostic, and the existing EXIT cleanup removes only the owned container.

### D5: Lifetime notice
The wrapper records `SECONDS` before `podman start`. On a non-zero client status with elapsed time at least the limit, it prints `antigravity-container: session lifetime limit reached (N s); exit status S`. The status is unchanged; 255 was measured on Podman 4.9.3.

### D6: Workspace guard
The guard uses the same refused set as the reference, compared on the physical mount source. The physical home is `cd -- "$HOME" && pwd -P`. The default state directory lives under the home, but it is a separate mount and is not affected.

### D7: Keyring and D-Bus under hardening
`dbus-run-session` and `gnome-keyring-daemon` run as the mapped user. They need no capabilities beyond the AF_UNIX sockets in the private `XDG_RUNTIME_DIR` on `/tmp`.
- `gnome-keyring-daemon` may try to lock memory, which needs `CAP_IPC_LOCK`, and may carry file capabilities. Without capabilities and with no-new-privileges, that request fails. The daemon is expected to warn and continue, because Debian builds treat locked memory as best effort.
- The existing runtime keyring tests check creation, persistence, wrong passphrase, missing terminal, mismatch and concurrent locking. They become the acceptance check.
- If the daemon cannot work, the change stops and the trade-off goes to the operator. Capabilities are not added back.

### D8: Pinned `agy` artifact instead of the installer
`Containerfile` records these arguments:
- `AGY_VERSION=1.5.3`;
- for amd64, `AGY_URL_AMD64` and `AGY_SHA512_AMD64`;
- for arm64, `AGY_URL_ARM64` and `AGY_SHA512_ARM64`.

The URLs are the immutable `storage.googleapis.com/antigravity-public/antigravity-cli/1.5.3-6604829099950080/...` paths that the official manifests returned on 2026-11-09. The install step:
1. selects the pair with `uname -m` (`x86_64`/`amd64` or `aarch64`/`arm64`) and fails explicitly on any other architecture;
2. downloads with `curl --fail`;
3. checks with `sha512sum --check`;
4. extracts the `antigravity` member to `/usr/local/bin/agy`;
5. runs `agy --version`, requiring it to start with `AGY_VERSION`.

The installer's post-install `agy install --dir`, which configures the shell, is not needed for a binary already on `PATH`, so it is dropped. `AGY_CLI_DISABLE_AUTO_UPDATE=true` and the read-only root already prevent self-update.
- Alternative: keep `install.sh`. Rejected, because it always installs the latest release and has no version argument.
- Risk: Google may remove old artifacts. The build then fails closed, and the maintenance procedure moves the pin.

### D9: Other pins
- The base image uses the `sandbox-ref-2` digest `sha256:4b150b48…79da`.
- OpenSpec is pinned with `ARG OPENSPEC_VERSION=1.16.0`.
- `tests/test_image_pins.py` follows the reference test. It also requires the `agy` URL and SHA-512 arguments for both architectures and rejects `install.sh` or manifest URLs.

### D10: Tests
`tests/test_wrapper.py` gets the same cases as Codex:
- the fake engine answers the `inspect` call, which `FAKE_AGENT_BUDGETS` can override;
- the hardening flags in every mode, including YOLO and delegation;
- budget overrides, and every rejected form failing before any engine call;
- a budget mismatch or an inspection failure removing only the owned container;
- the lifetime argument and notice;
- the refused workspaces and the exact override;
- help.

`tests/test_runtime.py` adds:
- effective capabilities and `NoNewPrivs`;
- cgroup budgets with default and overridden values, with and without delegation;
- process-limit enforcement;
- lifetime expiry and an early exit;
- a refused home workspace;
- Git, OpenSpec and bubblewrap.

The existing keyring, API-key and delegation tests run unchanged under the new defaults. Unit suites run in a host runner container, because this agent sandbox has a `noexec` `/tmp` and cannot bind Unix sockets on its v9fs workspace.

## Risks / Trade-offs

- **The keyring daemon refuses to start without `CAP_IPC_LOCK`:** D7 measures it first. If it fails, the change pauses for an operator decision and capabilities are not added back.
- **The `agy` 1.5.3 upgrade changes login or keyring behavior:** the existing credential-free keyring and API-key checks run on the new image. Authenticated login remains an operator check, recorded separately.
- **Hosts without delegated cgroup controllers:** the launch stops with a diagnostic and the README states the requirement.
- **4 GiB or 512 processes too small:** operators can override the budgets per launch.
- **Users who launch from their home or a drive root:** the launch is refused with guidance, and the exact override exists.

## Migration Plan

1. Implement on branch `harden-session-baseline`. Run the unit suites in a runner container and the real-engine suite on the host.
2. Users rebuild with `--container-build` to get the pinned image. Existing images keep working until they rebuild.
3. Account users verify their login after the rebuild. The keyring format and state directory are unchanged.
4. Rollback: revert the commit and rebuild. No state format changes.
