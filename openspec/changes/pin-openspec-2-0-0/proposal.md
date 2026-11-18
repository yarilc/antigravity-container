## Why

The image pins OpenSpec 1.16.0. On 2026-11-18 the six repositories agreed to
move to the newest stable release that was at least 72 hours old at that
time. For OpenSpec that is 2.0.0.

The `agy` CLI stays at 1.5.3. Its only newer release, 1.5.11, was uploaded on
2026-11-18 and fails that age rule. A later change will move it.

## What Changes

- `Containerfile`: `OPENSPEC_VERSION` moves from `1.16.0` to `2.0.0`.
  `AGY_VERSION`, both `AGY_URL_*` values, both `AGY_SHA512_*` values and the
  base image digest are unchanged.
- `tests/test_image_pins.py`: the version-range mutation follows the new pin.
- `docs/validation.md`: a dated maintenance entry is added.
- `CHANGELOG.md`: the bump is recorded under Unreleased.
- **BREAKING (inside the image):** OpenSpec 2.0 removes the generated `/opsx:*`
  command files and installs skills in `.agents/skills/`. `agy` reads neither
  of these by default. The operator's planning CLI migrates to 2.0 at the end
  of the six-repository effort, outside this change.

No shared launcher file changes. The change creates no new reference tag.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The image requirement already asks for the exact recorded OpenSpec
version. `network-egress` names `agy` 1.5.3, which does not change. The change
sets `skip_specs: true`.

## Impact

- **Files:** `Containerfile`, `tests/test_image_pins.py`, `docs/validation.md`,
  `CHANGELOG.md`.
- **Policy:** `agent/policies/default.json` `tested.cli` is unchanged, because
  `agy` keeps its version. No Google host is remeasured.
- **Image identity:** the image changes, so the operator reruns
  `--container-setup` on the three hosts.
- **Persistent state:** state is kept. `agy` state and the shared OpenSpec
  configuration must work with the new image.
