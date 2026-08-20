# WO-P1-020: Concrete Serena Lifecycle Operations

Status: completed
Lane/files: `src/a_conductor/serena_operations.py`, `src/a_conductor/serena_materializer.py`, `src/a_conductor/__init__.py`, `tests/test_serena_operations.py`, `tests/test_serena_materializer.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-020-serena-lifecycle-operations.md`
Branch: main
Model tier: high

## Goal

Implement concrete pre-bound `SerenaLifecycleOperations` using existing bounded local components and injected tunnel/preflight/project-identity/assignment/evidence boundaries.

## Acceptance evidence

- RED: `ModuleNotFoundError: a_conductor.serena_operations` before implementation.
- Assignment verification is read-only path existence check.
- Resource verification re-checks PID ownership + health port and tunnel availability immediately before materialization/start.
- Stale/invalid/unknown PID states fail closed with recovery semantics.
- Profile rendering uses injected token provider + bounded materializer; token-provider exceptions are redacted to `PROFILE_TOKEN_RESOLUTION_FAILED`.
- Start delegates only to exact-owned process controller.
- `targeted_stop()` and `wait_ready()` can reconstruct deterministic existing spec after app restart without re-rendering or resolving token secrets.
- Readiness requires valid PID ownership + expected health-port ownership + loopback `/readyz` ready state within bounded timeout.
- Wait-exit requires absent PID metadata + free health port.
- Release additionally delegates tunnel-release guard.
- Preflight/project identity/assignment clear/evidence emit remain explicit injected boundaries.
- Targeted tests: `32 passed`.
- Full suite: `313 passed in 4.59s`.
- `compileall`: PASS.
- `git diff --check`: PASS.
- Direct I/O scan on operations module: clean (no subprocess/PowerShell/SQLite/socket/url/keyring primitives).
- Atomic active-worker preservation: Sunday-Conducter PID `25396` before/after full suite.
- No live Serena/tunnel/A-Worker 3 mutation.

## Checkpoint log

- [2026-08-20] Opened after P1-019 commit `963a9c4`.
- [2026-08-20] Coordination commit `33d82fa`.
- [2026-08-20] RED module-missing checkpoint captured.
- [2026-08-20] GREEN targeted 32/32; full suite 313/313; active worker preserved. Work order complete.
