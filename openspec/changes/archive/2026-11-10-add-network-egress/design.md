# Design

## Context

See `proposal.md`. The reference is `claude-container` at tag `sandbox-ref-8` (commit `12cffab`). Since `sandbox-ref-5` it added three things:
- the optional profile field `install.files` (`sandbox-ref-6`);
- the optional `install.runtime_build` (`sandbox-ref-7`);
- a shared setup-test fix (`sandbox-ref-8`).

Codex, OpenCode and Pi completed both Wave 3 changes on it. Their archived changes are the templates. The Codex port is the closest for authentication, because it has an account profile with file tokens; the Pi port is the closest for the wrapper shape.

**Current Antigravity wrapper.** `antigravity-container.sh` (414 lines) already has the hardened baseline:
- no capabilities and no-new-privileges;
- validated and verified budgets;
- the workspace guard and the optional lifetime;
- atomic naming, bounded owned cleanup and strict engine verification.

It has no network modes and no `--init`. It mounts one dedicated home (`ANTIGRAVITY_CONTAINER_STATE_DIR`, default `~/.local/share/antigravity-container/home`) at `/antigravity-home`, and never the host `~/.gemini`. It forwards only `GEMINI_API_KEY`. It builds a missing image automatically, and `--container-build` rebuilds with `--no-cache`. `ANTIGRAVITY_YOLO` adds `--dangerously-skip-permissions`.

**Entrypoint and keyring.** `container-entrypoint.sh` execs `agy` directly for help, version and `modelProvider: gemini` (read from `settings.json` or session `--settings`). Otherwise it runs `keyring-session.sh`, which:
- takes an exclusive lock on the keyring directory;
- starts `dbus-run-session`;
- reads a passphrase from `/dev/tty` and unlocks `gnome-keyring-daemon`;
- checks the collection over D-Bus;
- sets the `SSH_CONNECTION` marker that requests the remote URL/code sign-in;
- execs `agy`.

Its runtime directory is `/tmp/antigravity-runtime-<uid>`.

**Runtime image.** The base is `node:22-bookworm-slim` pinned by digest. The image installs `agy` 1.5.3 from the official artifact verified by SHA-512, OpenSpec 1.16.0, `python3`, `ca-certificates`, `bubblewrap`, `podman`, the keyring packages and the common toolset. The default name is `localhost/antigravity-cli:latest`.

**Static inventory of `agy` 1.5.3** (strings in the binary; to be confirmed by measurement):
- **Keyring:** `zalando/go-keyring` with a `fileTokenStorage` and a composite storage. The embedded changelog for 1.1.3 says the CLI "bypasses the keyring when no D-Bus session bus is present (headless hosts and containers)".
- **Proxy and TLS:** the Go client references `HTTPS_PROXY`/`https_proxy`, `SSL_CERT_FILE`, `SSL_CERT_DIR`, `AGY_CA_CERT` and `AGY_PROXY_STRICT_SSL`.
- **Google hosts:**
  - OAuth: `accounts.google.com` (browser), `oauth2.googleapis.com`;
  - model service: `cloudcode-pa.googleapis.com`, with `daily-` and sandbox variants;
  - API key: `generativelanguage.googleapis.com`;
  - also `www.googleapis.com`, `iamcredentials.googleapis.com`, `sts.googleapis.com`, `aiplatform.googleapis.com` and the auto-updater at `antigravity-cli-auto-updater-…run.app`.
- **Controls:** `AGY_CLI_DISABLE_AUTO_UPDATE`, and telemetry settings (`disableTelemetry`, `isTelemetryDisabledPersisted`).
- **Internal channels:** a language server and sidecar addressed by `ANTIGRAVITY_LS_ADDRESS` and `ANTIGRAVITY_SIDECAR_WEB_PORT`, which are expected to be loopback TCP.

**Tests.**
- `tests/test_wrapper.py` (49 tests) embeds its fake engine.
- `tests/run-runtime.sh` runs `tests/test_runtime.py` inside the `agy` image (Python 3.11, Podman client).
- There are also `tests/image-smoke.sh` and `tests/test_image_pins.py`.
- There is no CI workflow.

## Goals / Non-Goals

**Goals:**
- `network/` and `setup/diagnostics.py` byte-identical to `sandbox-ref-8`. Antigravity differences stay in `agent/`, the wrapper, the entrypoint, the image files and the per-agent tests.
- Restricted Antigravity sessions behave like those of the other four wrappers. `unrestricted` keeps today's networking and key forwarding.
- Account sign-in works in every mode without D-Bus, a keyring or a Unix-socket exception.
- The Antigravity-specific risks are measured before the wrapper integration.

**Non-Goals:**
- Setup, the managed launcher and the parity row (all in `add-container-setup`).
- Changes to shared files. A defect is fixed in Claude first.
- Vertex AI, enterprise endpoints, ADC and other providers.
- A CI workflow: Antigravity has none today. Adding one is a separate change.
- Authenticated checks in automated tests. The operator runs them after all Waves.

## Decisions

