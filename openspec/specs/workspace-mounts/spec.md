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
The wrapper SHALL mount a dedicated application home from `ANTIGRAVITY_CONTAINER_STATE_DIR`, defaulting to `${HOME}/.local/share/antigravity-container/home`, at `/antigravity-home`. It SHALL preserve settings, sessions, caches, and the application keyring across runs, creating state with user-only permissions.

#### Scenario: State reused
- **WHEN** a second session starts with the same state directory
- **THEN** it finds previous settings and sessions without mounting the host home or generic host `~/.gemini`

### Requirement: Read only system and temporary storage
The container SHALL use a read-only root filesystem, writable state and workspace, and ephemeral temporary directories required by the runtime. It SHALL expose only these mounts and the Podman socket when explicitly enabled.

#### Scenario: System write attempt
- **WHEN** a process attempts to modify `/usr` and then writes a temporary file
- **THEN** the first operation fails, the second succeeds, and the temporary file does not persist after container removal
