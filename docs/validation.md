# Validation record

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
