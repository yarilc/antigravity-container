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
The wrapper SHALL reject named remote connections, TCP/SSH launch transports, and Unix launch endpoints without a nonempty absolute socket path before querying the launch engine. Paths consisting only of slashes SHALL be rejected, including `unix:///` and `unix:////`. Delegation settings SHALL NOT retarget the launch engine.

#### Scenario: Empty Unix endpoint
- **WHEN** `CONTAINER_HOST` is `unix:///`
- **THEN** startup fails without querying Podman or performing image operations

#### Scenario: Unsupported connection
- **WHEN** a named connection, TCP/SSH endpoint, or relative Unix endpoint is selected
- **THEN** startup fails before querying the launch engine

#### Scenario: Slash-only Unix endpoints
- **WHEN** `CONTAINER_HOST` is `unix:////`, `unix://////`, or another Unix endpoint with no non-slash path component
- **THEN** startup fails before any Podman query or image operation

#### Scenario: Valid absolute socket path
- **WHEN** the launch endpoint names an absolute Unix socket path with a non-slash component
- **THEN** endpoint validation allows the existing engine verification to proceed

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

### Requirement: Bounded owned session shutdown
In CLI and shell modes, the wrapper SHALL forward the first handled TERM/INT/HUP to the owned attached session, allow up to five seconds for graceful exit after successful forwarding, and then attempt forced owned-container removal. Shutdown control calls and client termination/reaping SHALL use finite deadlines. Repeated signals SHALL NOT restart shutdown or replace the first signal status.

#### Scenario: Cooperative interruption
- **WHEN** an attached session receives TERM, INT, or HUP through the wrapper and exits cooperatively
- **THEN** the wrapper forwards that signal once, cleans up its owned container, and exits with status 143, 130, or 129 respectively

#### Scenario: Application ignores TERM
- **WHEN** the application ignores forwarded TERM
- **THEN** the wrapper stops its graceful wait after five seconds, attempts forced removal, terminates its client within finite deadlines, and returns 143

#### Scenario: Stalled control call or client
- **WHEN** signal forwarding, forced removal, or client termination stalls
- **THEN** shutdown advances after the relevant finite deadline rather than waiting indefinitely
- **AND** a second handled signal does not extend the deadlines or change the primary status

### Requirement: Ownership through interrupted creation
The wrapper SHALL retain verifiable ownership evidence independently of create-client stdout. On interruption during creation, it SHALL resolve or terminate the pending client within finite deadlines, SHALL NOT attach the interrupted session, and SHALL attempt removal only for a verified owned container. An unresolved creation outcome SHALL produce a diagnostic without deleting containers by guessed name.

#### Scenario: Creation succeeds after interruption
- **WHEN** a handled signal arrives during creation and creation subsequently supplies a valid owned container ID
- **THEN** the wrapper does not start the session, attempts removal using that ID, and returns the first signal's exit status

#### Scenario: Creation stalls after interruption
- **WHEN** creation remains stalled after a handled signal
- **THEN** the wrapper bounds its wait and client termination, handles any recoverable owned ID, and reports an uncertain outcome if ownership cannot be established

#### Scenario: Collision with unrelated container
- **WHEN** creation encounters a preexisting same-name container and supplies no owned ID
- **THEN** the wrapper does not remove that container during retries, interruption, or cleanup

### Requirement: Cleanup diagnostics preserve primary status
The wrapper SHALL report failed or timed-out signal forwarding, owned-container removal, and unresolved cleanup outcomes without replacing the primary application or interruption exit status. A process exit of 125 SHALL remain an application result rather than triggering create-time collision handling. Temporary diagnostics and ownership bookkeeping SHALL be removed on handled exits.

#### Scenario: Removal fails after normal exit
- **WHEN** the application exits with 0, 23, or 125 and owned removal fails or times out
- **THEN** the wrapper reports the owned ID and need for manual cleanup while returning the application status

#### Scenario: Forwarding fails on interruption
- **WHEN** forwarding the first handled signal fails
- **THEN** the wrapper reports the failure, still attempts bounded owned removal, and preserves that signal's exit status

### Requirement: Shutdown prerequisite and user guidance
The wrapper SHALL check for coreutils `timeout` before session creation and document shutdown deadlines, signal statuses, owned-only cleanup, and manual recovery when the engine is unavailable. Wrapper help SHALL remain available without Podman, timeout, or state creation.

#### Scenario: Timeout unavailable
- **WHEN** a session would start but coreutils `timeout` is unavailable
- **THEN** the wrapper fails before container creation with an actionable prerequisite diagnostic

#### Scenario: Help without lifecycle tools
- **WHEN** wrapper help is requested without Podman or timeout
- **THEN** help succeeds without state or engine side effects and describes shutdown behavior