### Copy the reference tree from `sandbox-ref-8`

`git -C ../claude-container archive sandbox-ref-8 network setup/diagnostics.py <shared tests>`, without `test_alignment.py` and `test_setup.py`, which come with `add-container-setup`. The agent-neutral `tests/test_reference_copy.py` of Pi's `add-network-egress` is reused, with the manifest moved to `sandbox-ref-8`.

### Antigravity agent profile

| Field | Value |
| --- | --- |
| `name` / `wrapper` | `antigravity-container` / `antigravity-container.sh` |
| `env_prefix` / `label_namespace` | `ANTIGRAVITY_CONTAINER` / `io.antigravity-container` |
| `identifiers` | `antigravity`, `agy`, `gemini` (checked against the shared files in task 1.2) |
| `images` | `localhost/antigravity-cli`, `localhost/antigravity-egress`, `localhost/antigravity-guard-toolchain` |
| `install.state_name` | `antigravity-egress` |
| `install.files` | `container-entrypoint.sh` (bound by qualification and installed by setup) |
| `install.runtime_build` | not declared (`recipe`): the Containerfile has no wrapper-computed build arguments |
| `native.home` / `command` | `/antigravity-home` / `agy` |
| `native.config_home` / `shared_dirs` | `.gemini` / none |
| `native.config_dir_env` | `ANTIGRAVITY_CONTAINER_CONFIG_DIR` (new) |
| `native.approval_bypass_env` | `ANTIGRAVITY_YOLO` (existing) |

Authentication methods:

| Method | Policy profile | Credential | Hosts |
| --- | --- | --- | --- |
| `account` | `google-account` | file tokens in the state home | measured in task 2.1 |
| `gemini` | `gemini-api` | `GEMINI_API_KEY` | `generativelanguage.googleapis.com` |

`account` gets `login_args` only if `agy` 1.5.3 has a non-interactive sign-in command. Otherwise sign-in happens on the first interactive launch, as today.

### Account tokens in files, keyring removed (operator decision of 2026-11-10)

The guard denies new Unix sockets and listeners. `dbus-run-session`, `gnome-keyring-daemon` and the go-keyring client all need them, so the keyring cannot work under the guard. `agy` falls back to file token storage when `DBUS_SESSION_BUS_ADDRESS` is absent. The operator chose that storage in every mode, for one consistent token location:
- `keyring-session.sh` and the keyring packages are removed.
- The entrypoint no longer reads `modelProvider`. It keeps the help and version shortcut, sets the scoped `SSH_CONNECTION` marker for `agy`, and execs `agy`.
- The wrapper unsets `DBUS_SESSION_BUS_ADDRESS` in every session.
- The keyring lock is dropped. Concurrent sessions sharing one state behave like Claude and Codex with a shared configuration. Task 2.2 measures concurrent token refresh; a corrupting race is a finding for the operator, not a reason to keep D-Bus.
- Old keyring files (`~/.local/share/keyrings` in the state home) are left untouched. The README tells users how to remove them after signing in again.

Rejected alternatives:
- **A Unix-socket exception in the guard for the bus.** It weakens the shared guard.
- **Keyring only in unrestricted mode.** A sign-in would then not carry across modes.
- **Account only in unrestricted mode.** Restricted modes would lose the main sign-in method.

Task 2.2 confirms the fallback before any wrapper change. It checks where the token files go, that they are mode `0600` inside the private state, that they persist and refresh, and that `/logout` removes them. If `agy` refuses to work without a bus, the port stops and goes back to the operator.

### State model (operator decision of 2026-11-10)

The shared setup and qualification offer shared state (`~/<config_home>`, or `config_dir_env`) and isolated state (the state directory mounted as the whole home).

| `ANTIGRAVITY_CONTAINER_STATE_DIR` | Mount |
| --- | --- |
| unset | today's dedicated home `~/.local/share/antigravity-container/home`, as an isolated home |
| nonempty | that isolated home |
| empty | shared state: the host `~/.gemini` (or `ANTIGRAVITY_CONTAINER_CONFIG_DIR`) at `/antigravity-home/.gemini`, below a tmpfs home |

The shared case:
- follows the Pi and OpenCode lessons: lexical checks before the engine, and creation and validation after it;
- accepts `ANTIGRAVITY_CONTAINER_CONFIG_DIR` only with shared state; with the dedicated or an isolated home it fails before the engine;
- sets `ANTIGRAVITY_CONTAINER_CONFIG_DIR=/antigravity-home/.gemini` in every session, which the shared smoke check verifies;
- comes with a README warning that Gemini CLI also keeps files under `~/.gemini`.

The default stays the dedicated home, so existing users see no state change.

### Check order

The reference order applies:
1. arguments;
2. mode and delegation;
3. budgets and lifetime;
4. lexical state checks;
5. engine;
6. restricted platform queries;
7. state creation and validation;
8. CA;
9. `session.py prepare`;
10. image operations under maintenance;
11. the immutable image ID;
12. `qualify.py check`;
13. `session.py start` and `agent-args`;
14. owned create and start;
15. `session.py stop`.

