# Validation record

## Adoption of `sandbox-ref-36` development checks: 2026-11-26

Copied the shared files from `sandbox-container` commit
`ce2c9d28873838a4ac541da34edaf7d8b5264be4`. The adoption runner generated
the checklist for the full shared, setup, setup-runtime, qualification,
wrapper, runtime, network-feasibility, guard and network modes.

The development session had a WSL2 6.6.87.2 kernel, a Windows-mounted 9p
checkout, and a read-only container root. The mounted drive permits
fixture script execution and reports file and directory modes as `0777`.
The local Podman client returned `Operation not permitted`.

| Check | Result |
| --- | --- |
| Manifest, alignment, engine fixtures, profile, image pins, Windows bootstrap and wrapper help | 84 passed and one skipped on executable 9p storage. This group includes the byte comparison against the tagged reference |
| Legacy Podman opt-in | Nine configured mode and argument combinations, including build-only, refused it before state creation |
| Network policy, TLS, multiplexing and platform | 67 passed and one skipped |
| Qualification contracts and toolchain recipe validation | 30 passed, including schema 2, image recipe and catalog checks |
| Shared setup on `/tmp` | 25 passed, 19 failures and 49 errors. The failing cases and result categories matched the reference checkout in the same environment. They include rejected writable ancestors and unavailable executable fixtures or engine calls |
| Windows namespace entry and library path fixtures | The Windows enter fixture failed its `0700` and `0600` assertions on 9p because the mount reports `0777`. The recipe and archive translation test reached library preparation and was blocked by the world-writable `/tmp` ancestor |
| Runtime discovery | 55 Podman-dependent tests discovered and skipped. The wrapper runner stopped when Podman returned `Operation not permitted` |
| Syntax, whitespace and specification checks | Bash and Python syntax, `git diff --check`, strict OpenSpec validation and the spec merge preview passed |
| Pinned ShellCheck and PSScriptAnalyzer | Unavailable. Podman returned `Operation not permitted` and the analyzer package endpoint returned HTTP 502 |
| Adoption runner | Generated the checklist and stopped in preflight. The Podman queries failed, image availability could not be established, and both the home and temporary filesystems had less than 1 GiB free |

Production validation follows closure of this change. The Linux or WSL run
uses the recorded checklist, including the runtime and guard-toolchain
images and the Alpine sample pinned in `tests/test_runtime.py`. The runner
rebuilds `localhost/antigravity-cli-engine:latest`. Record its identity and
`SETUID,SETGID,SYS_CHROOT,CHOWN` label, the native setup and guarded Gemini
results, and the Windows post-release validation as they are performed.
Open separate changes for defects found in production. The older entries
below retain the evidence for their tags.

## Environment

Initial implementation checks on 2026-10-31 used Linux amd64, rootless
Podman 4.9.3 on Ubuntu 24.04 / WSL2 kernel 6.6.87.2, with SELinux disabled.
Codex ran in a container connected to the host through a Unix socket.
Workspace bind sources retained their host absolute paths.

The official installer selected Antigravity CLI 1.4.12, verified its SHA-512
checksum, and installed an x86-64 dynamically linked ELF executable.
The image reported glibc 2.36 and OpenSpec 1.16.0. Required shared libraries
resolved successfully as UID/GID 1000 with a read-only root filesystem.

## Commands and coverage

The initial implementation automated run passed **19 wrapper tests and 9 runtime tests**.
ShellCheck passed for the wrapper, entrypoint, keyring helper, and verification
scripts. `openspec validate add-antigravity-container-runtime --strict` passed.

- `python3 -m unittest discover -s tests -p test_wrapper.py -v`: wrapper
  argument forwarding, boolean combinations, help without Podman, build paths,
  errors, identity/mount argv, name collisions, stdin, exit status, signals,
  and API key forwarding by name.
- `bash tests/run-runtime.sh`: opt-in runtime checks using the built image,
  rootless service, real workspace binds, and private native Linux storage for
  dummy keyring data. The runner creates and removes its own Podman volume.
- `tests/image-smoke.sh`, fed to Bash inside the image: non-root CLI startup,
  tool availability, ABI, writable home/tmp, read-only system, and disabled
  automatic updates.

The runtime suite checks project isolation with an external sentinel,
file ownership, persistent state, ephemeral `/tmp`, Git worktrees with shared
metadata, child container binds through the host socket, concurrent shell
sessions, Secret Service persistence, incorrect passphrases, and native
missing-API-key diagnostics. Test secrets are synthetic and never represent
Google credentials.

## Filesystem findings

The Windows-backed workspace did not enforce mode 0700 for new directories.
The wrapper rejects application state with group/other permissions or the
wrong owner. Credential tests therefore use a disposable native Linux Podman
volume mounted at its original host path in the verification runner.
Projects can remain on Windows-backed storage; choose a private native Linux
path for `ANTIGRAVITY_CONTAINER_STATE_DIR`.

In the initial implementation, the image's `/run` directory was not writable
by the non-root process; the explicit mount policy below supersedes that layout. The
private D-Bus/keyring runtime directory is created with mode 0700 in `/tmp`,
which is a per-container ephemeral tmpfs.

Concurrent account helpers using the same state are rejected by an exclusive
keyring lock; this was verified with two real container sessions. Sequential
sessions reused a dummy credential after container recreation and rejected
an incorrect passphrase. An in-container `/proc` audit found no plaintext
keyring passphrase in readable process arguments or environments. Concurrent
shell sessions completed independently. Targeted checks also confirmed that
YOLO combined with `--version` does not prompt for a keyring passphrase.

An interactive probe of the actual CLI reached the Google OAuth menu and,
after selecting it, printed an external authorization URL without using a
host display, browser, keyring, or bus. That initial probe did not sign in to
a Google account. No live authorization URL was retained in this report.

## User-reported account acceptance

The user subsequently completed manual acceptance on Linux amd64 with
rootless Podman 4.9.3 and Antigravity CLI 1.4.12, using a new dedicated state
directory with mode 0700 and owner UID 1000. They confirmed:

- Google OAuth completed and the CLI opened an authenticated session.
- The agent created `acceptance.txt` containing `antigravity-container-ok`.
  The host reported owner `1000:1000` and permissions `600`.
- After exiting and recreating the container, entering only the keyring
  passphrase restored the authenticated session without repeating OAuth.
- `/logout` returned the CLI to authentication. After exiting and recreating
  the container again, Google authentication was still required.

These results establish the account login, model-backed project operation,
session persistence, and logout lifecycle for the tested environment. No
credentials or authorization codes were supplied to Codex.

The user then completed the account-backed worktree check with
`--container-git-worktree`, YOLO disabled, and Podman socket access disabled.
Inside the linked worktree, the agent ran `git status --short` successfully
with a clean initial result, and `git rev-parse --git-common-dir` resolved to
the main repository's `.git` directory under the mounted common parent.
The agent created `worktree-acceptance.txt` containing `worktree-ok`. After
exiting the container, the user's host-side `cat` confirmed that content and
`git status --short` reported `?? worktree-acceptance.txt`. Together with the
earlier login/restart/logout results and automated mount-boundary checks,
this completes task 5.2 for the tested amd64 environment.

## User-reported API provider acceptance

The user ran a headless prompt with session-only
`--settings '{"modelProvider":"gemini"}'`, an exported API key, stdin
redirected from `/dev/null`, and a 60-second print timeout. The CLI returned
`api-provider-ok` and the wrapper exited with code 0. The key was entered
privately in the user's terminal and was not supplied to Codex.

The user then ran a headless API-provider prompt with
`ANTIGRAVITY_YOLO=1` and `ANTIGRAVITY_CONTAINER_PODMAN=0`. The agent executed a
terminal command that checked that `/run/podman/podman.sock` was not a socket
and `CONTAINER_HOST` was empty before writing `yolo-acceptance.txt`. The
agent reported command exit status 0, the wrapper exited with code 0, and
the user's host-side `cat` returned `yolo-no-podman-ok`. Stdin was redirected
from `/dev/null`, so the command completed without interactive approvals.

## User-reported sandbox failure

With YOLO and Podman access disabled, the user ran `--sandbox` with the API
provider and `toolPermission: proceed-in-sandbox`. The agent reported:

```text
Command failed to run: connecting to sandbox server: read unix @->@: recvmsg: connection reset by peer.
```

The wrapper returned exit code 0, but `sandbox-acceptance.txt` was absent.
This is a failed sandbox operation, not a successful execution. Native CLI
completion status alone does not establish success of an agent tool call.

Credential-free probes in the built image, with a read-only root, UID 1000,
and the wrapper's tmpfs options, successfully ran both
`unshare --user --map-root-user true` and a Bubblewrap user-namespace command.
These probes establish basic namespace availability in the tested engine;
they do not establish that Google's sandbox starts correctly.

The user subsequently supplied the specific CLI diagnostic:

```text
sbox: sethostname: operation not permitted
```

The host's actual default seccomp profile allows `sethostname` only when the
container has `CAP_SYS_ADMIN`, and explicitly returns EPERM otherwise. A
credential-free probe reproduced EPERM when calling `sethostname` as root
inside newly created user and UTS namespaces under the default profile.

A temporary diagnostic profile retained the host policy and changed only
`sethostname` to unconditional syscall allowance. The same namespaced probe
then succeeded without adding capabilities or changing the read-only root.
Outside the nested user namespace, the call still failed with EPERM and the
container hostname remained unchanged. These tests isolate a seccomp obstacle;
full Google sandbox execution with the diagnostic profile has not yet been
tested. No production wrapper policy was changed.

The earlier certificate-installation hypothesis from a similar Google issue
is not supported by the diagnostic supplied for this environment.

### Accepted limitation

The user chose to document this incompatibility and retain the standard
container security policy. The project does not add a custom seccomp profile,
a profile-selection environment variable, `CAP_SYS_ADMIN`, or privileged
execution. The temporary profile was a diagnostic experiment, not a supported
runtime configuration or proof of successful Google sandbox execution.

