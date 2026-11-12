# Spec Delta

## MODIFIED Requirements

### Requirement: Saved budgets govern managed launches and verification
The managed launcher SHALL supply the saved budgets and lifetime through `ANTIGRAVITY_CONTAINER_MEMORY_LIMIT`, `ANTIGRAVITY_CONTAINER_CPU_LIMIT`, `ANTIGRAVITY_CONTAINER_PIDS_LIMIT` and `ANTIGRAVITY_CONTAINER_RUN_TIMEOUT` when these are absent from the launch environment. An explicitly present variable SHALL take precedence. Setup smoke and qualification SHALL use the saved values for every budget the engine can enforce.

#### Scenario: Managed launch uses saved budgets
- **WHEN** the user launches through the managed command with no budget variables exported
- **THEN** the agent container receives the saved budgets and lifetime
- **AND** a restricted launch matches the qualification report produced by setup

#### Scenario: Explicit override differs from qualified values
- **WHEN** the user exports `ANTIGRAVITY_CONTAINER_MEMORY_LIMIT=16g` for a restricted managed launch qualified with `4g`
- **THEN** the override is used and the qualification check stops the launch with requalification guidance

#### Scenario: Smoke verifies saved values
- **WHEN** setup runs its installed smoke check
- **THEN** the smoke compares the effective cgroup limits of every enforced budget with the saved budgets, not with ambient environment values
- **AND** it requires every unenforced budget to be absent

#### Scenario: Setup plan names unenforced budgets
- **WHEN** setup runs on an engine that does not report the `cpu` controller
- **THEN** the setup plan lists the CPU budget as not enforced, with the missing controller, and setup continues without an extra question

## ADDED Requirements

### Requirement: Host CA trust covers setup package fetches
When host CA trust is enabled, setup SHALL give the selected CA bundle to the runtime image and guard toolchain builds only as a non-persisted build secret, so their HTTPS package fetches verify on TLS-intercepting networks. Without host CA trust, setup SHALL pass no host CA to any build. The proxy build SHALL never receive it.

#### Scenario: Toolchain build on a TLS-intercepting network
- **WHEN** setup prepares the guard toolchain with host CA trust enabled and a bundle containing the interception CA
- **THEN** the toolchain package fetches verify against that bundle and the build completes
- **AND** the toolchain image contains neither the bundle nor its temporary copy

#### Scenario: Host CA trust disabled
- **WHEN** setup prepares images with host CA trust disabled
- **THEN** no build receives a host CA bundle, and the toolchain build verifies only against the base image's certificates
