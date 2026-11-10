# Design

## Context

See `proposal.md`. The reference is `claude-container` at tag `sandbox-ref-8` (commit `12cffab`); this change moves it to `sandbox-ref-9`. `add-network-egress` (merged as `51a88d8`) copied `network/`, `setup/diagnostics.py` and the shared tests except `test_setup.py` and `test_alignment.py`, and integrated the restricted modes into `antigravity-container.sh`. Codex, OpenCode and Pi completed the same step. Pi's archived `add-container-setup` is the template for the wrapper and test work. Codex's is the template for an account method.

**Observed in the reference.**

`setup/` takes every agent value from `agent/profile.json`. `setup.py`:
- proposes the first method of the profile (`account` here) and, on the first run, shared state with `~/<config_home>` (`~/.gemini`);
- offers isolated state with `~/.local/share/<name>/home`, which is Antigravity's existing dedicated home;
- in `authenticate()`, for a method with `login_args`, asks `Run <name> <method> login now?` and runs `bash <release>/<wrapper> <login_args>` on the terminal in a scratch workspace. Otherwise it prints the next action;
- for a method with `credential_env`, prints `Authentication pending. Supply <variable>`;
- builds the runtime image with `build_image(release, 'Containerfile', …)` (the default `recipe` path), runs `--container-qualify`, the `--container-shell` smoke check and `--container-git-worktree`, and installs a managed dispatcher that calls `setup/launch.py`.

`network/agent_profile.py` validates `login_args` with `strings(..., minimum=1, maximum=8)`. An empty list is therefore rejected.

`smoke.py` checks `HOME`, the budgets, a writable `config_dir_env`, `<command> --version`, the CA variables and, in restricted modes, the network and socket denials.

**Observed in Antigravity.**
- `agy` 1.5.3 has no login subcommand (`agy --help` lists none). Sign-in happens only in the interactive TUI (Google OAuth, then a URL and a code), as measured in `add-network-egress`.
- The wrapper already has:
  - the session label;
  - `ANTIGRAVITY_YOLO` as a validated boolean, which setup can export as `0` or `1`;
  - `ANTIGRAVITY_CONTAINER_CONFIG_DIR`, set in the session to `/antigravity-home/.gemini`;
  - the three state choices: an empty state variable with `ANTIGRAVITY_CONTAINER_CONFIG_DIR` is exactly what setup saves for shared state.
- It does not yet:
  - accept `--container-setup`;
  - print `setup required:`;
  - filter stderr.
- The Containerfile has no wrapper-computed build arguments, so the `recipe` build path fits.

## Goals / Non-Goals

**Goals:**
- `network/`, `setup/` and every shared test byte-identical to `sandbox-ref-9`. Unchanged `test_alignment.py` and `test_setup.py` pass against the Antigravity wrapper.
- Guided setup produces a working managed launcher in all three modes, with qualification and the smoke check passing on the WSL target.
- The `account` method can be signed in from setup through the interactive agent.
- The Antigravity parity row is identical in the five repositories, and every row names `sandbox-ref-9`.

**Non-Goals:**
- Authenticated verification, which stays operator-run after all Waves.
- A setup default other than the reference (`shared`).
- Enabling real systemd user services in tests.

## Decisions

### Shared fix first: empty `login_args` (`sandbox-ref-9`)

The operator chose a shared fix on 2026-11-10. In `claude-container`:
- **`network/agent_profile.py`:** accepts `login_args` with zero to eight arguments; an empty list means "sign in through the interactive agent". The other rules stay: at most eight unique arguments, each matching the argument pattern.
- **`setup/setup.py`, `authenticate()`:** with empty `login_args`:
  - asks `Run <name> <method> sign-in now? It opens <name> interactively; exit it when signed in.`;
  - runs `bash <release>/<wrapper>` with no further arguments (plus `--container-git-worktree` when saved), on the terminal, in the scratch workspace, with `runtime_environment(value, release, overrides=False)`, exactly as the existing login path;
  - reports `verified (<name> <method> interactive sign-in session exited successfully; no model request tested)` on success. The success status says that the session exited, not that sign-in succeeded, because setup cannot observe it;
  - when declined or failed, prints `Next authentication action: <command> (sign in inside the interactive session)`.

  Methods with arguments keep today's wording and command.
- **Tests:**
  - `tests/test_agent_profile.py` accepts `[]` and still rejects nine arguments and duplicates;
  - `tests/test_setup.py` gains a case with a scratch profile declaring `login_args: []`. It checks the exact command (wrapper with no agent arguments), the terminal inheritance, the environment and both messages.

Claude and Codex declare arguments and OpenCode and Pi declare none, so their behavior is unchanged; `--setup` and `--shared` must still pass in all four.

The steps are:
1. Merge in Claude and create the tag `sandbox-ref-9`.
2. Adopt it in Codex, OpenCode and Pi: manifest, references, `--shared` and `--setup`.
3. Copy it here.