The sandbox compatibility check is complete with a documented failure on the
tested versions; sandboxed command execution did not pass. Headless API and
YOLO operations passed independently. Task 5.3 is satisfied by recording
these outcomes and the seccomp limitation without expanding privileges.
Recheck the internal sandbox after relevant CLI or engine updates.

## Acceptance checks requiring additional environments or credentials

The following checks remain separate from synthetic Secret Service and
wrapper tests and must not be counted as passed based on those tests:

- Linux arm64 image build and execution on a suitable runner.
- SELinux enforcing socket and workspace access.

The user confirmed that no ARM machine is currently available. The local
amd64 engine also had no registered ARM emulator when checked. No arm64
build or execution result is claimed. Task 5.1 remains open for its arm64
portion; its amd64 checks have passed. The user explicitly authorized
archiving the change with this task incomplete. The archived checklist
preserves that status; future arm64 verification can be tracked separately
when a suitable runner becomes available.

To reproduce manual account acceptance, start with a new private state directory on a
native Linux filesystem, launch the wrapper in a terminal, set its keyring
passphrase, and finish Google sign-in in your own browser. Ask the agent to
create a harmless file in a disposable project. Restart with the same state,
unlock the keyring, confirm session reuse, then run `/logout` and verify a new
launch no longer reuses the account. Never put credentials, authorization
codes, or live authorization URLs into a test report.

For the API provider, set `modelProvider: gemini` in the dedicated settings,
export your key privately in your shell, and run a harmless `-p` prompt with a
finite `--print-timeout`. Repeat with `ANTIGRAVITY_YOLO=1` and inspect the
container to confirm that YOLO did not add a Podman socket. Test `--sandbox`
separately, recording the actual host behavior without expanding privileges.


## Launch preflight hardening (2026-11-01)

Change: `harden-container-launch-preflight`. Tests used the existing Linux
amd64 image through the same-host Unix rootless Podman service, retaining host
absolute bind paths and using disposable native Linux volume storage for state.
The host engine is Podman 4.9.3 on WSL2 kernel
`6.6.87.2-microsoft-standard-WSL2`; the outer client is Podman 4.3.1.
SELinux is disabled and the standard seccomp policy remains enabled.
The existing image reports Antigravity CLI 1.4.12 and OpenSpec 1.16.0.

Final checks passed:

- `python3 -m unittest discover -s tests -p test_wrapper.py -v`:
  **32 tests passed** (41.389 seconds).
- `bash tests/run-runtime.sh`: **12 tests passed** (65.684 seconds), using
  a disposable native-state volume that the runner removed after completion.
- Bash syntax checks for all five shell scripts, and ShellCheck 0.11.0
  through `docker.io/koalaman/shellcheck:stable`: passed.
- `openspec validate harden-container-launch-preflight --strict`: passed.

The expanded wrapper regressions cover complete engine and delegation
responses (including extra blank records), failed queries, empty Unix launch
endpoints, socket precedence/canonicalization/remapping and spaces, exact
opt-in across CLI/shell and YOLO combinations, early private-state rejection,
state symlinks, inherited wrapper umask, explicit mount arguments, and cleanup
on success, failure, retry exhaustion, unexpected command failure, and handled
TERM/INT/HUP interruption after diagnostic allocation. Fault injection tests
exercise ownership, non-native mode reporting, and path-resolution failures
without requiring administrator privileges or filesystem races.

The real rootless runtime checks established:

- `/tmp` is executable tmpfs, `/var/tmp` and `/run` are `noexec` tmpfs;
  all use `nosuid,nodev` and are writable by the session user. Their limits
  are respectively 512 MiB, 512 MiB, and 32 MiB. The wrapper explicitly sets
  mode `1777`, including `/run`, rather than copying its root-owned image mode.
  Native executable probes succeed from `/tmp` and are denied on the other
  two mounts; temporary sentinels disappear on container replacement.
- A disposable derived image defining `CONTAINER_HOST` cannot retain that
  value when delegation is `0` or `true`; the environment variable is absent,
  no socket is exposed, and the outer Unix launch connection still works.
- Delegation enabled with `1` supports a real child-container project bind
  and preserves caller ownership. Fake-engine checks separately establish
  that choosing a distinct delegation endpoint does not retarget launch calls.
- Shell and API-entrypoint probes observed umask `022` and controlled file
  mode `0644`. The API test substitutes a harmless `agy` probe after selecting
  the native `gemini` provider; it performs no model request. The real account
  helper with dummy passphrases observed umask `077`, file mode `0600`, and
  private runtime mode `0700`. These are measured runtime properties, not
  consequences inferred from the wrapper's temporary state-creation umask.
- Image smoke checks, state persistence and ownership, worktree boundaries,
  concurrent sessions, keyring persistence/unlock and rejection of wrong or
  mismatched passphrases, credential process audits, and native missing-key
  diagnostics pass with the explicit mount policy.

These tests use synthetic secrets and do not repeat Google OAuth or paid
model acceptance. Existing arm64, SELinux-enforcing, and internal sandbox
limitations remain as recorded above. Temporary diagnostic cleanup covers
exits where the EXIT handler can run; SIGKILL and host failure are excluded.


### TODO acceptance mapping

| TODO item | Evidence |
| --- | --- |
| Complete launch response | `test_complete_launch_response_required`, both normal and explicit rebuild paths |
| Empty Unix launch endpoint | `test_launch_endpoint_rejected_before_query`, no engine calls |
| Exact delegation opt-in | `test_exact_delegation_cli_and_shell`, independent YOLO combinations |
| Strict socket path and response | Socket response, inaccessible/relative socket, selection, canonicalization, and host remapping wrapper regressions |
| Clear disabled connection | `test_disabled_delegation_removes_image_default` plus launch-connection independence checks |
| State before image operations | `test_state_preflight_failures_before_images`, creation/resolution/ownership/access/mode failures |
| Explicit temporary mounts | Argument regression, `test_explicit_temporary_mounts`, image smoke and keyring lifecycle |
| Scoped state umask | `test_private_state_symlink_and_scoped_umask` and `test_runtime_file_modes_by_execution_path` |
| Diagnostic cleanup | `test_diagnostic_cleanup_all_exit_paths` and `test_diagnostic_cleanup_on_startup_signals` |


## Bounded shutdown and build-context alignment (2026-11-01)

Change: `harden-session-shutdown-and-build-context`. Checks used the existing
Antigravity CLI 1.4.12 image, Linux amd64, and the same-host Unix rootless
Podman 4.9.3 service on WSL2, with SELinux disabled and standard seccomp.
Runtime state used a disposable native Linux volume at its original host path.

Final checks passed:

- `python3 -m unittest discover -s tests -p test_wrapper.py -v`:
  **39 tests passed** in 126.591 seconds.
- Bash syntax checks and ShellCheck 0.11.0 for all five shell scripts: passed.
  ShellCheck ran through the existing `docker.io/koalaman/shellcheck:stable`
  container because the host sandbox does not provide the executable.
- `openspec validate harden-session-shutdown-and-build-context --strict` and
  `git diff --check`: passed.

`bash tests/run-runtime.sh` passed **14 tests** in 82.729 seconds. The new real
shutdown check started a shell ignoring TERM, identified its unique workdir
and owned container ID, interrupted the wrapper, observed bounded status 143,
and confirmed that the owned container was gone while an unrelated stopped
sentinel container survived. Test resources were removed afterward.

The new build fixture used the actual `.containerignore` and both real helper
sources. Podman successfully copied and installed the executable entrypoint
and keyring helper. A `COPY .` inventory contained exactly the root-level
`Containerfile`, `.containerignore`, `container-entrypoint.sh`, and
`keyring-session.sh`. Synthetic unknown files, `.env`, local Gemini settings,
keyring/state files, Git metadata, and nested same-named files were absent.
The fixture image and synthetic context were removed. This verifies engine
ignore matching independently of Git ignore rules without a release download.

Wrapper lifecycle regressions exercise first-signal precedence in CLI and
shell modes; CID publication before and after interruption; five-second
interrupted-create completion followed by bounded cancellation; CID recovery
from a TERM cancellation handler; stalled creation with no recoverable ID;
ignored application TERM; stalled or failed kill/removal calls; and clients
ignoring TERM. Real timeout budgets remain active, with a conservative
30-second outer ceiling for combined failure paths. Normal exit statuses 0,
23, and 125 survive failed or timed-out removal without create retries.
Private bookkeeping directories use mode 0700; redirected output/error files
use mode 0600 without changing the engine client's inherited umask.

The full existing runtime suite also passed keyring/D-Bus persistence,
wrong-passphrase/mismatch rejection, account locking, native API missing-key
diagnostics, measured shell/API/account file modes, temporary mount limits and
execution policies, workspace/worktree boundaries, and delegated child binds.
No real Google OAuth or paid model request was repeated. Existing arm64,
SELinux-enforcing, and internal sandbox limitations remain unchanged.

Coreutils timeout is now a checked host prerequisite. Five seconds of
application grace is one phase, not the total shutdown budget. Every engine
forward/removal call has five seconds plus one second for KILL escalation;
local client TERM grace is five seconds with at most one second for final
observation/reaping. Successful client cancellation does not prove that a
remote create request was cancelled: unresolved ownership is reported for
manual inspection and never permits deletion by guessed name. Engine loss,
SIGKILL, host failure, and uninterruptible kernel tasks can prevent resource
removal despite bounded userspace cleanup attempts.

## Common specification names: 2026-11-09

The OpenSpec capabilities were renamed to the scheme shared by the five wrappers (Wave 1, `sandbox-ref-2`). Requirements and scenarios are unchanged; only directory names and spec titles changed. Earlier sections and archived changes keep the names that were current at the time.

| Previous name | Current name |
| --- | --- |
| `agent-permissions` | `container-podman-access` |
| `container-authentication` | `agent-authentication` |

`openspec validate --specs` passed: 5 specs, 0 failures.

## Session hardening baseline (B01–B05): 2026-11-09

