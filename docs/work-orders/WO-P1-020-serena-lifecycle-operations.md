# WO-P1-020: Concrete Serena Lifecycle Operations

Status: in_progress
Lane/files: `src/a_conductor/serena_operations.py`, `src/a_conductor/serena_materializer.py`, `src/a_conductor/__init__.py`, `tests/test_serena_operations.py`, `tests/test_serena_materializer.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-020-serena-lifecycle-operations.md`
Branch: main
Model tier: high

## Goal

Implement the concrete pre-bound `SerenaLifecycleOperations` adapter for one worker/project assignment using existing bounded local components: runtime materializer, Windows observer, exact-owned process controller, and explicit injected boundary services for tunnel/preflight/project-identity/assignment/evidence.

## Acceptance

- tests first / RED before implementation;
- assignment verification checks exact worktree path existence only, no repo mutation;
- resource verification re-checks PID metadata + health port immediately before render/start and delegates tunnel availability to an injected guard;
- render uses an injected token provider and `SerenaRuntimeMaterializer`;
- start delegates only to `WindowsOwnedProcessController` with the materialized spec;
- stop can reconstruct the existing owned-process spec after app restart without re-rendering/secret resolution;
- wait-ready uses bounded observer polling and requires both `/readyz` success and expected health-port ownership;
- wait-exit/release verification require absent PID metadata + free health port and injected tunnel release result;
- preflight, project identity, assignment clear, evidence emit are explicit injected boundary services;
- all dependency failures return generic codes without raw secret/token/command content;
- no live Serena/tunnel/A-Worker 3 mutation; tests use temp/fake/dummy only;
- full suite + compileall + `git diff --check` pass.

## Forbidden

- No broad kill or direct shell command construction in operations module.
- No Git mutation.
- No direct secret-store implementation.
- No direct SQLite writes.
- No live worker mutation.

## Checkpoint log

- [2026-08-20] Opened after P1-019 commit `963a9c4`; worktree clean.
