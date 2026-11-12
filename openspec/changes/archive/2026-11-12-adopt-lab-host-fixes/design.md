# Design

## Context

Antigravity `main` (`91f2740`) pins `sandbox-ref-10`. The dry run of
`tools/propagate.py ../antigravity-container sandbox-ref-10 sandbox-ref-12`
reports:

- the same 21 modified shared files as for Pi;
- nothing added, removed or "not adopted";
- three documents (no `README.md` reference);
- the runner modes `--shared`, `--setup`, `--setup-runtime`,
  `--qualification`, `--guard` and `--network`.

The Codex, OpenCode and Pi ports set the pattern. Antigravity differs in
these points:

- **Engine and socket:**
  - `capture_engine_info` rejects multiline responses;
  - the delegation query returns a single record
    `true <path>`, matched by `^true[[:blank:]]+(/.+)$` (around line 368),
    so a `unix://` value fails the pattern before any prefix could be
    removed.
- **Build:**
  - one build call (around line 471), with `--no-cache` on explicit
    rebuilds;
  - `ca_bundle` is resolved earlier (around line 396), so no reordering is
    needed;
  - `runtime_build` is `recipe`.
- **Budgets:**
  - `"--memory=$memory_bytes" "--cpus=$cpu_text" "--pids-limit=$pids_limit"`
    in `container_args`;
  - the inspection requires the exact triple (around line 819);
  - the help text states that budgets require all three controllers.
- **Mounts:**
  - `--read-only-tmpfs=false`;
  - executable `/tmp` 512 MiB, `noexec` `/run` 32 MiB and `/var/tmp`
    512 MiB;
  - a 64 MiB home tmpfs in shared-state mode.
- **Recipe:**
  - the first `RUN` runs apt `update` and `install`, then `npm install` and
    the cleanup;
  - a second `RUN` downloads the agy release with `curl`, checks it with
    `sha512sum` and installs it;
  - then `COPY` and `RUN chmod`, and finally `WORKDIR /workspace` and
    `ENTRYPOINT`. `/workspace` is therefore in no layer.
- **`.containerignore`** uses unanchored patterns.
- **Tests:**
  - `tests/fake_podman.py` derives the agent inspection from the last
    `create`, but fails on a missing `--memory=` or `--cpus=`;
  - the wrapper fixture (around line 825 of `tests/test_wrapper.py`) lacks
    `network/agent_budgets.py`;
  - `test_runtime.py` and `run-runtime.sh` honor
    `ANTIGRAVITY_CONTAINER_IMAGE`;
  - `tests/image-smoke.sh` exists.

## Goals / Non-Goals

**Goals:**
- Antigravity adopts `sandbox-ref-12` byte for byte, with launcher and
  recipe behavior equivalent to the other wrappers.
- Its image needs no engine workdir creation.

**Non-Goals:**
- The Google account and Gemini API profiles and policy hosts.
- The pending authenticated Gemini API-key check.

## Decisions

1. **Single branch with stash**, as in the other wrappers: `--apply`
   creates `adopt-sandbox-ref-12`, the change directory is stashed around
   it, and one `--no-ff` merge follows.

2. **Socket URL.** Widen the pattern to `^true[[:blank:]]+(unix://)?(/.+)$`
   and take the path from group 2. `unix://relative`, `unix://` and
   `unix:///` still fail: the first two do not match, and the third gives
   `/`, which the existing "beyond /" rule rejects. If no such rule exists
   here, add one.

3. **Budgets.** Use the reference block with the `antigravity-container:`
   prefix and `capture_engine_info`:
   - query and validate `{{.Host.CgroupControllers}}` after the
     launch-engine checks;
   - `budget_args`, with `--pids-limit=-1` when `pids` is missing;
   - one notice per missing controller;
   - an inspection that accepts `0` or `-1` for unenforced pids, with a
     diagnostic naming the reported controllers;
   - the help text.

   The fake inspection defaults unrequested values to `0`.

