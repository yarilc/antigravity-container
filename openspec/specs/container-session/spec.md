# container-session Specification

## Purpose

Admit Antigravity sessions only with an explicit network mode, and require a current local qualification bound to the host, engine, enforcement inputs and hardening settings before restricted launches.

## Requirements

### Requirement: Explicit network mode admission
Ordinary `agy` and shell launches SHALL require a nonempty effective `ANTIGRAVITY_CONTAINER_NETWORK`, explicit or from the managed launcher. An unset or empty mode SHALL exit with status 1 and a `setup required:` message naming `--container-setup` and the explicit-mode alternative, before runtime prerequisite checks, engine queries, state creation or image operations. It SHALL NOT prompt, run setup or start an application; help, setup and `--container-qualify` keep their own checks.

#### Scenario: Existing invocation without a mode
- **WHEN** a user runs `antigravity-container.sh` with no `ANTIGRAVITY_CONTAINER_NETWORK`, interactively or with redirected input
- **THEN** it exits with status 1 and the setup-required message before any engine call, without application output, state or runtime resources
- **AND** the message names `bash <wrapper> --container-setup` and states that an operator can set `ANTIGRAVITY_CONTAINER_NETWORK` explicitly

#### Scenario: Help without a mode
- **WHEN** `--container-help` runs with no mode
- **THEN** help succeeds without engine calls or state side effects

#### Scenario: Options and other settings do not imply setup
- **WHEN** an unconfigured launch uses shell, build, worktree or YOLO, `ANTIGRAVITY_CONTAINER_MAINTENANCE=1`, or state, image, endpoint, policy or delegation settings
- **THEN** it receives the same setup-required refusal before validating those settings
- **AND** files in the current directory never admit the launch

### Requirement: Restricted launches require current local qualification
Before ordinary offline or provider execution, the wrapper SHALL validate a protected successful qualification report matching the current host, engine and enforcement inputs. Missing or mismatched evidence SHALL stop startup with requalification guidance. A report SHALL NOT replace per-launch engine, protected-path, guard, policy or readiness checks. Unrestricted launches and help SHALL NOT require it.

#### Scenario: Changed environment or artifacts
- **WHEN** boot, engine version, backend or endpoint, effective security policy, guard or code, runtime or proxy image identity, hardening, gate revision or selected mode, profile or policy differs from the report
- **THEN** ordinary restricted startup fails before application execution and requests `--container-qualify`
- **AND** changing environment variables never suppresses that failure

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
The qualification identity of a restricted installation SHALL include the agent capability and no-new-privileges settings, the selected memory, CPU and process budgets, and the session lifetime setting. A launch whose effective settings differ from the qualified identity SHALL stop with requalification guidance.

#### Scenario: Budget changed after qualification
- **WHEN** an installation was qualified with default budgets and the operator launches with `ANTIGRAVITY_CONTAINER_PIDS_LIMIT=1024`
- **THEN** the qualification check reports mismatched evidence and `agy` does not start

#### Scenario: Matching settings
- **WHEN** the operator qualifies and launches with the same budgets and lifetime
- **THEN** the qualification check accepts the report

### Requirement: First-user setup and migration guidance
README, wrapper help and setup guidance SHALL name `--container-setup` as the first step for new users, explain the managed launcher and the explicit operator alternative, state that offline sessions cannot reach any model provider, and give the migration path for direct invocations from versions without network modes.

#### Scenario: User follows first-run guidance
- **WHEN** a new user reads the help or the README
- **THEN** they find how to run setup and then use its managed launcher
- **AND** they learn that offline cannot reach any model provider and that no unrestricted fallback is automatic

#### Scenario: Operator migrates an existing direct invocation
- **WHEN** an operator reads the migration guidance
- **THEN** it explains that earlier versions needed no network mode, that `ANTIGRAVITY_CONTAINER_NETWORK=unrestricted` keeps the previous networking, and that builds need `ANTIGRAVITY_CONTAINER_MAINTENANCE=1`
- **AND** it does not imply that selecting a mode proves restricted readiness