Change `harden-session-baseline` (Wave 2), ported from the `claude-container`
reference at tag `sandbox-ref-2` and the matching Codex change. Host: WSL2
x86_64, kernel 6.6.87.2-microsoft-standard-WSL2, rootless Podman 4.9.3 with
cgroup v2. No credentials, Google login or model requests were used.

Pre-change baseline with image `5c425a152ccc` (agy 1.4.12 from the latest-release
installer, OpenSpec 1.16.0 unpinned): capability sets 0 except bounding
`00000000800405fb`, `NoNewPrivs` 0, `memory.max` `max`, `pids.max` 2048 (engine
default), `cpu.max` `max 100000`. The existing runtime suite passed 14 tests.
Before changing the wrapper, the same image was run with `--cap-drop=all`,
`--security-opt=no-new-privileges` and the default budgets: a private
`dbus-run-session` with `gnome-keyring-daemon --unlock` reported the collection
unlocked, `secret-tool` stored and looked up a dummy secret, and Bubblewrap and
the delegated Podman client worked. No capability was needed.

After the change, image `ec5d5f1df09e` built from the pinned recipe: base
`docker.io/library/node:22-bookworm-slim@sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da`,
`agy --version` `1.5.3` from the recorded `linux-x64` artifact and SHA-512,
`openspec --version` `1.16.0`. A build with a wrong SHA-512 failed at
`sha512sum --check` and produced no image. The arm64 artifact and checksum are
recorded from the official manifest but were not built on this host.

| Check | Result |
| --- | --- |
| `tests/test_wrapper.py` (runner container) | Initial run: 2 failures and 1 error, because the existing fake engine keeps its call log across invocations; the ported tests now clear it. Then 1 failure: a fast exit with a 1-second limit printed the lifetime notice because Bash `SECONDS` has whole-second granularity; the test uses a 2-second limit and a 30-second limit for the early exit. Rerun: passed, 48 tests |
| `tests/test_image_pins.py` | Passed: 2 tests, including mutated recipes (tag-only base, `@latest`, unversioned OpenSpec, installer, manifest URL, missing or malformed SHA-512, missing architecture, version mismatch, missing verification) |
| `bash tests/run-runtime.sh` | Initial run: 2 failures, because two unrelated `pi-container` containers named `project-with-spaces-*` (created 2026-11-03) were present; the checks now compare the session list before and after. Rerun: passed, 18 tests |
| Effective hardening | All capability sets 0, `NoNewPrivs` 1, private cgroup namespace; `memory.max`, `pids.max` and `cpu.max` matched 4 GiB/512/2 CPUs and 1536 MiB/256/1.5 CPUs, with and without delegation; 80 children with a 32-process budget failed as expected |
| Keyring under hardening | The keyring runtime tests now run with the wrapper's capability drop, no-new-privileges and default budgets: creation, persistence, wrong passphrase, missing terminal, mismatch and concurrent locking passed |
| Tools under hardening | Bubblewrap, Git, OpenSpec, image smoke, the build-context inventory and a delegated child container passed. The Gemini API-key missing-key diagnostic passed without a terminal |
| Lifetime | `ANTIGRAVITY_CONTAINER_RUN_TIMEOUT=3` stopped `sleep 60`; the client returned 255, the notice was printed and the owned container was removed. An early `exit 7` returned 7 without a notice |
| Refused workspace | A launch with the workspace equal to `HOME` exited 1 before any engine operation |
| `bash -n`, `git diff --check`, `openspec validate harden-session-baseline --strict` | Passed |

Known limitation shared with the reference wrappers: the lifetime notice
compares whole seconds, so with a 1-second limit a fast non-zero exit can
print the notice; the exit status is never altered. Not covered by the
automated checks: the Python budget module, setup questions and qualification
binding (Wave 3).

Operator check, 2026-11-09: authenticated account login with agy 1.5.3 on the
hardened, pinned image succeeded.

## Network egress port (`add-network-egress`): 2026-11-10

Target: WSL2 kernel 6.6.87.2, Landlock ABI 3, rootless Podman client 4.3.1 and
server 4.9.3 with Netavark. Shared files at `claude-container` `sandbox-ref-8`
(commit `12cffab`). The guard was packaged from the reference toolchain
(`localhost/antigravity-guard-toolchain:development`, `0b69ba43c894…`). Its
SHA-256 `0c647dfea75667a46a8cd4cc4dfea4ee3d10363752ea7ce5957162bacd6d7ec9`
equals the guard of the other wrappers. The proxy image
`localhost/antigravity-egress:local` is `13adbfafd7bd…`, the same agent-neutral
image.

### Keyring decision

The guard denies new Unix sockets and listeners, so the private D-Bus session
and GNOME keyring cannot work in restricted modes. On 2026-11-10 the operator
chose `agy`'s file token storage in every mode and the removal of the keyring.
The measurements below confirm the fallback without a bus.

### Measured `agy` 1.5.3 behavior

Image `ec5d5f1df09e` (before this change) and `8084f5fea2ba` (after), with
dummy credentials only:

| Check | Result |
| --- | --- |
| Token storage | `agy` logs `Using file-based token storage because SSH session detected` (with the sign-in marker) or `because no D-Bus session bus detected` (under the guard). It reads `~/.gemini/antigravity-cli/antigravity-oauth-token` (traced with `strace`). Plugin secrets and the user scope live in `~/.config/antigravity/` |
| Sign-in without a bus | The TUI offers Google OAuth; the URL/code flow reached the code prompt with no keyring prompt. The authorization URL uses `accounts.google.com` with redirect `https://antigravity.google/oauth-callback` |
| Concurrent sessions on one state | Two concurrent `agy -p` sessions left valid configuration JSON; `agy` writes it with a temporary file and rename. Concurrent token refresh needs a real account and is part of the operator checks |
| Hosts, logging proxy | Account mode without a token: only `CONNECT play.googleapis.com:443` (telemetry). Gemini API mode: `generativelanguage.googleapis.com:443` plus telemetry. `strace` showed no direct connection besides the proxy |
| Account hosts (static) | Token endpoint `https://oauth2.googleapis.com/token`, model service `https://cloudcode-pa.googleapis.com`; `www.googleapis.com` (user information) is excluded. A synthetic token file was not accepted (the stored token also records the authentication method), so post-sign-in hosts remain an operator check |
| Telemetry and update | `AGY_CLI_DISABLE_AUTO_UPDATE=true` logged as honored. Telemetry to `play.googleapis.com/log` continued with `telemetryEnabled: false`; no environment control was found. The proxy denies it |
| Proxy and CA | `HTTPS_PROXY` honored. With a synthetic CA: no trust gave `x509: certificate signed by unknown authority`; `SSL_CERT_FILE` with the bundle reached the fixture; `AGY_CA_CERT` alone did not |
| Under the guard (offline) | `enforced revision=abi3-seccomp-mux-v1 abi=3`. `agy --version` 1.5.3. `agy -p` against a loopback Gemini stub (`GOOGLE_GEMINI_BASE_URL`) streamed `fixture-done`. With `--dangerously-skip-permissions`, a `run_command` tool call wrote a sentinel owned by UID 1000. The language server listened on loopback TCP. The TUI rendered and exited 0 after two Ctrl+C |
| Denied under the guard | A Unix listener (`PermissionError`); Bubblewrap (`Failed to make / slave: Operation not permitted`). `agy`'s only Unix-socket use was a connection attempt to the absent `/var/run/nscd/socket` |
| Layout | The guard accepted the dedicated home, exec `/tmp`, noexec `/run` and `/var/tmp` (mode `1777`), and a shared `.gemini` bind below a mode-`1777` tmpfs home (a mode-`0700` tmpfs home blocked traversal) |

### Results

Runtime image after the change: `localhost/antigravity-cli:latest`
`8084f5fea2ba…` (`agy` 1.5.3; `relay.py` and `mux.py` match `network/` by
SHA-256; no `dbus-daemon`, `gnome-keyring-daemon` or `secret-tool`).

| Check | Result |
| --- | --- |
| `bash -n`, ShellCheck | Passed, no findings |
| `tests/test_reference_copy.py` | Passed; fails on an injected byte change and an injected identifier |
| `--wrapper` | Passed: 61 tests. First run: 7 expected failures from the new maintenance gate, the D-Bus `--unsetenv` and the state-resolution message; tests and the build-status propagation were updated |
| `--shared` | Passed: 138 tests, 27 skipped (run by the modes) |
| `--guard`, `--guard-idle` | Passed: 19 tests (1 skipped) and 1 test. Before `tests/test_network_runtime.py` existed, the three guarded TLS cases could not import it |
| `--network-feasibility`, `--network-policy`, `--mux` | Passed: 1, 14 and 26 tests |
| `--qualification` | Passed: 18 tests (before the wrapper integration: 6 expected failures) |
| `--network` (offline, provider, TLS fixture, CA off and on, budgets, concurrency, cleanup, real `agy` tool call through the relay, TUI) | Passed: 21 tests |
| default (unrestricted runtime suite) | Passed: 16 tests, including the five-file build context, image smoke, no bus and file token storage. A first run failed because the runner mounted the project read-only; the default mode now mounts it read-write, as before |
| `openspec validate add-network-egress --strict`, `git diff --check` | Valid, clean |
| markdownlint | No findings except MD013 (line length), which the existing README already had; the repository has no markdownlint configuration |

The provider acceptance ran `agy --dangerously-skip-permissions -p` with a
synthetic key under `controlled-gemini-api`: the request to
`generativelanguage.googleapis.com` went through the relay and the production
proxy to the TLS fixture, trusted through the host CA bundle; the returned
`run_command` call wrote the workspace sentinel, and the second turn returned
`fixture-tool-complete`.

No container, network or volume labeled `io.antigravity-container` remained
after the runs; pre-existing containers were untouched.

Operator-run authenticated checks (Google account sign-in, token reuse and
refresh, model requests and `/logout` under `google-account`; Gemini API-key
requests under `gemini-api`) are pending until all Waves are complete. They
also decide whether `google-account` needs another host.

## Guided setup (`add-container-setup`): 2026-11-10

