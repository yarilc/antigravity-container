# Spec Delta

## MODIFIED Requirements

### Requirement: Every session drops capabilities and privilege gains
Every agy and shell container SHALL drop all Linux capabilities and enable container-level no-new-privileges, in every network mode, with or without Podman delegation and independently of `ANTIGRAVITY_YOLO`, in account and Gemini API-key modes. The wrapper SHALL NOT add a capability back or disable no-new-privileges to resolve an incompatibility; such a limitation SHALL be documented instead.

#### Scenario: agy or shell session starts
- **WHEN** an agy or shell session starts in any network mode, with either Podman access setting where allowed
- **THEN** its container has zero inheritable, permitted, effective, bounding and ambient capabilities and no-new-privileges set
- **AND** `agy --version`, Bash, Git and OpenSpec run with caller-owned persistence

#### Scenario: Account keyring works without capabilities
- **WHEN** an account-mode session starts, now without a private D-Bus session or keyring
- **THEN** `agy` stores and reuses its account tokens in files in the private state, without capabilities and with no-new-privileges set
- **AND** if account sign-in cannot work, the wrapper adds no capability, bus or Unix-socket exception, and the limitation is recorded in the validation record

#### Scenario: Gemini API-key mode works without capabilities
- **WHEN** a session uses `modelProvider: gemini` without a terminal
- **THEN** agy starts and reports its native missing-key diagnostic without capabilities or privilege gains

#### Scenario: Delegated Podman client works without capabilities
- **WHEN** an unrestricted session with exact `ANTIGRAVITY_CONTAINER_PODMAN=1` runs `podman info` and creates a child container through the mounted socket
- **THEN** the client succeeds without capabilities in the session container
- **AND** the documentation states that the socket still grants host engine authority beyond these limits
