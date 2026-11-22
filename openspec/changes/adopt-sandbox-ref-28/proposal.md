# Proposal

## Why

Antigravity runs on `sandbox-ref-25`. Claude and Codex adopted
`sandbox-ref-28` on 2026-11-22. The three tags since `sandbox-ref-25` bring:

- **`sandbox-ref-26`:** the budgets rule.
  - Only the `systemd` cgroup manager delegates controllers.
  - Without the `pids` controller, the process budget falls back to the
    process rlimit.
  - The shared launcher files pass ShellCheck.
- **`sandbox-ref-27`:** Windows support on a Podman machine.
  - The PowerShell entry, the shim, the bootstrap, the namespace helper and
    the installer.
  - Offline and provider networking in the machine, with the guard as the
    confined init of restricted sessions.
  - Setup changes for the machine, and API key variables forwarded from
    Windows.
- **`sandbox-ref-28`:** setup started from Windows names the sign-in and API
  key steps for PowerShell.

Without these tags, Antigravity has two gaps:

- On a `cgroupfs` engine, which applies no budget, Antigravity reports the
  budgets as enforced.
- Antigravity cannot run from Windows.

## What Changes

- **Adopt the tag.** `tools/propagate.py` adopts `sandbox-ref-28` from
  `sandbox-ref-25`. The dry run of 2026-11-22 gave this plan:
  - update 22 shared files;
  - add 8: the `launcher/windows/` files and the Windows tests;
  - rewrite 8 tag references: 6 in `docs/network-contract.md`, 1 each in
    `AGENTS.md` and `docs/setup.md`;
  - move the manifest.
- **Files outside the copied directories,** handled as Claude and Codex
  handled them:
  - `antigravity-container.ps1`, the thin Windows entry, copied byte for byte
    from `sandbox-container.ps1`;
  - `.gitattributes`, followed by an LF renormalization.
- **Antigravity's agent part** (`agent/launcher.sh`) gets the reference's
  ShellCheck header. Without it, the lint requirement that arrives with the
  tag reports 26 findings in that file.
- **Antigravity's own tests** change only where the shared changes alter what
  they check:
  - `tests/test_setup_wrapper.py` is identical to Codex's file before Codex's
    adoption. It takes the adapted version that Claude and Codex now share:
    setup without a launch service, and the budget notices.
  - The budget checks of `tests/test_runtime.py` follow the engine's delegated
    controllers and process mechanism, as Claude's and Codex's do.

  A failure caused by shared code pauses the change for a fix in the
  reference.
- **Antigravity's documentation** (`README.md`, `docs/setup.md`, `AGENTS.md`):
  - a Windows section adapted to Antigravity:
    - provider is the default;
    - the Google sign-in with the URL and code runs inside an interactive
      `agy` session in the machine;
    - `$env:GEMINI_API_KEY` supplies the API key, and `modelProvider: gemini`
      is set in the machine's state;
    - the installer;
    - host CA trust with `--import-native-ca`;
    - the Windows limits, including Bitdefender;
  - the process rlimit fallback and the `cgroupfs` budgets;
  - the guard as the confined init;
  - the setup changes.
- **Parity tables:**
  - Antigravity's row names `sandbox-ref-28`, with this adoption's results;
  - the reference, Claude and Codex rows match `sandbox-container`;
  - Antigravity's row is copied into the reference and the other wrappers.
- **Validation on Windows** with Antigravity, by the operator:
  - setup in provider mode with the account method;
  - the Google sign-in and a session with tool use;
  - token reuse in a second session;
  - `windows-validate -Checkout` on both PowerShell editions, including
    `-Install` and `-StopMachine`;
  - the Gemini API key method.

## Capabilities

### New Capabilities

- `windows-launcher`: the reference capability, copied as is. It runs
  Antigravity from PowerShell in a Podman machine's WSL distribution.
- `windows-installation`: the reference capability, copied as is. It installs
  the Windows entry for one Windows user.

### Modified Capabilities

- `agent-authentication`: the Google sign-in also works from the Windows
  entry, with a Windows browser and the tokens in the machine user's state.
- `container-isolation`:
  - budgets follow the controllers the engine delegates;
  - the process budget falls back to the process rlimit;
  - the documented hardening controls include that fallback.
- `container-session`: the budget notices name the reason or the rlimit
  mechanism, and the qualification identity includes the process budget
  mechanism.
- `container-setup`:
  - the questionnaire and saved budgets with the fallback;
  - recovery tags;
  - setup without a launch service;
  - carriage-return checks;
  - setup started by the Windows entry, with the PowerShell authentication
    steps, including the interactive sign-in step of the `account` method;
  - the service endpoint proposed for restricted modes.
- `network-egress`: the proxy process budget falls back to the rlimit, and the
  guard runs restricted sessions as a confined init.
- `shared-launcher`:
  - ShellCheck;
  - the shared Windows shim and bootstrap;
  - the thin PowerShell entry;
  - LF line endings;
  - PSScriptAnalyzer;
  - the bootstrap tests.
- `workspace-mounts`: Windows system and profile folders are sensitive
  workspace roots.

## Impact

- **Code:** only these files change:
  - the shared files;
  - `antigravity-container.ps1` and `.gitattributes`;
  - the ShellCheck header of `agent/launcher.sh`;
  - the two adapted tests.
- **Installations:** the installed core, setup and guard change, so every
  Antigravity installation reruns `--container-setup`.
- **Behavior on Linux:**
  - On a `cgroupfs` engine, the launch notices state that the memory and CPU
    budgets are not enforced and that the process budget uses the rlimit.
  - Restricted sessions run under the guard as init, so Ctrl+C reaches `agy`
    at once.
  - The internal sandbox limitation of `agy` stays as recorded.
- **Repositories:** the adoption is in `antigravity-container`.
  `sandbox-container` and the other wrappers get only the parity row.
- **Dependency:** `sandbox-ref-28` already exists. The Claude and Codex
  adoptions give the pattern.
