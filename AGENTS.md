# Language conventions

- Write all project documentation in English, including OpenSpec proposals, designs, specifications, tasks, and archived artifacts.
- Communicate with the user in Italian in chat.

# Security constraints

- Every session drops all capabilities and sets no-new-privileges. Never add capabilities back, add `--privileged` or disable no-new-privileges to fix a tool; record the limitation in `docs/validation.md` instead.
- Sessions have validated, inspected memory, CPU and process budgets (`ANTIGRAVITY_CONTAINER_MEMORY_LIMIT`, `ANTIGRAVITY_CONTAINER_CPU_LIMIT`, `ANTIGRAVITY_CONTAINER_PIDS_LIMIT`; defaults 4g, 2, 512) and an optional `ANTIGRAVITY_CONTAINER_RUN_TIMEOUT`. No value disables a budget.
- Sensitive workspace roots (`/`, system directories, `/tmp`, the physical home and `/mnt/<letter>`) are refused unless exactly `ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1`.
- Image inputs (base digest, `agy` release artifact and SHA-512 per architecture, OpenSpec version) are pinned in `Containerfile` and change only through the README update procedure.
- Run `tests/test_wrapper.py` and `tests/test_image_pins.py` without credentials; real-engine checks use `bash tests/run-runtime.sh`.
