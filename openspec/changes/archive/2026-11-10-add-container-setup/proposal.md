# Proposal

## Why

`add-network-egress` gave Antigravity restricted modes, but preparing them is still a manual operator procedure, and a missing mode only names `ANTIGRAVITY_CONTAINER_NETWORK`. This second Wave 3 change completes the Antigravity port of the Claude reference sandbox, and with it Wave 3. It adds guided setup with a managed launcher, the unchanged shared setup and alignment tests, and the Antigravity row of the five-wrapper parity table.

One gap in the shared setup blocks Antigravity, and the operator decided it on 2026-11-10. Setup offers account sign-in only through a profile's `login_args`, a non-interactive login subcommand such as `claude auth login`. `agy` 1.5.3 has no login subcommand: Google sign-in happens only in the interactive TUI (Google OAuth, then a URL and a code). The profile validator requires at least one argument, so setup would neither offer sign-in nor say how to do it.

## What Changes

- **Shared setup fix first (`sandbox-ref-9`).** In `claude-container`, an account method may declare an empty `login_args`, meaning "sign in through the interactive agent".
  - Setup then asks whether to run the interactive sign-in now, and launches the installed wrapper without arguments in the scratch workspace, so the agent's own sign-in screen appears.
  - When declined or interrupted, setup prints the managed command to run.
  - Methods with arguments and API-key methods are unchanged.

  Tag `sandbox-ref-9`, then recopy into Codex, OpenCode and Pi (manifests and tests) and into this repository.
- The profile's `account` method declares `"login_args": []`.
- Copy the rest of `setup/` unchanged from `sandbox-ref-9` (`common.py`, `setup.py`, `launch.py`, `smoke.py`), plus the shared tests `tests/test_setup.py` and `tests/test_alignment.py`.
- Add `--container-setup`, used alone in an interactive terminal. It runs the shared setup, which:
  - asks for the mode, the authentication method (`account` or `gemini`), state, endpoint, delegation, CA trust, YOLO, budgets and lifetime;
  - discloses the residual exfiltration risk of provider mode and requires its acknowledgement;
  - prepares the images and the guard under maintenance consent;
  - installs a protected release, including `container-entrypoint.sh`, with a managed launcher at `~/.local/bin/antigravity-container`;
  - runs qualification and a credential-free smoke check;
  - offers the interactive account sign-in, or reports the API key to supply.
- Setup state follows the reference, as the operator decided on 2026-11-10:
  - it proposes `shared` on the first run, with the host `~/.gemini` as the default configuration directory and the existing disclosure;
  - `isolated` defaults to `~/.local/share/antigravity-container/home`, today's dedicated home.

  The wrapper's own default for direct launches (an unset variable means the dedicated home) is unchanged.
- **BREAKING (message only)**: an ordinary launch with an unset or empty `ANTIGRAVITY_CONTAINER_NETWORK` now stops with `setup required:` guidance pointing to `--container-setup`. Explicit operator modes keep working unchanged.
- The wrapper passes the application's stderr through the shared `setup/diagnostics.py` filter, as the other wrappers do. Wrapper messages that the shared tests check literally are aligned to the reference wording.
- Replace the per-agent identifier scan with the unchanged `tests/test_alignment.py`. Keep `tests/test_reference_copy.py` as the byte-identity check, extended to the new shared files.
- Add the per-agent `tests/test_setup_runtime.py` and the `--setup` and `--setup-runtime` runner modes.
- Add `docs/setup.md`, and update the README, help, `AGENTS.md`, `CHANGELOG.md`, `docs/network-contract.md` and `docs/validation.md`.
- Add the five-wrapper parity table to `docs/network-contract.md` with the Antigravity row. Replace the "Pending" Antigravity row in the other four repositories with the same row, and move every row to `sandbox-ref-9`.

## Capabilities

### New Capabilities

- `container-setup`: interactive host-side setup, covering:
  - the questionnaire and its prerequisites;
  - reviewed mutations and maintenance consent;
  - the protected installation and managed launch preferences;
  - authentication assistance, including the interactive account sign-in;
  - qualification and smoke readiness;
  - repeatable activation with rollback;
  - the provider acknowledgement;
  - saved budgets.

### Modified Capabilities

- `container-session`: missing-mode admission points to setup; first-user setup and migration guidance is added.
- `agent-authentication`: account sign-in can be started from setup through the interactive agent.
- `network-egress`:
  - the missing-mode scenario directs to setup;
  - the managed launcher can supply the mode;
  - the alignment check uses the shared `test_alignment.py` across `network/` and `setup/`;
  - the contract documentation includes the parity table.

## Impact

- **Code:**
  - `antigravity-container.sh`: `--container-setup`, the setup-required message, the diagnostics filter and the aligned messages;
  - `agent/profile.json`: `login_args: []` for `account`;
  - new copied files: `setup/common.py`, `setup/setup.py`, `setup/launch.py`, `setup/smoke.py`.
- **Tests:**
  - shared `test_setup.py` and `test_alignment.py`;
  - per-agent `test_setup_runtime.py`;
  - updates to `test_wrapper.py`, `test_reference_copy.py` and `run-runtime.sh`.
- **Users:**
  - new users run `bash ./antigravity-container.sh --container-setup` once and then use the managed launcher;
  - direct operator launches still work with an explicit mode.
- **Other repositories:**
  - `claude-container`: empty `login_args`, tag `sandbox-ref-9`, and the Antigravity parity row;
  - `codex-container`, `opencode-container` and `pi-container`: adoption of `sandbox-ref-9` and the Antigravity parity row.
- **Out of scope:**
  - authenticated verification, which stays operator-run after all Waves;
  - a setup default of `isolated` (the operator kept the reference default);
  - Wave 4 propagation.
