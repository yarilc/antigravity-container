# Tasks

## 1. Adopt `sandbox-ref-28`

- [x] 1.1 Commit this change directory on `main`. Then, from `sandbox-container`, run `python3 -I tools/propagate.py ../antigravity-container sandbox-ref-25 sandbox-ref-28` (dry run), then the same command with `--apply`. Verify:
  - the plan lists the files in design "Context";
  - the checklist includes `--guard`;
  - the tool switched to `adopt-sandbox-ref-28`.
- [x] 1.2 Restore the OpenCode and Pi rows of `docs/network-contract.md` from `main` (design decision 5). Verify:
  - those two rows equal the ones on `main`;
  - the reference, Claude and Codex rows equal the ones in `sandbox-container`.
- [x] 1.3 Copy `sandbox-container.ps1` to `antigravity-container.ps1` byte for byte, and copy `.gitattributes`. Commit both, then rewrite the working files with LF (design decision 2). Verify:
  - `git status` is clean after the renormalization;
  - with host Python next to the `sandbox-container` checkout, and the sibling check not skipped, `python3 -m unittest tests.test_reference_copy tests.test_alignment` passes, including the entry, ASCII and line-ending tests.
- [x] 1.4 Add the reference header to `agent/launcher.sh` (design decision 3). Verify, from `sandbox-container`:
  - `bash tools/shellcheck.sh ../antigravity-container` reports no finding;
  - `bash tools/powershell.sh ../antigravity-container` passes the shim cases with no finding.

## 2. Antigravity's tests and documentation

- [x] 2.1 Rebuild the runner's stale images with the maintenance build and host CA trust, and make the guard toolchain available as `development` or through `SANDBOX_GUARD_TOOLCHAIN` (design decision 7). Verify: `localhost/antigravity-cli:latest` carries the current `build-inputs-hash`, `agy --version` reports 1.5.3 and `openspec --version` 2.0.0.
- [x] 2.2 Adapt Antigravity's own tests (design decision 4):
  - copy the current Claude and Codex `tests/test_setup_wrapper.py` byte for byte;
  - in `tests/test_runtime.py`, add `engine_budgets()`, make the budget assertions follow it, and change the process probe to a budget of 128 with 200 children, skipped when no mechanism applies;
  - in `test_build_context_allows_only_required_inputs`, copy the inputs with `shutil.copy2`, so the entrypoint keeps its executable bit (operator decision).

  Verify: `bash tests/run-runtime.sh --wrapper` passes, and the default `bash tests/run-runtime.sh` passes `test_effective_hardening_and_budgets`, `test_tools_without_capabilities` and `test_build_context_allows_only_required_inputs`.
- [x] 2.3 Run the unit discovery in the disposable test container, then `bash tests/run-runtime.sh` in each of these modes:
  - `--shared`, `--setup` and `--setup-runtime`;
  - `--qualification`, `--guard` and `--network`;
  - no mode.

  Record the image and the guard toolchain used. Fix in Antigravity's own tests any failure that a shared behavior change causes. Verify: every mode passes, apart from failures already recorded for this runner. A failure in shared code pauses the change.
- [x] 2.4 Adapt the documentation (design decision 6):
  - `README.md`:
    - the `## Windows with Podman machine` section, with the sign-in inside an interactive `agy` session, the `gemini` method, host CA trust on Windows and the install as a command;
    - the Windows limits, including Bitdefender and `agy`'s internal sandbox;
    - the Podman Machine connection sentence and the guard as the confined init;
    - the cgroup managers and the rlimit fallback in `### Session hardening, budgets and lifetime`;
    - the Windows sensitive folders;
  - `docs/setup.md`:
    - the Windows setup and the authentication steps from Windows;
    - setup without a launch service;
    - the carriage-return check;
    - candidate tags;
    - the service endpoint for restricted modes;
    - the budget plan;
  - `AGENTS.md`: `antigravity-container.ps1`, the Windows files, the ShellCheck and PowerShell checks, the Windows sensitive roots, and the cgroup manager and rlimit rule.

  Verify:
  - the README names `antigravity-container.ps1`, `$env:GEMINI_API_KEY`, `modelProvider` and `podman machine set --import-native-ca`;
  - no `SANDBOX_CONTAINER_`, `CLAUDE_` or `CODEX_` name, and no statement specific to another wrapper, appears in the new text;
  - `git diff --check` passes.

## 3. Validation on Windows

- [x] 3.1 Prepare the operator bundle: snapshots of `antigravity-container` and `sandbox-container`, and a README with the steps of design decision 8. Verify:
  - the README lists each step, the summary copies and the data to send back;
  - the checksums match.
- [x] 3.2 Have the operator run design decision 8. Verify that `docs/validation.md` records:
  - the setup with the declined sign-in and its Windows next step;
  - the Google sign-in, the session with tool use and Ctrl+C;
  - the token reuse in a second session;
  - `windows-validate` on both editions, once with `-Install -StopMachine`;
  - the `gemini` method check, with a real key or with a dummy one.

  No case may fail. If one does, the change pauses for a decision between a documented limit in the README's Windows limits and a fix.

## 4. Record, merge and parity

- [x] 4.1 Add the `sandbox-ref-28` adoption section to `docs/validation.md`, from the tool's template, with every result of tasks 2.1 to 2.3 and 3.2. Set Antigravity's parity row to "Adopted `sandbox-ref-28`". Commit with the tool's message and merge into `main`. Verify: `tests/test_reference_copy.py` passes on `main`.
- [x] 4.2 Copy Antigravity's parity row into `sandbox-container`, `claude-container`, `codex-container`, `opencode-container` and `pi-container`, with one commit on `main` in each. Verify: the reference, Claude, Codex and Antigravity rows are identical in the six repositories.

## Workflow follow-up

- The operator pushes `main` in every touched repository. They also push `adopt-sandbox-ref-28` in `antigravity-container`.
- The operator reruns `--container-setup` for Antigravity on the Linux hosts and on Windows.
- Archive this change with spec sync.
