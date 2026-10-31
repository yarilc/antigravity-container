# Spec Delta

## Purpose

Make Antigravity CLI login usable in a container without a host desktop, keeping credentials only in the dedicated application state area.

## ADDED Requirements

### Requirement: Desktop independent account login
The container SHALL support Google's remote authentication flow with a URL and manual code, providing an internal Secret Service and D-Bus session when required. It SHALL avoid dependencies on the host browser, bus, and keyring.

#### Scenario: First interactive login
- **WHEN** a user starts the CLI with empty state in a terminal without a host display or desktop services
- **THEN** they receive a URL usable in an external browser and can complete login by entering the code in the terminal

### Requirement: Persistent credentials and logout
The container SHALL retain keyring state and authentication profiles in the persistent application area with access limited to the user. It SHALL document their protection properties and respect the CLI's native logout behavior.

#### Scenario: Login reused after restart
- **WHEN** login has completed and the container is removed and restarted with the same state area
- **THEN** the CLI reuses the session while valid without accessing external host credentials

#### Scenario: Logout
- **WHEN** the user runs `/logout` in the CLI authenticated with an account
- **THEN** the session is removed according to Google behavior and does not become authenticated again on restart through automatic host imports

### Requirement: Explicit API key forwarding
The wrapper SHALL forward `GEMINI_API_KEY` only if present in the caller's environment, without reading it from host files or printing its value. It SHALL document the native `modelProvider: gemini` selection in dedicated configuration and SHALL NOT change it implicitly.

#### Scenario: API key configured
- **WHEN** `modelProvider` is `gemini` and the caller exports `GEMINI_API_KEY`
- **THEN** the CLI receives the key and uses the native provider without starting account login

#### Scenario: Incomplete native configuration
- **WHEN** `modelProvider: gemini` is selected but the key is missing
- **THEN** native CLI diagnostics remain visible without falling back to host credentials or printing secrets
