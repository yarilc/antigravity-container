# Spec Delta

## ADDED Requirements

### Requirement: Sessions receive no Podman socket

No Podman API socket SHALL be mounted into an agy or shell session, in any network mode and with any state, YOLO or worktree setting. A session's Podman command SHALL reach only the session's own container engine, and only when the session has one.

#### Scenario: Session without library images

- **WHEN** a session starts while the toolchain library holds no image
- **THEN** `/run/podman/podman.sock` is absent and `CONTAINER_HOST` and `DOCKER_HOST` are unset

#### Scenario: Session with library images

- **WHEN** a session starts while the toolchain library holds an image
- **THEN** `CONTAINER_HOST` names the session's engine at `tcp://127.0.0.1:2375`, and no host Podman socket is mounted
- **AND** a host path outside the session's mounts stays inaccessible, also through containers started by the engine

### Requirement: Sessions drop all capabilities and privilege gains

Every agy and shell container SHALL drop all Linux capabilities and enable container-level no-new-privileges, in every network mode, with or without a session container engine and independently of `ANTIGRAVITY_YOLO`, in account and Gemini API-key modes. The wrapper SHALL NOT add a capability back or disable no-new-privileges to resolve an incompatibility. Such a limitation SHALL be documented.

#### Scenario: agy or shell session starts

- **WHEN** an agy or shell session starts in any network mode, with or without a session container engine
- **THEN** its container has zero inheritable, permitted, effective, bounding and ambient capabilities and no-new-privileges set
- **AND** `agy --version`, Bash, Git and OpenSpec run with caller-owned persistence

#### Scenario: Account tokens work without capabilities

- **WHEN** an account-mode session starts, without a private D-Bus session or keyring
- **THEN** `agy` stores and reuses its account tokens in files in the private state, without capabilities and with no-new-privileges set
- **AND** if account sign-in cannot work, the wrapper adds no capability, bus or Unix-socket exception, and the limitation is recorded in the validation record

#### Scenario: Gemini API-key mode works without capabilities

- **WHEN** a session uses `modelProvider: gemini` without a terminal
- **THEN** agy starts and reports its native missing-key diagnostic without capabilities or privilege gains

#### Scenario: Session engine client works without capabilities

- **WHEN** a session runs Podman against its private engine
- **THEN** the client works with zero capabilities and no-new-privileges in the session container

## MODIFIED Requirements

### Requirement: Engine default secrets mount is masked

Every agy and shell container SHALL be created with an empty read-only tmpfs at `/run/secrets`, in every network mode and with or without a session container engine. An engine default mount there, such as RHEL subscription secrets from `mounts.conf`, SHALL then be neither visible nor writable. No host configuration change SHALL be required.

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
- **THEN** `/tmp` keeps its executable 512 MiB policy, `/var/tmp` its `noexec` 512 MiB policy, `/run` its `noexec` 32 MiB policy and the ephemeral home its executable 512 MiB tmpfs
- **AND** no writable `/var/log` tmpfs or writable `/dev/shm` is introduced by automatic provisioning

### Requirement: Process budget falls back to the process rlimit

When the verified engine does not delegate the `pids` controller and the engine host counts the process rlimit per container, the agent container's first process SHALL set its soft and hard process rlimit to the selected process budget before the container's program runs. The engine SHALL apply no process rlimit for the budget: one applied at creation counts every container of the user. Otherwise the process budget SHALL stay unenforced. Memory and CPU SHALL have no fallback.

#### Scenario: Process controller missing on a per-container host

- **WHEN** a session starts with the default budgets on an engine delegating `cpu` and `memory` but not `pids`, on a host that counts the process rlimit per container
- **THEN** the container's first process sets a soft and hard process rlimit of 512 before the application, or the guard in restricted modes, runs
- **AND** the container is created without a cgroup process limit and without a process rlimit requested from the engine
- **AND** the memory and CPU limits are applied as before

#### Scenario: Process controller delegated

- **WHEN** the engine delegates the `pids` controller
- **THEN** the process budget is enforced only by the cgroup process limit
- **AND** the wrapper sets no process rlimit

#### Scenario: Per-container counting not established

- **WHEN** the engine does not delegate `pids` and the host is not known to count the process rlimit per container
- **THEN** the wrapper requests neither a cgroup process limit nor a process rlimit for the container
- **AND** the session continues with a notice that names the unenforced process budget and why the fallback was not applied

#### Scenario: Memory controller missing

- **WHEN** the engine does not delegate the `memory` controller
- **THEN** the memory budget stays unenforced and no substitute memory limit is set

#### Scenario: The session cannot raise its process rlimit

- **WHEN** a process in a session on the fallback tries to raise its soft or hard process rlimit above the selected budget
- **THEN** the attempt fails, because the session has no capabilities and no-new-privileges is set

#### Scenario: Concurrent sessions have independent limits

- **WHEN** two sessions on the fallback run at the same time and the first holds processes up to its limit
- **THEN** the second session can still create processes up to its own limit

#### Scenario: Other containers do not consume the session's budget

- **WHEN** other containers of the same user, such as proxies, engines or their nested containers, together hold more processes than the session's budget
- **THEN** the session starts, and can create processes up to its own budget

#### Scenario: The limit cannot be set

- **WHEN** the container's first process cannot set the process rlimit to the selected budget
- **THEN** the container stops before the application or the guard runs, and the launch exits non-zero

### Requirement: Process rlimit fallback is verified

When the process budget uses the rlimit fallback, each launch SHALL require the created agent container to start with the step that sets the selected budget, and to carry no process rlimit requested by the wrapper. Setup smoke and restricted qualification SHALL measure the effective limit inside the agent container. A mismatch SHALL stop startup or setup with an actionable diagnostic, without a retry using weaker limits.

#### Scenario: Engine drops the process rlimit

- **WHEN** the created container does not start with the step that sets the selected budget, for example because the engine dropped or replaced its entry command, or the step sets another value, or the container carries a process rlimit requested by the wrapper
- **THEN** the wrapper removes only its own container and exits non-zero before the application starts
- **AND** the diagnostic names the process rlimit fallback

#### Scenario: Effective rlimit is measured

- **WHEN** setup smoke or the restricted qualification probe runs inside an agent container on the fallback
- **THEN** it reads the effective soft and hard process rlimit and requires both to equal the selected budget
- **AND** it requires the cgroup process interface to be absent or unlimited

## REMOVED Requirements

### Requirement: Every session drops capabilities and privilege gains

**Reason**: The delegated client scenario referred to retired host Podman access.

**Migration**: The replacement requirement preserves Antigravity's hardening and account and API scenarios, and exercises the client against the private session engine.
