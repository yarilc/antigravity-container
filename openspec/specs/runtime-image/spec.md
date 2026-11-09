# runtime-image Specification

## Purpose

Provide a complete, documented Linux environment for running the official Google Antigravity CLI without installing it on the host.

## Requirements

### Requirement: Official CLI and compatible Linux runtime
The image SHALL distribute the official Google `agy` CLI for Linux amd64 and arm64 on a base compatible with Google requirements. Each architecture SHALL be installed from a recorded immutable release artifact URL. The artifact SHALL be verified against its recorded SHA-512 before installation. The image SHALL record the installed version.

#### Scenario: Build for a supported architecture
- **WHEN** the image is built for amd64 or arm64
- **THEN** the binary comes from that architecture's recorded artifact, matches its recorded SHA-512, matches the architecture, and `agy --version` reports the recorded version as a non-root user

#### Scenario: Checksum mismatch
- **WHEN** the downloaded artifact does not match its recorded SHA-512
- **THEN** the build fails without installing the binary

#### Scenario: Unsupported architecture
- **WHEN** an architecture without a recorded artifact is requested
- **THEN** the build fails with an explicit diagnosis without installing an incompatible binary

### Requirement: Complete documented toolset
The image SHALL include Google installation and runtime dependencies applicable to the CLI, local Linux keyring support, Bash, Git, Python 3, Bubblewrap, the Podman client, OpenSpec, and documented search, editing, archive, and diagnostic tools.

#### Scenario: Dependency inventory
- **WHEN** image verification runs under a non-root identity
- **THEN** the declared tools are available, required dynamic libraries are resolvable, and the README distinguishes Google requirements from additional project tools

### Requirement: Image managed upgrades
The image SHALL disable automatic `agy` updates during sessions. Updates SHALL happen only by changing the recorded inputs and rebuilding the image explicitly.

#### Scenario: Session on a read only root filesystem
- **WHEN** an ordinary session starts
- **THEN** `agy` uses the image binary without attempting to replace it and writes state or caches only to the designated paths

#### Scenario: Refresh requested
- **WHEN** `--container-build` is requested
- **THEN** the build reuses no cached layer, downloads the recorded artifacts again, verifies their checksums and displays the resulting version
- **AND** the version equals the recorded version rather than the latest published release

### Requirement: Explicit image build inputs
The image build context SHALL deny local inputs by default and allow only root-level `Containerfile`, `container-entrypoint.sh`, `keyring-session.sh`, and `.containerignore`. New local inputs SHALL require deliberate allowlist changes. Unknown files, credentials, configuration, and nested directories SHALL remain excluded independently of Git tracking or ignore rules.

#### Scenario: Unknown or sensitive files exist
- **WHEN** the build context contains unknown files, `.env`, local authentication/configuration, state, or nested directories
- **THEN** none of those inputs is available to build COPY/ADD operations

#### Scenario: Nested filenames resemble allowed inputs
- **WHEN** nested directories contain files named `Containerfile`, `container-entrypoint.sh`, or `keyring-session.sh`
- **THEN** those nested files remain excluded

#### Scenario: Required helper copies
- **WHEN** the image recipe copies its root-level entrypoint and keyring helper from the restricted context
- **THEN** both copies succeed and retain the executable helper content needed for the existing runtime

#### Scenario: Context inventory
- **WHEN** a real Podman fixture copies all available context inputs into an inspection directory
- **THEN** the resulting inventory contains exactly the four allowed root-level files and no other local inputs

### Requirement: Runtime image inputs are pinned
The image recipe SHALL install an exact `@fission-ai/openspec` version recorded in the repository and SHALL reference the base image by registry digest. No floating tag, `latest` specifier or version range SHALL select an image input. Sessions SHALL NOT change the installed `agy` or OpenSpec version.

#### Scenario: Build uses recorded versions
- **WHEN** the image is built with `--container-build`
- **THEN** `agy --version` and `openspec --version` in the resulting image report exactly the recorded versions
- **AND** the base layer comes from the recorded digest

#### Scenario: Unpinned input is rejected by tests
- **WHEN** the recipe uses a base image without digest, an OpenSpec package without exact version or `@latest`, a release manifest or remote installer instead of a recorded `agy` artifact, or an `agy` artifact without a recorded SHA-512
- **THEN** the credential-free unit suite fails

### Requirement: Version updates follow explicit maintenance
Documentation SHALL describe the update procedure:
- read the official release manifest for each supported architecture;
- record the new `agy` version, artifact URLs and SHA-512 values, the OpenSpec version or the base digest in the recipe;
- rebuild explicitly with `--container-build`;
- rerun the credential-free and real-engine checks, including the keyring checks;
- record the tested versions with the date in the validation record.

#### Scenario: Maintainer updates agy
- **WHEN** a maintainer follows the documented procedure to move to a new `agy` release
- **THEN** the procedure requires recorded per-architecture URLs and checksums, an explicit rebuild, a rerun of the checks and a dated validation entry naming the tested versions
