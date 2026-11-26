# workspace-mounts Specification

## Purpose

Define Antigravity's host data boundary and preserve workspace and worktree paths through the private session container engine.

## Requirements

### Requirement: Default workspace boundary

By default, the wrapper SHALL mount only the physical current directory as the read/write workspace at the same absolute path and retain it as the working directory. It SHALL avoid implicit mounts of the host home, its services, or generic credentials.

#### Scenario: Ordinary project

- **WHEN** the wrapper starts from `/projects/app` without the worktree option
- **THEN** `/projects/app` is accessible and writable, while a host sentinel file in `/projects/other` is inaccessible

#### Scenario: Symbolic cwd

- **WHEN** the current directory is reached through a symbolic link
- **THEN** the mount and working directory use the resolved physical path

#### Scenario: Session engine resolves a workspace bind

- **WHEN** a session starts a nested container with a bind of its workspace through its private engine
- **THEN** the engine resolves the workspace source at the same absolute path that the outer launcher uses

### Requirement: Explicit parent directory for worktrees

With `--container-git-worktree`, the wrapper SHALL mount the immediate parent of the physical current directory at the same absolute path and retain the original working directory. It SHALL document that the entire parent, including siblings, is writable and that it does not automatically search for a Git root.

#### Scenario: Shared metadata in parent

- **WHEN** the wrapper starts from `/projects/repo/main` with shared Git metadata under `/projects/repo` and the worktree flag
- **THEN** it mounts `/projects/repo`, works in `/projects/repo/main`, and Git can access shared metadata and create sibling worktrees

#### Scenario: Metadata outside selected parent

- **WHEN** a worktree points to metadata outside the selected parent
- **THEN** the wrapper adds no other mounts and documents the limitation instead of implicitly expanding access

#### Scenario: Session engine uses the same worktree scope

- **WHEN** the session has a private engine and the worktree option is active
- **THEN** the engine gets the selected parent at the same absolute path and the session still starts in the original project directory

### Requirement: Read only system and temporary storage

The container SHALL use a read-only root filesystem, writable state and workspace, and explicitly provisioned ephemeral tmpfs storage. It SHALL expose only these mounts, the read-only CA bundle when enabled, the toolchain library, and the guard and its session inputs in restricted modes. An engine-enabled session SHALL also see the host's `/sys` read-only. Host service sockets stay outside both the session and its engine. Because the profile declares executable temporary storage, `/tmp` and the ephemeral home SHALL be executable. `/var/tmp` and `/run` SHALL be `noexec`.

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

#### Scenario: Session with library images

- **WHEN** an agy or shell session starts with its private engine
- **THEN** the session keeps its read-only root filesystem and approved temporary paths, sees /sys read-only, and uses only its session-scoped engine endpoint

### Requirement: Scoped state creation permissions
The wrapper SHALL limit its private state-creation umask to state creation and preserve the inherited wrapper umask for subsequent operations. It SHALL NOT claim that this sets the container process umask. Account keyring runtime privacy SHALL remain enforced independently inside the container.

#### Scenario: Wrapper operations after state creation
- **WHEN** the wrapper starts with a known inherited umask and creates missing state
- **THEN** state is private while later engine operations observe the inherited wrapper umask

#### Scenario: Container file permissions
- **WHEN** runtime validation creates controlled files in shell, API-provider, and account execution paths
- **THEN** their actual modes are checked against the container process umask and file-creation behavior rather than inferred from the wrapper's state-creation umask
- **AND** the account helper retains its `077` umask and private runtime directory

### Requirement: Sensitive workspace roots are refused
The wrapper SHALL refuse to mount a sensitive directory as the writable workspace. It SHALL compare the physical mount source, after `--container-git-worktree` parent selection, against `/`, the caller's physical home, fixed system directories, single-letter WSL drive roots under `/mnt` and, case-insensitively, the Windows system and profile folders on those drives. Refusal SHALL precede engine queries, state creation and image operations. Descendants of refused directories SHALL remain allowed, except folders inside a Windows profile's `AppData`.

#### Scenario: Refused system directories
- **WHEN** the physical mount source is `/`, `/home`, `/root`, `/etc`, `/usr`, `/var`, `/bin`, `/sbin`, `/lib`, `/lib64`, `/boot`, `/opt`, `/srv`, `/mnt`, `/media`, `/proc`, `/sys`, `/dev`, `/run` or `/tmp`
- **THEN** the wrapper exits with status 1 before any engine query

