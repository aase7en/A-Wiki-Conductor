# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Continue from the completed durable job execution transaction layer toward safe operation resolution and later durable Work-class execution.

## Current task

No active work order. Most recently completed: `WO-P1-035`.

## Evidence

- durable store baseline: `9382442`
- P1-035 targeted: 11 passed
- full suite: 502 passed, 1 Tk environment skip
- compileall/diff: PASS
- active Conductor listener: PID 25396
- raw backend exception text is not persisted
- raw-command-like `operation_ref` is rejected
- no scheduler/router/retry-loop surface in coordinator

## Next safe action

Create an allowlisted operation registry/backend that maps opaque identifiers to fixed NativeGitReadAdapter/NativeVerificationAdapter operations. No arbitrary argv or shell string should cross this boundary.
