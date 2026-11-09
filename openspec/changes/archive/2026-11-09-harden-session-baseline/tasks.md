# Tasks

## 1. Baseline and privilege dropping (B01)

- [x] 1.1 On the host, record a pre-change baseline with the current image `localhost/antigravity-cli:latest` (agy 1.4.12): capability sets and `NoNewPrivs`, cgroup `memory.max`/`pids.max`/`cpu.max`, `agy --version`, Git, OpenSpec, bubblewrap, delegated `podman info` plus a child container, and the existing keyring runtime tests; verify the results are captured in working notes for `docs/validation.md`
- [x] 1.2 Measure the account keyring (private `dbus-run-session`, `gnome-keyring-daemon` unlock with a test passphrase, collection `Locked` false) in a container with `--cap-drop=all --security-opt=no-new-privileges` on the current image (D7); verify it works, or stop and report the trade-off to the operator without adding capabilities
- [x] 1.3 Add `--cap-drop=all` and `--security-opt=no-new-privileges` to the common `container_args` (D3) and update help; verify a new `tests/test_wrapper.py` case finds both flags in the recorded `podman create` arguments for agy, shell, YOLO and delegated launches

## 2. Resource budgets (B02)

- [x] 2.1 Add budget validation and normalization per D1/D2 after option parsing and before `command -v podman`, and append `--memory`, `--cpus`, `--pids-limit`; verify table-driven wrapper tests for defaults, overrides and every rejected form (status 1, variable named, no engine call, no state directory)
- [x] 2.2 Add the post-create budget inspection before `podman start` (D4) and extend the fake engine (`FAKE_AGENT_BUDGETS`, `FAKE_INSPECT_STATUS`); verify wrapper tests for matching, missing and different limits and an inspection failure, each removing only the owned container without start
- [x] 2.3 Add real-engine checks in `tests/test_runtime.py` for zero capabilities, `NoNewPrivs: 1`, default and overridden effective cgroup v2 limits with and without delegation, and process-limit enforcement; verify `bash tests/run-runtime.sh` passes on the host

## 3. Sensitive workspace roots (B03)

- [x] 3.1 Move `workspace`/`workspace_mount` computation before engine checks and add the guard per D6 with the exact override and warning; verify wrapper tests for the physical home, the worktree parent equal to the home, a symlink to `/etc`, `/`, `/tmp`, `/mnt/d` refused and a project below it accepted, exact and non-exact override, with no engine call or state creation on refusal
- [x] 3.2 Confirm wrapper and runtime fixtures use non-refused workspaces; verify both suites pass, with any test that deliberately launches from a refused directory setting the exact override

## 4. Session lifetime (B04)

- [x] 4.1 Add `ANTIGRAVITY_CONTAINER_RUN_TIMEOUT` validation, `--timeout N` for N ≥ 1 and the lifetime notice (D5); verify wrapper tests for unset, empty, `0`, valid and invalid values and for the notice after a slow non-zero client
- [x] 4.2 Add a real-engine test with a short limit (expiry, notice, non-zero status, owned cleanup) and an early exit without notice; verify on the host and record the observed status

## 5. Pinned image inputs (B05)

- [x] 5.1 Replace the installer step in `Containerfile` with the pinned per-architecture `agy` artifact install (D8), pin the base digest and `OPENSPEC_VERSION=1.16.0` (D9), and add the update-procedure comment; rebuild with `--container-build`; verify `agy --version` reports 1.5.3, `openspec --version` 1.16.0, and a deliberately wrong SHA-512 fails the build
- [x] 5.2 Add `tests/test_image_pins.py` per D9; verify it passes and fails on mutated copies (tag-only base, `@latest`, unversioned OpenSpec, installer or manifest URL, missing or malformed SHA-512, missing architecture)
- [x] 5.3 Run the existing image checks (`tests/image-smoke.sh` and the build-context runtime test) on the new image; verify they pass or update them for the removed installer step

## 6. Keyring and tools under hardening

- [x] 6.1 Run the existing keyring, API-key and delegation runtime tests on the hardened, pinned image together with Git, OpenSpec and bubblewrap checks; verify on the host with no credentials or model request, and record any limitation without adding capabilities

## 7. Documentation and evidence

- [x] 7.1 Update `--container-help`, README and `AGENTS.md` with the budgets, defaults and formats, the lifetime, the refused set and override, the capability drop in every mode, the storage-growth statement, the cgroup controller requirement, the pinned versions and the `agy` update procedure; verify a help test lists all five variables with defaults, and `bash -n` and `git diff --check` pass
- [x] 7.2 Run the full credential-free unit suites and `bash tests/run-runtime.sh` on the host and add a dated `docs/validation.md` section (baseline comparison, results, initial failures and reruns, lifetime status, pinned versions, keyring outcome, limitations); verify `openspec validate harden-session-baseline --strict` passes
- [x] 7.3 Mark B01–B05 and the agent-container part of C07 in `todo.md` with an implementation note; verify the note names the change and the evidence section

## Workflow follow-up

- Archive the change after review, then commit and merge when the user asks; the user pushes.
- Authenticated account login with `agy` 1.5.3 was verified by the operator on 2026-11-09.
- Continue Wave 2 with OpenCode (`narrow-exposed-state` first).
