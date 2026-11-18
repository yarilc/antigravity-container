## MODIFIED Requirements

### Requirement: Complete delegation service validation
The wrapper SHALL require one complete delegation response containing verified rootless `true` and a nonempty absolute reported host socket path. A reported path given as a `unix://` URL SHALL be reduced to its pathname before validation. It SHALL reject missing values, invalid rootless values, extra response records, and failed service queries before image inspection, build, or container creation. Paths containing spaces SHALL remain intact. The host socket path, after removing a `unix://` prefix, SHALL NOT consist only of slash characters. When that path exists in the wrapper's own filesystem namespace, it SHALL be a Unix socket; a path the wrapper cannot see is accepted as the remapped socket of a containerized wrapper, whose answer stays trusted. Guided setup SHALL apply the same checks.

#### Scenario: Invalid delegation response
- **WHEN** the selected service query fails or returns empty, incomplete, rootful, malformed, relative-path, or multiline output
- **THEN** startup fails before image operations or container creation with a relevant diagnostic

#### Scenario: Host socket path contains spaces
- **WHEN** the service reports a valid absolute socket path containing spaces in a single response record
- **THEN** the bind source preserves that path intact

#### Scenario: Podman 5 reports a socket URL
- **WHEN** the service reports `true unix:///run/user/1000/podman/podman.sock`
- **THEN** the wrapper binds `/run/user/1000/podman/podman.sock` to `/run/podman/podman.sock`

#### Scenario: Invalid socket URL
- **WHEN** the reported value is `unix://` followed by an empty, relative or slash-only pathname, or a bare slash-only path such as `/` or `//`
- **THEN** startup fails before image operations or container creation, and the host root is never mounted

#### Scenario: Host socket path is not a socket
- **WHEN** the service reports a host socket path that exists in the wrapper's namespace as a directory, a regular file, a dangling link or another non-socket
- **THEN** startup fails before image operations or container creation naming the reported path, and nothing is mounted from it
