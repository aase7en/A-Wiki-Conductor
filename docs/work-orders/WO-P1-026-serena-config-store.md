# WO-P1-026: Durable Serena Runtime Configuration Store

Status: in_progress
Lane/files: `src/a_conductor/serena_config_store.py`, `src/a_conductor/__init__.py`, `tests/test_serena_config_store.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-026-serena-config-store.md`
Branch: main
Model tier: high

## Goal

Persist only non-secret Serena worker/project configuration needed to reconstruct lifecycle operations after app restart. Keep tunnel/credential values outside the database; store opaque refs and allowlisted reference-file paths only.

## Acceptance

- tests first / RED before implementation;
- schema coexists safely in the same SQLite file as registry/lifecycle journal;
- worker config round-trip preserves `SerenaWorkerConfig` fields;
- project binding round-trip preserves identity policy/expected branch/head/mutation flag;
- local reference mapping stores only `reference_id`, `file_path`, `allowed_root`; never file contents;
- health host/port and instance root uniqueness enforced across worker configs;
- invalid persisted enum/port/path/reference data fails closed with stable configuration error;
- no API/token/secret value columns/tables;
- no reading referenced secret/tunnel files in this store;
- full suite + compileall + diff/schema scan pass.

## Forbidden

- No plaintext tunnel IDs, API keys, credentials, or reference-file contents in SQLite.
- No process/network/Git mutation.
- No live worker mutation.
- No remote/push.

## Checkpoint log

- [2026-08-20] Opened after desktop shell commit `ac25478`; worktree clean.
