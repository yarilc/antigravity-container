# Tasks

## 1. Launch engine and endpoint preconditions

- [x] 1.1 Validate complete launch-engine output and query failures in `antigravity-container.sh`; extend fake-engine tests for empty, missing, extra, invalid-boolean, rootful, non-Linux, and multiline responses, including an extra blank record, and verify no image/build/create calls occur for failures in normal and rebuild modes.
- [x] 1.2 Reject `unix:///`, relative Unix endpoints, named connections, and unsupported transports before any engine query; verify logged calls remain empty, while valid local and explicit Unix remote-service responses continue to pass.
- [x] 1.3 Update README launch prerequisites and diagnostics to describe strict response and endpoint checks; verify examples match supported local and Unix-service launch behavior and retain wrapper-help side-effect tests.

## 2. Exact delegation and strict socket checks

- [x] 2.1 Replace delegation boolean parsing with exact `1` selection and explicitly unset disabled `CONTAINER_HOST`; add CLI/shell tests crossing YOLO with unset, empty, `0`, `1`, `true`, `yes`, `01`, `maybe`, and whitespace variants, verifying non-`1` inputs skip delegation checks and omit the socket mount without errors.
- [x] 2.2 Require absolute selected socket paths before canonicalization and validate complete delegation responses; extend fake-service controls and tests for socket precedence, symlinks, relative/missing/inaccessible sockets, failed queries, missing/rootful results, relative reported paths, extra records, and preserved host paths with spaces, checking failure before image operations including explicit rebuilds.
- [x] 2.3 Verify launch and delegation engines stay independent with distinct fake endpoints and real rootless delegated child-container binds; add a runtime fixture supplying image/engine `CONTAINER_HOST` defaults and assert the variable is absent in disabled containers while the wrapper retains its launch connection.
- [x] 2.4 Update wrapper help and README permissions/environment/migration sections to distinguish exact delegation from YOLO booleans; verify four permission examples remain accurate and `true`/`yes` migration to `1` is explicit.

## 3. Private state ordering and umask scope

- [x] 3.1 Move state creation, canonicalization, ownership, access, and mode checks before both image paths and isolate `umask 077` to creation; add regressions for creation failure, resolution failure, wrong owner, inaccessible or insecure state, symlink resolution, and filesystems not enforcing modes, verifying no image operations occur on failure.
- [x] 3.2 Update image-error expectations for already-created private state and add fake-engine observation of inherited wrapper umask under at least `022` and `002`; verify state stays private and later engine operations retain the original mask.
- [x] 3.3 Add controlled real-container file-mode checks for shell, API entrypoint using a harmless test `agy` probe, and account-helper execution with dummy passphrases; verify actual modes against the observed container umask and confirm account runtime privacy without paid model requests.
- [x] 3.4 Update README state/permission descriptions to explain early creation and independent runtime modes; verify no recursive permission repair or container-wide umask promise is documented.

## 4. Explicit temporary storage

- [x] 4.1 Add `--read-only-tmpfs=false` and the design's explicit `/tmp`, `/run`, and `/var/tmp` options; update wrapper argument tests and direct keyring fixtures to verify exact limits, executable `/tmp`, `noexec` on `/run` and `/var/tmp`, and required directory modes.
- [x] 4.2 Extend runtime checks to inspect actual mount properties and limits, write to all three paths, execute a probe from `/tmp`, reject execution from `/run` and `/var/tmp`, and confirm files disappear after container replacement; verify image smoke and private keyring persistence/unlock tests pass under this layout.
- [x] 4.3 Update README mount documentation with explicit paths, limits, and execution policies; record observed mount/keyring/file-mode results and environment limitations in `docs/validation.md`, distinguishing new evidence from earlier runs.

## 5. Diagnostic cleanup reliability

- [x] 5.1 Track `create_error` in EXIT cleanup from before allocation, retain prompt normal-path removal, and preserve status and diagnostics; add synchronized fake-engine tests using an isolated temporary directory for success, create failure, all collision retries exhausted, unexpected command failure, and handled signals after allocation, verifying no diagnostic files remain and unrelated containers are untouched.
- [x] 5.2 Document temporary diagnostic cleanup and its handled-exit scope in the README lifecycle description; verify the wording agrees with signal regressions and does not promise cleanup after SIGKILL or host failure.

## 6. Integration acceptance

- [x] 6.1 Run `python3 -m unittest discover -s tests -p test_wrapper.py -v`, Bash syntax checks, and ShellCheck on affected scripts; verify all checks pass, including forwarding, stdin/TTY, worktrees, collision handling, application exit 125, and signal cleanup regressions.
- [x] 6.2 Run `bash tests/run-runtime.sh` against real rootless Podman with native Linux private state; verify mount boundaries, state reuse, explicit temporary storage, measured modes, disabled environment clearing, keyring lifecycle, and delegated child binds, and update `docs/validation.md` with exact results and any blocked checks without claiming unexecuted passes.
- [x] 6.3 Run `openspec validate harden-container-launch-preflight --strict` and review all nine TODO items against the final code, tests, docs, and deltas; verify each item has implementation and acceptance evidence before marking implementation complete.
