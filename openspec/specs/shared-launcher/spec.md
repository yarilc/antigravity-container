# shared-launcher Specification

## Purpose
Defines how Antigravity's launcher is built from the shared Bash core of the `sandbox-container` reference and Antigravity's own agent part, so launcher behavior is specified, fixed and tested once for all wrappers.

## Requirements

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

- **WHEN** tests/test_wrapper.py exercises enabled and disabled ANTIGRAVITY_YOLO in shared and isolated sessions
- **THEN** the agy bypass arguments follow ANTIGRAVITY_YOLO and the existing mount and hardening assertions continue to hold

#### Scenario: Retired host-service opt-in

- **WHEN** the shared launcher fixture checks the old Podman opt-in across network modes
- **THEN** the shared suite covers the early refusal and its migration diagnostic

### Requirement: Launcher files pass ShellCheck
`launcher/core.sh`, `launcher/windows/bootstrap.sh`, the launcher fixtures and every `agent/launcher.sh` SHALL each pass ShellCheck alone, at warning level. Each SHALL declare its shell with a `shell=bash` directive. A suppressed finding SHALL concern only data and state the core shares with the agent part, or an indirectly assigned variable, and SHALL carry a comment naming the reason. The reference SHALL provide a check with a pinned ShellCheck version that runs on any checkout.

#### Scenario: Shared files checked alone
- **WHEN** the reference check runs on a reference or wrapper checkout at warning level
- **THEN** it reports no finding for `launcher/core.sh`, `launcher/windows/bootstrap.sh`, `tests/fixtures/agent/launcher.sh`, `tests/fixtures/shell-agent/launcher.sh` or `agent/launcher.sh`

#### Scenario: New finding in the core
- **WHEN** a change to `launcher/core.sh` introduces a ShellCheck warning
- **THEN** the reference check fails naming the file and line

#### Scenario: Lint-only edits keep behavior
- **WHEN** the directives and quoting are added
- **THEN** the shared launcher tests pass unchanged

### Requirement: Shared Windows shim and bootstrap
The shared launcher SHALL include the Windows shim `launcher/windows/core.ps1`, the installer scripts under `launcher/windows/` and the bootstrap `launcher/windows/bootstrap.sh`, copied byte for byte from the reference tag like the other shared files. None SHALL contain agent identifiers: the shim and the installer SHALL read the wrapper name, file name and variable prefix from `agent/profile.json`. Setup SHALL install the bootstrap in every release.

#### Scenario: Shim edited in a wrapper
- **WHEN** a wrapper's `launcher/windows/core.ps1` differs from the reference tag
- **THEN** the reference-copy test fails naming the file

#### Scenario: Agent-neutral shim
- **WHEN** the alignment test scans the shim and the bootstrap
- **THEN** neither contains the reference's name, prefix or other profile identifiers

#### Scenario: Agent-neutral installer
- **WHEN** the alignment test scans the installer scripts
- **THEN** none contains the reference's name, prefix or other profile identifiers, and each is ASCII

### Requirement: Thin PowerShell entry script
Each wrapper SHALL provide `<wrapper>-container.ps1` next to its Bash entry. It SHALL only set strict error handling and run the shared shim with its own directory, its arguments and whether it received pipeline input. The PowerShell entries of all wrappers SHALL be identical. Because propagation copies only shared directories, the adoption steps SHALL name the entry and the repository's `.gitattributes`.

#### Scenario: Comparing two wrappers
- **WHEN** the PowerShell entries of two wrappers are compared
- **THEN** they are byte-identical and contain no agent identifier

#### Scenario: Adopting the Windows entry
- **WHEN** a wrapper adopts the reference tag that introduces the shim
- **THEN** the propagation guide tells the operator to copy `<wrapper>-container.ps1` and `.gitattributes` from the reference

### Requirement: Scripts keep LF line endings in every repository
The reference and every wrapper SHALL carry a `.gitattributes` that checks out text files with LF line endings regardless of the user's `core.autocrlf` setting. A shared test SHALL fail when a tracked text file contains a carriage return.

#### Scenario: Clone with Git for Windows defaults
- **WHEN** a repository is cloned on Windows with `core.autocrlf=true`
- **THEN** the checked-out `.sh`, `.py` and `.ps1` files contain no carriage return

#### Scenario: Carriage return committed
- **WHEN** a tracked text file contains a carriage return
- **THEN** the shared test fails naming the file

### Requirement: PowerShell files pass PSScriptAnalyzer and logic tests
The shim and the PowerShell entry SHALL pass PSScriptAnalyzer at warning level with a pinned analyzer version, and the shim's logic tests SHALL pass on PowerShell 7. The reference SHALL provide one check that runs both, in a digest-pinned PowerShell container without network, on any reference or wrapper checkout. Windows PowerShell 5.1 SHALL be validated on a Windows host and recorded in the validation log.

#### Scenario: New analyzer finding
- **WHEN** a change to the shim introduces a PSScriptAnalyzer warning
- **THEN** the reference check fails naming the file and line

#### Scenario: Shim logic regression
- **WHEN** a change breaks argument encoding, environment selection or a refusal rule
- **THEN** the shim logic tests fail without a Windows host

#### Scenario: Windows PowerShell 5.1 validation
- **WHEN** a reference tag changes the shim, the bootstrap or the Windows entry
- **THEN** the validation log records the Windows host check of that tag on Windows PowerShell 5.1

### Requirement: Shared bootstrap tests
The bootstrap SHALL be tested by shared Linux tests that run it with a fake `wslpath` and a fake managed command. They SHALL cover argument decoding, working-directory translation and refusals, the missing installation and the entry-directory overlap.

#### Scenario: Bootstrap regression
- **WHEN** a change to the bootstrap drops empty arguments
- **THEN** the shared bootstrap tests fail on Linux without Windows
