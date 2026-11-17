# Spec Delta

## Purpose

Defines how Antigravity's launcher is built from the shared Bash core of the `sandbox-container` reference and Antigravity's own agent part, so launcher behavior is specified, fixed and tested once for all wrappers.

## ADDED Requirements

### Requirement: Launcher runs on the shared core
`antigravity-container.sh` SHALL be the thin entry script of the reference. It SHALL be identical to the reference's `sandbox-container.sh` after the wrapper name is replaced, and SHALL only source `launcher/core.sh` with `agent/launcher.sh` and its arguments. `launcher/core.sh` SHALL be a byte-identical copy from the adopted reference tag, recorded in the reference-copy manifest. Antigravity SHALL NOT keep launcher logic outside the core and its agent part.

#### Scenario: Core edited in this wrapper
- **WHEN** `launcher/core.sh` differs from the adopted reference tag
- **THEN** the reference-copy test fails naming the file

#### Scenario: Entry script compared with the reference
- **WHEN** `antigravity-container.sh` is compared with the reference entry script after replacing the wrapper name
- **THEN** they are identical

### Requirement: Antigravity agent launcher part
`agent/launcher.sh` SHALL hold Antigravity's profile data for the core, consistent with `agent/profile.json` and `agent/policies/default.json`, including a credential entry for each policy profile of the default policy. Antigravity's hooks SHALL be `agent_approval_bypass` and `agent_help`. Every other hook SHALL use the core default.

#### Scenario: Profile and launcher part disagree
- **WHEN** `agent/launcher.sh` and `agent/profile.json` or the default policy declare different values for the same property
- **THEN** the shared alignment test fails naming the property

#### Scenario: Credential entries
- **WHEN** the alignment test reads `AGENT_CREDENTIALS`
- **THEN** it lists `gemini-api=GEMINI_API_KEY` and `google-account=` with an empty credential

#### Scenario: Help documents the agent variables
- **WHEN** `--container-help` runs
- **THEN** it lists `ANTIGRAVITY_YOLO` with `--dangerously-skip-permissions` and `GEMINI_API_KEY` with its forwarding rule after the common variables, and states that the container has no D-Bus session or keyring

### Requirement: Antigravity session settings from the agent part
The agent part SHALL make the core run `/usr/local/bin/antigravity-entrypoint` as the restricted application, while unrestricted `agy` sessions use the image entrypoint. Every session SHALL receive `AGY_CLI_DISABLE_AUTO_UPDATE=true` after forwarded and toolchain variables and SHALL have `DBUS_SESSION_BUS_ADDRESS` removed. `ANTIGRAVITY_YOLO` SHALL add `--dangerously-skip-permissions` before the user's arguments, never in shell mode or the qualification probe. The profile SHALL declare executable temporary storage.

#### Scenario: Restricted application
- **WHEN** an offline or provider `agy` session starts with `ANTIGRAVITY_YOLO=1` and the user arguments `-p "a b"`
- **THEN** the guard runs `/usr/local/bin/antigravity-entrypoint --dangerously-skip-permissions -p "a b"` with `a b` as one argument

#### Scenario: Fixed settings win
- **WHEN** a toolchain or `ANTIGRAVITY_CONTAINER_ENV_VARS` supplies `AGY_CLI_DISABLE_AUTO_UPDATE=false` or `DBUS_SESSION_BUS_ADDRESS`
- **THEN** the session has `AGY_CLI_DISABLE_AUTO_UPDATE=true` and no `DBUS_SESSION_BUS_ADDRESS`
- **AND** the forwarding list skips both names with a notice

### Requirement: Antigravity launcher tests cover only Antigravity's part
Antigravity's launcher behavior SHALL be tested by the shared `tests/test_launcher.py` and `tests/fake_podman.py`, copied unchanged from the reference tag. `tests/test_wrapper.py` SHALL test only Antigravity's hooks, agent data, credential rules per policy profile and shipped policy inventories. An Antigravity launcher case that the shared tests do not cover SHALL be added to the reference first, not kept as a wrapper copy.

#### Scenario: Wrapper runtime tests
- **WHEN** `bash tests/run-runtime.sh --wrapper` runs
- **THEN** it runs both `tests/test_launcher.py` and `tests/test_wrapper.py` against this checkout

#### Scenario: Approval bypass combinations
- **WHEN** `tests/test_wrapper.py` runs every combination of `ANTIGRAVITY_YOLO` and `ANTIGRAVITY_CONTAINER_PODMAN=1` in unrestricted shared and isolated modes
- **THEN** only `ANTIGRAVITY_YOLO` determines the bypass flag, and only the Podman opt-in determines the delegation mounts and variables
