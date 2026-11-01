# Design

## Context

See `proposal.md` for motivation and the two capability deltas for acceptance behavior. Current shutdown performs synchronous, unbounded `podman kill`, `wait`, and `podman rm`; removal errors are discarded. Creation captures stdout in a command substitution, so a signal can arrive before the parent learns the owned ID. Current signal-during-create tests release a failing client and never exercise a successfully created container.

Codex provides useful patterns: private CID bookkeeping, first-signal status, explicit signal forwarding, five-second grace periods, and timed control commands. Its ordinary wait-for-create loop is not itself a bounded interrupted-create solution and must not be copied unchanged. Claude rejects slash-only launch paths. Both siblings deny build inputs by default, but Antigravity additionally requires two local helper COPY inputs.

## Goals / Non-Goals

**Goals:** Make handled shutdown progress through finite phases; retain reliable ownership across create races; preserve primary status and useful diagnostics; prove build isolation through the actual Podman context implementation.

**Non-Goals:** Time-limit normal builds, prompts, or un-interrupted creation; guarantee remote removal when the service is unavailable; change keyring/D-Bus, provider selection, state, temporary mounts, or delegation semantics; alter the user's existing `.gitignore` edits.

## Decisions

### 1. Record signals and centralize shutdown

Record only the first TERM/INT/HUP and corresponding 143/130/129 status. Signal handlers trigger a single cleanup path rather than performing unbounded control operations themselves. Ignore repeated handled signals once cleanup begins so they cannot restart budgets or replace the first status. Use `--sig-proxy=false` on the attached Podman client to avoid duplicate signal forwarding.

On attached interruption, send the original signal through a bounded engine call. If forwarding succeeds, allow up to five seconds for graceful completion, then attempt `podman rm --force --ignore --time 0` for the owned ID. On normal completion, preserve the application's actual status, including 125, and perform the same bounded removal without a signal grace period. Retain explicit stdin redirection and existing TTY selection.

An engine failure is observable: report forwarding/removal failure and the known owned ID for manual recovery. The EXIT cleanup captures and restores the primary status. Never remove by workspace prefix or colliding name. Silencing failures would retain the current misleading success behavior; replacing application status would break the transparent wrapper contract.

### 2. Assign finite budgets to every shutdown phase

Use coreutils `timeout --kill-after=1s 5s` for each forwarding/removal command, including escalation for a control client ignoring TERM. Use five seconds for application grace, five seconds for interrupted-create completion, and five seconds for local-client TERM grace before KILL. Bound post-KILL observation/reaping to one second and report a client that cannot be reaped; do not call an unconditional wait on a still-live process.

These are per-phase limits, not a five-second total shutdown promise. Track deadlines using elapsed/monotonic time and prevent repeated signals from resetting them. Validate a conservative end-to-end ceiling of 30 seconds in combined failure tests on a normally scheduled host, with tighter checks where fewer phases apply. This covers five seconds of interrupted creation, at most six seconds each for forwarding and removal, five seconds of application grace, and at most six seconds of client termination. Mutually exclusive phases need not all execute.

Check for `timeout` before container creation; wrapper help still exits before prerequisites. Document the host coreutils requirement. Reusing the existing GNU tool avoids adding a Python runtime dependency to the host wrapper. Uninterruptible kernel tasks and a failed host are outside a userspace wall-clock guarantee, and an unavailable engine can leave a residual container even after the wrapper exits promptly.

### 3. Retain ownership independently of stdout

Create a private `0700` session bookkeeping directory with a scoped `077` umask and register cleanup before allocating it. Run `podman create` asynchronously with a private `--cidfile`, stdout/error files, and tracked client PID. Validate a recovered ID as a full hexadecimal Podman ID before adopting it. The CID file, not stdout or the generated name, is authoritative ownership evidence. Keep collision retries and their diagnostics, but distinguish a genuine collision from an engine failure checking container existence.

On a signal during creation, allow the pending create client a finite completion interval. If it completes, adopt any valid CID and remove that owned container without ever attaching. If it stalls, terminate/escalate/reap the local client within deadlines, then re-read the CID file before deciding cleanup ownership. This final read handles CID publication during cancellation. No additional create retry or attach starts once interruption is pending.

Cancelling a remote client cannot prove cancellation of an engine-side request. If no verified ID is recoverable after bounded termination, report uncertain creation and the attempted name for manual inspection; never delete by that name. If an ID exists, attempt bounded removal even when create itself returned failure. Remove bookkeeping only after final ownership handling, retaining existing temporary-diagnostic cleanup guarantees. A name-only fallback was rejected because it could delete an unrelated session.

### 4. Reject slash-only paths lexically

For an explicit Unix launch URL, extract its path, require a leading slash, and require at least one non-slash character before any Podman call. Do not normalize an all-slash path into a valid endpoint. Keep existing transport, complete-response, and remote-service checks. This matches Claude's intent and fixes the current glob accepting `unix:////` without changing valid absolute path handling.

### 5. Deny build inputs by default

Replace `.containerignore` with a deny-all rule and explicit root-only exceptions for the four files in the runtime-image delta. Preserve both helper COPY instructions and image package/install logic. Including `.containerignore` makes the context inventory explicit and follows Claude's convention; excluding it would also be possible but is not the selected contract.

Validate actual Podman matching rather than simulating ignore semantics in Python. In a synthetic context, copy the real ignore file and both helpers, use an existing local image as base, and create only dummy sensitive/unknown/nested sentinels. A small fixture recipe exercises both production helper COPY destinations and `COPY .` into an inventory directory. Assert exact inventory, helper content and executable installation, including exclusion of same-named nested files. Clean up fixture images and contexts. No full release download or paid model request is needed for this test.

## Risks / Trade-offs

- Additional lifecycle states and create/signal races -> synchronize fake-engine tests with readiness markers, test CID publication both before and after interruption, and verify first-signal precedence.
- Timed-out service calls may leave residual resources -> report known IDs or unresolved creation explicitly and never broaden deletion authority.
- New timeout prerequisite affects minimal hosts -> check before creation and document installation through coreutils; retain tool-free wrapper help.
- Ignore syntax may differ from assumptions -> require a real rootless Podman context inventory test, including nested allowed-name sentinels and both helper copies.
- Longer shutdown tests can become flaky -> use generous outer deadlines without replacing real internal timeout behavior with shortened mock budgets.

## Migration Plan

1. Land each behavior with its tests and affected help/README updates. Preserve existing argument/stdin/TTY, permission, state, temporary-mount, keyring, and image checks.
2. Run wrapper regressions, Bash syntax, ShellCheck, OpenSpec strict validation, and the expanded rootless runtime suite with native private state. Record observed versions/results and any blocked environment checks in `docs/validation.md`.
3. Users need coreutils `timeout`; no environment opt-in or state migration is introduced. Future local image dependencies require allowlist edits.
4. Rollback restores the previous wrapper and ignore policy without state conversion. Restoring the old ignore policy reintroduces permissive build inputs; document that trade-off in review.
