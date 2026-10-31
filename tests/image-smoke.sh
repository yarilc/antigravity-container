#!/usr/bin/env bash
# Run inside the built image as a non-root user with a read-only root.
set -Eeuo pipefail
[[ $(id -u) != 0 ]]
for tool in agy openspec bash git python3 bwrap podman rg nano curl jq \
    dbus-run-session gnome-keyring-daemon secret-tool tar gzip bzip2 zip unzip \
    file ps find patch diff awk xz sed grep less sha512sum; do
    command -v "$tool" >/dev/null
done
agy --version
agy --help >/dev/null
openspec --version
file /usr/local/bin/agy
linking=$(ldd /usr/local/bin/agy 2>&1) || {
    [[ "$linking" == *'not a dynamic executable'* || "$linking" == *'statically linked'* ]]
}
[[ "$linking" != *'not found'* ]]
printf '%s\n' "$linking"
getconf GNU_LIBC_VERSION
[[ "$AGY_CLI_DISABLE_AUTO_UPDATE" == true ]]
[[ -w "$HOME" && -w /tmp && ! -w /usr ]]
findmnt --noheadings --output OPTIONS --target / | grep -Eq '(^|,)ro(,|$)'
touch /tmp/antigravity-image-smoke
printf 'Image smoke checks passed.\n'
