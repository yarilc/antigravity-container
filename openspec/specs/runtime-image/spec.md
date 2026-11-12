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
The image SHALL include Google installation and runtime dependencies applicable to the CLI, Bash, Git, Python 3, OpenSSL, Bubblewrap, the Podman client, OpenSpec, and documented search, editing, archive, and diagnostic tools. It SHALL NOT include a D-Bus daemon, GNOME keyring or libsecret tools.

#### Scenario: Dependency inventory
- **WHEN** image verification runs under a non-root identity
- **THEN** the declared tools are available, required dynamic libraries are resolvable, `dbus-daemon` and `gnome-keyring-daemon` are absent, and the README distinguishes Google requirements from additional project tools

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

### Requirement: Image package sources use verified HTTPS
The runtime image recipe SHALL fetch Debian packages only from `https://` sources, with TLS peer verification enabled for every fetch. The build SHALL NOT require outbound port 80 and SHALL NOT fall back to plain HTTP. The built image SHALL keep HTTPS Debian sources.

#### Scenario: Host blocks outbound port 80
- **WHEN** the runtime image is built under maintenance authorization on a host where outbound TCP 80 is blocked and HTTPS to the Debian, npm and container registries is reachable
- **THEN** the build completes and the image reports the recorded agy and OpenSpec versions

#### Scenario: Built image keeps HTTPS sources
- **WHEN** a user inspects the Debian source configuration inside a container started from the runtime image
- **THEN** every Debian source URI uses `https://`

#### Scenario: Insecure transport is rejected by tests
- **WHEN** the recipe uses a plain-HTTP Debian source or disables apt TLS peer or host verification
- **THEN** the credential-free unit suite fails and names the violation

### Requirement: Package-source trust bootstrap uses pinned inputs and opt-in host CA
Before Debian `ca-certificates` is installed, the recipe SHALL verify HTTPS package fetches with roots from the digest-pinned base image, plus the operator's selected CA bundle only when host CA trust is enabled. It SHALL add no image, digest or download input. It SHALL remove the bootstrap bundle in the same build step, and the built image SHALL contain Debian `ca-certificates`.

#### Scenario: No bootstrap residue
- **WHEN** a user lists the bootstrap bundle path inside a container started from the runtime image
- **THEN** the file does not exist
- **AND** the Debian `ca-certificates` package is installed

#### Scenario: Host CA trust disabled
- **WHEN** setup or `--container-build` builds the runtime image with host CA trust disabled
- **THEN** the build receives no host CA bundle and verifies only against the base image's roots

#### Scenario: TLS-intercepting network with host CA trust
- **WHEN** setup or `--container-build` builds the runtime image with host CA trust enabled and a CA bundle that includes the network's interception CA
- **THEN** the build receives that bundle only as a build secret, the HTTPS package fetches verify against it, and the build completes

#### Scenario: Host CA bundle is not persisted
- **WHEN** a user searches a container started from an image built with host CA trust enabled
- **THEN** neither the bootstrap bundle nor the build secret is present in the image

### Requirement: Image working directory exists in the image
The runtime image SHALL contain its configured working directory `/workspace` in an image layer, owned by root with mode 755, so that a container started without `--workdir` never makes the engine create or chown it at start.

#### Scenario: Container started without an explicit workdir
- **WHEN** a qualification gate container starts from the runtime image without `--workdir`
- **THEN** the engine uses the existing `/workspace` and performs no workdir creation or ownership change

#### Scenario: Host with a large domain UID
- **WHEN** the caller's UID, for example 31600276, cannot be used for an engine-side chown under `--userns=keep-id`
- **THEN** qualification containers still start, because no workdir chown is needed

#### Scenario: Recipe regression is rejected by tests
- **WHEN** the recipe declares `WORKDIR /workspace` without creating `/workspace` in a build step
- **THEN** the credential-free unit suite fails

### Requirement: Release artifact download honors the opt-in host CA
The recipe's download of the recorded agy release artifact SHALL verify TLS against the image's CA certificates plus the operator's selected CA bundle only when host CA trust is enabled, supplied as the same optional `build-ca` build secret. The artifact SHALL still be verified against its recorded SHA-512. Neither bundle SHALL remain in the image.

#### Scenario: TLS-intercepting network with host CA trust
- **WHEN** the runtime image is built with host CA trust enabled and a bundle that includes the network's interception CA
- **THEN** the artifact download verifies against that bundle, the SHA-512 check passes and the build completes

#### Scenario: Host CA trust disabled
- **WHEN** the runtime image is built without host CA trust
- **THEN** the download verifies only against the image's CA certificates

#### Scenario: Tampered artifact
- **WHEN** the downloaded artifact does not match the recorded SHA-512
- **THEN** the build fails, whatever CA bundle was used
