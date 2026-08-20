# WO-P1-022: Tunnel Reference + Strict Preflight Boundaries

Status: completed
Lane/files: `src/a_conductor/tunnel_boundaries.py`, `src/a_conductor/owned_process.py`, `src/a_conductor/serena_materializer.py`, `src/a_conductor/__init__.py`, `tests/test_tunnel_boundaries.py`, `tests/test_owned_process.py`, `tests/test_serena_materializer.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-022-tunnel-preflight-references.md`
Branch: main
Model tier: high

## Goal

Implement secret-safe local reference/token resolution and a strict bounded `tunnel-client doctor --profile-file ... --explain` preflight service without starting a long-lived runtime.

## Acceptance evidence

- RED: import failed because shared child-environment builder did not yet exist.
- Safe child environment filtering was refactored into shared `build_owned_child_environment()` and reused by spawner/preflight.
- Materializer exposes one canonical `discover_profile_placeholders()` utility; no duplicate placeholder regex in token provider.
- `LocalFileReferenceStore` maps opaque refs to allowlisted local files and returns trimmed single-line non-empty NUL-free values; errors are code-only.
- `ReferenceBackedSerenaTokenProvider` returns only tokens requested by the actual template and derives project/home/health/worker tokens locally.
- `__TUNNEL_ID__` resolves only through the opaque reference store; unknown placeholders fail closed.
- `LocalTunnelOwnershipGuard` detects configured collisions and unreleased ownership without revealing binding values.
- Strict preflight executes only exact runtime executable + `doctor --profile-file <profile> --explain`, `shell=False`, bounded timeout, safe child env.
- Preflight stdout/stderr are not returned in `SerenaOperationResult`; timeout/nonzero/OS failures map to stable codes.
- Targeted tests: `59 passed` across tunnel/owned-process/materializer suites.
- Full suite: `343 passed in 4.83s`.
- `compileall`: PASS.
- `git diff --check`: PASS.
- Static forbidden scan: no taskkill, shell=True, broad process mutation, Git network/mutation patterns.
- Atomic active-worker preservation: Sunday-Conducter PID `25396` before/after full suite.
- No long-lived tunnel process, no live A-Worker 3 mutation.

## Checkpoint log

- [2026-08-20] Opened after P1-021 commit `d6589a7`.
- [2026-08-20] Coordination commit `e69b190`.
- [2026-08-20] RED shared-env-builder/import checkpoint captured.
- [2026-08-20] GREEN targeted 59/59; full suite 343/343; active worker preserved. Work order complete.
