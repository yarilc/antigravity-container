# Spec Delta

## MODIFIED Requirements

### Requirement: Build and invocation preconditions

The wrapper SHALL use `ANTIGRAVITY_CONTAINER_IMAGE` with default `localhost/antigravity-cli:latest`. It SHALL build the image only when absent (image-existence status 1) or when `--container-build` is requested, and every build SHALL require the exact `ANTIGRAVITY_CONTAINER_MAINTENANCE=1`. `--container-build` without `agy` arguments SHALL validate every launch setting, build and exit without a session. With `agy` arguments it SHALL build and then start the session. A present image with a stale label SHALL be refused with the rebuild command. Other image-existence errors SHALL stop startup. It SHALL diagnose missing prerequisites before launch.

#### Scenario: Image absent

- **WHEN** the selected image does not exist and maintenance is authorized
- **THEN** it is built from the Containerfile alongside the wrapper, even when the current directory is an external project, and labeled with the hash of its build inputs

#### Scenario: Build only

- **WHEN** `--container-build` runs under maintenance without `agy` arguments
- **THEN** the wrapper validates the launch settings, builds the image and exits without creating a session container

#### Scenario: Stale image

- **WHEN** the selected image exists but its `build-inputs-hash` label differs from the current build inputs
- **THEN** startup fails naming the rebuild command, without creating a session

#### Scenario: Build without maintenance authorization

- **WHEN** the image is absent or `--container-build` is requested and `ANTIGRAVITY_CONTAINER_MAINTENANCE` differs from exactly `1`
- **THEN** the wrapper exits nonzero naming the variable, without building, pulling or creating a session

#### Scenario: Image inspection fails

- **WHEN** image existence returns an error other than 1
- **THEN** startup fails without attempting a build or session creation

#### Scenario: Runtime unavailable

- **WHEN** Podman is absent, uses an unsupported remote context, or is not rootless
- **THEN** the wrapper fails with relevant instructions without starting the container

#### Scenario: Leftover delegation on a build-only invocation

- **WHEN** the operator sets ANTIGRAVITY_CONTAINER_PODMAN=1 and runs --container-build without agy arguments
- **THEN** the wrapper exits with migration guidance before any engine query or image operation

### Requirement: Valid Unix launch endpoint

The wrapper SHALL reject named remote connections, TCP/SSH launch transports, and Unix launch endpoints without a nonempty absolute socket path before querying the launch engine. Paths consisting only of slashes SHALL be rejected, including `unix:///` and `unix:////`. An explicit launch endpoint SHALL be for a service on the same host and SHALL be used for host-side operations only.

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

#### Scenario: Explicit endpoint used by a containerized launcher

- **WHEN** the wrapper runs inside a container with an explicit same-host launch socket and absolute host bind paths
- **THEN** the wrapper can launch the session using that service, and the launched session receives no Podman socket
