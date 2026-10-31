# Design

## Context

See `proposal.md` for the motivation. Repository inspection found `LICENSE`, OpenSpec configuration, and no implementation or main specifications. The references were inspected on 2026-10-31 through their READMEs, Containerfiles, and wrappers on `main`:

- [claude-container](https://github.com/yarilc/claude-container): rootless execution, keep-id, a read-only root filesystem, absolute paths, a worktree flag exposing the immediate parent, nano, and optional host CA trust.
- [codex-container](https://github.com/yarilc/codex-container): the same wrapper model and Node Bookworm image, OpenSpec, Python, and Bubblewrap.

Both always mount the Podman socket. Here it will be optional to support the environment-based configuration requested by the user. Mounts and extensions from the references will not be imported indiscriminately.

Verified Google sources:

- [Quickstart](https://antigravity.google/docs/getting-started?tab=cli) and [download](https://antigravity.google/download): the `agy` CLI is separate from the IDE; the public page lists glibc >= 2.28 and GLIBCXX >= 3.4.25 for Linux. This is not a separate, complete list of CLI packages.
- [Official installer](https://antigravity.google/cli/install.sh), read without executing it: selects amd64/arm64, downloads the platform manifest, verifies SHA-512, and supports `--dir`; uses Bash, curl/wget, sed, coreutils, and tar/gzip for archives. Installing `agy` does not require npm.
- [CLI reference](https://antigravity.google/docs/cli/reference): `--dangerously-skip-permissions`, `--sandbox`, and `-p`; YOLO maps to the native approval bypass without inventing a `--yolo` flag.
- [Settings](https://antigravity.google/docs/cli/using): files under `~/.gemini/antigravity-cli/`.
- [Authentication](https://antigravity.google/docs/install?tab=cli): Linux keyring, remote URL/code flow, and API keys with an explicitly selected provider. Binding configuration alone is not documented as sufficient to preserve login.
- [Troubleshooting](https://antigravity.google/docs/cli/troubleshooting): D-Bus/keyring in headless environments and `AGY_CLI_DISABLE_AUTO_UPDATE=true` to prevent automatic updates.
- [Sandbox](https://antigravity.google/docs/sandbox/): Linux isolation through namespaces; containers can prevent its use. Google does not appear to declare the external `bwrap` command as a mandatory dependency.

## Goals / Non-Goals

**Goals:** make every expansion of host access verifiable; use the native CLI; provide writable paths compatible with non-root identity and a runtime without a desktop; keep commands familiar to users of the two reference projects.

**Non-Goals:** reproduce the IDE or install a complete graphical environment; guarantee confinement to the project when Podman service access is granted; manage ADC/enterprise, corporate CAs, host SSH/Git, or browser integrations in this first version. The native API key provider is included as an alternative without a desktop.

## Decisions

### 1. Debian base with Node for OpenSpec

Use `docker.io/library/node:22-bookworm-slim`. Debian 12 provides glibc 2.36 and libstdc++ compatible with the published thresholds; verify compatibility in the built image. This is a project choice, not an image officially recommended by Google. Node/npm support OpenSpec and workflow tools, while `agy` comes from the official native distribution.

Alternatives considered: plain Debian slim would require adding and maintaining Node separately for OpenSpec; Ubuntu meets the requirements but offers no concrete advantage over the base already used by the references; Alpine adds a libc variant that is unnecessary for this first version.

Planned inventory, to be documented in the README with native dependencies distinguished from project additions:

| Group | Planned packages/tools | Rationale |
| --- | --- | --- |
| Installation and ABI | bash, ca-certificates, curl, coreutils, sed, grep, tar, gzip, libc6, libstdc++6, libgcc-s1 | Official installer, HTTPS, extraction, and native compatibility |
| Linux credentials | dbus, gnome-keyring, libsecret-1-0, libsecret-tools | Local Secret Service and secret storage/retrieval checks |
| Workflow | Node 22/npm from the base, `@fission-ai/openspec`, python3, bubblewrap, podman | Tool parity with the references; bwrap is not presented as a Google requirement |
| Repository | git, ripgrep, findutils, diffutils, patch, gawk, nano, less | Search, editing, terminal editor, and local Git operations |
| Archives and diagnostics | bzip2, xz-utils, zip, unzip, file, procps, util-linux | Archives, diagnostics, and environment checks |

Use apt without recommended packages, remove caches and package lists, and set `EDITOR=VISUAL=nano`. The build runs `agy --version`, checks any dynamic dependencies with `ldd`/`file`, and verifies the declared commands. A static binary must not be mistaken for a linking error. Do not add the Python SDK, Chromium, or Electron libraries merely by analogy with the IDE.

### 2. Official installation and image-managed updates

Download the installer to a file, run it with Bash and `--dir /usr/local/bin`, and retain its SHA-512 verification. Do not use installation flags found only in documentation if the distributed script does not accept them. Install `agy` in the read-only root filesystem, set `AGY_CLI_DISABLE_AUTO_UPDATE=true`, and update through `--container-build` with the download build cache disabled. Log the actual version and architecture. Do not promise bit-for-bit reproducibility: the installer channel selects the current release.

Rejected alternative: storing the executable in the persistent home, which would decouple the runtime from the image version and allow silent updates.

### 3. Wrapper and environment contract

Use a Bash wrapper with arrays and no `eval`, exposing these public variables:

| Variable | Default | Effect |
| --- | --- | --- |
| `ANTIGRAVITY_CONTAINER_IMAGE` | `localhost/antigravity-cli:latest` | Image to use/build |
| `ANTIGRAVITY_CONTAINER_STATE_DIR` | `${HOME}/.local/share/antigravity-container/home` | Dedicated persistent home |
| `ANTIGRAVITY_YOLO` | disabled | Adds `--dangerously-skip-permissions` to agy only |
| `ANTIGRAVITY_CONTAINER_PODMAN` | disabled | Exposes the rootless Podman service |
| `ANTIGRAVITY_CONTAINER_PODMAN_SOCKET` | `${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock` | Unix socket when enabled |
| `GEMINI_API_KEY` | absent | Forwarded by name, if present, for the provider configured by the user |

Both booleans accept an empty value and `0/false/no`, or `1/true/yes`, case-insensitively. Invalid values fail before building, creating state, or starting a container. Do not import the entire host environment or `.env` files. Never print the API key. Help does not require Podman. Resolve builds relative to the physical wrapper path, not the current directory; check for local rootless Podman and reject remote contexts/Podman Machine in this version.

The wrapper consumes only the four documented `--container-*` flags and uses arrays for forwarding. Allocate a TTY only when terminals are available; preserve stdin for `-p`, exit codes, and signals. Use workspace-index names and handle startup collisions by trying a new index without deleting other sessions.

### 4. Mounts and identity

Use `pwd -P`, `--userns=keep-id`, `--user UID:GID`, `--workdir` matching the host path, `--read-only`, and `--rm`. The workspace mount is the current directory or, in worktree mode, `dirname(cwd)`; do not search for Git roots. The parent can be the home directory or `/`: the README must clearly explain the breadth of this explicit choice. Git metadata outside the parent remains inaccessible.

Mount dedicated state at `/antigravity-home`, set `HOME` there, and use `umask 077` and 0700 directories for new data. This includes `.gemini/antigravity-cli`, caches, OpenSpec settings, and `.local/share/keyrings` without mounting the corresponding paths from the host home. Do not automatically import generic `~/.gemini` state, which might contain data from other Google products. Document protection of existing data without recursively changing its ownership or permissions.

Use tmpfs for `/tmp` and `/run`; provide a private, writable 0700 runtime directory per UID for D-Bus and the keyring. Check the CLI's actual temporary-file requirements before applying `noexec`: do not copy that reference option if it prevents native CLI components from starting. No additional mounts for host OpenSpec configuration, CAs, SSH, D-Bus, displays, or the full home directory.

### 5. Podman socket as explicit delegation

When enabled, verify the local Unix socket, accessibility, and rootless service; mount it at `/run/podman/podman.sock` and set `CONTAINER_HOST=unix:///run/podman/podman.sock`. The client uses the host service; it does not start a nested daemon or storage engine. Child bind mounts work because workspace paths match host paths.

When disabled, do not require the socket to exist. Do not automatically use `--privileged`, `seccomp=unconfined`, or globally disable SELinux. On SELinux enforcing hosts, check socket compatibility and provide an explicit diagnosis if policy prevents access: do not claim verified support solely because it works on hosts without SELinux. The [Podman documentation](https://docs.podman.io/en/latest/markdown/podman-system-service.1.html) describes both compatible policy requirements and the full control granted by the API.

### 6. Authentication with services local to the container

Provide an entrypoint for `agy`, keeping the shell directly usable. For account login, start a `dbus-run-session` session and GNOME Keyring with only the `secrets` component; the [Debian manual](https://manpages.debian.org/bookworm/gnome-keyring/gnome-keyring-daemon.1.en.html) documents creating/unlocking the login keyring through a password on stdin. Use a dedicated keyring protected by a passphrase, read without echo from `/dev/tty`, never saved in the environment, logs, or files. Reading the secret must not consume stdin intended for agy. Do not automatically choose an empty keyring password.

Profiles and the keyring persist in the dedicated home; the user may need to unlock the keyring for each new container without repeating OAuth while the session remains valid. The [D-Bus manual](https://manpages.debian.org/bookworm/dbus-daemon/dbus-run-session.1.en.html) supports tying the bus lifetime to the child process and preserving its exit status.

To obtain Google's URL/code flow in a container without a desktop, verify remote-environment detection in the selected binary and establish the headless context only for the agy process. The details of SSH signals recognized by the binary are not public contracts: do not assume that an absent DISPLAY is sufficient. The URL/code test is a mandatory acceptance criterion, not a success inferred from package installation.

Help/version do not require unlocking. For automation without a TTY, use the native API key provider, manually setting `modelProvider: gemini` in the dedicated settings.json. This path does not require a keyring; do not attempt to migrate ADC or host keyrings. An account path requiring unlocking without a terminal exits with guidance to use interactive login or the API provider. Termination and signals must also stop local services.

Rejected alternative: binding the host bus and keyring, which would expand access to external credentials and require a desktop session. Do not promise login persistence before actual restart and logout tests.

### 7. Verification proportional to the boundaries

Test the wrapper using a fake Podman executable that records structured argv: consumed and forwarded flags, booleans, four YOLO/socket combinations, spaces/empty arguments, worktrees and symlinks, socket errors, help without side effects, builds from the script path, TTY, exit status, and name collisions.

Run runtime checks on real rootless Podman: toolchain and ABI on amd64/arm64, writes and ownership, read-only root, a host sentinel outside the workspace, persistent state, a real worktree with shared metadata, a child container with a bind mount only in socket mode, Secret Service, and login/restart/logout. Test `--sandbox` separately: namespace availability depends on the host and must not trigger fallback to broader privileges. Record the environment and limitations of tests actually performed.

Acceptance found an internal sandbox incompatibility with CLI 1.4.12 and rootless Podman 4.9.3 on Linux amd64 / WSL2: the engine's standard seccomp profile blocks `sethostname`, causing the Google sandbox server to abort. Basic namespace tests passed independently. The user chose to retain the standard policy and document the failure; no custom-profile option or extra capabilities are introduced. This satisfies the compatibility-reporting check without claiming successful internal sandbox execution. Evidence and future recheck guidance are in `docs/validation.md`.

## Risks / Trade-offs

- Podman socket → exceeds the filesystem boundary; separate opt-in and an explanation alongside examples.
- Google dependencies and versions change, with pages listing different versions → use the actual installer/manifests, record releases, and check CLI/ABI during the build; revalidate requirements before implementation.
- Keyring without a desktop and remote detection → dedicated entrypoint, actual Secret Service and OAuth tests; do not claim account login is complete based solely on an API key test.
- Keyring passphrase required → explicit interactive unlocking; API key for automation; no automatic passphrase storage.
- Multiple sessions share state/keyring → verify concurrent access without corruption; use separate state directories for separate profiles and document daemon limitations.
- Google sandbox blocked by namespaces/seccomp/SELinux → document actual availability; keep the container rootless without automatically expanding privileges.
- Build follows the current channel → explicit updates and visible version; rollback by retaining the previous image tag/ID.

## Migration Plan

No existing code or data migration. Implement the image and entrypoint, then the wrapper, checks, and README. First launch uses new state; explicit login or API key configuration. Update only through rebuilding and retain the previous image for rollback. Removing ephemeral containers does not delete application state; deleting that state remains a manual user action.
