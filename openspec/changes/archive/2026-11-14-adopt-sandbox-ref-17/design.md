# Design

## Context

Antigravity `main` (`75900fd`, one commit ahead of `origin/main`) pins
`sandbox-ref-12`. A first apply targeted `sandbox-ref-16` and paused at the
real-engine check. On Podman server 4.9.3, `--unsetenv` does not remove a
value given with `--env`, so a toolchain could set the bus variable that
Antigravity removes. The reference fixed this in `sandbox-ref-17` (merge
`a23f155`):

- it protects `DBUS_SESSION_BUS_ADDRESS` in every wrapper;
- it leaves another wrapper's profile variables out of the session with a
  warning instead of failing.

The paused branch `adopt-sandbox-ref-16` holds the tool output and the
uncommitted wrapper work of tasks 2.1–2.3.

The `sandbox-ref-16` dry run reported six modified files and two added files,
nothing removed or "not adopted", and three documents (`AGENTS.md`,
`docs/setup.md`, `docs/network-contract.md` with seven references). The
`sandbox-ref-17` delta touches only `setup/toolchains.py` and
`tests/test_toolchains.py`, which are already in that set.

The reference launcher change is claude-container commit `e45957f`, ported by
Codex (`adopt-sandbox-ref-14`), OpenCode and Pi (`adopt-sandbox-ref-16`).
Antigravity differs:

- **State:** one writable state directory, `state_dir`, validated private at
  `antigravity-container.sh` line 425:
  - unset `ANTIGRAVITY_CONTAINER_STATE_DIR`: the dedicated home
    `~/.local/share/antigravity-container/home`, mounted as
    `/antigravity-home`;
  - a path: that isolated home, mounted the same way;
  - empty: the shared `~/.gemini` (or `ANTIGRAVITY_CONTAINER_CONFIG_DIR`),
    mounted at `/antigravity-home/.gemini` below a tmpfs home.

  The default library `~/.local/share/sandbox-toolchains` is a sibling of the
  dedicated home's parent, so the defaults do not overlap.
- **Dispatch:** `--container-qualify` and `--container-setup` are dispatched
  before the network mode is read (lines 151–174). The option loop at line 182
  collects the remaining `--container-*` options.
- **Order:**
  - the runtime image identity (`session_image`) is resolved before
    `container_args` is built (lines 531–536);
  - `container_args` sets `HOME`, `EDITOR`, `VISUAL` and the workspace mount,
    then the state mounts, `ANTIGRAVITY_CONTAINER_CONFIG_DIR`, the CA mount
    and variables, `--timeout`, `TERM` and the forwarded credential;
  - the protected values come last: `--unsetenv DBUS_SESSION_BUS_ADDRESS
    --env AGY_CLI_DISABLE_AUTO_UPDATE=true`, then `CONTAINER_HOST` or its
    removal.
- **Helpers:** `capture_engine_info <podman args>` sets `engine_response`.
- **Protected names:** the shared module protects, as neutral names, `HOME`,
  `EDITOR`, `VISUAL`, `TERM`, `CONTAINER_HOST`, the CA variables and
  `DBUS_SESSION_BUS_ADDRESS`. As profile names it protects
  `ANTIGRAVITY_CONTAINER_*`, `ANTIGRAVITY_YOLO` and `GEMINI_API_KEY`.
  `AGY_CLI_DISABLE_AUTO_UPDATE` is outside both groups.
- **Temporary storage:** `/tmp` is an executable tmpfs, `/var/tmp` and `/run`
  are `noexec`, and the shared-state tmpfs home has no `noexec` flag.
- **Image:** the `Containerfile` has one digest-pinned `FROM`, the same base
  as the reference; the default image is `localhost/antigravity-cli:latest`.
- **Agent instructions:** the `agy` binary of the current image contains the
  names `AGENTS.md`, `GEMINI.md`, `~/.gemini/GEMINI.md` and
  `~/.gemini/AGENTS.md`. Which files it loads was not tested without
  credentials.
- **Tests:**
  - there is no separate runner image: `tests/run-runtime.sh` runs the suites
    in the agy image itself, with `HOME=/tmp` and a world-writable `/tmp`
    tmpfs;
  - `tests/test_wrapper.py` creates its base with `TemporaryDirectory` and no
    directory argument, and inherits the caller's `HOME`, so the default
    library would land in the real home;
  - `tests/test_runtime.py` inherits the runner's `HOME=/tmp`, and the shared
    module refuses a library below a world-writable directory, so every
    runtime launch would stop;
  - `tests/test_wrapper.py` has a restricted fixture that copies an
    installation (line 909), and `tests/test_network_runtime.py` builds a
    protected installation (line 47).

## Goals / Non-Goals

**Goals:**

- Antigravity adopts `sandbox-ref-17` byte for byte, and its parity table
  matches the reference.
- Antigravity sessions mount the library and get the default environment as
  reference sessions do. Antigravity's own settings cannot be overridden by a
  toolchain.
- Every runner mode the tool lists passes, plus the default runtime mode.

**Non-Goals:**

- Any shared-file change.
- The example recipes.
- Verifying which instruction files `agy` loads; the README offers both names.

## Decisions