#### Scenario: Launch from the home directory
- **WHEN** the caller launches the wrapper with the current directory equal to their physical home
- **THEN** the wrapper exits with status 1 and a message naming the refused path and suggesting a project subdirectory
- **AND** no engine query, state directory or image operation occurs

#### Scenario: Worktree parent is sensitive
- **WHEN** the caller launches with `--container-git-worktree` from a directory whose immediate parent is their physical home
- **THEN** the wrapper refuses the parent mount

#### Scenario: Symlinked path resolves to a sensitive root
- **WHEN** the current directory is reached through a symlink whose physical target is `/etc`
- **THEN** the wrapper refuses the workspace using the physical path

#### Scenario: WSL drive root
- **WHEN** the caller launches from `/mnt/d`
- **THEN** the wrapper refuses it, while `/mnt/d/Workspace/project` is accepted

#### Scenario: Ordinary project directory
- **WHEN** the caller launches from a project directory that is not in the refused set
- **THEN** the workspace mount proceeds unchanged

#### Scenario: Windows system and profile folders
- **WHEN** the physical mount source is `/mnt/<drive>/Users`, `/mnt/<drive>/Users/<name>`, `/mnt/<drive>/Users/<name>/Documents`, `/mnt/<drive>/Users/<name>/OneDrive` (also `OneDrive - <organization>`) or its `Documents`, `/mnt/<drive>/Users/<name>/AppData` or any folder inside it, `/mnt/<drive>/Windows`, `/mnt/<drive>/Program Files`, `/mnt/<drive>/Program Files (x86)` or `/mnt/<drive>/ProgramData`, for any single drive letter and any profile name
- **THEN** the wrapper exits with status 1 naming the refused path, before any engine query

#### Scenario: Windows folders in another letter case
- **WHEN** the physical mount source is `/mnt/c/users/YARI` or `/mnt/C/PROGRAM FILES`
- **THEN** the wrapper refuses it like the canonical spelling

#### Scenario: Project below a Windows profile
- **WHEN** the caller launches from `/mnt/c/Users/me/projects/app` or `/mnt/c/Users/me/Documents/GitHub/app`
- **THEN** the workspace mount proceeds, while `--container-git-worktree` from `/mnt/c/Users/me/app` is refused because the parent is the profile

#### Scenario: Folders where Windows runs user code
- **WHEN** the caller launches from `/mnt/c/Users/me/Documents`, which holds the PowerShell profile and modules, or from `/mnt/c/Users/me/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup`
- **THEN** the wrapper refuses it, because code written there would run on Windows outside the sandbox

### Requirement: Explicit unsafe workspace override
`ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` SHALL be the only value that permits a refused workspace. When it is used, the wrapper SHALL print a stderr warning naming the exposed path before continuing. Any other value SHALL leave the refusal in force. The override SHALL NOT relax any other mount, state or engine check.

#### Scenario: Exact override
- **WHEN** the caller sets `ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` and launches from a refused directory
- **THEN** the wrapper warns that the sensitive directory is explicitly exposed read/write and continues startup

#### Scenario: Non-exact override
- **WHEN** the variable is set to `true`, `yes` or any value other than `1`
- **THEN** the refusal remains in force

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
- **WHEN** a nonempty `ANTIGRAVITY_CONTAINER_STATE_DIR` overlaps the workspace or worktree parent
- **THEN** the wrapper exits with status 1 naming the variable before any engine query
- **AND** the shared configuration directory is not checked for overlap

### Requirement: Read-only state
`ANTIGRAVITY_CONTAINER_READONLY_STATE`, a boolean (`1`, `true`, `yes`; empty, `0`, `false`, `no`), SHALL mount the configuration directory read-only below the ephemeral home, taken from shared state or from the isolated home. That directory SHALL already exist and be accessible to the caller; the launcher SHALL NOT create it, check its owner or privacy, or pass it to restricted preparation as writable. The isolated home itself SHALL NOT be mounted.

#### Scenario: Read-only shared state
- **WHEN** `ANTIGRAVITY_CONTAINER_READONLY_STATE=1` is set and `~/.gemini` exists
- **THEN** the session sees it read-only and writes there fail

#### Scenario: Missing state
- **WHEN** read-only state is selected and the configuration directory does not exist
- **THEN** the launch stops before the engine and names the missing directory
