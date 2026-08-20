# WO-P1-001: Typed Core Domain Models

Status: done
Lane/files: `pyproject.toml`, `src/a_conductor/__init__.py`, `src/a_conductor/domain.py`, `tests/test_domain.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-001-domain-models.md`
Branch: main
Model tier: mid

## Goal + Acceptance criteria

Implement the first dependency-light typed domain layer that mirrors the approved C1 vocabulary without starting runtime/process orchestration.

Acceptance:
- Python 3.11+ compatible;
- no third-party runtime dependency;
- canonical enums/models cover Worker/Project/Runtime/Assignment/TaskState/RecoveryClassification/ReviewOutcome/RiskClass/ExecutionSurfaceTraits;
- `Worker` remains runtime-neutral and may be unassigned;
- Serena/provider/model names are not hard-coded into core domain types;
- identifiers reject empty/whitespace-only values;
- recovery state/classifications exactly match `docs/contracts/core-domain.md`;
- tests are written first and demonstrate the contract;
- `pytest` passes;
- no process spawning, shell execution, SQLite broker, UI, network, or provider adapters are implemented.

## Reference pattern

- `docs/contracts/core-domain.md`
- `schemas/task-contract.schema.json`
- `schemas/repository-identity.schema.json`
- `schemas/evidence-record.schema.json`

## Steps

1. Add minimal pytest config for `src/` layout.
2. Write failing `tests/test_domain.py` from the approved contract.
3. Run tests and capture the expected failure.
4. Implement `src/a_conductor/domain.py` minimally to satisfy the contract.
5. Run tests until green.
6. Review for provider/runtime leakage and schema terminology drift.
7. Update checkpoint/current-work/handoff.

## Forbidden

- No Serena process management.
- No tunnel management.
- No subprocess/shell execution.
- No SQLite/task broker implementation.
- No UI.
- No provider SDK/API integration.
- No A-Wiki/Phase6 mutation.
- No remote creation/push.
- No unnecessary third-party runtime dependency.

## Verify commands

- `pytest -q`
- `python -m compileall -q src`
- search `src/a_conductor/domain.py` for `Serena`, provider product names, or hard-coded model names -> none expected.

## Checkpoint log

- [2026-08-20] ChatGPT/Sunday-Conducter: opened after local Git baseline `3ed22df0d884cf15729167d923ec4a0e32593662`. Python 3.11.15 + pytest 9.1.1 confirmed available. Strategy: stdlib dataclasses/enums first; no framework lock-in.

- [2026-08-20] RED checkpoint: `pytest -q` failed during collection as expected with `ModuleNotFoundError: No module named a_conductor` (1 collection error). No source implementation existed yet. Proceeding to minimal implementation.

- [2026-08-20] GREEN checkpoint: implemented dependency-light frozen dataclasses/enums in `src/a_conductor/domain.py` plus package exports. Verification: `pytest -q` = 17 passed; `python -m compileall -q src` PASS; `git diff --check` PASS; provider/product leakage scan clean. No process/network/broker/UI behavior added.
