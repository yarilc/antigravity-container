# Spec Delta

## REMOVED Requirements

### Requirement: Independent opt in permissions

**Reason**: The host delegation setting is retired.

**Migration**: Use the approval-bypass requirements in container-session. Unset the old opt-in and follow the migration guidance in container-session.

### Requirement: Official YOLO mechanism

**Reason**: The approval-bypass contract belongs with session configuration.

**Migration**: Use the approval-bypass requirements in container-session.

### Requirement: Optional host Podman service

**Reason**: Sessions receive their own engine when the library contains images.

**Migration**: Register the required image toolchains and use the private session engine.

### Requirement: Honest isolation contract

**Reason**: Sessions no longer receive host Podman authority.

**Migration**: Use the isolation, approval-bypass and session-engine documentation.

### Requirement: Complete delegation service validation

**Reason**: The delegated endpoint is gone.

**Migration**: Use the verified same-host launch service for host-side launch operations.

### Requirement: Disabled delegation clears service environment

**Reason**: Host engine endpoints stay outside all sessions.

**Migration**: Use the session-only endpoint described in session-container-engine.

### Requirement: Exact opt in migration documentation

**Reason**: Exact opt-in now triggers migration instead of enabling delegation.

**Migration**: Unset the old opt-in and follow the migration guidance in container-session.

### Requirement: Delegation only in unrestricted mode

**Reason**: The host delegation path is retired in every mode.

**Migration**: Register the required image toolchains and use the private session engine.
