# Design

## Context

See proposal.md (Why) for the failures and the denial logs.

The `google-account` host list exists in two protected inputs that must agree:
- `agent/profile.json` (`auth.account.hosts`): the shared `network/policy.py` derives the exact base-profile rules from it, and rejects a `google-account` policy whose destinations differ ("exact base profile; use a new profile for extensions");
- `agent/policies/default.json`: the destinations of the policy revision that the proxy enforces and that qualification binds by digest.

The shared `setup/setup.py` builds the residual-exfiltration notice from `PROFILE.auth`, so updating `agent/profile.json` updates the setup notice. The wrapper help (`antigravity-container.sh`) and the documents list the hosts by hand.

A static scan of the `agy` 1.5.3 binary inside the image, run offline, found:
- `https://daily-cloudcode-pa.googleapis.com` embedded as the default Cloud Code URL;
- the sandbox variants `autopush-cloudcode-pa.sandbox.googleapis.com` and `preprod-daily-cloudcode-pa.sandbox.googleapis.com`;
- the overrides `CLOUD_CODE_URL`, `cloud_code_endpoint` and `ForceUseCloudCodeAPI`;
- `www.googleapis.com` paths for `userinfo`, `tokeninfo` and Drive;
- `https://aicode.googleapis.com` next to the entitlement and gateway messages;
- `www.gstatic.com/antigravity/web/...` scripts.

## Goals / Non-Goals

**Goals:**
- Make `google-account` usable through the eligibility check, with exact hosts the operator observed.
- Keep the two protected inputs, the setup notice, the wrapper help and the documents consistent with one policy revision.
- Leave `gemini-api` unchanged, including its telemetry denial.

**Non-Goals:**
- Changing `network/` or `setup/`, or tagging a new reference.
- Removing `cloudcode-pa.googleapis.com`. That is decided after a complete operator session.
- Logging allowed connections, which would be a shared proxy change.

## Decisions

1. **Base profile, not an extension profile.** These hosts are needed for the account session to work at all. An extension profile would leave the default `google-account` broken.
2. **Allow every host the operator saw denied, including `www.googleapis.com` and `play.googleapis.com`.**
   - **Why all of them:** the client reports only one failure at a time, so allowing hosts one by one costs a full operator round per host. The operator chose to accept the observed set.
   - **Alternative considered:** keep `www.googleapis.com` and telemetry denied, as in the first draft of this change. Rejected because the second session failed on `www.googleapis.com` itself. For telemetry, the operator judged the evidence sufficient.
   - **Trade-offs, disclosed:** `www.googleapis.com` is a general API host that also serves Drive. Under `google-account`, the client's telemetry reaches Google.
3. **Telemetry exception scoped to one profile.** The optional-traffic requirement keeps its rule that a missing disable control does not broaden the allowlist, with one narrow exception: a telemetry host measured by an operator-run session of a base profile may be allowed in that profile only. `gemini-api` was measured to work without telemetry and keeps denying it.
4. **Do not redirect the client with `CLOUD_CODE_URL`.** Forcing an endpoint is untested for Antigravity accounts, and writable configuration must not choose endpoints. The policy decides the destinations.
5. **Keep `cloudcode-pa.googleapis.com` provisionally.** The proxy records denials only, so nothing shows whether `agy` uses it.
6. **Revision `antigravity-2026-11-11-v2`.** The `-v1` revision was already qualified by the operator with the intermediate host set. A new label keeps the two sets distinguishable in diagnostics. The changed digest forces requalification.
7. **Tests.**
   - Controlled copies of the profile cover all seven hosts in the TLS binding check.
   - Under `google-account`, the denial check covers the updater, `generativelanguage` and the sandbox variants.
   - Under `gemini-api`, it covers the account hosts and telemetry.
   - The binding test passes one comma-separated argument, the format the shared fixture parses, and asserts that the fixture reports every host. The previous space-separated form checked only the first host.

## Risks / Trade-offs

- [The next operator session hits another denied host] → The sanitized denial log names it. A follow-up change adds it after the operator decides.
- [Wider foreign-credential channel through `www.googleapis.com`, which includes Drive APIs] → It is disclosed in the wrapper help, the setup notice, the README and the contract. Only `offline` removes the channel. Exact host, port and SNI binding still apply.
- [Account-mode telemetry reaches Google] → It is disclosed. Operators who need it blocked use `gemini-api` or `offline`.
- [`aicode.googleapis.com` and `www.gstatic.com` have no documented purpose] → They are recorded with the static-scan evidence. Removal is revisited if a complete session shows they are unused. Today's denial-only logging cannot show that.

## Migration Plan

- Operators with a protected installation rerun `--container-setup`, or `--container-qualify` after preparation. The old qualification no longer matches the policy digest.
- Rollback: restore revision `antigravity-2026-11-11-v1` (or `-10-v1`) and requalify.