Target as in the network egress port (WSL2 kernel 6.6.87.2, Landlock ABI 3,
Podman client 4.3.1 and server 4.9.3, Netavark). Shared files at
`claude-container` `sandbox-ref-9` (commit `8b191e5`). Images:
`localhost/antigravity-cli:latest` `8084f5fea2ba…`,
`localhost/antigravity-egress:local` `13adbfafd7bd…`, toolchain
`0b69ba43c894…`.

`sandbox-ref-9` was created for this change. `agy` 1.5.3 has no login
subcommand, so the `account` method declares empty `login_args`, and setup
offers sign-in inside the interactive `agy` through the installed wrapper.
Codex, OpenCode and Pi adopted the tag before this copy, with `--shared` and
`--setup` (Pi also `--setup-runtime`) passing.

Found during apply: the shared smoke check requires a writable
`ANTIGRAVITY_CONTAINER_CONFIG_DIR`, but a fresh dedicated or isolated home has
no `.gemini` until `agy` runs. The wrapper now creates a private `.gemini` in
that home when it is missing, as the other wrappers create their configuration
directory, and leaves an existing one unchanged.

### Setup transcripts (provider mode, disposable `HOME`, no credentials)

| Run | Observed |
| --- | --- |
| `gemini`, no key | Residual exfiltration notice and acknowledgement; maintenance authorization; guard `abi3-seccomp-mux-v1` packaged; `Sandbox qualification: locally-qualified`; `Sandbox: ready`; `Authentication pending. Supply GEMINI_API_KEY`; the managed `--version` launch printed 1.5.3 |
| `account`, offer declined | `Run Antigravity account sign-in now? It opens Antigravity interactively; exit it when signed in.`; `Next authentication action: <managed command> (sign in inside the interactive session, ...)`; `Authentication: pending` |
| `account`, offer accepted | The installed wrapper started `agy` under the guard in provider mode with `google-account` (`network profile=google-account`); the TUI showed the sign-in menu and was quit with two Ctrl+C without signing in; setup reported `verified (Antigravity account interactive sign-in session exited successfully; no model request tested)` |
| `shared` state | Setup saved an empty state directory and `~/.gemini`; the managed shell saw `ANTIGRAVITY_CONTAINER_CONFIG_DIR=$HOME/.gemini` and wrote to the host `~/.gemini` (mode `0700`) |

The accepted-offer status reports that the session exited, not a confirmed
sign-in; real sign-in remains an operator check. A raw PTY driver in the test
sends Ctrl+C without the trailing newline of the shared `pty_run`, which would
otherwise select the first menu entry.

### Final verification

| Check | Result |
| --- | --- |
| `bash -n`, ShellCheck | Passed, no findings |
| `--wrapper` | Passed: 63 tests |
| `--shared` (includes `test_reference_copy.py` and `test_alignment.py`) | Passed: 148 tests, 27 skipped (run by the modes) |
| `--setup` (shared `test_setup.py`, unchanged) | Passed: 65 tests |
| `--setup-runtime` | Passed: 5 tests (fresh provider with rerun, offline and failed update; unrestricted and relocation; shared state; Gemini transcript; account sign-in declined and accepted) |
| `--qualification` | Passed: 18 tests |
| `--network` | 21 tests: one run had a `test_agent_budgets_are_effective_and_lifetime_cleans_owned_proxy` failure (the lifetime notice missed by the known whole-second `SECONDS` granularity); two reruns of that test passed |
| default (unrestricted runtime suite) | Passed: 16 tests |
| `openspec validate add-container-setup --strict`, `git diff --check` | Valid, clean |

The shared setup notice refers to a "Residual exfiltration" section of
`docs/network-contract.md`; this repository now has it. Codex, OpenCode and Pi
lack that section (a documentation gap for Wave 4).

Operator-run authenticated checks remain pending until all Waves are complete.

## Account profile hosts (`add-daily-cloudcode-host`): 2026-11-11

### Operator sessions (google-account)

In both sessions the operator signed in with a Google account in provider mode,
and the banner showed the account e-mail. The eligibility check then failed with
`Bad Gateway`, which the relay returns for every policy denial. The client
reports one failure at a time, so the sanitized denial logs are the complete
evidence. They contained only `policy-denied` entries, plus a final
`transport-closed` entry.

1. **Session `session.EPGcuRaMkTsB`**, policy `antigravity-2026-11-10-v1`.
   Failure: `Post "https://daily-cloudcode-pa.googleapis.com/v1internal:loadCodeAssist"`.
2. **Session `session.9TeqMf00VuXH`**, policy `antigravity-2026-11-11-v1`, with
   `daily-cloudcode-pa` allowed. The banner also showed the selected model
   (`Gemini 4 Argon (Medium)`). Failure:
   `Get "https://www.googleapis.com/oauth2/v2/userinfo"`.

| Host | Denials (session 1 / 2) | Decision |
| --- | --- | --- |
| `daily-cloudcode-pa.googleapis.com:443` | 11 / allowed | Allowed (default Cloud Code URL) |
| `www.googleapis.com:443` | 1 / 3 | Allowed (user information; general API host that also serves Drive) |
| `aicode.googleapis.com:443` | 0 / 2 | Allowed |
| `www.gstatic.com:443` | 0 / 2 | Allowed |
| `play.googleapis.com:443` | 3 / 4 | Allowed under `google-account` only (telemetry) |

The operator approved every host denied in these sessions. Under `gemini-api`,
telemetry and all account hosts stay denied. The proxy logs denials only, so
the logs cannot show whether `cloudcode-pa.googleapis.com` was used.

### Offline binary scan (`agy` 1.5.3, `--network none`)

- `https://daily-cloudcode-pa.googleapis.com` is embedded as the default Cloud
  Code URL, next to the CLI flag help. `cloudcode-pa.googleapis.com` appears
  five times.
- Sandbox variants: `autopush-cloudcode-pa.sandbox.googleapis.com` and
  `preprod-daily-cloudcode-pa.sandbox.googleapis.com`. Both stay denied.
- Overrides: `CLOUD_CODE_URL`, `cloud_code_endpoint` and
  `ForceUseCloudCodeAPI`. The wrapper neither sets nor forwards them.
- `www.googleapis.com` paths: `oauth2/v2/userinfo`, `oauth2/v3/tokeninfo`, Drive.
- `https://aicode.googleapis.com` sits next to `to get entitlement` and
  `Making Gateway request to`, and the binary contains the
  `https://www.googleapis.com/auth/aicode` OAuth scope.
- `www.gstatic.com` is referenced as `www.gstatic.com/antigravity/web/...`
  (scripts of the embedded web pages).

### Test defect found

The controlled TLS binding test passed the `google-account` hosts separated by
spaces. The shared fixture reads one comma-separated argument, so only
`oauth2.googleapis.com` was checked from `add-network-egress` onward. Codex,
Claude, OpenCode and Pi already pass comma-separated hosts. The test now passes
a comma-separated list and asserts that the fixture reports every host.

### Test results

| Check | Result |
| --- | --- |
| `bash -n`, ShellCheck | Passed, no findings |
| `--network-policy` | Passed: 14 tests. `tested` values stay within the 120-character limit; the session details are kept here |
| `--shared` (includes the exact base-profile check in `test_agent_profile`) | Passed: 148 tests, 27 skipped (run by the modes) |
| `--wrapper` (help names all seven account hosts and the telemetry treatment) | Passed: 63 tests |
| `--network` | Passed: 21 tests. Under `controlled-google-account`, TLS binding is asserted for all seven hosts, and the updater, `generativelanguage` and both sandbox variants are denied. Under `controlled-gemini-api`, telemetry and every account host are denied |
| `--setup-runtime` (the provider notice lists all seven account hosts) | Passed: 5 tests |
| `openspec validate add-daily-cloudcode-host --strict`, `git diff --check` | Valid, clean |
| markdownlint | No new findings except MD013 (line length) |

### Operator authenticated test (after the change)

On 2026-11-11, after requalifying with policy `antigravity-2026-11-11-v2`, the
operator reported that their authenticated `google-account` test passed. The
report did not list the individual steps.

Still open:

- Gemini API-key requests under `gemini-api`.
- Whether `cloudcode-pa.googleapis.com`, `aicode.googleapis.com` and
  `www.gstatic.com` are needed. The proxy logs denials only, so a passing
  session cannot show that a host went unused.

## Adoption of `sandbox-ref-10`: 2026-11-11

Copied from `claude-container` tag `sandbox-ref-10` (commit `0f6585f`):

- `network/agent_profile.py`, `setup/common.py`, `setup/setup.py`;
- `tests/test_agent_profile.py`, `tests/test_setup.py`.

The `tests/test_reference_copy.py` manifest moved to the tag. Antigravity has
no shared directories, so the profile keeps the default
`native.private_shared_dirs: false`. A failed setup smoke launch now shows the
wrapper's sanitized stderr.

| Check | Result |
| --- | --- |
| `bash tests/run-runtime.sh --shared` | Passed: 149 tests, 27 skipped (run by the modes) |
| `bash tests/run-runtime.sh --setup` | Passed: 68 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 5 tests |
| `bash tests/run-runtime.sh --wrapper` | Passed: 63 tests |

A first run of all wrappers' suites was interrupted by a host crash. Its
leftover test containers were removed before this run.

## Operator authenticated session: 2026-11-11

The operator ran an authenticated Antigravity session in provider mode with the
setup-default profile `google-account`. In the TUI, they asked the model to confirm
that it could use the harness tools and to report the sandbox's access limits.
The model did both, and the operator found the result correct.

The session ran on policy `antigravity-2026-11-11-v2`, after `add-daily-cloudcode-host` allowed the hosts that the first two sessions saw denied.

This covers an authenticated model request with tool use through the sandbox.
Token refresh, `/logout` and the `gemini-api` key checks remain pending. Full profile verification under the readiness checklist is not
claimed. The checklist also covers streaming and long-lived requests,
WebSockets, sign-in, token reuse and refresh, CA behavior and shell mode.

## Adoption of `sandbox-ref-12` and lab-host fixes (`adopt-lab-host-fixes`): 2026-11-12

