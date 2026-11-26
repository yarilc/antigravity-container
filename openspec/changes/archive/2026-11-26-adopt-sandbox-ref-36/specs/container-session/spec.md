# Spec Delta

## ADDED Requirements

### Requirement: Preserve Podman verification response boundaries

The wrapper SHALL validate complete successful Podman verification responses, allowing zero or one final LF terminator. After removing at most one terminator, the launch response SHALL have exactly one record. Additional blank or nonblank records and CR characters SHALL be rejected before image operations or startup. Failed queries SHALL remain failures even when their output looks valid.

#### Scenario: Normal response termination

- **WHEN** a successful launch response contains one valid record, with no final LF or exactly one final LF
- **THEN** record-boundary validation accepts the response and the existing field checks still apply

#### Scenario: Extra blank records

- **WHEN** the verification response contains leading, interior, or additional trailing blank records beyond its required format
- **THEN** startup fails before image inspection, building, or session creation
- **AND** trailing newlines are not silently discarded to make the response valid

#### Scenario: Extra nonblank records or CR

- **WHEN** a response includes an additional nonblank record or a CR character
- **THEN** the wrapper rejects it as an invalid verification response

#### Scenario: Failed query with valid-looking output

- **WHEN** a verification query exits nonzero after writing otherwise valid records
- **THEN** startup fails and no image operation or session creation occurs

### Requirement: Document verification input boundaries

Help and README SHALL explain that Unix launch endpoints require an absolute socket path beyond the root directory and that malformed or additional Podman verification records stop startup. Runtime guidance SHALL document the one-record launch format and its optional final LF.

#### Scenario: Diagnose rejected verification

- **WHEN** a user reads the connection and verification guidance
- **THEN** they find the endpoint constraint, the record format, normal terminator policy, and rejection of additional records

### Requirement: Leftover delegation opt-in is refused

An exact `ANTIGRAVITY_CONTAINER_PODMAN=1` in the launch environment SHALL stop every session launch and build-only operation, in every network mode, before any engine query or image operation. After network-mode and setup admission, the diagnostic SHALL state that host Podman delegation was removed. It SHALL direct the operator to add needed images as toolchains and to unset the variable. Other values of the variable, and the former socket override, SHALL be ignored.

#### Scenario: Unrestricted launch with the old opt-in

- **WHEN** an operator starts an unrestricted session with `ANTIGRAVITY_CONTAINER_PODMAN=1`
- **THEN** the wrapper exits nonzero before querying an engine, names the variable, and points to image toolchains and the README section on container tests

#### Scenario: Configured restricted launch

- **WHEN** an offline or provider launch supplies the required configuration and sets `ANTIGRAVITY_CONTAINER_PODMAN=1`
- **THEN** the migration diagnostic appears before any engine query or state creation

#### Scenario: Restricted setup required

- **WHEN** a restricted launch sets the old opt-in and lacks its protected installation
- **THEN** setup guidance appears before any engine query or state creation

#### Scenario: Other values

- **WHEN** `ANTIGRAVITY_CONTAINER_PODMAN` is empty or `0`, or `ANTIGRAVITY_CONTAINER_PODMAN_SOCKET` is set
- **THEN** the launch proceeds as if the variables were unset, and no Podman socket is mounted

#### Scenario: Help and toolchain commands

- **WHEN** `--container-help` or `--container-toolchain list` runs with `ANTIGRAVITY_CONTAINER_PODMAN=1`
- **THEN** the command succeeds unchanged

### Requirement: Case-insensitive YOLO environment values

The wrapper SHALL parse `ANTIGRAVITY_YOLO` case-insensitively. Values `1`, `true`, and `yes` SHALL enable wrapper-added YOLO. Unset, empty, `0`, `false`, and `no` SHALL disable it. Other values SHALL fail before image operations or startup. Shell mode SHALL validate the value without adding agy arguments. Help and README SHALL document the accepted values, their effect on agy and the separate session isolation boundary.

