# Spec Delta

## MODIFIED Requirements

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
