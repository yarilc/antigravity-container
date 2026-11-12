#!/usr/bin/env bash
set -Eeuo pipefail

die() { printf 'antigravity-container: %s\n' "$*" >&2; exit 1; }

usage() {
    cat <<'EOF'
Usage: antigravity-container.sh [container options] [agy arguments...]

Run Google Antigravity CLI in a rootless Podman container.

Container options:
  --container-setup         interactively prepare a complete user installation
                           and its managed launcher; must be used alone
  --container-qualify       verify a prepared restricted installation with
                           fixed local controls; must be used alone
  --container-build         rebuild the image without cached downloads
                           (requires ANTIGRAVITY_CONTAINER_MAINTENANCE=1)
  --container-shell         open Bash instead of agy
  --container-git-worktree  mount the physical current directory's immediate
                           parent read/write; keep the original working directory
  --container-help          show this help without requiring Podman

All other arguments are forwarded unchanged to agy.
TERM/INT/HUP are forwarded once; interruption exits are 143/130/129.
Shutdown allows five seconds of application grace, then forces owned cleanup.
Control calls and client termination have separate finite deadlines.
Only this invocation's verified container is removed. Engine loss or SIGKILL
can leave residual resources requiring manual inspection. Host coreutils
provides the required timeout command.

Environment:
  ANTIGRAVITY_CONTAINER_NETWORK     offline, provider, or unrestricted; required
                                    for every launch (unrestricted is the
                                    previous behavior)
  ANTIGRAVITY_CONTAINER_NETWORK_PROFILE  provider profile: google-account or
                                    gemini-api
  ANTIGRAVITY_CONTAINER_NETWORK_POLICY   absolute operator policy JSON path
  ANTIGRAVITY_CONTAINER_NETWORK_RUNTIME_DIR  private native directory at its
                                    host path
  ANTIGRAVITY_CONTAINER_EGRESS_IMAGE  immutable proxy image ID or registry digest
  ANTIGRAVITY_CONTAINER_MAINTENANCE  authorize image builds and proxy pulls only
                                    with exact value 1, including the build of a
                                    missing image
  ANTIGRAVITY_CONTAINER_IMAGE       default: localhost/antigravity-cli:latest
  ANTIGRAVITY_CONTAINER_STATE_DIR   unset: dedicated home
                                    ~/.local/share/antigravity-container/home;
                                    a path: that private isolated home; empty:
                                    shared host ~/.gemini below an ephemeral home
  ANTIGRAVITY_CONTAINER_CONFIG_DIR  private directory replacing ~/.gemini with
                                    shared state; inside the session it is
                                    always /antigravity-home/.gemini; requires
                                    an empty ANTIGRAVITY_CONTAINER_STATE_DIR
  ANTIGRAVITY_CONTAINER_TRUST_HOST_CA  trust a host CA bundle: 1, true, or yes
                                    (default: disabled)
  ANTIGRAVITY_CONTAINER_CA_BUNDLE   CA bundle file to trust (default: first of
                                    /etc/ssl/certs/ca-certificates.crt and
                                    /etc/pki/tls/certs/ca-bundle.crt)
  ANTIGRAVITY_YOLO                  bypass agy approvals (default: disabled)
  ANTIGRAVITY_CONTAINER_PODMAN      expose the host Podman service (default:
                                    disabled); rejected in offline and provider
  ANTIGRAVITY_CONTAINER_PODMAN_SOCKET
    default: ${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock
  GEMINI_API_KEY                    forwarded if set in unrestricted mode and
                                    with the gemini-api profile; requires
                                    modelProvider: gemini
  ANTIGRAVITY_CONTAINER_MEMORY_LIMIT  session memory, integer with k/m/g unit (default: 4g)
  ANTIGRAVITY_CONTAINER_CPU_LIMIT     session CPUs, up to 3 decimals (default: 2)
  ANTIGRAVITY_CONTAINER_PIDS_LIMIT    session process limit (default: 512)
    Budgets cannot be disabled; each is enforced only when the rootless engine
    delegates its cgroup v2 controller (memory, cpu, pids). A missing controller
    leaves that budget unenforced with a notice; without memory or process
    budgets a session can exhaust host resources
  ANTIGRAVITY_CONTAINER_RUN_TIMEOUT   session container lifetime in whole seconds
    (default: 0, disabled by default)
  ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE  exact 1 permits a refused
    sensitive workspace with a warning (default: disabled)

YOLO accepts 1/true/yes or 0/false/no, case-insensitively; empty is disabled.
Podman delegation is enabled only with exact ANTIGRAVITY_CONTAINER_PODMAN=1.
Every other value disables it without error; migrate true/yes to 1.
YOLO adds --dangerously-skip-permissions without changing mounts or settings.
Native CLI flags and existing permissions still apply when YOLO is disabled.

The Podman socket grants control over the host user's containers and permits
host mounts beyond the workspace. It removes the project-only access boundary.
Worktree mode exposes the entire parent, including siblings, read/write.

Every session drops all capabilities and sets no-new-privileges; no
security-policy overrides are added. Budgets and tmpfs sizes do not limit
workspace or state storage growth. The writable workspace (or worktree parent)
must not physically be /, /home, /root, /etc, /usr, /var, /bin, /sbin, /lib,
/lib64, /boot, /opt, /srv, /mnt, /media, /proc, /sys, /dev, /run, /tmp, the
caller's home or a /mnt/<letter> drive root; descendants such as
/mnt/d/project are allowed. When the lifetime limit stops a session, a notice
is printed and the engine client's exit status is returned.

New users must first run: bash ./antigravity-container.sh --container-setup
Then use the managed launch command printed by setup (by default
~/.local/bin/antigravity-container) from your workspace. An ordinary launch
with an unset or empty ANTIGRAVITY_CONTAINER_NETWORK stops with setup guidance
before runtime checks or state creation. Direct operator launches remain
available with an explicit mode.

There is no D-Bus session or keyring in the container: agy keeps account
tokens in files in the private state home, protected by Unix permissions only.
Sign-in uses the remote URL and code flow with a host browser.

Migration: every direct launch now needs an explicit ANTIGRAVITY_CONTAINER_NETWORK
(the managed launcher supplies it). Set ANTIGRAVITY_CONTAINER_NETWORK=unrestricted
to keep the previous networking,
and add ANTIGRAVITY_CONTAINER_MAINTENANCE=1 to commands that build the image:
  ANTIGRAVITY_CONTAINER_NETWORK=unrestricted ANTIGRAVITY_CONTAINER_MAINTENANCE=1 bash ./antigravity-container.sh --container-build --version
Accounts signed in through the removed keyring must sign in again once.
Offline sessions cannot reach any model service. Restricted failures never
retry unrestricted networking.

Restricted modes (offline, provider) require host Python 3, a same-host Unix
rootless Netavark service with Podman >= 4.9, standard OCI seccomp, usable
Landlock ABI >= 3, a protected installation outside writable workspace/state
trees, a static guard and SHA-256 manifest in network/bin, and a current local
qualification report (run --container-qualify alone after preparation or
relevant updates). Changed boot, engine/backend/security, code/images,
policy/profile, CA trust or hardening invalidates the report; an unidentifiable
active LSM policy requires the gate on each launch. Locally-qualified
installations are distinguished from release-measured acceptance records.
Restricted sessions receive no host proxy or CA variables; provider mode
forwards GEMINI_API_KEY only with gemini-api, and offline forwards none.
AGY_CLI_DISABLE_AUTO_UPDATE=true is set after forwarding; agy telemetry
(play.googleapis.com) is allowed only with google-account, where the account
session uses it, and denied with gemini-api. Named Unix sockets and the Bubblewrap terminal sandbox
are unavailable under the guard; the container is the boundary.
Provider mode uses an external CONNECT proxy that binds the TLS server name
(initial and retried ClientHello) to the CONNECT host before forwarding; it
does not prove exclusive communication with your Google account or project.
Allowed services can receive data: an injected agent can send workspace data
to an allowed host (google-account: oauth2.googleapis.com,
cloudcode-pa.googleapis.com, daily-cloudcode-pa.googleapis.com,
www.googleapis.com, aicode.googleapis.com, www.gstatic.com and
play.googleapis.com; gemini-api: generativelanguage.googleapis.com) with an
attacker's key or account. Only offline removes this. Provider-hosted
tools such as web search run at the provider, outside this boundary.
See network/README.md and docs/network-contract.md.
EOF
}

# Help takes precedence regardless of option order and never needs Podman.
for arg in "$@"; do
    case "$arg" in --container-help) usage; exit 0 ;; esac