4. **Mounts.** Remove `--read-only-tmpfs=false` and add `/run/secrets` and
   `/dev/shm` as empty read-only tmpfs mounts. `/dev` is left to the engine.
   The other mounts are unchanged.

   Revised during apply: the reference layout also mounts its own `/dev`
   tmpfs and `--mount type=devpts,destination=/dev/pts`. That `devpts` takes
   the kernel defaults `mode=600,ptmxmode=000`, so no pseudo-terminal can be
   allocated ("out of pty devices"). agy runs tool commands in a PTY, and
   `test_actual_agy_tool_with_synthetic_gemini_api` failed. Podman rejects
   `ptmxmode` as a `devpts` mount option, so an explicit `/dev` cannot
   provide usable PTYs. The engine's own `/dev` has a `devpts` with
   `ptmxmode=666,mode=620`. With the two explicit mounts removed, the
   failing test passed.

   Trade-off: on Podman 5, `/dev` is the engine's writable tmpfs without the
   extra `noexec`. On Podman 4.9 it stays read-only. The original crun 1.27
   terminal failure came from `--read-only-tmpfs=false`, which is still
   removed. The Rocky check confirms terminal attach.

   The same defect exists in the Claude, Codex, OpenCode and Pi launchers.
   They are fixed in their own follow-up changes.

5. **Build secret.** Add `--secret id=build-ca,src=$ca_bundle` to
   `build_args` when a bundle is selected, and `!podman-build-secret*` to
   `.containerignore`.

6. **Recipe.**
   - **First `RUN`:** add the reference HTTPS prologue (Node.js roots,
     optional `build-ca`, `sed` to `https://`, `Acquire::https::CAInfo` on
     `update` and `install`). Remove the bootstrap bundle before
     `npm install`. Add `mkdir -p /workspace` next to `/antigravity-home`.
   - **Second `RUN`:** mount the same optional `build-ca` secret, build
     `/tmp/agy/ca.pem` from `/etc/ssl/certs/ca-certificates.crt` plus the
     secret when present, pass `--cacert /tmp/agy/ca.pem` to `curl`, and
     let `rm -rf /tmp/agy` remove it. The SHA-512 check is unchanged.

   This extends the reference, whose second network fetch is npm in the
   same step, because Antigravity has an extra HTTPS download that would
   otherwise fail on a TLS-intercepting network with host CA trust.
   Alternative considered: leave `curl` on system roots. Rejected, because
   the build would then pass apt and fail at the artifact download on such
   networks.

7. **Tests.**
   - `tests/fake_podman.py`: answer the controller query, and use `0`
     defaults in the inspection.
   - `tests/test_wrapper.py`: copy `agent_budgets.py` into the fixture,
     and add the controller, socket, mount and build-secret cases. Update
     the `--read-only-tmpfs=false` assertion.
   - `tests/test_image_pins.py`: add the reference transport and
     toolchain checks, the workdir check, and an artifact-download check
     (optional `build-ca`, `--cacert`, the SHA-512 kept), with mutations
     adapted to this recipe.

## Risks / Trade-offs

- [`agy` or its tools need POSIX shared memory] → Covered by
  `test_runtime.py` and `image-smoke.sh`. A break is recorded and needs a
  new change.
- [Unenforced budgets let a session exhaust host resources] → Notices,
  qualification binding and README text.
- [The extra `--cacert` path diverges from the reference recipe] → It is
  limited to the agy download, covered by the pin tests, and recorded in
  the validation record.
- [Rocky-specific failures cannot be reproduced here] → The operator runs
  the final Rocky check.

## Migration Plan

1. Merge `adopt-sandbox-ref-12` with `--no-ff` after validation. The
   operator pushes it, together with the two pending parity commits.
2. On each host: `--container-setup` with refresh approved.
3. Rollback before the push: reset `main` to `91f2740`.
