# Tasks

## 1. Adopt sandbox-ref-12

- [x] 1.1 From claude-container, run `python3 -I tools/propagate.py
  ../antigravity-container sandbox-ref-10 sandbox-ref-12` (dry run). Verify
  that it lists 21 modified shared files, nothing added, removed or "not
  adopted", three documents, and `REFERENCE_COMMIT` `fd196c9`.
- [x] 1.2 Stash the change directory, run `--apply`, and restore the stash
  on `adopt-sandbox-ref-12`. Verify:
  - the stash list is empty;
  - `git diff --name-only` lists only the shared files, the manifest and
    the three documents;
  - `python3 -m unittest tests.test_reference_copy tests.test_alignment`
    passes.

## 2. Wrapper test fixtures

- [x] 2.1 In `tests/test_wrapper.py`, copy `network/agent_budgets.py` into
  the fixture. In `tests/fake_podman.py`, answer
  `{{.Host.CgroupControllers}}` from `FAKE_CONTROLLERS`, by default
  `[cpu memory pids]`. Verify that the full unit discovery passes on the
  adopted shared files.

## 3. Launcher

- [x] 3.1 Accept a `unix://` host socket report (design decision 2). Add
  tests:
  - `true unix:///host/podman.sock` binds `/host/podman.sock`;
  - `unix://relative`, `unix://` and `unix:///` are rejected before image
    operations.

  Verify that they pass.
- [x] 3.2 Make budgets follow the delegated controllers (design decision 3),
  including the help text. Make the fake inspection default unrequested
  values to `0`. Add tests:
  - every subset of controllers;
  - an unverifiable list, rejected before state;
  - an unenforced budget present, and an enforced budget missing.

  Verify that they pass, together with the existing budget tests.
- [x] 3.3 Replace `--read-only-tmpfs=false` with the `/run/secrets`, `/dev`,
  `/dev/pts` and `/dev/shm` mounts (design decision 4), and update the
  existing assertion. Add a test asserting the four mounts and the
  unchanged temporary mounts:
  - in agy and shell mode, with and without delegation;
  - in offline and provider mode;
  - on the provider proxy, the secrets mask and its budgets.

  Verify that they pass.
- [x] 3.4 Add the `build-ca` secret to the build and `!podman-build-secret*`
  to `.containerignore` (design decision 5). Add tests with and without
  trust, for `--container-build` and for a missing image. Verify that they
  pass.
- [x] 3.5 Run `bash -n antigravity-container.sh container-entrypoint.sh
  tests/run-runtime.sh tests/image-smoke.sh` and the full wrapper suite.
  Verify that both pass.

- [x] 3.6 Remove the explicit `/dev` tmpfs and `devpts` mounts (revised design
  decision 4), keeping the read-only `/dev/shm` and `/run/secrets` masks.
  Update the wrapper mount assertions. Add a runtime test that opens a
  pseudo-terminal inside a session. Verify that the wrapper suite and the
  new runtime test pass.

## 4. Runtime image recipe

- [x] 4.1 Port the HTTPS bootstrap into the first `RUN`, add
  `mkdir -p /workspace`, and give the agy download the optional
  `build-ca` secret through `--cacert` (design decision 6). Extend
  `tests/test_image_pins.py` with the transport, toolchain, workdir and
  artifact-download checks and their mutations. Verify that
  `python3 -m unittest tests.test_image_pins` passes and that each
  mutation is rejected.
- [x] 4.2 Build the image with the wrapper's arguments as
  `localhost/antigravity-cli:adopt-ref-12`. Verify:
  - every Debian `URIs:` line is `https://`;
  - no bootstrap bundle or `/tmp/agy` remains;
  - `agy --version` and `openspec --version` report the pinned versions;
  - `/workspace` is in the exported layer, and a `keep-id` container
    without `--workdir` leaves its time unchanged.

## 5. Documentation

- [x] 5.1 Update `README.md` and `AGENTS.md`:
  - conditional budgets, with notices and the exhaustion risk;
  - the `/run/secrets` mask;
  - the `noexec` `/dev`, `/dev/pts` and read-only `/dev/shm`;
  - HTTPS-only image fetches on port 443;
  - the `build-ca` secret for apt and the agy download;
  - the image working directory.

  Verify that the documented paths and variables match the launcher and
  `--container-help`.

## 6. Validation and publication

- [x] 6.1 Run the full unit discovery on executable, private, native
  temporary storage. Verify that there are no failures, apart from known
  timing-sensitive tests that pass on a rerun, which are recorded as such.
- [x] 6.2 With the image from 4.2, run `bash tests/run-runtime.sh` with
  `--shared`, `--setup`, `--setup-runtime`, `--qualification`, `--guard`,
  `--network` and the default mode (`test_runtime.py`). Verify that every
  mode passes, or record it as unavailable on this host.
- [x] 6.3 Fill in the tool's validation-record template in
  `docs/validation.md` with the results of 6.1–6.2, the adaptations and the
  image ID. Record the operator setups as pending. Verify that the parity
  table hash matches claude-container's.
- [x] 6.4 Commit on `adopt-sandbox-ref-12` with the tool's message and the
  co-author trailer, merge it into `main` with `--no-ff`, and verify that
  `git log --oneline -3` shows the merge.

## Workflow follow-up

- The operator pushes Antigravity `main`, then runs `--container-setup`
  (refresh approved) and a session on this host, the Rocky Linux 9 lab host
  and the newer WSL host. The results are added to `docs/validation.md`.
- Sync the delta specs and archive this change after review.
- Fix the same PTY defect (explicit `devpts` with `ptmxmode=000`) in the
  Claude reference launcher and in Codex, OpenCode and Pi, each in its own
  change, with the same runtime PTY test.