done
readonly DEDICATED_HOME_SUFFIX=.local/share/antigravity-container/home
for arg in "$@"; do
    if [[ "$arg" == --container-qualify ]]; then
        [[ $# == 1 ]] || die '--container-qualify must be used alone'
        command -v python3 >/dev/null || die 'host Python 3 is required for qualification'
        qualify_dir=$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")
        # An unset state directory selects the dedicated home; qualification
        # binds the same writable paths as the launches it qualifies.
        if [[ -z "${ANTIGRAVITY_CONTAINER_STATE_DIR+x}" && "${HOME:-}" == /* ]]; then
            export ANTIGRAVITY_CONTAINER_STATE_DIR="$HOME/$DEDICATED_HOME_SUFFIX"
        fi
        exec python3 -I "$qualify_dir/network/qualify.py" qualify
    fi
done

for arg in "$@"; do
    if [[ "$arg" == --container-setup ]]; then
        [[ $# == 1 ]] || die '--container-setup must be used alone'
        [[ -t 0 && -t 1 ]] || die '--container-setup requires an interactive terminal'
        command -v python3 >/dev/null || die 'host Python 3 is required for interactive setup'
        setup_script=$(readlink -f -- "${BASH_SOURCE[0]}")
        exec python3 -I "$(dirname -- "$setup_script")/setup/setup.py"
    fi
done

build_image=0
qualification_probe=0
shell_mode=0
git_worktree=0
args=()
for arg in "$@"; do
    case "$arg" in
        --container-qualify-probe)
            [[ $# == 1 ]] || die 'the fixed qualification probe must be used alone'
            qualification_probe=1 ;;
        --container-build) build_image=1 ;;
        --container-shell) shell_mode=1 ;;
        --container-git-worktree) git_worktree=1 ;;
        *) args+=("$arg") ;;
    esac
done

# An explicit mode precedes every other check, engine query and state operation.
if [[ -z "${ANTIGRAVITY_CONTAINER_NETWORK:-}" ]]; then
    setup_wrapper=${BASH_SOURCE[0]}
    [[ "$setup_wrapper" == /* ]] || setup_wrapper="$PWD/$setup_wrapper"
    printf -v setup_command 'bash %q --container-setup' "$setup_wrapper"
    die "setup required: run $setup_command; use the managed launcher afterward or explicitly set ANTIGRAVITY_CONTAINER_NETWORK for an operator workflow (offline, provider, or unrestricted; unrestricted keeps the previous networking behavior)"
fi
network_mode=$ANTIGRAVITY_CONTAINER_NETWORK
case "$network_mode" in
    offline|provider|unrestricted) ;;
    *) die 'ANTIGRAVITY_CONTAINER_NETWORK must be offline, provider, or unrestricted' ;;
esac
restricted=0
[[ "$network_mode" == unrestricted ]] || restricted=1

boolean() {
    case "${2,,}" in
        1|true|yes) printf 1 ;;
        ''|0|false|no) printf 0 ;;
        *) die "$1 must be 0, 1, true, false, yes, or no" ;;
    esac
}
yolo=$(boolean ANTIGRAVITY_YOLO "${ANTIGRAVITY_YOLO:-}")
trust_host_ca=$(boolean ANTIGRAVITY_CONTAINER_TRUST_HOST_CA "${ANTIGRAVITY_CONTAINER_TRUST_HOST_CA:-}")
podman_access=0
[[ "${ANTIGRAVITY_CONTAINER_PODMAN:-}" != 1 ]] || podman_access=1
if ((restricted && podman_access)); then
    die 'restricted networking rejects ANTIGRAVITY_CONTAINER_PODMAN=1: the host API bypasses egress enforcement; select explicit unrestricted mode for delegation'
fi
# The provider credential follows the selected profile (agent/profile.json).
profile_credential=''
if [[ "$network_mode" == provider ]]; then
    [[ -n "${ANTIGRAVITY_CONTAINER_NETWORK_PROFILE:-}" && -n "${ANTIGRAVITY_CONTAINER_NETWORK_POLICY:-}" ]] \
        || die 'provider mode requires ANTIGRAVITY_CONTAINER_NETWORK_PROFILE and ANTIGRAVITY_CONTAINER_NETWORK_POLICY'
    [[ -n "${ANTIGRAVITY_CONTAINER_NETWORK_RUNTIME_DIR:-}" && -n "${ANTIGRAVITY_CONTAINER_EGRESS_IMAGE:-}" ]] \
        || die 'provider mode requires a private host-path ANTIGRAVITY_CONTAINER_NETWORK_RUNTIME_DIR and immutable ANTIGRAVITY_CONTAINER_EGRESS_IMAGE'
    [[ "$ANTIGRAVITY_CONTAINER_NETWORK_PROFILE" != gemini-api ]] || profile_credential=GEMINI_API_KEY
fi

# Session budgets and lifetime, validated before any engine or state operation.
# Same rules and messages as the claude-container reference (sandbox-ref-2).
# Only an unset budget selects its default; no value disables a budget.
memory_text=${ANTIGRAVITY_CONTAINER_MEMORY_LIMIT-4g}
cpu_text=${ANTIGRAVITY_CONTAINER_CPU_LIMIT-2}
pids_text=${ANTIGRAVITY_CONTAINER_PIDS_LIMIT-512}
timeout_text=${ANTIGRAVITY_CONTAINER_RUN_TIMEOUT:-0}
memory_bytes=0
if [[ "$memory_text" =~ ^([1-9][0-9]{0,15})([kmgKMG])$ ]]; then
    case "${BASH_REMATCH[2],,}" in
        k) unit=1024 ;;
        m) unit=1048576 ;;
        *) unit=1073741824 ;;
    esac
    ((10#${BASH_REMATCH[1]} > (1 << 50) / unit)) || memory_bytes=$((10#${BASH_REMATCH[1]} * unit))
fi
((memory_bytes > 0)) || die 'ANTIGRAVITY_CONTAINER_MEMORY_LIMIT must be a positive integer with unit k, m or g, for example 4g'
cpu_nano=0
if [[ "$cpu_text" =~ ^([0-9]{1,4})(\.([0-9]{1,3}))?$ ]]; then
    fraction=${BASH_REMATCH[3]}000
    cpu_nano=$((10#${BASH_REMATCH[1]} * 1000000000 + 10#${fraction:0:3} * 1000000))
    ((cpu_nano <= 1024000000000)) || cpu_nano=0
fi
((cpu_nano > 0)) || die 'ANTIGRAVITY_CONTAINER_CPU_LIMIT must be a positive number of CPUs with at most 3 decimals, for example 2 or 1.5'
# shellcheck disable=SC2015 # die must run when either test fails.
[[ "$pids_text" =~ ^(0|[1-9][0-9]{0,9})$ ]] && ((pids_text > 0 && pids_text <= 4194304)) \
    || die 'ANTIGRAVITY_CONTAINER_PIDS_LIMIT must be a positive integer process count up to 4194304'
# shellcheck disable=SC2015 # die must run when either test fails.
[[ "$timeout_text" =~ ^(0|[1-9][0-9]{0,9})$ ]] && ((timeout_text <= 2147483647)) \
    || die 'ANTIGRAVITY_CONTAINER_RUN_TIMEOUT must be whole seconds; 0 disables the lifetime limit'
pids_limit=$((10#$pids_text))
run_timeout=$((10#$timeout_text))

# Refuse sensitive writable workspaces before any engine or state operation.
workspace=$(pwd -P)
workspace_mount=$workspace
((git_worktree == 0)) || workspace_mount=$(dirname -- "$workspace")
[[ "${HOME:-}" == /* ]] || die 'HOME must be an absolute path'
# A missing home cannot be a workspace, so its lexical path is sufficient then.
physical_home=$(cd -- "$HOME" 2>/dev/null && pwd -P) || physical_home=$HOME
unsafe_workspace=0
case "$workspace_mount" in
    /|/home|/root|/etc|/usr|/var|/bin|/sbin|/lib|/lib64|/boot|/opt|/srv|/mnt|/media|/proc|/sys|/dev|/run|/tmp)
        unsafe_workspace=1 ;;
esac
[[ "$workspace_mount" != "$physical_home" && ! "$workspace_mount" =~ ^/mnt/[A-Za-z]$ ]] || unsafe_workspace=1
if ((unsafe_workspace)); then
    [[ "${ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE:-}" == 1 ]] \
        || die "refusing sensitive workspace $workspace_mount; launch from a project subdirectory or set exact ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1"
    printf 'antigravity-container: WARNING: sensitive workspace explicitly exposed read/write: %s\n' "$workspace_mount" >&2
fi

# State: unset selects the dedicated home, a path an isolated home, and an
# empty value shared host ~/.gemini (or the configuration override). Only
# lexical checks precede the engine; creation and validation follow it.
readonly CONTAINER_HOME=/antigravity-home
config_override=${ANTIGRAVITY_CONTAINER_CONFIG_DIR:-}
if [[ -n "${ANTIGRAVITY_CONTAINER_STATE_DIR+x}" && -z "$ANTIGRAVITY_CONTAINER_STATE_DIR" ]]; then
    shared_state=1
    state_variable=ANTIGRAVITY_CONTAINER_CONFIG_DIR
    state_request=${config_override:-$HOME/.gemini}
else
    shared_state=0
    [[ -z "$config_override" ]] \
        || die 'ANTIGRAVITY_CONTAINER_CONFIG_DIR requires shared state; set ANTIGRAVITY_CONTAINER_STATE_DIR to an empty value, or unset ANTIGRAVITY_CONTAINER_CONFIG_DIR to keep an isolated home'
    state_variable=ANTIGRAVITY_CONTAINER_STATE_DIR
    state_request=${ANTIGRAVITY_CONTAINER_STATE_DIR:-$HOME/$DEDICATED_HOME_SUFFIX}
fi
[[ "$state_request" == /* && "$state_request" != *:* && "$state_request" != *$'\n'* && "$state_request" != *$'\r'* ]] \
    || die "$state_variable must be an absolute path without colon, CR or LF: $state_request"
state_physical=$state_request
if [[ -d "$state_request" ]]; then
    state_physical=$(cd -- "$state_request" && pwd -P) || die "cannot resolve state directory: $state_request"
elif [[ -d "$(dirname -- "$state_request")" ]]; then
    state_physical=$(cd -- "$(dirname -- "$state_request")" && pwd -P) || die "cannot resolve state directory: $state_request"
    state_physical=$state_physical/$(basename -- "$state_request")
fi
state_physical=${state_physical%/}
[[ "$state_physical/" != "$workspace_mount/"* && "$workspace_mount/" != "$state_physical/"* ]] \
    || die "$state_variable must not overlap the workspace: $state_request"

command -v podman >/dev/null || die 'Podman is required on the host'
command -v timeout >/dev/null || die 'coreutils timeout is required for bounded session cleanup'
# Unix service access also supports running this wrapper inside another container
# on the same host. TCP/SSH transports and Podman Machine are not supported.
[[ -z "${CONTAINER_CONNECTION:-}" ]] || die 'named remote connections are not supported; use local Podman or a local Unix CONTAINER_HOST'
case "${CONTAINER_HOST:-}" in
    '') ;;
    unix://*)
        launch_socket=${CONTAINER_HOST#unix://}
        [[ "$launch_socket" == /* && -n "${launch_socket//\//}" ]] || die 'CONTAINER_HOST requires an absolute Unix socket path beyond /'
        ;;
    *) die 'remote TCP/SSH Podman contexts are not supported; use a local Unix socket' ;;
esac
# Preserve record boundaries: command substitution normally strips all trailing
# newlines, hiding extra blank records. The sentinel retains them for validation.
engine_response=''
capture_engine_info() {
    engine_response=$(podman "$@" && printf '\001') || return 1
    engine_response=${engine_response%$'\001'}
    engine_response=${engine_response%$'\n'}
    [[ "$engine_response" != *$'\n'* && "$engine_response" != *$'\r'* ]]
}
capture_engine_info info --format '{{.Host.Security.Rootless}} {{.Host.OS}} {{.Host.ServiceIsRemote}}' || die 'cannot query Podman or invalid engine response; check local rootless Podman or the same-host Unix service'
runtime_info=$engine_response
launch_pattern='^[[:blank:]]*true[[:blank:]]+linux[[:blank:]]+(true|false)[[:blank:]]*$'
[[ "$engine_response" =~ $launch_pattern ]] || die 'a complete Linux rootless Podman response is required (true linux true|false)'
remote=${BASH_REMATCH[1]}
if [[ "$remote" == true && "${CONTAINER_HOST:-}" != unix:///?* ]]; then
    die 'remote Podman contexts are not supported; set CONTAINER_HOST to a local Unix socket'
fi

# A budget is enforced only when the verified engine reports its cgroup v2
# controller as delegated. Unenforced budgets are not requested, are announced,
# and must be absent from the created configuration (see network/agent_budgets.py).
capture_engine_info info --format '{{.Host.CgroupControllers}}' \
    || die 'cannot query the rootless cgroup controllers; check the Podman engine'
cgroup_controllers=$engine_response
[[ "$cgroup_controllers" =~ ^\[([a-z_]+( [a-z_]+)*)?\]$ ]] \
    || die 'unverifiable cgroup controller list from the Podman engine'
controller_delegated() {
    [[ " ${cgroup_controllers:1:${#cgroup_controllers}-2} " == *" $1 "* ]]
}
budget_args=()
expected_memory=0
expected_cpu=0
pids_enforced=0
if controller_delegated memory; then
    budget_args+=("--memory=$memory_bytes")
    expected_memory=$memory_bytes
else
    printf 'antigravity-container: agent memory budget not enforced: cgroup controller memory is not delegated to the rootless engine\n' >&2
fi
if controller_delegated cpu; then
    budget_args+=("--cpus=$cpu_text")
    expected_cpu=$cpu_nano
else
    printf 'antigravity-container: agent CPU budget not enforced: cgroup controller cpu is not delegated to the rootless engine\n' >&2
fi
if controller_delegated pids; then
    budget_args+=("--pids-limit=$pids_limit")
    pids_enforced=1
else
    # Override any containers.conf default that would request the missing controller.
    budget_args+=(--pids-limit=-1)
    printf 'antigravity-container: agent process budget not enforced: cgroup controller pids is not delegated to the rootless engine\n' >&2
fi
if ((restricted)); then
    command -v python3 >/dev/null || die 'host Python 3 is required for restricted network policy validation'
    [[ "$remote" == true ]] \
        || die 'restricted networking currently requires the tested same-host Unix service; local-engine enforcement is unverified'
    capture_engine_info info --format '{{.Host.NetworkBackend}}' || die 'cannot verify restricted network backend'
    network_backend=$engine_response
    capture_engine_info version --format '{{.Server.Version}}' || die 'cannot verify restricted network server version'
    network_version=$engine_response
    capture_engine_info info --format '{{json .Host}}' || die 'cannot verify restricted platform security policy'
    network_platform=$engine_response
elif ((qualification_probe)); then
    die 'qualification probes require restricted networking'
fi

caller_uid=$(id -u)
caller_gid=$(id -g)
socket="${ANTIGRAVITY_CONTAINER_PODMAN_SOCKET:-${XDG_RUNTIME_DIR:-/run/user/$caller_uid}/podman/podman.sock}"
if [[ -z "${ANTIGRAVITY_CONTAINER_PODMAN_SOCKET:-}" && "${CONTAINER_HOST:-}" == unix:///* ]]; then
    socket=${CONTAINER_HOST#unix://}
fi
if ((podman_access)); then
    [[ "$socket" == /* ]] || die "Podman socket path must be absolute: $socket"
    [[ -S "$socket" && -r "$socket" && -w "$socket" ]] || die "Podman socket not accessible: $socket; enable 'systemctl --user start podman.socket' or start 'podman system service --time=0'"
    socket=$(readlink -f -- "$socket") || die "cannot resolve Podman socket: $socket"
    capture_engine_info --remote --url "unix://$socket" info --format '{{.Host.Security.Rootless}} {{.Host.RemoteSocket.Path}}' || die 'cannot access the selected Podman socket or invalid multiline response; check service permissions and SELinux policy'
    # The path is the complete remainder, including spaces. It can differ from
    # the accessible endpoint when this wrapper runs inside another container.
    # Podman 5 reports the service socket as a unix:// URL; earlier releases report the bare path.
    socket_pattern='^true[[:blank:]]+(unix://)?(/.+)$'
    [[ "$engine_response" =~ $socket_pattern ]] || die 'the selected Podman socket must report verified rootless true and an absolute host socket path'
    host_socket=${BASH_REMATCH[2]}
fi

script_path=$(readlink -f -- "${BASH_SOURCE[0]}")
script_dir=$(dirname -- "$script_path")
image="${ANTIGRAVITY_CONTAINER_IMAGE:-localhost/antigravity-cli:latest}"

validate_private() {
    local path=$1 mode
    [[ -r "$path" && -w "$path" && -x "$path" ]] || die "state directory is not accessible: $path"
    mode=$(stat -c '%a' -- "$path")
    [[ $(stat -c '%u' -- "$path") == "$caller_uid" ]] || die 'the state directory must belong to the calling user'
    (( (8#$mode & 077) == 0 )) || die 'the state directory must be private (chmod 700); use a native Linux filesystem if this filesystem does not enforce Unix permissions'
}
(umask 077; mkdir -p -- "$state_request") || die "cannot create state directory: $state_request"
state_dir=$(cd -- "$state_request" && pwd -P) || die "cannot resolve state directory: $state_request"
validate_private "$state_dir"
if ((shared_state == 0)); then
    # The configuration directory always exists in the session, as for the
    # other wrappers; an existing one created by agy is left unchanged.
    if [[ ! -e "$state_dir/.gemini" && ! -L "$state_dir/.gemini" ]]; then
        (umask 077; mkdir -- "$state_dir/.gemini") || die "cannot create state directory: $state_dir/.gemini"
    fi
    [[ -d "$state_dir/.gemini" && ! -L "$state_dir/.gemini" ]] || die "configuration directory is not a directory: $state_dir/.gemini"
fi

ca_bundle=''
if ((trust_host_ca)); then
    if [[ -n "${ANTIGRAVITY_CONTAINER_CA_BUNDLE:-}" ]]; then
        [[ -f "$ANTIGRAVITY_CONTAINER_CA_BUNDLE" ]] || die "ANTIGRAVITY_CONTAINER_CA_BUNDLE is not a file: $ANTIGRAVITY_CONTAINER_CA_BUNDLE"
        ca_bundle=$(readlink -f -- "$ANTIGRAVITY_CONTAINER_CA_BUNDLE")
    else
        for candidate in /etc/ssl/certs/ca-certificates.crt /etc/pki/tls/certs/ca-bundle.crt; do
            if [[ -f "$candidate" ]]; then
                ca_bundle=$candidate
                break
            fi
        done
        [[ -n "$ca_bundle" ]] || die 'no default CA bundle found; set ANTIGRAVITY_CONTAINER_CA_BUNDLE to a bundle file'
    fi
    [[ "$ca_bundle" != *[:$'\n'$'\r']* ]] || die "CA bundle path must not contain colon, CR or LF: $ca_bundle"
    if ((shared_state == 0)); then
        # Resolve first so an existing symlink cannot move the CA mount parent.
        ca_parent=$(readlink -m -- "$state_dir/ca")
        [[ "$ca_parent" == "$state_dir/ca" ]] || die "CA mount parent escapes the state home: $state_dir/ca"
        if [[ ! -e "$ca_parent" ]]; then
            (umask 077; mkdir -- "$ca_parent") || die "cannot create state directory: $ca_parent"
        fi
        validate_private "$ca_parent"
    fi
fi

# Restricted sessions use the shared helper; this wrapper keeps only the
# agent-specific command, environment, state and credentials.
session_helper=(python3 -I "$script_dir/network/session.py")
network_inputs=()
qualification_inputs=()
guard_digest=''
if ((restricted)); then
    network_inputs=(--installation "$script_dir" --writable "$workspace_mount" --writable "$state_dir"
        --mount-target "$workspace_mount" --mount-target "$CONTAINER_HOME")
    if [[ "$network_mode" == provider ]]; then
        network_inputs+=(--policy "$ANTIGRAVITY_CONTAINER_NETWORK_POLICY"
            --profile "$ANTIGRAVITY_CONTAINER_NETWORK_PROFILE" --proxy-image "$ANTIGRAVITY_CONTAINER_EGRESS_IMAGE"
            --runtime "$ANTIGRAVITY_CONTAINER_NETWORK_RUNTIME_DIR")
    fi
    prepare_inputs=(--mode "$network_mode" --server-version "$network_version"
        --backend "$network_backend" --endpoint "${CONTAINER_HOST:-}" --engine "$runtime_info")
    if ((qualification_probe)); then
        prepare_inputs+=(--probe --qualification-input "${ANTIGRAVITY_CONTAINER_QUALIFICATION_INPUT:-}"
            --workspace "$workspace")
    fi
    prepared=$(printf '%s\n' "$network_platform" | "${session_helper[@]}" prepare "${network_inputs[@]}" "${prepare_inputs[@]}") \
        || exit 1
    read -r guard_digest qualification_token qualification_tls <<< "$prepared"
    if ((qualification_probe)); then
        qualification_inputs=(--probe --token "$qualification_token" --workspace "$workspace"
            --qualification-input "${ANTIGRAVITY_CONTAINER_QUALIFICATION_INPUT:-}")
        [[ "$qualification_tls" != 1 ]] || qualification_inputs+=(--tls)
    fi
fi

# Every build, including the automatic build of a missing image, is maintenance:
# it downloads the pinned agy release outside runtime filtering.
maintenance=0
[[ "${ANTIGRAVITY_CONTAINER_MAINTENANCE:-}" != 1 ]] || maintenance=1
needs_build=$build_image
if ((build_image == 0)); then
    if podman image exists "$image"; then
        :
    else
        image_status=$?
        [[ "$image_status" == 1 ]] || die "cannot inspect image: $image"
        needs_build=1
    fi
fi
if ((needs_build)); then
    ((maintenance)) || die "image $image needs a build; prepare it with exact ANTIGRAVITY_CONTAINER_MAINTENANCE=1 (host pulls and build RUN steps are outside runtime filtering)"
    build_args=(--tag "$image" --file "$script_dir/Containerfile")
    ((build_image == 0)) || build_args=(--no-cache "${build_args[@]}")
    # The opted-in host CA bundle also verifies the build's package and artifact
    # fetches. It is a build secret: mounted only for its RUN steps, never stored.
    [[ -z "$ca_bundle" ]] || build_args+=(--secret "id=build-ca,src=$ca_bundle")
    build_status=0
    podman build "${build_args[@]}" "$script_dir" </dev/null || build_status=$?
    if ((build_status)); then
        printf 'antigravity-container: image build failed: %s (status %s)\n' "$image" "$build_status" >&2
        exit "$build_status"
    fi
fi
if [[ "$network_mode" == provider ]]; then
    if podman image exists "$ANTIGRAVITY_CONTAINER_EGRESS_IMAGE"; then
        :
    else
        image_status=$?
        [[ "$image_status" == 1 ]] || die 'cannot inspect immutable egress proxy image'
        ((maintenance)) && [[ "$ANTIGRAVITY_CONTAINER_EGRESS_IMAGE" == *@sha256:* ]] \
            || die 'proxy image is absent; prepare the pinned artifact under explicit operator maintenance authorization (ANTIGRAVITY_CONTAINER_MAINTENANCE=1 and a registry digest)'
        podman pull "$ANTIGRAVITY_CONTAINER_EGRESS_IMAGE"
    fi
fi
# Restricted sessions and their qualification bind the immutable image ID.
session_image=$image
if ((restricted)); then
    capture_engine_info image inspect --format '{{.Id}}' "$image" || die 'cannot resolve restricted runtime image identity'
    [[ "$engine_response" =~ ^(sha256:)?[a-f0-9]{64}$ ]] || die 'invalid restricted runtime image identity'
    session_image=$engine_response
fi

container_args=(
    --rm --interactive --read-only
    --userns=keep-id --user "$caller_uid:$caller_gid"
    --cap-drop=all --security-opt=no-new-privileges
    "${budget_args[@]}"
    --workdir "$workspace"
    --tmpfs '/tmp:rw,exec,nosuid,nodev,mode=1777,size=512m'
    --tmpfs '/run:rw,nosuid,nodev,noexec,mode=1777,size=32m'
    --tmpfs '/var/tmp:rw,nosuid,nodev,noexec,mode=1777,size=512m'
    # Mask engine default mounts at /run/secrets (RHEL subscription secrets from
    # mounts.conf): Podman skips its own mount there, leaving an empty read-only
    # tmpfs that the guard accepts and that exposes no host material.
    --mount type=tmpfs,destination=/run/secrets,ro=true
    # Podman forces /dev read-only with --read-only-tmpfs=false, and crun >= 1.27
    # must replace /dev/console to attach a terminal. Keep automatic provisioning,
    # so the engine provides /dev and a devpts that allows pseudo-terminals (an
    # explicit devpts mount gets ptmxmode=000 and no PTY can be opened), and mask
    # /dev/shm with an empty read-only tmpfs.
    --mount type=tmpfs,destination=/dev/shm,ro=true
    --env "HOME=$CONTAINER_HOME"
    --env EDITOR=nano --env VISUAL=nano
    --volume "$workspace_mount:$workspace_mount:rw"
)
if ((shared_state)); then
    # The shared configuration is the only persistent part of an ephemeral home.
    container_args+=(--tmpfs "$CONTAINER_HOME:rw,nosuid,nodev,mode=1777,size=64m"
        --volume "$state_dir:$CONTAINER_HOME/.gemini:rw")
else
    container_args+=(--volume "$state_dir:$CONTAINER_HOME:rw")
fi
# The profile's configuration variable names the effective directory in the
# session; the host value is never forwarded.
container_args+=(--env "ANTIGRAVITY_CONTAINER_CONFIG_DIR=$CONTAINER_HOME/.gemini")
if ((trust_host_ca)); then
    container_args+=(--volume "$ca_bundle:$CONTAINER_HOME/ca/bundle.pem:ro")
    for variable in SSL_CERT_FILE REQUESTS_CA_BUNDLE CURL_CA_BUNDLE NODE_EXTRA_CA_CERTS; do
        container_args+=(--env "$variable=$CONTAINER_HOME/ca/bundle.pem")
    done
fi
((run_timeout == 0)) || container_args+=(--timeout "$run_timeout")
if [[ -t 0 && -t 1 ]]; then
    container_args+=(--tty)
    [[ -z "${TERM:-}" ]] || container_args+=(--env TERM)
fi
# Values for credentials remain in the creating client's environment, never argv.
# Restricted modes forward no host proxy or CA value and only the profile's key.
if ((restricted)); then
    [[ -z "$profile_credential" || ! -v "$profile_credential" ]] || container_args+=(--env "$profile_credential")
else
    [[ ! -v GEMINI_API_KEY ]] || container_args+=(--env GEMINI_API_KEY)
fi
# Protected values follow forwarding: no bus or keyring, and no self-update.
container_args+=(--unsetenv DBUS_SESSION_BUS_ADDRESS --env AGY_CLI_DISABLE_AUTO_UPDATE=true)
if ((podman_access)); then
    container_args+=(
        --volume "$host_socket:/run/podman/podman.sock:rw"
        --env CONTAINER_HOST=unix:///run/podman/podman.sock
    )
else
    container_args+=(--unsetenv CONTAINER_HOST)
fi
if ((qualification_probe)); then
    args=()  # The shared helper supplies the fixed probe command.
elif ((shell_mode)); then
    ((restricted)) || container_args+=(--entrypoint /bin/bash)
    args=()
elif ((yolo)); then
    args=(--dangerously-skip-permissions "${args[@]}")
fi

prefix=${workspace##*/}
prefix=$(printf '%s' "$prefix" | sed -E 's/[^a-zA-Z0-9_.-]+/-/g; s/^[.-]+//; s/[.-]+$//')
prefix=${prefix:-antigravity-container}

# Ownership comes from a private CID file, including when create is interrupted.
container_id=''
client_pid=''
session_tmp=''
pending_signal=''
pending_status=0
creating=0
attached=0
name=''
qualification_check_pid=''
session_start_pid=''
diagnostics_pid=''
diagnostics_fd=''

# shellcheck disable=SC2329 # Invoked by signal traps.
record_signal() {
    if ((pending_status == 0)); then
        pending_signal=$1
        pending_status=$2
    fi
    # A pending create is resolved by cleanup, with a finite completion budget.
    if [[ -n "$client_pid" || -n "$qualification_check_pid" || -n "$session_start_pid" ]]; then
        exit "$pending_status"
    fi
}

# Restricted helpers: TERM, a bounded grace period, then KILL and reap.
# shellcheck disable=SC2329 # Invoked through signal/EXIT cleanup.
child_running() {
    local child=$1 running
    [[ -n "$child" ]] || return 1
    while IFS= read -r running; do
        [[ "$running" != "$child" ]] || return 0
    done < <(jobs -p)
    return 1
}
# shellcheck disable=SC2329 # Invoked through signal/EXIT cleanup.
reap_helper() {
    local child=$1 grace=$2 until
    child_running "$child" || { wait "$child" 2>/dev/null || true; return 0; }
    kill -TERM "$child" 2>/dev/null || true
    until=$((SECONDS + grace))
    while child_running "$child" && ((SECONDS < until)); do sleep 0.05; done
    if child_running "$child"; then
        printf 'antigravity-container: restricted helper %s did not confirm cleanup before the deadline\n' "$child" >&2
        kill -KILL "$child" 2>/dev/null || true
    fi
    until=$((SECONDS + 1))
    while child_running "$child" && ((SECONDS < until)); do sleep 0.05; done
    if child_running "$child"; then
        printf 'antigravity-container: cannot reap restricted helper %s within deadline; inspect it explicitly\n' "$child" >&2
    else
        wait "$child" 2>/dev/null || true
    fi
}

# shellcheck disable=SC2329 # Called by EXIT cleanup and its client reaper.
wait_for_client_until() {
    local deadline=$1
    while kill -0 "$client_pid" 2>/dev/null; do
        ((SECONDS < deadline)) || return 1
        sleep 0.05
    done
}

# shellcheck disable=SC2329 # Called by EXIT cleanup.
reap_client() {
    [[ -n "$client_pid" ]] || return 0
    if ! wait_for_client_until "$SECONDS"; then
        kill -TERM "$client_pid" 2>/dev/null || true
        if ! wait_for_client_until "$((SECONDS + 5))"; then
            kill -KILL "$client_pid" 2>/dev/null || true
        fi
    fi
    if wait_for_client_until "$((SECONDS + 1))"; then
        wait "$client_pid" 2>/dev/null || true
    else
        printf 'antigravity-container: cannot reap Podman client %s; inspect it manually\n' "$client_pid" >&2
    fi
    client_pid=''
}

recover_container_id() {
    local recovered=''
    [[ -n "$session_tmp" && -s "$session_tmp/cid" ]] || return 0
    recovered=$(< "$session_tmp/cid")
    [[ "$recovered" =~ ^[a-f0-9]{64}$ ]] || {
        printf 'antigravity-container: invalid container ID in private creation record; inspect creation manually\n' >&2
        return 1
    }
    container_id=$recovered
}

# shellcheck disable=SC2329 # Invoked by the EXIT trap.
cleanup() {
    local status=$? control_status=0 shutdown_deadline
    ((pending_status == 0)) || status=$pending_status
    trap '' TERM INT HUP
    shutdown_deadline=$((SECONDS + 20))
    if [[ -n "$qualification_check_pid" ]]; then
        reap_helper "$qualification_check_pid" 13
        qualification_check_pid=''
    fi
    if [[ -n "$session_start_pid" ]]; then
        # The session helper owns a separate process group. Reap the whole
        # group before its leader, including an engine client that ignores TERM.
        kill -TERM -- "-$session_start_pid" 2>/dev/null || true
        sleep 0.1
        kill -KILL -- "-$session_start_pid" 2>/dev/null || true
        reap_helper "$session_start_pid" 1
        session_start_pid=''
    fi
    if ((creating)); then
        if [[ -n "$client_pid" ]]; then
            wait_for_client_until "$((SECONDS + 5))" || true
            reap_client
        fi
        # A CID can be published while the local client is being cancelled.
        recover_container_id || true
        if ((pending_status)) && [[ -z "$container_id" ]]; then
            printf 'antigravity-container: creation outcome unresolved for %s; inspect the engine manually (no verified owned ID)\n' "$name" >&2
        fi
    fi
    if [[ -n "$container_id" ]]; then
        if ((pending_status && attached)); then
            if timeout --kill-after=1s 5s podman kill --signal "$pending_signal" "$container_id" >/dev/null; then
                [[ -z "$client_pid" ]] || wait_for_client_until "$((SECONDS + 5))" || true
            else
                printf 'antigravity-container: cannot forward %s to owned container %s\n' "$pending_signal" "$container_id" >&2
            fi
        fi
        timeout --kill-after=1s 5s podman rm --force --ignore --time 0 "$container_id" >/dev/null || control_status=$?
        if ((control_status)); then
            printf 'antigravity-container: cannot remove owned container %s (status %s); inspect the engine and remove it manually\n' "$container_id" "$control_status" >&2
        fi
    fi
    reap_client
    if [[ -n "$diagnostics_fd" ]]; then
        exec {diagnostics_fd}>&-
        diagnostics_fd=''
    fi
    if [[ -n "$diagnostics_pid" ]]; then
        # Drain the final client output before reaping the stderr filter.
        drain_until=$((SECONDS + 1))
        while child_running "$diagnostics_pid" && ((SECONDS < drain_until)); do sleep 0.01; done
        reap_helper "$diagnostics_pid" 1
        diagnostics_pid=''
    fi
    if [[ "$network_mode" == provider && -n "$session_tmp" ]]; then
        # Owned proxy recovery/removal and diagnostics share the remaining budget.
        "${session_helper[@]}" stop --session "$session_tmp" --deadline "$((shutdown_deadline - SECONDS))" \
            --container "${container_id:-unknown}" || true
    fi
    [[ -z "$session_tmp" ]] || rm -rf -- "$session_tmp" || true
    return "$status"
}
trap cleanup EXIT
trap 'record_signal TERM 143' TERM
trap 'record_signal INT 130' INT
trap 'record_signal HUP 129' HUP
if [[ "$network_mode" == provider ]]; then
    session_tmp=$(umask 077; mktemp -d -- "$ANTIGRAVITY_CONTAINER_NETWORK_RUNTIME_DIR/session.XXXXXXXXXXXX") \
        || die 'cannot create private session directory in ANTIGRAVITY_CONTAINER_NETWORK_RUNTIME_DIR'
else
    session_tmp=$(umask 077; mktemp -d) || die 'cannot create private session bookkeeping directory'
fi
(umask 077; : > "$session_tmp/output"; : > "$session_tmp/error")
((pending_status == 0)) || exit "$pending_status"
printf 'antigravity-container: network mode=%s\n' "$network_mode" >&2
if ((restricted && qualification_probe == 0)); then
    # The report binds the effective state; an unset variable is the dedicated home.
    ANTIGRAVITY_CONTAINER_IMAGE="$session_image" ANTIGRAVITY_CONTAINER_STATE_DIR="${ANTIGRAVITY_CONTAINER_STATE_DIR-$state_dir}" \
        python3 -I "$script_dir/network/qualify.py" check &
    qualification_check_pid=$!
    qualification_status=0
    wait "$qualification_check_pid" || qualification_status=$?
    qualification_check_pid=''
    ((pending_status == 0)) || exit "$pending_status"
    ((qualification_status == 0)) || exit "$qualification_status"
fi
if [[ "$network_mode" == provider ]]; then
    "${session_helper[@]}" start "${network_inputs[@]}" "${qualification_inputs[@]}" --session "$session_tmp" \
        --guard-digest "$guard_digest" >"$session_tmp/policy.identity" &
    session_start_pid=$!
    start_status=0
    wait "$session_start_pid" || start_status=$?
    session_start_pid=''
    ((pending_status == 0)) || exit "$pending_status"
    ((start_status == 0)) || exit "$start_status"
fi
if ((restricted)); then
    application=()
    if ((shell_mode)); then
        application=(/bin/bash)
    elif ((qualification_probe == 0)); then
        application=(/usr/local/bin/antigravity-entrypoint "${args[@]}")
    fi
    "${session_helper[@]}" agent-args --installation "$script_dir" --mode "$network_mode" \
        --session "$session_tmp" --guard-digest "$guard_digest" "${qualification_inputs[@]}" \
        -- "${application[@]}" >"$session_tmp/agent.args"
    mapfile -d '' -t restricted_args <"$session_tmp/agent.args"
    [[ "${restricted_args[0]:-}" =~ ^[0-9]+$ ]] || die 'invalid restricted session arguments'
    container_args+=("${restricted_args[@]:1:${restricted_args[0]}}")
    args=("${restricted_args[@]:$((1 + restricted_args[0]))}")
fi

names=$(podman ps --all --format '{{.Names}}') || die 'cannot list Podman containers'
((pending_status == 0)) || exit "$pending_status"
next_index=0
while IFS= read -r name; do
    [[ "$name" == "$prefix-"* ]] || continue
    suffix=${name#"$prefix-"}
    [[ "$suffix" =~ ^[0-9]+$ && ${#suffix} -lt 10 ]] || continue
    numeric=$((10#$suffix))
    ((numeric < next_index)) || next_index=$((numeric + 1))
done <<< "$names"
name=''

for ((attempt=0; attempt<20; attempt++)); do
    ((pending_status == 0)) || exit "$pending_status"
    name="$prefix-$next_index"
    rm -f -- "$session_tmp/cid"
    creating=1
    podman create --name "$name" --cidfile "$session_tmp/cid" \
        --label "io.antigravity-container.session=${session_tmp##*/}" \
        "${container_args[@]}" "$session_image" "${args[@]}" \
        </dev/null >"$session_tmp/output" 2>"$session_tmp/error" &
    client_pid=$!
    ((pending_status == 0)) || exit "$pending_status"
    create_status=0
    wait "$client_pid" || create_status=$?
    ((pending_status == 0)) || exit "$pending_status"
    client_pid=''
    recover_container_id || die 'cannot verify the created container identity'
    creating=0
    if ((create_status == 0)); then
        [[ -n "$container_id" ]] || die 'creation succeeded without a container ID'
        break
    fi
    cat -- "$session_tmp/error" >&2
    [[ -z "$container_id" ]] || exit "$create_status"
    exists_status=0
    podman container exists "$name" || exists_status=$?
    ((pending_status == 0)) || exit "$pending_status"
    case "$exists_status" in
        0) next_index=$((next_index + 1)) ;;
        1) exit "$create_status" ;;
        *) die "cannot verify container name collision for $name (status $exists_status)" ;;
    esac
done
[[ -n "$container_id" ]] || die 'could not reserve a container name after 20 attempts'
((pending_status == 0)) || exit "$pending_status"

# Engine flags alone are not evidence: require the created configuration to
# carry every enforced budget and no unenforced one before the application starts.
configured_budgets=$(timeout --kill-after=1s 10s podman inspect --type container \
    --format '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}} {{.HostConfig.PidsLimit}}' "$container_id") \
    || die 'Cannot inspect session resource budgets; session not started'
((pending_status == 0)) || exit "$pending_status"
read -r configured_memory configured_cpu configured_pids extra <<< "$configured_budgets"
budgets_applied=0
if [[ -z "${extra:-}" && "$configured_budgets" != *$'\n'* && "$configured_memory" == "$expected_memory" && "$configured_cpu" == "$expected_cpu" ]]; then
    if ((pids_enforced)); then
        [[ "$configured_pids" == "$pids_limit" ]] && budgets_applied=1
    else
        [[ "$configured_pids" =~ ^(0|-1)$ ]] && budgets_applied=1
    fi
fi
((budgets_applied)) \
    || die "Session resource budgets were not applied as expected (memory=$expected_memory nano_cpus=$expected_cpu pids=$( ((pids_enforced)) && printf '%s' "$pids_limit" || printf 'unenforced')); engine reports controllers $cgroup_controllers; check rootless cgroup v2 controller delegation; session not started"

# Explicit stdin redirection prevents Bash replacing stdin with /dev/null.
attached=1
started_at=$SECONDS
if [[ -f "$script_dir/setup/diagnostics.py" ]] && command -v python3 >/dev/null; then
    # Optional for unrestricted installs without host Python. Only the exact
    # successful Podman 4.3 restart-check line changes level; errors pass.
    mkfifo -- "$session_tmp/diagnostics.pipe"
    python3 -I "$script_dir/setup/diagnostics.py" <"$session_tmp/diagnostics.pipe" >&2 &
    diagnostics_pid=$!
    exec {diagnostics_fd}>"$session_tmp/diagnostics.pipe"
    podman start --attach --interactive --sig-proxy=false "$container_id" <&0 2>&"$diagnostics_fd" {diagnostics_fd}>&- &
    client_pid=$!
    exec {diagnostics_fd}>&-
    diagnostics_fd=''
else
    podman start --attach --interactive --sig-proxy=false "$container_id" <&0 &
    client_pid=$!
fi
((pending_status == 0)) || exit "$pending_status"
status=0
wait "$client_pid" || status=$?
((pending_status == 0)) || exit "$pending_status"
client_pid=''
if ((run_timeout > 0 && status != 0 && SECONDS - started_at >= run_timeout)); then
    printf 'antigravity-container: session lifetime limit reached (%s s); exit status %s\n' "$run_timeout" "$status" >&2
fi
exit "$status"
