# Tasks

## 1. Copy the shared components from `sandbox-ref-8`

- [x] 1.1 Create branch `add-network-egress` from `main`. Use `git -C ../claude-container archive sandbox-ref-8` to unpack:
  - `network/`, without `bin/` and `__pycache__`;
  - `setup/diagnostics.py`;
  - the shared tests listed in that tag's `tests/test_alignment.py`, except `test_alignment.py` and `test_setup.py`.

  Add `__pycache__/` and `network/bin/` to `.gitignore`. Verify with `diff -r` against the tag tree: no differences.
- [x] 1.2 Add `tests/test_reference_copy.py`, reusing Pi's agent-neutral version from its `add-network-egress`, with the manifest moved to `sandbox-ref-8`. Check that `antigravity`, `agy` and `gemini` occur in no shared file; drop and record any that do. Verify that the test passes, and that it fails on an injected byte change and on an injected identifier.

## 2. Measure the Antigravity-specific unknowns

- [x] 2.1 Build a static and credential-free inventory of `agy` 1.5.3 in the image, and confirm it with a logging CONNECT proxy and dummy credentials. Record in `docs/validation.md`:
  - the account sign-in, token exchange, refresh and model-service hosts;
  - the Gemini API host;
  - the update and telemetry hosts;
  - whether a non-interactive sign-in command exists.
- [x] 2.2 Without D-Bus (`DBUS_SESSION_BUS_ADDRESS` unset, no keyring packages used), check with a disposable state home that `agy`:
  - selects file token storage, and records where it writes and with which modes;
  - starts the URL/code sign-in with the `SSH_CONNECTION` marker, up to the code prompt;
  - shows no keyring prompt or error.

  With synthetic token files, also check two concurrent sessions sharing one state for corruption. Record the result. If `agy` needs a bus, stop and report to the operator.
- [x] 2.3 Measure the telemetry and update controls (`AGY_CLI_DISABLE_AUTO_UPDATE`, telemetry settings, any environment control) against a logging proxy. Record which requests each control suppresses, and whether writable settings can re-enable them. Record the chosen protected values.
- [x] 2.4 With the synthetic TLS fixture (a `CA:FALSE`, `serverAuth` leaf certificate) and a local CONNECT proxy, check whether `agy` honors:
  - `HTTPS_PROXY`/`https_proxy` and the loopback `NO_PROXY` for HTTPS, streaming and token refresh;
  - `SSL_CERT_FILE` and/or `AGY_CA_CERT` for trust.

  Record any transport that bypasses the proxy, which must fail closed.
- [x] 2.5 Build the guard (task 3.2), then run in offline mode under the guard, with `--cap-drop=all` and no-new-privileges:
  - the `agy` TUI in a PTY;
  - `agy -p` against a loopback stub;
  - a command through the Bubblewrap terminal sandbox;
  - the language server and sidecar startup.

  Record the Unix-socket, bus or `bwrap` dependencies and the documented outcome. If the core CLI needs a Unix listener, stop and report to the operator.
- [x] 2.6 Run the guard runtime fixtures with Antigravity's layout:
  - the dedicated home, the shared `.gemini` bind below a tmpfs home and an isolated home;
  - exec `/tmp`, noexec `/run` and `/var/tmp`, all mode `1777`.

  Verify that layout validation passes. If it fails, stop and fix the shared code in Claude first.

## 3. Agent profile, policy and operator artifacts

- [x] 3.1 Write `agent/profile.json` from design.md, with the hosts and sign-in arguments measured in task 2.1. Write `agent/policies/default.json` with:
  - `google-account` and `gemini-api`;
  - revision `antigravity-2026-11-10-v1`, `source_date` and `sources`;
  - `tested.cli` `1.5.3`, with authentication marked unverified.

  Verify the profile query, the policy against the profile rules, and `tests/test_agent_profile.py` and `tests/test_network_policy.py`.
