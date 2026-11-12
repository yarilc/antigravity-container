# Spec Delta

## ADDED Requirements

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
