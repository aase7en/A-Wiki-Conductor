# WO-P1-004: Serena Worker Runtime Profile Model

Status: done
Lane/files: `src/a_conductor/serena_runtime.py`, `src/a_conductor/__init__.py`, `tests/test_serena_runtime.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-004-serena-runtime-profile.md`
Branch: main
Model tier: mid

## Goal + Acceptance criteria

Implement pure configuration models that separate stable A-Worker-owned Serena resources from dynamically assigned Project/worktree binding.

Acceptance:
- tests written before implementation;
- `SerenaWorkerConfig` contains stable worker/runtime resources only;
- `SerenaProjectBinding` contains assignment-owned project/worktree identity only;
- worker config has no permanent `project_id`/`worktree` field;
- credential/tunnel material represented only by opaque references, never secret values;
- health port validates `1..65535`;
- startup/stop timeouts are positive;
- identifiers/paths/references reject blank values;
- no filesystem/process/network calls;
- `pytest`, `compileall`, forbidden-import scan, and `git diff --check` pass.

## Reference pattern

- `docs/contracts/serena-runtime-manager.md` sections 4-5, 14, 16.
- `docs/contracts/core-domain.md` INV-003/INV-004.

## Steps

1. Write failing tests for worker-owned vs assignment-owned configuration.
2. Capture RED result.
3. Implement minimal frozen configuration dataclasses.
4. Run tests to GREEN.
5. Review for permanent project binding or secret-value fields.
6. Update checkpoint/current-work/handoff and commit.

## Forbidden

- No file existence checks or writes.
- No subprocess/socket/network/runtime calls.
- No process lifecycle logic.
- No tunnel/API credential values.
- No broker/UI/provider integration.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Verify commands

- `pytest -q`
- `python -m compileall -q src`
- `git diff --check`
- forbidden import/product/secret-field scan.

## Checkpoint log

- [2026-08-20] ChatGPT/Sunday-Conducter: opened after pure runtime-safety commit `676a881`. Scope is configuration/data validation only.
- [2026-08-20] RED checkpoint: `pytest -q` failed during collection with `ModuleNotFoundError: a_conductor.serena_runtime` as expected; no Serena runtime-profile implementation existed yet.
- [2026-08-20] GREEN checkpoint: implemented immutable `SerenaWorkerConfig`, `SerenaProjectBinding`, and `ProjectIdentityPolicy`. Full verification: `pytest -q` = 67 passed; `python -m compileall -q src` PASS; `git diff --check` PASS; forbidden process/network/secret-value pattern scan clean. Worker config contains no permanent project/worktree binding and stores transport/credential references only as opaque refs. No I/O/process lifecycle behavior added.
