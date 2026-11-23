# Design

## Context

Antigravity adopted `sandbox-ref-25` on 2026-11-18 and pinned OpenSpec 2.0.0
the same day, with `agy` 1.5.3. Its runtime and egress images are its own and
stay as they are. The tag changes no Antigravity build input.

**Dry run.** `tools/propagate.py ../antigravity-container sandbox-ref-25
sandbox-ref-28` (2026-11-22) gave this plan:

- **Update:**
  - `launcher/core.sh`;
  - `network/README.md`, `agent_budgets.py`, `control.py`, `guard.c`,
    `proxy_hardening.py`, `qualification_probe.py`,
    `qualification_records.py` and `session.py`;
  - `setup/common.py`, `launch.py`, `setup.py` and `smoke.py`;
  - `tests/fake_podman.py` and both fixture `launcher.sh`;
  - `tests/test_alignment.py`, `test_guard.py`, `test_launcher.py`,
    `test_qualification.py`, `test_session.py` and `test_setup.py`.
- **Add:**
  - the five `launcher/windows/` files;
  - `tests/test_windows_bootstrap.py` and `tests/test_windows_enter.py`;
  - `tests/windows/shim_tests.ps1`.
- **Rewrite:** 1 reference each in `AGENTS.md` and `docs/setup.md`, and 6 in
  `docs/network-contract.md`. The 6 include the "Adopted `sandbox-ref-25`"
  cells of the OpenCode and Pi rows. The README names no tag.
- **Move:** the manifest to `ba1ef14`.
- **Runner modes listed:** `--shared`, `--setup`, `--setup-runtime`,
  `--qualification`, `--guard` and `--network`.

**ShellCheck today.** `tools/shellcheck.sh ../antigravity-container` reports
findings in two groups:

- `launcher/core.sh` (14) and both fixtures (32 and 25), which the tag
  replaces;
- `agent/launcher.sh`: 25 `SC2034` and 1 `SC2148`. Antigravity's agent part has
  no `shell=bash` directive.

No other tracked script has a finding.

**Antigravity's own tests.**
- `tests/test_setup_wrapper.py` is byte for byte the file Codex had before its
  adoption. Claude and Codex now share one adapted version: a fake
  `systemctl` for setup without a launch service, and the reference
  budget-notice test.
- In `tests/test_runtime.py`, `test_effective_hardening_and_budgets` asserts
  cgroup limits for all three budgets. It also starts 80 children under a
  process budget of 32. Codex changed this test the same way as Claude.
- No other Antigravity test reads the engine's controllers or cgroup manager.
- `test_build_context_allows_only_required_inputs` copies
  `container-entrypoint.sh` into its build context with `shutil.copyfile`,
  which drops the executable bit, then requires `test -x` in the image. It
  passed on 2026-11-18 on another host. On this runner it fails on `main` too,
  with the old and the rebuilt image, so the tag does not cause it.

**Antigravity specifics on Windows.** The shim reads every wrapper-specific
value from `agent/profile.json`:
- `native.command` is `agy`, so `tools/windows-validate.ps1` runs its cases
  with `--container-shell`.
- The `account` method declares empty `login_args`. Sign-in therefore happens
  inside an interactive `agy` session. The container entrypoint requests
  Google's remote flow, with a URL and a code. Setup started from Windows
  already names `antigravity-container.ps1` as the next step, with no
  arguments. The shared `test_windows_entry_names_the_powershell_authentication_steps`
  covers this case with an interactive method.
- The `gemini` method reads `GEMINI_API_KEY`, which the shim forwards. A key
  alone does not select the provider. `modelProvider: gemini` must be in the
  settings, or in a session-only `--settings` argument.
- `native.config_dir_env` is `ANTIGRAVITY_CONTAINER_CONFIG_DIR`. The shim
  forwards it only when it holds a distribution path. Shared state is the
  machine user's `~/.gemini`.
- `agy`'s internal sandbox (`--sandbox`) failed on Linux with Podman's standard
  seccomp profile (`sethostname`). The guard also stops Bubblewrap in
  restricted modes. Nobody has measured it in a Podman machine.

**Images.** The runner's engine has no `localhost/antigravity-cli:latest`. It
has only two `setup-*` tags of one image, from 2026-11-18, with
`build-inputs-hash` `d8e79c17…`. That is the hash from before the OpenSpec
2.0.0 pin, whose record gives `e28d7bab…`. The guard toolchain exists only
under `setup-*` tags.

## Goals / Non-Goals

**Goals:**

- Antigravity runs on the `sandbox-ref-28` shared files. Beyond the ShellCheck
  header, the two adapted tests and the build-context test fix, no
  Antigravity-specific code changes.
