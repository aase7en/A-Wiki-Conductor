# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / local process manager**

## Active work order

None — `WO-P1-016` completed; next work order will be opened after the clean checkpoint commit.

## Completed foundation

- [x] Contracts/local Git/provider-neutral runtime safety stack complete.
- [x] Registry + SQLite persistence complete.
- [x] Lifecycle planner/executor/journal/recovery stack complete.
- [x] Read-only Windows observer + strict inspection backend complete.
- [x] Stage A self-owned dummy-runtime lifecycle integration complete.
- [x] Windows exact-owned process controller complete.
- [x] P1-016 targeted tests: 16 passed.
- [x] Full suite at P1-016 close: 250 passed.
- [x] Atomic preservation run: active Conductor PID 25396 before/after; no active-worker targeting.

## Repository state

- Branch: `main`
- HEAD before P1-016 close commit: `b0f8762`
- Git remote: none
- Use exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`; global Git config unchanged.

## External integration state

- GitHub connector was explicitly attempted at user request but returned platform `FORBIDDEN`; no GitHub-side mutation performed.
- Local repo has no remote, so GitHub publication remains unresolved.

## DECISION_REQUIRED

- `DR-C1-001`: GitHub publication; private-first recommended; no remote/push until destination/visibility is known.
- `DR-P1-002`: first live Serena/tunnel lifecycle integration must use a dedicated isolated worker, never the active Sunday-Conducter or Phase6 worker.

## Constraints

- Exact owned process only; no broad kill.
- No `shell=True`.
- Mutable PID/log paths restricted to the worker-owned runtime root.
- Active Sunday-Conducter/Phase6 workers are protected.
- `serena-test` remains read-only candidate unless a disposable mutation target is created separately.

## Next safe action

Open `WO-P1-017` for Serena runtime profile rendering + lifecycle backend composition. Keep tests on fake/dummy resources first; do not provision or mutate A-Worker 3 until the Stage B preflight and isolation resources are explicitly validated.
