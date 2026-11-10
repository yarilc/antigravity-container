# Spec Delta

## MODIFIED Requirements

### Requirement: Dedicated persistent state
The wrapper SHALL mount the persistent application home at `/antigravity-home`: the dedicated home `${HOME}/.local/share/antigravity-container/home` when `ANTIGRAVITY_CONTAINER_STATE_DIR` is unset, the named private home when it is nonempty, and shared `~/.gemini` state when it is empty. State SHALL keep settings, sessions, caches and account tokens, be caller-owned, accessible and private before image operations, and never be recursively re-permissioned.

#### Scenario: State reused
- **WHEN** a second session starts with the same dedicated or isolated state directory
- **THEN** it finds previous settings and sessions without mounting the host home or generic host `~/.gemini`

#### Scenario: New state
- **WHEN** the selected state does not exist on a filesystem enforcing Unix permissions
- **THEN** it is created privately and validated before any image operation

#### Scenario: Insecure existing state
- **WHEN** the selected state allows group/other access or has incorrect ownership
- **THEN** startup fails before image operations with actionable guidance rather than silently changing existing permissions

#### Scenario: Shared state selected explicitly
- **WHEN** `ANTIGRAVITY_CONTAINER_STATE_DIR` is set to an empty value
- **THEN** only the host `~/.gemini`, or `ANTIGRAVITY_CONTAINER_CONFIG_DIR` when set, is mounted at `/antigravity-home/.gemini`, after the same ownership and privacy checks
- **AND** the README states that other tools using `~/.gemini`, such as Gemini CLI, then share their files with the container

#### Scenario: Configuration directory override
- **WHEN** `ANTIGRAVITY_CONTAINER_CONFIG_DIR` names a private absolute directory with shared state
- **THEN** it replaces `~/.gemini`; a relative value, or a value without shared state (an unset or nonempty `ANTIGRAVITY_CONTAINER_STATE_DIR`), fails before engine queries
- **AND** every session has `ANTIGRAVITY_CONTAINER_CONFIG_DIR=/antigravity-home/.gemini`, and the host value is never forwarded

#### Scenario: Isolated state overlaps the workspace
- **WHEN** the selected state directory or configuration directory overlaps the workspace or worktree parent
- **THEN** the wrapper exits with status 1 naming the variable before any engine query

### Requirement: Read only system and temporary storage
The container SHALL use a read-only root filesystem, writable state and workspace, and explicitly provisioned ephemeral tmpfs storage with automatic read-only tmpfs provisioning disabled. It SHALL expose only these mounts, the read-only CA bundle when enabled, the guard and its session inputs in restricted modes, and the Podman socket when explicitly enabled in unrestricted mode.

#### Scenario: System write attempt
- **WHEN** a process attempts to modify `/usr` and then writes a temporary file
- **THEN** the first operation fails, the second succeeds, and the temporary file does not persist after container removal

#### Scenario: Explicit temporary paths
- **WHEN** a CLI or shell container starts
- **THEN** `/tmp` is writable and executable with `nosuid,nodev`, mode `1777`, and a 512 MiB limit
- **AND** `/var/tmp` is writable with `nosuid,nodev,noexec`, mode `1777`, and a 512 MiB limit
- **AND** `/run` is writable with `nosuid,nodev,noexec` and a 32 MiB limit

#### Scenario: Temporary data expires
- **WHEN** a session writes to `/tmp`, `/var/tmp`, and `/run`, terminates, and a new session starts
- **THEN** those files are absent from the new session

#### Scenario: Private keyring runtime
- **WHEN** an account session starts in a restricted mode with explicit temporary mounts
- **THEN** no keyring runtime directory is created, `XDG_RUNTIME_DIR` is the guard's private `/tmp/sandbox-runtime`, and the guard's private-root layout checks accept the mounts
