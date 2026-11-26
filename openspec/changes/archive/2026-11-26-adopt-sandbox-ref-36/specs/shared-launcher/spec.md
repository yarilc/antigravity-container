# Spec Delta

## MODIFIED Requirements

### Requirement: Antigravity launcher tests cover only Antigravity's part

Antigravity's launcher behavior SHALL be tested by the shared `tests/test_launcher.py` and `tests/fake_podman.py`, copied unchanged from the reference tag. `tests/test_wrapper.py` SHALL test only Antigravity's hooks, agent data, credential rules per policy profile and shipped policy inventories. An Antigravity launcher case that the shared tests do not cover SHALL be added to the reference first, not kept as a wrapper copy.

#### Scenario: Wrapper runtime tests

- **WHEN** `bash tests/run-runtime.sh --wrapper` runs
- **THEN** it runs both `tests/test_launcher.py` and `tests/test_wrapper.py` against this checkout

#### Scenario: Approval bypass combinations

- **WHEN** tests/test_wrapper.py exercises enabled and disabled ANTIGRAVITY_YOLO in shared and isolated sessions
- **THEN** the agy bypass arguments follow ANTIGRAVITY_YOLO and the existing mount and hardening assertions continue to hold

#### Scenario: Retired host-service opt-in

- **WHEN** the shared launcher fixture checks the old Podman opt-in across network modes
- **THEN** the shared suite covers the early refusal and its migration diagnostic
