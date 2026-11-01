# Spec Delta

## ADDED Requirements

### Requirement: Explicit image build inputs
The image build context SHALL deny local inputs by default and allow only root-level `Containerfile`, `container-entrypoint.sh`, `keyring-session.sh`, and `.containerignore`. New local inputs SHALL require deliberate allowlist changes. Unknown files, credentials, configuration, and nested directories SHALL remain excluded independently of Git tracking or ignore rules.

#### Scenario: Unknown or sensitive files exist
- **WHEN** the build context contains unknown files, `.env`, local authentication/configuration, state, or nested directories
- **THEN** none of those inputs is available to build COPY/ADD operations

#### Scenario: Nested filenames resemble allowed inputs
- **WHEN** nested directories contain files named `Containerfile`, `container-entrypoint.sh`, or `keyring-session.sh`
- **THEN** those nested files remain excluded

#### Scenario: Required helper copies
- **WHEN** the image recipe copies its root-level entrypoint and keyring helper from the restricted context
- **THEN** both copies succeed and retain the executable helper content needed for the existing runtime

#### Scenario: Context inventory
- **WHEN** a real Podman fixture copies all available context inputs into an inspection directory
- **THEN** the resulting inventory contains exactly the four allowed root-level files and no other local inputs
