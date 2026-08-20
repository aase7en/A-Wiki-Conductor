# WO-P1-008: Reusable Worker Pool + Project Registry

Status: done
Lane/files: `src/a_conductor/registry.py`, `src/a_conductor/__init__.py`, `tests/test_registry.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-008-worker-pool-registry.md`
Branch: main
Model tier: mid

## Goal + Acceptance criteria

Implement an in-memory control-plane registry for many Projects and a small reusable A-Worker pool, with deterministic assignment/release guards and no filesystem/process side effects.

Reuse classification: `NEW` at the A-Conductor runtime-control layer. It must coexist with, not replace, A-Wiki work-order/claim ownership.

Acceptance:
- tests written before implementation;
- Project registration stores metadata only and performs no filesystem/Git action;
- worker slots have stable IDs/display names and may be free or assigned;
- same Worker slot can be released and assigned to a different Project;
- exact Windows worktree identity is normalized case-insensitively for conflict checks;
- two mutating workers cannot hold the same exact worktree concurrently;
- duplicate project/worker IDs are rejected rather than overwritten;
- release of a busy worker is refused unless state is first reconciled outside this registry;
- registry exposes safe snapshots without mutable internal dictionaries;
- no I/O/process/network/SQLite/UI code;
- full tests, compileall, I/O scan, and `git diff --check` pass.

## Reference pattern

- `PROJECT-PLAN.md` sections 4-7.
- `docs/contracts/core-domain.md` Project/Worker/Assignment and INV-002/INV-003.
- `src/a_conductor/domain.py`.
- `src/a_conductor/serena_runtime.py`.

## Steps

1. Write failing registry/assignment/release/conflict tests.
2. Capture RED result.
3. Implement minimal in-memory registry and normalized worktree key.
4. Run tests to GREEN.
5. Review against A-Wiki claim boundary and non-mutating registration invariant.
6. Update checkpoint/current-work/handoff and commit.

## Forbidden

- No filesystem/Git/process/network calls.
- No persistence/SQLite yet.
- No runtime start/stop.
- No A-Wiki claim implementation duplication.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Verify commands

- `python -m pytest tests -q --basetemp=runtime/pytest-temp`
- `python -m compileall -q src`
- `git diff --check`
- source scan for I/O/process/persistence imports.

## Checkpoint log

- [2026-08-20] ChatGPT/Sunday-Conducter: opened after strict read-only Windows I/O commit `e0682cc`. Worker-pool registry is an A-Conductor runtime-control primitive and does not replace A-Wiki cross-agent claims.

- [2026-08-20] RED checkpoint: `src/a_conductor/registry.py` confirmed absent; targeted registry tests failed during collection with `ModuleNotFoundError: a_conductor.registry` as expected.

- [2026-08-20] GREEN checkpoint: implemented side-effect-free in-memory `ControlPlaneRegistry`, approved default `A-Worker 1..3` factory, deterministic snapshots, Windows worktree normalization, mutating-worktree conflict guard, runtime mismatch guard, busy-worker release guard, and reusable assign/release semantics. Targeted registry tests 16 passed; full suite 150 passed; compileall PASS; `git diff --check` PASS; I/O/persistence scan clean. No A-Wiki claim/work-order behavior duplicated.
