#!/usr/bin/env bash
set -Eeuo pipefail

die() { printf 'antigravity-container: %s\n' "$*" >&2; exit 1; }

usage() {
    cat <<'EOF'
Usage: antigravity-container.sh [container options] [agy arguments...]

Run Google Antigravity CLI in a rootless Podman container.

Container options:
  --container-build         rebuild the image without cached downloads
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
  ANTIGRAVITY_CONTAINER_IMAGE       default: localhost/antigravity-cli:latest
  ANTIGRAVITY_CONTAINER_STATE_DIR   default: ~/.local/share/antigravity-container/home
  ANTIGRAVITY_YOLO                  bypass agy approvals (default: disabled)
  ANTIGRAVITY_CONTAINER_PODMAN      expose the host Podman service (default: disabled)
  ANTIGRAVITY_CONTAINER_PODMAN_SOCKET
    default: ${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock
  GEMINI_API_KEY                    forwarded if set; requires modelProvider: gemini
  ANTIGRAVITY_CONTAINER_MEMORY_LIMIT  session memory, integer with k/m/g unit (default: 4g)
  ANTIGRAVITY_CONTAINER_CPU_LIMIT     session CPUs, up to 3 decimals (default: 2)
  ANTIGRAVITY_CONTAINER_PIDS_LIMIT    session process limit (default: 512)
    Budgets cannot be disabled; they require delegated rootless cgroup v2
    cpu/memory/pids controllers
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
EOF
}

build_image=0
shell_mode=0
git_worktree=0
args=()
for arg in "$@"; do
    case "$arg" in
        --container-help) usage; exit 0 ;;
        --container-build) build_image=1 ;;
        --container-shell) shell_mode=1 ;;
        --container-git-worktree) git_worktree=1 ;;
        *) args+=("$arg") ;;
    esac
done

