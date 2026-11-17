## ADDED Requirements

### Requirement: Shared persistent state by default
With `ANTIGRAVITY_CONTAINER_STATE_DIR` unset or empty, the wrapper SHALL mount the host `~/.gemini`, or `ANTIGRAVITY_CONTAINER_CONFIG_DIR` when set, read/write at `/antigravity-home/.gemini` below an ephemeral home. A nonempty `ANTIGRAVITY_CONTAINER_STATE_DIR` SHALL select an isolated persistent home mounted at `/antigravity-home`, holding `.gemini`, settings, sessions, caches and account tokens. Both paths SHALL be absolute without colon, CR or LF, checked before engine queries, and SHALL conflict when both are nonempty. Selected state SHALL be caller-owned, accessible and private before image operations, and SHALL never be recursively re-permissioned. Every child of an isolated home and the CA mount parent SHALL resolve inside the home and be private.

#### Scenario: Shared state by default
- **WHEN** no state variable is set
- **THEN** the host `~/.gemini` is mounted at `/antigravity-home/.gemini` after the ownership and privacy checks, and the rest of the home is ephemeral
- **AND** the README states that other tools using `~/.gemini`, such as Gemini CLI, then share their files with the container

#### Scenario: Isolated state reused
- **WHEN** a second session starts with the same `ANTIGRAVITY_CONTAINER_STATE_DIR`
- **THEN** it finds previous settings and sessions without mounting the host home or host `~/.gemini`

#### Scenario: New state
- **WHEN** the selected state does not exist on a filesystem enforcing Unix permissions
- **THEN** it is created privately and validated before any image operation

#### Scenario: Insecure existing state
- **WHEN** the selected state allows group/other access or has incorrect ownership
- **THEN** startup fails before image operations with actionable guidance rather than silently changing existing permissions

#### Scenario: Configuration directory override
- **WHEN** `ANTIGRAVITY_CONTAINER_CONFIG_DIR` names a private absolute directory and `ANTIGRAVITY_CONTAINER_STATE_DIR` is unset or empty
- **THEN** it replaces `~/.gemini`; a relative value, or one combined with a nonempty `ANTIGRAVITY_CONTAINER_STATE_DIR`, fails before engine queries
- **AND** every session has `ANTIGRAVITY_CONTAINER_CONFIG_DIR=/antigravity-home/.gemini`, and the host value is never forwarded

#### Scenario: Isolated child escapes the home
- **WHEN** `.gemini` or the CA mount parent in an isolated home is a symbolic link that resolves outside the home, or grants group/other access
- **THEN** startup fails before image operations naming the path

#### Scenario: Isolated state overlaps the workspace
- **WHEN** the selected state directory or configuration directory overlaps the workspace or worktree parent
- **THEN** the wrapper exits with status 1 naming the variable before any engine query

### Requirement: Read-only state
`ANTIGRAVITY_CONTAINER_READONLY_STATE`, a boolean (`1`, `true`, `yes`; empty, `0`, `false`, `no`), SHALL mount the configuration directory read-only below the ephemeral home, taken from shared state or from the isolated home. That directory SHALL already exist and be accessible to the caller; the launcher SHALL NOT create it, check its owner or privacy, or pass it to restricted preparation as writable. The isolated home itself SHALL NOT be mounted.

#### Scenario: Read-only shared state
- **WHEN** `ANTIGRAVITY_CONTAINER_READONLY_STATE=1` is set and `~/.gemini` exists
- **THEN** the session sees it read-only and writes there fail

#### Scenario: Missing state
- **WHEN** read-only state is selected and the configuration directory does not exist
- **THEN** the launch stops before the engine and names the missing directory

## REMOVED Requirements

### Requirement: Dedicated persistent state
**Reason**: Every wrapper shares the host's native agent directories by default (launcher contract U4); the dedicated home `~/.local/share/antigravity-container/home` is no longer used.
**Migration**: Use "Shared persistent state by default"; set `ANTIGRAVITY_CONTAINER_STATE_DIR` to the former dedicated home to keep using it.

## MODIFIED Requirements

### Requirement: Read only system and temporary storage
The container SHALL use a read-only root filesystem, writable state and workspace, and explicitly provisioned ephemeral tmpfs storage. It SHALL expose only these mounts, the read-only CA bundle when enabled, the toolchain library, the guard and its session inputs in restricted modes, and the Podman socket with private nested-Podman storage when explicitly enabled in unrestricted mode. Because the profile declares executable temporary storage, `/tmp` and the ephemeral home SHALL be executable; `/var/tmp` and `/run` SHALL be `noexec`.

#### Scenario: System write attempt
- **WHEN** a process attempts to modify `/usr` and then writes a temporary file
- **THEN** the first operation fails, the second succeeds, and the temporary file does not persist after container removal

#### Scenario: Explicit temporary paths
- **WHEN** a CLI or shell container starts
- **THEN** `/tmp` is writable and executable with `nosuid,nodev`, mode `1777`, and a 512 MiB limit
- **AND** `/var/tmp` is writable with `nosuid,nodev,noexec`, mode `1777`, and a 512 MiB limit
- **AND** with shared state the ephemeral home `/antigravity-home` is writable and executable with `nosuid,nodev`, mode `1777`, and a 512 MiB limit
- **AND** `/run` is a `nosuid,nodev,noexec` tmpfs with a 32 MiB limit that the session user cannot write

#### Scenario: Temporary data expires
- **WHEN** a session writes to `/tmp`, `/var/tmp` and the ephemeral home outside `.gemini`, terminates, and a new session starts
- **THEN** those files are absent from the new session

#### Scenario: Private keyring runtime
- **WHEN** an account session starts in a restricted mode with explicit temporary mounts
- **THEN** no keyring runtime directory is created, `XDG_RUNTIME_DIR` is the guard's private `/tmp/sandbox-runtime`, and the guard's private-root layout checks accept the mounts