- [x] 3.2 Tag or build `localhost/antigravity-guard-toolchain:development` from `network/guard-build.Containerfile`. Package the guard with `ANTIGRAVITY_CONTAINER_MAINTENANCE=1 bash network/build-guard.sh` into a native directory. Build `localhost/antigravity-egress` from `network/Containerfile`. Verify that the guard SHA-256 equals the guard of the other wrappers, and that the guard runtime mode passes.
- [x] 3.3 Run the copied shared suites. They must all pass without edits to shared files.

## 4. Runtime image, entrypoint and test runner

- [x] 4.1 Update the image:
  - remove `dbus`, `gnome-keyring`, `libsecret-1-0` and `libsecret-tools`;
  - delete `keyring-session.sh`, and reduce `container-entrypoint.sh` to the help and version shortcut, the scoped `SSH_CONNECTION` marker and `exec agy`;
  - add `COPY network/relay.py network/mux.py /opt/sandbox-egress/`;
  - restrict `.containerignore` to the five inputs.

  Extend `tests/test_image_pins.py` so that `AGY_VERSION` must equal the policy's `tested.cli`. Verify:
  - the pin tests, including an injected divergence;
  - the five-file build-context probe;
  - `image-smoke.sh` with the new toolset (keyring daemons absent);
  - a rebuilt image whose `agy --version` reports 1.5.3.
- [x] 4.2 Move the inline fake engine of `tests/test_wrapper.py` to `tests/fake_podman.py`, adapted from Pi. Extend `tests/run-runtime.sh` with the Pi mode set:
  - `--wrapper` and `--shared`;
  - `--network-feasibility`, `--network-policy`, `--network`, `--mux`, `--guard`, `--guard-idle` and `--qualification`;
  - the default runtime mode.

  Keep the `agy` image as the runner. Verify that each mode starts and reports its suite.

## 5. Wrapper integration

- [x] 5.1 Mode admission:
  - parse `ANTIGRAVITY_CONTAINER_NETWORK`; an unset or empty value stops before engine calls, naming the three values and `unrestricted` as the previous behavior;
  - unknown values fail;
  - `ANTIGRAVITY_CONTAINER_PODMAN=1` is rejected in restricted modes;
  - help gains the new options, variables, migration notes and the provider disclosure.

  Verify with `test_wrapper.py` cases across `agy`, shell, build, worktree and YOLO.
- [x] 5.2 Maintenance gate: the automatic build and `--container-build` require the exact `ANTIGRAVITY_CONTAINER_MAINTENANCE=1`. Restricted preconditions are checked before image operations. Verify with fake-engine cases for:
  - present and absent images;
  - an explicit build, with and without authorization;
  - an inspection error;
  - an invalid policy.
- [x] 5.3 State and CA:
  - unset state as the dedicated home, nonempty as isolated, empty as shared `~/.gemini`;
  - the `ANTIGRAVITY_CONTAINER_CONFIG_DIR` override, its conflict with a nonempty state directory and its session value;
  - lexical checks before the engine and creation after it, with overlap checks;
  - `ANTIGRAVITY_CONTAINER_TRUST_HOST_CA` and `ANTIGRAVITY_CONTAINER_CA_BUNDLE`, giving a read-only `/antigravity-home/ca/bundle.pem` plus the four variables (and `AGY_CA_CERT` if task 2.4 requires it), with the private `ca` parent in writable state.

  Verify with `test_wrapper.py` cases.
- [x] 5.4 Restricted forwarding:
  - no host proxy or CA variables;
  - offline forwards no key;
  - provider forwards `GEMINI_API_KEY` only with `gemini-api`;
  - `DBUS_SESSION_BUS_ADDRESS` is unset in every mode;
  - the protected optional-traffic values (task 2.3) follow forwarding.

  Unrestricted forwarding is unchanged apart from the bus variable. Verify with `test_wrapper.py` cases for both profiles.
