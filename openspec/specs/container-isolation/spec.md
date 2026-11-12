# container-isolation Specification

## Purpose

Drop privileges and bound the resources of every Antigravity session container, verify the configured limits before the application starts, and document these controls.

## Requirements

### Requirement: Every session drops capabilities and privilege gains
Every agy and shell container SHALL drop all Linux capabilities and enable container-level no-new-privileges, in every network mode, with or without Podman delegation and independently of `ANTIGRAVITY_YOLO`, in account and Gemini API-key modes. The wrapper SHALL NOT add a capability back or disable no-new-privileges to resolve an incompatibility; such a limitation SHALL be documented instead.

#### Scenario: agy or shell session starts
- **WHEN** an agy or shell session starts in any network mode, with either Podman access setting where allowed
- **THEN** its container has zero inheritable, permitted, effective, bounding and ambient capabilities and no-new-privileges set
- **AND** `agy --version`, Bash, Git and OpenSpec run with caller-owned persistence

#### Scenario: Account keyring works without capabilities
- **WHEN** an account-mode session starts, now without a private D-Bus session or keyring
- **THEN** `agy` stores and reuses its account tokens in files in the private state, without capabilities and with no-new-privileges set
- **AND** if account sign-in cannot work, the wrapper adds no capability, bus or Unix-socket exception, and the limitation is recorded in the validation record

#### Scenario: Gemini API-key mode works without capabilities
- **WHEN** a session uses `modelProvider: gemini` without a terminal
- **THEN** agy starts and reports its native missing-key diagnostic without capabilities or privilege gains

#### Scenario: Delegated Podman client works without capabilities
- **WHEN** an unrestricted session with exact `ANTIGRAVITY_CONTAINER_PODMAN=1` runs `podman info` and creates a child container through the mounted socket
- **THEN** the client succeeds without capabilities in the session container
- **AND** the documentation states that the socket still grants host engine authority beyond these limits

### Requirement: Sessions have explicit resource budgets
Every agy and shell container SHALL be created with a memory limit, a CPU limit and a process limit for each budget whose cgroup v2 controller (`memory`, `cpu`, `pids`) the verified rootless engine reports as available. The defaults SHALL be 4 GiB memory, 2 CPUs and 512 processes. `ANTIGRAVITY_CONTAINER_MEMORY_LIMIT`, `ANTIGRAVITY_CONTAINER_CPU_LIMIT` and `ANTIGRAVITY_CONTAINER_PIDS_LIMIT` SHALL override them. Only an unset variable SHALL select its default; no value SHALL disable a budget, and only a missing controller SHALL leave it unenforced.

#### Scenario: Accepted formats
- **WHEN** the operator sets a budget variable
- **THEN** memory accepts a positive integer with unit `k`, `m` or `g`, CPU accepts a positive decimal with at most three fractional digits up to 1024, and the process limit accepts an integer from 1 to 4194304

#### Scenario: Default budgets
- **WHEN** a session starts with none of the budget variables set on an engine reporting the `cpu`, `memory` and `pids` controllers
- **THEN** the container is created with 4 GiB memory, 2 CPUs and 512 processes

#### Scenario: Operator overrides budgets
- **WHEN** the operator sets `ANTIGRAVITY_CONTAINER_MEMORY_LIMIT=8g`, `ANTIGRAVITY_CONTAINER_CPU_LIMIT=1.5` and `ANTIGRAVITY_CONTAINER_PIDS_LIMIT=1024` on an engine reporting all three controllers
- **THEN** the container is created with exactly those limits

#### Scenario: Invalid or unbounded budget value
- **WHEN** a budget variable is set but empty or whitespace, zero, negative, `-1`, `max`, non-numeric, out of range, or has an unsupported unit
- **THEN** the wrapper exits with status 1 and names the variable before any engine query, state creation or image operation

#### Scenario: Controller not delegated
- **WHEN** the verified engine does not report the `cpu` controller
- **THEN** the container is created without a CPU limit, while the memory and process limits are still applied when their controllers are reported
- **AND** the session continues and prints a notice naming the unenforced CPU budget and the missing controller

#### Scenario: Process controller not delegated
- **WHEN** the verified engine does not report the `pids` controller
- **THEN** the container is created with an explicitly unlimited process setting, so no engine default requests the missing controller

