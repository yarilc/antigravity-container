# Spec Delta

## ADDED Requirements

### Requirement: Delegation only in unrestricted mode
`ANTIGRAVITY_CONTAINER_PODMAN=1` SHALL be accepted only with explicit `ANTIGRAVITY_CONTAINER_NETWORK=unrestricted`. In offline and provider modes it SHALL fail before image or resource operations, explaining that the host API bypasses egress enforcement. Shell, YOLO and native permission settings SHALL NOT change this.

#### Scenario: Delegation requested in a restricted mode
- **WHEN** the wrapper starts in offline or provider mode with `ANTIGRAVITY_CONTAINER_PODMAN=1`, in `agy` or shell mode, with or without YOLO
- **THEN** it exits nonzero before image or resource operations and names explicit unrestricted mode as the only mode with delegation

#### Scenario: Delegation in unrestricted mode
- **WHEN** the wrapper starts in unrestricted mode with `ANTIGRAVITY_CONTAINER_PODMAN=1`
- **THEN** delegation behaves as before this change