boolean() {
    case "${2,,}" in
        1|true|yes) printf 1 ;;
        ''|0|false|no) printf 0 ;;
        *) die "$1 must be 0, 1, true, false, yes, or no" ;;
    esac
}
yolo=$(boolean ANTIGRAVITY_YOLO "${ANTIGRAVITY_YOLO:-}")
podman_access=0
[[ "${ANTIGRAVITY_CONTAINER_PODMAN:-}" != 1 ]] || podman_access=1

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
[[ "$pids_text" =~ ^(0|[1-9][0-9]{0,9})$ ]] && ((pids_text > 0 && pids_text <= 4194304)) \
    || die 'ANTIGRAVITY_CONTAINER_PIDS_LIMIT must be a positive integer process count up to 4194304'
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
capture_engine_info info --format '{{.Host.Security.Rootless}} {{.Host.OS}} {{.Host.ServiceIsRemote}}' || die 'cannot query Podman or invalid multiline response; check the local rootless service'
launch_pattern='^[[:blank:]]*true[[:blank:]]+linux[[:blank:]]+(true|false)[[:blank:]]*$'
[[ "$engine_response" =~ $launch_pattern ]] || die 'a complete Linux rootless Podman response is required (true linux true|false)'
remote=${BASH_REMATCH[1]}
if [[ "$remote" == true && "${CONTAINER_HOST:-}" != unix:///?* ]]; then
    die 'remote Podman contexts are not supported; set CONTAINER_HOST to a local Unix socket'
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
    socket_pattern='^true[[:blank:]]+(/.+)$'
    [[ "$engine_response" =~ $socket_pattern ]] || die 'the selected Podman socket must report verified rootless true and an absolute host socket path'
    host_socket=${BASH_REMATCH[1]}
fi

script_path=$(readlink -f -- "${BASH_SOURCE[0]}")
script_dir=$(dirname -- "$script_path")
image="${ANTIGRAVITY_CONTAINER_IMAGE:-localhost/antigravity-cli:latest}"
state_dir="${ANTIGRAVITY_CONTAINER_STATE_DIR:-$HOME/.local/share/antigravity-container/home}"

(umask 077; mkdir -p -- "$state_dir") || die "cannot create state directory: $state_dir"
state_dir=$(cd -- "$state_dir" && pwd -P) || die "cannot resolve state directory: $state_dir"
[[ -r "$state_dir" && -w "$state_dir" && -x "$state_dir" ]] || die "state directory is not accessible: $state_dir"
state_mode=$(stat -c '%a' -- "$state_dir")
[[ $(stat -c '%u' -- "$state_dir") == "$caller_uid" ]] || die 'the state directory must belong to the calling user'
(( (8#$state_mode & 077) == 0 )) || die 'the state directory must be private (chmod 700); use a native Linux filesystem if this filesystem does not enforce Unix permissions'

if ((build_image)); then
    podman build --no-cache --tag "$image" --file "$script_dir/Containerfile" "$script_dir"
else
    if podman image exists "$image"; then
        :
    else
        image_status=$?
        [[ "$image_status" == 1 ]] || die "cannot inspect image: $image"
        podman build --tag "$image" --file "$script_dir/Containerfile" "$script_dir"
    fi
fi

container_args=(
    --rm --interactive --read-only --read-only-tmpfs=false
    --userns=keep-id --user "$caller_uid:$caller_gid"
    --cap-drop=all --security-opt=no-new-privileges
    "--memory=$memory_bytes" "--cpus=$cpu_text" "--pids-limit=$pids_limit"
    --workdir "$workspace"
    --tmpfs '/tmp:rw,exec,nosuid,nodev,mode=1777,size=512m'
    --tmpfs '/run:rw,nosuid,nodev,noexec,mode=1777,size=32m'
    --tmpfs '/var/tmp:rw,nosuid,nodev,noexec,mode=1777,size=512m'
    --env HOME=/antigravity-home
    --env EDITOR=nano --env VISUAL=nano
    --env AGY_CLI_DISABLE_AUTO_UPDATE=true
    --volume "$workspace_mount:$workspace_mount:rw"
    --volume "$state_dir:/antigravity-home:rw"
)
((run_timeout == 0)) || container_args+=(--timeout "$run_timeout")
if [[ -t 0 && -t 1 ]]; then
    container_args+=(--tty)
    [[ -z "${TERM:-}" ]] || container_args+=(--env TERM)
fi
[[ ! -v GEMINI_API_KEY ]] || container_args+=(--env GEMINI_API_KEY)
if ((podman_access)); then
    container_args+=(
        --volume "$host_socket:/run/podman/podman.sock:rw"
        --env CONTAINER_HOST=unix:///run/podman/podman.sock
    )
else
    container_args+=(--unsetenv CONTAINER_HOST)
fi
if ((shell_mode)); then
    container_args+=(--entrypoint /bin/bash)
    args=()
elif ((yolo)); then
    args=(--dangerously-skip-permissions "${args[@]}")
fi

prefix=${workspace##*/}
prefix=$(printf '%s' "$prefix" | sed -E 's/[^a-zA-Z0-9_.-]+/-/g; s/^[.-]+//; s/[.-]+$//')
prefix=${prefix:-antigravity-container}
names=$(podman ps --all --format '{{.Names}}') || die 'cannot list Podman containers'
next_index=0
while IFS= read -r name; do
    [[ "$name" == "$prefix-"* ]] || continue
    suffix=${name#"$prefix-"}
    [[ "$suffix" =~ ^[0-9]+$ && ${#suffix} -lt 10 ]] || continue
    numeric=$((10#$suffix))
    ((numeric < next_index)) || next_index=$((numeric + 1))
done <<< "$names"

# Ownership comes from a private CID file, including when create is interrupted.
container_id=''
client_pid=''
session_tmp=''
pending_signal=''
pending_status=0
creating=0
attached=0
name=''

# shellcheck disable=SC2329 # Invoked by signal traps.
record_signal() {
    if ((pending_status == 0)); then
        pending_signal=$1
        pending_status=$2
    fi
    # A pending create is resolved by cleanup, with a finite completion budget.
    [[ -z "$client_pid" ]] || exit "$pending_status"
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
    local status=$? control_status=0
    ((pending_status == 0)) || status=$pending_status
    trap '' TERM INT HUP
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
    [[ -z "$session_tmp" ]] || rm -rf -- "$session_tmp" || true
    return "$status"
}
trap cleanup EXIT
trap 'record_signal TERM 143' TERM
trap 'record_signal INT 130' INT
trap 'record_signal HUP 129' HUP
session_tmp=$(umask 077; mktemp -d) || die 'cannot create private session bookkeeping directory'
(umask 077; : > "$session_tmp/output"; : > "$session_tmp/error")
((pending_status == 0)) || exit "$pending_status"
for ((attempt=0; attempt<20; attempt++)); do
    ((pending_status == 0)) || exit "$pending_status"
    name="$prefix-$next_index"
    rm -f -- "$session_tmp/cid"
    creating=1
    podman create --name "$name" --cidfile "$session_tmp/cid" "${container_args[@]}" "$image" "${args[@]}" \
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
# carry every selected budget before the application starts.
configured_budgets=$(timeout --kill-after=1s 10s podman inspect --type container \
    --format '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}} {{.HostConfig.PidsLimit}}' "$container_id") \
    || die 'Cannot inspect session resource budgets; session not started'
((pending_status == 0)) || exit "$pending_status"
[[ "$configured_budgets" == "$memory_bytes $cpu_nano $pids_limit" ]] \
    || die "Session resource budgets were not applied (expected memory=$memory_bytes nano_cpus=$cpu_nano pids=$pids_limit); check rootless cgroup v2 cpu/memory/pids controller delegation; session not started"

# Explicit stdin redirection prevents Bash replacing stdin with /dev/null.
attached=1
started_at=$SECONDS
podman start --attach --interactive --sig-proxy=false "$container_id" <&0 &
client_pid=$!
((pending_status == 0)) || exit "$pending_status"
status=0
wait "$client_pid" || status=$?
((pending_status == 0)) || exit "$pending_status"
client_pid=''
if ((run_timeout > 0 && status != 0 && SECONDS - started_at >= run_timeout)); then
    printf 'antigravity-container: session lifetime limit reached (%s s); exit status %s\n' "$run_timeout" "$status" >&2
fi
exit "$status"