The existing lifecycle code stays. Restricted sessions replace the image entrypoint with the guard, which then runs `/usr/local/bin/antigravity-entrypoint`. Shell mode runs `/bin/bash` under the guard.

### Maintenance

Every `podman build` requires `ANTIGRAVITY_CONTAINER_MAINTENANCE=1`, both the automatic build and `--container-build`, which keeps `--no-cache`. There is no staleness label today and none is added: the image identity bound by qualification already detects a changed image in restricted modes.

### Credentials and forwarding

| Mode | `GEMINI_API_KEY` | Proxy and CA variables | `DBUS_SESSION_BUS_ADDRESS` |
| --- | --- | --- | --- |
| Offline | not forwarded | none | unset |
| Provider, `google-account` | not forwarded | relay values only | unset |
| Provider, `gemini-api` | forwarded by name | relay values only | unset |
| Unrestricted | forwarded by name, as today | as today | unset |

`AGY_PROXY_STRICT_SSL`, `AGY_CA_CERT`, `GOOGLE_GEMINI_BASE_URL` and `GOOGLE_GENAI_USE_VERTEXAI` are never forwarded, because the wrapper forwards nothing but the key. In restricted modes the protected optional-traffic values are set after forwarding.

### Optional traffic

`AGY_CLI_DISABLE_AUTO_UPDATE=true` stays protected in every mode. Task 2.3 measures telemetry with a logging proxy:
- If an environment control exists, it is set as a protected value.
- If only a writable setting exists, the proxy denial is the control, and the README says so.

The updater and telemetry hosts are not in any profile, so a missing control fails closed.

### Go client proxy and CA behavior

Go's `net/http` honors `HTTPS_PROXY`/`https_proxy` and `NO_PROXY` through `ProxyFromEnvironment`, and reads `SSL_CERT_FILE`. Task 2.4 measures HTTPS, streaming, OAuth refresh and any gRPC or WebSocket transport with the synthetic TLS fixture. It also checks whether `AGY_CA_CERT` is needed for the host CA bundle. If it is, the wrapper sets it to `/antigravity-home/ca/bundle.pem` only when trust is enabled, and this change records that in the per-agent documentation. Bypassing transports fail closed and are documented; the allowlist is never broadened.

### `agy` components under the guard

Task 2.5 runs, in offline mode under the guard:
- the TUI in a PTY;
- `agy -p` against a loopback stub;
- a terminal-sandbox command (Bubblewrap);
- the language server.

A Unix listener, bus or `bwrap` namespace dependency is recorded. If the core CLI needs a Unix listener, the port stops and goes back to the operator. Bubblewrap is expected to fail under the guard's filter and the dropped capabilities. In that case the documented outcome is that the container, not the native sandbox, is the boundary, and the guard is not relaxed.

### Tests

`test_wrapper.py`'s inline fake moves to `tests/fake_podman.py`, adapted from Pi, so the restricted cases can record `session.py` and engine calls. `tests/run-runtime.sh` gains the mode set of Pi and keeps the `agy` image as the runner. The keyring test cases are replaced by file-token and no-bus cases.

## Risks / Trade-offs

- **[Account tokens lose passphrase protection]** → The state home stays private (`0700`, caller-owned, checked before every launch), as for Claude and Codex. The README states the property. The operator accepted this on 2026-11-10.
- **[`agy` needs a bus or a Unix listener for a core path]** → Measured first, in tasks 2.2 and 2.5. The port stops for an operator decision; the guard is never weakened.
- **[Unknown account hosts]** → Measured with a logging proxy, dated, and pinned to `agy` 1.5.3. Missing hosts fail closed; wildcards are never used.
- **[The Bubblewrap terminal sandbox does not work under the guard]** → Documented. The outer guard and proxy bound every command anyway.
- **[Three breaking changes at once]** (mode required, maintenance gate, keyring removal) → The messages name the replacement, and a new `CHANGELOG.md` and the README migration section cover them.
- **[A shared-file defect appears]** → Fix it in Claude under a new tag, as for `sandbox-ref-3` to `sandbox-ref-8`.

## Migration Plan

1. To keep today's behavior, users set `ANTIGRAVITY_CONTAINER_NETWORK=unrestricted` and add `ANTIGRAVITY_CONTAINER_MAINTENANCE=1` to commands that build. Keyring users sign in again once, then may delete the old keyring files.
2. Restricted use requires, in order:
   1. the operator build inputs;
   2. `ANTIGRAVITY_CONTAINER_NETWORK=offline bash ./antigravity-container.sh --container-qualify`;
   3. ordinary launches.

   Provider mode adds the proxy image and the profile, policy and runtime-directory variables.
3. Rollback: check out the previous `main` merge (`50d04ed`). Tokens written to files are not read by the old keyring path, so users sign in again after a rollback.

## Open Questions

- The exact `google-account` hosts and whether `agy` 1.5.3 has a non-interactive sign-in command (task 2.1).
- The telemetry control on 1.5.3 (task 2.3).
