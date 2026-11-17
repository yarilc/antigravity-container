## MODIFIED Requirements

### Requirement: Read-only session mount with live updates

Every session SHALL mount the library at `/toolchains` read-only with `nosuid` and `nodev`, unless `ANTIGRAVITY_CONTAINER_TOOLCHAINS` is `0`, `false` or `no`; an empty value selects the default and mounts the library. The launcher SHALL create the library privately when it is missing. A toolchain added or removed on the host SHALL become visible to running sessions without a restart. The mount SHALL add no network, IPC or socket access.

#### Scenario: Toolchain added during a session

- **WHEN** the operator adds a toolchain while a provider-mode session is running
- **THEN** the session can run its check command through `env.sh` without a restart, under the same network restrictions

#### Scenario: Library is read-only for the agent

- **WHEN** a process in the session tries to create, change or remove a file under `/toolchains`
- **THEN** the operation fails

#### Scenario: Mount disabled

- **WHEN** `ANTIGRAVITY_CONTAINER_TOOLCHAINS=0` is set
- **THEN** the session has no `/toolchains` mount and no toolchain environment

#### Scenario: Empty switch

- **WHEN** `ANTIGRAVITY_CONTAINER_TOOLCHAINS` is set to an empty value
- **THEN** the library is mounted as by default