#### Scenario: Mixed-case enabled values

- **WHEN** an agy invocation sets `ANTIGRAVITY_YOLO` to `TrUe`, `YeS`, or another capitalization of an enabled word
- **THEN** the wrapper adds `--dangerously-skip-permissions` before the unchanged user arguments, retaining their order and boundaries

#### Scenario: Mixed-case disabled values

- **WHEN** `ANTIGRAVITY_YOLO` is unset, empty, `0`, or any capitalization of `false` or `no`
- **THEN** the wrapper does not add `--dangerously-skip-permissions`
- **AND** explicit native arguments and saved settings retain their existing behavior

#### Scenario: Invalid values

- **WHEN** `ANTIGRAVITY_YOLO` is an unsupported value such as `enabled`, `2`, or a boolean word surrounded by spaces
- **THEN** the wrapper fails with accepted-value guidance before image inspection, building, or session creation

#### Scenario: Shell-mode compatibility

- **WHEN** shell mode receives any valid case-insensitive YOLO value
- **THEN** Bash starts without wrapper-added agy arguments
- **AND** invalid values remain errors in shell mode

#### Scenario: Exact Podman opt-in remains independent

- **WHEN** a valid mixed-case YOLO value is combined with `ANTIGRAVITY_CONTAINER_PODMAN` equal to `1`, `TrUe`, or `YeS`
- **THEN** only exactly `1` stops the launch as a leftover delegation opt-in, independently of the YOLO value, and the other values are ignored
- **AND** YOLO normalization does not change workspace mounts or the read-only image filesystem

#### Scenario: Native permission arguments

- **WHEN** the caller supplies a native permission flag with wrapper-added YOLO disabled
- **THEN** agy receives that flag unchanged and persistent settings retain their existing behavior

## MODIFIED Requirements

### Requirement: Explicit network mode admission

Ordinary `agy` and shell launches SHALL use the effective `ANTIGRAVITY_CONTAINER_NETWORK`, explicit or from the managed launcher. An unset or empty mode SHALL select `provider`. A provider launch without its protected installation or provider settings SHALL exit with status 1 and a `setup required:` message. The message SHALL name `--container-setup` and the explicit-mode alternative. The refusal SHALL come before engine queries, state creation or image operations. It SHALL NOT prompt, run setup or start an application. Help, setup and `--container-qualify` keep their own checks.

#### Scenario: Existing invocation without a mode

- **WHEN** a user runs `antigravity-container.sh` with no `ANTIGRAVITY_CONTAINER_NETWORK` and no provider settings, interactively or with redirected input
- **THEN** it exits with status 1 and the setup-required message before any engine call, without application output, state or runtime resources
- **AND** the message names `bash <wrapper> --container-setup` and states that an operator can set `ANTIGRAVITY_CONTAINER_NETWORK` explicitly

#### Scenario: Empty mode with provider settings

- **WHEN** `ANTIGRAVITY_CONTAINER_NETWORK` is empty and the provider settings select a protected installation
- **THEN** the launch runs in provider mode

#### Scenario: Help without a mode

- **WHEN** `--container-help` runs with no mode
- **THEN** help succeeds without engine calls or state side effects

#### Scenario: Options and other settings do not imply setup

- **WHEN** an unconfigured launch uses shell, build, worktree or YOLO, `ANTIGRAVITY_CONTAINER_MAINTENANCE=1`, or state, image, endpoint or policy settings
- **THEN** it receives the same setup-required refusal
- **AND** files in the current directory never admit the launch

### Requirement: Read-only engine queries are bounded

Every read-only engine query (`info`, `version`, `ps`, image and container existence and inspection, the session container engine's readiness query) SHALL be bounded by a timeout. A response with a carriage return or extra records SHALL be refused. `create`, `start`, `build` and `pull` SHALL NOT be bounded.

#### Scenario: Stalled engine query

- **WHEN** a read-only engine query does not answer
- **THEN** the wrapper stops after the query timeout with the query's diagnostic and creates no container
