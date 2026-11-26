# Spec Delta

## ADDED Requirements

### Requirement: Separate runtime and session engine images

The runtime image selection SHALL continue to apply to the agy or shell container. Sessions that require a container engine SHALL use a separate prepared engine image. A missing engine image SHALL stop an engine-required launch with setup guidance.

#### Scenario: Runtime image is overridden

- **WHEN** ANTIGRAVITY_CONTAINER_IMAGE selects a custom runtime and a session uses an installed image toolchain
- **THEN** the session uses the requested runtime and starts its engine from the separate prepared engine image

#### Scenario: Required engine image is missing

- **WHEN** the toolchain library contains images and the configured or default engine image is missing
- **THEN** the launch stops with guidance to rerun setup or disable the library, before the application starts
