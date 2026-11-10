#!/usr/bin/env bash
set -Eeuo pipefail

# Help and version must work without a terminal or credentials.
case "${1:-}" in
    --help|-h|--version|help) exec agy "$@" ;;
esac

# There is no D-Bus session or keyring in the container, so agy keeps account
# tokens in files in the private state home. Google documents the URL/code flow
# for remote sessions; this marker is scoped to the agy process and requests
# that flow without mounting an SSH agent or client.
unset DBUS_SESSION_BUS_ADDRESS DBUS_SESSION_BUS_PID GNOME_KEYRING_CONTROL
export SSH_CONNECTION="${SSH_CONNECTION:-127.0.0.1 0 127.0.0.1 0}"
exec agy "$@"
