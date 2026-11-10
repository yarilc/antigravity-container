# Changelog

All notable changes to this project are documented in this file.

## Unreleased

### Added

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
