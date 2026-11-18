# Tasks

## 1. Adopt `sandbox-ref-25`

- [ ] 1.1 Commit this change directory on `main`. From `sandbox-container`, run `python3 -I tools/propagate.py ../antigravity-container sandbox-ref-24 sandbox-ref-25` (dry run), then `--apply`. Verify that:
  - the plan lists exactly the files in design "Context";
  - the tool switched to `adopt-sandbox-ref-25`.
- [ ] 1.2 Fix the parity table in `docs/network-contract.md` by hand (design decision 3): the reference row names `sandbox-ref-25` and the other wrappers' rows equal those in their repositories. Leave Antigravity's row for task 2.2. Verify that `python3 -m unittest tests.test_reference_copy tests.test_alignment` passes with host Python next to the `sandbox-container` checkout, with the sibling check not skipped.

## 2. Validation and integration

- [ ] 2.1 Run the unit discovery in the disposable test container, `bash tests/run-runtime.sh` with `--wrapper`, `--setup` and `--setup-runtime`, the default runtime run, and `git diff --check` (design decision 4). Verify that all pass. If a Antigravity test fails, pause the change.
- [ ] 2.2 Set Antigravity's parity row to "Adopted `sandbox-ref-25`" with the results of task 2.1. Add the `sandbox-ref-25` adoption section to `docs/validation.md`, starting from the tool's template, with every result of task 2.1 and the note that the old case `test_complete_socket_response_required` is now covered by a shared case. Commit with the tool's message and merge into `main`. Verify that `tests/test_reference_copy.py` passes on `main` with host Python.
- [ ] 2.3 Copy Antigravity's parity row, and the reference row naming `sandbox-ref-25`, into `sandbox-container` and every other wrapper already on the shared core, and commit each on `main`. Verify that the reference, Claude, Codex and Antigravity rows are identical in those repositories.

## Workflow follow-up

- The operator pushes `main` in every touched repository and runs `--container-setup` for Antigravity on this host, the Rocky Linux 9 lab host and the newer WSL host.
- Archive this change with spec sync.
