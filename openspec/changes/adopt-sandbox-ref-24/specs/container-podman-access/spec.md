## MODIFIED Requirements

### Requirement: Optional host Podman service
With delegation enabled, the wrapper SHALL select the first nonempty endpoint from `ANTIGRAVITY_CONTAINER_PODMAN_SOCKET`, an explicit Unix `CONTAINER_HOST`, and `${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock`. It SHALL require an absolute, readable, writable Unix socket before canonicalization and verify a rootless service. It SHALL mount the reported absolute host socket path without a nested daemon or privileged mode. Delegated sessions SHALL get private tmpfs mounts at `/var/lib/containers` and `/run/containers`.

#### Scenario: Service disabled
- **WHEN** Podman access is disabled and the host socket does not exist
- **THEN** the container starts without a socket mount or service connection variables

#### Scenario: Service enabled and unavailable
- **WHEN** Podman access is enabled and the path is not an accessible socket
- **THEN** the wrapper fails before building or launching with guidance on activating the rootless service

#### Scenario: Child container uses project
- **WHEN** Podman access is enabled and the agent launches a child container with a workspace bind mount
- **THEN** the host service resolves the absolute path correctly and the child sees the project files

#### Scenario: Nested Podman storage
- **WHEN** a delegated session starts
- **THEN** `/var/lib/containers` and `/run/containers` are private tmpfs mounts, absent from sessions without delegation

#### Scenario: Relative override
- **WHEN** delegation is enabled with a relative socket override, even one resolving to an accessible socket
- **THEN** startup fails before querying the selected service or performing image operations

#### Scenario: Socket precedence and remapping
- **WHEN** delegation is enabled and the selected accessible socket is remapped inside an outer container
- **THEN** the wrapper queries its canonical accessible path and uses the service-reported absolute host socket path as the bind source
- **AND** selecting a delegation override does not change the launch engine
