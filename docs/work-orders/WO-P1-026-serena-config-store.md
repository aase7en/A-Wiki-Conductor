# WO-P1-026: Durable Serena Runtime Configuration Store

Status: completed
Lane/files: `src/a_conductor/serena_config_store.py`, `src/a_conductor/__init__.py`, `tests/test_serena_config_store.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-026-serena-config-store.md`
Branch: main
Model tier: high

## Goal

Persist only non-secret Serena worker/project configuration needed to reconstruct lifecycle operations after app restart.

## Acceptance evidence

- RED: config-store module missing before implementation.
- Namespaced SQLite tables coexist with registry tables in same database.
- Worker config round-trip preserves all `SerenaWorkerConfig` fields.
- Project binding round-trip preserves identity policy/branch/head/mutation policy.
- Local reference mapping stores only `reference_id`, `file_path`, `allowed_root`; referenced files are never opened by this store.
- Instance root and health endpoint uniqueness enforced.
- Operational paths must be absolute; worker-owned home/run/log remain under instance root.
- Invalid persisted identity policy/data fails closed with `CONFIG_INVALID`.
- Schema tests confirm no `secret_value`, `token_value`, or `file_contents` columns.
- Targeted tests: `12 passed`.
- Full suite: `375 passed in 7.32s`.
- `compileall`: PASS.
- `git diff --check`: PASS.
- Static sensitive-action scan found no reference-file read, process/network primitive, or secret/token value storage marker.

## Checkpoint log

- [2026-08-20] Opened after desktop shell commit `ac25478`.
- [2026-08-20] Coordination commit `41eb5b2`.
- [2026-08-20] RED module-missing checkpoint.
- [2026-08-20] GREEN targeted 12/12, full 375/375. Complete.
