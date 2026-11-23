# Spec Delta

## ADDED Requirements

### Requirement: Setup without a launch service offers only unrestricted networking
Before asking for the network mode, setup SHALL check, read-only, whether a same-host Unix launch service answers at `CONTAINER_HOST`, the saved endpoint or the default endpoint, and whether a usable systemd user manager could start one. When neither holds, setup SHALL offer only unrestricted networking, explain why, require explicit confirmation, and offer no delegation.

#### Scenario: Host without systemd user manager or service
- **WHEN** setup runs where no launch service answers and `systemctl --user` is missing or fails, as in a Podman machine distribution on WSL
- **THEN** setup states that offline and provider networking need a same-host service and that none is available or startable
- **AND** it asks for explicit confirmation of unrestricted networking, does not ask about delegation, and saves the local engine as the launch endpoint

#### Scenario: Local endpoint leaves CONTAINER_HOST unset
- **WHEN** the saved launch endpoint is the local engine
- **THEN** the smoke check and managed launches run Podman without `CONTAINER_HOST`, and the launcher treats an empty `CONTAINER_HOST` or `CONTAINER_CONNECTION` as unset, because Podman treats a set variable as a remote context even when it is empty

#### Scenario: Confirmation declined
- **WHEN** the user declines unrestricted networking in that situation
- **THEN** setup ends with status 1 without changes and explains how to make a service available: start a same-host Podman service, or set `CONTAINER_HOST` to its Unix endpoint, then rerun setup

#### Scenario: Saved restricted mode without a service
- **WHEN** setup is rerun with saved offline networking and no service is reachable or startable any longer
- **THEN** setup does not propose offline, states that the saved mode cannot be kept, and changes to unrestricted only after explicit confirmation

#### Scenario: Service reachable or startable
- **WHEN** a launch service answers at one of the checked endpoints, or a usable systemd user manager exists
- **THEN** setup offers every mode the profile allows, as before

#### Scenario: Explanation names no runtime directory
- **WHEN** setup explains how to make a service available
- **THEN** the explanation refers to the setup guide and names no socket path derived from `XDG_RUNTIME_DIR`

### Requirement: Installation inputs with carriage returns are refused
Before copying installation inputs into a new release, setup SHALL refuse any input file that contains a carriage return byte. The refusal SHALL name the file, explain that release files must have LF line endings, point to the repository's `.gitattributes` and the renormalization step, and leave the last working installation selected.

#### Scenario: CRLF checkout
- **WHEN** an installation input in the checkout contains CRLF line endings
- **THEN** setup stops with status 1 naming that file and the renormalization step, before creating the release

#### Scenario: LF checkout
- **WHEN** every installation input has LF line endings
- **THEN** setup copies the inputs as before

### Requirement: Setup started by the Windows entry
When the Windows entry starts setup, setup SHALL omit the shell `PATH` guidance and the managed-command lines for launching and reviewing setup from its plan and summary, and SHALL state that the Windows entry starts sessions. Its pending authentication steps SHALL name `<name>.ps1` and PowerShell's `$env:`, not the managed command. Setup started from a Linux shell SHALL keep that guidance.

#### Scenario: Setup from the Windows entry
- **WHEN** the user runs `<name>.ps1 --container-setup`, or `--container-install` runs setup from the installed copy
- **THEN** the setup output contains no `export PATH=` line, no shell startup file and no distribution path of the managed command, and the entry then prints how to start sessions

#### Scenario: Login postponed from the Windows entry
- **WHEN** setup started by the Windows entry selects a method with login arguments and the user declines the login
- **THEN** the next authentication action is `<name>.ps1` followed by the login arguments, with no distribution path

#### Scenario: API key method from the Windows entry
- **WHEN** setup started by the Windows entry selects a method with a credential variable `<KEY>`
- **THEN** it says to set `$env:<KEY>` in PowerShell before running `<name>.ps1`

#### Scenario: Setup from a Linux shell
- **WHEN** setup runs from a Linux shell whose `PATH` lacks the managed command directory
- **THEN** it prints the `export PATH=` guidance and the managed-command lines as before

### Requirement: Restricted modes propose a service endpoint
When the selected workflow needs a same-host Unix service and the saved launch endpoint is the local engine, setup SHALL propose `default` as the launch endpoint instead of the saved value.

