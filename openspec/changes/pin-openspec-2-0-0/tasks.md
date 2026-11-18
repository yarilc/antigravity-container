## 1. Baseline

- [x] 1.1 Record the current image ID, `agy --version` (1.5.3) and `openspec --version` (1.16.0). Run `python3 -m unittest discover -s tests -p test_image_pins.py` on the unchanged tree.

## 2. Pin

- [x] 2.1 Set `ARG OPENSPEC_VERSION=2.0.0` in `Containerfile`. Leave every `AGY_*` value and the base digest unchanged.
- [x] 2.2 Update the version-range mutation in `tests/test_image_pins.py` to the new pin. Run the pin tests: they must pass, and every mutation must still be rejected.
- [x] 2.3 Run `git grep -n 1.16.0`. Outside `docs/validation.md` and the archive, nothing may still name 1.16.0 as the current pin.

## 3. Build and verify

- [x] 3.1 Rebuild with `ANTIGRAVITY_CONTAINER_NETWORK=unrestricted ANTIGRAVITY_CONTAINER_MAINTENANCE=1 ./antigravity-container.sh --container-build`. The build itself checks the versions: `agy` must report 1.5.3 and OpenSpec must report 2.0.0.
- [x] 3.2 Run the offline OpenSpec round trip from the reference change (init without agent tools, `new change`, `validate --all`, `list --json`) in shell mode under the guard. Then run `agy --version`.
- [x] 3.3 Run the credential-free suites and every `bash tests/run-runtime.sh` mode, then requalify. All of them must pass.
- [x] 3.4 Run `bash ../sandbox-container/tools/shellcheck.sh .` and `git diff --check`. Record the agent-part ShellCheck findings already known from before; this change must add none.

## 4. Record

- [x] 4.1 Add a dated entry to `docs/validation.md`. It records:
  - the version rule, and why `agy` stays at 1.5.3;
  - the old and new image IDs and the reported versions;
  - the round-trip and suite results.
- [x] 4.2 Add a line to `CHANGELOG.md` under Unreleased.
- [x] 4.3 Run `openspec validate pin-openspec-2-0-0 --strict`, then commit on `main`.

## Workflow follow-up

- The operator pushes `main` and reruns `--container-setup` on the three hosts.
- Archive with `/opsx:archive pin-openspec-2-0-0`. There are no specs to sync.
- `agy` 1.5.11 or later goes in a separate change, once it meets the age rule.
