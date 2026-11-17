# Design

## Context

Antigravity is on `sandbox-ref-21`. Its launcher, `antigravity-container.sh` (1024 lines), differs from the shared core where the launcher contract (`docs/launcher-contract.md` in `sandbox-container`, column A) records:

- **State (U4):** the default is a dedicated home `~/.local/share/antigravity-container/home`; an empty `ANTIGRAVITY_CONTAINER_STATE_DIR` selects shared `~/.gemini`, and `ANTIGRAVITY_CONTAINER_CONFIG_DIR` needs that empty value.
- **Temporary storage (U7, L7):** `/tmp` is executable (512m), the shared-state home is an executable 64 MiB tmpfs, and `/run` has mode 1777.
- **Signals (U9):** family-B lifecycle with separate creation phases.
- **Builds (U3, U8):** `--container-build` forces `--no-cache` and always starts a session; no `build-inputs-hash` label.
- **Credentials (U10):** unrestricted sessions forward `GEMINI_API_KEY` whenever it is set.
- **Toolchains:** an empty `ANTIGRAVITY_CONTAINER_TOOLCHAINS` omits the library.
- **Antigravity-only behavior:**
  - the restricted application is `/usr/local/bin/antigravity-entrypoint`;
  - `AGY_CLI_DISABLE_AUTO_UPDATE=true` is set after forwarding and toolchain variables;
  - `DBUS_SESSION_BUS_ADDRESS` is removed;
  - `ANTIGRAVITY_YOLO` → `--dangerously-skip-permissions`;
  - `container-entrypoint.sh` is an installed file (`install.files`).

The test map (`docs/launcher-test-map.md`) sorts Antigravity's 80 `tests/test_wrapper.py` cases into 26 shared, 7 rewritten into shared cases, 45 duplicates of the reference and 2 hooks (`test_four_independent_permission_combinations`, `test_antigravity_settings_win_over_toolchain_variables`). 32 cases are marked "to verify at adoption".

The `tools/propagate.py` dry run from `sandbox-ref-21` straight to `sandbox-ref-24` (2026-11-17) gives this plan:

- **Add:** `launcher/core.sh`, `tests/fake_podman.py`, `tests/fixtures/agent/launcher.sh`, `tests/fixtures/shell-agent/launcher.sh`, `tests/test_launcher.py`.
- **Update:** `network/README.md`, `network/agent_profile.py`, `network/control.py`, `network/qualification_records.py`, `network/qualify.py`, `setup/common.py`, `setup/launch.py`, `setup/setup.py`, `tests/fixtures/agent/profile.json`, `tests/sandbox_profile.py`, `tests/test_agent_profile.py`, `tests/test_alignment.py`, `tests/test_network_policy.py`, `tests/test_qualification.py`, `tests/test_setup.py`.
- **Rewrite:** one reference each in `AGENTS.md` and `docs/setup.md`, and eight in `docs/network-contract.md`.
- **Move:** the manifest to `sandbox-ref-24` (`dd5d82e`).

`tests/fake_podman.py` already exists here as Antigravity's own fake engine, which the old `tests/test_wrapper.py` uses. The tool replaces it with the shared fake.

The Claude and Codex adoptions found what every adoption needs:
- `tests/test_reference_copy.py` lists `launcher` in `CLOSED_DIRECTORIES`;
- the old wrapper tests run against the core only with an adapted harness: the fake answers the `build-inputs-hash` label and the core's one-line socket query, and synthetic installations copy the core, the agent part and the build inputs;
- the core prints no help for agent variables, so the agent part defines `agent_help`;
- U10 holds strictly: real network tests that relied on a host key set it inside the session;
- `/run` is not writable by the session user under the core; for Codex the user classified this as a visible change (2026-11-17), and the same contract rule (L7) applies here.

## Goals / Non-Goals

**Goals:**
- Antigravity runs entirely on the shared core. Its own launcher code is the entry script and `agent/launcher.sh`.
- No Antigravity launcher behavior disappears without being either a recorded visible change or a shared test.

