# Antigravity CLI in Podman

Run Google's official Antigravity CLI (`agy`) in a rootless Linux Podman
container. The wrapper follows the workflow of
[claude-container](https://github.com/yarilc/claude-container) and
[codex-container](https://github.com/yarilc/codex-container).

The default session exposes the current project and a dedicated application
home. YOLO and access to the host Podman service are independent opt-ins.

## Requirements and first run

The host needs Linux, Bash 4.3+, Podman with a rootless engine, and standard
utilities (`id`, `readlink`, `dirname`, `mkdir`, `sed`, `stat`, `mktemp`). No host Node,
Python, Google CLI, browser service, or keyring service is required. Network
access is needed to build the image, sign in, and contact model services.
Linux amd64 is verified in the recorded test environment. Linux arm64 is an
intended target but remains unverified because no arm64 test environment is
currently available. Actual results and limitations are recorded in
[docs/validation.md](docs/validation.md).

```bash
chmod +x antigravity-container.sh
./antigravity-container.sh --container-build --version
cd /absolute/path/to/your-project
/absolute/path/to/antigravity-container/antigravity-container.sh
```

You can replace the native command with an alias:

```bash
alias agy=/absolute/path/to/antigravity-container/antigravity-container.sh
agy --help
agy --container-shell
agy --container-help
```

The wrapper handles only `--container-build`, `--container-shell`,
`--container-git-worktree`, and `--container-help`. Other arguments retain their
order, spaces, and empty values when forwarded to `agy`. Shell mode starts
Bash instead of `agy` and ignores CLI arguments. Help for the wrapper requires
no engine and creates no state. Non-interactive CLI invocation does not
allocate a TTY; stdin is preserved.

## Authentication

Application state lives in a separate home, not the host's generic `~/.gemini`.
Settings are at
`~/.local/share/antigravity-container/home/.gemini/antigravity-cli/settings.json`
on the host by default. The container sees them under
`/antigravity-home/.gemini/antigravity-cli/settings.json`.

For account sign-in, launch from an interactive terminal. The entrypoint starts
a private D-Bus session and a GNOME Secret Service keyring in the container.
Choose and confirm a nonempty passphrase when creating the keyring. On later
launches, unlock it with the same passphrase. The passphrase is read without
echo from the terminal, separately from CLI stdin; it is not saved in files,
environment variables, or command arguments. An incorrect passphrase stops
startup. Help and version do not require unlocking.

The account path requests Google's remote sign-in flow using a process-local
SSH environment marker, so authorization can use an external browser and a
code entered in the terminal. No host SSH client, SSH agent, display, D-Bus,
or keyring is mounted. Google account login, token reuse, and `/logout` must
be verified with an actual account; see the validation record for current
coverage. A successful Secret Service test alone does not establish working
Google OAuth.

Keyring files and Google token profiles persist in the dedicated application
home. Keep this directory private and protect its backups. Newly created
directories use user-only permissions; existing directory permissions are not
changed recursively. The state directory must belong to the caller and deny
group/other access. Startup fails if it is not private; run `chmod 700` on an
existing directory or select native Linux storage if the filesystem ignores
Unix permissions (for example, some WSL Windows drive mounts). The keyring uses passphrase protection; application
profiles and other state follow Google's native storage behavior. Do not
assume every file in this directory is encrypted. `/logout` uses the CLI's
native account logout behavior. Removing a container does not remove its
persistent state.

For automation without a terminal, select the native API key provider. Open
the dedicated settings file and merge this setting into its JSON object:

```json
{
  "modelProvider": "gemini"
}
```

Export `GEMINI_API_KEY` in the calling shell, then run:

```bash
agy -p "Describe this repository" --print-timeout 60s
```

The wrapper forwards an existing key by name without printing it or reading
host credential files. A key alone does not select the provider. Missing keys
produce native CLI diagnostics. Session-only `--settings` provider selection
is also recognized by the entrypoint. Removing `modelProvider` restores account
sign-in. ADC and enterprise setup are outside this version's scope.

## Permissions

| `ANTIGRAVITY_YOLO` | `ANTIGRAVITY_CONTAINER_PODMAN` | Behavior |
| --- | --- | --- |
| disabled | disabled | Native CLI approvals; no host Podman socket |
| enabled | disabled | Approval bypass; no host Podman socket |
| disabled | enabled | Native CLI approvals; host Podman access |
| enabled | enabled | Approval bypass and host Podman access |

```bash
agy
ANTIGRAVITY_YOLO=1 agy
ANTIGRAVITY_CONTAINER_PODMAN=1 agy
ANTIGRAVITY_YOLO=1 ANTIGRAVITY_CONTAINER_PODMAN=1 agy
```

Both booleans accept `1`, `true`, or `yes`, and `0`, `false`, or `no`, ignoring
case. Empty/unset means disabled; other values fail before build or launch.
YOLO adds Google's `--dangerously-skip-permissions` without modifying saved
settings. Disabling this variable does not override permission flags supplied
directly to `agy` or existing settings. Google's internal terminal sandbox
(`--sandbox`) is separate from approvals and from container isolation. Its
availability depends on the host kernel and namespace policy.

### Known internal sandbox incompatibility

Antigravity CLI 1.4.12 failed to execute sandboxed terminal commands in the
tested Linux amd64 / WSL2 environment with rootless Podman 4.9.3 and its
standard seccomp profile. The CLI reported a sandbox server connection reset;
its log identified the underlying failure:

```text
sbox: sethostname: operation not permitted
```

The default profile blocks `sethostname` without `CAP_SYS_ADMIN`, including
when the CLI attempts it inside a nested user namespace. Basic namespace and
Bubblewrap checks succeeded, so those checks alone do not establish that
Google's internal sandbox is usable. The CLI returned exit code 0 despite
the failed tool call; verify the actual operation and its output.

The project retains Podman's standard seccomp policy and does not provide a
custom-profile override or add capabilities to work around this issue. On
the tested setup, omit `--sandbox` and keep the native
`enableTerminalSandbox` setting disabled. Normal approval checks remain
available, and the outer container still enforces its existing mount,
identity, and read-only root filesystem boundaries. YOLO remains a separate
choice about native approvals.

This finding applies to the tested versions and environment. Recheck internal
sandbox compatibility after relevant CLI or engine updates; see the evidence
and accepted limitation in [docs/validation.md](docs/validation.md).

**The Podman socket grants control over containers, volumes, and host bind
mounts available to the service user. With the socket enabled, the agent can
access host paths beyond this project's mount.** This delegation cannot enforce
project-only filesystem access. The wrapper never starts a nested daemon,
uses `--privileged`, or automatically disables seccomp or SELinux.

Enable the host rootless service only when you want this delegation:

```bash
systemctl --user start podman.socket
# Alternatively, without systemd:
podman system service --time=0 "unix://${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock"
```

The foreground alternative occupies its terminal; start the agent from
another terminal. With socket access disabled, no service socket is required.
If SELinux blocks the socket or project bind, the wrapper reports the engine
error. Configure an appropriate host policy; it does not automatically relabel
the project or disable labels. SELinux enforcing support requires separate
validation.

## Mounts, worktrees, and identity

The physical current directory is mounted read/write at the same absolute path
inside the container. It remains the working directory. The wrapper does not
search for a Git root. With `--container-git-worktree`, it mounts the immediate
parent instead:

```bash
cd /projects/repository/main
agy --container-git-worktree
agy --container-git-worktree --container-shell
```

This exposes all of `/projects/repository`, including sibling worktrees,
read/write, while starting in `/projects/repository/main`. Git metadata outside
that parent is not exposed. Launch from the worktree root when its shared
metadata is in the common parent. Launching from a nested subdirectory selects
a different parent. If the selected parent is the host home or `/`, the flag
exposes that entire directory.

Absolute paths are preserved because the host service resolves bind sources
for child containers. The process uses `--userns=keep-id` and the caller's
UID/GID, so files created in the project belong to the caller. The container
root is read-only; workspace and application state are writable, with ephemeral
tmpfs storage at `/tmp` and `/run`. `/tmp` allows execution for native runtime
components; `/run` uses `noexec`. No full host home, host OpenSpec settings,
host certificates, or SSH configuration is mounted automatically.

Each session reserves a workspace-index name and removes its own container at
termination. Existing sessions are not deleted to resolve a name collision.
Separate state directories provide separate authentication profiles. An account
session holds an exclusive lock on its keyring directory to prevent independent
daemons from overwriting a shared collection. Another account session using
that state fails with an actionable message; choose a different
`ANTIGRAVITY_CONTAINER_STATE_DIR` for concurrent account sessions. Shell sessions
and the API provider do not acquire this keyring lock.

The wrapper can itself run inside a container connected to the same Linux host
through a local Unix Podman socket. Its workspace and state paths must also
exist on that host at exactly the same absolute paths. For socket delegation,
the wrapper uses the service-reported host socket path as the bind source.
TCP/SSH transports, named remote connections, Podman Machine, and rootful
engines are rejected.

## Environment

| Variable | Default |
| --- | --- |
| `ANTIGRAVITY_CONTAINER_IMAGE` | `localhost/antigravity-cli:latest` |
| `ANTIGRAVITY_CONTAINER_STATE_DIR` | `${HOME}/.local/share/antigravity-container/home` |
| `ANTIGRAVITY_YOLO` | disabled |
| `ANTIGRAVITY_CONTAINER_PODMAN` | disabled |
| `ANTIGRAVITY_CONTAINER_PODMAN_SOCKET` | `${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock` |

When the wrapper already uses a local Unix `CONTAINER_HOST`, that accessible
socket is the default service endpoint instead. An explicit
`ANTIGRAVITY_CONTAINER_PODMAN_SOCKET` takes precedence. `GEMINI_API_KEY` and
terminal `TERM` are the only caller variables explicitly forwarded by name;
the entire environment and `.env` files are not imported by the wrapper.
`EDITOR` and `VISUAL` use the included nano editor.

## Image and dependencies

The base is `docker.io/library/node:22-bookworm-slim`: Debian 12 provides glibc
2.36, exceeding the Linux thresholds published on Google's download page, and
Node 22 runs OpenSpec. This is the project's choice, not an image prescribed
by Google. `agy` is installed as a native executable using the
[official installer](https://antigravity.google/cli/install.sh), including its
platform manifest and SHA-512 verification. No npm Antigravity substitute,
graphical IDE, Python SDK, or browser is installed.

| Group | Packages/tools | Purpose |
| --- | --- | --- |
| Installer/ABI | bash, ca-certificates, curl, coreutils, sed, grep, tar, gzip, libc6, libstdc++6, libgcc-s1 | Official installer operations, HTTPS, archive extraction, native compatibility |
| Local credentials | dbus, gnome-keyring, libsecret-1-0, libsecret-tools | Linux Secret Service and credential checks without host services |
| Workflow additions | Node 22/npm, `@fission-ai/openspec`, python3, bubblewrap, podman | Reference-project workflow tools; Bubblewrap is not claimed as a Google CLI requirement |
| Repository additions | git, ripgrep, findutils, diffutils, patch, gawk, nano, less, jq | Local Git, searching, editing, and JSON settings |
| Archive/diagnostic additions | bzip2, xz-utils, zip, unzip, file, procps, util-linux | Archive support, ABI/process checks, and local diagnostics |

Package dependencies may also install supporting libraries. The verification
script checks the executable and available libraries rather than treating IDE
dependencies as CLI requirements.

Sources: [Google quickstart](https://antigravity.google/docs/getting-started?tab=cli),
[download requirements](https://antigravity.google/download),
[CLI reference](https://antigravity.google/docs/cli/reference),
[authentication](https://antigravity.google/docs/install?tab=cli),
[troubleshooting](https://antigravity.google/docs/cli/troubleshooting),
[sandbox](https://antigravity.google/docs/sandbox/), and
[Podman API security](https://docs.podman.io/en/latest/markdown/podman-system-service.1.html).

## Updates and rollback

`agy` automatic updates are disabled with `AGY_CLI_DISABLE_AUTO_UPDATE=true`.
The binary belongs to the read-only image. To update, preserve the current
image and explicitly rebuild:

```bash
podman tag localhost/antigravity-cli:latest localhost/antigravity-cli:previous
agy --container-build --version
# Roll back the executable and toolchain:
ANTIGRAVITY_CONTAINER_IMAGE=localhost/antigravity-cli:previous agy --version
```

An absent image is built automatically. Explicit builds use `--no-cache` to
recheck the official release rather than reusing an old download layer.
The build prints CLI and OpenSpec versions and binary architecture. It tracks
the current official release and does not promise bit-for-bit reproducibility.
State persists across image updates; back it up separately if you need to
restore application data as well as the executable.

## Verification

Run wrapper tests using standard-library Python on the host or in a suitable
container:

```bash
python3 -m unittest discover -s tests -p test_wrapper.py -v
ANTIGRAVITY_RUNTIME_TESTS=1 python3 -m unittest discover -s tests -p test_runtime.py -v
# On filesystems without Unix permissions, or without host Python:
bash tests/run-runtime.sh
```

The second command uses real rootless Podman and temporary directories under
`.test-state/`, exercising image checks, mount boundaries, ownership,
worktrees, child containers, keyring persistence, and native startup diagnostics.
It uses only dummy secrets and does not complete Google account authentication
or submit paid model requests. Manual OAuth and model-request results, the
known internal sandbox incompatibility, and outstanding architecture/SELinux
checks are recorded in [docs/validation.md](docs/validation.md).
