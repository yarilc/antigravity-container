## Context

`README.md`, section "Updating pinned image inputs", gives the procedure. Only
`OPENSPEC_VERSION` moves. `tested.cli` follows `AGY_VERSION`, and
`tests/test_image_pins.py` checks that they match, so both stay at 1.5.3. The
`Containerfile` belongs to the wrapper, so the bump needs no propagation from
`sandbox-container`.

The reference makes the same bump in its own change, `pin-openspec-2-0-0`, and
records there an offline round trip and a check against existing state.

## Goals / Non-Goals

**Goals:**
- Pin OpenSpec 2.0.0 exactly. The build check `openspec --version`, the image
  smoke check and the runtime suites must all pass.
- Show that `agy` 1.5.3 still starts and behaves as before in the rebuilt image.

**Non-Goals:**
- Moving `agy` to 1.5.11 or any later version. That needs a new endpoint
  measurement and a fresh manifest read, and gets its own change.
- Changing the base digest. A separate change will review the sandbox image.
- Changing Google profiles, policy revision or network contract rows.

## Decisions

- **Keep `agy` 1.5.3.**
  - It follows the agreed age rule: newest non-prerelease that was at least 72
    hours old on 2026-11-18.
  - The official manifest only offers its current build, 1.5.11.
  - Alternative rejected: an exception for 1.5.11.
- **No spec delta.**
  - Behavior does not change; only the recorded version does.
  - The `network-egress` text that names `agy` 1.5.3 remains true.
- **Reuse the reference's functional check.**
  - Run the same offline OpenSpec round trip inside this image.
  - Then run `agy --version` under the guard, so that the OpenSpec layer change
    is shown not to affect the agent.

## Risks / Trade-offs

- [OpenSpec 2.0 dependencies change the global `node_modules` that `agy` also
  sits beside] → `agy` is a standalone binary unpacked from its artifact, not
  an npm package. The guard check and the runtime suite confirm that it is
  unaffected.
- [OpenSpec 2.0 behaves differently with existing state] → The reference
  change covers that check. This change repeats only the version and the round
  trip.
- [Rollback] → Revert one line and rebuild.

## Migration Plan

1. The operator pushes `main`.
2. The operator reruns `--container-setup` on the three hosts.
