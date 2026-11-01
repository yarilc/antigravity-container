# Design

## Context

See `proposal.md` for motivation and the three capability deltas for acceptance scenarios. The wrapper currently parses only the first engine response line, treats delegation as a general boolean, performs image operations before state checks, leaves a global `077` umask active, and depends partly on automatic tmpfs provisioning. Its EXIT handler removes its container but does not track `create_error`.

The sibling wrappers and tests confirm that every delegation value other than exactly `1` disables access without error. Their mount policies differ: Antigravity must retain executable temporary storage for native components and its private keyring runtime under `/tmp`. `keyring-session.sh` independently applies `077` inside account sessions; shell and API-provider paths do not pass through it.

## Goals / Non-Goals

**Goals:** Establish a visible preflight boundary before image operations, preserve the distinction between launch and delegated engines, and make temporary mount and file-permission behavior independently testable.

**Non-Goals:** Introduce a shared library across sibling projects, change account-helper permission policy, impose a new container-wide umask, or add automatic permission repair. Image provisioning and authentication remain as described in the proposal.

## Decisions

### 1. Order preflight before image work

Use the following order, retaining the help short circuit:

```text
parse options / wrapper help
          |
validate YOLO and exact delegation selection
          |
validate launch transport and engine response
          |
validate delegation endpoint if enabled
          |
create / resolve / validate private state
          |
inspect or build image
          |
reserve container / attach / cleanup
```

Keeping engine and delegation checks before state creation avoids creating state for an invalid engine. Moving state checks ahead of both image paths avoids a costly build followed by predictable state rejection. The alternative of checking only at container creation violates the desired failure ordering. State can remain after a subsequent image failure; document this and update the existing test that expects absence.

### 2. Validate complete responses, preserving path content

For launch info, validate exactly one record and exactly the three expected tokens before using any values; explicitly validate the remote boolean. A normal terminating newline is allowed, but additional records, including blank records, are rejected. Do not rely on `read` accepting an incomplete first line. Capture output in a way that preserves record boundaries through validation: command substitution strips trailing newlines, so use a sentinel capture or equivalent technique and preserve the query exit status.

For delegation, validate a single rootless marker and the absolute path remainder without splitting the path on spaces. Reject missing paths and extra records, while preserving whitespace inside legitimate absolute paths. Do not impose the launch response's three-token grammar on this response. A plain first-line `read` is inadequate; JSON would add parsing complexity unnecessary for these existing formats.

Reject `unix:///` and nonabsolute Unix launch paths before any query. Reject relative delegation paths before `readlink -f`, even if they would canonicalize successfully. Keep precedence override, launch Unix socket, then XDG/UID default; use the canonical accessible endpoint for verification and the reported host path for the mount. The latter may be unavailable in the wrapper's own namespace, so do not require local existence of that reported path.

### 3. Separate exact delegation from YOLO parsing

Use a literal equality check against `1`; do not call the general boolean parser for delegation. Disabled delegation skips all delegation checks and adds `--unsetenv CONTAINER_HOST` to the created container. Enabled delegation supplies the socket mount and in-container URL. Preserve the wrapper's own environment for image/create/start operations. Rejecting `true`, `yes`, or arbitrary values was considered and rejected because it differs from both reference projects and the confirmed user decision.

### 4. Scope state umask without changing runtime permissions

Create missing state in a subshell using `umask 077`, then resolve and validate the resulting directory in the parent shell. Keep caller ownership, read/write/search access, and absence of group/other permissions as preconditions. Fail clearly on non-native filesystems rather than applying recursive chmod. A subshell naturally restores the inherited wrapper umask; manually saving and restoring it creates additional failure paths.

Leave the account helper's existing `077` behavior intact. Verify wrapper umask isolation with the fake engine observing its inherited mask. Separately verify controlled file creation inside actual shell, API-entrypoint, and account-helper paths. Use a harmless test `agy` probe for API-entrypoint permission checks, with provider settings selecting `gemini`, rather than a paid model request. Compare observed file modes to the actual process umask; account probes must additionally demonstrate private modes. Host state creation alone proves none of these runtime properties.

### 5. Declare temporary mounts explicitly

Add `--read-only-tmpfs=false`. Set `/tmp` to `rw,exec,nosuid,nodev,mode=1777,size=512m`, `/run` to `rw,nosuid,nodev,noexec,mode=1777,size=32m`, and `/var/tmp` to `rw,nosuid,nodev,noexec,mode=1777,size=512m`. Keep the keyring runtime under `/tmp` with mode `0700`.

A separate `/var/tmp` mount provides ephemeral writable storage without relying on engine defaults. Its `noexec` and 512 MiB limit are design defaults; executable temporary storage remains available in `/tmp`. Reusing Codex's full mount policy would weaken Antigravity's existing `/run` restriction. Retaining automatic mounts would leave the writable layout dependent on engine behavior.

Update the direct keyring runtime fixture to use these same flags, so it does not validate a more permissive layout than the wrapper. Inspect actual mount options, limits, execution, writability, and cross-session disappearance with real rootless Podman.

### 6. Give EXIT cleanup ownership of diagnostic files

Initialize `create_error` before installing traps; create it only after cleanup is registered. Cleanup conditionally removes the tracked file and owned container without changing the original exit status. Retain prompt removal after normal creation, clearing the tracking variable after removal. Preserve create-error output before cleanup and never treat an application exit of 125 as a naming collision.

Test normal exit, creation failure, retry exhaustion, an unexpected command failure, and handled interruption after allocation using a dedicated temporary diagnostic directory and synchronized fake-engine events. Waiting for a marker avoids timing-dependent sleeps. EXIT cleanup cannot guarantee removal after SIGKILL or host failure; the contract explicitly covers exits for which cleanup can run.

## Risks / Trade-offs

- Stricter output parsing can expose unusual engine output → test supported output and diagnostics separately, preserve paths with spaces, and record tested engine versions.
- Disabling automatic tmpfs mounts can expose hidden runtime dependencies → run image smoke and keyring persistence/unlock tests with the explicit layout before acceptance.
- `true` and `yes` silently disable delegation → document exact-value migration prominently in help and README and test both CLI and shell modes.
- Host and container file permissions can differ → measure each execution path and retain native Linux state storage in runtime tests.
- Additional tmpfs limits increase the permitted temporary footprint → document the separate limits; tmpfs capacity is not a preallocation guarantee.

## Migration Plan

1. Implement and run the wrapper regression suite, preserving forwarding, TTY/stdin, naming, exit-code, and signal behavior.
2. Validate the explicit mounts, default environment removal, file modes, keyring lifecycle, and delegated child-container binds with real rootless Podman. Use only dummy credentials and no model requests.
3. Update help, README, and `docs/validation.md` with migration guidance and observed results or explicit environment limitations. Keep main specifications unchanged until the normal sync/archive workflow.
4. Users currently setting delegation to `true` or `yes` switch to `1`. Existing state needs no format migration; insecure directories require manual correction or selection of native storage.
5. Roll back by restoring the prior wrapper and documentation; state remains compatible. Restore old delegation values only when intentionally reverting the exact-value contract.
