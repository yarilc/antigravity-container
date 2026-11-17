## MODIFIED Requirements

### Requirement: Image managed upgrades
The image SHALL disable automatic `agy` updates during sessions. Updates SHALL happen only by changing the recorded inputs and rebuilding the image explicitly. A rebuild after an input change SHALL download the changed artifacts again and verify their checksums; an explicit rebuild without input changes MAY reuse cached layers.

#### Scenario: Session on a read only root filesystem
- **WHEN** an ordinary session starts
- **THEN** `agy` uses the image binary without attempting to replace it and writes state or caches only to the designated paths

#### Scenario: Refresh requested
- **WHEN** `--container-build` is requested after the recorded version or checksum changed
- **THEN** the build downloads the recorded artifacts again, verifies their checksums and labels the image with the new build-inputs hash
- **AND** the installed version equals the recorded version rather than the latest published release

### Requirement: Explicit image build inputs
The image build context SHALL deny local inputs by default and allow only root-level `Containerfile`, `container-entrypoint.sh` and `.containerignore`, plus `network/relay.py` and `network/mux.py`, which the image copies to `/opt/sandbox-egress/`. The image SHALL NOT contain the guard. New local inputs SHALL require deliberate allowlist changes. The image SHALL carry a `build-inputs-hash` label over `Containerfile`, `.containerignore`, `network/relay.py`, `network/mux.py` and `container-entrypoint.sh`, and a launch SHALL refuse an image whose label does not match. Unknown files, credentials, configuration, and other nested files SHALL remain excluded independently of Git tracking or ignore rules.

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

#### Scenario: Entrypoint change makes the image stale
- **WHEN** `container-entrypoint.sh` changes after the image was built
- **THEN** a launch without `--container-build` stops naming the rebuild command
