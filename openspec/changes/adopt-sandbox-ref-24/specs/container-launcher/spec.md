## MODIFIED Requirements

### Requirement: Transparent wrapper interface
`antigravity-container.sh` SHALL handle `--container-build`, `--container-shell`, `--container-git-worktree`, `--container-toolchain`, `--container-setup`, `--container-qualify`, the internal `--container-qualify-probe` and `--container-help`, forwarding every other argument to `agy` while preserving order, spaces, and empty values. Wrapper help SHALL come from the shared core with Antigravity's agent part and SHALL describe the network contract.

#### Scenario: Normal CLI arguments
- **WHEN** the wrapper receives `--help`, a prompt containing spaces, or empty arguments
- **THEN** it passes them to the CLI without reinterpreting them as container options or shell code

#### Scenario: Wrapper help without runtime
- **WHEN** `--container-help` is requested, even without Podman installed
- **THEN** the wrapper displays options and variables, exits successfully, and neither creates directories nor starts builds or containers

#### Scenario: Shell mode
- **WHEN** `--container-shell` is requested with further arguments
- **THEN** Bash opens with the same mounts, identity and network mode, receives those arguments, and neither starts `agy` nor applies the YOLO flag

#### Scenario: Help describes the network contract
- **WHEN** wrapper help is requested
- **THEN** it names `ANTIGRAVITY_CONTAINER_NETWORK` with its three values and the provider default, `ANTIGRAVITY_CONTAINER_MAINTENANCE`, the profile, policy, runtime-directory, egress-image, configuration-directory and CA variables, and `--container-qualify`
- **AND** it states the residual exfiltration limit of provider mode with the hosts of each base profile, and that the container has no keyring

### Requirement: Build and invocation preconditions
The wrapper SHALL use `ANTIGRAVITY_CONTAINER_IMAGE` with default `localhost/antigravity-cli:latest`. It SHALL build the image only when absent (image-existence status 1) or when `--container-build` is requested, and every build SHALL require the exact `ANTIGRAVITY_CONTAINER_MAINTENANCE=1`. `--container-build` without `agy` arguments SHALL validate every launch setting, build and exit without a session; with `agy` arguments it SHALL build and then start the session. A present image with a stale label SHALL be refused with the rebuild command. Other image-existence errors SHALL stop startup. It SHALL diagnose missing prerequisites before launch.

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

### Requirement: Private state preflight before image operations
The wrapper SHALL check the selected state lexically before engine queries, then complete private state creation, physical path resolution, ownership, accessibility, and mode validation after engine verification and before image inspection or build. The build-only operation SHALL check state lexically and skip state creation. Invalid state SHALL prevent image operations. Errors SHALL carry the wrapper prefix and name the path; no raw shell error SHALL replace them. Wrapper help SHALL remain free of engine and state side effects.

#### Scenario: Invalid existing state
- **WHEN** state is inaccessible, belongs to another user, allows group/other access, or cannot be resolved
- **THEN** normal startup fails before image inspection or build with `antigravity-container:` and the path

#### Scenario: State creation fails
- **WHEN** the selected state directory cannot be created
- **THEN** startup fails before image operations naming the directory

#### Scenario: Engine query fails
- **WHEN** a missing state directory is selected and the engine query fails
- **THEN** the wrapper exits without creating the directory

#### Scenario: Later image failure
- **WHEN** state preflight succeeds but image inspection or build fails
- **THEN** the wrapper returns failure and the private state directory may already exist

### Requirement: Bounded owned session shutdown
In CLI and shell modes, a handled TERM, INT or HUP SHALL start shutdown at once, also while the container is being created. The wrapper SHALL forward the signal to the owned attached session, allow up to five seconds for graceful exit, and then attempt forced owned-container removal. Shutdown SHALL complete within one 20-second deadline; each shutdown engine call SHALL be bounded by the time left, and local clients SHALL be terminated and reaped within it. Repeated signals SHALL NOT restart shutdown or replace the first signal status.

#### Scenario: Cooperative interruption
- **WHEN** an attached session receives TERM, INT, or HUP through the wrapper and exits cooperatively
- **THEN** the wrapper forwards that signal once, cleans up its owned container, and exits with status 143, 130, or 129 respectively

#### Scenario: Application ignores TERM
- **WHEN** the application ignores forwarded TERM
- **THEN** the wrapper stops its graceful wait after five seconds, attempts forced removal, terminates its client within the deadline, and returns 143

#### Scenario: Stalled control call or client
- **WHEN** signal forwarding, forced removal, or client termination stalls
- **THEN** shutdown ends within the 20-second deadline rather than waiting indefinitely
- **AND** a second handled signal does not extend the deadline or change the primary status

### Requirement: Ownership through interrupted creation
The wrapper SHALL retain verifiable ownership evidence independently of create-client stdout, through a validated private CID record and a session ownership label. On interruption during creation, it SHALL terminate the pending client within the shutdown deadline, SHALL NOT attach the interrupted session, and SHALL attempt removal only for a verified owned container. An unresolved creation outcome SHALL produce a diagnostic without deleting containers by guessed name.

#### Scenario: Creation succeeds after interruption
- **WHEN** a handled signal arrives during creation and creation subsequently supplies a valid owned container ID
- **THEN** the wrapper does not start the session, attempts removal using that ID, and returns the first signal's exit status

#### Scenario: Creation stalls after interruption
- **WHEN** creation remains stalled after a handled signal
- **THEN** the wrapper bounds its wait and client termination, handles any recoverable owned ID, and reports an uncertain outcome if ownership cannot be established

#### Scenario: Collision with unrelated container
- **WHEN** creation encounters a preexisting same-name container and supplies no owned ID
- **THEN** the wrapper does not remove that container during retries, interruption, or cleanup

### Requirement: Restricted forwarding and secret controls
Secret values SHALL NOT appear in wrapper-generated argv or diagnostics. Offline and provider modes SHALL forward no host proxy or CA variable and only the selected policy profile's credential. Unrestricted mode SHALL forward the host proxy variables but no credential unless `ANTIGRAVITY_CONTAINER_ENV_VARS` lists it.

#### Scenario: Restricted forwarding
- **WHEN** offline or provider mode runs with `HTTPS_PROXY`, `no_proxy`, `SSL_CERT_FILE` and `GEMINI_API_KEY` set on the host
- **THEN** none of the host proxy or CA values reaches the session, offline forwards no key, and provider forwards `GEMINI_API_KEY` only with `gemini-api`

#### Scenario: Unrestricted forwarding
- **WHEN** unrestricted mode runs with `HTTPS_PROXY` and `GEMINI_API_KEY` set on the host
- **THEN** the session receives `HTTPS_PROXY`, and receives `GEMINI_API_KEY` only when `ANTIGRAVITY_CONTAINER_ENV_VARS` names it

#### Scenario: Secret values stay out of argv
- **WHEN** a session forwards a dummy `GEMINI_API_KEY`
- **THEN** recorded engine arguments contain the variable name without its value
