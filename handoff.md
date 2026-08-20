# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Bind the completed allowlisted native-operation backend to real current Control Center worker/project assignment state without adding routing or lifecycle mutation.

## Current task

`WO-P1-037 — Native Worker Adapter Assembly`

Status: `IN_PROGRESS`

## Baseline

- allowlisted native operation backend commit: `50bc4c7`
- P1-036 full suite: 518 passed
- active Conductor listener: PID `25396`

## Boundary

- fresh snapshot per resolve
- exact assigned project root only
- exact assignment mutation authority only
- Git + Python executable allowlist only
- default result: NativeGitReadAdapter + NativeVerificationAdapter
- no Git mutation/lifecycle/tunnel/router/scheduler surface

## Next safe action

Commit P1-037 coordination/contract checkpoint, then write RED assembly tests with injected adapter factories and real ControlCenterService coverage.
