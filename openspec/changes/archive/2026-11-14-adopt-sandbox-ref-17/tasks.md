# Tasks

## 1. Adopt sandbox-ref-17

- [x] 1.1 On the paused branch `adopt-sandbox-ref-16`, save the wrapper-owned
  changes as a patch in the scratchpad (design decision 1): every changed or
  untracked file except the eight shared files,
  `tests/test_reference_copy.py`, `AGENTS.md`, `docs/setup.md`,
  `docs/network-contract.md` and the change directory. Then stash the change
  directory, discard the branch, and switch to `main`. Verify that:
  - the patch lists `antigravity-container.sh`, `tests/fake_podman.py`,
    `tests/test_wrapper.py`, `tests/test_runtime.py`,
    `tests/test_network_runtime.py` and `tests/run-runtime.sh`;
  - `main` is clean apart from the stash;
  - `adopt-sandbox-ref-16` no longer exists.
- [x] 1.2 From claude-container, run `python3 -I tools/propagate.py
  ../antigravity-container sandbox-ref-12 sandbox-ref-17` (dry run), then
  `--apply`. Restore the stash on `adopt-sandbox-ref-17` and apply the patch
  after `git apply --check`. Verify that:
  - the dry run lists six modified and two added shared files, nothing
    removed or "not adopted", and commit `a23f155`;
  - the stash list is empty;
  - `python3 -m unittest tests.test_reference_copy tests.test_toolchains
    tests.test_alignment` passes on private temporary storage, including the
    agent-identifier scans and the profile variables.

## 2. Launcher, test first

- [x] 2.1 In `tests/test_wrapper.py`, give the setup a synthetic host home and
  `self.library`, add the cases of design decision 4, and install `setup/`
  and `Containerfile` in the restricted fixture. Add the `.Config.Env`
  answer to `tests/fake_podman.py`. The settings case checks only
  `AGY_CLI_DISABLE_AUTO_UPDATE`; `DBUS_SESSION_BUS_ADDRESS` is the shared
  module's (design decision 3). Verify that the new cases fail on the
  launcher of `main`.
- [x] 2.2 Port design decisions 2 and 3 to `antigravity-container.sh`,
  including the help text for `--container-toolchain`,
  `ANTIGRAVITY_CONTAINER_TOOLCHAINS` and
  `ANTIGRAVITY_CONTAINER_TOOLCHAINS_DIR`. Verify that:
  - `bash -n` passes on `antigravity-container.sh`;
  - `tests/test_wrapper.py` and `tests/test_alignment.py` pass on private
    temporary storage.

  The launcher comment on the toolchain environment states only the
  `--env` order. Record each existing fixture that needs an adaptation.
- [x] 2.3 Give `tests/run-runtime.sh` the private tmpfs and
  `SANDBOX_TEST_TMPDIR`, and create the `tests/test_wrapper.py` base there
  (design decision 5). Verify that `bash tests/run-runtime.sh --wrapper`
  passes.

## 3. Real-engine checks

- [x] 3.1 Give `tests/test_runtime.py` a private home per test on the native
  state root, port the runtime cases including the Antigravity settings
  check for `AGY_CLI_DISABLE_AUTO_UPDATE`, and add the live add to `tests/test_network_runtime.py`, whose
  installation gains `setup/` and `Containerfile`. With the current
  Antigravity setup image as `ANTIGRAVITY_CONTAINER_IMAGE`, verify that
  `bash tests/run-runtime.sh` and `bash tests/run-runtime.sh --network -k
  toolchain` pass.

## 4. Documentation

- [x] 4.1 Add the README "Toolchains" section (design decision 6) and update
  the help-related README parts ("Environment"), `AGENTS.md` and
  `docs/setup.md`. Verify that every `ANTIGRAVITY_CONTAINER_TOOLCHAINS*`
  variable and every `--container-toolchain` operation appears in both the
  help text and the README.

## 5. Validation and publication

- [x] 5.1 Run the full unit discovery on executable, private, native
  temporary storage. Verify that there are no failures, apart from known
  timing-sensitive tests that pass on a rerun, which are recorded as such.
- [x] 5.2 Run `bash tests/run-runtime.sh` with every mode the tool listed and
  the default mode. Verify that each passes, or record it as unavailable.
- [x] 5.3 Fill in the tool's validation-record template in
  `docs/validation.md` with the results of 1.2–5.2, the fixture adaptations,
  the requalification note and the operator checks as pending. Verify that:
  - the parity table rows match claude-container's;
  - `git diff --check` is clean;
  - `openspec validate adopt-sandbox-ref-17 --strict` passes.
- [x] 5.4 Commit on `adopt-sandbox-ref-17` with the co-author trailer, merge
  it into `main` with `--no-ff`, and verify that `git log --oneline -3` shows
  the merge.

## Workflow follow-up

- The operator pushes Antigravity `main` and reruns `--container-setup` on
  the three hosts. They check `java -version` in an Antigravity session with
  the Temurin 21 toolchain and run `--container-toolchain verify java21`.
  The results are added to `docs/validation.md`.
- Sync the delta spec and archive this change.