### Requirement: Resource budgets are verified, not assumed
Before starting the application, each launch SHALL inspect the created container and require each enforced budget to equal its selected value and each unenforced budget to be absent. A mismatch or missing enforced limit SHALL stop startup with an actionable diagnostic, without a retry using weaker limits. Runtime verification SHALL measure the effective cgroup v2 limits inside the session in the same way.

#### Scenario: Engine ignores a budget
- **WHEN** the created container reports no limit or a different limit for a budget whose controller the engine reports as available
- **THEN** the wrapper removes only its own container and exits non-zero before the application starts
- **AND** the diagnostic names rootless cgroup v2 controller delegation and the controllers the engine reported

#### Scenario: Unenforced budget unexpectedly present
- **WHEN** the created container reports a limit for a budget whose controller the engine does not report
- **THEN** the wrapper removes only its own container and exits non-zero before the application starts

#### Scenario: Effective limits are measured
- **WHEN** the real-engine runtime checks run a session with default and overridden budgets on an engine reporting all three controllers
- **THEN** the container's cgroup v2 `memory.max`, `pids.max` and `cpu.max` match the selected budgets
- **AND** a process count beyond the process limit fails inside the session

### Requirement: Hardening controls are documented
Wrapper help and the README SHALL document the budget variables with defaults and accepted formats, the lifetime variable, the unsafe-workspace override with the refused directories, and that capabilities are dropped in every mode. They SHALL state that budgets and tmpfs sizes do not bound workspace or state storage growth. Help SHALL remain free of engine queries and state creation.

#### Scenario: Operator reads wrapper help
- **WHEN** the operator runs `--container-help`
- **THEN** the output lists `ANTIGRAVITY_CONTAINER_MEMORY_LIMIT`, `ANTIGRAVITY_CONTAINER_CPU_LIMIT`, `ANTIGRAVITY_CONTAINER_PIDS_LIMIT`, `ANTIGRAVITY_CONTAINER_RUN_TIMEOUT` and `ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE` with their defaults
- **AND** it states that capabilities are dropped and budgets do not limit persistent storage
- **AND** no engine query or state creation occurs

### Requirement: Engine default secrets mount is masked
Every agy and shell container SHALL be created with an empty read-only tmpfs at `/run/secrets`, in every network mode and with or without Podman access. An engine default mount there, such as RHEL subscription secrets from `mounts.conf`, SHALL then be neither visible nor writable. No host configuration change SHALL be required.

#### Scenario: Host with a default secrets mount
- **WHEN** the engine's `mounts.conf` maps `/usr/share/rhel/secrets` to `/run/secrets`
- **THEN** the session has exactly one mount at `/run/secrets`, an empty tmpfs mounted read-only
- **AND** no host subscription file is readable inside the session

#### Scenario: Host without a default secrets mount
- **WHEN** the engine adds no mount at `/run/secrets`
- **THEN** the session still has the empty read-only tmpfs there and behaves as before

### Requirement: Terminal-compatible device mounts
Every agy and shell container SHALL keep automatic read-only tmpfs provisioning enabled, so that the engine provides `/dev` with its standard device nodes and a `devpts` at `/dev/pts` that allows pseudo-terminals, and a terminal attaches where `--read-only-tmpfs=false` would make `/dev` read-only. The container SHALL mask `/dev/shm` with an empty read-only tmpfs. Automatic provisioning SHALL add no writable path beyond the explicit temporary mounts and the engine's `/dev`.

#### Scenario: Terminal attaches on an engine that mounts /dev read-only
- **WHEN** an interactive session starts with a terminal on Podman 5 with crun 1.27
- **THEN** the terminal attaches and `agy` starts without any host configuration change
- **AND** `/dev/pts` is present and `/dev/shm` is read-only and empty

#### Scenario: Pseudo-terminals are available to tools
- **WHEN** a process inside the session opens a pseudo-terminal, as agy does to run a tool command
- **THEN** the allocation succeeds through `/dev/ptmx`

#### Scenario: Temporary mounts keep their agy policy
- **WHEN** a session starts
- **THEN** `/tmp` keeps its executable 512 MiB policy, `/var/tmp` its `noexec` 512 MiB policy, `/run` its `noexec` 32 MiB policy and the shared-state home its 64 MiB tmpfs
- **AND** no writable `/var/log` tmpfs or writable `/dev/shm` is introduced by automatic provisioning
