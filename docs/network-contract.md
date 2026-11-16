# Network policy contract

Status: ported by the `add-network-egress` change.

- Restricted modes are implemented and verified with synthetic and real
  rootless runtime suites.
- The authenticated Google account and Gemini API-key checks are operator-run
  and recorded separately in [the validation record](validation.md).
- Guided setup and the managed launcher (`add-container-setup`) are described in
  [setup](setup.md).

The durable contract is [network-egress](../openspec/specs/network-egress/spec.md),
with [host-ca-trust](../openspec/specs/host-ca-trust/spec.md),
[container-session](../openspec/specs/container-session/spec.md) and the
authentication, isolation, delegation, launcher, image and mount specifications
in `openspec/specs/`.

## Reference and intentional differences

The shared components are copied unchanged from `sandbox-container` at tag
`sandbox-ref-20` (commit `d4fd4ca88050e1090ba9898d161100d4de87815e`):

- `network/` (except the build output `network/bin/`);
- `setup/`;
- the shared tests listed in that tag's `tests/test_alignment.py`.

`tests/test_reference_copy.py` holds the SHA-256 of every copied file and fails
on a changed, missing or extra file; the unchanged `tests/test_alignment.py`
fails on a profile identifier (`antigravity`, `agy`, `gemini`) in a shared
file. A defect in a shared file is fixed in
`sandbox-container` first and then copied; this repository never carries a fork.
[network/README.md](../network/README.md) is part of the copy and describes the
shared mechanism in agent-neutral terms.

Intentional differences are limited to per-agent files:

| File | Antigravity value or behavior |
| --- | --- |
| `agent/profile.json` | Identity: `antigravity-container`, prefix `ANTIGRAVITY_CONTAINER`, labels `io.antigravity-container.*`. Images: `localhost/antigravity-cli`, `localhost/antigravity-egress`, `localhost/antigravity-guard-toolchain`. Runtime: home `/antigravity-home`, command `agy`. State: configuration `.gemini` with override `ANTIGRAVITY_CONTAINER_CONFIG_DIR`, no shared directories. Approval variable `ANTIGRAVITY_YOLO`. Methods `account` (`google-account`) and `gemini` (`gemini-api`). Installation file `container-entrypoint.sh` (`install.files`). The `account` method declares empty `login_args`: setup offers sign-in inside the interactive `agy` |
| `agent/policies/default.json` | `google-account` and `gemini-api`, revision `antigravity-2026-11-11-v2` |
| `antigravity-container.sh` | `agy` arguments and YOLO; three state choices (unset: dedicated home; path: isolated home; empty: shared `~/.gemini` below an ephemeral home); no D-Bus session; protected `AGY_CLI_DISABLE_AUTO_UPDATE=true`; `GEMINI_API_KEY` only with `gemini-api`; no host proxy or CA variables in restricted modes; `--container-setup`, the `setup required:` message and the stderr diagnostics filter |
| `container-entrypoint.sh` | Help and version shortcut, scoped `SSH_CONNECTION` marker for the remote URL/code sign-in, `exec agy`; no keyring |
| `Containerfile`, `.containerignore` | `agy` 1.5.3 from the pinned release artifact, no keyring packages; copies `network/relay.py` and `network/mux.py` |
| `tests/test_wrapper.py`, `fake_podman.py`, `test_runtime.py`, `test_network_runtime.py`, `network_tls_fixture.py`, `test_setup_runtime.py`, `run-runtime.sh`, `test_image_pins.py`, `image-smoke.sh`, `test_reference_copy.py` | Antigravity names, synthetic Gemini `streamGenerateContent` fixture, Google host inventories |

Where the reference treats an unset state variable as shared state, this
wrapper keeps its dedicated home. It passes that home to `network/qualify.py`
explicitly, so qualification and launch bind the same writable paths.

## Modes

| Mode | Agent access | Socket delegation |
| --- | --- | --- |
| unset or empty | Launch stops with `setup required:` guidance before engine calls and state creation | No session |
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
| `google-account` | `oauth2.googleapis.com:443`, `cloudcode-pa.googleapis.com:443`, `daily-cloudcode-pa.googleapis.com:443`, `www.googleapis.com:443`, `aicode.googleapis.com:443`, `www.gstatic.com:443`, `play.googleapis.com:443` | Account tokens in `~/.gemini/antigravity-cli/antigravity-oauth-token` | Static inventory of 1.5.3, plus the hosts denied in two operator sessions (2026-11-11); operator authenticated test passed on `antigravity-2026-11-11-v2` (2026-11-11) |
| `gemini-api` | `generativelanguage.googleapis.com:443` | `GEMINI_API_KEY` | Measured on 1.5.3 with a logging proxy; real key unverified |

The browser step of sign-in (`accounts.google.com`, redirect to
`antigravity.google`) runs on the host and has no container rule.
The account hosts beyond the static inventory come from two operator-run
sessions on 2026-11-11. In each, sign-in succeeded and the eligibility check
then failed with `Bad Gateway`. The client reports only one failure at a time:

1. `daily-cloudcode-pa.googleapis.com` (`loadCodeAssist`), the default Cloud
   Code URL embedded in `agy` 1.5.3;
2. `www.googleapis.com` (`oauth2/v2/userinfo`).

Both sessions also logged denials of `aicode.googleapis.com`, `www.gstatic.com`
and `play.googleapis.com`. The operator approved all of them. Two of these
hosts widen the profile beyond the model service:

