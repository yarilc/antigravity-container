# Proposal

## Why

Antigravity is on `sandbox-ref-28`. Adopting `sandbox-ref-36` brings the shared launcher, setup and qualification to the same baseline as the reference and gives Antigravity sessions a private container engine for operator-installed image toolchains.

## What Changes

- Adopt the shared files and regenerate the reference manifest from `sandbox-ref-36` at `ce2c9d28873838a4ac541da34edaf7d8b5264be4`.
- **BREAKING** Remove host Podman delegation in every mode. An exact `ANTIGRAVITY_CONTAINER_PODMAN=1` stops session launches and build-only operations before engine access. Rerunning managed setup removes the saved delegation setting. Operators register images with `--container-toolchain add` to run them through the session engine.
- Provide a session-owned rootless engine when library image toolchains are installed. The engine shares the session network boundary, uses a read-only image store, and supports nested systemd and explicit nested container limits on eligible engines.
- Adopt the release toolchain catalog, host-side archive provisioning, image recipe checks, and Windows toolchain path handling. Adopt the per-container process-budget and runtime-test portability changes.
- Update Antigravity's wrapper tests and operator documentation. Keep its provider defaults and Google account and Gemini API profiles, the `agy` entrypoint and executable temporary storage, and the existing behavior of `ANTIGRAVITY_YOLO`.

## Capabilities

### New Capabilities

- `session-container-engine` covers lifecycle, local access, storage, containment, qualification, budgets and nested systemd for the private engine.

### Modified Capabilities

- `container-isolation` applies session hardening with the private engine and updates process-budget verification.
- `container-launcher` covers launch endpoint validation and admission of build-only operations after delegation removal.
- `container-podman-access` retires the delegation requirements. The approval-bypass and launch-engine requirements move to `container-session`.
- `container-session` covers the old opt-in refusal, YOLO behavior and bounded engine queries.
- `container-setup` prepares the engine image, migrates saved settings and re-verifies the toolchain library.
- `network-egress` updates runtime-mode, proxy-budget and qualification evidence requirements.
- `runtime-image` covers startup image selection and build admission independently of the session engine.
- `shared-launcher` updates the boundary between shared acceptance and tests for Antigravity's hooks.
- `toolchain-library` adds the shipped catalog, host provisioning, image storage and Windows path handling.
- `windows-launcher` covers migration from delegation before the launch enters the machine.
- `workspace-mounts` preserves absolute workspace paths for the session engine and defines the paths exposed to the session.

## Impact

- Shared files in `launcher/`, `network/`, `setup/` and the shared test manifest move to the tagged baseline. Antigravity's wrapper, runtime, setup and network acceptance suites need matching assertions and fixtures.
- The runtime remains `localhost/antigravity-cli:latest`. The profile derives the new `localhost/antigravity-cli-engine:latest` image. The Antigravity runtime image pins and authentication policies remain on their existing versions.
- Existing managed installations rerun `--container-setup` to build and select the session engine and refresh qualification. The adoption records verification from the current development environment. Production checks on other environments follow closure of the change.