- Antigravity works from Windows on a Podman machine, in provider mode, with
  the Google sign-in, token reuse and the installer.
- The parity tables of the reference and the five wrappers state the same rows.

**Non-Goals:**

- OpenCode and Pi, which adopt the tag in their own changes.
- Delegation on Windows and macOS.
- `agy`'s internal sandbox on Windows. The Linux limitation and its policy stay
  as they are.
- A real-key Gemini check when no key is available.

## Decisions

1. **Adopt with the tool, from `sandbox-ref-25` directly.** Commit this change
   directory on `main`, then run the dry run and `--apply`. `--apply` creates
   `adopt-sandbox-ref-28`. This repeats the Claude and Codex adoptions.
   Adopting `sandbox-ref-26` and `sandbox-ref-27` on their own adds runs and
   covers nothing more.
2. **Hand-copied files on the same branch.**
   - `sandbox-container.ps1` becomes `antigravity-container.ps1`, byte for
     byte.
   - `.gitattributes` is copied. Then, on a clean tree,
     `git rm -r -q --cached . && git reset --hard` rewrites the working files.
   - The shared alignment tests then check the entry, ASCII and line endings.
3. **Antigravity's agent part.** Add the reference header to
   `agent/launcher.sh`, as Claude and Codex did:
   - the comment that the core sources the file;
   - `# shellcheck shell=bash disable=SC2034,SC2154`.

   No hook changes. `SC2154` has no finding today, but the same header in
   every wrapper keeps the agent parts comparable. Listing each variable or
   exporting the data instead would make Antigravity's header differ for no
   gain.
4. **Antigravity's own tests.**
   - `tests/test_setup_wrapper.py` takes the current Claude and Codex file
     byte for byte, because the files matched before. Copying it keeps them
     comparable at the next adoption.
   - `tests/test_runtime.py` takes Codex's approach:
     - an `engine_budgets()` helper reads the delegated controllers and the
       process mechanism through `network/agent_budgets.py`, the launcher's
       rule;
     - the assertions follow that result, with the `ANTIGRAVITY_CONTAINER_*`
       names and the `agy --version` check kept;
     - the process-budget probe uses a budget of 128 and 200 children, and is
       skipped when no mechanism applies.
   - `test_build_context_allows_only_required_inputs` copies its inputs with
     `shutil.copy2`, which keeps the entrypoint's mode. The operator chose to
     fix this pre-existing test defect here, so the default suite passes on
     this runner.
   - Any other failure caused by a shared behavior change is fixed in
     Antigravity's test on the same branch. A failure in shared code pauses
     the change for a reference fix and a new tag.
5. **Parity rows after `--apply`.**
   - The tool rewrites every `sandbox-ref-25` in `docs/network-contract.md`,
     including the rows of the wrappers that stay on it.
   - After `--apply`, restore the OpenCode and Pi rows from `main`. Check that
     the reference, Claude and Codex rows equal `sandbox-container`'s.
   - Task 4.1 sets Antigravity's own row.
6. **Docs adapted, not copied.** The Codex text for the shared behavior moves
   into Antigravity's layout, which has no host CA section of its own.
   - **`README.md`:**
     - a new `## Windows with Podman machine` section before
       `## Mounts, worktrees, and identity`, with
       `### Trusting a host CA on Windows` and `### Install as a command`. It
       covers:
       - the provider default and the `account` method;
       - the sign-in inside an interactive `agy` session, with the URL opened
         in a Windows browser. The tokens stay in the machine user's
         `~/.gemini`, separate from Antigravity or Gemini CLI on Windows;
       - the `gemini` method: `$env:GEMINI_API_KEY`, and `modelProvider:
         gemini` set in the machine's settings through `--container-shell`,
         or for one session with `--settings`;
       - `antigravity-container.ps1` and the `ANTIGRAVITY_CONTAINER_*`
         variables, with distribution paths for the state variables;
       - the Windows limits, with Bitdefender;
       - `agy`'s internal sandbox: not measured on the machine, so omit
         `--sandbox` there as on Linux;
     - host CA trust on Windows points to the `ANTIGRAVITY_CONTAINER_TRUST_HOST_CA`
       and `ANTIGRAVITY_CONTAINER_CA_BUNDLE` rows of `## Environment`;
     - the rejected Podman Machine connection sentence points to the Windows
       section;
     - the restricted sessions' guard as the confined init, next to the
       `--init` of unrestricted sessions;
     - in `### Session hardening, budgets and lifetime`:
       - the `systemd` and `cgroupfs` managers;
       - the process rlimit fallback, with its risk;
       - the Windows sensitive folders.
   - **`docs/setup.md`:**
     - the Windows setup and the authentication steps from Windows;
     - setup without a launch service;
     - the carriage-return check;
     - candidate tags;
     - the service endpoint for restricted modes;
     - the budget plan, replacing the stale statement that the controllers
       must be delegated.
   - **`AGENTS.md`:** `antigravity-container.ps1`, the Windows files, the
     ShellCheck and PowerShell checks, the Windows sensitive roots, and the
     cgroup manager and rlimit rule.
