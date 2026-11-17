# Antigravity agent part for the shared launcher core (launcher/core.sh). It
# mirrors agent/profile.json and agent/policies/default.json;
# tests/test_alignment.py compares them. See docs/launcher-contract.md in
# sandbox-container.
AGENT_NAME=antigravity-container
AGENT_DISPLAY_NAME=Antigravity
AGENT_WRAPPER=antigravity-container.sh
AGENT_ENV_PREFIX=ANTIGRAVITY_CONTAINER
AGENT_LABEL_NAMESPACE=io.antigravity-container
AGENT_IMAGE=localhost/antigravity-cli
AGENT_PROXY_IMAGE=localhost/antigravity-egress
AGENT_HOME=/antigravity-home
AGENT_COMMAND=agy
# Restricted sessions run the image's entrypoint script through the guard; it
# requests agy's remote sign-in flow and clears the D-Bus and keyring variables.
AGENT_EXEC=/usr/local/bin/antigravity-entrypoint
AGENT_CONFIG_DIR_ENV=ANTIGRAVITY_CONTAINER_CONFIG_DIR
AGENT_CONFIG_HOME=.gemini
AGENT_SHARED_DIRS=()
AGENT_PRIVATE_SHARED_DIRS=0
AGENT_APPROVAL_BYPASS_ENV=ANTIGRAVITY_YOLO
# agy's native runtime components run from /tmp and the home (contract U7).
AGENT_EXEC_TMP=1
AGENT_INSTALL_FILES=(container-entrypoint.sh)
AGENT_CREDENTIALS=(gemini-api=GEMINI_API_KEY google-account=)
AGENT_POLICY_HOSTS=("gemini-api=generativelanguage.googleapis.com" "google-account=oauth2.googleapis.com cloudcode-pa.googleapis.com daily-cloudcode-pa.googleapis.com www.googleapis.com aicode.googleapis.com www.gstatic.com play.googleapis.com")
# Fixed settings follow toolchain and forwarded variables, so they win.
AGENT_SESSION_ENV=(AGY_CLI_DISABLE_AUTO_UPDATE=true)
AGENT_RESTRICTED_ENV=()
AGENT_PROVIDER_ENV=()
# No D-Bus session or keyring: agy keeps account tokens in its state files.
AGENT_UNSET_ENV=(DBUS_SESSION_BUS_ADDRESS)
# The fixed setting is never forwarded from the host either.
AGENT_RESERVED_ENV=(AGY_CLI_DISABLE_AUTO_UPDATE)

agent_help() {
    printf '  ANTIGRAVITY_YOLO        enable agy --dangerously-skip-permissions: 1, true or\n'
    printf '                          yes (case-insensitive; default: disabled; never\n'
    printf '                          applied in shell mode)\n'
    printf '  GEMINI_API_KEY          forwarded by name only to provider sessions using\n'
    printf '                          gemini-api, or to unrestricted sessions when\n'
    printf '                          ANTIGRAVITY_CONTAINER_ENV_VARS lists it; requires\n'
    printf '                          modelProvider: gemini\n'
    printf '\nThere is no D-Bus session or keyring in the container: agy keeps account\n'
    printf 'tokens in files in its state directory, protected by Unix permissions only.\n'
    printf 'Sign-in uses the remote URL and code flow with a host browser.\n'
}

agent_approval_bypass() {
    agent_bypass_args=(--dangerously-skip-permissions)
}