#### Scenario: From unrestricted to offline
- **WHEN** a rerun moves an installation that saved unrestricted networking and the local endpoint to offline networking, and the user accepts the proposed endpoint
- **THEN** setup saves the `default` endpoint without refusing the answer first

#### Scenario: Unrestricted rerun
- **WHEN** a rerun keeps unrestricted networking without delegation
- **THEN** setup still proposes the saved local endpoint

## MODIFIED Requirements

### Requirement: Workflow questionnaire with explicit defaults
Setup SHALL explain and collect network mode, provider authentication method when relevant, state sharing, installation paths, host CA trust, permission bypass and workspace scope. First-run defaults SHALL select provider networking, the first authentication method of the profile (`account` for Antigravity), shared state and disabled optional authority. Existing saved choices SHALL be offered for review on rerun. When no same-host launch service is available, the network choice SHALL follow the rule for setup without a launch service instead.

#### Scenario: First setup choices
- **WHEN** the user reviews first-run defaults on a host where a same-host launch service is reachable or can be started
- **THEN** network options distinguish offline, provider-restricted and unrestricted use, and provider questions list the `account` and `gemini` methods with their hosts
- **AND** accepting the first-run network/authentication defaults selects provider/`account`
- **AND** shared host credentials, isolated fresh state, worktree-parent exposure and permission bypass are explained before selection

#### Scenario: Provider selected
- **WHEN** the user chooses provider mode and the `gemini` method without `GEMINI_API_KEY` set, and a same-host launch service is reachable or can be started
- **THEN** setup selects the protected `gemini-api` profile and reports authentication as pending
- **AND** the `account` method selects the separate `google-account` profile

#### Scenario: State defaults follow the reference
- **WHEN** the user reviews the state question on a first run
- **THEN** setup proposes shared state with the host `~/.gemini` as the configuration directory, and isolated state with `~/.local/share/antigravity-container/home` as its directory
- **AND** the saved shared choice launches with an empty `ANTIGRAVITY_CONTAINER_STATE_DIR` and the selected `ANTIGRAVITY_CONTAINER_CONFIG_DIR`

#### Scenario: Previously saved network mode
- **WHEN** setup is rerun with a saved configuration, including explicit offline mode, and a same-host launch service is reachable or can be started
- **THEN** the saved network mode remains the proposed choice instead of the first-run provider default

### Requirement: Saved budgets govern managed launches and verification
The managed launcher SHALL supply the saved budgets and lifetime through `ANTIGRAVITY_CONTAINER_MEMORY_LIMIT`, `ANTIGRAVITY_CONTAINER_CPU_LIMIT`, `ANTIGRAVITY_CONTAINER_PIDS_LIMIT` and `ANTIGRAVITY_CONTAINER_RUN_TIMEOUT` when these are absent from the launch environment. An explicitly present variable SHALL take precedence. Setup smoke and qualification SHALL use the saved values for every budget the engine can enforce, through its cgroup controller or the process rlimit fallback.

#### Scenario: Managed launch uses saved budgets
- **WHEN** the user launches through the managed command with no budget variables exported
- **THEN** the agent container receives the saved budgets and lifetime
- **AND** a restricted launch matches the qualification report produced by setup

#### Scenario: Explicit override differs from qualified values
- **WHEN** the user exports `ANTIGRAVITY_CONTAINER_MEMORY_LIMIT=16g` for a restricted managed launch qualified with `4g`
- **THEN** the override is used and the qualification check stops the launch with requalification guidance

#### Scenario: Smoke verifies saved values
- **WHEN** setup runs its installed smoke check
- **THEN** the smoke compares the effective cgroup limits of every cgroup-enforced budget with the saved budgets, not with ambient environment values
- **AND** when the process budget uses the rlimit fallback, it compares the effective soft and hard process rlimit with the saved process budget
- **AND** it requires every budget whose controller is missing to have no cgroup limit

#### Scenario: Setup plan names unenforced budgets
- **WHEN** setup runs on an engine that does not delegate the `cpu` controller
- **THEN** the setup plan lists the CPU budget as not enforced, with the missing controller, and setup continues without an extra question

