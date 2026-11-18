# Changelog

All notable changes to this project are documented in this file.

## Unreleased

### Added

- Guided setup (`add-container-setup`): `--container-setup` prepares images,
  guard and a protected installation with a managed launcher at
  `~/.local/bin/antigravity-container`, qualifies restricted modes and runs a
  smoke check. For the `account` method it offers sign-in inside the interactive
  `agy` (empty `login_args`, `claude-container` tag `sandbox-ref-9`).
- `docs/setup.md`, the shared `tests/test_setup.py` and `tests/test_alignment.py`,
  `tests/test_setup_runtime.py`, and the five-wrapper parity table.
- The wrapper passes client stderr through the shared diagnostics filter.

- Network modes (`add-network-egress`): `ANTIGRAVITY_CONTAINER_NETWORK` selects
  `offline`, `provider` (exact-destination egress proxy) or `unrestricted`.
  Restricted modes use the native guard, the multiplexed relay and the egress
  proxy copied unchanged from `claude-container` tag `sandbox-ref-8`.
- Provider profiles `google-account` and `gemini-api` in
  `agent/policies/default.json`, with `agent/profile.json`.
- `--container-qualify` and the per-launch local qualification check.
- Opt-in host CA trust (`ANTIGRAVITY_CONTAINER_TRUST_HOST_CA`,
  `ANTIGRAVITY_CONTAINER_CA_BUNDLE`).
- Shared state: an empty `ANTIGRAVITY_CONTAINER_STATE_DIR` mounts the host
  `~/.gemini` (or the new `ANTIGRAVITY_CONTAINER_CONFIG_DIR`) below an
  ephemeral home. An unset value keeps the dedicated home.
- `docs/network-contract.md`; network runtime, TLS fixture and reference-copy
  tests.

### Changed

- Pin OpenSpec 2.0.0 in the image. This release generates skills in
  `.agents/skills/` and removes the generated `/opsx:*` command files.
- Shared files now come from `claude-container` tag `sandbox-ref-10`: a failed
  setup smoke check shows the wrapper's sanitized stderr, and setup refusals of
  non-private directories name the reason and the `chmod 700` fix.
- Account profile hosts (`add-daily-cloudcode-host`): `google-account` now
  also allows the hosts that the operator sessions of 2026-11-11 saw denied:
  `daily-cloudcode-pa.googleapis.com` (default Cloud Code URL of `agy` 1.5.3),
  `www.googleapis.com` (user information), `aicode.googleapis.com`,
  `www.gstatic.com` and `play.googleapis.com` (telemetry). Without them, the
  eligibility check failed with `Bad Gateway`. Telemetry stays denied under
  `gemini-api`, and the sandbox Cloud Code variants stay denied. Policy
  revision `antigravity-2026-11-11-v2`: existing installations must rerun
  `--container-setup` or `--container-qualify`.
- A launch with no `ANTIGRAVITY_CONTAINER_NETWORK` now stops with
  `setup required:` guidance naming `--container-setup`.
- Shared files now come from `claude-container` tag `sandbox-ref-9`.

- **BREAKING:** every launch requires an explicit
  `ANTIGRAVITY_CONTAINER_NETWORK`. Set `unrestricted` to keep the previous
  networking.
- **BREAKING:** every image build, including the build of a missing image,
  requires exact `ANTIGRAVITY_CONTAINER_MAINTENANCE=1`.
- **BREAKING:** the private D-Bus session, the GNOME keyring and its passphrase
  were removed (`keyring-session.sh`, `dbus`, `gnome-keyring`, `libsecret`).
  `agy` keeps account tokens in files in the private state home; accounts
  signed in through the keyring sign in again once.
- **BREAKING:** `ANTIGRAVITY_CONTAINER_PODMAN=1` is rejected in `offline` and
  `provider`.
- The image copies `network/relay.py` and `network/mux.py` and includes
  `openssl`; the build context admits five files.
- Restricted sessions forward no host proxy or CA variables; `GEMINI_API_KEY`
  is forwarded only in unrestricted mode and with `gemini-api`.
