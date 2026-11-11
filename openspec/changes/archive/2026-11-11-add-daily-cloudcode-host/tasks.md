# Tasks

## 1. Protected profile and policy

- [x] 1.1 Add `daily-cloudcode-pa.googleapis.com`, `www.googleapis.com`, `aicode.googleapis.com`, `www.gstatic.com` and `play.googleapis.com` to `auth.account.hosts` in `agent/profile.json`, and to the `google-account` destinations (port 443) in `agent/policies/default.json`. In the policy:
  - move the revision to `antigravity-2026-11-11-v2` and `source_date` to `2026-11-11`;
  - record the operator sessions in `tested`, keeping each value within the 120-character limit.

  Verify with `bash tests/run-runtime.sh --network-policy` and `--shared` (exact base-profile check in `test_agent_profile`), both passing.

## 2. Wrapper

- [x] 2.1 In the `antigravity-container.sh` help, list all seven `google-account` hosts, and state that telemetry is allowed only with `google-account` and denied with `gemini-api`. Extend the `tests/test_wrapper.py` help assertion accordingly. Verify with `bash -n`, ShellCheck and `bash tests/run-runtime.sh --wrapper`.

## 3. Runtime tests

- [x] 3.1 Update the controlled fixtures:
  - add the new hosts to the fixture certificate SANs and `PROVIDER_HOSTS`;
  - pass the seven `controlled-google-account` hosts to the shared binding fixture as one comma-separated argument, and assert that `tls-destination-binding-ok profiles=` reports all of them;
  - deny the updater, `generativelanguage` and both sandbox Cloud Code variants under `controlled-google-account`;
  - deny telemetry and every account host under `controlled-gemini-api`.

  Verify with `bash tests/run-runtime.sh --network` passing.
- [x] 3.2 In `tests/test_setup_runtime.py`, require all seven account hosts in the provider residual notice. Verify with `bash tests/run-runtime.sh --setup-runtime` passing.

## 4. Documentation

- [x] 4.1 Update the account hosts, the telemetry treatment and the residual-exfiltration text in:
  - the README;
  - `docs/setup.md`;
  - `docs/network-contract.md`: profile table, revision, the operator-session evidence, the sandbox variants that stay denied, and the optional-traffic bullet.

  Verify that the documents list the account hosts exactly as `agent/profile.json` does, and that markdownlint (no new findings except MD013) and `git diff --check` are clean.
- [x] 4.2 In `docs/validation.md`, record:
  - both operator sessions with their denial counts and decisions;
  - the offline binary scan;
  - the binding-test defect;
  - the test results.

  Keep the authenticated `google-account` checks (model request, streaming, refresh, `/logout`) pending. In `CHANGELOG.md`, note the new hosts, the telemetry treatment and that requalification is needed. Verify with markdownlint.

## 5. Final verification

- [x] 5.1 Run `bash tests/run-runtime.sh` with `--shared`, `--wrapper`, `--network-policy`, `--network` and `--setup-runtime`, then `openspec validate add-daily-cloudcode-host --strict`. All must pass. Record the results in `docs/validation.md`.

## Workflow follow-up

- `/opsx:archive`, then commit and merge into `main`; the user pushes.
- The operator reruns `--container-setup` (requalification), then tests a full `google-account` session: eligibility, a model request with streaming, token refresh and `/logout`. New denials go into a follow-up change.
- Decide whether to remove `cloudcode-pa.googleapis.com`, `aicode.googleapis.com` or `www.gstatic.com` if later evidence shows they are unused.
