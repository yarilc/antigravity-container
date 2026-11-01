# agent-permissions Specification

## Purpose

Allow users to explicitly select agent approvals and Podman access while keeping these permissions distinct from mount boundaries.

## Requirements

### Requirement: Independent opt in permissions
The wrapper SHALL enable delegation only for exact `ANTIGRAVITY_CONTAINER_PODMAN=1`; every other value, including unset or empty, SHALL disable it without error in CLI and shell modes. Independently, `ANTIGRAVITY_YOLO` SHALL accept `1/true/yes` and `0/false/no` case-insensitively, default to disabled, and reject other values before image operations.

#### Scenario: Invalid input
- **WHEN** `ANTIGRAVITY_YOLO` contains `maybe`
- **THEN** the wrapper exits with an error identifying the variable without building or launching containers

#### Scenario: Four permission combinations
- **WHEN** all combinations of the two booleans are tested
- **THEN** the YOLO flag depends only on `ANTIGRAVITY_YOLO` and the socket only on `ANTIGRAVITY_CONTAINER_PODMAN`

#### Scenario: Non-enabling delegation values
- **WHEN** `ANTIGRAVITY_CONTAINER_PODMAN` is unset, empty, or set to `0`, `true`, `yes`, `01`, `maybe`, or any string other than `1`
- **THEN** delegation is disabled without an error, regardless of CLI or shell mode and YOLO selection

### Requirement: Official YOLO mechanism
When `ANTIGRAVITY_YOLO` is enabled, the wrapper SHALL add `--dangerously-skip-permissions` to `agy` without changing persistent settings. When disabled, it SHALL leave native arguments and settings intact without promising to neutralize permissions supplied directly by the user.

#### Scenario: YOLO session
- **WHEN** `agy` is launched with YOLO enabled
- **THEN** it receives the official flag without gaining additional mounts, Podman privileges, or host access

#### Scenario: Native permissions explicitly supplied
- **WHEN** YOLO is disabled but the user directly passes a CLI permission flag
- **THEN** the wrapper forwards it unchanged and documents that the variable does not enforce a policy

### Requirement: Optional host Podman service
With delegation enabled, the wrapper SHALL select the first nonempty endpoint from `ANTIGRAVITY_CONTAINER_PODMAN_SOCKET`, an explicit Unix `CONTAINER_HOST`, and `${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock`. It SHALL require an absolute, readable, writable Unix socket before canonicalization and verify a rootless service. It SHALL mount the reported absolute host socket path without a nested daemon or privileged mode.

#### Scenario: Service disabled
- **WHEN** Podman access is disabled and the host socket does not exist
- **THEN** the container starts without a socket mount or service connection variables

#### Scenario: Service enabled and unavailable
- **WHEN** Podman access is enabled and the path is not an accessible socket
- **THEN** the wrapper fails before building or launching with guidance on activating the rootless service

#### Scenario: Child container uses project
- **WHEN** Podman access is enabled and the agent launches a child container with a workspace bind mount
- **THEN** the host service resolves the absolute path correctly and the child sees the project files

#### Scenario: Relative override
- **WHEN** delegation is enabled with a relative socket override, even one resolving to an accessible socket
- **THEN** startup fails before querying the selected service or performing image operations

#### Scenario: Socket precedence and remapping
- **WHEN** delegation is enabled and the selected accessible socket is remapped inside an outer container
- **THEN** the wrapper queries its canonical accessible path and uses the service-reported absolute host socket path as the bind source
- **AND** selecting a delegation override does not change the launch engine

### Requirement: Honest isolation contract
Documentation SHALL explain that the socket grants control over the Podman user's resources and allows new host mounts beyond the workspace. It SHALL distinguish YOLO, Google's internal sandbox, and container isolation and SHALL NOT automatically add `--privileged` or globally disable security controls.

#### Scenario: User reviews configuration
- **WHEN** the user reads help and the README before enabling the socket
- **THEN** they find the expansion beyond the filesystem boundary, defaults, and an example for each of the four combinations

### Requirement: Complete delegation service validation
The wrapper SHALL require one complete delegation response containing verified rootless `true` and a nonempty absolute reported host socket path. It SHALL reject missing values, invalid rootless values, extra response records, and failed service queries before image inspection, build, or container creation. Paths containing spaces SHALL remain intact.

#### Scenario: Invalid delegation response
- **WHEN** the selected service query fails or returns empty, incomplete, rootful, malformed, relative-path, or multiline output
- **THEN** startup fails before image operations or container creation with a relevant diagnostic

#### Scenario: Host socket path contains spaces
- **WHEN** the service reports a valid absolute socket path containing spaces in a single response record
- **THEN** the bind source preserves that path intact

### Requirement: Disabled delegation clears service environment
When delegation is disabled, the wrapper SHALL omit the socket mount, skip delegation socket validation, and explicitly remove `CONTAINER_HOST` from the launched container environment, including image or engine defaults. It SHALL preserve the wrapper's launch-engine connection and the host Podman prerequisite.

#### Scenario: Disabled with invalid override
- **WHEN** delegation is disabled and its socket override is invalid or inaccessible
- **THEN** the override does not block startup or trigger a delegation query

#### Scenario: Image or engine supplies connection defaults
- **WHEN** delegation is disabled but image or engine defaults supply `CONTAINER_HOST`
- **THEN** the container starts with `CONTAINER_HOST` absent and no delegated socket

#### Scenario: Wrapper uses a Unix launch service
- **WHEN** the wrapper itself uses a supported local Unix `CONTAINER_HOST` and delegation is disabled
- **THEN** outer image and container operations retain that launch connection while `CONTAINER_HOST` is absent inside the container

### Requirement: Exact opt in migration documentation
Wrapper help and the README SHALL document exact `ANTIGRAVITY_CONTAINER_PODMAN=1`, disabled semantics for every other value, independent YOLO semantics, and migration from previously enabling `true` or `yes` values.

#### Scenario: Existing boolean configuration migrates
- **WHEN** a user reviews help and the README after previously enabling delegation with `true` or `yes`
- **THEN** the documentation explains that these values now disable delegation and shows `ANTIGRAVITY_CONTAINER_PODMAN=1` to restore it
