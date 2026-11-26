# container-session Specification

## Purpose

Admit Antigravity sessions only with an explicit network mode, and require a current local qualification bound to the host, engine, enforcement inputs and hardening settings before restricted launches.

## Requirements

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

### Requirement: Restricted launches require current local qualification
Before ordinary offline or provider execution, the wrapper SHALL validate a protected successful qualification report matching the current host, engine and enforcement inputs. The check SHALL use the mode the launcher resolved, including the provider default. Missing or mismatched evidence SHALL stop startup with requalification guidance. A report SHALL NOT replace per-launch engine, protected-path, guard, policy or readiness checks. Unrestricted launches and help SHALL NOT require it.

#### Scenario: Changed environment or artifacts
- **WHEN** boot, engine version, backend or endpoint, effective security policy, guard or code, launcher core or agent part, runtime or proxy image identity, hardening, gate revision or selected mode, profile or policy differs from the report
- **THEN** ordinary restricted startup fails before application execution and requests `--container-qualify`
- **AND** changing environment variables never suppresses that failure

#### Scenario: Default mode is qualified as provider
- **WHEN** `ANTIGRAVITY_CONTAINER_NETWORK` is unset and the provider settings are present
- **THEN** the launcher and every Python helper check the provider report

#### Scenario: Matching evidence
- **WHEN** a trusted complete report matches the effective restricted workflow and all per-launch checks pass
- **THEN** `agy` starts with its existing argument, stdin, terminal and exit-status semantics
- **AND** a locally qualified combination without release acceptance is visibly identified as not release-measured

#### Scenario: Explicit qualification operation
- **WHEN** the operator runs `--container-qualify` without a current report
- **THEN** only the protected gate fixtures run through normal confinement and resource preparation
- **AND** no supplied application command or writable fixture can execute through the report-check exception

### Requirement: Consistent restricted prerequisite decisions
Restricted startup and qualification SHALL use the same protected platform eligibility rules and diagnostic categories. Malformed or unavailable engine or platform evidence SHALL fail closed. The rules SHALL keep launch endpoint verification and SHALL NOT reject SELinux or AppArmor merely for being enabled.

#### Scenario: Qualification and startup receive the same evidence
- **WHEN** qualification and direct restricted startup inspect equivalent host and engine evidence
- **THEN** they agree on eligibility and identify the same failed prerequisite

### Requirement: Qualification binds agent hardening settings
The qualification identity of a restricted installation SHALL include:
- the agent capability and no-new-privileges settings;
- the selected memory, CPU and process budgets;
- the set of agent and proxy budgets actually enforced, as determined by the controllers the engine delegates;
- the mechanism enforcing each agent and proxy process budget: cgroup controller, process rlimit, or none;
- the session lifetime setting.

A launch whose effective settings differ from the qualified identity SHALL stop with requalification guidance.

#### Scenario: Budget changed after qualification
- **WHEN** an installation was qualified with default budgets and the operator launches with `ANTIGRAVITY_CONTAINER_PIDS_LIMIT=1024`
- **THEN** the qualification check reports mismatched evidence and `agy` does not start

#### Scenario: Matching settings
- **WHEN** the operator qualifies and launches with the same budgets and lifetime
- **THEN** the qualification check accepts the report

#### Scenario: Controller delegation changed after qualification
- **WHEN** an installation was qualified while `cpu` was not delegated and the engine later delegates `cpu`
- **THEN** the qualification check reports mismatched evidence and requires requalification

#### Scenario: Process budget mechanism changed after qualification
- **WHEN** an installation was qualified with the agent process budget on the process rlimit fallback and the engine later delegates `pids`
- **THEN** the qualification check reports mismatched evidence and requires requalification

### Requirement: Unenforced budgets are announced
Each launch SHALL print one notice per unenforced agent or proxy budget, naming the budget, its container and the reason: the missing cgroup controller, or a cgroup manager that applies no cgroup limits. A process budget enforced through the process rlimit fallback SHALL get one notice naming the budget, its container and the rlimit mechanism instead. Notices SHALL NOT ask for confirmation. When every budget is enforced by its cgroup controller, no notice SHALL be printed.

#### Scenario: CPU controller missing
- **WHEN** a session starts on an engine delegating only `memory` and `pids`
- **THEN** stderr shows a notice that the agent CPU budget is not enforced because the `cpu` controller is not delegated to the rootless engine
- **AND** the session starts without waiting for input

#### Scenario: All controllers delegated
- **WHEN** the engine delegates `cpu`, `memory` and `pids`
- **THEN** no budget notice is printed

#### Scenario: Engine with the cgroupfs manager
- **WHEN** a session starts on a rootless engine with the `cgroupfs` cgroup manager that reports `cpu`, `memory` and `pids`
- **THEN** stderr shows notices that the agent memory and CPU budgets are not enforced because the rootless engine uses the `cgroupfs` cgroup manager, which applies no cgroup limits
- **AND** the process budget notice names the process rlimit fallback, or the reason it was not applied

