# Proposal

## Why

On 2026-11-11 the operator ran the first authenticated provider sessions under `google-account`. In each one, sign-in worked, and then `agy` 1.5.3 failed its eligibility check with `Bad Gateway`, the response the relay gives for every policy denial. The client reports only one failure at a time:

1. **Session `session.EPGcuRaMkTsB`, policy `antigravity-2026-11-10-v1`.** Failure: `Post "https://daily-cloudcode-pa.googleapis.com/v1internal:loadCodeAssist"`. Denied: `daily-cloudcode-pa.googleapis.com` (11 times), `www.googleapis.com` (once) and `play.googleapis.com` (3 times).
2. **Session `session.9TeqMf00VuXH`, after `daily-cloudcode-pa` was allowed.** The model selection showed, and the eligibility check then failed with `Get "https://www.googleapis.com/oauth2/v2/userinfo"`. Denied: `www.googleapis.com` (3 times), `aicode.googleapis.com` (twice), `www.gstatic.com` (twice) and `play.googleapis.com` (4 times).

The static inventory that defined `google-account` had only `oauth2.googleapis.com` and `cloudcode-pa.googleapis.com`, because a synthetic token was not accepted for measurement. As a result, `google-account` is unusable. The operator decided to allow every host denied in these sessions.

## What Changes

- Add these hosts to the `google-account` base profile in `agent/profile.json` and `agent/policies/default.json`, each on port 443:
  - `daily-cloudcode-pa.googleapis.com`;
  - `www.googleapis.com`;
  - `aicode.googleapis.com`;
  - `www.gstatic.com`;
  - `play.googleapis.com`.

  The policy revision becomes `antigravity-2026-11-11-v2`. The operator's denial logs are the measurement source.
- **Telemetry:** `play.googleapis.com` becomes reachable under `google-account` and stays denied under `gemini-api`. This narrows the rule that a missing telemetry control never broadens the allowlist.
- Keep `oauth2.googleapis.com` and `cloudcode-pa.googleapis.com`. `cloudcode-pa` is removed only if a complete operator session shows it is unused. The proxy logs denials only, so today's evidence cannot show that.
- Keep the `autopush-` and `preprod-daily-` sandbox variants of `cloudcode-pa`, and the auto-updater, denied. Do not set or forward the `CLOUD_CODE_URL` override.
- Update every place that lists the account hosts or the telemetry treatment:
  - the wrapper help;
  - the setup residual-exfiltration notice;
  - the README;
  - `docs/setup.md`;
  - `docs/network-contract.md`;
  - `docs/validation.md`;
  - `CHANGELOG.md`.
- Update the controlled test profiles and the TLS fixture. Fix the TLS binding test: it passed the account hosts separated by spaces, so the shared fixture checked only the first one.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-egress`:
  - the Google account profile requirement covers all account hosts used after sign-in, and the new "Measured Google account hosts" requirement lists them and the hosts that stay denied;
  - the optional-traffic requirement refers to the new "Profile-scoped telemetry exception" requirement, which allows telemetry only under the profile whose measured session requires it;
  - the residual-exfiltration disclosure names the new hosts.

## Impact

- **Files:**
  - `agent/profile.json`, `agent/policies/default.json`;
  - `antigravity-container.sh`: provider help;
  - `tests/test_wrapper.py`, `tests/test_network_runtime.py`, `tests/network_tls_fixture.py`, `tests/test_setup_runtime.py`;
  - the README, `docs/setup.md`, `docs/network-contract.md`, `docs/validation.md` and `CHANGELOG.md`.
- **No change** to `network/`, `setup/` or the shared tests, so no new reference tag.
- **Users:** `google-account` sessions gain five Google-operated hosts. Each can receive workspace data sent with a foreign Google account.
  - `www.googleapis.com` is a general API host that includes Drive, which widens that channel beyond the model service.
  - Under `google-account`, the client's telemetry reaches Google.
  - `gemini-api` is unchanged.
- **Qualification:** the policy revision changes, so existing installations must run `--container-setup` or `--container-qualify` again.
- **Follow-up:** the operator's next session must go past the eligibility check (model request, streaming, refresh) to confirm that no other host is needed.
