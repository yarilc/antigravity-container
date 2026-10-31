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

The final automated run passed **19 wrapper tests and 9 runtime tests**.
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

The image's `/run` directory is not writable by the non-root process. The
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
