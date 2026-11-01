# workspace-mounts Specification

## Purpose

Define which host data is exposed to Antigravity and preserve paths compatible with Git worktrees and containers launched through the host Podman service.

## Requirements

### Requirement: Default workspace boundary
By default, the wrapper SHALL mount only the physical current directory as the read/write workspace at the same absolute path and retain it as the working directory. It SHALL avoid implicit mounts of the host home, its services, or generic credentials.

#### Scenario: Ordinary project
- **WHEN** the wrapper starts from `/projects/app` without the worktree option and without socket access enabled
- **THEN** `/projects/app` is accessible and writable, while a host sentinel file in `/projects/other` is inaccessible

#### Scenario: Symbolic cwd
- **WHEN** the current directory is reached through a symbolic link
- **THEN** the mount and working directory use the resolved physical path

### Requirement: Explicit parent directory for worktrees
With `--container-git-worktree`, the wrapper SHALL mount the immediate parent of the physical current directory at the same absolute path and retain the original working directory. It SHALL document that the entire parent, including siblings, is writable and that it does not automatically search for a Git root.

#### Scenario: Shared metadata in parent
- **WHEN** the wrapper starts from `/projects/repo/main` with shared Git metadata under `/projects/repo` and the worktree flag
- **THEN** it mounts `/projects/repo`, works in `/projects/repo/main`, and Git can access shared metadata and create sibling worktrees

#### Scenario: Metadata outside selected parent
- **WHEN** a worktree points to metadata outside the selected parent
- **THEN** the wrapper adds no other mounts and documents the limitation instead of implicitly expanding access

### Requirement: Dedicated persistent state
The wrapper SHALL mount a dedicated application home from `ANTIGRAVITY_CONTAINER_STATE_DIR`, defaulting to `${HOME}/.local/share/antigravity-container/home`, at `/antigravity-home`. It SHALL preserve settings, sessions, caches, and the application keyring across runs, creating state with user-only permissions. Before image operations, resolved state SHALL belong to the caller, allow read/write/search access, and deny group/other access. Existing permissions SHALL NOT be recursively rewritten.

#### Scenario: State reused
- **WHEN** a second session starts with the same state directory
- **THEN** it finds previous settings and sessions without mounting the host home or generic host `~/.gemini`

#### Scenario: New state
- **WHEN** the selected state does not exist on a filesystem enforcing Unix permissions
- **THEN** it is created privately and validated before any image operation

#### Scenario: Insecure existing state
- **WHEN** the selected state allows group/other access or has incorrect ownership
- **THEN** startup fails before image operations with actionable guidance rather than silently changing existing permissions

### Requirement: Read only system and temporary storage
The container SHALL use a read-only root filesystem, writable state and workspace, and explicitly provisioned ephemeral tmpfs storage with automatic read-only tmpfs provisioning disabled. It SHALL expose only these mounts and the Podman socket when explicitly enabled.

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
- **WHEN** an account session starts with explicit temporary mounts
- **THEN** its keyring runtime directory under `/tmp` remains private with mode `0700` and its private bus and keyring remain usable

### Requirement: Scoped state creation permissions
The wrapper SHALL limit its private state-creation umask to state creation and preserve the inherited wrapper umask for subsequent operations. It SHALL NOT claim that this sets the container process umask. Account keyring runtime privacy SHALL remain enforced independently inside the container.

#### Scenario: Wrapper operations after state creation
- **WHEN** the wrapper starts with a known inherited umask and creates missing state
- **THEN** state is private while later engine operations observe the inherited wrapper umask

#### Scenario: Container file permissions
- **WHEN** runtime validation creates controlled files in shell, API-provider, and account execution paths
- **THEN** their actual modes are checked against the container process umask and file-creation behavior rather than inferred from the wrapper's state-creation umask
- **AND** the account helper retains its `077` umask and private runtime directory
