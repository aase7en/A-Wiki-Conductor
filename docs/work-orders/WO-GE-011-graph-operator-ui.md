# WO-GE-011 — Graph operator visualization

Created: 2026-08-29
Owner: GPT-5.6 Sol Graph/UI lane
Status: ACTIVE / DESIGN_ACCEPTED / TDD
Parent: `docs/work-orders/WO-GE-001-graph-engineering-kickoff.md` (GE-11)
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-ge11-ui`
Branch: `feat/wo-ge-011-graph-operator-ui`
Base: `origin/main@1fea5cfffbe9bb8a9093e67dfa1065559e324ab2`

## Goal

Expose factual graph topology, queue state and durable job timeline inside the existing MONITOR surface without creating a second dashboard or inventing a current/latest graph run.

## Reuse / boundary

Classification: **REUSE + WRAP + EXTEND**.

- reuse existing MONITOR pane, 15 s monitor tick, background executor and copy behavior;
- reuse GraphStore schema, GE-7 GraphDispatchKey, GE-9 lifecycle projection and durable job events;
- runtime evidence requires an explicit operator-supplied graph run id;
- blank run id is planning-only and must display `RUNTIME: NO RUN EVIDENCE`;
- no graph/job/process/store mutation from the operator view.
## UX contract

- MONITOR header gains `Graph...` and `Connector` actions; all buttons remain English.
- `Graph...` chooses one saved graph id and an optional explicit run id.
- Graph mode shows factual queue counts, node states, dependency edges, and bounded latest durable job events.
- No run id: saved graph status/topology only; never label this LIVE/RUNNING.
- Run id present: GE-9 projection is authoritative; missing jobs remain TODO.
- Connector mode and connector recovery rendering remain unchanged.
- Existing 15 s monitor timer is reused; no second timer, process, network call, or continuous animation.

## WO-P1-068 overlap note

WO-P1-068 already owns connector clarity and active-project provenance. GE-11 does **not** reinterpret connector `ACTIVE PROJECT`, `BOUND PROJECT`, `/readyz`, or recovery state. It only adds a separate graph monitor mode inside the same MONITOR region.

## Allowed mutable scope

- `src/a_conductor/graph/operator_view.py` (new read-only adapter)
- `src/a_conductor/desktop_control.py`
- `src/a_conductor/desktop_ui.py`
- `tests/test_graph_operator_view.py` (new)
- `tests/test_graph_operator_ui.py` (new)
- this WO + GE-10 closeout / bounded GE-11 checkpoint in parent WO-GE-001

## Forbidden

- #131 files: `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, WO-P1-102, `worker_lease.py`, its tests
- graph/job mutation APIs, scheduler, dispatcher, lifecycle state machine
- connector semantics/runtime/process/tunnel changes
- A-Wiki mutation, secrets, provider credentials
## Acceptance

- [ ] graph database reads use SQLite read-only mode and do not create/migrate tables;
- [ ] no implicit latest/current run discovery;
- [ ] planning-only mode is explicitly labelled no-run-evidence;
- [ ] explicit run projection composes GE-7 identity + GE-9 state mapping;
- [ ] queue counts are derived from displayed factual states;
- [ ] timeline is bounded and derived from durable job events only;
- [ ] malformed/missing schema/read failures fail closed with a factual error code;
- [ ] connector MONITOR behavior remains regression-green;
- [ ] Graph view reuses existing monitor timer/future path; no periodic subprocess/network;
- [ ] focused UI/adapter tests, graph regression, GUI suite, smoke/E2E pass;
- [ ] exact-head 3-OS CI, remote diff review, merge and accepted-main verification pass.

## TDD plan

1. RED read-only operator adapter tests: graph ids, no-run planning snapshot, explicit-run lifecycle projection, bounded events, missing graph/schema.
2. GREEN additive read-only adapter.
3. RED UI formatter/mode tests, then add Graph/Connector controls and reuse existing monitor refresh path.
4. Review/debug/deep E2E, then PR/CI/re-audit/merge.

## Review / verification checkpoint — 2026-08-29

Implementation now exposes a factual Graph mode inside the existing MONITOR pane.

- read-only adapter uses SQLite `mode=ro` + `PRAGMA query_only=ON`;
- graph selection is explicit; no latest/current run inference exists;
- requested RUN ID without matching durable jobs/events remains `NO RUN EVIDENCE`;
- proven durable jobs project through GE-9; timeline reads bounded durable job events;
- connector MONITOR/recovery rendering remains on the existing path;
- Graph mode reuses `_monitor_tick_after_id`, `_monitor_future`, `_monitor_poll_after_id`, and the existing background executor.

Staff review found and repaired one provenance defect before commit: merely supplying any RUN ID previously set `runtime_evidence=True`. A deterministic RED test now pins that an unknown run remains no-evidence, while a matching `GraphDispatchKey` durable job enables durable-run evidence.

Local evidence at this checkpoint:

- focused adapter/UI: **15 passed**;
- full `tests/test_graph_*.py`: **182 passed**;
- operator + desktop UI: **63 passed**;
- connector monitor/recovery: **17 passed**;
- usability + all-buttons realistic UI E2E: **70 passed**;
- source compileall: PASS;
- headless smoke with repo `PYTHONPATH=src`: `A-CONDUCTOR_SMOKE_OK projects=0 workers=3`.

Remaining gate: final diff/static/secret/scope review, commit/push, exact-head 3-OS CI, remote re-audit, merge, accepted-main verification.