**Non-Goals:**
- Adopting the core in Pi or OpenCode.
- Changing the Antigravity image, `agy` version, entrypoint script, policy inventories or authentication methods.
- Changing reference files inside this repository. A defect found here is fixed in `sandbox-container` and arrives by a tag.

## Decisions

1. **Adopt with the tool, straight from `sandbox-ref-21` to `sandbox-ref-24`.** Before running it, save the current `antigravity-container.sh`, `tests/test_wrapper.py` and `tests/fake_podman.py` outside the repository as the old-test baseline. The dry run must list exactly the plan in "Context". `--apply` switches to the branch `adopt-sandbox-ref-24`. Then add `launcher` to `CLOSED_DIRECTORIES` in `tests/test_reference_copy.py` and fix the parity rows by hand.

2. **Entry script, agent part and profile.**
   - `antigravity-container.sh` is the reference `sandbox-container.sh`, with only the wrapper name changed.
   - `agent/profile.json` adds `native.exec: /usr/local/bin/antigravity-entrypoint` and `native.exec_tmp: true`. The contract foresees executable temporary storage for Antigravity (native runtime components); the old launcher already had an executable `/tmp` and home, so no new evidence is needed. The runtime test asserts it.
   - `agent/launcher.sh` declares:
     - the profile values, `AGENT_EXEC=/usr/local/bin/antigravity-entrypoint`, `AGENT_EXEC_TMP=1`, `AGENT_SHARED_DIRS=()`;
     - `AGENT_INSTALL_FILES=(container-entrypoint.sh)`, which also joins the build-inputs hash (the image copies it);
     - `AGENT_CREDENTIALS=(gemini-api=GEMINI_API_KEY google-account=)`;
     - `AGENT_POLICY_HOSTS` for the two base profiles;
     - `AGENT_SESSION_ENV=(AGY_CLI_DISABLE_AUTO_UPDATE=true)` and `AGENT_UNSET_ENV=(DBUS_SESSION_BUS_ADDRESS)`; the core places fixed settings after toolchain and forwarded variables, so they win;
     - empty restricted, provider and reserved arrays.
   - Hooks:
     - **`agent_approval_bypass`:** `agent_bypass_args=(--dangerously-skip-permissions)`.
     - **`agent_help`:** documents `ANTIGRAVITY_YOLO`, `GEMINI_API_KEY` (provider with `gemini-api`, or unrestricted through `ANTIGRAVITY_CONTAINER_ENV_VARS`) and the missing D-Bus session and keyring.

   Alternative rejected: an `agent_environment` hook for the auto-update setting. A fixed value belongs in `AGENT_SESSION_ENV`, which the core already orders after forwarding.

3. **State follows U4.** Shared `~/.gemini` is the default; `ANTIGRAVITY_CONTAINER_CONFIG_DIR` overrides it without needing an empty `STATE_DIR`, and conflicts with a nonempty one. The README tells users of the dedicated home to set `ANTIGRAVITY_CONTAINER_STATE_DIR` to it or sign in again.

4. **Old tests gate the deletion.**
   - **Setup:** the saved `tests/test_wrapper.py` with its saved fake engine runs against the new entry script and core. The 80 cases stay unchanged; only the harness is adapted, as in the Claude and Codex adoptions.
   - **Outcomes:** every failing case is resolved in exactly one way:
     - **(a) Visible change.** The failure matches a row of the contract's "Visible changes" list (U1, U3, U4, U7, U8, U9, U10, U14, phase 1-2 toolchain switch, M4, L7), so the case is dropped.
     - **(b) Lost behavior.** The work stops. The behavior and a shared case go into `sandbox-container` through a reference change and a new tag, and this change then adopts that tag.
     - **(c) Antigravity-only behavior.** The case stays in the reduced `tests/test_wrapper.py`.
   - **Record:** passing shared and duplicate cases are dropped; the 32 "to verify at adoption" cases are resolved by name; the table goes into `docs/validation.md`.

