# Antigravity CLI in Podman

Run Google's official Antigravity CLI (`agy`) in a rootless Linux Podman
container. The wrapper follows the workflow of
[claude-container](https://github.com/yarilc/claude-container) and
[codex-container](https://github.com/yarilc/codex-container).

The default session exposes the current project and the host's `~/.gemini`
below an ephemeral home. A launch runs in one network mode: `provider` (the
default, with an exact-destination egress proxy), `offline` or `unrestricted`.
Sessions use a private container engine when the toolchain library holds images.

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

Offline and provider launches need a same-host rootless Unix service. Guided
setup verifies or prepares it. A local rootless engine is sufficient for
unrestricted launches. The default launch socket is
`${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock`. An explicit same-host
Unix `CONTAINER_HOST` selects another endpoint. Choose a method below if
setup needs a launch service.

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

### Verify the launch service

For either method, run these commands as the same user in the terminal where
you will launch the wrapper:

```bash
podman_socket="${CONTAINER_HOST#unix://}"
podman_socket="${podman_socket:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock}"
test -S "$podman_socket" && echo "Socket exists"
podman --remote --url "unix://$podman_socket" info
```

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
when this wrapper runs inside another container. The launch service stays on the host.

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
`GEMINI_API_KEY`. See [docs/setup.md](docs/setup.md). A launch with no
`ANTIGRAVITY_CONTAINER_NETWORK` selects `provider`; without the provider settings
that setup saves, it stops with `setup required:` guidance.

### Direct operator launches

```bash
chmod +x antigravity-container.sh
export ANTIGRAVITY_CONTAINER_NETWORK=unrestricted
ANTIGRAVITY_CONTAINER_MAINTENANCE=1 ./antigravity-container.sh --container-build
cd /absolute/path/to/your-project
/absolute/path/to/antigravity-container/antigravity-container.sh
```

An unset or empty `ANTIGRAVITY_CONTAINER_NETWORK` selects `provider`, the default
for an agent wrapper; without a protected installation or the saved provider
settings the wrapper stops with setup guidance before any engine call. Every
image build, including the build of a missing image, needs the exact
`ANTIGRAVITY_CONTAINER_MAINTENANCE=1`.

A build pulls the exact `FROM` base first and then runs with `--pull=never`
and the docker format, without a timeout. Every image carries a
`build-inputs-hash` label over its build inputs (`Containerfile`,
`.containerignore`, `network/relay.py`, `network/mux.py`,
`container-entrypoint.sh`); a launch refuses an image built from other inputs and
names the rebuild command. `--container-build` without `agy` arguments, also
together with `--container-git-worktree` or `--container-shell`, validates every
setting, builds the image and exits without a session; setup uses this
operation. With `agy` arguments, it builds and then starts the session.

You can replace the native command with an alias:

```bash
alias agy=/absolute/path/to/antigravity-container/antigravity-container.sh
agy --help
agy --container-shell
agy --container-help
```

The wrapper handles only `--container-build`, `--container-shell`,
`--container-git-worktree`, `--container-qualify`, `--container-setup`,
`--container-toolchain` (first argument only, see [Toolchains](#toolchains))
and `--container-help`. Other arguments retain their
order, spaces, and empty values when forwarded to `agy`. Shell mode starts
Bash instead of `agy`, passes it the remaining arguments (for example
`--container-shell -c 'make test'`) and never adds the YOLO flag. Help for the
wrapper requires no engine and creates no state. Non-interactive CLI invocation
does not allocate a TTY; stdin is preserved.

The session receives `USER`, `EDITOR=nano`, `VISUAL=nano`,
`AGY_CLI_DISABLE_AUTO_UPDATE=true`, and by name `TERM`, `COLORTERM`, `LANG` and
`LC_ALL` when set; `DBUS_SESSION_BUS_ADDRESS` is removed. Unrestricted sessions
also receive `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY` and their
lowercase forms, run with `--init`, and see their container name as
`CONTAINER_NAME`. In offline and provider sessions the confined guard plays the
role of `--init`: Ctrl+C and the shutdown signals reach `agy`, and the session
ends with its status. `ANTIGRAVITY_CONTAINER_ENV_VARS` lists further host
variable names (separated by whitespace) to forward by name, never by value; an
invalid name stops the launch, an empty variable is not forwarded, and names
the launcher sets itself (and, in restricted modes, proxy, CA and provider settings,
or in provider mode another profile's credential) are skipped with a notice.

## Network modes

| Mode | Agent access |
| --- | --- |
| unset or empty | `provider`; without setup's saved provider settings the launch stops with setup guidance |
| `offline` | Own loopback, pipes and connected socket pairs only |
| `provider` | As offline, plus one channel to an exact-destination proxy |
| `unrestricted` (explicit only) | Ordinary networking |

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

Restricted sessions receive no host proxy or CA variable; provider mode forwards
`GEMINI_API_KEY` by name only with `gemini-api`, never with `google-account` or an
operator profile. Offline and unrestricted sessions get the key only when
`ANTIGRAVITY_CONTAINER_ENV_VARS` lists it. `AGY_CLI_DISABLE_AUTO_UPDATE=true` is protected, and
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

### Keyring migration

- The private D-Bus session and GNOME keyring were removed: `agy` now keeps
  account tokens in files. Accounts signed in through the keyring sign in again
  once. The old keyring files stay in the state home
  (`.local/share/keyrings/`); delete them after the new sign-in if you no
  longer need them.

## Authentication

By default the session shares the host's `~/.gemini` (or
`ANTIGRAVITY_CONTAINER_CONFIG_DIR`, an absolute path without colon, CR or LF),
mounted at `/antigravity-home/.gemini` below an ephemeral 512 MiB home. Settings
are at `~/.gemini/antigravity-cli/settings.json` on the host and
`/antigravity-home/.gemini/antigravity-cli/settings.json` in the container.

| `ANTIGRAVITY_CONTAINER_STATE_DIR` | State |
| --- | --- |
| unset or empty | Shared host `~/.gemini` (or `ANTIGRAVITY_CONTAINER_CONFIG_DIR`) below an ephemeral home |
| a path | That private isolated home, mounted at `/antigravity-home` |

A nonempty `ANTIGRAVITY_CONTAINER_STATE_DIR` conflicts with
`ANTIGRAVITY_CONTAINER_CONFIG_DIR`, must be absolute and must not overlap the
workspace; `.gemini` and the CA parent inside it must stay inside the home and
be private. Earlier versions defaulted to a separate home at
`~/.local/share/antigravity-container/home`; to keep using it, set
`ANTIGRAVITY_CONTAINER_STATE_DIR` to that path, or sign in again with the shared
`~/.gemini`. `ANTIGRAVITY_CONTAINER_READONLY_STATE` (`1`, `true` or `yes`) mounts
the existing configuration read-only instead; it must exist, nothing is created,
and `agy` cannot save sign-ins or sessions in such a launch.

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
the settings file in the selected state and merge this setting into its JSON object:

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

`ANTIGRAVITY_YOLO` accepts `1`, `true` or `yes`, and `0`, `false` or `no`,
ignoring case. An unset or empty value leaves native approvals enabled.
Unsupported values stop before image operations. Shell mode validates the
setting and starts Bash without agy arguments.

```bash
agy -p 'Check the project'
ANTIGRAVITY_YOLO=1 agy -p 'Check the project'
```

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

### Container tests

When the toolchain library contains an image, a session gets a private
rootless Podman engine at `tcp://127.0.0.1:2375` through `CONTAINER_HOST` and
`DOCKER_HOST`. The engine mounts the workspace at its original absolute
path and the library image store read-only. Nested containers have their own
process and hostname views. The engine and its writable storage are removed
when the session ends. The host launch socket and credential stores stay on
the host.

```bash
agy --container-toolchain add ~/recipes/alpine.json
agy --container-shell -c 'podman run --rm --network=none localhost/library-alpine:1 true'
```

See [Images](#images) for the example recipe. A new image becomes available
to a running engine. Adding the first image takes effect with the next
session. A library without images or `ANTIGRAVITY_CONTAINER_TOOLCHAINS=0`
leaves both connection variables absent.

- **Network.** The engine shares the session's network namespace and egress
  boundary. Offline nested containers have no external path. Use library
  images in offline and provider sessions. Unrestricted sessions can pull
  into ephemeral engine storage.
- **Workspace.** Files written inside a nested workspace bind belong to the
  caller. Other bind sources refer to the engine filesystem. A session with
  an engine sees the host's `/sys` read-only because it joins the engine's
  network namespace.
- **Budgets.** The engine receives the session's CPU, memory and process
  budgets for itself and its nested containers. The agy container has its
  own budgets. A process rlimit fallback applies where the host supports it.
- **Engine hardening.** The private engine uses the fixed user-namespace
  helper capabilities, `SYS_CHROOT`, FUSE and TUN, unmasked procfs, disabled
  SELinux labelling for the engine, and a host-derived seccomp profile that
  allows `sethostname` and `setdomainname`. Its startup step uses `CHOWN` for
  its own cgroup subtree and then runs as the mapped unprivileged user. The
  image declares `SETUID,SETGID,SYS_CHROOT,CHOWN` in its capability label.
  Guided setup prepares the engine image and seccomp profile.

#### Systemd containers and nested limits

An eligible engine needs a private cgroup v2 namespace with a writable
`nsdelegate` mount owned by namespace root. The reference verified nested
systemd on native Linux and in a Windows Podman machine. Register an init
image in the library, then run it inside the session. The example uses a
Rocky Linux init image registered as `localhost/library-rocky:9`.

```bash
podman run --detach --name target --systemd=always localhost/library-rocky:9
podman exec target timeout 120 sh -c 'until systemctl is-system-running | grep -qE "^(running|degraded)$"; do sleep 1; done'
podman exec target systemd-run --unit=probe --property=Type=oneshot /bin/true
podman rm --force target
```

Explicit nested limits such as `--memory` and `--pids-limit` require the
matching controller. The Windows Podman machine uses `cgroupfs` without
delegated controllers, so those limits are rejected and systemd
resource-control settings have no effect. An ineligible engine reports
the reason before launch. The reference's validation record lists the
hosts tested.

#### Migrating from host Podman delegation

An exact `ANTIGRAVITY_CONTAINER_PODMAN=1` stops launches and build-only
operations before engine access. An unconfigured restricted launch first
shows setup guidance. Remove the variable from launch scripts and rerun
`--container-setup` to migrate managed preferences and prepare the engine.
Register the images your tests use as toolchains. The former socket override
has no effect.

## Toolchains

Sessions can use file toolchains such as Java, Go or Python and registered
container images from the same operator-managed library. The operator keeps a
toolchain library on the host. Every session sees it read-only, with `nosuid`
and `nodev`, at `/toolchains`. The library is shared by the Claude, Codex,
OpenCode, Pi and Antigravity wrappers. A toolchain adds no network, IPC or
privilege capability: it runs under the same restrictions as the rest of the
session.

- **Location:** `${XDG_DATA_HOME:-~/.local/share}/sandbox-toolchains`, or
  `ANTIGRAVITY_CONTAINER_TOOLCHAINS_DIR`. The launcher creates it private
  (`0700`) when it is missing. It must stay outside the workspace (or the
  worktree parent), the Antigravity state directory and the installation. The
  state directory is the shared `~/.gemini` (or
  `ANTIGRAVITY_CONTAINER_CONFIG_DIR`) or the isolated
  `ANTIGRAVITY_CONTAINER_STATE_DIR`. A home directory exposed as the workspace with
  `ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` contains the default
  library, so that launch stops. Move the library with
  `ANTIGRAVITY_CONTAINER_TOOLCHAINS_DIR`, or omit it.
- **Disable:** `ANTIGRAVITY_CONTAINER_TOOLCHAINS=0` (or `false`, `no`) starts a session
  without the mount.
- **Live updates:** a toolchain added or removed on the host appears in
  running sessions without a restart.

### Managing the library

Run `--container-toolchain` as the first wrapper argument on the host.

```bash
agy --container-toolchain add java21        # install from the shipped catalog
agy --container-toolchain add ~/recipes/my-tool.json
agy --container-toolchain list              # installed toolchains and available catalog recipes
agy --container-toolchain remove java21
agy --container-toolchain verify [java21]   # rerun the checks on the current runtime image
```

- **Sources.** File toolchains can merge pinned OCI image paths, HTTPS
  archives and local archives. Archive sources require a SHA-256 checksum.
- **Recipe location.** Keep operator recipes outside workspace and state
  mounts. The saved worktree scope includes the workspace parent.
- **Fetching.** The host command fetches and verifies pinned sources before
  extraction. Archive downloads and redirects use HTTPS. They use the CA
  saved by setup when enabled. Fetches run outside session filtering.
- **Extraction:** it rejects absolute paths, `..`, device nodes and links
  that leave the toolchain, and clears setuid and setgid bits.
- **Atomic changes:** changes take a library lock and replace directories
  atomically.
- **Check:** before accepting a toolchain, `add` runs the recipe's `check`
  command in the Antigravity runtime image (`ANTIGRAVITY_CONTAINER_IMAGE`), without network and
  with the session's identity and hardening. A toolchain that needs a newer C
  library than the image's glibc fails here. The manifest records the base
  image from the installed `Containerfile`. If that base changes, the
  toolchain stays visible but loses its default environment until `verify`
  succeeds, and the launcher prints one warning naming it. All five wrappers
  build from the same base, so a toolchain verified by another wrapper keeps
  its default environment here.

### Recipes

A recipe is a JSON file that the operator keeps and reviews:

| Key | Meaning |
| --- | --- |
| `schema`, `name`, `version` | Schema `2`, a name matching `[a-z0-9][a-z0-9._-]*` and version text. Schema `1` recipes keep working. |
| `sources` | Ordered OCI image subpaths, HTTPS archives or local archives, each pinned by digest or checksum. |
| `images` | Container images for the session engine. See [Images](#images). |
| `path` | directories relative to the toolchain, added to `PATH` (default `["bin"]`) |
| `env` | variables: `{"toolchain": "<relative path>"}` or `{"value": "<literal>"}` |
| `requires` | other toolchains whose environment is loaded first |
| `notes` | short instructions shown to the agent in `toolchains.md` |
| `check` | command run in the runtime image before the toolchain is accepted |
| `default` | `true` adds the toolchain to new sessions' environment |

- **Protected variables:** recipes cannot set `PATH`, `HOME`, loader, proxy
  or CA variables, any `XDG_` variable or `DBUS_SESSION_BUS_ADDRESS` (no
  session has a bus, and `--unsetenv` cannot remove a value that `--env`
  sets). These rules are the same in every wrapper. Each wrapper also
  protects its own variables: its prefix, configuration, approval and
  credential variables, such as `ANTIGRAVITY_CONTAINER_*`, `ANTIGRAVITY_YOLO`
  and `GEMINI_API_KEY` here, and the agent's own variables that its profile
  lists in `native.protected_env`. For Antigravity these are every `AGY_`,
  `ANTIGRAVITY_` and `GEMINI_` variable and `GOOGLE_API_KEY`. `add` rejects
  them. If another wrapper installed a toolchain that sets one, this wrapper
  leaves that variable out of its sessions and prints a warning naming the
  toolchain; the rest of the toolchain stays available. The launcher also
  sets `AGY_CLI_DISABLE_AUTO_UPDATE=true` after the toolchain environment.
- **Default toolchains:** in new sessions, their `PATH` entries come **after**
  the image's. They never replace the runtime's own `node` or `python3`, which
  `agy` and the image tools use.
- **Conflicts:** two default toolchains cannot share a command or a variable.
  Install a second version with `"default": false` and use it through its
  `env.sh`.
- **Writable locations:** `/tmp` and the shared-state home are writable and
  executable, `/var/tmp` is writable but `noexec`, and all are discarded with
  the container; `/run` is not writable by the session user. An isolated home
  (`/antigravity-home`) persists; in shared-state mode only `.gemini` persists.
  Point caches to `/tmp` with literal values. Recipes shared with other
  wrappers keep notes such as `GOTMPDIR` under the workspace, because `/tmp` is
  `noexec` in the wrappers that do not declare executable temporary storage.
- **Dependency downloads** (Maven, npm, pip, Cargo, Go modules) need network
  access that provider and offline modes do not grant. Provide dependencies in
  the workspace, or use an unrestricted session.

The shipped catalog contains `java21`, `maven3.9`, `go`, `node24`,
`python3.13` and `rust`. Setup installs the catalog with the managed copy.

### Images

Use a digest-pinned registry reference in `images` or a local image object
with a full `sha256:` image ID and a `localhost/` name. For the example above:

```json
{
  "schema": 2,
  "name": "alpine",
  "version": "1",
  "images": [{"local": "sha256:<full image ID>", "name": "localhost/library-alpine:1"}],
  "check": ["podman", "run", "--rm", "--network=none", "localhost/library-alpine:1", "true"]
}
```

Get the full ID from `podman image inspect --format '{{.Id}}' <local-image>`.
Image-only toolchains omit path entries, environment and defaults. The host
command copies or fetches the image into the library store and runs the
check in the runtime image with a temporary offline engine. Running engines
mount the store read-only. Image removal waits until all session engines stop
and no remaining toolchain references the image.

### Telling the agent

The wrapper never edits `GEMINI.md`, `AGENTS.md` or other instruction files.
The library contains a generated `/toolchains/toolchains.md` with the usage
rules and every installed toolchain, plus a machine-readable
`/toolchains/index.json`. Add one line to the project's `GEMINI.md` or
`AGENTS.md`, or to `~/.gemini/GEMINI.md` (`/antigravity-home/.gemini/GEMINI.md`
in the session). The `agy` binary names both files; which ones it loads was
not verified without credentials.

```markdown
Read /toolchains/toolchains.md before using or looking for build tools.
```

The agent then runs a toolchain in one command with
`. /toolchains/<name>/env.sh && <command>`. This form also works for
toolchains added after the session started.

SELinux and AppArmor enforcement were not tested with the library mount. On
hosts that enforce them, profile the tools you add.

## Windows with Podman machine

On Windows, `antigravity-container.ps1` starts the sandbox from PowerShell on
the rootless engine of a Podman machine that Podman Desktop created with the
WSL provider. The session runs inside the machine's WSL distribution
(`podman-machine-default`, user `user`), in the PID and mount namespaces where
the machine runs systemd and its Podman service, as the machine's own login
shells do. The entry uses neither `podman.exe` nor the machine's SSH or
Windows API connection, so it works while other WSL distributions, such as
Ubuntu, are running.

Prerequisites:

- Windows PowerShell 5.1 or PowerShell 7, with a policy that allows local
  scripts, for example `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`;
- a rootless Podman machine with the WSL provider, created with Podman
  Desktop, and started by Podman (Podman Desktop or `podman machine start`)
  before setup and sessions;
- `sudo` without a password for the machine's user, which Podman machines
  provide: sessions and setup enter the machine's systemd namespaces with
  `sudo nsenter`, as its login shells do (`/usr/local/bin/enterns`);
- a checkout of this repository in a folder on a Windows drive, with LF line
  endings. The repository's `.gitattributes` keeps them LF even with
  `core.autocrlf=true`; [docs/setup.md](docs/setup.md) explains how to fix an
  older CRLF checkout.

Run setup once from the checkout, in an interactive PowerShell window:

```powershell
cd C:\Work\antigravity-container
.\antigravity-container.ps1 --container-setup
```

Setup runs the guided setup inside the machine distribution. The release,
preferences and images are installed there, in
`~/.local/lib/antigravity-container`. Its output leaves out the Linux shell
guidance; the entry prints how to start sessions. Setup finds the machine's
own Podman service, so it offers provider networking, the default, with the
`account` or `gemini` method, and offline and unrestricted networking, as on
Linux.

With the `account` method, sign-in happens inside an interactive `agy`
session, because `agy` has no login command. Setup offers to start one in the
machine: choose Google sign-in there, open the printed URL in a Windows
browser, sign in, enter the code shown in the PowerShell window, then exit
`agy`. The tokens stay in the machine user's Antigravity state (`~/.gemini` in
shared state mode), separate from Antigravity or Gemini CLI on Windows. When
you postpone the sign-in, setup names the next step: start
`antigravity-container.ps1` from a project folder and sign in inside the
session. With the `gemini` method, set `$env:GEMINI_API_KEY = '...'` in
PowerShell before `antigravity-container.ps1`. The entry forwards the key by
name, and setup stores none. The key alone does not select the provider:
merge `"modelProvider": "gemini"` into the settings file in the machine, which
`antigravity-container.ps1 --container-shell` shows at
`/antigravity-home/.gemini/antigravity-cli/settings.json`, or pass
`--settings '{"modelProvider":"gemini"}'` for one session (see
[Authentication](#authentication)). Rerun setup after updating the checkout,
and after the machine is recreated. To run the sandbox as a command without
keeping the checkout, install it instead
([Install as a command](#install-as-a-command)).

Start sessions from a project directory on a Windows drive:

```powershell
cd C:\Work\my-project
C:\Work\antigravity-container\antigravity-container.ps1
C:\Work\antigravity-container\antigravity-container.ps1 --container-shell -c 'git status'
C:\Work\antigravity-container\antigravity-container.ps1 --container-help
```

The project is mounted at its drive path, for example `/mnt/c/Work/my-project`.
A launch is refused before any engine query in these cases:

- the machine is stopped: the entry does not start its distribution, because
  `wsl.exe` would start it without the user's runtime directory
  `/run/user/<uid>`, where no `podman` command works. Start the machine with
  Podman Desktop or `podman machine start`;
- the distribution runs without that directory, because `wsl.exe` alone
  started it. Run `wsl --terminate podman-machine-default`, then start the
  machine with Podman. Setup refuses both states too;
- `sudo` asks the machine's user for a password, so the entry cannot enter the
  machine's systemd namespaces. Setup refuses it too;
- the location is a network share, a path inside a WSL distribution, a drive
  the distribution does not mount, or not a file system path;
- the project or the worktree parent contains the checkout, or lies inside it;
- the project is a Windows system or profile folder (see
  [Session hardening, budgets and lifetime](#session-hardening-budgets-and-lifetime)).

The exit status, the terminal and Ctrl+C work as on Linux. Closing the window
also ends the session and removes its container. The machine's engine uses
the `cgroupfs` manager: the memory and CPU budgets are not enforced, and the
process budget uses the process rlimit, as the launch notices state (see
[Session hardening, budgets and lifetime](#session-hardening-budgets-and-lifetime)).
`agy`'s internal terminal sandbox was not measured in the machine. Omit
`--sandbox` there as on Linux
([Known internal sandbox incompatibility](#known-internal-sandbox-incompatibility));
in `offline` and `provider` the guard stops it anyway.

| Variable | Meaning |
| --- | --- |
| `ANTIGRAVITY_CONTAINER_NETWORK` | `provider`, `offline` or `unrestricted` for one launch (default: the mode setup saved); a restricted mode needs a setup that prepared it |
| `ANTIGRAVITY_CONTAINER_WSL_DISTRO` | WSL distribution (default `podman-machine-default`) |
| `ANTIGRAVITY_CONTAINER_WSL_USER` | user in the distribution (default `user`) |
| `ANTIGRAVITY_CONTAINER_WSL_INSTALLATION` | absolute installation path in the distribution, when setup used another one |

Set them with `$env:NAME = 'value'`. The entry forwards to the launcher in the
distribution, by name, the other `ANTIGRAVITY_CONTAINER_*` variables whose
names use only letters, digits and `_`, `ANTIGRAVITY_YOLO`, `GEMINI_API_KEY`,
and the names listed in `ANTIGRAVITY_CONTAINER_ENV_VARS`.
`ANTIGRAVITY_CONTAINER_CONFIG_DIR` is forwarded only when it holds a
distribution path (starting with `/`): a Windows path is skipped with a
notice, and the directory saved by setup applies. `$env:GEMINI_API_KEY = '...'`
before the entry supplies the key as an exported variable does on Linux; the
help lists it. It forwards no other Windows variable. Path values, such as
`ANTIGRAVITY_CONTAINER_STATE_DIR`, are distribution paths, such as
`/home/user/...`.

Limits on Windows:

- An exact `ANTIGRAVITY_CONTAINER_PODMAN=1` stops before WSL runs. A managed
  release with saved delegation asks to rerun setup from Windows.
- PowerShell pipeline input, such as
  `'x' | .\antigravity-container.ps1 --container-shell -c cat`, is refused,
  because PowerShell alters it. Redirect a file from `cmd.exe` instead:
  `cmd /c "powershell -File C:\Work\antigravity-container\antigravity-container.ps1 --container-shell -c cat < input.txt"`.
- PowerShell parses the arguments first. Quote a `--` meant for `agy` or Bash
  (`'--'`), values with commas (`'a,b'`), numbers whose spelling matters
  (`'007'`) and arguments of the form `-x:y`. The encoded arguments are
  limited to 32766 characters.
- A variable with an empty value counts as unset.
- `podman machine stop` (`wsl --terminate`) ends running sessions.
- After the machine starts, the folder of its first session may stay in use
  by a WSL process until `wsl --shutdown`, so Windows cannot delete that
  folder meanwhile.
- Projects on a Windows drive go through drvfs, which is slow on large trees.
  Git for Windows clones with `core.autocrlf=true` look modified to Git in the
  session: set `core.autocrlf=false` for the project, or give it a
  `.gitattributes`.
- Bitdefender's Advanced Threat Control (`Atc4.Detection`) has blocked the
  operator validation script `tools/windows-validate.ps1` of
  `sandbox-container`, and quarantined files while validation bundles were
  extracted with `tar`, for example `tests/fixtures/shell-agent/launcher.sh`,
  which only the Linux tests use. Setup, the installer and sessions ran with it
  active, and another Windows system with other antivirus products ran the
  validation without problems. Run the validation script with the checkout
  folder excluded, or with the protection paused for the run, as your
  administrator allows. Setup and the entry fail when a file they need is
  missing: restore it from the quarantine, and report the false positive to
  the vendor.

### Trusting a host CA on Windows

Setup and sessions run in the machine, so host CA trust uses a bundle of the
machine, not the Windows certificate store. On a network that intercepts TLS
(a corporate proxy that re-signs certificates), the machine trusts the
interception CA only when Podman imports the Windows store into it. Without
it, image pulls and builds in the machine and HTTPS requests in sessions fail
with a certificate verification error. With Podman 6.0 or later, enable the
import once. `podman machine set` fails while the machine runs, so stop it
first:

```powershell
podman machine stop
podman machine set --import-native-ca
podman machine start
```

The import happens at every machine start: Podman copies the CAs that Windows
trusts into the machine and runs `update-ca-trust`, so the machine's system
bundle contains them. Restart the machine after Windows gains a new CA.

Then run setup and answer yes to "Trust a host CA bundle?". Keep the bundle
setup proposes, the machine's system bundle (see
`ANTIGRAVITY_CONTAINER_TRUST_HOST_CA` in [Environment](#environment)): setup
passes it to the image builds, including the `agy` download, and saves it for
sessions. Rerun setup after the machine is recreated, and enable the
import again on the new machine.

### Toolchains on Windows

The library lives inside the Podman machine. The wrappers running in that
machine share it. Recreating the machine removes the library.

```powershell
.\antigravity-container.ps1 --container-toolchain add java21
.\antigravity-container.ps1 --container-toolchain add C:\Work\recipes\my-tool.json
```

Drive-letter recipe paths and local archive paths in recipes translate to the
corresponding machine mount, such as `/mnt/c/Work/recipes`. The command refuses
UNC paths and drives the distribution cannot mount.

### Install as a command

Instead of setup from the checkout, you can install the entry for your
Windows account:

```powershell
cd C:\Work\antigravity-container
.\antigravity-container.ps1 --container-install
```

The install copies the entry, the Windows scripts and every file that setup
needs into `%LOCALAPPDATA%\Programs\antigravity-container`. It then adds that
folder to your user `PATH` (`HKCU\Environment`, no administrator rights; the
other entries and their `%VAR%` references stay as they are) and runs setup
from the copy. The installer announces the `PATH` change before making it;
nothing is written to the PowerShell profile or system-wide. Afterwards the
checkout can be deleted, and a new PowerShell window runs the command from any
project directory:

```powershell
cd C:\Work\my-project
antigravity-container
antigravity-container --container-shell -c 'git status'
antigravity-container --container-setup
```

New PowerShell windows and new Windows Terminal tabs find the command; the
window or tab that ran the install may not. When setup fails after the copy,
the copy and the `PATH` entry stay; finish with
`antigravity-container --container-setup`.

To update, run `--container-install` again from a newer checkout or download.
It replaces the installed files, removes the ones the new version no longer
has, and runs setup. Do not update while a setup runs from the installed
copy. The installed command refuses to install itself. An
interrupted install leaves the copy marked incomplete: the command then
refuses to start sessions until the next install completes. Two installs never
run at once.

`antigravity-container --container-uninstall` (also from a checkout) removes the
`PATH` entry and the installed copy. The installation inside the Podman machine
stays until the machine is reset. A folder still used by a WSL process is
reported; `wsl --shutdown` releases it.

The scripts are not signed. The installer writes new local files, so the
installed command runs under the default `RemoteSigned` policy. A downloaded
zip keeps the Mark of the Web on its files: run its first install as
`powershell -ExecutionPolicy Bypass -File .\antigravity-container.ps1 --container-install`,
or `Unblock-File` its files first. Running the installer is your decision to
trust that source. Policies stricter than `RemoteSigned`, such as `AllSigned`,
are unsupported.

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

Absolute paths are preserved for workspace binds, including binds requested
by nested containers through the private session engine. The process uses `--userns=keep-id` and the caller's
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
example RHEL subscription certificates from `mounts.conf`). `/tmp` and the
shared-state home allow execution for native runtime components (the profile
declares executable temporary storage) and have 512 MiB limits; `/var/tmp`
uses `noexec` with a separate 512 MiB limit; `/run` uses `noexec` with a 32 MiB
limit and is not writable by the session user. All use `nosuid,nodev`; `/tmp`,
`/var/tmp` and the home have mode `1777`; all disappear with the container. Restricted sessions also mount the
guard and its session inputs read-only. No full host home, host OpenSpec
settings, host certificates, or SSH configuration is mounted automatically.

Each session reserves a name from the physical current directory and the next
numeric index among all existing instances. Concurrent name collisions are
retried up to 20 times; existing sessions are never deleted to free a name.
Private per-attempt CID files and a unique session label support recovery when
creation is interrupted before its client returns an ID. A workspace name alone
never authorizes removal, and interrupted creation never starts the application.

A signal starts shutdown at once, also while the container is being created.
INT, TERM and HUP are forwarded to the owned container. Shutdown has one
20-second budget: after forwarding a signal, the wrapper allows at most 5
seconds for graceful exit, then attempts forced removal with Podman's stop wait
set to zero. Shutdown engine calls have a 2-second soft timeout and at most 1
further second before forced client termination, capped by the remaining
overall budget. Local create/attach clients are also terminated and reaped
within that budget. Normal application and build durations are unrestricted.
The first terminal signal selects status 143 (TERM), 130 (INT), or 129 (HUP);
later signals do not restart shutdown. Otherwise the application's exit status
is retained, including zero and 125.

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
exist on that host at exactly the same absolute paths. The wrapper uses the
explicit same-host service for host-side operations.

TCP/SSH transports, named remote connections, the Podman machine connection
that `podman.exe` uses, and rootful engines are rejected. On Windows, the
PowerShell entry runs the sandbox inside the Podman machine instead; see
[Windows with Podman machine](#windows-with-podman-machine).

### Session hardening, budgets and lifetime

Every agy and shell session runs with `--cap-drop=all` and
`--security-opt=no-new-privileges`, including sessions with a private engine.
The session's privilege boundary is independent of the approval setting.

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
After creating the container, the wrapper checks that every enforced budget was
applied and that no unenforced one is present, and stops before agy starts
otherwise. Restricted qualification records the enforced set, so a change in
delegation requires requalification. Budgets and tmpfs sizes do not limit
workspace or state storage growth.

A rootless engine applies cgroup limits only through the `systemd` cgroup
manager (`podman info --format '{{.Host.CgroupManager}}'`). With `cgroupfs`,
for example on a Podman machine on WSL, the engine reports every controller but
ignores the limits. The sandbox therefore treats no controller as delegated: it
prints `agent memory budget not enforced: the rootless engine uses the cgroupfs
cgroup manager, which applies no cgroup limits` and the matching CPU line, and
the process budget uses the fallback below.

The process budget has a fallback. Without the `pids` controller, the agent
container's first process sets its soft and hard process rlimit at the
selected budget before the application starts. The notice reads `agent process budget enforced through the
process rlimit (512 tasks of the session user, threads included)`. The limit is
per session: Linux 5.14 and later count it per user namespace, and every
container has its own. The session cannot raise it, because it has no
capabilities. Container startup uses a few of these tasks, so slightly fewer
than `N` processes are available. The fallback applies only when the engine
reports kernel 5.14 or later (`podman info --format '{{.Host.Kernel}}'`). Older
or unrecognized kernels may count every process of your user, so the process
budget then stays unenforced, and the notice names the reason. The memory and
CPU budgets have no fallback. The provider proxy's process budget uses the same
fallback. Which mechanism enforces each process budget is part of the restricted
qualification identity. The launch verifies the limit setup, and smoke and
qualification check the effective value.

Risk: without the memory or process budget, a session can exhaust host memory
or processes for your user; without a CPU budget it can saturate every CPU.
Delegating the controllers (for example a systemd
`Delegate=cpu cpuset io memory pids` drop-in for `user@.service`) restores full
enforcement, but the sandbox never requires it.

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
allowed.

On a WSL drive mount, it also must not be one of these Windows folders, in any
letter case, because drvfs ignores case:

- `/mnt/<drive>/Users`;
- a profile, `/mnt/<drive>/Users/<name>`, its `Documents`, its `OneDrive`
  (also `OneDrive - <organization>`) or `OneDrive/Documents`, which hold the
  PowerShell profile and modules;
- anything inside the profile's `AppData`, which holds the startup folder;
- `/mnt/<drive>/Windows`;
- `/mnt/<drive>/Program Files` or `/mnt/<drive>/Program Files (x86)`;
- `/mnt/<drive>/ProgramData`.

Apart from `AppData`, only these exact folders are refused. A project below
them, such as `/mnt/c/Users/me/projects/app` or
`/mnt/c/Users/me/Documents/GitHub/app`, is accepted. In worktree mode, however, a
project placed directly in a profile is refused, because its parent is the
profile.

Launch from a project directory, or set exactly
`ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` to expose a refused directory
deliberately; the wrapper then prints a warning.

## Environment

| Variable | Default |
| --- | --- |
| `ANTIGRAVITY_CONTAINER_NETWORK` | `provider` when unset or empty; `offline`, `provider` or `unrestricted` |
| `ANTIGRAVITY_CONTAINER_NETWORK_PROFILE` | provider only: `google-account` or `gemini-api` |
| `ANTIGRAVITY_CONTAINER_NETWORK_POLICY` | provider only: absolute policy path |
| `ANTIGRAVITY_CONTAINER_NETWORK_RUNTIME_DIR` | provider only: private native directory |
| `ANTIGRAVITY_CONTAINER_EGRESS_IMAGE` | provider only: immutable proxy image ID or digest |
| `ANTIGRAVITY_CONTAINER_MAINTENANCE` | disabled; exact `1` authorizes builds and proxy pulls |
| `ANTIGRAVITY_CONTAINER_IMAGE` | `localhost/antigravity-cli:latest` |
| `ANTIGRAVITY_CONTAINER_STATE_DIR` | unset or empty: shared `~/.gemini`; a path: isolated home |
| `ANTIGRAVITY_CONTAINER_CONFIG_DIR` | `~/.gemini` with shared state; the session always sees `/antigravity-home/.gemini` |
| `ANTIGRAVITY_CONTAINER_READONLY_STATE` | disabled; `1`, `true` or `yes` mounts the existing configuration read-only |
| `ANTIGRAVITY_CONTAINER_ENV_VARS` | empty; host variable names forwarded by name |
| `ANTIGRAVITY_CONTAINER_TRUST_HOST_CA` | disabled; `1`, `true` or `yes` mounts one host CA bundle read-only |
| `ANTIGRAVITY_CONTAINER_CA_BUNDLE` | first of `/etc/ssl/certs/ca-certificates.crt`, `/etc/pki/tls/certs/ca-bundle.crt` |
| `ANTIGRAVITY_YOLO` | disabled |
| `ANTIGRAVITY_CONTAINER_ENGINE_IMAGE` | prepared engine image or `localhost/antigravity-cli-engine:latest` |
| `ANTIGRAVITY_CONTAINER_MEMORY_LIMIT` | `4g` (positive integer with unit `k`, `m` or `g`) |
| `ANTIGRAVITY_CONTAINER_CPU_LIMIT` | `2` (positive number of CPUs, at most 3 decimals, up to 1024) |
| `ANTIGRAVITY_CONTAINER_PIDS_LIMIT` | `512` (integer from 1 to 4194304) |
| `ANTIGRAVITY_CONTAINER_RUN_TIMEOUT` | `0`, disabled (whole seconds) |
| `ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE` | disabled; only exact `1` enables it |
| `ANTIGRAVITY_CONTAINER_TOOLCHAINS` | enabled (also when empty); `0`, `false` or `no` omits the read-only `/toolchains` mount |
| `ANTIGRAVITY_CONTAINER_TOOLCHAINS_DIR` | `${XDG_DATA_HOME:-~/.local/share}/sandbox-toolchains`, shared by the wrappers |

An explicit same-host Unix `CONTAINER_HOST` selects the launch service.
Caller variables are forwarded only by name, as described in
[First run](#direct-operator-launches) and [Network modes](#network-modes).
`EDITOR` and `VISUAL` use the included nano editor.

With host CA trust on a Podman machine on Windows, the host is the machine: it
must first import the CAs that Windows trusts
([Trusting a host CA on Windows](#trusting-a-host-ca-on-windows)).

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
ANTIGRAVITY_CONTAINER_MAINTENANCE=1 agy --container-build
# Roll back the executable and toolchain:
ANTIGRAVITY_CONTAINER_IMAGE=localhost/antigravity-cli:previous agy --version
```

An absent image is built only with `ANTIGRAVITY_CONTAINER_MAINTENANCE=1`.
Explicit builds keep the layer cache; a changed recorded version or checksum in
`Containerfile` invalidates the download layers, so the build downloads the
recorded artifacts again and verifies their checksums. The build prints CLI and OpenSpec versions and binary architecture. It installs the
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

## Shared sandbox components and the agent profile

`network/`, `setup/`, `launcher/` and the shared tests come unchanged from the
reference repository `sandbox-container` and are shared with the Claude, Codex,
OpenCode and Pi wrappers. They contain no Antigravity-specific names.
`launcher/core.sh` is the whole launcher: `antigravity-container.sh` is the thin
entry script every wrapper shares, and `agent/launcher.sh` holds the profile
values the core needs plus Antigravity's two hooks, which document
`ANTIGRAVITY_YOLO` and `GEMINI_API_KEY` and turn `ANTIGRAVITY_YOLO` into
`--dangerously-skip-permissions` (`docs/launcher-contract.md` in
`sandbox-container`). Restricted sessions run the image's entrypoint script
`/usr/local/bin/antigravity-entrypoint` through the guard. The shared launcher
tests (`tests/test_launcher.py`, with the fake engine `tests/fake_podman.py`)
run the core against fixture agent parts; `tests/test_wrapper.py` covers only
Antigravity's part. Every other agent-specific value is declared in
`agent/profile.json`.

## Verification

Run the checks in the runner, which uses the `agy` image and native volume
storage (a noexec `/tmp` or a Windows drive cannot hold the test fixtures).
Prepare the runtime and guard-toolchain images, the adopted session engine
image, and the pinned Alpine sample named in `tests/test_runtime.py` before
running their required modes:

```bash
bash tests/run-runtime.sh --wrapper        # shared launcher and wrapper tests with a fake engine
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