Rejected alternatives:
- **A dummy login argument** (for example `--version`). It would report a sign-in that never happened.
- **Documentation only.** Setup would end with `pending` and no next action for the default method.

### Setup state follows the reference (operator decision of 2026-11-10)

No profile field is added.

| Setup choice | Saved values | Wrapper behavior |
| --- | --- | --- |
| `shared` (first-run default) | state empty, configuration directory `~/.gemini` | Shared state: `~/.gemini` below an ephemeral home |
| `isolated` | state `~/.local/share/antigravity-container/home` | The dedicated home |

The existing disclosure ("shared exposes your selected host Antigravity credentials…") is shown before the choice. `docs/setup.md` recommends `isolated` for operators who also use Gemini CLI, and notes that shared state keeps only `.gemini` across sessions (`~/.config/antigravity` is ephemeral). Direct launches keep their own default (unset means the dedicated home).

### Copy the remaining setup files and tests from the tag

`git -C ../claude-container archive sandbox-ref-9 network setup tests/<shared>` is unpacked over the checkout, including `tests/test_setup.py` and `tests/test_alignment.py`. `tests/test_reference_copy.py` extends its manifest to the new files and moves to `sandbox-ref-9`, as in Pi.

### Wrapper entry points follow the reference wrappers

- `--container-setup` is handled after help and qualification. It must be used alone, needs a terminal on stdin and stdout and host Python 3, and then `exec`s `python3 -I setup/setup.py`.
- The missing-mode message becomes `setup required: run bash <wrapper> --container-setup; use the managed launcher afterward or explicitly set ANTIGRAVITY_CONTAINER_NETWORK for an operator workflow (offline, provider, or unrestricted; unrestricted keeps the previous networking behavior)`, with the wrapper path quoted by `printf %q`.
- The attached client's stderr goes through `setup/diagnostics.py` on a FIFO in the private session directory. It is reaped within a one-second drain inside the shutdown budget, as in Pi.
- Messages that the shared tests check literally are aligned to the reference wording. A mismatch caused by shared code goes to Claude.

### Authentication

| Method | Profile | Setup assistance |
| --- | --- | --- |
| `account` | `google-account` | Interactive sign-in offer through the installed wrapper (empty `login_args`) |
| `gemini` | `gemini-api` | `Authentication pending. Supply GEMINI_API_KEY` |

Setup makes no model call and stores no key or token. In offline mode setup skips authentication, which is not applicable. An `account` sign-in in provider mode reaches only the profile hosts. If sign-in needs a host outside `google-account`, the session shows the proxy denial and the operator check decides the profile change.

### Parity table

`docs/network-contract.md` gets the five-wrapper table copied from Claude, with the Antigravity row:
- contract adoption: ported from `sandbox-ref-9`, shared files unchanged;
- implementation: guard, multiplexed proxy, qualification and guided setup integrated; keyring removed;
- real enforcement: WSL ABI 3, all runtime modes and setup acceptance passed (with the date);
- authentication: pending operator checks for `google-account` and `gemini-api`; synthetic Gemini streaming and tool call passed.

The same row replaces "Pending" in the other four repositories, and every row moves to `sandbox-ref-9` during adoption.

### Setup runtime acceptance

`tests/test_setup_runtime.py` is ported from Pi with Antigravity names: `ANTIGRAVITY_CONTAINER_IMAGE`, `localhost/antigravity-cli:latest`, `antigravity-container`, and `--version` printing `1.5.3`. It runs setup under a pseudo-terminal against the real same-host service, with:
- a disposable `HOME`, installation and command path;
- a disposable proxy image;
- prepared runtime images.

It covers:
- offline, provider and unrestricted installations;
- the `gemini` transcript;
- an `account` run that declines the sign-in offer and checks the next-action message;
- an `account` run that accepts it, with the TUI quit through two Ctrl+C, which checks the command and the reported status.

It does not enable systemd services, read real credentials or send model requests.

## Risks / Trade-offs

- **[Shared setup gains a new login path]** → The path is selected only by an empty list; the other wrappers' profiles keep their behavior, and their suites run before the tag is used.
- **[Setup cannot observe whether sign-in succeeded]** → The status wording says the interactive session exited successfully, not that the account is authenticated; the operator check covers real sign-in.
- **[Shared default exposes `~/.gemini`]** → The existing disclosure precedes the choice, `docs/setup.md` recommends `isolated` when Gemini CLI is used, and the operator kept the reference default.
- **[The diagnostics FIFO changes stderr buffering]** → The design is measured in the other wrappers; the TTY, pipe and signal tests are rerun.

## Migration Plan

1. New users run `bash ./antigravity-container.sh --container-setup`, then use `~/.local/bin/antigravity-container`.
2. Direct invocations keep working with an explicit `ANTIGRAVITY_CONTAINER_NETWORK`. Without one, they get the setup-required message.
3. Rollback:
   - setup keeps the last working release and restores it on failed activation;
   - at the repository level, check out `51a88d8`.
