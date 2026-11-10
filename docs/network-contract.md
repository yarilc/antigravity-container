# Network policy contract

Status: ported by the `add-network-egress` change.

- Restricted modes are implemented and verified with synthetic and real
  rootless runtime suites.
- The authenticated Google account and Gemini API-key checks are operator-run
  and recorded separately in [the validation record](validation.md).
- Guided setup and the managed launcher follow in `add-container-setup`.

The durable contract is [network-egress](../openspec/specs/network-egress/spec.md),
with [host-ca-trust](../openspec/specs/host-ca-trust/spec.md),
[container-session](../openspec/specs/container-session/spec.md) and the
authentication, isolation, delegation, launcher, image and mount specifications
in `openspec/specs/`.

## Reference and intentional differences

The shared components are copied unchanged from `claude-container` at tag
`sandbox-ref-8` (commit `12cffab0d248ec48a95f3b1840c573fcebdbb427`):

- `network/` (except the build output `network/bin/`);
- `setup/diagnostics.py`;
- the shared tests listed in that tag's `tests/test_alignment.py`, except
  `test_alignment.py` and `test_setup.py`, which arrive with
  `add-container-setup`.

`tests/test_reference_copy.py` holds the SHA-256 of every copied file. It fails
on a changed, missing or extra file, or on a profile identifier (`antigravity`,
`agy`, `gemini`) in a copied file. A defect in a shared file is fixed in
`claude-container` first and then copied; this repository never carries a fork.
[network/README.md](../network/README.md) is part of the copy and describes the
shared mechanism in agent-neutral terms.

Intentional differences are limited to per-agent files:

| File | Antigravity value or behavior |
| --- | --- |
| `agent/profile.json` | Identity: `antigravity-container`, prefix `ANTIGRAVITY_CONTAINER`, labels `io.antigravity-container.*`. Images: `localhost/antigravity-cli`, `localhost/antigravity-egress`, `localhost/antigravity-guard-toolchain`. Runtime: home `/antigravity-home`, command `agy`. State: configuration `.gemini` with override `ANTIGRAVITY_CONTAINER_CONFIG_DIR`, no shared directories. Approval variable `ANTIGRAVITY_YOLO`. Methods `account` (`google-account`) and `gemini` (`gemini-api`). Installation file `container-entrypoint.sh` (`install.files`) |
| `agent/policies/default.json` | `google-account` and `gemini-api`, revision `antigravity-2026-11-10-v1` |
| `antigravity-container.sh` | `agy` arguments and YOLO; three state choices (unset: dedicated home; path: isolated home; empty: shared `~/.gemini` below an ephemeral home); no D-Bus session; protected `AGY_CLI_DISABLE_AUTO_UPDATE=true`; `GEMINI_API_KEY` only with `gemini-api`; no host proxy or CA variables in restricted modes; missing-mode message without setup |
| `container-entrypoint.sh` | Help and version shortcut, scoped `SSH_CONNECTION` marker for the remote URL/code sign-in, `exec agy`; no keyring |
| `Containerfile`, `.containerignore` | `agy` 1.5.3 from the pinned release artifact, no keyring packages; copies `network/relay.py` and `network/mux.py` |
| `tests/test_wrapper.py`, `fake_podman.py`, `test_runtime.py`, `test_network_runtime.py`, `network_tls_fixture.py`, `run-runtime.sh`, `test_image_pins.py`, `image-smoke.sh`, `test_reference_copy.py` | Antigravity names, synthetic Gemini `streamGenerateContent` fixture, Google host inventories |

Where the reference treats an unset state variable as shared state, this
wrapper keeps its dedicated home. It passes that home to `network/qualify.py`
explicitly, so qualification and launch bind the same writable paths.

## Modes

| Mode | Agent access | Socket delegation |
| --- | --- | --- |
| unset or empty | Launch stops before engine calls and state creation | No session |
| `offline` | Own loopback, pipes and connected socket pairs only | Rejected |
| `provider` | As offline, plus one preconnected channel to an exact-destination proxy | Rejected |
| `unrestricted` (explicit only) | Ordinary runtime networking | Exact opt-in allowed |