#### Scenario: Setup plan names the process rlimit fallback
- **WHEN** setup runs on an engine that does not delegate the `pids` controller, on a host that counts the process rlimit per container
- **THEN** the setup plan lists the process budget as enforced through the process rlimit, with the missing controller, and setup continues without an extra question

#### Scenario: Setup plan names a cgroup manager without limits
- **WHEN** setup runs on a rootless engine with the `cgroupfs` cgroup manager that reports every controller
- **THEN** the setup plan lists no enforced cgroup budget, names the `cgroupfs` manager as the reason for the memory and CPU budgets, and lists the process budget mechanism
- **AND** setup continues without an extra question

### Requirement: Repeatable setup with owned recovery
Rerunning setup SHALL review saved choices and reuse valid artifacts. Activation SHALL preserve the previous working installation until the candidate passes validation. Cancellation, interruption or failure SHALL remove only setup-owned temporary resources, preserve credentials and unrelated containers, and report persistent changes already made. Concurrent setup runs SHALL NOT overwrite each other's activation.

#### Scenario: Rerun or interrupted update
- **WHEN** setup is rerun unchanged or interrupted while preparing an update
- **THEN** unchanged suitable artifacts need no rebuild and the last activated launcher remains usable
- **AND** any created images or enabled user socket remaining after interruption are reported without deleting shared resources

#### Scenario: Abandoned candidate tags
- **WHEN** setup fails, is cancelled or is interrupted after it tagged images `setup-<release>` for its candidate release
- **THEN** it removes those tags before exiting, keeps every other tag of the same images and the tags of retained releases and other installation roots, and reports an image left without a name with the command that removes it

#### Scenario: Competing activation
- **WHEN** another setup already holds the target installation's update lock
- **THEN** setup exits with an actionable busy message without modifying that installation

#### Scenario: Unrelated launcher exists
- **WHEN** the desired command path contains a file not owned by this setup
- **THEN** setup offers a different path or stops without overwriting that file

#### Scenario: Managed command path changes
- **WHEN** a validated candidate chooses a different physical command entry
- **THEN** activation retires the previous owned command only after publishing the new command
- **AND** retirement or publication failure restores the previous activation and command
- **AND** two path spellings of the same physical entry do not cause its removal

#### Scenario: Group leader exits before timeout cleanup
- **WHEN** a setup-owned process group has surviving descendants after its leader exits or its captured pipes close
- **THEN** timeout or interruption cleanup terminates the remaining owned group within bounded teardown time
- **AND** the primary timeout/interruption remains the reported outcome

### Requirement: Credential-preserving authentication assistance
Setup SHALL NOT copy credentials, collect or persist API keys or tokens in setup preferences, or call a model. Authentication SHALL use the chosen installed sandbox and preserve its selected network and CA policies. For the `account` method, whose profile declares empty `login_args`, setup SHALL offer an interactive sign-in through the installed wrapper without arguments. For API-key methods it SHALL report authentication as pending with the variable to supply.

#### Scenario: Interactive account sign-in accepted
- **WHEN** the operator selects `account` and accepts the sign-in offer
- **THEN** setup starts the installed wrapper with no `agy` arguments on the terminal, in a scratch workspace, with the saved mode and policies
- **AND** the operator completes Google's URL and code flow in `agy`, exits, and setup reports authentication as verified only when the session exits successfully

#### Scenario: Interactive account sign-in declined
- **WHEN** the operator declines the offer or the session fails, in setup started from a Linux shell
- **THEN** setup keeps the sandbox ready, reports authentication as pending and names the managed command to start for sign-in

#### Scenario: API key unavailable
- **WHEN** the `gemini` method is selected but `GEMINI_API_KEY` is not set
- **THEN** sandbox preparation can complete with authentication explicitly pending and instructions for supplying the key through the existing runtime mechanism
- **AND** no paid model request is made automatically
- **AND** no port is published and no host-network exception is added for a browser callback

#### Scenario: Interactive sign-in postponed from the Windows entry
- **WHEN** setup started by the Windows entry selects `account` and the operator declines the sign-in offer, or the sign-in session fails
- **THEN** the next authentication action names `antigravity-container.ps1` with no arguments and no distribution path, and says to sign in inside the interactive session
