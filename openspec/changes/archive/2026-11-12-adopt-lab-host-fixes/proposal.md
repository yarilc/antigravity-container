# Proposal

## Why

The other wrappers now run on `sandbox-ref-12` with the lab-host
adaptations. Claude, Codex, OpenCode and Pi passed the operator's setup on
this host, the Rocky Linux 9 lab host and the newer WSL host. Antigravity
is still on `sandbox-ref-10` with its own launcher and recipe, so on those
hosts it fails as the others did before their ports:

- it rejects the Podman 5 `unix://` socket report;
- it requests undelegated budgets;
- the guard refuses the RHEL secrets mount;
- the terminal cannot attach on crun 1.27;
- the image build needs outbound port 80.

Its recipe also declares `WORKDIR /workspace` after its last build step, so
`/workspace` is in no layer. That broke the Codex qualification on the
Rocky host's domain UID. `sandbox-ref-12` stops the gate depending on it,
but the image should not rely on that either.

## What Changes

- **Adopt `sandbox-ref-12`** (from `sandbox-ref-10`) with
  `tools/propagate.py`: the 21 shared files, the reference manifest and the
  current-state documents (`AGENTS.md`, `docs/setup.md`,
  `docs/network-contract.md`, including the parity cells).
- **Launcher (`antigravity-container.sh`)**, as in Codex, OpenCode and Pi:
  - reduce a `unix://` host socket report to its pathname;
  - request each budget only when its cgroup controller is delegated.
    Announce each unenforced budget, and at inspection require enforced
    budgets to match and unenforced ones to be absent;
  - mask `/run/secrets` with an empty read-only tmpfs;
  - replace `--read-only-tmpfs=false` with a `noexec` `/dev`, `devpts` and
    an empty read-only `/dev/shm`;
  - pass the selected host CA to the image build as the `build-ca` secret.
- **Runtime image recipe**:
  - fetch Debian packages only over verified HTTPS, bootstrapped from the
    base image's Node.js roots plus the optional `build-ca` secret;
  - the agy release download also verifies against the optional
    `build-ca` secret, keeping its SHA-512 check;
  - create `/workspace` in the package step;
  - `.containerignore` admits `podman-build-secret*`;
  - the pin tests reject plain-HTTP sources, disabled verification and a
    `WORKDIR` that no build step creates.
- **Wrapper tests**: fixtures for the shared-code imports and the
  controller query, and assertions for the new mounts, budgets, socket and
  build secret.
- **BREAKING (policy):** undelegated budgets are not enforced; `/dev` is a
  writable `noexec` tmpfs.
- **BREAKING (installation):** the qualification identity, code digests and
  runtime image identity change. Restricted installations rebuild and rerun
  setup. The operator can clean existing state, because the project is not
  distributed.
- **Unchanged:**
  - executable `/tmp`, `noexec` `/var/tmp` and `/run`, and the home tmpfs;
  - the Google account and Gemini API profiles and their policy;
  - the entrypoint;
  - the guard's `/run/secrets` rule.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-isolation`:
  - budgets are enforced per delegated controller and verified;
  - the secrets mask;
  - terminal-compatible device mounts.
- `container-podman-access`: the delegation response accepts a `unix://`
  host socket report.
- `container-session`:
  - the qualification identity binds the enforced budget sets;
  - unenforced budgets are announced.
- `container-setup`:
  - smoke and plan follow the enforced set;
  - the host CA covers setup package fetches.
- `network-egress`:
  - proxy budgets per delegated controller;
  - IPv6-less qualification;
  - the bootstrap admits only the read-only secrets mask;
  - the proxy skips unsupported address families;
  - qualification containers do not depend on the image working
    directory.
- `runtime-image`:
  - HTTPS package sources and the pinned trust bootstrap;
  - the image working directory exists in the image;
  - the release artifact download honors the opt-in host CA.

## Impact

- Shared files through the tool, as listed above.
- Antigravity-owned files:
  - `antigravity-container.sh`, `Containerfile`, `.containerignore`;
  - `tests/test_wrapper.py`, `tests/fake_podman.py`,
    `tests/test_image_pins.py`;
  - `README.md`, `AGENTS.md`, `docs/validation.md`.
- `main` is two commits ahead of `origin/main` (the parity-table
  alignment). That is unrelated and stays as it is.
