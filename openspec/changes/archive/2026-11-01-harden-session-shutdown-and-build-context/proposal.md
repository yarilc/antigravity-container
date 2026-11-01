# Proposal

## Why

The remaining items in `todo.md` expose three gaps: shutdown can hang indefinitely, slash-only Unix endpoints pass launch validation, and unknown local files enter the image build context. Close these gaps in one change while preserving Antigravity's authentication and runtime isolation policies.

## What Changes

- Bound session shutdown in CLI and shell modes: forward TERM/INT/HUP once, allow five seconds for graceful application exit, then force removal of only the owned container. Bound shutdown engine calls and client termination; report failures without replacing application or signal exit status.
- Retain container ownership evidence across interruption during creation, so a container created as the signal arrives is never attached and can be removed safely. An interrupted, stalled create client must not make shutdown wait indefinitely.
- Reject Unix launch endpoints whose path contains only slashes, including `unix:///`, `unix:////`, and longer equivalents, before contacting Podman. Continue accepting absolute socket paths containing a non-slash component.
- Replace `.containerignore` exclusions with a default-deny allowlist: root `Containerfile`, `container-entrypoint.sh`, `keyring-session.sh`, and `.containerignore`. Unknown files, private local settings, credentials, and nested directories remain excluded without updating the list.
- Add wrapper regressions and real rootless runtime/build-context checks, and update affected help, README, and validation records.

## Capabilities

### New Capabilities

None; extend existing capabilities.

### Modified Capabilities

- `container-launcher`: bounded shutdown, ownership tracking across interrupted creation, cleanup failure reporting, preservation of primary exit status, and rejection of slash-only Unix launch endpoints.
- `runtime-image`: explicit minimal build-context inputs, with both required authentication/runtime helper copies retained.

## Impact

Implementation affects `antigravity-container.sh`, `.containerignore`, `tests/test_wrapper.py`, `tests/test_runtime.py`, README, and validation evidence. GNU coreutils `timeout` becomes a checked host prerequisite for session lifecycle management; the image already includes coreutils. No new third-party dependency or image package is needed.

Existing application exits, including `125`, remain application results. Handled signals return `143`, `130`, and `129`; cleanup errors become visible diagnostics. Previously accepted slash-only launch endpoints now fail earlier. Future local image inputs must be deliberately added to the build allowlist.

Preserve private keyring/D-Bus behavior, OAuth/API-provider selection, state layout, exact Podman opt-in, workspace/worktree mounts, and the current executable `/tmp` and restricted `/run` and `/var/tmp` policies. This change does not add timeouts to ordinary builds or model sessions, repair unrelated `.gitignore` edits, or promise removal when the engine is unavailable. No implementation or new runtime verification is performed during proposal creation.
