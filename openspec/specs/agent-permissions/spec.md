# agent-permissions Specification

## Purpose

Allow users to explicitly select agent approvals and Podman access while keeping these permissions distinct from mount boundaries.

## Requirements

### Requirement: Independent opt in permissions
The wrapper SHALL interpret `ANTIGRAVITY_YOLO` and `ANTIGRAVITY_CONTAINER_PODMAN` as independent booleans, disabled when empty or absent. It SHALL accept `1/true/yes` and `0/false/no` case-insensitively and reject other values before building or launching.

#### Scenario: Invalid input
- **WHEN** either variable contains `maybe`
- **THEN** the wrapper exits with an error identifying the variable without building or launching containers

#### Scenario: Four permission combinations
- **WHEN** all combinations of the two booleans are tested
- **THEN** the YOLO flag depends only on `ANTIGRAVITY_YOLO` and the socket only on `ANTIGRAVITY_CONTAINER_PODMAN`

### Requirement: Official YOLO mechanism
When `ANTIGRAVITY_YOLO` is enabled, the wrapper SHALL add `--dangerously-skip-permissions` to `agy` without changing persistent settings. When disabled, it SHALL leave native arguments and settings intact without promising to neutralize permissions supplied directly by the user.

#### Scenario: YOLO session
- **WHEN** `agy` is launched with YOLO enabled
- **THEN** it receives the official flag without gaining additional mounts, Podman privileges, or host access

#### Scenario: Native permissions explicitly supplied
- **WHEN** YOLO is disabled but the user directly passes a CLI permission flag
- **THEN** the wrapper forwards it unchanged and documents that the variable does not enforce a policy

### Requirement: Optional host Podman service
When Podman access is enabled, the wrapper SHALL connect the client to the local rootless socket selected by `ANTIGRAVITY_CONTAINER_PODMAN_SOCKET`, defaulting to `${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock`, without a nested daemon or privileged mode.

#### Scenario: Service disabled
- **WHEN** Podman access is disabled and the host socket does not exist
- **THEN** the container starts without a socket mount or service connection variables

#### Scenario: Service enabled and unavailable
- **WHEN** Podman access is enabled and the path is not an accessible socket
- **THEN** the wrapper fails before building or launching with guidance on activating the rootless service

#### Scenario: Child container uses project
- **WHEN** Podman access is enabled and the agent launches a child container with a workspace bind mount
- **THEN** the host service resolves the absolute path correctly and the child sees the project files

### Requirement: Honest isolation contract
Documentation SHALL explain that the socket grants control over the Podman user's resources and allows new host mounts beyond the workspace. It SHALL distinguish YOLO, Google's internal sandbox, and container isolation and SHALL NOT automatically add `--privileged` or globally disable security controls.

#### Scenario: User reviews configuration
- **WHEN** the user reads help and the README before enabling the socket
- **THEN** they find the expansion beyond the filesystem boundary, defaults, and an example for each of the four combinations
