# Proposal

## Why

Every Antigravity session runs with ordinary Podman networking. With YOLO or a prompt-injected tool, `agy` can reach any host, the LAN and host services without a prompt. Claude, Codex, OpenCode and Pi already run the shared restricted-mode components of `claude-container` unchanged. This change ports the reference state (tag `sandbox-ref-8`) to Antigravity as the first of its two consolidated Wave 3 changes. `add-container-setup` follows with guided setup, the managed launcher and the parity row.

One Antigravity-specific blocker had to be decided first. Account sign-in starts a private D-Bus session and a GNOME keyring, and `agy` reaches them over Unix sockets. The shared guard denies new Unix sockets and listeners, so account login cannot work under it. `agy` 1.5.3 bypasses the OS keyring when no D-Bus session bus is present and stores its tokens in files (its 1.1.3 changelog entry; `fileTokenStorage` in the binary). On 2026-11-10 the operator chose that file storage in every mode.

## What Changes

- **BREAKING** `ANTIGRAVITY_CONTAINER_NETWORK` selects `offline`, `provider` or `unrestricted`.
  - An unset or empty mode stops ordinary launches before any engine call, with a message naming the three values and stating that `unrestricted` keeps the previous behavior.
  - Unknown values fail before image operations.
  - Restricted failures never fall back to unrestricted networking.

  This replaces the "default offline" note of 2026-11-08 in `todo.md`, as for the other ports.
- **BREAKING** The private D-Bus session, the GNOME keyring and its passphrase are removed in every mode, as the operator decided on 2026-11-10.
  - `keyring-session.sh` is deleted. The entrypoint runs `agy` directly, and still sets the scoped `SSH_CONNECTION` marker that requests the remote URL/code sign-in.
  - `agy` stores account tokens in files in the private state home (`0700`), as Claude and Codex do.
  - Users who signed in through the keyring must sign in again. Old keyring files stay in the state directory, and the README explains how to remove them.
  - `dbus`, `gnome-keyring`, `libsecret-1-0` and `libsecret-tools` leave the image.
- **BREAKING** Every image build requires the exact `ANTIGRAVITY_CONTAINER_MAINTENANCE=1`, both the automatic build of a missing image and `--container-build`. The build downloads the pinned `agy` release. A provider proxy image is pulled only under the same authorization and only by digest.
- **BREAKING** `ANTIGRAVITY_CONTAINER_PODMAN=1` is rejected in `offline` and `provider` before image or resource operations.
- Copy `network/` and `setup/diagnostics.py` unchanged from `claude-container` `sandbox-ref-8`. The copy brings:
  - the guard;
  - the multiplexed relay and egress proxy with `tls-clienthello-sni-v2`;
  - protected policy and installation checks;
  - proxy hardening;
  - platform eligibility and local qualification;
  - the shared session helper.
- Add `agent/profile.json` and `agent/policies/default.json` with two profiles:

  | Profile | Hosts | Credential |
  | --- | --- | --- |
  | `google-account` | the exact OAuth token and model-service hosts of `agy` 1.5.3, measured (candidates: `oauth2.googleapis.com`, `cloudcode-pa.googleapis.com`) | account tokens in the state home |
  | `gemini-api` | `generativelanguage.googleapis.com:443` | `GEMINI_API_KEY` |

  The browser step of account sign-in (`accounts.google.com`) runs on the host and gets no container rule. There are no wildcards such as `*.googleapis.com` or `*.google.com`. Vertex AI, enterprise and custom endpoints and ADC get no profile.
- Credentials and proxy settings by mode:
  - provider sessions forward `GEMINI_API_KEY` only with `gemini-api`;
  - offline sessions forward no key;
  - unrestricted keeps forwarding `GEMINI_API_KEY`;
  - restricted modes forward no host proxy or CA variable;
  - the shared helper sets the relay values and `NO_PROXY=localhost,127.0.0.1,::1`.
- In restricted modes, keep `AGY_CLI_DISABLE_AUTO_UPDATE=true` and disable telemetry with protected values that the writable settings cannot override, as measured on 1.5.3.
- Add `--container-qualify` and require a current local qualification report before every ordinary `offline` or `provider` launch.
- Port opt-in host CA trust (`ANTIGRAVITY_CONTAINER_TRUST_HOST_CA`, `ANTIGRAVITY_CONTAINER_CA_BUNDLE`), with a read-only bundle at `/antigravity-home/ca/bundle.pem`. Restricted launches use the immutable image ID.
- State changes, decided by the operator on 2026-11-10:
  - an unset `ANTIGRAVITY_CONTAINER_STATE_DIR` keeps today's dedicated home `~/.local/share/antigravity-container/home`;
  - an empty value selects shared state: the host `~/.gemini`, or the new `ANTIGRAVITY_CONTAINER_CONFIG_DIR`, mounted at `/antigravity-home/.gemini`;
  - `ANTIGRAVITY_CONTAINER_CONFIG_DIR` applies only to shared state and is set in every session to `/antigravity-home/.gemini`;
  - isolated state is checked lexically before the engine and created after it, following the reference order.
