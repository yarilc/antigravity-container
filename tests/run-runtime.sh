#!/usr/bin/env bash
# Execute credential-free acceptance from native Linux volume storage.
set -Eeuo pipefail
root=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
image=${ANTIGRAVITY_CONTAINER_IMAGE:-localhost/antigravity-cli:latest}
command -v podman >/dev/null || { printf 'Podman is required\n' >&2; exit 1; }
info=$(podman info --format '{{.Host.Security.Rootless}} {{.Host.OS}}')
[[ "$info" == 'true linux' ]] || { printf 'A Linux rootless Podman engine is required\n' >&2; exit 1; }
podman image exists "$image" || { printf 'Build the image first: ANTIGRAVITY_CONTAINER_NETWORK=unrestricted ANTIGRAVITY_CONTAINER_MAINTENANCE=1 ANTIGRAVITY_CONTAINER_IMAGE=%s ./antigravity-container.sh --container-build --version\n' "$image" >&2; exit 1; }
# Mode selection: the default runs the unrestricted runtime suite. The agy
# image is the runner: it provides Python 3.11, Bash, Git, OpenSSL and the
# Podman client.
pattern=test_runtime.py
selection_env=(--env ANTIGRAVITY_RUNTIME_TESTS=1 --env SANDBOX_RUNTIME_TESTS=1)
guard_environment=()
project_mode=ro
shared=(test_reference_copy test_agent_profile test_network_policy test_mux test_tls_client_hello
    test_tls_proxy test_platform test_qualification test_guard test_session test_network_feasibility test_image_pins)
case "${1:-}" in
    --wrapper) pattern=test_wrapper.py ;;
    --shared) pattern='' ;;
    --qualification) pattern=test_qualification.py ;;
    --network-feasibility) pattern=test_network_feasibility.py ;;
    --network) pattern=test_network_runtime.py; project_mode=rw ;;
    --network-policy) pattern=test_network_policy.py ;;
    --mux) pattern=test_mux.py ;;
    --guard|--guard-idle)
        pattern=test_guard.py
        guard_toolchain=$(podman image inspect --format '{{.Id}}' \
            "${SANDBOX_GUARD_TOOLCHAIN:-localhost/antigravity-guard-toolchain:development}")
        guard_environment=(--env SANDBOX_GUARD_TESTS=1 --env "SANDBOX_GUARD_TOOLCHAIN=$guard_toolchain")
        if [[ "$1" == --guard-idle ]]; then
            guard_environment+=(--env SANDBOX_IDLE_TESTS=1)
            set -- "$1" -k test_guarded_multiplex_idle_resume "${@:2}"
        fi
        ;;
    *) set -- '' "$@"; project_mode=rw ;;  # test_runtime.py writes .test-state/
esac
shift
if [[ -n "$pattern" ]]; then
    selection=(discover -s tests -p "$pattern" -v)
else
    selection=(-v "${shared[@]/#/tests.}")
    selection_env=()
fi
socket=${ANTIGRAVITY_CONTAINER_PODMAN_SOCKET:-}
if [[ -z "$socket" && "${CONTAINER_HOST:-}" == unix:///?* ]]; then socket=${CONTAINER_HOST#unix://}; fi
socket=${socket:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock}
response=$(podman --remote --url "unix://$socket" info --format '{{.Host.Security.Rootless}}{{"\n"}}{{.Host.RemoteSocket.Path}}')
[[ "$response" == true$'\n'/* && "$response" != *$'\r'* ]] || { printf 'An accessible rootless Unix service with an absolute host socket path is required\n' >&2; exit 1; }
host_socket=${response#*$'\n'}
[[ "$host_socket" != *$'\n'* && -n "${host_socket//\//}" ]] || exit 1
volume=''
cleanup() {
    status=$?
    [[ -z "$volume" ]] || podman volume rm --force "$volume" >/dev/null || true
    return "$status"
}
trap cleanup EXIT
volume=$(podman volume create)
native_root=$(podman volume inspect --format '{{.Mountpoint}}' "$volume")
podman run --rm --interactive --userns=keep-id --user "$(id -u):$(id -g)" \
    --volume "$root:$root:$project_mode" --volume "$native_root:$native_root:rw" \
    --volume "$host_socket:/run/podman/podman.sock:rw" --workdir "$root" \
    --env CONTAINER_HOST=unix:///run/podman/podman.sock \
    "${selection_env[@]}" --env "ANTIGRAVITY_TEST_STATE_ROOT=$native_root" \
    --env "SANDBOX_TEST_STATE_ROOT=$native_root" "${guard_environment[@]}" \
    --env "ANTIGRAVITY_CONTAINER_IMAGE=$image" --env HOME=/tmp \
    --tmpfs /tmp:rw,exec,nosuid,nodev,mode=1777 \
    --entrypoint python3 "$image" -B -m unittest "${selection[@]}" "$@"
