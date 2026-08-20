# WO-AC-RES-002: Supervised Subprocess Launch / Inspect / Collect

Status: in_progress
Lane/files: `src/a_conductor/supervised_child.py`, `src/a_conductor/supervised_execution.py`, `src/a_conductor/__init__.py`, `tests/test_supervised_child.py`, `tests/test_supervised_execution.py`, `docs/contracts/supervised-subprocess.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-AC-RES-002-supervised-subprocess.md`
Branch: main
Model tier: high

## Goal

Launch suitable medium/long commands so their lifetime and result do not depend on one MCP/chat request. Reuse existing exact-owned-process primitives and AC-RES-001 durable execution records.

## Architecture choice

Do not generalize/duplicate the existing owned-process engine. Launch an internal A-Conductor supervisor helper as the exact owned process. Its command line includes the stable `execution_id`, which reuses the existing `expected_profile_marker` field as a generic ownership marker without changing existing Serena behavior. The helper then launches the target with `shell=False`, inherits sanitized environment/stdout/stderr handles, atomically records child PID, waits, and atomically writes bounded result metadata.

## Acceptance

- Stable per-execution run directory with supervisor PID, child PID, stdout/stderr refs and result JSON ref.
- Target command never uses `shell=True`.
- Target argv is not persisted in SQLite/result JSON; only fingerprint/summary live in durable record.
- Existing WindowsOwnedProcessController owns the supervisor process and prevents duplicate owned supervisor launch for one execution run directory.
- Helper result JSON contains bounded metadata only: schema version, execution_id, child_pid, exit_code, started_at, finished_at.
- Launch returns without waiting for target completion after bounded child-start handshake.
- Inspect distinguishes supervisor alive / result available / unresolved without launching anything.
- Collect reads result metadata and updates AC-RES-001 durable store; it never reruns target.
- Tests use fake/injected process/controller paths first; no active Conductor/Phase6 worker is touched.

## Forbidden

- No blind retry.
- No automatic reconnect/failover.
- No generic operator shell surface.
- No raw command/env/output persistence.
- No active worker/tunnel mutation.
- No A-Wiki/Phase6 mutation.

## Verify

- targeted supervised child/execution tests
- compileall
- diff/static `shell=True` scan
- PID 25396 unchanged

## Checkpoint log

- [2026-08-20] Opened from clean AC-RES-001 completion `0a3040d`.