5. **Reduced `tests/test_wrapper.py`.** It uses the shared `tests/fake_podman.py` and the real `agent/launcher.sh`. It covers:
   - the two hook cases: every combination of `ANTIGRAVITY_YOLO` and the Podman opt-in in shared and isolated state, and the fixed settings winning over toolchain and forwarded variables;
   - the application and bypass in offline, provider, unrestricted, shell and probe launches, with user arguments containing spaces;
   - `GEMINI_API_KEY` with each policy profile, in offline and unrestricted mode, and with an `ANTIGRAVITY_CONTAINER_ENV_VARS` attempt under `google-account`;
   - the help: provider hosts from the policy, `ANTIGRAVITY_YOLO`, `GEMINI_API_KEY` and the keyring note;
   - every outcome (c) from decision 4.

6. **Wrapper-owned runtime tests follow the reference diff.**
   - `tests/run-runtime.sh --wrapper` runs `test_launcher.py` and `test_wrapper.py`; `--shared` also runs `test_launcher`.
   - `tests/test_runtime.py` asserts 512/512/32 MiB for `/tmp`, `/var/tmp`, `/run` and 512 MiB for the shared-state home; `/tmp` and the home executable, `/var/tmp` and `/run` `noexec`; `/run` not writable by the session user; shared `~/.gemini` as default state.
   - `tests/test_network_runtime.py` installs `agent/launcher.sh`, `launcher/core.sh`, `container-entrypoint.sh` and `.containerignore`, and supplies the provider settings to the delegation grid.
   - The `tests/test_setup_runtime.py` shim answers only the `{{.Id}}` inspection.
   - `tests/test_setup_wrapper.py` covers the provider default.
   - Real network tests that need `GEMINI_API_KEY` under an operator profile set a synthetic key inside the session (U10).

7. **Documentation.**
   - **README:** help and first steps without migration history; network modes and the provider default; shared state by default and the isolated home; temporary storage; signals and the 20 s deadline; `ANTIGRAVITY_CONTAINER_ENV_VARS` and `ANTIGRAVITY_CONTAINER_READONLY_STATE`; credentials; build-only and stale images; a shared components section naming the core.
   - **`docs/setup.md`** follows the provider default; **`AGENTS.md`** describes the entry script and the agent part.
   - **Parity table:** the reference, Claude and Codex rows are copied from their repositories; the Antigravity row says it adopted `sandbox-ref-24`; the OpenCode and Pi rows are copied from theirs. After the merge, the Antigravity row is copied into `sandbox-container`, `claude-container` and `codex-container`.

8. **Validation scope.** The launcher, installation manifest and qualification identity all change, so validation covers the full set: the unit discovery in the disposable test container; `bash tests/run-runtime.sh` with `--wrapper`, `--shared`, `--setup`, `--setup-runtime`, `--qualification`, `--network` and `--guard`; the default runtime run against an image rebuilt with the build-only operation; `git diff --check`; and `tests/test_reference_copy.py` with host Python next to the `sandbox-container` checkout.

## Risks / Trade-offs

- **[Decision 4 finds a lost behavior]** → Implementation pauses for a reference change and a new tag. The most likely areas are the keyring and account-runtime checks and the isolated-home layout.
- **[Users of the dedicated home lose their sign-in by default]** → Intended (U4). The README gives the one-variable way to keep it.
- **[Executable `/tmp` and home stay a wider surface than the other wrappers]** → Intended by the contract for Antigravity's native runtime components; `/var/tmp` and `/run` become `noexec`.
- **[Images built before the adoption have no `build-inputs-hash` label and are refused as stale]** → Intended (U8). Test images and installations are rebuilt with `--container-build` or `--container-setup`.
- **[Installed qualification reports no longer match]** → The operator runs `--container-setup` on the three reference hosts after the merge.

## Migration Plan

1. Commit this change directory on `main`, save the old-test baseline, then dry-run and apply the propagation (branch `adopt-sandbox-ref-24`).
2. Write the entry script, the agent part and the profile fields. Run the old tests (decision 4) and resolve every failure before touching `tests/test_wrapper.py`.
3. Reduce the wrapper tests, update the runtime tests and the documentation, validate, and merge into `main`.
4. The operator pushes and runs `--container-setup` on the three hosts. The change is archived with spec sync.

Rollback: before the merge, delete the branch. After the merge, revert the merge commit.