Copied from `claude-container` tag `sandbox-ref-12` (commit `fd196c9`),
adopted directly from `sandbox-ref-10`:

- `network/.containerignore`, `network/README.md`, `network/agent_budgets.py`;
- `network/control.py`, `network/guard-build.Containerfile`, `network/guard.c`;
- `network/proxy.py`, `network/proxy_hardening.py`;
- `network/qualification_peer.py`, `network/qualification_probe.py`,
  `network/qualification_records.py`, `network/qualification_runtime.py`;
- `network/qualify.py`, `network/session.py`;
- `setup/setup.py`, `setup/smoke.py`;
- `tests/test_guard.py`, `tests/test_network_policy.py`,
  `tests/test_qualification.py`, `tests/test_session.py`, `tests/test_setup.py`.

The `tests/test_reference_copy.py` manifest moved to the tag.

Antigravity adaptations, equivalent to the other wrappers' ports:

- the delegation response accepts a Podman 5 `unix://` host socket report;
- each budget is requested only when its cgroup controller is delegated,
  with notices, and the inspection requires enforced budgets and no
  unenforced one;
- the `/run/secrets` and `/dev/shm` read-only masks;
- `--read-only-tmpfs=false` is removed;
- the `build-ca` secret is passed to the build;
- Debian packages are fetched over verified HTTPS;
- `/workspace` is created in the image.

Antigravity also passes the optional `build-ca` secret to the agy artifact
download (`curl --cacert`), keeping the SHA-512 check.

**PTY defect found and fixed.** The reference layout also mounts its own
`/dev` tmpfs and `--mount type=devpts,destination=/dev/pts`. That `devpts`
gets the kernel defaults `mode=600,ptmxmode=000`, so no pseudo-terminal can be
opened inside the session ("out of pty devices"). agy runs tool commands in a
PTY, and `test_actual_agy_tool_with_synthetic_gemini_api` failed: the tool
command never wrote its sentinel. Podman rejects `ptmxmode` as a `devpts`
mount option. Antigravity therefore leaves `/dev` to the engine, whose
`devpts` has `ptmxmode=666,mode=620`, and keeps only the `/dev/shm` mask. The
new runtime test `test_pseudo_terminals_and_device_masks` fails on the
previous layout and passes now.

