# Tasks

## 1. Adopt `sandbox-ref-24`

- [x] 1.1 Commit this change directory on `main`. Save the current `antigravity-container.sh`, `tests/test_wrapper.py` and `tests/fake_podman.py` outside the repository as the old-test baseline. From `sandbox-container`, run `python3 -I tools/propagate.py ../antigravity-container sandbox-ref-21 sandbox-ref-24` (dry run), then `--apply`. Add `launcher` to `CLOSED_DIRECTORIES` in `tests/test_reference_copy.py`. Verify that:
  - the plan lists exactly the files in design "Context";
  - the tool switched to `adopt-sandbox-ref-24`.
- [x] 1.2 Fix the parity table in `docs/network-contract.md` by hand (design decision 7). Verify that the reference, Claude and Codex rows equal those in their repositories, and the OpenCode and Pi rows equal theirs.

## 2. Launcher on the shared core

- [ ] 2.1 Add `native.exec` and `native.exec_tmp` to `agent/profile.json`, write `agent/launcher.sh` (design decision 2) and replace `antigravity-container.sh` with the reference entry script. Verify that:
  - `python3 -m unittest tests.test_alignment tests.test_agent_profile tests.test_launcher` passes in the disposable test container;
  - `bash antigravity-container.sh --container-help` prints the provider disclosure with the `google-account` and `gemini-api` hosts and the `ANTIGRAVITY_YOLO` and `GEMINI_API_KEY` entries;
  - `diff <(sed s/sandbox-container/antigravity-container/g ../sandbox-container/sandbox-container.sh) antigravity-container.sh` is empty.
- [ ] 2.2 Run the saved `tests/test_wrapper.py` with its saved fake engine against the new entry script and core in the disposable test container. Adapt only its harness (design decision 4). Classify every failing case as (a) visible change, (b) lost behavior or (c) Antigravity-only behavior, and resolve the 32 "to verify at adoption" cases by name. Record the table in a scratch note for task 4.2. Verify that every failing case has exactly one outcome.
- [ ] 2.3 If task 2.2 found any (b), pause this change and ask the user. Fix each behavior with a shared case in `sandbox-container` through its own reference change and tag, then propagate to that tag and rerun task 2.2. Update this change's artifacts to name that tag. Verify that a rerun of task 2.2 finds no (b). If task 2.2 found none, mark this task done with the note "no lost behavior".

## 3. Antigravity tests and documentation

- [ ] 3.1 Rewrite `tests/test_wrapper.py` with the shared `tests/fake_podman.py` and the real agent part (design decision 5). Verify that `python3 -m unittest tests.test_wrapper` passes in the disposable test container.
- [ ] 3.2 Update the wrapper-owned runtime tests (design decision 6): `tests/run-runtime.sh`, `tests/test_runtime.py`, `tests/test_network_runtime.py`, `tests/test_setup_runtime.py` and `tests/test_setup_wrapper.py`. Verify that `python3 -m unittest tests.test_setup_wrapper` passes in the disposable test container and that `bash -n tests/run-runtime.sh` succeeds.
- [ ] 3.3 Update the README, `docs/setup.md`, `docs/network-contract.md` and `AGENTS.md` (design decision 7). Verify that `grep -rn "dedicated home\|previous networking\|DEDICATED_HOME\|no-cache\|first handled" --exclude-dir=openspec --exclude=validation.md --exclude=CHANGELOG.md .` finds nothing stale.

## 4. Integration

- [ ] 4.1 Rebuild the Antigravity test image with `--container-build`. Then run:
  - the unit discovery in the disposable test container;
  - `bash tests/run-runtime.sh` with `--wrapper`, `--shared`, `--setup`, `--setup-runtime`, `--qualification`, `--network` and `--guard`, and the default mode;
  - `git diff --check`.

  Verify that all pass. A real-runtime failure that the old-test gate did not show is classified as in task 2.2, asking the user for any case not already covered by a contract decision.
- [ ] 4.2 Add the `sandbox-ref-24` adoption section to `docs/validation.md`, starting from the tool's template. It holds every result and the old-test classification table from task 2.2. Commit with the tool's message and merge into `main`. Verify that `tests/test_reference_copy.py` passes on `main` with host Python next to the `sandbox-container` checkout, with the sibling check not skipped.
- [ ] 4.3 Copy the Antigravity parity row into `sandbox-container`, `claude-container` and `codex-container` and commit each on `main`. Verify that the reference, Claude, Codex and Antigravity rows are identical in the four repositories.

## Workflow follow-up

- The operator pushes `main` in the four repositories and runs `--container-setup` for Antigravity on this host, the Rocky Linux 9 lab host and the newer WSL host, then checks an Antigravity session in provider mode.
- Archive this change with spec sync. This creates `openspec/specs/shared-launcher/spec.md` in this repository.
- Pi adopts `sandbox-ref-24` in its own change, and OpenCode after it.
