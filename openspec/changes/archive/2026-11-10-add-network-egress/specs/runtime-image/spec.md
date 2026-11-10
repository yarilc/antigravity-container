# Spec Delta

## MODIFIED Requirements

### Requirement: Complete documented toolset
The image SHALL include Google installation and runtime dependencies applicable to the CLI, Bash, Git, Python 3, OpenSSL, Bubblewrap, the Podman client, OpenSpec, and documented search, editing, archive, and diagnostic tools. It SHALL NOT include a D-Bus daemon, GNOME keyring or libsecret tools.

#### Scenario: Dependency inventory
- **WHEN** image verification runs under a non-root identity
- **THEN** the declared tools are available, required dynamic libraries are resolvable, `dbus-daemon` and `gnome-keyring-daemon` are absent, and the README distinguishes Google requirements from additional project tools

### Requirement: Explicit image build inputs
The image build context SHALL deny local inputs by default and allow only root-level `Containerfile`, `container-entrypoint.sh` and `.containerignore`, plus `network/relay.py` and `network/mux.py`, which the image copies to `/opt/sandbox-egress/`. The image SHALL NOT contain the guard. New local inputs SHALL require deliberate allowlist changes. Unknown files, credentials, configuration, and other nested files SHALL remain excluded independently of Git tracking or ignore rules.

#### Scenario: Unknown or sensitive files exist
- **WHEN** the build context contains unknown files, `.env`, local authentication/configuration, state, or nested directories
- **THEN** none of those inputs is available to build COPY/ADD operations

#### Scenario: Nested filenames resemble allowed inputs
- **WHEN** nested directories contain files named `Containerfile`, `container-entrypoint.sh`, `relay.py` or `mux.py` outside `network/`
- **THEN** those nested files remain excluded

#### Scenario: Required helper copies
- **WHEN** the image recipe copies its root-level entrypoint and the relay and multiplex modules from the restricted context
- **THEN** the copies succeed and retain the content needed for the existing runtime and restricted sessions

#### Scenario: Context inventory
- **WHEN** a real Podman fixture copies all available context inputs into an inspection directory
- **THEN** the resulting inventory contains exactly the five allowed files and no other local inputs

## ADDED Requirements

### Requirement: Pinned CLI matches the tested policy version
The `agy` version pinned in `Containerfile` SHALL equal the CLI version recorded in the protected network policy's tested metadata. A version change SHALL update both in the same change and record the tested version in the validation record.

#### Scenario: Versions diverge
- **WHEN** the pinned `AGY_VERSION` differs from the policy's tested CLI field
- **THEN** the credential-free unit suite fails and names both versions

### Requirement: Restricted sessions use an immutable runtime image identity
Offline and provider launches SHALL resolve the selected runtime image to its immutable image ID before preparation and SHALL create the agent container from that ID. An unresolvable or malformed identity SHALL stop startup. Unrestricted launches MAY keep using the image name.

#### Scenario: Image tag moves during a launch
- **WHEN** the selected tag is rebuilt after a restricted launch has resolved its identity
- **THEN** the session and its qualification check use the resolved ID, not the moved tag

#### Scenario: Identity cannot be resolved
- **WHEN** image inspection fails or returns a malformed ID in a restricted mode
- **THEN** startup fails before agent execution

### Requirement: Proxy image acquisition requires maintenance and a digest
Provider mode SHALL use the immutable egress proxy image named by `ANTIGRAVITY_CONTAINER_EGRESS_IMAGE`. An absent proxy image SHALL be pulled only with exact `ANTIGRAVITY_CONTAINER_MAINTENANCE=1` and only when the reference is pinned by digest. Otherwise startup SHALL fail with maintenance guidance before agent execution.

#### Scenario: Proxy image absent without authorization
- **WHEN** the proxy image is absent and maintenance is not authorized or the reference has no digest
- **THEN** startup fails without pulling and names the required operator action
