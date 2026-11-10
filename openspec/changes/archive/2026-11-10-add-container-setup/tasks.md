# Tasks

## 1. Shared interactive sign-in and reference `sandbox-ref-9`

- [x] 1.1 In `claude-container`, on a dedicated branch:
  - `network/agent_profile.py` accepts empty `login_args` (zero to eight unique arguments);
  - `setup/setup.py` `authenticate()` offers the interactive sign-in for empty `login_args`, runs the installed wrapper with no agent arguments on the terminal, and prints the next action when declined or failed;
  - `tests/test_agent_profile.py` accepts `[]` and still rejects nine arguments and duplicates;
  - `tests/test_setup.py` adds the empty-`login_args` case with a scratch profile and a fake wrapper.

  Verify `test_agent_profile`, `test_alignment`, `--setup`, `--shared` and `--qualification` in Claude, with unchanged results for the existing methods. Record in Claude `docs/validation.md`, merge, and create the tag `sandbox-ref-9`.
- [x] 1.2 In `codex-container`, `opencode-container` and `pi-container`, each on its own branch, copy the changed shared files from `sandbox-ref-9`. Update the `tests/test_reference_copy.py` manifest, tag and commit, and the current-state references. Verify `--shared` and `--setup` (Pi: also `--setup-runtime`). Record, commit and merge.
- [x] 1.3 In this repository, on branch `add-container-setup`, unpack `network/`, `setup/` and the shared tests (now including `tests/test_setup.py` and `tests/test_alignment.py`) from `sandbox-ref-9`. Verify with `diff -r` against the tag: no differences.
- [x] 1.4 Extend the `tests/test_reference_copy.py` manifest to the new files and move it to `sandbox-ref-9`. Verify that it passes, and that it fails on an injected byte change in `setup/common.py`.

## 2. Profile and wrapper setup entry points

- [x] 2.1 Add `"login_args": []` to the `account` method in `agent/profile.json`. Verify the profile query and `tests/test_agent_profile.py`.
- [x] 2.2 Add `--container-setup` to `antigravity-container.sh`. It must be used alone, needs an interactive terminal and host Python 3, and runs `exec python3 -I setup/setup.py`. Help keeps precedence. Replace the missing-mode message with the `setup required:` form that names the wrapper path. Update the help text. Verify with new `test_wrapper.py` cases.
- [x] 2.3 Pass the attached client's stderr through `setup/diagnostics.py` over a FIFO in the private session directory, when the filter and host Python exist. Reap the filter after the client within a one-second drain, inside the shutdown budget. Verify with `test_wrapper.py` cases:
  - the restart line is reclassified and real errors pass through;
  - the existing signal, TTY, pipe and exit-status cases still pass.
- [x] 2.4 Add `--setup` (shared `test_setup.py`) and `test_alignment` to `tests/run-runtime.sh` and the shared list, and run both. They must pass without edits to shared files. Align any wrapper message the shared tests check literally. If a failure comes from shared code, stop and fix it in `claude-container` first.

## 3. Setup runtime acceptance

- [x] 3.1 Port `tests/test_setup_runtime.py` from Pi with Antigravity names, and add the `--setup-runtime` runner mode. Verify:
  - offline, provider and unrestricted installations;
  - the managed launcher from another workspace;
  - qualification and the smoke check;
  - the shared-state choice saved as an empty state variable with `~/.gemini`, and the isolated choice as the dedicated home;
  - no credentials and no systemd changes.
- [x] 3.2 Add setup transcripts under a pseudo-terminal with a disposable `HOME`, in provider mode:
  - `gemini` with no key: the residual exfiltration acknowledgement naming the profile hosts, the maintenance review, `Sandbox: ready`, and `Authentication pending` naming `GEMINI_API_KEY`;
  - `account` with the sign-in declined: the next-action message naming the managed command;
  - `account` with the sign-in accepted: the TUI starts through the installed wrapper and is quit with two Ctrl+C, and the reported status names the interactive session.

  Record the transcript summaries in `docs/validation.md`.

## 4. Documentation and parity

- [x] 4.1 Add `docs/setup.md`, adapted from Pi, covering:
  - guided installation and maintenance consent;
  - the state choices, recommending `isolated` with Gemini CLI;
  - the managed launcher and rollback;
  - the interactive account sign-in and the Gemini key.

  Update:
  - the README: first-run section, setup-required migration, direct-launch section, verification modes;
  - the wrapper help;
  - `AGENTS.md`: the shared-file list with `setup/`, `test_setup.py` and `test_alignment.py`, the setup command and `sandbox-ref-9`;
  - `CHANGELOG.md` and `docs/network-contract.md`: references to `sandbox-ref-9`.

  Verify with markdownlint on the changed files and `git diff --check`.
- [x] 4.2 Add the five-wrapper parity table with the Antigravity row to `docs/network-contract.md`. Replace the Antigravity row in the other four repositories, documentation only. Verify that the five rows are identical and that the links resolve.
- [x] 4.3 Final verification:
  - `bash -n` and ShellCheck;
  - `bash tests/run-runtime.sh` with `--wrapper`, `--shared`, `--setup`, `--setup-runtime`, `--qualification`, `--network` and the default mode;
  - `openspec validate add-container-setup --strict`;
  - `git diff --check`.

  Record the results in `docs/validation.md`, and update `todo.md` items C09 and C11.

## Workflow follow-up

- `/opsx:archive`, then commit and merge into `main` here, and merge the parity-row branches in the other four repositories. The user pushes, including the tag `sandbox-ref-9`.
- Wave 3 is then complete. Next: the operator-run authenticated checks for all five wrappers, then Wave 4 propagation.
