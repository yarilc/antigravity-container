# Proposal

## Why

The nine gaps identified in `todo.md` allow incomplete engine responses, implicit Podman connection settings, and invalid private state to pass too far through startup. Harden the existing launcher contract so invalid inputs fail before image operations, writable temporary storage is explicit, and launch diagnostics are cleaned up reliably.

## What Changes

1. Validate the entire launch-engine response: exactly one record containing rootless `true`, OS `linux`, and a `ServiceIsRemote` value of `true` or `false`. Reject missing or extra fields and additional records before image inspection or build, retaining the existing transport restrictions.
2. Reject `CONTAINER_HOST=unix:///` before querying Podman; a Unix launch endpoint must identify a nonempty absolute socket path rather than `/`.
3. **BREAKING**: enable socket delegation only when `ANTIGRAVITY_CONTAINER_PODMAN` is exactly `1`; unset, empty, and every other value disable delegation without an error, in both CLI and shell modes. Document migration from `true`/`yes`; keep the existing YOLO boolean contract independent.
4. Require an absolute selected delegation socket path before canonicalization, retain socket accessibility checks, and validate the complete service response as one rootless result plus an absolute host socket path. Preserve service-side bind-source resolution for wrappers running inside containers.
5. Explicitly unset `CONTAINER_HOST` in the created container when delegation is disabled, including values supplied by image or engine defaults. This must not clear the wrapper's own launch-engine connection.
6. Create, resolve, and validate private state ownership, accessibility, and permissions before image inspection or build, including `--container-build`. Keep wrapper help free of state and engine side effects.
7. Disable automatic read-only tmpfs provisioning with `--read-only-tmpfs=false` and explicitly provide required temporary paths, including `/var/tmp`. Preserve executable `/tmp`, its 512 MiB limit, `/run` with `noexec` and its 32 MiB limit, and the private keyring runtime directory.
8. Limit the wrapper's `umask 077` to state directory creation. Verify actual container file modes separately across shell, API-provider, and account paths; preserve the keyring helper's private runtime behavior.
9. Remove the temporary create-error file through EXIT cleanup, including interruption and unexpected failure, while preserving diagnostics, exit status, and cleanup limited to the session's own container.

Cover each behavior with regression tests and update affected help, README, OpenSpec contracts, and validation evidence. Runtime checks must exercise temporary mount properties, environment clearing, and file permissions rather than infer them from wrapper arguments alone.

## Capabilities

### New Capabilities

None; extend existing capabilities.

### Modified Capabilities

- `container-launcher`: complete launch-engine validation, Unix endpoint preconditions, private-state checks before image operations, and temporary diagnostic cleanup throughout the lifecycle.
- `agent-permissions`: exact socket opt-in, strict delegation endpoint validation, and explicit removal of disabled service connection settings.
- `workspace-mounts`: private state creation and validation, scoped creation permissions, and explicit ephemeral mount provisioning.

## Impact

Implementation will primarily affect `antigravity-container.sh`, `tests/test_wrapper.py`, `tests/test_runtime.py`, and the corresponding documentation and specification deltas. Review direct Podman invocations in runtime fixtures so keyring tests exercise the explicit mount policy. No new dependency or image toolchain change is proposed.

The state directory may now be created even when a later image operation fails; an existing wrapper test currently expects otherwise and must change. Strict validation intentionally rejects malformed responses previously accepted. Automated regression and real rootless Podman checks are required during implementation; this proposal records no new runtime verification.

### Planning decisions

- **Confirmed delegation semantics:** match `CODEX_CONTAINER_PODMAN` and `CLAUDE_CONTAINER_PODMAN`: all values other than exactly `1` disable delegation silently and skip delegation socket validation. YOLO retains its existing boolean interpretation.
- **`/var/tmp` policy:** use a separate ephemeral tmpfs with `nosuid,nodev,noexec` and a 512 MiB limit, with mode `1777`. This design choice preserves executable temporary storage in `/tmp` and requires runtime compatibility checks.

Scope excludes changes to Google authentication, YOLO semantics, the image toolchain, and worktree selection, plus workarounds for the recorded internal sandbox incompatibility. The proposal is grounded in the local TODO, source, tests, existing specifications, and the now-accessible sibling Codex and Claude wrappers and their delegation tests.
