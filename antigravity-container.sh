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

Environment:
  ANTIGRAVITY_CONTAINER_IMAGE       default: localhost/antigravity-cli:latest
  ANTIGRAVITY_CONTAINER_STATE_DIR   default: ~/.local/share/antigravity-container/home
  ANTIGRAVITY_YOLO                  bypass agy approvals (default: disabled)
  ANTIGRAVITY_CONTAINER_PODMAN      expose the host Podman service (default: disabled)
  ANTIGRAVITY_CONTAINER_PODMAN_SOCKET
    default: ${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock
  GEMINI_API_KEY                    forwarded if set; requires modelProvider: gemini

Booleans accept 1/true/yes or 0/false/no, case-insensitively; empty is disabled.
YOLO adds --dangerously-skip-permissions without changing mounts or settings.
Native CLI flags and existing permissions still apply when YOLO is disabled.

The Podman socket grants control over the host user's containers and permits
host mounts beyond the workspace. It removes the project-only access boundary.
Worktree mode exposes the entire parent, including siblings, read/write.
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
podman_access=$(boolean ANTIGRAVITY_CONTAINER_PODMAN "${ANTIGRAVITY_CONTAINER_PODMAN:-}")

command -v podman >/dev/null || die 'Podman is required on the host'
# Unix service access also supports running this wrapper inside another container
# on the same host. TCP/SSH transports and Podman Machine are not supported.
[[ -z "${CONTAINER_CONNECTION:-}" ]] || die 'named remote connections are not supported; use local Podman or a local Unix CONTAINER_HOST'
case "${CONTAINER_HOST:-}" in
    ''|unix:///*) ;;
    *) die 'remote TCP/SSH Podman contexts are not supported; use a local Unix socket' ;;
esac
runtime_info=$(podman info --format '{{.Host.Security.Rootless}} {{.Host.OS}} {{.Host.ServiceIsRemote}}') || die 'cannot query Podman; check the local rootless service'
read -r rootless runtime_os remote <<< "$runtime_info"
[[ "$rootless" == true && "$runtime_os" == linux ]] || die 'a Linux rootless Podman engine is required'
if [[ "$remote" == true && "${CONTAINER_HOST:-}" != unix:///* ]]; then
    die 'remote Podman contexts are not supported; set CONTAINER_HOST to a local Unix socket'
fi

caller_uid=$(id -u)
caller_gid=$(id -g)
socket="${ANTIGRAVITY_CONTAINER_PODMAN_SOCKET:-${XDG_RUNTIME_DIR:-/run/user/$caller_uid}/podman/podman.sock}"
if [[ -z "${ANTIGRAVITY_CONTAINER_PODMAN_SOCKET:-}" && "${CONTAINER_HOST:-}" == unix:///* ]]; then
    socket=${CONTAINER_HOST#unix://}
fi
if ((podman_access)); then
    [[ -S "$socket" && -r "$socket" && -w "$socket" ]] || die "Podman socket not accessible: $socket; enable 'systemctl --user start podman.socket' or start 'podman system service --time=0'"
    socket=$(readlink -f -- "$socket")
    socket_info=$(podman --remote --url "unix://$socket" info --format '{{.Host.Security.Rootless}} {{.Host.RemoteSocket.Path}}') || die 'cannot access the selected Podman socket; check service permissions and SELinux policy'
    read -r socket_rootless host_socket <<< "$socket_info"
    [[ "$socket_rootless" == true ]] || die 'the selected Podman socket must serve a rootless engine'
    # A wrapper already inside a container sees a remapped Unix socket. Bind
    # sources are resolved by the service, so use its host-side socket path.
    [[ "$host_socket" == /* ]] || die 'the service did not report an absolute host socket path'
fi

script_path=$(readlink -f -- "${BASH_SOURCE[0]}")
script_dir=$(dirname -- "$script_path")
workspace=$(pwd -P)
workspace_mount=$workspace
((git_worktree == 0)) || workspace_mount=$(dirname -- "$workspace")
image="${ANTIGRAVITY_CONTAINER_IMAGE:-localhost/antigravity-cli:latest}"
state_dir="${ANTIGRAVITY_CONTAINER_STATE_DIR:-$HOME/.local/share/antigravity-container/home}"

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

umask 077
mkdir -p -- "$state_dir"
state_dir=$(cd -- "$state_dir" && pwd -P)
[[ -r "$state_dir" && -w "$state_dir" && -x "$state_dir" ]] || die "state directory is not accessible: $state_dir"
state_mode=$(stat -c '%a' -- "$state_dir")
[[ $(stat -c '%u' -- "$state_dir") == "$caller_uid" ]] || die 'the state directory must belong to the calling user'
(( (8#$state_mode & 077) == 0 )) || die 'the state directory must be private (chmod 700); use a native Linux filesystem if this filesystem does not enforce Unix permissions'

container_args=(
    --rm --interactive --read-only
    --userns=keep-id --user "$caller_uid:$caller_gid"
    --workdir "$workspace"
    --tmpfs '/tmp:rw,nosuid,nodev,size=512m'
    --tmpfs '/run:rw,nosuid,nodev,noexec,size=32m'
    --env HOME=/antigravity-home
    --env EDITOR=nano --env VISUAL=nano
    --env AGY_CLI_DISABLE_AUTO_UPDATE=true
    --volume "$workspace_mount:$workspace_mount:rw"
    --volume "$state_dir:/antigravity-home:rw"
)
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

# Reserve the name with create, so an actual process exit code 125 is never
# confused with a create-time naming collision. Remove only our own container.
container_id=''
client_pid=''
# shellcheck disable=SC2329 # Invoked by the EXIT trap.
cleanup() {
    [[ -z "$container_id" ]] || podman rm --force --ignore "$container_id" >/dev/null 2>&1 || true
}
# shellcheck disable=SC2329 # Invoked by signal traps.
forward_signal() {
    local signal=$1 status=$2
    [[ -z "$container_id" ]] || podman kill --signal "$signal" "$container_id" >/dev/null 2>&1 || true
    [[ -z "$client_pid" ]] || wait "$client_pid" 2>/dev/null || true
    exit "$status"
}
trap cleanup EXIT
trap 'forward_signal TERM 143' TERM
trap 'forward_signal INT 130' INT
trap 'forward_signal HUP 129' HUP
create_error=$(mktemp)
for ((attempt=0; attempt<20; attempt++)); do
    name="$prefix-$next_index"
    if container_id=$(podman create --name "$name" "${container_args[@]}" "$image" "${args[@]}" 2>"$create_error"); then
        break
    else
        create_status=$?
        container_id=''
        if podman container exists "$name"; then
            next_index=$((next_index + 1))
        else
            cat -- "$create_error" >&2
            rm -f -- "$create_error"
            exit "$create_status"
        fi
    fi
done
rm -f -- "$create_error"
[[ -n "$container_id" ]] || die 'could not reserve a container name after 20 attempts'

# Explicit stdin redirection prevents Bash from replacing stdin with /dev/null
# for the background client; traps can forward signals while wait is active.
podman start --attach --interactive "$container_id" <&0 &
client_pid=$!
status=0
wait "$client_pid" || status=$?
exit "$status"