- The runtime image copies `network/relay.py` and `network/mux.py`. `.containerignore` admits them and no longer admits `keyring-session.sh`.
- Port the shared tests, adapt the wrapper and runtime tests, and record real rootless evidence. Documentation covers the README, wrapper help, `AGENTS.md`, a new `CHANGELOG.md`, `docs/network-contract.md` and `docs/validation.md`.

Out of scope, deferred to `add-container-setup`:
- `--container-setup` and `setup/` other than `diagnostics.py`;
- the managed launcher and the setup acknowledgement;
- `docs/setup.md`;
- the missing-setup message;
- the Antigravity parity row.

## Capabilities

### New Capabilities

- `network-egress`: operator-selected network modes, the native guard, the multiplexed egress proxy, the protected policy and profile, the two Google profiles, optional-traffic suppression, `agy` tools and its terminal sandbox under the guard, platform prerequisites, local qualification, owned proxy lifecycle, diagnostics and documented limits.
- `host-ca-trust`: opt-in exposure of one host CA bundle, read-only at `/antigravity-home/ca/bundle.pem`, with the standard CA variables.
- `container-session`: explicit network-mode admission, required qualification, consistent prerequisite decisions and the qualification binding of hardening settings. Antigravity has no such capability yet; the other ports have it.

### Modified Capabilities

- `agent-authentication`: account tokens in file storage without D-Bus or keyring; API-key forwarding by mode.
- `container-launcher`:
  - help gains the network contract and `--container-qualify`;
  - every build needs maintenance authorization;
  - restricted forwarding is narrowed.
- `container-isolation`: account sign-in works without capabilities and without a keyring.
- `container-podman-access`: delegation only in explicit unrestricted mode.
- `runtime-image`:
  - the pinned `agy` version matches the policy's tested CLI;
  - restricted launches use the immutable image identity;
  - proxy image acquisition needs maintenance and a digest;
  - the build context admits the relay and multiplex inputs and drops the keyring helper;
  - the toolset drops the keyring packages.
- `workspace-mounts`:
  - shared, dedicated and isolated state;
  - `ANTIGRAVITY_CONTAINER_CONFIG_DIR`;
  - no private keyring runtime directory.

## Impact

- **Code:**
  - `antigravity-container.sh` gains mode parsing, preflight, the `network/session.py` calls, `--container-qualify`, the state and CA changes, the maintenance gate and the restricted forwarding rules.
  - `container-entrypoint.sh` loses the keyring branch. `keyring-session.sh` is deleted.
  - New directories: `network/` (copied), `setup/diagnostics.py`, `agent/`.
  - `Containerfile` and `.containerignore` change.
- **Tests:**
  - the shared tests from Claude (except `test_alignment.py` and `test_setup.py`), plus the per-agent `tests/test_reference_copy.py`;
  - adapted `test_wrapper.py` (moving its inline fake engine to `tests/fake_podman.py`), `test_runtime.py`, `test_image_pins.py`, `image-smoke.sh` and `run-runtime.sh` modes;
  - a new `test_network_runtime.py` with `network_tls_fixture.py`.
- **Users:**
  - existing launches must set `ANTIGRAVITY_CONTAINER_NETWORK=unrestricted`;
  - builds need `ANTIGRAVITY_CONTAINER_MAINTENANCE=1`;
  - keyring users sign in again once;
  - restricted modes need host Python 3, a same-host rootless Podman ≥ 4.9 Unix service with Netavark, Landlock ABI ≥ 3 and a passing `--container-qualify`.
- **Compatibility risks, measured before integration:**
  - whether `agy` without D-Bus really uses file token storage, where it writes, and whether tokens persist and refresh;
  - whether `agy` or its language server needs a Unix listener, which the guard denies;
  - the exact account hosts;
  - whether the Go client honors `HTTPS_PROXY` and `SSL_CERT_FILE` for HTTPS, streaming and token refresh;
  - the telemetry controls;
  - the Bubblewrap terminal sandbox under the guard.

  A blocking result goes to the operator; the guard is never weakened.
