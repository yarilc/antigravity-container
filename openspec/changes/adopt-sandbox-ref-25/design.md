# Design

## Context

Antigravity adopted `sandbox-ref-24` on 2026-11-17. The `tools/propagate.py` dry run from `sandbox-ref-24` to `sandbox-ref-25` (2026-11-18) gives this plan:

- **Update:** `launcher/core.sh`, `setup/setup.py`, `tests/test_launcher.py`, `tests/test_setup.py`.
- **Rewrite:** `AGENTS.md` (1), `docs/setup.md` (1), `docs/network-contract.md` (7).
- **Move:** the manifest to `sandbox-ref-25` (`6bed770`).

The core and setup changes only add checks on the host socket path that a delegated service reports; Antigravity's agent part does not touch delegation. The shared cases `test_reported_host_socket_must_be_a_socket_when_visible` and the extended `test_socket_validation_rejects_rootful_and_cr_responses` arrive with the tag.

The old Antigravity case `test_complete_socket_response_required` (`true /`, `true unix:///`), recorded as a visible change in the `sandbox-ref-24` adoption, is now covered by the shared case `test_reported_host_socket_must_be_a_socket_when_visible`; the validation record says so.

## Goals / Non-Goals

**Goals:**
- Antigravity runs on the `sandbox-ref-25` core and setup with no Antigravity-specific change.
- The parity tables of the reference and the adopted wrappers state the same rows.

**Non-Goals:**
- Pi and OpenCode, which adopt `sandbox-ref-25` in their own full adoptions.

## Decisions

1. **Adopt with the tool.** Commit this change directory on `main`, then `--apply`, which creates `adopt-sandbox-ref-25`. The tool rewrites tag references in the parity table; check every row by hand afterwards.

2. **No old-test gate.** The core gains two refusals and the shared tests that cover them arrive with the tag. Antigravity's own tests run unchanged; a failure there pauses the change.

3. **Parity rows.** The reference row names `sandbox-ref-25`; Antigravity's row says it adopted `sandbox-ref-25` with this adoption's runner results; the other rows are copied from their repositories. After the merge, Antigravity's row is copied into `sandbox-container` and every other wrapper that already runs on the shared core, so the rows stay identical.

4. **Validation scope.** The installed core and setup change, so validation covers what they touch:
   - `python3 -m unittest tests.test_reference_copy tests.test_alignment` with host Python next to the `sandbox-container` checkout, with the sibling check not skipped;
   - the unit discovery in the disposable test container;
   - `bash tests/run-runtime.sh` with `--wrapper`, `--setup` and `--setup-runtime`, and the default runtime run;
   - `git diff --check`.

## Risks / Trade-offs

- **[Installed qualification reports no longer match]** → The operator reruns `--container-setup` on the three hosts after the merge.
- **[A containerized caller still trusts an invisible reported path]** → Documented limit of the reference; delegation already grants equivalent authority through the API.
