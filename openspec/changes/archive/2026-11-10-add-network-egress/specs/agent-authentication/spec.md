# Spec Delta

## MODIFIED Requirements

### Requirement: Desktop independent account login
The container SHALL support Google's remote authentication flow with a URL and manual code. It SHALL start no D-Bus session, Secret Service or keyring, in any network mode, so that `agy` uses its file token storage. It SHALL avoid dependencies on the host browser, bus and keyring, and SHALL add no port, host-network or Unix-socket exception for sign-in.

#### Scenario: First interactive login
- **WHEN** a user starts the CLI with empty state in a terminal without a host display or desktop services
- **THEN** they receive a URL usable in an external browser and can complete login by entering the code in the terminal

#### Scenario: No bus or keyring in the session
- **WHEN** an account session starts in any mode
- **THEN** no D-Bus or keyring process runs, `DBUS_SESSION_BUS_ADDRESS` is unset, and no keyring passphrase is requested

#### Scenario: Sign-in in provider mode
- **WHEN** a user signs in under the `google-account` profile in provider mode
- **THEN** token exchange reaches only the profile's hosts through the relay, and the browser step stays on the host

### Requirement: Persistent credentials and logout
The container SHALL retain `agy` account tokens and authentication profiles as files in the selected persistent state with access limited to the user. Documentation SHALL state that these files are protected only by Unix permissions, not by a passphrase, and SHALL respect the CLI's native logout behavior. Keyring files from earlier versions SHALL be left in place, unused, with removal guidance.

#### Scenario: Login reused after restart
- **WHEN** login has completed and the container is removed and restarted with the same state area, in the same or another network mode
- **THEN** the CLI reuses the session while valid, refreshing its token when needed, without accessing external host credentials

#### Scenario: Logout
- **WHEN** the user runs `/logout` in the CLI authenticated with an account
- **THEN** the session is removed according to Google behavior and does not become authenticated again on restart through automatic host imports

#### Scenario: Earlier keyring sign-in
- **WHEN** a user who signed in through the removed keyring starts a session
- **THEN** `agy` asks for a new sign-in, and the old keyring files are not read, changed or deleted

### Requirement: Explicit API key forwarding
The wrapper SHALL forward `GEMINI_API_KEY` only if present in the caller's environment, without reading it from host files or printing its value: in unrestricted mode as before, in provider mode only with the `gemini-api` profile, and never in offline mode. It SHALL document the native `modelProvider: gemini` selection in dedicated configuration and SHALL NOT change it implicitly.

#### Scenario: API key configured
- **WHEN** `modelProvider` is `gemini`, the caller exports `GEMINI_API_KEY`, and the mode is unrestricted or provider with `gemini-api`
- **THEN** the CLI receives the key and uses the native provider without starting account login

#### Scenario: Incomplete native configuration
- **WHEN** `modelProvider: gemini` is selected but the key is missing
- **THEN** native CLI diagnostics remain visible without falling back to host credentials or printing secrets

#### Scenario: Key withheld by mode
- **WHEN** the caller exports `GEMINI_API_KEY` in offline mode or in provider mode with `google-account`
- **THEN** the key does not reach the container