1. **Regenerate the branch on `sandbox-ref-17`:**

   - save the wrapper-owned work of the paused branch as a patch. This is
     every changed file except the eight shared files,
     `tests/test_reference_copy.py` and the three tool-updated documents,
     whose changes the tool reproduces;
   - discard the uncommitted branch `adopt-sandbox-ref-16`;
   - stash the change directory, dry run, `--apply` (`sandbox-ref-12` →
     `sandbox-ref-17`) on `adopt-sandbox-ref-17`, restore the stash;
   - apply the patch with `git apply` after `git apply --check`;
   - commit the wrapper port on the same branch and merge once with
     `--no-ff`.
2. **Port the reference launcher block, renaming only.** Placement:

   - the dispatch before the `--container-qualify` loop, accepted only as the
     first argument; the option loop rejects it elsewhere;
   - `ANTIGRAVITY_CONTAINER_TOOLCHAINS` parsed with `boolean` next to
     `ANTIGRAVITY_CONTAINER_TRUST_HOST_CA`;
   - the library check after state validation and the CA parent, before the
     restricted network inputs, so an unsafe library stops before any image
     or container operation. It is skipped for the qualification probe, as
     in the reference;
   - the `--avoid` list is `workspace_mount` plus `state_dir`, in every state
     mode;
   - the image `PATH` read from `session_image` with `capture_engine_info`;
   - the mount and the toolchain environment appended to `container_args`
     after the forwarded credential and before the protected values
     (decision 3).
3. **Antigravity settings last.**

   - Podman keeps the last `--env` for a name, so the toolchain environment
     is placed before `--env AGY_CLI_DISABLE_AUTO_UPDATE=true`, and the
     launcher's value wins. Pi uses the same rule for its restricted
     settings.
   - `--unsetenv` does not remove a value given with `--env` (observed on
     Podman server 4.9.3). The launcher therefore cannot remove
     `DBUS_SESSION_BUS_ADDRESS` once a toolchain sets it. Since
     `sandbox-ref-17`, the shared module rejects that variable in `add` and in
     `launch-env`, so no toolchain can set it.
   - Alternative: extend the shared protected set with agent-specific names.
     Rejected: the shared code cannot name the agents.
4. **Tests mirror the other ports.**

   - `tests/test_wrapper.py`:
     - the setup gives the wrapper a synthetic host home below the base,
       with the library at `self.library`;
     - dispatch, and the rejection when not first;
     - private creation and the read-only mount;
     - unsafe library: mode, workspace, worktree parent, installation, the
       isolated home and the shared `~/.gemini`;
     - disable;
     - appended `PATH` and environment, and the stale-base warning;
     - a toolchain's `AGY_CLI_DISABLE_AUTO_UPDATE` losing to the
       launcher's value;
     - restricted `--mount-target`;
     - the home-workspace overlap.
   - `tests/fake_podman.py` answers the image `.Config.Env` inspection.
   - The restricted fixture installs `setup/common.py`, `setup/toolchains.py`
     and `Containerfile`.
   - `tests/test_runtime.py`:
     - each test gives the wrapper a private home on the native state root,
       outside the workspace and the worktree parent;
     - archive and image sources, failing check, read-only mount, `node` and
       `python3` not shadowed, disabled mount;
     - `AGY_CLI_DISABLE_AUTO_UPDATE=true` kept against a toolchain that sets
       it.
   - `tests/test_network_runtime.py`: the live add during an offline
     session, with `setup/` and `Containerfile` in its installation.
   - Existing fixtures that fail because of the mount are adapted and
     recorded.
5. **Runner storage.** `tests/run-runtime.sh` mounts a private executable
   tmpfs at `/sandbox-test-tmp` (`0700`, `U=true`, 1 GiB) as
   `SANDBOX_TEST_TMPDIR`. `tests/test_wrapper.py` creates its base there when
   the variable is set. The runtime suites keep the native state root for
   anything a session container mounts, because the runner's tmpfs is not
   visible to the host engine.
6. **Documentation:** the README section states the reference rules for
   Antigravity:

   - the instruction line for the project's `GEMINI.md` or `AGENTS.md`, or
     `~/.gemini/GEMINI.md` (`/antigravity-home/.gemini/GEMINI.md` in the
     session);
   - `/tmp` is executable, `/var/tmp` and `/run` are `noexec`; recipes shared
     with other wrappers keep notes such as `GOTMPDIR` under the workspace;
   - the three state modes as overlap cases;
   - the neutral and profile protected variables, and decision 3.

## Risks / Trade-offs

- [The dedicated home is the default state and lives under `~/.local/share`]
  → The library is a sibling; a custom `ANTIGRAVITY_CONTAINER_STATE_DIR` or
  `ANTIGRAVITY_CONTAINER_TOOLCHAINS_DIR` that nests one in the other stops
  the launch with the library path.
- [Unsafe-workspace launches from the home now stop] → As in the other
  wrappers; documented.
- [The paused branch carries work written against `sandbox-ref-16`] → The
  patch excludes every tool-owned file, and the full suites run again on the
  regenerated branch.
- [The instruction file names come from the binary, not a session] → The
  README names both; the operator can confirm with an authenticated session.
- [Qualification reports become stale] → The operator reruns
  `--container-setup`.

## Migration Plan

1. Merge `adopt-sandbox-ref-17` with `--no-ff`. The operator pushes it.
2. Rerun `--container-setup` on this host, the Rocky Linux 9 lab host and the
   newer WSL host. With the Temurin 21 toolchain in the library, check
   `java -version` in an Antigravity session and run
   `antigravity-container --container-toolchain verify java21`.
3. Record the results, then archive with the spec sync.
4. Rollback before the push: reset `main` to `75900fd`.
