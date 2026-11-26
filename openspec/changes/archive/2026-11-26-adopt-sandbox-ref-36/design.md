# Design

## Context

Antigravity's reference manifest names `sandbox-ref-28` at
`ba1ef1428a57625b70bb45d55cade5f08f46eecc`. Its shared launcher still admits
host Podman delegation in unrestricted mode. Its own tests exercise that
socket, the setup prompt and the old service environment. The target tag
changes both the launch path and the fixtures these tests consume.

A dry run with the reference's current propagation tool on a clean clone of
Antigravity found 29 shared files to update, 17 to add, zero removals and 16
review lines. The thin PowerShell entry and `.gitattributes` are identical
between the reference tags.

## Goals / Non-Goals

- Keep the shared files byte-identical to `sandbox-ref-36` and validate the
  Antigravity-specific integration against its real entrypoint.
- Keep the existing agent image inputs, Google account and Gemini API
  policies, and authentication flow. These inputs determine the existing
  provider evidence independently of reference adoption.
- Limit the change to the Antigravity adoption. Reference tooling and the
  proposed dependency mirror have their own change histories.

## Decisions

1. **Propagate from the tag.** Run `tools/propagate.py` from
   `sandbox-container` against a clean target, first as a dry run and then
   with `--apply`. It owns the copied files, the manifest and current-state
   version references. Review the target-owned lines for stale file lists
   and behavior descriptions. Use `setup/engine.py`'s `INPUTS` in the
   network test installation to carry the complete tagged engine recipe.
   A defect in shared code belongs in the reference and needs a new tag.
2. **Keep engine policy in shared code.** Guided setup builds the prepared
   engine image and saves its identity in schema 3 preferences. The launcher
   starts an engine only when the enabled library has image toolchains. A
   private loopback endpoint and a per-session engine lifetime keep image
   tests within the workspace, resource and network limits. In offline and
   provider modes qualification also checks the engine path when it is used.
   `agent/profile.json` already yields `localhost/antigravity-cli-engine:latest`
   through the shared image-name derivation. The engine image declares
   `SETUID,SETGID,SYS_CHROOT,CHOWN` for its startup step and follows the
   reference's fixed exceptions. It runs non-root after startup.
3. **Preserve Antigravity's hooks.** The profile keeps the `agy` entrypoint,
   executable `/tmp` and ephemeral home, and file-backed Google account
   state. The wrapper keeps `AGY_CLI_DISABLE_AUTO_UPDATE=true` with its
   existing precedence and forwards Gemini credentials under the existing
   profile rules. Wrapper tests retain argument boundaries, native permission
   flags, shell behavior and the credential-free fixed qualification probe.
   The shared launcher suite owns the old opt-in refusal grid.
4. **Adapt the real-engine fixtures.** Use the reference's engine acceptance
   patterns for workspace binds, session isolation and offline containment.
   Keep Antigravity's account and Gemini fixtures, synthetic Gemini tool
   request, and PTY coverage. Apply the shared guarded-terminal probe to
   engine-dependent terminal cases. Measure cgroup limits according to
   actual controller delegation and read the effective process rlimit when
   its fallback applies. Setup acceptance uses a host-visible CA fixture and
   tracks only its disposable release image tags.
5. **Use Antigravity's existing spec boundaries.** Apply the reference
   engine, toolchain and process-budget deltas through the proposal's
   capability paths. Keep launch endpoint validation in
   `container-launcher`, preserve its response boundary contract in
   `container-session`, and move `ANTIGRAVITY_YOLO` semantics there before
   retiring `container-podman-access` through the change metadata. Refresh
   the existing workspace and toolchain purpose statements to describe
   the private engine. Keep executable temporary storage in the workspace
   and isolation requirements. Preserve historical
   adoption evidence when updating the parity row.
6. **Verify in the current development environment.** Run the checks that
   its filesystem, network and tools support. Record passes, skips, and
   unavailable checks with the reasons observed. The tag's reference record
   provides platform and nested systemd evidence for the shared files.
   Run production Linux, WSL and Windows checks after closing the change.
   Open a separate change for each defect discovered during those checks.

## Risks / Trade-offs

- Older local scripts may still set `ANTIGRAVITY_CONTAINER_PODMAN=1`. The
  early migration diagnostic names the setting and the image-toolchain
  replacement. Guided setup migrates the saved setting and keeps the other
  proposed values.
- Hosts delegate different cgroup controllers and some OCI runtimes cannot
  attach the guarded terminal fixture. Record measured limits and probe
  results with the host identity and the affected cases.
- The Windows bootstrap changed. Its real-machine validation exercises the
  Windows entry, refusal of saved delegation and a session with library
  images. A normal interactive launch provides evidence for the entrypoint.
- The new engine image and records must match the adopted checkout. Use the
  adoption runner to prepare the tagged engine and record its ID and label.
  Use the wrapper's setup to generate installation-specific launch and
  qualification records.

## Migration Plan

1. Adopt the tag and record the local development checks and the Antigravity
   parity row before closing the change. Record production evidence after
   closing it.
2. Rerun `--container-setup` for existing installations, from PowerShell
   for the managed Windows installation. Remove exact legacy delegation
   settings from the launch environment and register the required image
   toolchains before starting a new session.
3. If the release needs to be rolled back, select the previous trusted
   wrapper release and rerun its setup to restore compatible managed
   launch and qualification records.
