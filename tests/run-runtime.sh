#!/usr/bin/env bash
# Run checks in a disposable container with private state on native Linux storage.
set -Eeuo pipefail
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
image=${ANTIGRAVITY_CONTAINER_IMAGE:-localhost/antigravity-cli:latest}
socket=$(podman info --format '{{.Host.RemoteSocket.Path}}')
volume=$(podman volume create)
cleanup() { podman volume rm --force "$volume" >/dev/null; }
trap cleanup EXIT
native_state=$(podman volume inspect --format '{{.Mountpoint}}' "$volume")
podman run --rm --interactive --userns=keep-id --user "$(id -u):$(id -g)" \
    --volume "$project_root:$project_root:rw" \
    --volume "$native_state:$native_state:rw" \
    --volume "$socket:/run/podman/podman.sock:rw" \
    --workdir "$project_root" \
    --env CONTAINER_HOST=unix:///run/podman/podman.sock \
    --env ANTIGRAVITY_RUNTIME_TESTS=1 \
    --env "ANTIGRAVITY_CONTAINER_IMAGE=$image" \
    --env "ANTIGRAVITY_TEST_STATE_ROOT=$native_state" \
    --entrypoint python3 "$image" \
    -m unittest discover -s tests -p test_runtime.py -v "$@"
