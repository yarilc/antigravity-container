# Spec Delta

## MODIFIED Requirements

### Requirement: Valid Unix launch endpoint
The wrapper SHALL reject named remote connections, TCP/SSH launch transports, and Unix launch endpoints without a nonempty absolute socket path before querying the launch engine. Paths consisting only of slashes SHALL be rejected, including `unix:///` and `unix:////`. Delegation settings SHALL NOT retarget the launch engine.

#### Scenario: Empty Unix endpoint
- **WHEN** `CONTAINER_HOST` is `unix:///`
- **THEN** startup fails without querying Podman or performing image operations

#### Scenario: Unsupported connection
- **WHEN** a named connection, TCP/SSH endpoint, or relative Unix endpoint is selected
- **THEN** startup fails before querying the launch engine

#### Scenario: Slash-only Unix endpoints
- **WHEN** `CONTAINER_HOST` is `unix:////`, `unix://////`, or another Unix endpoint with no non-slash path component
- **THEN** startup fails before any Podman query or image operation

#### Scenario: Valid absolute socket path
- **WHEN** the launch endpoint names an absolute Unix socket path with a non-slash component
- **THEN** endpoint validation allows the existing engine verification to proceed

## ADDED Requirements

### Requirement: Bounded owned session shutdown
In CLI and shell modes, the wrapper SHALL forward the first handled TERM/INT/HUP to the owned attached session, allow up to five seconds for graceful exit after successful forwarding, and then attempt forced owned-container removal. Shutdown control calls and client termination/reaping SHALL use finite deadlines. Repeated signals SHALL NOT restart shutdown or replace the first signal status.

#### Scenario: Cooperative interruption
- **WHEN** an attached session receives TERM, INT, or HUP through the wrapper and exits cooperatively
- **THEN** the wrapper forwards that signal once, cleans up its owned container, and exits with status 143, 130, or 129 respectively

#### Scenario: Application ignores TERM
- **WHEN** the application ignores forwarded TERM
- **THEN** the wrapper stops its graceful wait after five seconds, attempts forced removal, terminates its client within finite deadlines, and returns 143

#### Scenario: Stalled control call or client
- **WHEN** signal forwarding, forced removal, or client termination stalls
- **THEN** shutdown advances after the relevant finite deadline rather than waiting indefinitely
- **AND** a second handled signal does not extend the deadlines or change the primary status

### Requirement: Ownership through interrupted creation
The wrapper SHALL retain verifiable ownership evidence independently of create-client stdout. On interruption during creation, it SHALL resolve or terminate the pending client within finite deadlines, SHALL NOT attach the interrupted session, and SHALL attempt removal only for a verified owned container. An unresolved creation outcome SHALL produce a diagnostic without deleting containers by guessed name.

#### Scenario: Creation succeeds after interruption
- **WHEN** a handled signal arrives during creation and creation subsequently supplies a valid owned container ID
- **THEN** the wrapper does not start the session, attempts removal using that ID, and returns the first signal's exit status

#### Scenario: Creation stalls after interruption
- **WHEN** creation remains stalled after a handled signal
- **THEN** the wrapper bounds its wait and client termination, handles any recoverable owned ID, and reports an uncertain outcome if ownership cannot be established

#### Scenario: Collision with unrelated container
- **WHEN** creation encounters a preexisting same-name container and supplies no owned ID
- **THEN** the wrapper does not remove that container during retries, interruption, or cleanup

### Requirement: Cleanup diagnostics preserve primary status
The wrapper SHALL report failed or timed-out signal forwarding, owned-container removal, and unresolved cleanup outcomes without replacing the primary application or interruption exit status. A process exit of 125 SHALL remain an application result rather than triggering create-time collision handling. Temporary diagnostics and ownership bookkeeping SHALL be removed on handled exits.

#### Scenario: Removal fails after normal exit
- **WHEN** the application exits with 0, 23, or 125 and owned removal fails or times out
- **THEN** the wrapper reports the owned ID and need for manual cleanup while returning the application status

#### Scenario: Forwarding fails on interruption
- **WHEN** forwarding the first handled signal fails
- **THEN** the wrapper reports the failure, still attempts bounded owned removal, and preserves that signal's exit status

### Requirement: Shutdown prerequisite and user guidance
The wrapper SHALL check for coreutils `timeout` before session creation and document shutdown deadlines, signal statuses, owned-only cleanup, and manual recovery when the engine is unavailable. Wrapper help SHALL remain available without Podman, timeout, or state creation.

#### Scenario: Timeout unavailable
- **WHEN** a session would start but coreutils `timeout` is unavailable
- **THEN** the wrapper fails before container creation with an actionable prerequisite diagnostic

#### Scenario: Help without lifecycle tools
- **WHEN** wrapper help is requested without Podman or timeout
- **THEN** help succeeds without state or engine side effects and describes shutdown behavior
