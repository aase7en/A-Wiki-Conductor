# WO-P1-134 — MODELS & AGENTS Provider Evidence Detail

Date: 2026-09-02
Owner: GLM-5.3 MAX / ZCode Goal + `$a-loop`
Integrator / merge authority: GPT-5.6 Sol
Status: CLAIMED / RED_FIRST_PENDING
Priority: P1 AHA-7B
Base: `b6d50921035ae6ec6d32b6c05b3f723530b8c68d`; WO128 post-main CI `33591789871` GREEN.
Worktree: `A:\GitHub\A-Wiki-Conductor-wo134-provider-evidence-detail`
Branch: `feat/wo-p1-134-provider-evidence-detail`

## Goal
Complete WO128 T2–T4: expose truthful provider selection/fallback evidence in MODELS & AGENTS using only persisted/read-model authority already accepted in WO125–WO128.

## Non-negotiable truth
- `SELECTION_REASON=UNKNOWN` unless a future accepted authority persists a reason.
- `FALLBACK_REASON=NOT_EVALUATED` unless a future accepted fallback authority exists.
- Admission lifecycle is capacity evidence, not execution outcome.
- Declared models/harnesses are capabilities, not per-execution proof.
- No fuzzy task/execution joins and no latest-run inference.

## Dependencies
WO125 read model → WO126 panel → WO127 actions → WO128 T0/T1 core → this WO134 T2/T3/T4.
WO096 remains a separate P0 release blocker and is forbidden here.

## Mutable scope
- `src/a_conductor/desktop_control.py`
- `src/a_conductor/desktop_ui.py`
- `src/a_conductor/i18n.py`
- `src/a_conductor/error_explanations_en.py` only for genuinely user-facing typed evidence errors
- `tests/test_desktop_control.py`
- `tests/test_models_agents_panel.py`
- `tests/test_i18n.py`
- `tests/test_graph_operator_ui.py` for exact-link reuse tests only
- this work order, bounded USER-GUIDE TH/EN and CHANGELOG rows

## Forbidden
- `src/a_conductor/provider_config_store.py` write/read authority changes
- `src/a_conductor/provider_selection_observability.py` authority expansion
- `src/a_conductor/graph/**` production mutation
- scheduler/job/execution/parallel/elastic/provider policy/readiness/runtime assembly
- provider endpoint/credential resolution or display
- live control DB, Workers, tunnels, WO096, version/release publication

## Required facade
Read admissions first → query-only snapshots second → exact provider match → one aware UTC clock → operator row + pure selection evidence.
Do not call write-capable/bootstrap `load_provider_snapshot()` from operator evidence.
Missing target after second read is typed and fail-closed.

## UI contract
- Add canonical-English `Evidence...` action on the second status/action row; localized TH/en/zh-CN tooltip/help.
- One evidence Toplevel for the selected provider; reuse/refresh instead of stacking dialogs.
- Copyable CLI-style text via existing `_enable_copyable_text()`.
- Render selection/fallback constants on every successful detail view.
- Show current operator evidence and declared capabilities separately from admission rows.
- Show up to N newest admissions in store order; never claim `has_more` without authority.
- Evidence fetch is background-only, single-flight, request-generation guarded and teardown safe.
- Language switch re-renders cached evidence with zero DB I/O.
- Preferences close destroys/invalidates the detail and any late completion.

## Graph-link contract
Only when an explicit Graph Monitor `graph_id` + `graph_run_id` already exist: derive each visible node's `GraphDispatchKey(...).job_id` and exact-compare with admission `execution_id`.
Exact match may expose node id / Show Graph. Otherwise show `NO_READABLE_GRAPH_EVIDENCE`.
Never search all graphs, infer latest run, fuzzy-match ids, or alter graph state.

## User-facing error contract
Persisted `PROVIDER_ADMISSION_RECORD_INVALID` must have TH/EN teaching coverage and render as an error, not empty evidence.
Internal invalid limit/filter codes are unreachable from fixed UI parameters.
Use a dedicated typed evidence-target-unavailable code for provider disappearance; do not reuse Test-specific wording.

## RED-first acceptance
1. Prove admissions-before-snapshot call order and released-generation race becomes `STALE_VS_CURRENT`.
2. Missing/corrupt evidence is typed; never partial/empty truth.
3. Selection/fallback constants do not vary under healthy/failing/multi-admission fixtures.
4. No cross-provider ranking/correlation API appears.
5. Background executor only; rapid refresh single-flight; no Tk-thread store read.
6. Close/provider switch discards late future with no TclError/orphan window.
7. TH/en/zh-CN evidence keys complete; language switch re-renders cache without I/O.
8. Secret/base-url/credential sentinel scan over every evidence widget is zero hits.
9. Exact explicit graph identity links; near-miss/no-run context does not.
10. Real temp SQLite E2E covers observation + ACTIVE/RELEASED/EXPIRED admissions + generation drift + graph context.
11. Focused → impact → GUI/i18n → graph UI → real Tk → full suite → compileall/diff/UTF-8/secret/scope audits.
12. Independent exact-head review after freeze; P0/P1/P2 block merge.

## Completion
Commit/push exact SHA → draft PR → remote diff audit → exact-head CI → re-audit → merge expected SHA → fetch/reconcile → post-main CI/Frozen Setup E2E → Defect Memory + CURRENT-WORK/handoff/AGENT_TASKS checkpoint → next ready node.