- `www.googleapis.com` is a general API host that also serves Drive;
- `play.googleapis.com` receives the client's telemetry. See the optional
  traffic section below.

`cloudcode-pa.googleapis.com` stays allowed provisionally: the proxy logs
denials only, so whether `agy` uses it is not yet known.

The sandbox Cloud Code variants `autopush-cloudcode-pa.sandbox.googleapis.com`
and `preprod-daily-cloudcode-pa.sandbox.googleapis.com`, embedded in the
binary, stay denied. The client's Cloud Code URL override is neither set nor
forwarded, and if it is set in writable configuration, the policy still
decides.

Vertex AI, enterprise and custom endpoints, ADC and other providers have no
profile.

In provider mode only `gemini-api` forwards `GEMINI_API_KEY`; offline and
`google-account` forward none. Unrestricted mode keeps forwarding
`GEMINI_API_KEY`.

## Optional traffic and client behavior (measured on 1.5.3)

- `AGY_CLI_DISABLE_AUTO_UPDATE=true` is set after forwarding; `agy` logs that
  auto-update is disabled.
- Telemetry goes to `play.googleapis.com/log` even with the
  `telemetryEnabled: false` setting, and no environment control was found. The
  proxy denies it under `gemini-api`. Under `google-account` it is allowed,
  because the operator sessions of 2026-11-11 required it together with the
  other account hosts. There, the account's telemetry reaches Google.
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
- Allowed services can receive data; see
  [Residual exfiltration to allowed services](#residual-exfiltration-to-allowed-services).
- Provider-hosted tools such as web search run outside the local boundary.
- Account tokens are files protected by Unix permissions only, as in the other
  wrappers.
- Image pulls and build `RUN` steps happen outside runtime filtering and need
  separate maintenance authorization.
- Qualification reports are local (`locally-qualified`); the release
  acceptance inventory is empty.

### Residual exfiltration to allowed services

Destination and SNI binding cannot tell the operator's credentials from
attacker-supplied ones. A prompt-injected agent can therefore send workspace
data to every allowed host of the selected profile with a foreign Gemini API key
or Google account:

- `google-account`: `oauth2.googleapis.com`, `cloudcode-pa.googleapis.com`,
  `daily-cloudcode-pa.googleapis.com`, `www.googleapis.com`,
  `aicode.googleapis.com`, `www.gstatic.com` and `play.googleapis.com`;
- `gemini-api`: `generativelanguage.googleapis.com`.

Reducing the host list does not remove this channel; only `offline` does. Setup
shows this notice and requires its acknowledgement whenever provider mode is
selected.

## Five-wrapper parity

The same Antigravity row appears in `sandbox-container`, `claude-container`, `codex-container`,
`opencode-container` and `pi-container`.

| Wrapper | Contract adoption | Implementation | Real enforcement | Auth compatibility |
| --- | --- | --- | --- | --- |
| Sandbox (reference) | Reference (`sandbox-ref-20`) | Guard, qualification and guided setup integrated; no provider mode (no authentication method); provider mechanics covered by the fixture profile | WSL ABI 3: all runner modes passed (2026-11-15) | Not applicable |
| Claude | Ported from `sandbox-ref-20`; shared files unchanged | Mandatory bootstrap, multiplexed proxy and guided setup integrated | See the Claude validation record | Account login, reuse and refresh passed; operator session with tool use passed (2026-11-11, `anthropic-account`); real-key API unavailable |
| Codex | Ported from `sandbox-ref-20`; shared files unchanged | Guard, multiplexed proxy, qualification and guided setup integrated | WSL ABI 3: all runtime modes and setup acceptance passed (2026-11-09) | Operator session with tool use passed (2026-11-11, `openai-account`); refresh and API-key checks pending; synthetic Responses API streaming and tool call passed |
| Antigravity | Ported from `sandbox-ref-20`; shared files unchanged | Guard, multiplexed proxy, qualification and guided setup integrated; keyring removed | WSL ABI 3: all runtime modes and setup acceptance passed (2026-11-10) | Operator session with tool use passed (2026-11-11, `google-account`, policy `antigravity-2026-11-11-v2`); refresh and Gemini API-key checks pending; synthetic Gemini streaming and tool call passed |
| OpenCode | Ported from `sandbox-ref-20`; shared files unchanged | Guard, multiplexed proxy, qualification and guided setup integrated | WSL ABI 3: all runtime modes and setup acceptance passed (2026-11-10) | Operator session with tool use passed (2026-11-11, `anthropic-api`); the other three profiles pending; synthetic Chat Completions streaming and tool call passed |
| Pi | Ported from `sandbox-ref-20`; shared files unchanged | Guard, multiplexed proxy, qualification and guided setup integrated | WSL ABI 3: all runtime modes and setup acceptance passed (2026-11-10) | Operator session with tool use passed (2026-11-11, `anthropic-api`); the other three profiles pending; synthetic Chat Completions streaming and tool call passed |

## Port status

| Item | Status |
| --- | --- |
| Shared copy and identifier scan | Done (`tests/test_reference_copy.py`) |
| Shared suites, guard, mux, policy, feasibility, qualification | See [validation](validation.md) |
| Wrapper integration and restricted runtime acceptance | See [validation](validation.md) |
| Authenticated Google account and Gemini API-key checks | Operator-run, pending until all Waves are complete |
| Shared setup suite and alignment | See [validation](validation.md) (`tests/test_setup.py`, `tests/test_alignment.py`) |
| Guided setup acceptance | See [validation](validation.md) |
