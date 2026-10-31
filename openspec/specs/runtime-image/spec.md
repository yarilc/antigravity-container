# runtime-image Specification

## Purpose

Provide a complete, documented Linux environment for running the official Google Antigravity CLI without installing it on the host.

## Requirements

### Requirement: Official CLI and compatible Linux runtime
The image SHALL distribute the official Google `agy` CLI for Linux amd64 and arm64 on a base compatible with Google requirements, verifying download integrity and recording the installed version.

#### Scenario: Build for a supported architecture
- **WHEN** the image is built for amd64 or arm64
- **THEN** the binary matches the architecture, passes the official manifest checksum verification, and `agy --version` succeeds as a non-root user

#### Scenario: Unsupported architecture
- **WHEN** an architecture unsupported by the official distributor is requested
- **THEN** the build fails with an explicit diagnosis without installing an incompatible binary

### Requirement: Complete documented toolset
The image SHALL include Google installation and runtime dependencies applicable to the CLI, local Linux keyring support, Bash, Git, Python 3, Bubblewrap, the Podman client, OpenSpec, and documented search, editing, archive, and diagnostic tools.

#### Scenario: Dependency inventory
- **WHEN** image verification runs under a non-root identity
- **THEN** the declared tools are available, required dynamic libraries are resolvable, and the README distinguishes Google requirements from additional project tools

### Requirement: Image managed upgrades
The image SHALL disable automatic `agy` updates during sessions and support updates through explicit image rebuilds.

#### Scenario: Session on a read only root filesystem
- **WHEN** an ordinary session starts
- **THEN** `agy` uses the image binary without attempting to replace it and writes state or caches only to the designated paths

#### Scenario: Refresh requested
- **WHEN** `--container-build` is requested
- **THEN** the build rechecks the Google distribution without reusing a stale download layer and displays the resulting version