Unknown modes fail before image operations. Restricted failures never retry
with unrestricted networking. YOLO, writable `settings.json`, session
`--settings` JSON, `modelProvider` and shell mode cannot broaden the outer
policy. Restricted agents have no direct route, external resolver, UDP/QUIC,
host/LAN/metadata access or proxy administration access. Every agent
container, in every mode, drops all capabilities, enables no-new-privileges and
has verified memory, CPU and process budgets.

Restricted launches follow the Claude wrapper order:

1. arguments;
2. mode and delegation;
3. budgets and lifetime;
4. lexical state checks;
5. engine verification;
6. restricted platform queries;
7. state creation and validation;
8. CA;
9. `network/session.py prepare`;
10. image operations under the maintenance gate;
11. the immutable image ID;
12. `network/qualify.py check`;
13. `session.py start` and `agent-args`;
14. owned create and start;
15. `session.py stop` within the remaining shutdown budget.

The guard replaces the image entrypoint and then runs
`/usr/local/bin/antigravity-entrypoint`.

## Provider profiles

| Profile | Destinations | Credential | Status |
| --- | --- | --- | --- |
| `google-account` | `oauth2.googleapis.com:443`, `cloudcode-pa.googleapis.com:443` | Account tokens in `~/.gemini/antigravity-cli/antigravity-oauth-token` | Static inventory of 1.5.3 (token and model endpoints); real sign-in, refresh and requests unverified |
| `gemini-api` | `generativelanguage.googleapis.com:443` | `GEMINI_API_KEY` | Measured on 1.5.3 with a logging proxy; real key unverified |

The browser step of sign-in (`accounts.google.com`, redirect to
`antigravity.google`) runs on the host and has no container rule.
`www.googleapis.com` (user information) is deliberately not allowed: it is a
general API host. If the operator check shows that sign-in needs it, the
profile changes in a separate decision. Vertex AI, enterprise and custom
endpoints, ADC and other providers have no profile.

In provider mode only `gemini-api` forwards `GEMINI_API_KEY`; offline and
`google-account` forward none. Unrestricted mode keeps forwarding
`GEMINI_API_KEY`.

## Optional traffic and client behavior (measured on 1.5.3)

- `AGY_CLI_DISABLE_AUTO_UPDATE=true` is set after forwarding; `agy` logs that
  auto-update is disabled.
- Telemetry goes to `play.googleapis.com/log` even with the
  `telemetryEnabled: false` setting, and no environment control was found. The
  proxy denies it in every profile.
- `agy` honors `HTTPS_PROXY` for model, OAuth and telemetry requests; no direct
  connection was observed.
- `agy` trusts the host CA bundle through `SSL_CERT_FILE`; `AGY_CA_CERT` alone
  did not establish trust.
- Under the guard, `agy` runs its language server on loopback TCP, which the
  guard permits. Its Bubblewrap terminal sandbox cannot create namespaces
  (`Failed to make / slave: Operation not permitted`); commands still run
  inside the guarded container, which is the boundary.

## Limits

- The proxy binds the initial and retried TLS ClientHello server name
  (`tls-clienthello-sni-v2`) to the CONNECT host; TLS 1.2 renegotiation is
  encrypted and not inspected.
- It does not prove exclusive communication with the operator's Google account
  or project: the HTTP `Host`, shared-service routing and provider-side
  forwarding stay opaque.
- Allowed services can receive data: an injected agent can send workspace data
  to an allowed host with an attacker's Gemini API key or Google account. Only
  `offline` removes this.
- Provider-hosted tools such as web search run outside the local boundary.
- Account tokens are files protected by Unix permissions only, as in the other
  wrappers.
- Image pulls and build `RUN` steps happen outside runtime filtering and need
  separate maintenance authorization.
- Qualification reports are local (`locally-qualified`); the release
  acceptance inventory is empty.

## Port status

| Item | Status |
| --- | --- |
| Shared copy and identifier scan | Done (`tests/test_reference_copy.py`) |
| Shared suites, guard, mux, policy, feasibility, qualification | See [validation](validation.md) |
| Wrapper integration and restricted runtime acceptance | See [validation](validation.md) |
| Authenticated Google account and Gemini API-key checks | Operator-run, pending until all Waves are complete |
| `test_alignment.py`, `test_setup.py`, guided setup, parity row | `add-container-setup` |
