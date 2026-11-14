# Proposal

## Why

claude-container published the operator-managed toolchain library in
`sandbox-ref-13`. It is one host directory shared by all five wrappers and
mounted read-only at `/toolchains`, so a restricted session can use Java, Go
or another relocatable toolchain without Podman access, an unrestricted
network or a rebuilt image. Later tags fixed defects found during the
adoptions:

- `sandbox-ref-14`: the shared qualification fixture installs `setup/`.
- `sandbox-ref-15`: toolchains cannot set `XDG_` variables.
- `sandbox-ref-16`: a shared comment no longer names an agent.
- `sandbox-ref-17`, found while porting the library to Antigravity:
  - toolchains cannot set `DBUS_SESSION_BUS_ADDRESS`, which `--unsetenv`
    cannot remove once `--env` sets it;
  - a toolchain that sets a variable protected only by another wrapper's
    profile no longer stops that wrapper's sessions. `launch-env` leaves the
    variable out with a warning.

Antigravity is the last wrapper on `sandbox-ref-12`. Without this change, its
shared files diverge from the reference, its parity table falls behind, and
its sessions cannot see the library.

## What Changes

- **Adopt `sandbox-ref-17`** with `tools/propagate.py` (`sandbox-ref-12` →
  `sandbox-ref-17`). The tool copies eight shared files byte for byte:
  - added: `setup/toolchains.py`, `tests/test_toolchains.py`;
  - modified: `network/agent_profile.py`, `network/control.py`,
    `network/qualification_records.py`, `setup/common.py`,
    `tests/test_alignment.py`, `tests/test_qualification.py`.

  It also moves the manifest and the current-state references (`AGENTS.md`,
  `docs/setup.md`, `docs/network-contract.md`) to the tag.
- **Port the launcher integration to `antigravity-container.sh`:**
  - `--container-toolchain add|list|remove|verify` as the first argument,
    dispatched before the network mode is read;
  - `ANTIGRAVITY_CONTAINER_TOOLCHAINS` (`0`/`false`/`no` omits the mount) and
    `ANTIGRAVITY_CONTAINER_TOOLCHAINS_DIR`;
  - the library checked by `launch-env` against the workspace (or worktree
    parent) and the one writable state directory: the dedicated or isolated
    home, or the shared `~/.gemini` (or `ANTIGRAVITY_CONTAINER_CONFIG_DIR`).
    It is then mounted at `/toolchains` with `ro,nosuid,nodev`;
  - `--mount-target /toolchains` for restricted sessions;
  - default toolchain `PATH` entries appended after the image's `PATH`, plus
    their variables;
  - the wrapper's own setting winning over toolchain variables. The launcher
    sets `AGY_CLI_DISABLE_AUTO_UPDATE=true`, which the shared module does not
    protect. The toolchain environment is therefore placed before it, and
    Podman keeps the last `--env`;
  - help text for the option and both variables.
- **Tests:**
  - wrapper cases with the synthetic engine;
  - real-engine runtime cases;
  - the live add during an offline session;
  - adaptations of existing fixtures that the new mount affects.
- **Test runner:** `tests/run-runtime.sh` gives the suites a private
  executable tmpfs as `SANDBOX_TEST_TMPDIR`, and `tests/test_wrapper.py`
  creates its fixtures there with a synthetic host home. The runtime suites
  give the wrapper a private home on native storage, because the runner's
  `HOME=/tmp` would place the default library below a world-writable
  directory.
- **Documentation:**
  - a README "Toolchains" section adapted to Antigravity: the instruction
    line for `GEMINI.md` or `AGENTS.md`, the writable locations, the three
    state modes, and the protected variables in their neutral and profile
    groups;
  - the help-related README parts, `AGENTS.md` and `docs/setup.md`
    (requalification).

  The example recipes stay in claude-container and are linked.
- **BREAKING (installation):** the launcher and the qualified shared code
  change, so restricted installations rerun `--container-setup`.

## Capabilities

### New Capabilities

- `toolchain-library`: the shared library, the `--container-toolchain`
  command, the read-only `/toolchains` mount and default environment in
  Antigravity sessions, and the protected session variables. An
  Antigravity-specific requirement covers the wrapper setting that toolchains
  cannot override.

### Modified Capabilities

None.

## Impact

- The eight shared files, `tests/test_reference_copy.py`, `README.md`,
  `AGENTS.md`, `docs/setup.md`, `docs/network-contract.md`,
  `docs/validation.md`.
- `antigravity-container.sh`, `tests/fake_podman.py`, `tests/test_wrapper.py`,
  `tests/test_runtime.py`, `tests/test_network_runtime.py`,
  `tests/run-runtime.sh`.
- `main` is one commit ahead of `origin/main` (the archive of
  `adopt-lab-host-fixes`); that stays as it is.
- The uncommitted `adopt-sandbox-ref-16` branch from the paused apply is
  replaced by `adopt-sandbox-ref-17`. Its wrapper-owned work is carried over.
- Out of scope:
  - registry network access;
  - the example recipes;
  - changes to the shared files.
