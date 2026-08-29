# WO-GE-010 — Graph chaos / E2E program

Created: 2026-08-29
Owner: GPT-5.6 Sol Graph Engineering lane
Status: COMPLETE / MERGED PR #139 / POST-MERGE MAIN CI GREEN
Parent: `docs/work-orders/WO-GE-001-graph-engineering-kickoff.md` (GE-10)
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-ge10-chaos`
Branch: `feat/wo-ge-010-graph-chaos`
Base: `origin/main@da50305961536cc68b072ca99769a9c8e3048ffd`

## Goal

Prove graph + durable execution behavior under deterministic failure without mutating real workers, connectors, tunnels or repositories. Start tests-only; any production defect must become a bounded repair step with RED evidence before source mutation.

## Reuse-before-build

Classification: **REUSE + COMPOSE**.

- reuse all 10 `FaultScenario` values from `fault_injection.py`;
- reuse SQLite durable job/execution stores and recovery services;
- reuse GE-7 `GraphDispatchKey`, GE-9 lifecycle projection, GE-8 barriers and GE-5 ReadySet;
- no second fake executor, lifecycle, retry loop, graph store or scheduler.

## 13-case program

Fault-contract cases:
1. NORMAL_SUCCESS
2. DISCONNECT_BEFORE_LAUNCH
3. DISCONNECT_AFTER_LAUNCH
4. DISCONNECT_MID_COMMAND
5. DISCONNECT_AFTER_COMPLETION
6. DELAYED_SUCCESS
7. LARGE_STDOUT
8. NONZERO_EXIT
9. MALFORMED_RESULT
10. UNKNOWN_PROCESS

Graph-specific resilience:
11. wrong repository identity blocks recovery and cannot advance graph truth;
12. durable store reopen preserves GraphDispatchKey identity and same-key replay cannot execute twice;
13. fan-in remains blocked through recovery and opens only after both durable lifecycle and expected-output evidence are complete.

## Allowed mutable scope

- `tests/test_graph_chaos.py` (new)
- this WO
- GE-9 accepted-main closeout in WO-GE-009
- bounded GE-10 checkpoint in WO-GE-001
- production source only if a deterministic new RED defect is found and recorded before mutation.

## Forbidden

- `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, WO-P1-102, worker lease source/tests (active Draft PR #131 ownership);
- real connector/tunnel/Serena process mutation;
- A-Wiki mutation;
- scheduler/lifecycle/store redesign;
- UI files (GE-11 owns UI).

## Acceptance

- [x] exactly 13 deterministic scenario cases collected;
- [x] no `sleep`, network, process spawn or live worker/tunnel mutation;
- [x] all 10 existing FaultScenario values are covered once by the graph chaos matrix;
- [x] transport/execution uncertainty never silently projects graph DONE;
- [x] wrong repo identity blocks recovery;
- [x] durable reopen preserves graph-run/node identity and prevents same-key replay;
- [x] fan-in recovery blocks downstream until durable state + outputs are complete;
- [x] existing fault-injection and explicit graph suites remain green;
- [x] compile/diff/scope/secret gates pass;
- [ ] exact-head 3-OS CI green, final remote diff reviewed, PR merged and main verified.

## Next

Write tests-only program -> run focused 13 cases -> classify any RED as test/spec defect vs production defect -> repair only evidence-backed source if needed -> regressions -> review -> PR/CI/re-audit/merge.

## Local verification checkpoint - 2026-08-29

- Focused collection is exactly 13 tests and focused execution is **13/13 PASS**.
- Broader graph + fault/recovery/transport regression is **200/200 PASS**.
- Staff review restored the promised same-key replay case: reopening durable job control cannot execute an already-VERIFYING GraphDispatchKey twice.
- No production source mutation was required; compileall/diff-check and forbidden-call scan pass.

## Merge closeout - 2026-08-29

PR #139 merged as `1fea5cfffbe9bb8a9093e67dfa1065559e324ab2`. Post-merge main CI run `33237480511` passed Windows, Ubuntu, and macOS. The deterministic 13-case chaos matrix is accepted; this work order is complete.
