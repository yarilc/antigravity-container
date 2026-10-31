# Spec Delta

## Purpose

Allow users to run Antigravity CLI through a local wrapper with a predictable lifecycle for the rootless Podman container.

## ADDED Requirements

### Requirement: Transparent wrapper interface
`antigravity-container.sh` SHALL handle `--container-build`, `--container-shell`, `--container-git-worktree`, and `--container-help`, forwarding every other argument to `agy` while preserving order, spaces, and empty values.

#### Scenario: Normal CLI arguments
- **WHEN** the wrapper receives `--help`, a prompt containing spaces, or empty arguments
- **THEN** it passes them to the CLI without reinterpreting them as container options or shell code

#### Scenario: Wrapper help without runtime
- **WHEN** `--container-help` is requested, even without Podman installed
- **THEN** the wrapper displays options and variables, exits successfully, and neither creates directories nor starts builds or containers

#### Scenario: Shell mode
- **WHEN** `--container-shell` is requested
- **THEN** Bash opens with the same mounts and identity without starting `agy` or applying the YOLO flag to the shell

### Requirement: Rootless lifecycle and identity
The wrapper SHALL use rootless Podman with the caller's UID/GID, remove the container on termination, and use distinct workspace-based names. It SHALL preserve the exit code and allow process interruption.

#### Scenario: File ownership and termination
- **WHEN** the process creates a file in the project and exits with a nonzero code
- **THEN** the file belongs to the host user, the wrapper returns that code, and the container is removed

#### Scenario: Multiple sessions
- **WHEN** two sessions are started from the same workspace
- **THEN** they use distinct names without interrupting active sessions

### Requirement: Build and invocation preconditions
The wrapper SHALL use `ANTIGRAVITY_CONTAINER_IMAGE` with default `localhost/antigravity-cli:latest`, build the image if absent, and force a rebuild with `--container-build`. It SHALL diagnose missing prerequisites before launch.

#### Scenario: Image absent
- **WHEN** the selected image does not exist
- **THEN** it is built from the Containerfile alongside the wrapper, even when the current directory is an external project

#### Scenario: Runtime unavailable
- **WHEN** Podman is absent, uses an unsupported remote context, or is not rootless
- **THEN** the wrapper fails with relevant instructions without starting the container

### Requirement: Terminal independent operation
The wrapper SHALL support both TUI use on a terminal and non-interactive CLI use with redirected stdin without requiring a nonexistent TTY.

#### Scenario: Headless prompt
- **WHEN** the wrapper is invoked with `-p` from a pipeline without a terminal
- **THEN** stdin and arguments reach `agy` and Podman does not fail due to TTY allocation
