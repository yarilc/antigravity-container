# Spec Delta

## MODIFIED Requirements

### Requirement: Separate Google account and Gemini API profiles
Provider mode SHALL require a named protected profile that describes the upstream service rather than the model brand. The base profiles SHALL be:
- `google-account`, allowing only the account hosts that `agy` uses after sign-in, each on port 443;
- `gemini-api`, allowing `generativelanguage.googleapis.com:443`.

Hosts SHALL be measured on the pinned `agy` version. Wildcards such as `*.googleapis.com` or `*.google.com`, and shared cloud storage, SHALL NOT be used.

#### Scenario: API profile
- **WHEN** `gemini-api` is selected
- **THEN** only `generativelanguage.googleapis.com:443` is reachable, and the account hosts, telemetry, update checks and unrelated feature hosts are denied

#### Scenario: Account profile
- **WHEN** `google-account` is selected
- **THEN** only its measured hosts are reachable, and `generativelanguage.googleapis.com`, update hosts and the sandbox Cloud Code variants are denied

#### Scenario: Profile inventory is dated
- **WHEN** a profile is shipped
- **THEN** the policy records the `agy` version, the source documentation date and the measured hosts

#### Scenario: Credential follows the profile
- **WHEN** a provider session uses `google-account` and the host sets `GEMINI_API_KEY`
- **THEN** the key is not passed to the container
- **AND** a `gemini-api` session receives `GEMINI_API_KEY` by name, and offline sessions receive no credential from the wrapper

### Requirement: Optional traffic remains opt-in
Restricted sessions SHALL keep `AGY_CLI_DISABLE_AUTO_UPDATE=true` and SHALL disable telemetry where the tested version supports it, using protected values, set after forwarding, that writable settings and forwarded variables cannot override. Runtime extension, plugin or package installs SHALL stay denied. A missing disable control SHALL NOT broaden the allowlist, except as the profile-scoped telemetry exception allows. Shell mode SHALL keep the same outer restrictions.

#### Scenario: Optional feature attempts outbound access
- **WHEN** a disabled feature, an extension or a writable setting attempts an update, telemetry, package or share request to an unapproved host
- **THEN** the proxy denies it without adding vendor or CDN wildcards

#### Scenario: Protected values cannot be overridden
- **WHEN** the host sets an optional-traffic variable to another value
- **THEN** the session receives the protected value

#### Scenario: Provider-hosted tools
- **WHEN** `agy` uses a provider-hosted tool such as remote web search
- **THEN** documentation states that this network activity happens at the provider, outside the local boundary

### Requirement: Residual exfiltration disclosure
Provider help, README and the network contract SHALL state that destination and SNI binding cannot distinguish the operator's credentials from attacker-supplied ones, so each allowed host can receive workspace data sent with a foreign Gemini API key or Google account. They SHALL name the hosts of each base profile, state that only offline mode removes the channel, and SHALL NOT present host reduction as preventing it.

#### Scenario: Operator reads the provider limits
- **WHEN** an operator reads the provider help, README or network contract
- **THEN** the foreign-credential channel is described for every allowed host of the selected profile: all seven `google-account` hosts, and `generativelanguage.googleapis.com`

#### Scenario: Setup acknowledgement lists the current hosts
- **WHEN** guided setup asks the operator to acknowledge the residual-exfiltration notice for provider mode
- **THEN** the notice lists the same account hosts as the protected policy

## ADDED Requirements

### Requirement: Measured Google account hosts
For `agy` 1.5.3, `google-account` SHALL allow exactly these hosts on port 443:
- `oauth2.googleapis.com`;
- `cloudcode-pa.googleapis.com`;
- `daily-cloudcode-pa.googleapis.com`, the CLI's default Cloud Code endpoint;
- `www.googleapis.com`;
- `aicode.googleapis.com`;
- `www.gstatic.com`;
- `play.googleapis.com`.

They were measured by static inventory and operator-run authenticated sessions. The auto-updater and the sandbox Cloud Code variants SHALL stay denied in every profile.

#### Scenario: Account eligibility check reaches its hosts
- **WHEN** a signed-in `agy` 1.5.3 session under `google-account` runs its eligibility check (`loadCodeAssist` and user information)
- **THEN** the proxy admits the connections to the measured account hosts, and the TLS destination binding applies as for the other allowed hosts

#### Scenario: Unmeasured endpoint variants stay denied
- **WHEN** a `google-account` session connects to `autopush-cloudcode-pa.sandbox.googleapis.com`, `preprod-daily-cloudcode-pa.sandbox.googleapis.com` or the auto-updater
- **THEN** the proxy denies it, and the sanitized diagnostics name the host as `policy-denied`

### Requirement: Profile-scoped telemetry exception
A telemetry host MAY be allowed only in a base profile whose operator-run authenticated session measured it together with that profile's required hosts. It SHALL be disclosed as telemetry, and other profiles SHALL keep denying it. On `agy` 1.5.3 the exception applies only to `play.googleapis.com` under `google-account`.

#### Scenario: Telemetry follows the profile
- **WHEN** `agy` 1.5.3 sends telemetry to `play.googleapis.com`
- **THEN** it is admitted under `google-account` and denied under `gemini-api`
- **AND** provider help, README and the network contract state that account-mode telemetry reaches Google
