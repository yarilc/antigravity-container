# Spec Delta

## MODIFIED Requirements

### Requirement: Desktop independent account login
The container SHALL support Google's remote authentication flow with a URL and manual code. It SHALL start no D-Bus session, Secret Service or keyring, in any network mode, so that `agy` uses its file token storage. It SHALL avoid dependencies on the host browser, bus and keyring, and SHALL add no port, host-network or Unix-socket exception for sign-in. Guided setup SHALL be able to start this sign-in through the installed wrapper.

#### Scenario: First interactive login
- **WHEN** a user starts the CLI with empty state in a terminal without a host display or desktop services
- **THEN** they receive a URL usable in an external browser and can complete login by entering the code in the terminal

#### Scenario: No bus or keyring in the session
- **WHEN** an account session starts in any mode
- **THEN** no D-Bus or keyring process runs, `DBUS_SESSION_BUS_ADDRESS` is unset, and no keyring passphrase is requested

#### Scenario: Sign-in in provider mode
- **WHEN** a user signs in under the `google-account` profile in provider mode
- **THEN** token exchange reaches only the profile's hosts through the relay, and the browser step stays on the host

#### Scenario: Sign-in started from setup
- **WHEN** the operator selects the `account` method in `--container-setup` and accepts the sign-in offer
- **THEN** the installed wrapper starts `agy` interactively with the saved mode and policies, and the operator completes the URL and code flow there
- **AND** the tokens are stored in the selected state as for any other interactive sign-in