#### Scenario: Process budget on the rlimit fallback
- **WHEN** a session starts on an engine delegating `cpu` and `memory` but not `pids`, on a host that counts the process rlimit per container
- **THEN** stderr shows a notice that the agent process budget is enforced through the process rlimit because the `pids` controller is not delegated
- **AND** the notice states that the limit counts the session user's tasks, threads included
- **AND** no notice reports the agent process budget as unenforced

#### Scenario: Process rlimit fallback not applied
- **WHEN** a session starts without the `pids` controller on a host where per-container counting is not established
- **THEN** stderr shows a notice that the agent process budget is not enforced, naming the missing `pids` controller and why the rlimit fallback was not applied

### Requirement: Extra variables forwarded by name
`ANTIGRAVITY_CONTAINER_ENV_VARS` SHALL list host variable names, separated by whitespace, to forward into the session by name, never by value. An invalid name SHALL stop the launch before any engine or state operation. Unset or empty variables SHALL NOT be forwarded. Reserved names SHALL be skipped with one notice each.

#### Scenario: Listed variable reaches the session
- **WHEN** `ANTIGRAVITY_CONTAINER_ENV_VARS="GH_TOKEN"` is set and `GH_TOKEN` has a value
- **THEN** the session receives `GH_TOKEN` by name and the value is absent from engine arguments

#### Scenario: Names reserved by mode
- **WHEN** the list names a variable the launcher or agent part sets, a proxy or CA setting in a restricted mode, or `GEMINI_API_KEY` in a provider session using the `google-account` profile
- **THEN** that name is skipped with a notice and the session starts

#### Scenario: Invalid name
- **WHEN** the list contains a name such as `1BAD`
- **THEN** the launch stops before any engine query

### Requirement: Session environment is fixed by the launcher
Every `agy` and shell session SHALL receive `TERM`, `COLORTERM`, `LANG` and `LC_ALL` when the host sets them, and SHALL set `USER` to the caller's name and `EDITOR` and `VISUAL` to `nano`. Unrestricted sessions SHALL also forward the host proxy variables in both cases. Restricted sessions SHALL NOT forward proxy variables. No session SHALL receive a credential except as the network-egress credential rules allow.

#### Scenario: Unrestricted environment
- **WHEN** an unrestricted session starts with `TERM`, `LANG` and `HTTPS_PROXY` set on the host
- **THEN** the session receives `TERM`, `LANG` and `HTTPS_PROXY`, `USER` with the caller's name, and `EDITOR=nano`

#### Scenario: Restricted environment
- **WHEN** an offline or provider session starts with `HTTPS_PROXY` set on the host
- **THEN** the session receives `TERM` when set, `USER` and `EDITOR=nano`, but not the host `HTTPS_PROXY`

### Requirement: Shell mode passes its arguments
`--container-shell` SHALL start `/bin/bash` with the remaining arguments in every network mode. It SHALL never add `agy` arguments or the approval bypass.

#### Scenario: Shell command
- **WHEN** `--container-shell -c "echo ok"` runs in offline, provider or unrestricted mode
- **THEN** Bash runs `-c` and `echo ok` as two arguments and prints `ok`

### Requirement: Session name and init process
Each create attempt SHALL set `CONTAINER_NAME` to the reserved container name and run with stdin from `/dev/null`. Unrestricted sessions SHALL run with `--init`. A failed create whose name holds this session's own container SHALL never count as a collision: that container SHALL be removed, or reported as unresolved.

#### Scenario: Session name inside the container
- **WHEN** an unrestricted session starts as `<prefix>-3`
- **THEN** it runs with `--init` and `CONTAINER_NAME=<prefix>-3`

#### Scenario: Own container behind a failed create
- **WHEN** create fails without publishing an ID and the engine reports this session's ownership label for the name
- **THEN** the wrapper returns the create status without retrying and removes that container

### Requirement: Read-only engine queries are bounded

Every read-only engine query (`info`, `version`, `ps`, image and container existence and inspection, the session container engine's readiness query) SHALL be bounded by a timeout. A response with a carriage return or extra records SHALL be refused. `create`, `start`, `build` and `pull` SHALL NOT be bounded.

#### Scenario: Stalled engine query

- **WHEN** a read-only engine query does not answer
- **THEN** the wrapper stops after the query timeout with the query's diagnostic and creates no container

### Requirement: First-user setup guidance
README, wrapper help and setup guidance SHALL name `--container-setup` as the first step for new users. They SHALL explain the managed launcher and the explicit operator alternative. They SHALL state that provider is the default mode, and that offline sessions cannot reach any model provider.

#### Scenario: User follows first-run guidance
- **WHEN** a new user reads the help or the README
- **THEN** they find how to run setup and then use its managed launcher
- **AND** they learn that offline cannot reach any model provider and that no unrestricted fallback is automatic

#### Scenario: Operator chooses a mode explicitly
- **WHEN** an operator reads the guidance
- **THEN** it explains that `ANTIGRAVITY_CONTAINER_NETWORK` selects offline, provider or unrestricted, that builds need `ANTIGRAVITY_CONTAINER_MAINTENANCE=1`, and that selecting a mode does not prove restricted readiness

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
