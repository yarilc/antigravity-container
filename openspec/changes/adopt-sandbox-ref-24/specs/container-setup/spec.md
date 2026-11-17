## MODIFIED Requirements

### Requirement: Protected complete installation
Setup SHALL prepare all files needed for the selected workflow in a native installation outside writable workspace, worktree-parent and state trees. Those files include the shared launcher core and the agent launcher part.

Setup SHALL validate ownership, ancestor permissions and overlaps, and SHALL create missing private directories. It SHALL refuse unsafe existing paths without recursive permission repair, credential imports, relabeling or added privileges.

Managed launches SHALL verify the entry script, the launcher core and the agent launcher part as protected files. Setup and its smoke checks SHALL ignore host values of `ANTIGRAVITY_CONTAINER_ENV_VARS` and `ANTIGRAVITY_CONTAINER_READONLY_STATE`.

#### Scenario: Checkout on a Windows mount
- **WHEN** setup runs from a checkout on a permission-emulating Windows filesystem and the user selects a valid native installation
- **THEN** it copies the required installation inputs to native storage and validates them there
- **AND** it does not require executing a compiled guard on the source mount

#### Scenario: Unsafe installation or state path
- **WHEN** a chosen path has unsafe ancestors, cannot enforce private permissions or overlaps an application-writable mount
- **THEN** setup identifies the path and fails without modifying existing permissions or claiming completion

#### Scenario: Installed launcher core
- **WHEN** setup completes an installation
- **THEN** the release contains `launcher/core.sh` and `agent/launcher.sh` as protected files, and a managed launch refuses a release where either is writable by others

### Requirement: Mode-specific image and guard preparation
Setup SHALL inspect or prepare the runtime image and the additional components required by the selected mode. The runtime image SHALL be built through the wrapper's build-only operation. Restricted modes SHALL receive a validated static guard and digest manifest. Provider mode, Antigravity's default, SHALL also receive a valid selected policy, a private runtime directory and an immutable proxy image identity. Existing suitable artifacts SHALL be reused unless refresh is approved.

#### Scenario: Fresh provider setup
- **WHEN** provider setup is approved with no prepared artifacts
- **THEN** setup prepares the pinned build inputs, toolchain, runtime and proxy images, compiles the guard and validates its manifest and policy
- **AND** launch preferences refer to an inspected immutable proxy image rather than an unresolved local tag

#### Scenario: Offline or unrestricted setup
- **WHEN** setup prepares offline mode
- **THEN** it prepares the runtime and guard without requiring a provider proxy image or authentication
- **AND** unrestricted setup requires neither the restricted guard nor provider proxy components

#### Scenario: Runtime image built by the wrapper
- **WHEN** setup needs the runtime image
- **THEN** it runs the wrapper's `--container-build` without `agy` arguments, so the image carries the current `build-inputs-hash` label

#### Scenario: Preparation fails
- **WHEN** an image build, image inspection, guard compilation or validation fails
- **THEN** setup reports the failed stage and leaves the last working installation selected
- **AND** it does not substitute a different policy, toolchain or network mode

### Requirement: Persistent non-secret managed launch preferences
Setup SHALL save versioned non-secret preferences and a managed launcher usable from any workspace without exports. Preferences and launcher code SHALL stay outside application-writable mounts and be validated before use. The launcher SHALL preserve arguments, stdin, terminal handling and the current directory. Direct invocation SHALL accept explicit runtime modes. An unset or empty effective mode SHALL select Antigravity's provider default, which needs the provider settings or gets setup guidance.

#### Scenario: New terminal and workspace
- **WHEN** the user invokes the managed launcher in a new terminal from a separate workspace
- **THEN** the saved network, profile, state, service, CA and approval choices apply without modifying shell startup files
- **AND** the current directory determines the mounted workspace and container working directory

#### Scenario: Explicit environment overrides
- **WHEN** a supported runtime variable is explicitly present in the launch environment
- **THEN** its value, including an empty value, takes precedence over the saved default
- **AND** the effective configuration still passes existing conflict, privacy and enforcement checks

#### Scenario: Unsafe or malformed preferences
- **WHEN** managed preferences are untrusted, invalid or use an unsupported schema
- **THEN** the launcher fails before image operations or container creation without evaluating their contents as shell code

#### Scenario: Invoked dispatcher or alias is writable
- **WHEN** an invocation uses a dispatcher copy or a symlink chain with any entry inside a writable workspace or state mount
- **THEN** launch fails before application execution even if the configured command and final symlink target are protected
- **AND** relative paths and dot-dot components are interpreted with filesystem symlink semantics

#### Scenario: Legacy managed dispatcher needs migration
- **WHEN** an old managed dispatcher cannot identify its actual invocation path to the installed helper
- **THEN** normal launch fails with setup guidance while help and setup remain available
- **AND** setup atomically upgrades the recognized dispatcher without overwriting unrelated command files

#### Scenario: Saved mode supplies launch configuration
- **WHEN** a validated managed launcher supplies saved offline, provider or unrestricted mode and there is no network environment override
- **THEN** the wrapper uses that mode instead of its default
- **AND** existing mode-specific readiness and qualification checks still determine whether an application can start

#### Scenario: Empty network override is not replaced
- **WHEN** an operator explicitly sets `ANTIGRAVITY_CONTAINER_NETWORK` to an empty value for a managed launch whose saved mode is offline or unrestricted
- **THEN** the empty value overrides the saved mode and the wrapper applies its provider default, with setup guidance when the provider settings are missing
- **AND** it does not silently restore the saved mode

#### Scenario: Explicit direct operator workflow
- **WHEN** an operator invokes the wrapper directly with a valid nonempty network mode and its required configuration
- **THEN** it proceeds through existing runtime checks without requiring managed preferences
- **AND** mode selection alone does not authorize maintenance, delegation or restricted qualification
