#!/usr/bin/env bash
set -Eeuo pipefail

# Help and version must work without a terminal or credentials.
case "${1:-}" in
    --help|-h|--version|help) exec agy "$@" ;;
esac
next_is_value=0
for arg in "$@"; do
    if ((next_is_value)); then
        next_is_value=0
        continue
    fi
    case "$arg" in
        --help|-h|--version) exec agy "$@" ;;
        --add-dir|--agent|--conversation|--effort|-i|--prompt-interactive|\
        --input-format|--json-schema|--log-file|--mode|--model|--output-format|\
        -p|--print|--prompt|--print-timeout|--project|--settings)
            next_is_value=1 ;;
    esac
done

settings="$HOME/.gemini/antigravity-cli/settings.json"
provider=''
if [[ -f "$settings" ]]; then
    provider=$(jq -r '.modelProvider // ""' "$settings" 2>/dev/null) || true
fi
# Session-only settings take precedence over persisted provider selection.
pending_settings=0
for arg in "$@"; do
    if ((pending_settings)); then
        if [[ -f "$arg" ]]; then
            session_provider=$(jq -r '.modelProvider // empty' "$arg" 2>/dev/null) || true
        else
            session_provider=$(jq -nr --argjson settings "$arg" '$settings.modelProvider // empty' 2>/dev/null) || true
        fi
        [[ -z "${session_provider:-}" ]] || provider=$session_provider
        pending_settings=0
    elif [[ "$arg" == --settings ]]; then
        pending_settings=1
    elif [[ "$arg" == --settings=* ]]; then
        value=${arg#--settings=}
        if [[ -f "$value" ]]; then
            session_provider=$(jq -r '.modelProvider // empty' "$value" 2>/dev/null) || true
        else
            session_provider=$(jq -nr --argjson settings "$value" '$settings.modelProvider // empty' 2>/dev/null) || true
        fi
        [[ -z "${session_provider:-}" ]] || provider=$session_provider
    fi
done
if [[ "$provider" == gemini ]]; then
    # Let agy report missing or invalid keys; do not hide native diagnostics.
    exec agy "$@"
fi

exec /usr/local/lib/antigravity/keyring-session.sh agy "$@"
