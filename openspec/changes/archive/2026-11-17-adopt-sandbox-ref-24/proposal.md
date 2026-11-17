# Proposal

## Why

`sandbox-ref-22` added the shared Bash launcher core (`launcher/core.sh`), `sandbox-ref-23` removed the Claude identifiers from its shared tests, and `sandbox-ref-24` reports an inaccessible state directory with the wrapper's diagnostic. The reference, Claude and Codex already run on the core. Antigravity is still on `sandbox-ref-21` with its own 1024-line `antigravity-container.sh`, whose state layout, temporary storage, signal handling and credential forwarding differ from the core's. Until Antigravity adopts the tag, its launcher keeps diverging and the 32 Antigravity cases marked "to verify at adoption" in the reference test map stay open.

## What Changes

- Adopt `sandbox-ref-24` directly from `sandbox-ref-21` with `tools/propagate.py`. This adds `launcher/core.sh`, `tests/test_launcher.py`, `tests/fake_podman.py` and the launcher fixtures, updates the changed shared files (`network/*`, `setup/*`, `tests/test_alignment.py`, `tests/test_setup.py`, ...), and moves the manifest and the current-state references to the tag. `tests/test_reference_copy.py` treats `launcher/` as a closed directory.
- Replace `antigravity-container.sh` with the thin entry script, identical to the reference's apart from its name.
- Add `agent/launcher.sh` with the Antigravity profile data and two hooks:
  - `agent_approval_bypass` turns `ANTIGRAVITY_YOLO` into `--dangerously-skip-permissions`;
  - `agent_help` documents `ANTIGRAVITY_YOLO`, `GEMINI_API_KEY` and the missing keyring.

  The data declares the entrypoint `/usr/local/bin/antigravity-entrypoint` as the restricted application, executable temporary storage, `container-entrypoint.sh` as an installed file, `AGY_CLI_DISABLE_AUTO_UPDATE=true` in every session, the removal of `DBUS_SESSION_BUS_ADDRESS`, and credentials per policy profile: `gemini-api` gets `GEMINI_API_KEY`, `google-account` gets none.
- `agent/profile.json` declares `native.exec` (the entrypoint) and `native.exec_tmp: true`, as the launcher contract foresees for Antigravity (U7).
- Before the old launcher is deleted, run Antigravity's current `tests/test_wrapper.py` against the new core and classify each failing case as a visible change, a lost behavior (fixed in the reference first, with a new tag) or Antigravity-only behavior (kept in the reduced `tests/test_wrapper.py`).
- Reduce `tests/test_wrapper.py` to Antigravity's hook and data tests and update the wrapper-owned runtime tests.
- Visible changes for Antigravity users, all from the contract's "Visible changes" list. Breaking changes are allowed: the project has no release.
  - **BREAKING**: a missing `ANTIGRAVITY_CONTAINER_NETWORK` selects `provider`. Without the provider settings, the launch still stops with setup guidance.
  - **BREAKING**: shared `~/.gemini` (or `ANTIGRAVITY_CONTAINER_CONFIG_DIR`) is the default state; the dedicated home `~/.local/share/antigravity-container/home` is no longer used. `ANTIGRAVITY_CONTAINER_STATE_DIR` still selects an isolated home, and an empty value means unset.
  - **BREAKING**: `--container-build` without `agy` arguments validates every setting, builds and exits. A stale image is refused until rebuilt, and an explicit build no longer skips the layer cache.
  - **BREAKING**: `/tmp` and the ephemeral home stay executable (512 MiB each); `/var/tmp` and `/run` are `noexec`, and `/run` is no longer writable by the session user.
  - **BREAKING**: signals follow the shared core: shutdown starts at once, also during creation, within one 20-second deadline.
  - **BREAKING**: unrestricted sessions no longer forward `GEMINI_API_KEY` unless `ANTIGRAVITY_CONTAINER_ENV_VARS` lists it.
  - **BREAKING**: shell mode passes its arguments to Bash.
  - An empty `ANTIGRAVITY_CONTAINER_TOOLCHAINS` mounts the library (the default) instead of omitting it.
  - New: `ANTIGRAVITY_CONTAINER_ENV_VARS` and `ANTIGRAVITY_CONTAINER_READONLY_STATE`.
  - Every session gets `TERM`, `COLORTERM`, `LANG` and `LC_ALL` when set, `USER`, `EDITOR=nano`, `VISUAL=nano` and `CONTAINER_NAME`. Unrestricted sessions also forward the proxy variables and run with `--init`; delegated sessions get private tmpfs storage for nested Podman. Isolated-home children must be contained and private.
  - Engine queries are bounded by timeouts, and builds use `--format docker`.
- Update the README, `docs/setup.md`, `docs/network-contract.md`, `AGENTS.md` and `docs/validation.md`. The help text now comes from the core.

## Capabilities

### New Capabilities

- `shared-launcher`: Antigravity's launcher is the shared core with a thin entry script and the Antigravity agent part. The agent part stays consistent with the profile, and its hooks and data are tested by Antigravity's own tests.

### Modified Capabilities

- `container-session`: provider default with setup guidance; session environment, extra variables, shell arguments, `--init` and `CONTAINER_NAME`; bounded engine queries; first-user guidance without the migration history.
- `container-launcher`: build-only `--container-build` and stale images; state preflight; the shared 20-second shutdown and immediate interruption of creation; credential forwarding in unrestricted mode.
- `workspace-mounts`: shared state by default; temporary storage layout and the read-only `/run`.
- `agent-authentication`: `GEMINI_API_KEY` reaches unrestricted sessions only through `ANTIGRAVITY_CONTAINER_ENV_VARS`.
- `container-podman-access`: private nested-Podman tmpfs mounts in delegated sessions.
- `container-setup`: the installation contains the core and the agent part; runtime builds go through the build-only operation; an empty network override selects provider.
- `network-egress`: provider default; launcher files as protected restricted inputs; profile fields `native.exec` and `native.exec_tmp`; the shared `launcher/` component; qualification uses the default mode.
- `runtime-image`: explicit builds keep the layer cache; the build-inputs label.
- `toolchain-library`: an empty switch mounts the library.

## Impact

- **Code:** `antigravity-container.sh` shrinks to the thin entry script; new `agent/launcher.sh`; `agent/profile.json` gains `native.exec` and `native.exec_tmp`; shared files copied from the tag; wrapper-owned tests and docs updated. `container-entrypoint.sh` and the `Containerfile` are unchanged.
- **Qualification:** the qualification identity now includes the core and the agent part. Every installation needs `--container-setup` again; the operator runs it on the three reference hosts.
- **State:** users of the dedicated home either set `ANTIGRAVITY_CONTAINER_STATE_DIR` to it or sign in again in the shared `~/.gemini`.
- **Other wrappers:** Pi adopts `sandbox-ref-24` next, OpenCode after it. If this adoption finds a lost behavior, a reference fix and a new tag come first.
