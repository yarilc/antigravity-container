# Spec Delta

## MODIFIED Requirements

### Requirement: Transparent wrapper interface
`antigravity-container.sh` SHALL handle `--container-build`, `--container-shell`, `--container-git-worktree`, `--container-qualify`, the internal `--container-qualify-probe` and `--container-help`, forwarding every other argument to `agy` while preserving order, spaces, and empty values. Wrapper help SHALL describe the network contract.

#### Scenario: Normal CLI arguments
- **WHEN** the wrapper receives `--help`, a prompt containing spaces, or empty arguments
- **THEN** it passes them to the CLI without reinterpreting them as container options or shell code

#### Scenario: Wrapper help without runtime
- **WHEN** `--container-help` is requested, even without Podman installed
- **THEN** the wrapper displays options and variables, exits successfully, and neither creates directories nor starts builds or containers

#### Scenario: Shell mode
- **WHEN** `--container-shell` is requested
- **THEN** Bash opens with the same mounts, identity and network mode without starting `agy` or applying the YOLO flag to the shell

#### Scenario: Help describes the network contract
- **WHEN** wrapper help is requested
- **THEN** it names `ANTIGRAVITY_CONTAINER_NETWORK` with its three values, `ANTIGRAVITY_CONTAINER_MAINTENANCE`, the profile, policy, runtime-directory, egress-image, configuration-directory and CA variables, and `--container-qualify`
- **AND** it states the residual exfiltration limit of provider mode and the removal of the keyring

### Requirement: Build and invocation preconditions
The wrapper SHALL use `ANTIGRAVITY_CONTAINER_IMAGE` with default `localhost/antigravity-cli:latest`. It SHALL build the image only when absent (image-existence status 1) or when `--container-build` forces a rebuild, and every build SHALL require the exact `ANTIGRAVITY_CONTAINER_MAINTENANCE=1`. Other image-existence errors SHALL stop startup. It SHALL diagnose missing prerequisites before launch.

#### Scenario: Image absent
- **WHEN** the selected image does not exist and maintenance is authorized
- **THEN** it is built from the Containerfile alongside the wrapper, even when the current directory is an external project

#### Scenario: Build without maintenance authorization
- **WHEN** the image is absent or `--container-build` is requested and `ANTIGRAVITY_CONTAINER_MAINTENANCE` differs from exactly `1`
- **THEN** the wrapper exits nonzero naming the variable, without building, pulling or creating a session

#### Scenario: Image inspection fails
- **WHEN** image existence returns an error other than 1
- **THEN** startup fails without attempting a build or session creation

#### Scenario: Runtime unavailable
- **WHEN** Podman is absent, uses an unsupported remote context, or is not rootless
- **THEN** the wrapper fails with relevant instructions without starting the container

### Requirement: Private state preflight before image operations
The wrapper SHALL check the selected state lexically before engine queries, then complete private state creation, physical path resolution, ownership, accessibility, and mode validation after engine verification and before image inspection or build, including explicit rebuilds. Invalid state SHALL prevent image operations. Wrapper help SHALL remain free of engine and state side effects.

#### Scenario: Invalid existing state
- **WHEN** state is inaccessible, belongs to another user, allows group/other access, or cannot be resolved
- **THEN** normal startup and `--container-build` both fail before image inspection or build

#### Scenario: State creation fails
- **WHEN** the selected state directory cannot be created
- **THEN** startup fails before image operations

#### Scenario: Engine query fails
- **WHEN** a missing state directory is selected and the engine query fails
- **THEN** the wrapper exits without creating the directory

#### Scenario: Later image failure
- **WHEN** state preflight succeeds but image inspection or build fails
- **THEN** the wrapper returns failure and the private state directory may already exist

## ADDED Requirements

### Requirement: Restricted forwarding and secret controls
Secret values SHALL NOT appear in wrapper-generated argv or diagnostics. Offline and provider modes SHALL forward no host proxy or CA variable and only the profile's credential. Unrestricted mode SHALL keep today's forwarding.

#### Scenario: Restricted forwarding
- **WHEN** offline or provider mode runs with `HTTPS_PROXY`, `no_proxy`, `SSL_CERT_FILE` and `GEMINI_API_KEY` set on the host
- **THEN** none of the host proxy or CA values reaches the session, offline forwards no key, and provider forwards `GEMINI_API_KEY` only with `gemini-api`

#### Scenario: Secret values stay out of argv
- **WHEN** a session forwards a dummy `GEMINI_API_KEY`
- **THEN** recorded engine arguments contain the variable name without its value
