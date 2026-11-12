# Antigravity CLI in Podman

Run Google's official Antigravity CLI (`agy`) in a rootless Linux Podman
container. The wrapper follows the workflow of
[claude-container](https://github.com/yarilc/claude-container) and
[codex-container](https://github.com/yarilc/codex-container).

The default session exposes the current project and a dedicated application
home. Every launch selects a network mode: `offline`, `provider` (an
exact-destination egress proxy) or `unrestricted`. YOLO and access to the host
Podman service are independent opt-ins.

## Requirements

The host needs Linux, Bash 4.3+, Podman with a rootless engine, and standard
utilities (`id`, `readlink`, `dirname`, `mkdir`, `sed`, `stat`, `mktemp`, and coreutils `timeout`). No host Node,
Google CLI, browser service, or keyring service is required. The restricted
modes (`offline`, `provider`) also need host Python 3, a same-host rootless
Podman 4.9 or later Unix service with Netavark, and Landlock ABI 3 or later;
see [Network modes](#network-modes). Network access is needed to build the
image, sign in, and contact model services.
Linux amd64 is verified in the recorded test environment. Linux arm64 is an
intended target but remains unverified because no arm64 test environment is
currently available. Actual results and limitations are recorded in
[docs/validation.md](docs/validation.md).

## Enable rootless Podman on the host

Run this setup on the Linux host (or inside your Linux/WSL distribution),
using the same non-root account that will run `antigravity-container.sh`.
Install Podman and its rootless dependencies using your distribution's
[installation instructions](https://podman.io/docs/installation).
The account needs subordinate UID/GID ranges in `/etc/subuid` and
`/etc/subgid`, the `newuidmap`/`newgidmap` helpers, and a rootless networking
backend supported by the installed Podman version. If these are missing,
complete the administrator steps in the
[rootless setup guide](https://github.com/podman-container-tools/podman/blob/main/docs/tutorials/rootless_tutorial.md)
before continuing.

Check that local rootless Podman works:

```bash
podman info --format '{{.Host.Security.Rootless}}'
podman run --rm docker.io/library/alpine:latest id
```

The first command must print `true`; the second must successfully start a
container. Root inside that container is normal for rootless Podman.

The host API socket is required only when you enable delegation with
`ANTIGRAVITY_CONTAINER_PODMAN=1`. With delegation disabled, local rootless
Podman is sufficient: skip the socket setup and proceed to [First run](#first-run).

For delegation, the default socket is
`${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock`. You can select another
socket with `ANTIGRAVITY_CONTAINER_PODMAN_SOCKET`; an existing local Unix
`CONTAINER_HOST` is used by default when no explicit socket override is set.
Choose **one** of the following methods to start the host service.

### With a systemd user session

From a normal login session for your account, enable socket activation:

```bash
systemctl --user enable --now podman.socket
systemctl --user status podman.socket --no-pager
```

Systemd creates the socket and its parent directory, and starts the API
service when a client connects. An inactive `podman.service` between requests
is normal. To keep the user service available after logout and start it at
boot, optionally enable lingering:

```bash
sudo loginctl enable-linger "$(id -un)"
```

If `systemctl --user` reports that it cannot connect to the bus, ensure you
are logged in directly as the intended user with a working systemd user
session. On systems without systemd, use the manual procedure below.

### Without systemd: create the directories and start the service

An error such as
`bind: no such file or directory` when creating the socket means that a
parent directory is missing. The socket file itself is created by Podman;
do not create it with `touch`.

In a terminal on the host, prepare the runtime directory. On systems without
a login manager, `/run/user/<uid>` may also be absent; creating it under
`/run` usually requires administrator privileges:

```bash
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
if [ ! -d "$XDG_RUNTIME_DIR" ]; then
    sudo install -d -m 0700 -o "$(id -u)" -g "$(id -g)" "$XDG_RUNTIME_DIR"
fi
ls -ld "$XDG_RUNTIME_DIR"
```

The directory must belong to your account and have mode `0700`
(`drwx------`). If an existing directory has incorrect ownership or
permissions, have the administrator correct it before continuing. Then run
the following as your normal user:

```bash
install -d -m 0700 "$XDG_RUNTIME_DIR/podman"
podman system service --time=0 "unix://$XDG_RUNTIME_DIR/podman/podman.sock"
```

Leave this terminal open and use a second terminal for the checks and wrapper
commands below. The service runs in the foreground; Ctrl+C stops it.
Repeat this setup after reboot because `/run` is temporary. Export the same
`XDG_RUNTIME_DIR` in any other terminal used to run local Podman if your
session does not set it automatically. Run the service and wrapper without
`sudo` so they use your rootless containers and configuration.

### Verify the socket before enabling delegation

For either method, run these commands as the same user in the terminal where
you will launch the wrapper:

```bash
podman_socket="${ANTIGRAVITY_CONTAINER_PODMAN_SOCKET:-${CONTAINER_HOST#unix://}}"
podman_socket="${podman_socket:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock}"
test -S "$podman_socket" && echo "Socket exists"
podman --remote --url "unix://$podman_socket" info
```

Enable delegation only if the socket exists and the API command succeeds.
A socket file alone does not prove that a service is listening. If the API
command fails, check the systemd status or the foreground service output above.
See also the official
[Podman API service documentation](https://docs.podman.io/en/latest/markdown/podman-system-service.1.html).

### Launch preflight diagnostics

Before image inspection or build, the wrapper requires a complete single-record
engine response confirming Linux, rootless `true`, and a valid remote-service
boolean. Missing fields, extra fields, additional lines (including blank lines),
query failures, rootful engines, and non-Linux engines stop startup.
An explicit Unix launch endpoint must contain an absolute socket path;
`CONTAINER_HOST=unix:///`, `unix:////`, and longer slash-only paths are rejected
before contacting Podman. A valid example is
`CONTAINER_HOST=unix:///run/user/1000/podman/podman.sock`. Named remote
connections, TCP/SSH transports, and implicit remote contexts are unsupported.
A local engine or an explicit same-host Unix service is supported, including
when this wrapper runs inside another container. Launch-engine selection is
independent of any optional delegation socket override.

## First run

New users run guided setup once, from a reviewed checkout, in an interactive
terminal:

```bash
bash ./antigravity-container.sh --container-setup
cd /absolute/path/to/your-project
"$HOME/.local/bin/antigravity-container"
```

Setup asks for the network mode, the authentication method (`account` or
`gemini`), state, budgets and optional authority. It prepares the images and the
guard under maintenance consent, installs a protected release with a managed
launcher, qualifies restricted modes and runs a credential-free smoke check. For
`account` it offers to open `agy` for the Google sign-in; for `gemini` it names
`GEMINI_API_KEY`. See [docs/setup.md](docs/setup.md). An ordinary launch with no
`ANTIGRAVITY_CONTAINER_NETWORK` stops with `setup required:` guidance.

### Direct operator launches

```bash
chmod +x antigravity-container.sh
export ANTIGRAVITY_CONTAINER_NETWORK=unrestricted
ANTIGRAVITY_CONTAINER_MAINTENANCE=1 ./antigravity-container.sh --container-build --version
cd /absolute/path/to/your-project
/absolute/path/to/antigravity-container/antigravity-container.sh
```

Every direct launch needs an explicit `ANTIGRAVITY_CONTAINER_NETWORK`; without
one the wrapper stops with setup guidance before any engine call. Every image build, including the build of
a missing image, needs the exact `ANTIGRAVITY_CONTAINER_MAINTENANCE=1`.

You can replace the native command with an alias:

```bash
alias agy=/absolute/path/to/antigravity-container/antigravity-container.sh
agy --help
agy --container-shell
agy --container-help
```

The wrapper handles only `--container-build`, `--container-shell`,
`--container-git-worktree`, `--container-qualify`, `--container-setup`, and
`--container-help`. Other arguments retain their
order, spaces, and empty values when forwarded to `agy`. Shell mode starts
Bash instead of `agy` and ignores CLI arguments. Help for the wrapper requires
no engine and creates no state. Non-interactive CLI invocation does not
allocate a TTY; stdin is preserved.

## Network modes

| Mode | Agent access | Host Podman delegation |
| --- | --- | --- |
| unset or empty | Launch stops before engine calls and state creation | No session |
| `offline` | Own loopback, pipes and connected socket pairs only | Rejected |
| `provider` | As offline, plus one channel to an exact-destination proxy | Rejected |
| `unrestricted` (explicit only) | Ordinary networking, as before this mode switch | Exact opt-in allowed |

Restricted modes run a native guard (Landlock plus seccomp) as the first
process, deny new Unix sockets and every direct route, and never fall back to
unrestricted networking. YOLO, settings files, `modelProvider` and shell mode
cannot broaden them. Before the first restricted launch, prepare the operator
inputs and qualify the installation:

```bash
# Guard toolchain, guard and proxy image (maintenance steps):
podman tag <reference toolchain image> localhost/antigravity-guard-toolchain:development
ANTIGRAVITY_CONTAINER_MAINTENANCE=1 bash network/build-guard.sh "$PWD/network/bin"
ANTIGRAVITY_CONTAINER_MAINTENANCE=1 podman build --tag localhost/antigravity-egress:local \
    --file network/Containerfile network
ANTIGRAVITY_CONTAINER_NETWORK=offline ./antigravity-container.sh --container-qualify
```

Provider mode also needs `ANTIGRAVITY_CONTAINER_NETWORK_PROFILE`,
`ANTIGRAVITY_CONTAINER_NETWORK_POLICY` (normally `agent/policies/default.json`),
a private native `ANTIGRAVITY_CONTAINER_NETWORK_RUNTIME_DIR` and the immutable
`ANTIGRAVITY_CONTAINER_EGRESS_IMAGE`, and its own qualification:

| Profile | Destinations | Credential |
| --- | --- | --- |
| `google-account` | `oauth2.googleapis.com:443`, `cloudcode-pa.googleapis.com:443`, `daily-cloudcode-pa.googleapis.com:443`, `www.googleapis.com:443`, `aicode.googleapis.com:443`, `www.gstatic.com:443`, `play.googleapis.com:443` | account tokens in the state home |
| `gemini-api` | `generativelanguage.googleapis.com:443` | `GEMINI_API_KEY` |

Restricted sessions receive no host proxy or CA variable; only `gemini-api`
forwards `GEMINI_API_KEY`. `AGY_CLI_DISABLE_AUTO_UPDATE=true` is protected, and
the proxy denies the update hosts. Telemetry (`play.googleapis.com`; the
`telemetryEnabled` setting does not stop it on 1.5.3) is denied under
`gemini-api` and allowed under `google-account`, which the operator sessions
showed needs it.

**Allowed services can receive data.** The proxy binds the TLS server name to
the allowed host, but it cannot tell your credentials from an attacker's: an
injected agent can send workspace data to an allowed host with its own Gemini
API key or Google account. Only `offline` removes this channel. Provider-hosted
tools such as web search run at Google, outside the local boundary. Image
builds and pulls happen outside runtime filtering, under maintenance.

Qualification reports are local and bound to the boot, the engine and its
security settings, the installed code and images, the policy and profile, CA
trust and the budgets. A reboot or any such change requires
`--container-qualify` again; an unidentifiable active SELinux or AppArmor
policy forces the gate on every launch. The shipped release acceptance
inventory is empty, so installations report `locally-qualified`. The full
contract is in [docs/network-contract.md](docs/network-contract.md), and the
shared mechanism in [network/README.md](network/README.md).

### Migration

- Set `ANTIGRAVITY_CONTAINER_NETWORK=unrestricted` to keep the previous
  networking, and add `ANTIGRAVITY_CONTAINER_MAINTENANCE=1` to commands that
  build the image.
- The private D-Bus session and GNOME keyring were removed: `agy` now keeps
  account tokens in files. Accounts signed in through the keyring sign in again
  once. The old keyring files stay in the state home
  (`.local/share/keyrings/`); delete them after the new sign-in if you no
  longer need them.
- `ANTIGRAVITY_CONTAINER_PODMAN=1` works only with `unrestricted`.

## Authentication

Application state lives in a dedicated home, not the host's generic
`~/.gemini`, unless you select shared state. Settings are at
`~/.local/share/antigravity-container/home/.gemini/antigravity-cli/settings.json`
on the host by default. The container sees them under
`/antigravity-home/.gemini/antigravity-cli/settings.json`.

| `ANTIGRAVITY_CONTAINER_STATE_DIR` | State |
| --- | --- |
| unset | Dedicated home `~/.local/share/antigravity-container/home` |
| a path | That private isolated home |
| empty | Shared host `~/.gemini` (or `ANTIGRAVITY_CONTAINER_CONFIG_DIR`) below an ephemeral home |

With shared state only `.gemini` persists; `agy` files under `~/.config`
(plugin secrets, user scope) last only for the session. Other tools that use
`~/.gemini`, such as Gemini CLI, then share their files with the container.

For account sign-in, launch from an interactive terminal and choose Google
OAuth. The container has no D-Bus session or keyring, so `agy` uses its file
token storage (`~/.gemini/antigravity-cli/antigravity-oauth-token`). A
process-local SSH environment marker requests Google's remote sign-in flow, so
authorization uses an external browser and a code entered in the terminal. No
host SSH client, SSH agent, display, D-Bus, or keyring is mounted, and no port
is published. Google account login, token reuse, and `/logout` must be verified
with an actual account; see the validation record for current coverage.

Account tokens and other state persist in the selected home. **They are
protected only by Unix permissions, not by a passphrase**, as in the other
wrappers: keep the directory private and protect its backups. State creation,
physical path resolution, ownership, access, and permission checks complete
after engine verification and before image inspection or build, including
explicit rebuilds. A new state directory can therefore remain after a later
image failure. The wrapper scopes its private creation umask to state directory
creation; this does not set the container process umask. Newly created
directories use user-only permissions; existing directory permissions are not
changed recursively. The state directory must belong to the caller and deny
group/other access. Startup fails if it is not private; run `chmod 700` on an
existing directory or select native Linux storage if the filesystem ignores
Unix permissions (for example, some WSL Windows drive mounts). `/logout` uses
the CLI's native account logout behavior. Removing a container does not remove
its persistent state.

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

The wrapper forwards an existing key by name, in unrestricted mode and with the
`gemini-api` profile, without printing it or reading host credential files. A
key alone does not select the provider. Missing keys produce native CLI
diagnostics. Session-only `--settings` provider selection also works. Removing
`modelProvider` restores account sign-in. ADC, Vertex AI and enterprise setup
are outside this version's scope.

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

`ANTIGRAVITY_YOLO` accepts `1`, `true`, or `yes`, and `0`, `false`, or `no`,
ignoring case. Empty/unset means disabled; other YOLO values fail before build
or launch. `ANTIGRAVITY_CONTAINER_PODMAN` enables delegation only for the exact
string `1`. Every other value (including `true`, `yes`, `01`, and `maybe`)
disables delegation without error, in CLI and shell modes.

**Migration:** replace previously enabling `ANTIGRAVITY_CONTAINER_PODMAN=true`
or `yes` with `ANTIGRAVITY_CONTAINER_PODMAN=1` to retain host service access.
When disabled, delegation socket overrides are ignored and `CONTAINER_HOST` is
explicitly removed from the container environment, including image or engine
defaults. The wrapper retains its own launch-engine connection.

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

In restricted modes the guard's filter and the dropped capabilities also stop
Bubblewrap from creating namespaces (`Failed to make / slave: Operation not
permitted`). Commands still run inside the guarded container, which is the
boundary; the guard is never relaxed for the internal sandbox.

This finding applies to the tested versions and environment. Recheck internal
sandbox compatibility after relevant CLI or engine updates; see the evidence
and accepted limitation in [docs/validation.md](docs/validation.md).

**The Podman socket grants control over containers, volumes, and host bind
mounts available to the service user. With the socket enabled, the agent can
access host paths beyond this project's mount.** This delegation cannot enforce
project-only filesystem access. The wrapper never starts a nested daemon,
uses `--privileged`, or automatically disables seccomp or SELinux.

Enable and verify the host rootless service using the
[host setup instructions](#enable-rootless-podman-on-the-host) only when you
want this delegation. With socket access disabled, no service socket is required.
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
tmpfs storage provisioned explicitly. Automatic read-only tmpfs provisioning
stays enabled, because Podman 5 with crun 1.27 cannot attach a terminal to a
read-only `/dev`: the engine provides `/dev` and a `devpts` that allows
pseudo-terminals, which agy uses to run tool commands. An explicit `devpts`
mount would get `ptmxmode=000` and no pseudo-terminal could be opened. `/dev/shm`
is masked with an empty read-only tmpfs, so tools that need POSIX shared memory
there are not supported. An empty
read-only tmpfs at `/run/secrets` masks engine default mounts there (for
example RHEL subscription certificates from `mounts.conf`). `/tmp` allows execution for native runtime components and has a
512 MiB limit; `/var/tmp` uses `noexec` with a separate 512 MiB limit; `/run`
uses `noexec` with a 32 MiB limit. All three use `nosuid,nodev`, writable mode
`1777`, and disappear with the container. Restricted sessions also mount the
guard and its session inputs read-only. No full host home, host OpenSpec
settings, host certificates, or SSH configuration is mounted automatically.

Each session reserves a workspace-index name. Creation records the full owned
container ID in a private CID file independently of client stdout. A signal
during creation prevents attachment: the wrapper waits up to five seconds for
creation, then bounds client cancellation and reads the CID again. It removes
only a verified owned ID. An unresolved remote creation outcome is reported
for manual inspection; a guessed name is never used for deletion. Existing
sessions are not removed to resolve a name collision.

TERM/INT/HUP are forwarded once to the attached owned session and produce
exit status 143/130/129. The first handled signal determines the result;
repeated signals do not restart shutdown. After successful forwarding, the
application has up to five seconds to exit gracefully before forced removal.
Engine forwarding and removal calls each use a five-second deadline with
one-second KILL escalation. Local client termination allows five seconds
before KILL and at most one second for final observation/reaping. These are
separate phase budgets, not a five-second total shutdown promise. Ordinary
builds and running sessions have no imposed runtime limit.

Cleanup reports failures without replacing the primary application or signal
status, including application exit 125. If removal fails, inspect the reported
owned ID and remove it manually once the engine is reachable. Temporary
creation output and ownership bookkeeping are removed on handled exits.
SIGKILL, engine loss, or host failure can leave residual containers. An
uninterruptible kernel task is outside a userspace timing guarantee.
Separate state directories provide separate authentication profiles.
Concurrent sessions may share one state directory; `agy` writes its
configuration files atomically.

The wrapper can itself run inside a container connected to the same Linux host
through a local Unix Podman socket. Its workspace and state paths must also
exist on that host at exactly the same absolute paths. For socket delegation,
the selected path must be absolute before canonicalization and identify a
readable, writable Unix socket. The service must return one complete rootless
result and an absolute host socket path; extra response lines are rejected.
The wrapper uses that reported path as the bind source, preserving spaces and
supporting paths remapped inside an outer container.
TCP/SSH transports, named remote connections, Podman Machine, and rootful
engines are rejected.

### Session hardening, budgets and lifetime

Every agy and shell session, with or without Podman delegation and YOLO and in
both account and Gemini API-key modes, runs with `--cap-drop=all` and
`--security-opt=no-new-privileges`. The private D-Bus session, the dedicated
GNOME keyring, Bubblewrap, Git, OpenSpec and the delegated Podman client work
under these settings. The wrapper never adds capabilities back to work around
a tool; such a limitation is recorded in `docs/validation.md`. Delegation
still grants host engine authority beyond these limits.

Every session has memory, CPU and process budgets (defaults 4 GiB, 2 CPUs and
512 processes; see [Environment](#environment)). Only an unset variable selects
the default; no value disables a budget, and an invalid value stops the wrapper
before any engine query. Each budget is enforced only when the rootless engine
delegates its cgroup v2 controller (`memory`, `cpu`, `pids`), as reported by
`podman info` (`Host.CgroupControllers`). A missing controller leaves that
budget unenforced: the wrapper does not request it, prints a notice such as
`antigravity-container: agent CPU budget not enforced: cgroup controller cpu is
not delegated to the rootless engine`, and continues without a question.
Provider proxies follow the same rule for their 128-process and 256 MiB limits.
Without the memory or process budget, a session can exhaust host memory or
processes for your user. After creating the container, the wrapper checks that
every enforced budget was applied and that no unenforced one is present, and
stops before agy starts otherwise. Restricted qualification records the
enforced set, so a change in delegation requires requalification. Budgets and
tmpfs sizes do not limit workspace or state storage growth.

`ANTIGRAVITY_CONTAINER_RUN_TIMEOUT` optionally sets the session container
lifetime in whole seconds; unset, empty or `0` disables it. When the engine
stops a session at the limit, the wrapper prints
`antigravity-container: session lifetime limit reached (N s); exit status S`
and returns the Podman client status (255 on the measured Podman 4.9.3).

The writable workspace, or the `--container-git-worktree` parent, is refused
when its physical path is `/`, `/home`, `/root`, `/etc`, `/usr`, `/var`, `/bin`,
`/sbin`, `/lib`, `/lib64`, `/boot`, `/opt`, `/srv`, `/mnt`, `/media`, `/proc`,
`/sys`, `/dev`, `/run`, `/tmp`, your physical home directory, or a WSL drive
root such as `/mnt/d`. Subdirectories such as `/mnt/d/Workspace/project` are
allowed. Launch from a project directory, or set exactly
`ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` to expose a refused directory
deliberately; the wrapper then prints a warning.

## Environment

| Variable | Default |
| --- | --- |
| `ANTIGRAVITY_CONTAINER_NETWORK` | required: `offline`, `provider` or `unrestricted` |
| `ANTIGRAVITY_CONTAINER_NETWORK_PROFILE` | provider only: `google-account` or `gemini-api` |
| `ANTIGRAVITY_CONTAINER_NETWORK_POLICY` | provider only: absolute policy path |
| `ANTIGRAVITY_CONTAINER_NETWORK_RUNTIME_DIR` | provider only: private native directory |
| `ANTIGRAVITY_CONTAINER_EGRESS_IMAGE` | provider only: immutable proxy image ID or digest |
| `ANTIGRAVITY_CONTAINER_MAINTENANCE` | disabled; exact `1` authorizes builds and proxy pulls |
| `ANTIGRAVITY_CONTAINER_IMAGE` | `localhost/antigravity-cli:latest` |
| `ANTIGRAVITY_CONTAINER_STATE_DIR` | unset: `${HOME}/.local/share/antigravity-container/home`; empty: shared `~/.gemini` |
| `ANTIGRAVITY_CONTAINER_CONFIG_DIR` | `~/.gemini` with shared state; the session always sees `/antigravity-home/.gemini` |
| `ANTIGRAVITY_CONTAINER_TRUST_HOST_CA` | disabled; `1`, `true` or `yes` mounts one host CA bundle read-only |
| `ANTIGRAVITY_CONTAINER_CA_BUNDLE` | first of `/etc/ssl/certs/ca-certificates.crt`, `/etc/pki/tls/certs/ca-bundle.crt` |
| `ANTIGRAVITY_YOLO` | disabled |
| `ANTIGRAVITY_CONTAINER_PODMAN` | disabled |
| `ANTIGRAVITY_CONTAINER_PODMAN_SOCKET` | `${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock` |
| `ANTIGRAVITY_CONTAINER_MEMORY_LIMIT` | `4g` (positive integer with unit `k`, `m` or `g`) |
| `ANTIGRAVITY_CONTAINER_CPU_LIMIT` | `2` (positive number of CPUs, at most 3 decimals, up to 1024) |
| `ANTIGRAVITY_CONTAINER_PIDS_LIMIT` | `512` (integer from 1 to 4194304) |
| `ANTIGRAVITY_CONTAINER_RUN_TIMEOUT` | `0`, disabled (whole seconds) |
| `ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE` | disabled; only exact `1` enables it |

When the wrapper already uses a local Unix `CONTAINER_HOST`, that accessible
socket is the default service endpoint instead. An explicit
`ANTIGRAVITY_CONTAINER_PODMAN_SOCKET` takes precedence. `GEMINI_API_KEY` (by
mode, see [Network modes](#network-modes)) and terminal `TERM` are the only
caller variables explicitly forwarded by name;
the entire environment and `.env` files are not imported by the wrapper.
`EDITOR` and `VISUAL` use the included nano editor.

## Image and dependencies

The base is `docker.io/library/node:22-bookworm-slim`: Debian 12 provides glibc
2.36, exceeding the Linux thresholds published on Google's download page, and
Node 22 runs OpenSpec. This is the project's choice, not an image prescribed
by Google; the base is pinned by digest. `agy` is installed as a native
executable from a recorded official release artifact for amd64 or arm64, whose
URL and SHA-512 come from Google's platform manifest and are pinned in
`Containerfile` (`AGY_VERSION`, `AGY_URL_*`, `AGY_SHA512_*`). OpenSpec is pinned
by `OPENSPEC_VERSION`. Other architectures fail the build explicitly.
`tests/test_image_pins.py` rejects floating inputs. Debian packages are fetched
over verified HTTPS only, so image preparation needs outbound HTTPS (443) to the
Debian, npm, container and release registries, not port 80. With host CA trust
enabled, the selected bundle is passed to the build as the `build-ca` secret:
apt and the agy artifact download verify against it on TLS-intercepting
networks, the artifact SHA-512 check is unchanged, and the bundle is never
stored in a layer. The recipe creates `/workspace` in the image, so the engine
never creates or chowns the working directory when a container starts (this
fails for large domain UIDs under `keep-id`). No npm Antigravity substitute,
graphical IDE, Python SDK, browser, D-Bus daemon or keyring is installed. The
image also contains `network/relay.py` and `network/mux.py` at
`/opt/sandbox-egress/` for restricted sessions; the guard is never part of
the image.

| Group | Packages/tools | Purpose |
| --- | --- | --- |
| Download/ABI | bash, ca-certificates, openssl, curl, coreutils, sed, grep, tar, gzip, libc6, libstdc++6, libgcc-s1 | Artifact download and checksum, HTTPS, archive extraction, native compatibility |
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

## Image build context

`.containerignore` denies local build inputs by default. Only the root-level
`Containerfile`, `container-entrypoint.sh` and `.containerignore`, plus
`network/relay.py` and `network/mux.py`, are allowed. Unknown files, local configuration or credentials, state, and nested
directories stay excluded, including nested files with an allowed basename.
These rules apply independently of `.gitignore` and whether a file is tracked.

When adding a deliberate local COPY/ADD input, add its exact root-level entry
to the allowlist and extend the real build-context inventory regression. Do
not replace the deny-all policy with a growing list of sensitive exclusions.

## Updates and rollback

`agy` automatic updates are disabled with `AGY_CLI_DISABLE_AUTO_UPDATE=true`.
The binary belongs to the read-only image. To update, preserve the current
image and explicitly rebuild:

```bash
podman tag localhost/antigravity-cli:latest localhost/antigravity-cli:previous
ANTIGRAVITY_CONTAINER_MAINTENANCE=1 agy --container-build --version
# Roll back the executable and toolchain:
ANTIGRAVITY_CONTAINER_IMAGE=localhost/antigravity-cli:previous agy --version
```

An absent image is built only with `ANTIGRAVITY_CONTAINER_MAINTENANCE=1`.
Explicit builds use `--no-cache`, so
they download the recorded artifacts again and verify their checksums. The
build prints CLI and OpenSpec versions and binary architecture. It installs the
recorded `agy` release, not the latest published one; Debian packages are not
pinned, so builds are not bit-for-bit reproducible.

### Updating pinned image inputs

1. Read `https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/linux_amd64.json`
   and `linux_arm64.json` for the new release.
2. Record `AGY_VERSION`, both `AGY_URL_*` values and both `AGY_SHA512_*` values,
   and any new `OPENSPEC_VERSION` or base digest (from
   `podman image inspect --format '{{.Digest}}'` after pulling
   `docker.io/library/node:22-bookworm-slim`) in `Containerfile`.
3. Rebuild with `--container-build` and check `agy --version` and
   `openspec --version`.
4. Update `tested.cli` in `agent/policies/default.json` to the same version
   (`tests/test_image_pins.py` checks it), remeasure the Google hosts, rerun
   the credential-free suites and every `bash tests/run-runtime.sh` mode, and
   requalify. Verify account login manually.
5. Record the tested versions and results with the date in `docs/validation.md`.
State persists across image updates; back it up separately if you need to
restore application data as well as the executable.

## Verification

Run the checks in the runner, which uses the `agy` image and native volume
storage (a noexec `/tmp` or a Windows drive cannot hold the test fixtures):

```bash
bash tests/run-runtime.sh --wrapper        # wrapper behavior with a fake engine
bash tests/run-runtime.sh --shared         # shared suites and per-agent unit tests
bash tests/run-runtime.sh --guard          # guard runtime (also --guard-idle)
bash tests/run-runtime.sh --qualification  # local qualification
bash tests/run-runtime.sh --setup          # shared setup suite
bash tests/run-runtime.sh --setup-runtime  # real guided setup acceptance
bash tests/run-runtime.sh --network        # offline and provider acceptance
bash tests/run-runtime.sh                  # unrestricted runtime suite
```

`--network-feasibility`, `--network-policy` and `--mux` run single suites. The
runtime suites use real rootless Podman with temporary directories, exercising
image checks, mount boundaries, ownership, worktrees, child containers, the
absence of a bus or keyring, zero capabilities and no-new-privileges, effective
cgroup v2 budgets, the lifetime limit, the refused home workspace, the guard,
the proxy, TLS binding, CA trust, cleanup and a real `agy` tool call against a
synthetic Gemini endpoint. They use only dummy secrets and do not complete
Google account authentication or submit paid model requests. Manual OAuth and
model-request results, the known internal sandbox incompatibility, and
outstanding architecture/SELinux checks are recorded in
[docs/validation.md](docs/validation.md).
