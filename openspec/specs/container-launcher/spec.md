# container-launcher Specification

## Purpose

Allow users to run Antigravity CLI through a local wrapper with a predictable lifecycle for the rootless Podman container.

## Requirements

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

### Requirement: Complete launch engine validation
The wrapper SHALL require a single launch-engine response record with exactly three fields: rootless `true`, OS `linux`, and ServiceIsRemote `true` or `false`. It SHALL reject malformed responses before image inspection, build, or container creation and require an explicit local Unix endpoint for a remote service.

#### Scenario: Malformed engine response
- **WHEN** the response is empty, lacks fields, contains extra fields, reports an invalid boolean, or includes additional records
- **THEN** startup fails before image operations or container creation with a relevant diagnostic

#### Scenario: Missing remote flag
- **WHEN** the engine response is `true linux` or `true linux maybe`
- **THEN** startup fails before image operations

#### Scenario: Supported launch engines
- **WHEN** the engine reports `true linux false`, or reports `true linux true` with an explicit local Unix launch endpoint
- **THEN** engine verification succeeds and remaining preconditions are checked

#### Scenario: Unsupported launch engine
- **WHEN** the engine reports rootful operation, a non-Linux OS, or remote operation without an explicit local Unix launch endpoint
- **THEN** startup fails before image operations

### Requirement: Valid Unix launch endpoint
The wrapper SHALL reject named remote connections, TCP/SSH launch transports, and Unix launch endpoints without a nonempty absolute socket path before querying the launch engine. `unix:///` SHALL be rejected. Delegation settings SHALL NOT retarget the launch engine.

#### Scenario: Empty Unix endpoint
- **WHEN** `CONTAINER_HOST` is `unix:///`
- **THEN** startup fails without querying Podman or performing image operations

#### Scenario: Unsupported connection
- **WHEN** a named connection, TCP/SSH endpoint, or relative Unix endpoint is selected
- **THEN** startup fails before querying the launch engine

### Requirement: Private state preflight before image operations
The wrapper SHALL complete private state creation, physical path resolution, ownership, accessibility, and mode validation before image inspection or build, including explicit rebuilds. Invalid state SHALL prevent image operations. Wrapper help SHALL remain free of engine and state side effects.

#### Scenario: Invalid existing state
- **WHEN** state is inaccessible, belongs to another user, allows group/other access, or cannot be resolved
- **THEN** normal startup and `--container-build` both fail before image inspection or build

#### Scenario: State creation fails
- **WHEN** the selected state directory cannot be created
- **THEN** startup fails before image operations

#### Scenario: Later image failure
- **WHEN** state preflight succeeds but image inspection or build fails
- **THEN** the wrapper returns failure and the private state directory may already exist

### Requirement: Temporary launch diagnostic cleanup
The wrapper SHALL remove its temporary create-error diagnostic file on every exit path where EXIT cleanup can run, including handled interruptions and unexpected failures. It SHALL preserve relevant create diagnostics and exit status and SHALL NOT remove unrelated containers.

#### Scenario: Create failure or exhausted retries
- **WHEN** container creation fails without a naming collision or exhausts naming retries
- **THEN** the wrapper reports failure and leaves no temporary diagnostic file

#### Scenario: Interrupted or unexpected exit
- **WHEN** a handled signal or unexpected command failure terminates startup after diagnostic file creation
- **THEN** EXIT cleanup removes the diagnostic file without masking the failure status

#### Scenario: Successful session
- **WHEN** creation succeeds and the session later terminates
- **THEN** no diagnostic file remains and existing owned-container cleanup and exit-code behavior are preserved