- [x] 5.5 Restricted preparation, in the reference order:
  1. platform queries;
  2. `session.py prepare` with the workspace, the state sources and `/antigravity-home`;
  3. the immutable image ID;
  4. proxy image acquisition under maintenance and by digest;
  5. `qualify.py check`;
  6. `session.py start`, `agent-args` and container creation;
  7. `session.py stop` within the remaining budget.

  The guard replaces the image entrypoint and then runs `antigravity-entrypoint`. Verify with fake-engine cases for order, arguments, interrupted start, exit status and owned cleanup.
- [x] 5.6 Add `--container-qualify` (alone) and `--container-qualify-probe` using `network/qualify.py`. Verify with fake-engine cases and `tests/test_qualification.py`.
- [x] 5.7 Unrestricted regression: the existing `test_wrapper.py`, `test_runtime.py` and `image-smoke.sh` cases pass, apart from:
  - the added mode and maintenance variables;
  - the removed keyring, whose cases are replaced by file-token and no-bus cases.

## 6. Runtime acceptance with real rootless Podman

- [x] 6.1 Add `tests/test_network_runtime.py` and `tests/network_tls_fixture.py`, adapted from Pi. Use Antigravity names, controlled profiles for the two base profiles and a synthetic streaming endpoint. Verify that every runner mode passes on the WSL target.
- [x] 6.2 Offline acceptance through `antigravity-container.sh` after `--container-qualify`:
  - IPv4, IPv6, DNS and UDP egress and host and abstract sockets are denied;
  - loopback and connected pairs work;
  - file ownership is preserved;
  - the `agy` TUI starts and quits in a PTY.
- [x] 6.3 Provider acceptance with controlled fixtures:
  - matching CONNECT and SNI pass, and mismatched SNI is rejected;
  - denied authority, redirect, IP-literal and deceptive-suffix requests fail;
  - proxy loss fails closed;
  - CA trust off and on behave as specified;
  - the proxy budgets and hardening are verified;
  - a real `agy -p` run against the synthetic endpoint streams a response through the relay, if task 2.4 found a way to point `agy` at a synthetic endpoint without a broader policy; otherwise the CONNECT and TLS path of `agy` is verified with the fixture and the limitation is recorded.
- [x] 6.4 Concurrency and cleanup: run two concurrent provider sessions with different policies and check that ownership is distinct. Afterward nothing labeled `io.antigravity-container` remains. Pre-existing containers are untouched.

## 7. Documentation and evidence

- [x] 7.1 Update the README with:
  - modes and migration (maintenance, keyring removal and new sign-in, state choices);
  - the prerequisites and `--container-qualify`;
  - the operator build inputs;
  - the two profiles and the credential rules;
  - the residual exfiltration disclosure;
  - the qualification behaviors;
  - the terminal sandbox and tool compatibility;
  - token storage protection and old keyring removal.

  Update the wrapper help and `AGENTS.md`. Add `CHANGELOG.md` and `docs/network-contract.md`, modeled on Pi. Verify with markdownlint and `git diff --check`.
- [x] 7.2 Record in `docs/validation.md`:
  - the target, Podman version, guard digest, image IDs and results by mode;
  - the measurements from task group 2;
  - the operator-run authenticated checks, marked pending until all Waves are complete.
- [x] 7.3 Final verification:
  - `bash -n` and ShellCheck;
  - all runner modes and `image-smoke.sh`;
  - `openspec validate add-network-egress --strict`;
  - `git diff --check`.

  Update `todo.md` (N01–N14, C01–C08, C10, C12) with status and evidence. Record that the keyring blocker is resolved by the operator decision of 2026-11-10.

## Workflow follow-up

- `/opsx:archive`, then commit and merge into `main`; the user pushes.
- Next change: `add-container-setup` for Antigravity (C09, C11, the parity row).
- Operator-run authenticated checks after all Waves.
