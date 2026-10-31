# Tasks

## 1. Official runtime image

- [x] 1.1 Create `Containerfile` from `node:22-bookworm-slim` with the design inventory, OpenSpec, nano, and a dedicated home; verify availability of the declared commands and `openspec --version` without host installations.
- [x] 1.2 Install `agy` using the official installer and `--dir /usr/local/bin`, retaining SHA-512 verification and disabling automatic updates; verify architecture, version, and actual linking, distinguishing static binaries from missing libraries.
- [x] 1.3 Add a repeatable image check as a non-root UID/GID with a read-only root and dedicated writable directories; verify `agy --help`, `agy --version`, tools, and temporary directories without permission or update errors.
- [x] 1.4 Document the selected base, official sources, inventory distinguishing Google requirements from project tools, and build/update/rollback procedures in the README; verify that documentation matches the Containerfile and version printed by the build.

## 2. Entrypoint and authentication

- [x] 2.1 Add an entrypoint with a private D-Bus session and GNOME Keyring limited to `secrets`, a runtime directory per UID, and persistent state; use `secret-tool` to verify storage and retrieval of a test credential without the host bus/display, including after container recreation.
- [x] 2.2 Implement creation/unlocking of a passphrase-protected keyring with the passphrase read without echo from `/dev/tty`, separate from agy stdin; verify incorrect passphrases, missing TTY, service shutdown, and absence of secrets in logs, the environment, and process arguments.
- [x] 2.3 Make the Google URL/code flow work in a headless context by checking the remote-environment signals actually recognized by the selected binary; complete login, restart with session reuse after keyring unlocking, and `/logout` tests, without treating API provider tests as sufficient.
- [x] 2.4 Handle help/version and the `modelProvider: gemini` provider without requesting unlocking, preserving native errors for a missing key; verify these paths without a TTY and without printing test credentials.
- [x] 2.5 Document onboarding, passphrase/keyring, dedicated state, remote login, API keys, logout, and concurrency limits; verify two sessions sharing state and report observed behavior and the use of separate state directories for separate profiles.

## 3. Podman wrapper and mounts

- [x] 3.1 Create `antigravity-container.sh` with the four wrapper flags and array-based forwarding; add fake-Podman checks for argument order, spaces, empty values, CLI arguments, shell, and help without side effects.
- [x] 3.2 Implement image selection, local rootless Podman checks, builds from the script directory, and explicit rebuilds without cached downloads; verify a missing image, `--container-build`, build errors, and rejection of remote or rootful contexts.
- [x] 3.3 Implement mounting the physical current directory at the same absolute path and replacing it with its immediate parent through `--container-git-worktree`; verify argv with symlinks and paths containing spaces, and test a real worktree with shared metadata in the parent.
- [x] 3.4 Implement configurable dedicated state with private permissions, keep-id identity, read-only root, and tmpfs; verify file ownership, state persistence, and invisibility of a host sentinel file outside the workspace without the socket.
- [x] 3.5 Implement conditional TTY allocation, stdin forwarding, exit status, signals, and workspace-index names with collision handling; verify non-interactive pipelines, interruption, process failure, and two sessions starting without removing others.
- [x] 3.6 Document use through an `agy` alias, help, shell, image, state, mounts, and worktrees, including exposed siblings and metadata outside the mount boundary; verify examples from a project outside the wrapper directory.

## 4. Agent permissions and Podman access

- [x] 4.1 Implement independent parsing of `ANTIGRAVITY_YOLO` and `ANTIGRAVITY_CONTAINER_PODMAN` booleans and insertion of the official flag for agy only; verify all accepted forms, invalid values before side effects, and the four combinations.
- [x] 4.2 Add a configurable rootless socket, accessibility/service checks, and remote connection for the internal client only with opt-in; verify a missing socket with the variable disabled, failure with opt-in, and absence of a nested daemon or privileged flags.
- [x] 4.3 Test a child container through the host service with an absolute workspace bind and a sentinel file; verify read/write access and file ownership from the child, recording SELinux limitations without automatically disabling policy.
- [x] 4.4 Document the four permission combinations, socket activation, and expansion beyond the filesystem boundary, distinguishing approval bypass from the internal sandbox; verify that help/README do not promise project confinement when the host service is enabled.

## 5. Integrated acceptance

- [ ] 5.1 Run wrapper and runtime checks on Linux rootless Podman, including amd64 and arm64 builds/execution on suitable runners; record versions, commands, results, and platforms actually verified without marking unavailable tests as passed.
- [x] 5.2 Run the complete flow from empty state with account login, a project task, restart, logout, and worktrees; verify mount boundaries and absence of dependencies on the host browser, keyring, or bus.
- [x] 5.3 Run a headless prompt with the API provider and one with YOLO, verifying that YOLO does not add the socket; test `--sandbox` separately and report namespace availability and kernel limitations without expanding privileges.
- [x] 5.4 Review README, help, and inventory against the final image and the five specifications; verify matching names/defaults, explicit updates, documented limitations, and absence of claims for tests not performed.

Task 5.1 remains open: amd64 verification passed, but arm64 build and
execution have not been tested. The user currently has no ARM machine, and
the local engine has no registered ARM emulator. This is unavailable
verification, not a passing result; see `docs/validation.md`.

Archive disposition (2026-10-31): the user explicitly authorized archiving
and syncing this change with 22 of 23 tasks complete. The unchecked task
records the outstanding arm64 verification and is not marked as passed.
