#!/usr/bin/env bash
set -Eeuo pipefail

die() { printf 'antigravity-container: %s\n' "$*" >&2; exit 1; }
umask 077
XDG_RUNTIME_DIR="/tmp/antigravity-runtime-$(id -u)"
export XDG_RUNTIME_DIR
mkdir -p -- "$XDG_RUNTIME_DIR" "$HOME/.local/share/keyrings"
chmod 700 -- "$XDG_RUNTIME_DIR"

# Independent daemons cache the collection and must not rewrite the same files
# concurrently. Keep the lock across the private bus and the application.
if [[ "${1:-}" != --inside-private-bus ]]; then
    exec 9>"$HOME/.local/share/keyrings/.container-session.lock"
    flock --nonblock 9 || die 'this account state is already in use; choose a separate ANTIGRAVITY_CONTAINER_STATE_DIR for another account session'
fi

# The bus is private to this container session. Never connect to a host bus.
if [[ "${1:-}" != --inside-private-bus ]]; then
    unset DBUS_SESSION_BUS_ADDRESS DBUS_SESSION_BUS_PID GNOME_KEYRING_CONTROL
    exec dbus-run-session -- "$0" --inside-private-bus "$@"
fi
shift

[[ -r /dev/tty && -w /dev/tty ]] || die 'account login requires a terminal to unlock the keyring; use an interactive login or configure the gemini API key provider for headless runs'
exec 3<>/dev/tty || die 'cannot open the terminal; use an interactive login or the gemini API key provider'
printf 'Keyring passphrase: ' >&3
IFS= read -r -s keyring_passphrase <&3 || die 'could not read keyring passphrase'
printf '\n' >&3
[[ -n "$keyring_passphrase" ]] || die 'an empty keyring passphrase is not supported'
if [[ ! -f "$HOME/.local/share/keyrings/login.keyring" ]]; then
    printf 'Confirm new keyring passphrase: ' >&3
    IFS= read -r -s keyring_confirmation <&3 || die 'could not read keyring confirmation'
    printf '\n' >&3
    [[ "$keyring_passphrase" == "$keyring_confirmation" ]] || die 'keyring passphrases do not match'
    unset keyring_confirmation
fi
exec 3>&-

# Shell builtins keep the passphrase out of the environment and process argv.
printf '%s' "$keyring_passphrase" | gnome-keyring-daemon \
    --unlock --components=secrets \
    --control-directory "$XDG_RUNTIME_DIR/keyring" >/dev/null
unset keyring_passphrase

# --unlock can return success even for an incorrect password. Query the
# collection instead of trusting the daemon's exit code or starting a GUI prompt.
locked=$(dbus-send --session --print-reply --dest=org.freedesktop.secrets \
    /org/freedesktop/secrets/collection/login \
    org.freedesktop.DBus.Properties.Get \
    string:org.freedesktop.Secret.Collection string:Locked) || die 'cannot query the dedicated keyring'
[[ "$locked" == *'boolean false'* ]] || die 'keyring is locked; check the passphrase and try again'

# Google documents the URL/code flow for remote sessions. This marker is scoped
# to the agy process and requests that flow without mounting an SSH agent/client.
if [[ "${1:-}" == agy ]]; then
    export SSH_CONNECTION="${SSH_CONNECTION:-127.0.0.1 0 127.0.0.1 0}"
fi
exec "$@"
