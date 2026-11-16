# Language conventions

- Write all project documentation in English, including OpenSpec proposals, designs, specifications, tasks, and archived artifacts.
- Communicate with the user in Italian in chat.

# Security constraints

- Every session drops all capabilities and sets no-new-privileges. Never add capabilities back, add `--privileged` or disable no-new-privileges to fix a tool; record the limitation in `docs/validation.md` instead.
- Sessions have validated, inspected memory, CPU and process budgets (`ANTIGRAVITY_CONTAINER_MEMORY_LIMIT`, `ANTIGRAVITY_CONTAINER_CPU_LIMIT`, `ANTIGRAVITY_CONTAINER_PIDS_LIMIT`; defaults 4g, 2, 512) and an optional `ANTIGRAVITY_CONTAINER_RUN_TIMEOUT`. No value disables a budget. A budget whose cgroup v2 controller the rootless engine does not delegate (`Host.CgroupControllers`) is omitted, announced and bound into the qualification identity; never require host changes to delegate it.
- Sessions keep automatic read-only tmpfs provisioning so the engine provides `/dev` and a PTY-capable `devpts`, with an empty read-only `/dev/shm` and `/run/secrets` mask; never reintroduce `--read-only-tmpfs=false`, an explicit `devpts` mount (it gets `ptmxmode=000`) or a writable `/dev/shm`.
- The recipe fetches Debian packages over verified HTTPS only; the host CA reaches the apt and agy download steps only as the `build-ca` secret. It creates `/workspace` in a build step: never declare a `WORKDIR` that no build step creates.
- Sensitive workspace roots (`/`, system directories, `/tmp`, the physical home and `/mnt/<letter>`) are refused unless exactly `ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1`.
- Image inputs (base digest, `agy` release artifact and SHA-512 per architecture, OpenSpec version) are pinned in `Containerfile` and change only through the README update procedure.
- Run `tests/test_wrapper.py` and `tests/test_image_pins.py` without credentials; real-engine checks use `bash tests/run-runtime.sh`.

# Network sandbox

- Every launch needs an explicit `ANTIGRAVITY_CONTAINER_NETWORK` (`offline`, `provider` or `unrestricted`); every image build and proxy pull needs exact `ANTIGRAVITY_CONTAINER_MAINTENANCE=1`. Host Podman delegation is rejected in restricted modes.
- `agent/profile.json` and `agent/policies/default.json` hold every Antigravity-specific value used by the shared network code (identity, images, state layout, the `google-account` and `gemini-api` profiles). Restricted preparation, proxy lifecycle and restricted container arguments come from `network/session.py` (`prepare`, `start`, `agent-args`, `stop`); never re-implement them in the wrapper.
- `network/`, `setup/` and the shared tests (`sandbox_profile.py`, `test_alignment.py`, `test_setup.py`, `test_agent_profile.py`, `test_network_policy.py`, `test_mux.py`, `test_tls_client_hello.py`, `test_tls_proxy.py`, `test_platform.py`, `test_qualification.py`, `test_guard.py`, `test_session.py`, `test_network_feasibility.py`, `test_toolchains.py` and their fixtures) are copied unchanged from `sandbox-container` at tag `sandbox-ref-21`. Never edit them here, and never add a profile identifier (`antigravity`, `agy`, `gemini`) to them. Fix a defect in `sandbox-container` first, then copy the files again and update `tests/test_reference_copy.py`.
- The shared `setup/toolchains.py` manages the operator toolchain library, mounted read-only at `/toolchains`; the launcher owns only its dispatch, mount and environment, and passes the toolchain environment before `AGY_CLI_DISABLE_AUTO_UPDATE=true`.
- There is no D-Bus session or keyring in the container: `agy` keeps account tokens in files in the private state home. Never add a Unix-socket exception to the guard for a bus or another tool.
- New users start with `bash ./antigravity-container.sh --container-setup`; the `account` method declares empty `login_args`, so setup offers sign-in inside the interactive `agy`.
- Run the suites through `bash tests/run-runtime.sh` with `--wrapper`, `--shared`, `--setup`, `--setup-runtime`, `--guard`, `--guard-idle`, `--network-feasibility`, `--network-policy`, `--mux`, `--qualification`, `--network` or no option (unrestricted runtime suite). Automated tests never use real credentials; authenticated Google account and Gemini API-key checks are operator-run.
