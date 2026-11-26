# Tasks

Verification for this change uses the current development environment.
Record the outcome of each check that can run and the reason for any
environment-dependent failure or unavailable check. Production validation
and any changes it identifies follow closure.

## 1. Adopt the shared reference

- [x] 1.1 Run `python3 -I tools/propagate.py ../antigravity-container sandbox-ref-28 sandbox-ref-36`
  from `sandbox-container` against a clean target, then rerun with `--apply`.
  Preserve the planning artifacts when preparing the clean worktree. Verify the
  plan against the design's file counts and review lines, check the resulting
  manifest names `ce2c9d28873838a4ac541da34edaf7d8b5264be4`, and run
  `python3 -B -m unittest tests.test_reference_copy tests.test_alignment`.
- [x] 1.2 Update `tests/run-runtime.sh` to select the test runner's Unix socket
  from `CONTAINER_HOST` or its default runtime directory. Drop the old
  delegation socket override. Align the `--shared` list with the tagged
  test manifest, including the new engine and toolchain modules and the
  Windows bootstrap and enter checks. Keep Antigravity's image-pin checks
  and guarded fixtures. Verify with `bash -n tests/run-runtime.sh` and
  compare the selected modules with `tests/test_alignment.py`.

## 2. Update Antigravity launch and setup acceptance

- [x] 2.1 In `tests/test_wrapper.py`, replace the YOLO-by-delegation grid with
  approval-bypass checks in shared and isolated state. Remove the synthetic
  delegation socket and keep the help, executable entrypoint, shell,
  settings and policy credential assertions. Let the tagged synthetic
  installation answer `qualification-input` in the probe test. Confirm the
  probe's argument assertions and run locally available wrapper checks,
  including help and the exact legacy opt-in refusal.
- [x] 2.2 In `tests/test_setup_wrapper.py` and `tests/test_setup_runtime.py`,
  remove the delegation answer and update setup assertions and saved
  preferences for schema 3. Use a private `XDG_RUNTIME_DIR` in synthetic
  setup tests. In real setup tests, pass a CA fixture under native
  host-visible storage, keep the fixture's proxy identity interception
  scoped to image ID lookups, and track the disposable runtime, proxy,
  guard-toolchain and engine tags owned by each test release. Verify the
  modules parse and run the setup fixtures that the development environment
  supports. Preserve the account and Gemini transcripts, failed-update
  rollback and image-tag checks in the production suite.
- [x] 2.3 Update `README.md`, `AGENTS.md`, `docs/setup.md` and the current
  contract prose in `docs/network-contract.md`. Explain the launch service,
  the removal diagnostic, schema 3 setup and the Windows entry. Keep the
  authentication and state instructions for `agy`. Verify that old host
  delegation examples are replaced by the setup and migration flows, and
  compare the new instructions with wrapper help and the setup transcripts.

## 3. Update session engine and containment acceptance

- [x] 3.1 In `tests/test_runtime.py`, replace the delegated-child workspace
  case with a workspace bind through the private engine and keep the
  caller-owned file check. Assert that sessions with no engine clear
  both inherited connection variables. Drop delegated variants of the
  hardening and tool-compatibility tests and retain the `agy`, Bubblewrap
  and temporary-mount checks. Port the reference's library-image,
  no-engine, concurrent engine and process-budget cases using Antigravity's
  engine and pinned sample image. Confirm test discovery and the assertions
  for engine isolation, inherited connection variables and the host socket.
- [x] 3.2 In `tests/test_network_runtime.py`, include `setup/engine.py` and its
  `INPUTS` in the fixture installation and copy its prepared seccomp
  profile when exercising the engine. Replace delegation success or mode
  conflict expectations with exact legacy opt-in refusal and ignored
  non-enabling values. Add the offline engine containment, offline
  image-recipe check and proxy process-budget case from the reference or
  an adopting wrapper. Confirm test discovery and retention of the
  credential-free Gemini tool and policy cases. Run available network unit
  tests in the development environment.
- [x] 3.3 Align Antigravity's runtime and network budget assertions with the
  host's cgroup controller selection and effective rlimit fallback. Apply
  the tagged terminal-availability probe to guarded terminal cases,
  including the `agy` TUI case, and keep pipe cases independently runnable.
  Give interrupted fixture processes bounded waits and owned cleanup.
  Run locally available budget and qualification tests, and record the
  disposition of `--guard`, `--network` and default runtime execution.
- [x] 3.4 Document the container test workflow and library image recipes in
  `README.md` and `docs/setup.md`. Include catalog recipes, Windows drive
  translation, image store scope, engine image preparation, read-only
  `/sys`, and nested systemd prerequisites. Verify the examples against
  the tagged command help and compare the image recipe with the runtime
  fixture and locally runnable recipe checks.

## 4. Verify and record the adoption

- [x] 4.1 Run the reference-copy and alignment tests, Bash and Python
  syntax checks, `git diff --check` and
  `openspec validate adopt-sandbox-ref-36 --strict`. Record the status of the
  pinned ShellCheck and PowerShell checks.
  Preview the spec merge in a disposable copy and verify that the obsolete
  Podman-access capability is removed, the session engine capability has
  its 20 requirements, and Antigravity's YOLO and executable temporary
  storage contracts survive. Refresh the `## Purpose` paragraphs of the
  existing `workspace-mounts` and `toolchain-library` specs during
  implementation so their descriptions refer to the private session engine.
- [x] 4.2 Generate the adoption checklist for Antigravity and run the local
  synthetic checks supported here. Confirm test discovery and record
  real-engine availability and runner preflight results. Keep the production
  checklist available for follow-up.
- [x] 4.3 Record the tag, available local results, environmental exclusions
  and pending production checks in `docs/validation.md`. Update Antigravity's parity row in
  `docs/network-contract.md` with the measured evidence and preserve prior
  history. Verify that synthetic provider checks, any authenticated
  checks actually performed, and the Windows post-release check have
  individually accurate statuses.

## Workflow follow-up

- Integrate and archive the Antigravity change through the repository's
  workflow. Propagate the Antigravity parity row to the reference and the
  sibling wrappers through the separate cross-repository parity step.
- After closure, run the production checklist on the supported Linux or
  WSL host with
  `bash tools/adoption-run.sh ../antigravity-container sandbox-ref-28 sandbox-ref-36`
  from `sandbox-container`. Record image identities and capability label,
  runtime suites and environment-dependent skips.
- After closure, rerun managed setup on Windows PowerShell 5.1 and run
  `.\tools\windows-validate.ps1 -Checkout <the Windows checkout>` from
  `sandbox-container`. Record the actual check results, including refusal
  of saved delegation and a session with library images.
- Open separate changes for defects found in production validation.