7. **Validation on this runner,** in Antigravity's checkout:
   - `python3 -m unittest tests.test_reference_copy tests.test_alignment` next
     to the `sandbox-container` checkout, with the sibling check not skipped;
   - the unit discovery in the disposable test container;
   - `bash tests/run-runtime.sh` in each of these modes:
     - `--wrapper`, `--shared`, `--setup` and `--setup-runtime`;
     - `--qualification`, `--guard` and `--network`;
     - the default runtime run;
   - from `sandbox-container`, `bash tools/shellcheck.sh ../antigravity-container`
     and `bash tools/powershell.sh ../antigravity-container`;
   - `git diff --check`.

   The runner's images are stale, so rebuild them first with
   `ANTIGRAVITY_CONTAINER_MAINTENANCE=1 antigravity-container.sh
   --container-build`. Behind the runner's TLS interception, the build also
   needs `ANTIGRAVITY_CONTAINER_TRUST_HOST_CA=1` and the session's CA bundle,
   as for Codex. For `--guard`, tag the guard toolchain as `development` or
   pass `SANDBOX_GUARD_TOOLCHAIN`. Record the image and the toolchain.
8. **Validation on Windows.** The operator gets a bundle with snapshots of
   `antigravity-container` and `sandbox-container`, and these steps:
   1. `.\antigravity-container.ps1 --container-setup` with the defaults:
      provider networking and the `account` method. Decline the sign-in and
      check that the next step names `antigravity-container.ps1` with no
      distribution path. The first setup builds the Antigravity images in the
      machine.
   2. The sign-in and a session, from a project folder:
      `antigravity-container.ps1`. Choose Google sign-in, open the URL in a
      Windows browser and enter the code in the window. Then one prompt that
      reads a file of the folder, which runs a tool, then Ctrl+C. Note the
      exit status. `podman ps -a` must list no container of the session.
   3. Token reuse: a second `antigravity-container.ps1` session must start
      signed in, without a new sign-in.
   4. `sandbox-container\tools\windows-validate.ps1 -Checkout
      C:\Work\antigravity-container`:
      - on Windows PowerShell 5.1 with `-Install -StopMachine`;
      - on PowerShell 7 without them.
   5. The `gemini` method: setup names `$env:GEMINI_API_KEY`. Then:
      - with a real key, `antigravity-container.ps1 -p 'Say hello'
        --print-timeout 60s --settings '{"modelProvider":"gemini"}'` must
        answer;
      - without one, with a dummy key, `--container-shell` shows that the
        variable reaches the session, and the same `-p` call must end with
        Gemini's API key error, not a proxy or certificate error.

      Then setup again with the `account` method, so the machine ends as
      before.

   Each summary is copied after its run. A failed step pauses the change for a
   decision between a documented Windows limit and a fix.
9. **Parity rows across repositories.**
   - Antigravity's row names "Adopted `sandbox-ref-28`", with this adoption's
     results.
   - After the merge, Antigravity's row is copied into `sandbox-container` and
     the four other wrappers, one commit on `main` each.
   - The rows of the wrappers still on `sandbox-ref-25` stay as they are.

## Risks / Trade-offs

- [Three tags at once widen the validation surface.] → Every runner mode that
  the tool lists runs, including `--guard`, plus `--wrapper` and the default
  runtime run.
- [The image rebuild on the runner may pull a changed Debian package set.] →
  The pins are unchanged, and the build verifies the `agy` checksum. The
  record names the rebuilt image.
- [The Google remote flow may behave differently in a PowerShell window, for
  example when the window wraps the URL.] → Windows step 2 measures it. A
  sign-in failure that the machine did not cause is recorded, not fixed here.
- [The first build in the machine downloads `agy` from Google storage through
  the TLS interception.] → The bundle README requires
  `podman machine set --import-native-ca` and the host CA answer, as for Codex.
- [Installed qualification reports no longer match.] → After the merge, the
  operator reruns `--container-setup` on the Linux hosts and on Windows.
- [The tool rewrites rows of wrappers it does not adopt.] → Decision 5 restores
  them before the commit. Task 4.2 checks them in every repository.
- [Docs drift from the other wrappers.] → The adapted sections follow Codex's
  structure, so a later adoption can compare them section by section.
