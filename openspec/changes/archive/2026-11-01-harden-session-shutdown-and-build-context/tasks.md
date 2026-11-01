# Tasks

## 1. Slash-only launch endpoint validation

- [x] 1.1 Update Unix launch-path validation to require an absolute path with a non-slash component; extend wrapper regressions for `unix:///`, `unix:////`, longer slash-only paths, relative paths, and valid absolute socket paths, verifying invalid endpoints produce no Podman calls in normal and rebuild modes.
- [x] 1.2 Update README launch preflight guidance with slash-only rejection and valid endpoint examples; verify documented behavior matches the endpoint tests and existing explicit Unix service support.

## 2. Owned creation and interrupted startup

- [x] 2.1 Add private session bookkeeping, asynchronous `create --cidfile`, and validated CID ownership independent of stdout; extend fake-engine support and regressions for valid/missing/invalid IDs, ordinary creation, collisions, retry exhaustion, and failed collision inspection, verifying no unrelated container is removed and diagnostic files remain private and are cleaned up.
- [x] 2.2 Record first-signal status during creation and bound interrupted create completion and local-client cancellation, including a final CID read after cancellation; add synchronized TERM/INT/HUP tests for successful CID publication before/after the signal, a stalled client with and without an owned ID, repeated signals, and unresolved ownership, verifying no attach/retry after interruption and actionable diagnostics without name-based deletion.
- [x] 2.3 Document interrupted creation, CID-scoped cleanup, and uncertain engine-side outcomes in README lifecycle guidance; verify descriptions match the startup race and failure tests without promising removal during engine failure.

## 3. Bounded attached shutdown and cleanup

- [x] 3.1 Add the checked coreutils `timeout` prerequisite and first-signal lifecycle handling with `--sig-proxy=false`; use bounded forwarding/removal calls, five-second application grace, finite TERM/KILL client termination and reaping, and cleanup status preservation, verifying wrapper-help remains usable without Podman or timeout and normal sessions have no imposed runtime limit.
- [x] 3.2 Extend fake-session regressions across CLI/shell and TERM/INT/HUP, including ignored TERM, stalled/failed forwarding, stalled/failed removal, a client ignoring TERM, and repeated signals; assert actual finite deadlines with a conservative combined 30-second ceiling, original signal status, only-owned cleanup, and no surviving fake child processes.
- [x] 3.3 Add normal-exit tests crossing application statuses 0, 23, and 125 with successful, failed, and timed-out removal; verify diagnostics identify known owned containers, primary status is preserved, application 125 never retries create, and temporary bookkeeping is removed on every handled exit.
- [x] 3.4 Add a real rootless runtime shutdown check with a disposable shell process ignoring TERM and an unrelated sentinel container; verify bounded wrapper exit, removal of the owned container, and survival of the unrelated container, with cleanup of test resources.
- [x] 3.5 Update wrapper help and README host requirements/lifecycle guidance with coreutils timeout, signal statuses, per-phase deadlines, first-signal precedence, forced removal, and manual recovery; record observed shutdown/race results and environment limits in `docs/validation.md` and check documentation against both regression and runtime evidence.

## 4. Default-deny build context

- [x] 4.1 Replace `.containerignore` exclusions with a deny-all policy and root-only exceptions for Containerfile, entrypoint, keyring helper, and `.containerignore`; verify both production helper COPY instructions remain supported without changes to image installation or runtime helper behavior.
- [x] 4.2 Add a real rootless Podman build fixture using the actual ignore file and helper sources, dummy unknown/config/credential/state inputs, and nested same-named files; assert exact four-file `COPY .` inventory plus both helper destinations/content/executable installation, and verify fixture images and contexts are removed afterward.
- [x] 4.3 Update README build-input documentation and `docs/validation.md` with the allowlist, deliberate procedure for new local inputs, and observed fixture result; verify descriptions distinguish `.containerignore` build isolation from Git ignore rules.

## 5. Integration acceptance

- [x] 5.1 Run the full wrapper suite with `python3 -m unittest discover -s tests -p test_wrapper.py -v`, Bash syntax checks, and ShellCheck for affected scripts; verify passing regressions for forwarding, stdin/TTY, exact delegation, state/umask, naming, diagnostics, and bounded lifecycle behavior, adjusting outer test deadlines only where the defined shutdown budgets require it.
- [x] 5.2 Run `bash tests/run-runtime.sh` against real rootless Podman with native private state; verify the new shutdown/context tests and existing keyring/D-Bus persistence, wrong-password handling, API-provider diagnostics, mounts, worktrees, and child binds pass, and record exact results without claiming unexecuted account/model acceptance.
- [x] 5.3 Run `openspec validate harden-session-shutdown-and-build-context --strict` and `git diff --check`; review all three TODO items against code, tests, docs, and deltas and verify the preexisting `.gitignore` edits remain untouched before marking implementation complete.
