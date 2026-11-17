## MODIFIED Requirements

### Requirement: Explicit API key forwarding
The wrapper SHALL forward `GEMINI_API_KEY` only if present in the caller's environment, without reading it from host files or printing its value: in unrestricted mode only when `ANTIGRAVITY_CONTAINER_ENV_VARS` lists it, in provider mode only with the `gemini-api` profile, and never in offline mode. It SHALL document the native `modelProvider: gemini` selection in dedicated configuration and SHALL NOT change it implicitly.

#### Scenario: API key configured
- **WHEN** `modelProvider` is `gemini`, the caller exports `GEMINI_API_KEY`, and the mode is provider with `gemini-api`, or unrestricted with `ANTIGRAVITY_CONTAINER_ENV_VARS=GEMINI_API_KEY`
- **THEN** the CLI receives the key and uses the native provider without starting account login

#### Scenario: Incomplete native configuration
- **WHEN** `modelProvider: gemini` is selected but the key is missing
- **THEN** native CLI diagnostics remain visible without falling back to host credentials or printing secrets

#### Scenario: Key withheld by mode
- **WHEN** the caller exports `GEMINI_API_KEY` in offline mode, in provider mode with `google-account` (also when `ANTIGRAVITY_CONTAINER_ENV_VARS` lists it), or in unrestricted mode without listing it
- **THEN** the key does not reach the container