The same defect exists in the Claude, Codex, OpenCode and Pi launchers. It is
latent there, because their tested tools do not open a PTY, and is fixed in
follow-up changes. Trade-off: on Podman 5, `/dev` is the engine's writable
tmpfs without the extra `noexec`. On Podman 4.9 it stays read-only.

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 350 tests, 72 skipped |
| `python3 -m unittest discover -s tests -p test_wrapper.py` | Passed: 69 tests, 1 skipped. New: socket URL and invalid `unix://` values, controller subsets, unverifiable lists, enforced or unenforced inspection, device masks without an explicit `/dev` or `devpts` in every mode, proxy mask and budgets, build secret with and without trust |
| `python3 -m unittest tests.test_image_pins` | Passed: 8 tests (transport, toolchain, workdir and artifact-download checks with mutations) |
| `bash tests/run-runtime.sh --shared` | Passed: 167 tests, 28 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 71 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 5 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 27 tests |
| `bash tests/run-runtime.sh --guard` | Passed: 20 tests, 1 skipped (the 305-second idle check) |
| `bash tests/run-runtime.sh --network` | Passed: 21 tests, including `test_actual_agy_tool_with_synthetic_gemini_api`. It failed with the explicit `devpts` |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 17 tests, including `test_pseudo_terminals_and_device_masks` |
| Runtime image `localhost/antigravity-cli:adopt-ref-12` | Built with the wrapper's build arguments (`--no-cache`), image `132d6f14c7c5`. Debian sources `https://`, no bootstrap bundle or `/tmp/agy`, agy `1.5.3`, OpenSpec `1.16.0`. `/workspace` is in the exported layer (build time 17:34), unchanged by a `keep-id` start at 17:35 |
| `bash -n` on the launcher, entrypoint and test scripts; `git diff --check`; `openspec validate adopt-lab-host-fixes --strict` | Passed, clean, valid |
| Operator `--container-setup` and a session on this host, the Rocky Linux 9 lab host (Podman 5: terminal attach with the engine's `/dev`) and the newer WSL host, provider profile | Passed (operator-reported, 2026-11-12): setup completed on all three hosts, and the operator interacted with the model in an attached terminal session on each |

Every restricted installation must rebuild and rerun setup. The project is
not distributed, so the operator may clean existing state instead.

## Adoption of `sandbox-ref-17` and the toolchain library (`adopt-sandbox-ref-17`): 2026-11-14

Copied from `claude-container` tag `sandbox-ref-17` (commit `a23f155`),
adopted directly from `sandbox-ref-12`:
`network/agent_profile.py`, `network/control.py`,
`network/qualification_records.py`, `setup/common.py`,
`tests/test_alignment.py`, `tests/test_qualification.py`,
`setup/toolchains.py`, `tests/test_toolchains.py`.
The `tests/test_reference_copy.py` manifest moved to the tag.

A first apply of this change targeted `sandbox-ref-16` and was paused before
any commit. In the real-engine check, a toolchain that set
`DBUS_SESSION_BUS_ADDRESS` reached the session. On this host's engine
(Podman server 4.9.3), `--unsetenv` does not remove a value given with
`--env`. The reference fixed this in `sandbox-ref-17`:

- the bus variable is protected in every wrapper;
- a variable protected only by another wrapper's profile is left out of the
  session with a warning, instead of stopping every launch.

The uncommitted branch was discarded, and its wrapper-owned work was
reapplied as a patch on the regenerated branch.

Wrapper port of the reference toolchain library (claude-container
`add-toolchain-library`; Codex `adopt-sandbox-ref-14`, OpenCode and Pi
`adopt-sandbox-ref-16`):

- `--container-toolchain add|list|remove|verify`, dispatched before the
  network mode and accepted only as the first argument;
- `ANTIGRAVITY_CONTAINER_TOOLCHAINS`, parsed like the other boolean settings,
  and `ANTIGRAVITY_CONTAINER_TOOLCHAINS_DIR`;
- the library checked against the workspace (or worktree parent) and the one
  writable state directory (the dedicated or isolated home, or the shared
  `~/.gemini` or `ANTIGRAVITY_CONTAINER_CONFIG_DIR`) before any image or
  container operation. It is skipped for the qualification probe;
- the read-only `/toolchains` mount (`ro,nosuid,nodev`), with
  `--mount-target /toolchains` in restricted modes;
- default toolchain `PATH` entries appended after the image `PATH`, read from
  the session image's `.Config.Env`;
- the toolchain environment placed before `AGY_CLI_DISABLE_AUTO_UPDATE=true`,
  so the launcher's value wins.

The README has a "Toolchains" section. Its instruction line names `GEMINI.md`
or `AGENTS.md`: the `agy` binary of the current image contains both names,
and which files it loads was not verified without credentials. The example
recipes are linked in claude-container.

`tests/run-runtime.sh` mounts a private executable tmpfs at
`/sandbox-test-tmp` as `SANDBOX_TEST_TMPDIR`, and `tests/test_wrapper.py`
creates its fixtures there.

Fixture adaptations required by the new mount:

- `tests/test_wrapper.py`:
  - the setup sets a synthetic `HOME` below the base, so the default library
    never lands in the caller's real home;
  - an exposed home (unsafe-workspace override) stops on the library overlap,
    and passes with `ANTIGRAVITY_CONTAINER_TOOLCHAINS=0`;
  - the bare copy without the diagnostics filter has no `setup/`, so it runs
    with `ANTIGRAVITY_CONTAINER_TOOLCHAINS=0`;
  - the host-mount count is three (workspace, state home, library);
  - the restricted fixture installs `setup/common.py` and
    `setup/toolchains.py`;
- `tests/fake_podman.py` answers the image `.Config.Env` inspection;
- `tests/test_runtime.py`: each test gives the wrapper a private home on the
  native state root, because the runner's `HOME=/tmp` is world-writable and
  the library refuses it;
- `tests/test_network_runtime.py`: the installation gains `setup/common.py`
  and `setup/toolchains.py`.

| Check | Result |
| --- | --- |
| New `tests/test_wrapper.py` cases with the launcher of `main` | Failed as intended (dispatch, private creation and mount, unsafe library including the worktree parent and the three state modes, disabled mount, appended `PATH`, `AGY_CLI_DISABLE_AUTO_UPDATE` order, restricted `--mount-target`, home workspace overlap, mount count) |
| `python3 -m unittest tests.test_reference_copy tests.test_toolchains tests.test_alignment` (private tmpfs), including the agent-identifier scans and profile variables | Passed: 38 tests |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 386 tests, 76 skipped (the runtime tests are opt-in) |
| `bash tests/run-runtime.sh --shared` | Passed: 168 tests, 28 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 71 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 5 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 28 tests |
| `bash tests/run-runtime.sh --guard` | Passed: 20 tests, 1 skipped (the 305-second idle check) |
| `bash tests/run-runtime.sh --network` | Passed: 22 tests, including a toolchain added on the host during an offline session, usable without direct network |
| `bash tests/run-runtime.sh --wrapper` | Passed: 76 tests |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 20 tests, including archive and image sources, a failing check, the read-only mount, the image's `node` and `python3` kept first, `AGY_CLI_DISABLE_AUTO_UPDATE=true` kept against a toolchain, and the omitted mount |
| Timing-sensitive checks | `test_lifetime_argument_and_notice` (synthetic) and `test_session_lifetime_limit_and_early_exit` (real engine) each failed once during development: exit status 255 without the lifetime notice. Both are unchanged by this adoption; each passed three isolated reruns and the full runs above |
| Five-wrapper parity table | Identical to claude-container's (`sandbox-ref-17`) |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host, `java -version` with the Temurin 21 toolchain, and `--container-toolchain verify java21` | Passed (operator-reported, 2026-11-14): `main` pushed; setups and both Temurin 21 checks passed |

Runtime image: `localhost/antigravity-cli:setup-cf551a6ade444811a7d732156d5aa0c0`
as `ANTIGRAVITY_CONTAINER_IMAGE`. Qualification digests the launcher and
`setup/toolchains.py`, so restricted installations rerun `--container-setup`.

## Adoption of `sandbox-ref-18`: 2026-11-15

Copied from `claude-container` tag `sandbox-ref-18` (commit `958465b`):
`network/agent_profile.py`, `setup/common.py`, `setup/toolchains.py`,
`tests/test_agent_profile.py`, `tests/test_alignment.py`, `tests/test_setup.py`,
`tests/test_toolchains.py`.
The `tests/test_reference_copy.py` manifest moved to the tag.

`sandbox-ref-18` adds the optional profile field `native.protected_env`, runs
the toolchain check in `/`, refuses an isolated state directory that overlaps
the workspace on managed launches, and makes the alignment test check the
launcher's code and its help text separately. The shared tests passed
without adapting an Antigravity fixture.

Antigravity changes, from the cross-wrapper review of 2026-11-14:

- **Agent variables:** `agent/profile.json` declares `AGY_`, `ANTIGRAVITY_`,
  `GEMINI_` and `GOOGLE_API_KEY`. A default toolchain could previously set
  `GEMINI_BASE_URL` or other `AGY_` controls in Antigravity sessions;
  `launch-env` now leaves them out with a warning, and `add` rejects them.
  `AGY_CLI_DISABLE_AUTO_UPDATE` is now dropped from the toolchain
  environment instead of only being overridden later, so
  `test_antigravity_settings_win_over_toolchain_variables` in
  `tests/test_wrapper.py` expects the toolchain value to be absent with one
  warning, and its `tests/test_runtime.py` counterpart expects `add` to
  reject the recipe and the session to keep `true`.
- **Name collisions (M2):** after a failed create without an ID, an existing
  container with the candidate name is a collision only when its session
  label differs. This session's own container is reported as the creation
  failure and removed in cleanup, instead of being left behind while the
  wrapper tried the next name.
- **Label recovery (M2):** when creation was interrupted or failed without a
  published ID, cleanup looks up the session label (`ps --all --no-trunc
  --filter label=…`), confirms exactly one ID by inspecting its label, and
  removes it. A failed lookup, several IDs or an unconfirmed label keep the
  "creation outcome unresolved" report.
- **Client wait:** `wait_for_client_until` polls `child_running` instead of
  `kill -0`, as Codex and Pi do.

`tests/fake_podman.py` now answers the session-label lookup and label
inspection. The new tests (`test_toolchain_cannot_set_agent_variables`,
`test_owned_name_is_not_a_collision`,
`test_interrupted_creation_is_recovered_by_label`) fail on `main` and pass on
the branch.

| Check | Result |
| --- | --- |
| `shellcheck antigravity-container.sh` | Same warning as on `main` (SC2054) |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 393 tests, 77 skipped |
| `bash tests/run-runtime.sh --shared` | Passed: 169 tests, 28 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 72 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 5 tests |
| `bash tests/run-runtime.sh --qualification` (not in the tool's checklist; shared `setup/` modules are qualified code) | Passed: 28 tests |
| `bash tests/run-runtime.sh --wrapper` | Passed: 79 tests (after adapting the settings test) |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 20 tests (after adapting the settings test) |
| Five-wrapper parity table | Identical to claude-container's (`sandbox-ref-18`) |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (2026-11-15, reported by the operator after the push) |

Runtime image: setup image `0c215fe6ecee`
(`localhost/antigravity-cli:setup-cf551a6a…`), tagged
`localhost/antigravity-cli:latest` only for the runs and untagged by name
afterwards. Shared qualified code changes, so restricted installations rerun
`--container-setup`.

## Adoption of `sandbox-ref-20`: 2026-11-16

`sandbox-container` is now the reference (it replaced `claude-container`).
Copied from `sandbox-container` tag `sandbox-ref-20` (commit `d4fd4ca`) with
`tools/propagate.py`: `network/README.md`, `network/agent_profile.py`,
`network/policy.py`, `network/qualification_records.py`, `network/qualify.py`,
`network/session.py`, `setup/common.py`, `setup/setup.py`, `setup/toolchains.py`,
`tests/sandbox_profile.py`, `tests/test_agent_profile.py`, `tests/test_alignment.py`,
`tests/test_guard.py`, `tests/test_qualification.py`, `tests/test_session.py`,
`tests/test_setup.py` and the fixture profiles in `tests/fixtures/`. The
`tests/test_reference_copy.py` manifest moved to the tag and names
`sandbox-container` as its sibling. Per-agent: `tests/test_setup_wrapper.py`
(copied from Claude), the lifetime notice measured with a monotonic clock
(`/proc/uptime`) from just before container creation plus a boundary test,
documents pointing at `sandbox-container`, parity table fixed by hand.

The first full run used the `EPOCHREALTIME` launcher: the default mode failed
`test_session_lifetime_limit_and_early_exit` (real 3 s expiry, status 255, no
notice), 2 of 10 isolated reruns failed the same way. WSL2 steps the wall clock
backwards (1.84 s measured), so the launcher now uses `/proc/uptime`; with it the
test passed 10 of 10 isolated runs, and the modes that run the launcher were
rerun.

Runtime image: `localhost/antigravity-cli:setup-9a4baafd86354976a2f08d429d70b0de`;
WSL2 6.6.87.2, Podman 4.9.3.

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 411 tests, 75 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 66 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 5 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 28 tests |
| `bash tests/run-runtime.sh --guard` | Passed: 20 tests, 1 skipped |
| `bash tests/run-runtime.sh --network` | Passed: 22 tests (rerun with the monotonic launcher) |
| `bash tests/run-runtime.sh --network-policy` | Passed: 15 tests |
| `bash tests/run-runtime.sh --network-feasibility` | Passed: 1 test |
| `bash tests/run-runtime.sh --wrapper` | Passed: 80 tests (rerun with the monotonic launcher) |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 20 tests (rerun with the monotonic launcher) |
| `git diff --check`, `bash -n antigravity-container.sh` | Passed |
| Operator `--container-setup` on the three hosts (`sandbox-ref-21`) | Passed (operator, 2026-11-16) |

## Adoption of `sandbox-ref-21`: 2026-11-16

Copied from `sandbox-container` tag `sandbox-ref-21` (commit `4b25eae`) with
`tools/propagate.py`: `tests/sandbox_profile.py`, `tests/test_guard.py`. The
`tests/test_reference_copy.py` manifest moved to the tag; parity table fixed by
hand. The shared guard runtime test now mounts the image's own native home
(`AGENT_HOME`) instead of the fixture profile's home.

Runtime image: `localhost/antigravity-cli:setup-9a4baafd86354976a2f08d429d70b0de`; WSL2 6.6.87.2, Podman 4.9.3.

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 411 tests, 75 skipped |
| `bash tests/run-runtime.sh --guard` | Passed: 20 tests, 1 skipped |
| `git diff --check` | Passed |
| Operator `--container-setup` on the three hosts (`sandbox-ref-21`) | Passed (operator, 2026-11-16) |

Only shared test files changed: installations need no new setup for this tag.

## Adoption of `sandbox-ref-24`: 2026-11-17

Change `adopt-sandbox-ref-24`. Copied with `tools/propagate.py` from
`sandbox-container` tag `sandbox-ref-24` (commit `dd5d82e`), straight from
`sandbox-ref-21`: `launcher/core.sh`, `tests/fake_podman.py` (replacing
Antigravity's own fake engine), `tests/fixtures/agent/launcher.sh`,
`tests/fixtures/shell-agent/launcher.sh`, `tests/test_launcher.py`,
`network/README.md`, `network/agent_profile.py`, `network/control.py`,
`network/qualification_records.py`, `network/qualify.py`, `setup/common.py`,
`setup/launch.py`, `setup/setup.py`, `tests/fixtures/agent/profile.json`,
`tests/sandbox_profile.py`, `tests/test_agent_profile.py`,
`tests/test_alignment.py`, `tests/test_network_policy.py`,
`tests/test_qualification.py`, `tests/test_setup.py`. The
`tests/test_reference_copy.py` manifest moved to the tag, with `launcher/` as a
closed shared directory; the parity table was fixed by hand.

- **Launcher:** `antigravity-container.sh` is the reference's thin entry script;
  `agent/launcher.sh` holds Antigravity's profile values,
  `AGENT_EXEC=/usr/local/bin/antigravity-entrypoint`, `AGENT_EXEC_TMP=1`,
  `AGENT_INSTALL_FILES=(container-entrypoint.sh)`, `AGENT_CREDENTIALS`
  (`gemini-api` with `GEMINI_API_KEY`, `google-account` without),
  `AGY_CLI_DISABLE_AUTO_UPDATE=true` as a fixed and reserved setting, the removal
  of `DBUS_SESSION_BUS_ADDRESS`, and two hooks: `agent_approval_bypass`
  (`--dangerously-skip-permissions`) and `agent_help`. `agent/profile.json`
  declares `native.exec` and `native.exec_tmp: true`.
- **State (U4):** shared `~/.gemini` is the default; the former default home
  `~/.local/share/antigravity-container/home` is used only when named in
  `ANTIGRAVITY_CONTAINER_STATE_DIR`.
- **Credentials:** offline sessions forward `GEMINI_API_KEY` only when
  `ANTIGRAVITY_CONTAINER_ENV_VARS` lists it, as the contract's reserved-name rule
  (M5, U13) allows; the change's deltas say so.
- **Temporary storage:** `/tmp` and the shared-state home are executable 512 MiB
  tmpfs mounts, `/var/tmp` and `/run` are `noexec`, and `/run` is not writable by
  the session user (L7, as for Codex).

Old tests gate (design decision 4): the `sandbox-ref-21` `tests/test_wrapper.py`
(80 cases) ran with its saved fake engine against the new entry script and core,
with only its harness adapted (the fake answers the `build-inputs-hash` label;
synthetic installations copy the core, the agent part, the relay inputs and the
policy; tmpfs options and removal arguments compare as sets; the old internal
`error` file is optional; the mount helper expects the classified `/run`
change). First run: 29 failing cases; after the harness adaptations: 23 failing
cases, each classified below. No lost behavior: three candidates were classified
as visible changes by the user (2026-11-17).

| Old case | Outcome | Maps to |
| --- | --- | --- |
| `test_application_status_survives_cleanup_failure` (removal failed or stalled) | visible change | wording: "cleanup rm failed or timed out" (U9 cleanup report); status preserved |
| `test_build_location_refresh_and_missing_image` | visible change | U8: an explicit build keeps the layer cache |
| `test_complete_socket_response_required` (`true /`, `true unix:///`) | visible change (user, 2026-11-17) | the core accepts a reported host socket path `/` and mounts the host root read/write at `/run/podman/podman.sock` |
| `test_creation_signal_ownership_races` (intermittent, mode=after) | visible change | U9: immediate shutdown terminates the create client; the CID may not be published |
| `test_explicit_temporary_mount_arguments` | visible change | L7: `/run` without mode 1777 (user, 2026-11-17, Codex) |
| `test_help_documents_hardening` | visible change | help text from the core |
| `test_help_documents_modes_migration_and_provider_limits` | visible change | U1: no migration text; hosts printed from the policy |
| `test_interrupted_creation_is_recovered_by_label` | visible change | wording of the core's cleanup reports |
| `test_key_forwarded_by_name_without_value_in_argv` | visible change | U10: unrestricted sessions forward no key unless listed |
| `test_missing_mode_stops_before_engine` | visible change | U1 provider default and its setup message |
| `test_mode_state_and_delegation_rejections_precede_engine` (provider settings, offline/provider + Podman) | visible change | phase 1-2 union: setup guidance before mode-specific settings |
| `test_mode_state_and_delegation_rejections_precede_engine` (STATE_DIR + CONFIG_DIR) | visible change | U4: the conflict message names both variables |
| `test_mode_state_and_delegation_rejections_precede_engine` (CONFIG_DIR = workspace parent) | visible change (user, 2026-11-17) | the core checks workspace overlap only for STATE_DIR, not for the configuration directory |
| `test_offline_order_arguments_and_forwarding` | visible change | the qualification check follows the name listing |
| `test_private_cid_ownership_and_collision_errors` | visible change | the core requires the create stdout ID to be valid and equal to the CID record; the created container is still removed |
| `test_proxy_image_acquisition_requires_maintenance_and_digest` (`--container-build` alone) | visible change | U16: build-only skips restricted preparation |
| `test_qualification_entry_points` | visible change | U4: no dedicated home default |
| `test_restricted_credentials_match_the_agent_profile` | visible change | source inspection of the old launcher; AGENT_CREDENTIALS (U10) |
| `test_setup_entry_point_is_dedicated_and_help_takes_precedence` | visible change | help text from the core |
| `test_shell_does_not_receive_yolo_or_cli_arguments` | visible change | U14: shell receives its arguments; still no bypass |
| `test_state_choices_and_configuration_directory` | visible change | U4: shared state by default |
| `test_state_preflight_failures_before_images` (pwd failure) | visible change (user, 2026-11-17) | the core exits 23 with no message when the state path cannot be resolved |
| `test_stubborn_sessions_and_control_failures_are_bounded` | visible change | U9 rewrite; wording |
| `test_timeout_prerequisite_without_help_side_effects` | visible change | wording ("GNU timeout is required") |
| `test_unrestricted_keeps_forwarding_without_bus` | visible change | U10 (DBus removal covered by the rewritten wrapper test) |

The other "to verify at adoption" cases passed against the core. The hook
cases `test_four_independent_permission_combinations` and
`test_antigravity_settings_win_over_toolchain_variables` passed and are
rewritten in the reduced `tests/test_wrapper.py`.

Environment: WSL2 6.6.87.2, Podman server 4.9.3 (client 4.3.1); image rebuilt
through the build-only path: `localhost/antigravity-cli:latest` `e263b4d334c2`,
`build-inputs-hash`
`d8e79c17c34f876d57866f6dcffce091f360c33d2009d4a447ef126416a514ea`; guard
toolchain tagged from the setup image of this host.

| Check | Result |
| --- | --- |
| `--container-build` alone (real engine, maintenance) | Passed: built, labeled, no session container |
| `python3 -m unittest tests.test_alignment tests.test_agent_profile tests.test_launcher` (disposable container) | Passed: 144 tests, 1 skipped |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 457 tests, 77 skipped |
| `bash tests/run-runtime.sh --wrapper` | Passed: 119 tests (`test_launcher.py`, `test_wrapper.py`) |
| `bash tests/run-runtime.sh --shared` | Passed: 295 tests, 29 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 67 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 5 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 29 tests |
| `bash tests/run-runtime.sh --network` | Passed: 22 tests |
| `bash tests/run-runtime.sh --guard` | Passed: 20 tests, 1 skipped |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 21 tests |
| `git diff --check`, `bash -n` on the entry script, core and agent part | Passed |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (operator, 2026-11-17) |

The installed and qualified code changes (entry script, core, agent part,
profile): installations rerun `--container-setup`.

## Adoption of `sandbox-ref-25`: 2026-11-18

Change `adopt-sandbox-ref-25`. Copied from `sandbox-container` tag `sandbox-ref-25`
(commit `6bed770`): `launcher/core.sh`, `setup/setup.py`, `tests/test_launcher.py`,
`tests/test_setup.py`. The `tests/test_reference_copy.py` manifest moved to the
tag; the parity rows were checked by hand.

With delegation enabled, the launcher and guided setup now refuse a reported host
socket path made only of slashes, and one that exists in the wrapper's namespace
as a non-socket (change `verify-delegated-socket-path` in `sandbox-container`). A
path the wrapper cannot see is still accepted as the remapped socket of a
containerized wrapper. No Antigravity file changed; the Antigravity tests ran
unchanged.

The old case `test_complete_socket_response_required` (`true /`, `true unix:///`),
recorded as a visible change in the `sandbox-ref-24` adoption, is now covered by
the shared case `test_reported_host_socket_must_be_a_socket_when_visible`: a
slash-only reported path fails before image operations and the host root is never
mounted.

Environment: WSL2 6.6.87.2, Podman server 4.9.3; image `localhost/antigravity-cli:latest`
`e263b4d334c2`, rebuilt through the build-only path (`build-inputs-hash`
`d8e79c17c34f876d57866f6dcffce091f360c33d2009d4a447ef126416a514ea`, unchanged).

| Check | Result |
| --- | --- |
| `python3 -m unittest tests.test_reference_copy tests.test_alignment` (host Python, siblings present) | Passed: 22 tests, no skips |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 458 tests, 77 skipped |
| `bash tests/run-runtime.sh --wrapper` | Passed: 120 tests |
| `bash tests/run-runtime.sh --setup` | Passed: 67 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 5 tests |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 21 tests |
| `git diff --check` | Passed |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (operator, 2026-11-18) |

The installed launcher core and setup change: installations rerun `--container-setup`.

## OpenSpec 2.0.0 image pin (2026-11-18)

For `pin-openspec-2-0-0`, OpenSpec 2.0.0 was the newest stable release at least
72 hours old on 2026-11-18. The `agy` pin stays at 1.5.3 because the 1.5.11
release had not met that age threshold. Both architecture-specific artifact
URLs and SHA-512 pins, the tested policy version, and the base digest
`sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da`
remain unchanged. The maintenance build verified the `agy` artifact checksum
and fetched Debian packages over HTTPS.

| Runtime image | Image ID | `agy --version` | `openspec --version` |
| --- | --- | --- | --- |
| Before | `e263b4d334c255b7d5fa046004ce351c92c6109cb645212377ec90603272f6e7` | `1.5.3` | `1.16.0` |
| After | `d7ebc9194ee1e9b2b408f09fa2e168b728050193b49d1b3c5d2fccc984be7801` | `1.5.3` | `2.0.0` |

Validation used WSL2 6.6.87.2 x86_64, Podman client 4.3.1, and the rootless
Podman 4.9.3 server through its same-host Unix socket. The updated runtime
image has build-inputs hash
`e28d7babf30d1121b98f3d49ae1ec14e422b2ae1434af96c05d69746676f4e49`.
The `agy` binary checksum and Debian package inventory matched between the two
images.

The reference ShellCheck runner reported the same 97 findings before and
after the change. The 26 in `agent/launcher.sh` comprise one SC2148 and 25
SC2034 findings. The remaining findings are in the shared
launcher core (14) and the agent and shell fixtures (32 and 25).

On a disposable, locally qualified offline installation, OpenSpec 2.0.0
initialized a temporary project with `--tools none`, created a change, passed
`openspec validate --all --strict --json`, and listed the change. The temporary
change used `skip_specs: true`. `agy --version` returned 1.5.3 under the same
guard (`abi3-seccomp-mux-v1`). The image smoke script passed in unrestricted
shell mode with synthetic state, exercising the image before the offline
launcher mounts its guard.

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -p test_image_pins.py` | Passed all 8 tests before and after the pin change |
| Host `tests.test_reference_copy` and `tests.test_alignment` | Passed all 22 tests with the reference checkout available |
| Credential-free unit discovery | Passed, 458 cases with 77 skips |
| `bash tests/run-runtime.sh` | Passed all 21 tests |
| `bash tests/run-runtime.sh --wrapper` | Passed all 120 tests |
| `bash tests/run-runtime.sh --shared` | Passed, 296 cases with 29 skips |
| `bash tests/run-runtime.sh --setup` | Passed all 67 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed all 5 tests in a serial rerun |
| `bash tests/run-runtime.sh --network-feasibility` | Passed |
| `bash tests/run-runtime.sh --network-policy` | Passed all 15 tests |
| `bash tests/run-runtime.sh --network` | Passed all 22 tests, including the `agy` TUI and the synthetic Gemini tool call |
| `bash tests/run-runtime.sh --mux` | Passed all 26 tests |
| `bash tests/run-runtime.sh --qualification` | Passed all 29 tests |
| `bash tests/run-runtime.sh --guard` | Passed, 20 cases with the idle case run separately |
| `bash tests/run-runtime.sh --guard-idle` | Passed the real 305-second idle and resume case |
| `--container-qualify` after all runner modes | Disposable offline installation returned `locally-qualified` with the new image ID |
| `git diff --check` | Passed |
| `openspec validate pin-openspec-2-0-0 --strict` | Passed |

The first `--setup-runtime` run overlapped other Podman suites. The first
provider setup failed qualification after a race for the container name
`project-0`. The entire setup suite passed when rerun on its own.

## Adoption of `sandbox-ref-28`: 2026-11-22

Change `adopt-sandbox-ref-28`, from `sandbox-ref-25` directly. It takes in
`sandbox-ref-26`, `sandbox-ref-27` and `sandbox-ref-28`:
- the process rlimit fallback and systemd-only cgroup delegation;
- the shared launcher files passing ShellCheck;
- Windows support on a Podman machine;
- the Windows setup guidance for agent wrappers.

Copied from `sandbox-container` tag `sandbox-ref-28` (commit `ba1ef14`):
- updated: `launcher/core.sh`, `network/README.md`, `network/agent_budgets.py`,
  `network/control.py`, `network/guard.c`, `network/proxy_hardening.py`,
  `network/qualification_probe.py`, `network/qualification_records.py`,
  `network/session.py`, `setup/common.py`, `setup/launch.py`, `setup/setup.py`,
  `setup/smoke.py`, `tests/fake_podman.py`, both fixture `launcher.sh`,
  `tests/test_alignment.py`, `tests/test_guard.py`, `tests/test_launcher.py`,
  `tests/test_qualification.py`, `tests/test_session.py` and
  `tests/test_setup.py`;
- added: the five `launcher/windows/` files, `tests/test_windows_bootstrap.py`,
  `tests/test_windows_enter.py` and `tests/windows/shim_tests.ps1`.

The `tests/test_reference_copy.py` manifest moved to the tag. The tool also
rewrote the OpenCode and Pi parity rows, which stay on `sandbox-ref-25`; they
were restored by hand.

By hand, as `docs/propagation.md` says:
- `antigravity-container.ps1` is a byte-for-byte copy of
  `sandbox-container.ps1`;
- `.gitattributes` was copied. The LF rewrite changed nothing: every tracked
  file was already LF in the index and the working tree;
- `agent/launcher.sh` gained the ShellCheck header of the reference agent part,
  which clears its 26 findings (25 `SC2034`, 1 `SC2148`).

Antigravity's own tests changed where the shared behavior did, as in Claude
and Codex:
- `tests/test_setup_wrapper.py` is the Claude and Codex file, byte for byte:
  the files were identical before. It adds a failing `systemctl`, the budget
  plan with the rlimit fallback and `cgroupfs`, and the case for setup without
  a launch service;
- `tests/test_runtime.py`: the budget checks follow the delegated controllers
  and the process mechanism, and the process probe uses a budget of 128 with
  200 children.

`test_build_context_allows_only_required_inputs` also changed, by the
operator's decision. It copied its inputs with `shutil.copyfile`, which drops
the entrypoint's executable bit, then required `test -x` in the image. On this
runner it failed on `main` too, with the old and the rebuilt image, so the tag
did not cause it; it had passed on 2026-11-18 on another host. It now copies
with `shutil.copy2`, which keeps the mode.

The README, `docs/setup.md` and `AGENTS.md` cover:
- the Windows entry for Antigravity, with the sign-in inside an interactive
  `agy` session, `$env:GEMINI_API_KEY` and `modelProvider`;
- the installer;
- host CA trust on Windows;
- the Windows limits, including Bitdefender and `agy`'s internal sandbox, not
  measured in the machine;
- the `cgroupfs` budgets, the rlimit fallback and the guard as init;
- the setup changes.

**This runner.** WSL2 `6.18.58.1-microsoft-standard-WSL2`, Podman server
4.9.3, the `systemd` cgroup manager and controllers `[cpu memory pids]`.
- The engine had no `localhost/antigravity-cli:latest`. Its two `setup-*` tags
  of image `22fa19363fe8` predate the OpenSpec 2.0.0 pin (`build-inputs-hash`
  `d8e79c17...`, inputs `e28d7bab...`). The adoption changes no build input.
- `localhost/antigravity-cli:latest` `c8eafdb59869` was rebuilt with
  `--container-build`, `build-inputs-hash` `e28d7bab...`, `agy` 1.5.3 and
  OpenSpec 2.0.0. The runner's network intercepts TLS, so the build used host
  CA trust with the session's CA bundle as the build secret.
- For the guard toolchain,
  `localhost/antigravity-guard-toolchain:setup-8bb44eb5e9604540bb1b2290d99b688e`
  was also tagged `localhost/antigravity-guard-toolchain:development`, the name
  that `--guard`, `--qualification` and `--network` use.

| Check | Result |
| --- | --- |
| `python3 -m unittest tests.test_reference_copy tests.test_alignment` (host Python, siblings present) | Passed: 26 tests, no skips |
| `bash tools/shellcheck.sh ../antigravity-container`, `bash tools/powershell.sh ../antigravity-container` (from `sandbox-container`) | Passed: no finding, 62 shim cases |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 513 tests, 85 skipped. A first run, while other Podman work loaded the computer, failed five boundary attempts of the timing-sensitive shared `test_lifetime_notice_preserves_status`, which passed in `--wrapper`; the rerun on its own passed |
| `bash tests/run-runtime.sh --wrapper` | Passed: 124 tests, 1 skipped |
| `bash tests/run-runtime.sh --shared` | Passed: 311 tests, 35 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 88 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 5 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 31 tests |
| `bash tests/run-runtime.sh --guard` | Passed: 25 tests, 1 skipped (`--guard-idle`) |
| `bash tests/run-runtime.sh --network` | Passed: 22 tests, including the `agy` TUI and the synthetic Gemini tool call |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 21 tests, including the budget checks above and the build-context test with the fix above |
| `git diff --check` | Passed |

**Windows** (operator, 2026-11-22 and 2026-11-23). Windows WSL 3.0.5.0, kernel
6.18.58.1-1, Landlock ABI 7. The Podman Desktop machine
`podman-machine-default` uses the `cgroupfs` manager, with Ubuntu running. The
checkouts were snapshots of this branch and of `sandbox-container` in
`C:\Work`.

| Step | Result |
| --- | --- |
| Setup from `antigravity-container.ps1`: provider networking with the `account` method, shared state, host CA trust with `/etc/ssl/certs/ca-certificates.crt`, permission bypass on, images refreshed, sign-in postponed | The plan printed `enforced agent budgets: none`, the `cgroupfs` notices and the process rlimit for the agent (512) and the proxy (128). Images prepared in the machine, `Sandbox qualification: locally-qualified`, `Sandbox: ready`. The next step read `Next authentication action: antigravity-container.ps1 (sign in inside the interactive session, or reuse your selected existing account state).`, with no distribution path |
| Sign-in from a project folder | The machine's `~/.gemini` already held a sign-in from an earlier setup. After `/logout`, a new `antigravity-container.ps1` session signed in again through Google's URL and code, with the URL opened in a Windows browser (confirmed by the operator; the TUI screens are not in the copied window text) |
| An `agy` session with tool use | Provider session with `google-account`, `agy` 1.5.3. `agy` ran `find` on the project and read its file, then ended with Ctrl+C; `$LASTEXITCODE` 0. `podman ps -a` then listed no container of the session |
| Token reuse | A second session started signed in and answered `Say hello`; `$LASTEXITCODE` 0 |
| `windows-validate.ps1 -Checkout C:\Work\antigravity-container -Install -StopMachine`, Windows PowerShell 5.1 | 55 passed, 0 failed, 1 skipped (restricted mode without a prepared installation, because setup saved provider). Installer, user `PATH`, uninstall, stopped machine, a distribution started by WSL alone, the restart with Podman, "Offline qualification", "Offline session", "Redirected input" and "One engine for sessions and the machine" passed |
| The same without `-Install -StopMachine`, PowerShell 7.7.0 | 43 passed, 0 failed, 3 skipped |
| `gemini` method with a dummy key | Setup said `Set $env:GEMINI_API_KEY = '...' in PowerShell before antigravity-container.ps1`. The provider session used `gemini-api`; `--container-shell -c 'echo "$GEMINI_API_KEY"'` printed the value. `antigravity-container.ps1 -p 'Say hello' --print-timeout 60s --settings '{"modelProvider":"gemini"}'` reached `generativelanguage.googleapis.com`, which answered `API_KEY_INVALID` (HTTP 400): the JSON argument crossed PowerShell intact, and the proxy and the CA trust worked. A real-key model request is unavailable. Setup then returned to the `account` method |

Notes:

- **Denied hosts in provider sessions.** With `google-account`, `agy` fetches
  the account picture from `lh3.googleusercontent.com`; with `gemini-api` it
  tries `play.googleapis.com`. The proxy refuses both (`policy-denied`), as the
  profiles require. The sessions are unaffected.
- **The `transport-closed` diagnostic.** At session end, the
  `recent protected egress diagnostics` line with `transport-closed` is the
  behavior already recorded on Linux.
- **A leftover qualification probe.** `podman ps -a` in the machine listed a
  container in the `Created` state, `nice_perlman`, from image
  `localhost/antigravity-cli:setup-1d2b933d03744fb88d0bee2f6a0d732c`, running
  `python3 -I -c` with the setup's security probe (`ipv6_state`). It comes
  from an earlier Antigravity setup in the machine, whose candidate tag
  remained, and it was there before the sessions of this run. It is not a
  session container; `podman rm` removes it.
- **A shared setup prompt prints its fallback text letter by letter.** The
  state-mode prompt reads `shared n, o,  , o, t, h, e, r configuration`, as
  recorded for Codex. It is cosmetic and is left to a reference fix.
- **The machine keeps the method of the last setup.** The operator reruns
  setup to return to the `account` method.

The installed launcher core, setup and guard change, so installations rerun
`--container-setup`.
