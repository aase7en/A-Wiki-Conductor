# WO-P1-231 — Conductor pivot Phase-0 read-only reconciliation

Status: PHASE0_COMPLETE / SAFE_TO_MUTATE_SRC=NO / DOCS_BOOTSTRAP_ONLY (this WO + GE-0008)
Date: 2026-09-13
Parent: Issue #317 (pivot pointer) / product roadmap reconciliation
Author: GLM-5.3 Phase-0 lane (read-only; docs-only bootstrap per 00-AGENT-ENTRY exception)
Adjudicator: GPT-5.6 Sol
Companion ADR: `docs/adr/GE-0008-conductor-pivot-executor-neutral-control-plane.md`

This WO IS the required Phase-0 durable report (14 items, §1–§14). A fresh
session with no chat history can recover the pivot state and next action from
this file + GE-0008 + Issue #317/#214 alone.

## 1. Actual Git/GitHub/runtime state (verified 2026-09-13, read-only)

- Repository: `https://github.com/aase7en/A-Wiki-Conductor.git` (verified remote).
- origin/main = **251df211afc1ee5452f3652675d7a2f38c526876** ("Merge pull request #312" — WO224 fold). 114 modules in `src/a_conductor/` + `graph/` subpackage (12 files).
- Root checkout `A:\GitHub\A-Wiki-Conductor`: branch `main` @ `f4ecf9a` — **~230 merges BEHIND origin/main** (PR-#80 era; no WO158+ modules present locally there). Dirty with the user-protected `assets/donate-promptpay-qr.png` + untracked artifacts. Never use as authority; never fast-forward without explicit user instruction (protected checkout).
- 245 registered worktrees (mostly historical detached evidence lanes); active branch lanes listed in §4.
- Open PRs (all draft except #313): #314 WO226 (head `fa85dce`), #316 WO229, #313 WO228, #310 WO227, #309 WO205 Phase-D refresh, #308/#307/#306/#305/#304 docs packets.

## 2. Current main SHA

`251df211afc1ee5452f3652675d7a2f38c526876` (re-pinned via fetch; `git log` verified).

## 3. Local branch/worktree/dirty state

- Root: stale + protected-dirty (see §1). 
- This Phase-0 lane: fresh isolated worktree `A:\GitHub\_worktrees\A-Wiki-Conductor-pivot-phase0`, branch `docs/pivot-2026-09-13-phase0` from origin/main, docs-only files (this WO + GE-0008). No `src/` mutation anywhere in Phase 0.

## 4. Active claims / leases / work orders (actual, from Issue #214 — NOT from stale files)

- **WO226** reviewer-execution bridge: PR #314 head **`fa85dce`** — chain d512b1e→653d637→78ec598 (rejected)→609a878→cc398d6 (combined R1+AF1-AF4, CI green)→`fa85dce` (WO226-CR1 "bind terminal cleanup generation + require authority", claim `WO-P1-226-REPAIR-CR1-GLM-001` by a later GLM session). Awaiting independent GPT rereview of `fa85dce`. Astra review branches exist (`review/wo226-astra-final`, `-r1`, `-combined`).
- **WO230** review task-contract authority ("architecture split") + **WO229** ZRA-2 continuity frontier + **WO228** fast-path tool routing (PR #313 open, non-draft) + **WO227** ZRA-3 activation gate + **WO205** Phase-D refresh (PR #309): all Sol-owned docs lanes in flight; Sol's two latest #214 comments (02:18Z "WO230 predecessor frozen/released", 02:23Z "ZRA-2 dependency rewire after WO230 architecture split") are **71–76-char header stubs with no body** — their content must be re-published before the rewire is actionable.
- **WO223/C1** packet ready @ `0c2069a` (PR #305), HOLD_AFTER_WO226.
- No lease/claim authority conflicts with this docs-only Phase-0 lane (no shared hotspot scope).

## 5. Stale / conflicting durable projections (verified conflicts)

1. **CURRENT-WORK.md (main) is STALE** — confirmed: authoritative section dated 2026-09-08 (WO166 P0-B activation, long merged) while the actual frontier is WO226/WO230 (§4). Fold is integrator-owned; do NOT edit from this lane.
2. **COLLAB.md in-progress rows** last meaningfully reconciled 2026-09-07 era; WO22x frontier rows live only in Issue #214. Same integrator-owned fold rule.
3. **Root checkout ~230 merges behind** (§1) — any tooling that reads the root tree sees a phantom old architecture.
4. **Raw pivot roadmap NOT present in local Drive sync** — `A-Wiki-Data/raw/a-conductor/pivot-2026-09/roadmap/A-CONDUCTOR-PIVOT-ROADMAP-2026-09-13.md` absent; recursive search found no PIVOT file; only the Drive file id `1PhXDwcD9RhPALG_fm03bDWC-XaXenwfx` (Issue #317) exists as reference. → **Blocker B1**: the pivot DIRECTION in Issue #317's body + the dispatching goal is rich enough for this reconciliation, but no roadmap-specific detail is binding until the file is ingested (likely unsynced from another device).
5. Sol #214 stub comments (§4) — unreadable bodies.

## 6. SAFE_TO_MUTATE

- `src/**` and all product/runtime state: **NO** — no pivot WO/claim exists yet, the WO22x chain has active owners, and GE-0008 is unadjudicated. (Also per policy: DEFECT_LESSONS read required before any future src mutation — done at heading level this session.)
- Docs-only bootstrap (this WO + GE-0008, clean isolated branch): **YES** — the explicit 00-AGENT-ENTRY bootstrap exception; immediately re-run the mutation gate after this bootstrap before ANY further mutation.

## 7. Reuse audit matrix (KEEP / REUSE / WRAP / EXTEND / DEPRECATE / REMOVE / BUILD)

| Component (src/a_conductor/) | Class | Rationale |
|---|---|---|
| domain.py (TaskState, RecoveryClassification) | KEEP | canonical vocabulary |
| job_store.py SQLiteJobStore (ordered events, checkpoints, CAS) | KEEP | the durable journal |
| job_state/execution/job_control | KEEP | durable execution transaction + facade |
| graph/ (dag, ready, scheduler, dispatch, store, lifecycle_bridge) | KEEP | durable dispatch lifecycle + single-winner CAS (WO226-proven) |
| worker_lease.py (broker, store, intents, scope fencing, release truth) | KEEP | claim/lease authority |
| provider_config_store.py (snapshot generation CAS, admission, list/reread) | KEEP | provider authority |
| provider_configuration / policy / execution_authority / service_authorization / operator_view / selection_observability / runtime_assembly | KEEP | trust/egress/admission stack |
| claude_code_harness.py (+job_assembly/backend/supervised_runner) | KEEP | task packet + dispatch contract vocabulary |
| zcode_production_assembly / runner / protocol / supervised_helper / child_recovery / process_truth | WRAP | Lane-B executor engine (review-hardened); wrap behind Executor Contract, do not fork |
| supervised_execution / supervised_child / supervised_command_runner / owned_process / windows_observer/io | KEEP | process supervision truth |
| execution_store / execution_record / execution_deduplication / execution_artifacts | KEEP | fingerprint/dedup/multiplicity authority |
| zero_relay.py + zero_relay_review_task + zero_relay_review_execution + repair_materializer | KEEP | Zero-Relay review pipeline (pivot-critical asset) |
| parallel_ready_execution.py | KEEP | lease+dispatch+admission composition |
| continuity_guard / continuity_projection / goal_closeout / agent_change_packets | KEEP | continuity/recovery/fold authority |
| recovery_reconciliation / transport_recovery / lifecycle_* | KEEP | recovery authority |
| registry.py (worktree keys) / native_git_transactions | KEEP | worktree/Git safety |
| operator_dispatch / operator_protocol / operator_wire / telegram_operator_commands / telegram_operator_render | EXTEND | existing remote-operator channel — first candidate surface for ChatGPT-Mobile command path (decision gate in WO-237) |
| control_center / control_events / desktop_control / desktop_app / desktop_ui | KEEP (deprioritize UI work) | future Mission Control; Phase 7 defers |
| serena_* (runtime, lifecycle_backend, transport_adapter, operations, settings) + worker_serena_settings | KEEP (WRAP later) | Sunday Worker = specialized executor, not orchestrator (matches pivot) |
| instance_* + local_instances + instance_templates_sh | KEEP | fleet management |
| tunnel_boundaries.py (+ Drive tunnel secrets, untouched) | KEEP | remote-access substrate that replaces AnyDesk |
| memory_presence / fault_injection / system_metrics / update/upstream check / i18n / branding / splash / logos / setup_wizard / config_blurbs | KEEP | product UX; nothing to strip |
| **executor contract module (executor-neutral port/descriptor)** | **BUILD** | the one new minimal seam (WO-232) |
| **kilo adapter (CLI/headless/session)** | **BUILD** | thin, no Kilo reimplementation (WO-233) |
| **mobile gateway (status/approval/command API)** | **BUILD or EXTEND operator wire** | decision gate WO-237 |
| generic editor / terminal agent / chat UI / MCP server / diff viewer / subagent framework | n/a — DOES NOT EXIST in src/ | Phase-6 challenge: nothing duplicated to DEPRECATE/REMOVE; desktop app is already control-center-shaped, not an IDE |

No second scheduler/task/claim/lease/state/review/recovery authority is introduced anywhere.

## 8. Existing modules that already satisfy the Executor Contract

Contract items 2–12 (capabilities, readiness, dispatch, three-identity execution model, binding, status, results, cancellation, recovery/attach, evidence identity, failure classification) are satisfied TODAY by: `parallel_ready_execution.py` + `worker_lease.py` + `graph/dispatch.py` + `job_execution.py` + `zcode_production_assembly.py`/`zcode_runner.py` + `supervised_execution.py`/`owned_process.py` + `execution_store.py`/`execution_deduplication.py` + `agent_change_packets.py` + `recovery_reconciliation.py` (deepest parts proven by WO226's accepted-through-rereview chain). Missing: executor-neutral descriptor/port (item 1 + adapters) — the only BUILD.

## 9. Smallest proposed Executor Contract

See GE-0008 §4 (12 items). Durable contract stays free of provider UI concepts; adapters translate.

## 10. Proposed Pivot ADR structure

GE-0008 (created in this bootstrap): decision, verified evidence basis, target architecture, minimal contract, explicit non-decisions (raw-roadmap gate, WO230 reconciliation, no removals, gateway choice), P0 sequence, consequences.

## 11. Proposed Work Order sequence (numbers provisional, Sol assigns)

P0-0 WO-231 (this) → P0-1 GE-0008 adjudication → WO-232 Executor Contract → WO-233 Kilo adapter → WO-234 ZCode/GLM conformance (WRAP) → WO-235 dual-executor parallel + cross-review proof → WO-236 recovery fail-closed matrix → WO-237 mobile control/status/approval API → WO-238 E2E Zero-Relay proof (metric: 0 human-relay actions per accepted external-agent task). AnyDesk-removal may pull WO-237 earlier if operator-wire EXTEND proves cheap.

## 12. Two-lane GPT/GLM development plan

- Lane A (Kilo + GPT-5.6 Sol): architecture-sensitive implementation, difficult integration, hard debugging, high-reasoning work.
- Lane B (Claude Code/ZCode + GLM-5.3): bounded implementation, tests, mechanical refactor, repair batches, archaeology, long scoped runs.
- Cross-review default: GLM candidate → GPT/Kilo review; GPT candidate → GLM independent review. Deterministic Git/tests/CI = completion authority.
- Parallel mutation gates: both READY + separate owned worktrees + valid claims + disjoint scopes + fan-in plan. WIP: ≤3 mutable lanes + 1 read-only review lane.

## 13. Risks / blockers

- **B1 (blocker)**: raw roadmap file absent from local Drive sync — ingest + reconcile before binding any roadmap-specific detail.
- **B2**: WO230 "architecture split" + ZRA-2 rewire stubs (unreadable #214 bodies) may re-scope the same seams GE-0008 targets — Sol must reconcile GE-0008 ↔ WO230 before WO-232.
- **B3**: WO226 rereview (fa85dce) unblocks the chain the pivot reuses (reviewer-execution bridge = contract's deepest proof).
- **B4**: root checkout stale + protected — all lanes MUST branch from origin/main (convention already followed by WO158+ lanes).
- **B5**: CURRENT-WORK/COLLAB stale — integrator fold needed (not executor-owned).
- **B6**: Kilo CLI/headless surface unaudited on this host (WO-233 starts with its own archaeology).
- **B7**: mobile gateway security/secrets — no credentials in repo; ride tunnel/operator substrate; ChatGPT→Conductor transport medium itself unverified.
- Risk: paying executors (Kilo/GPT credits) — any PAYG needs explicit user approval (goal rule, reaffirmed).

## 14. Exact next safe action

1. GPT-5.6 Sol: ingest the raw roadmap (B1), publish the two stubbed #214 comments' content, adjudicate GE-0008 + reconcile with WO230 (B2), then issue WO-232 (Executor Contract) as a bounded packet.
2. In parallel (independent): independent GPT rereview of WO226 `fa85dce` on PR #314 (B3) — unblocks the ZRA-2/review chain the pivot reuses.
3. Until 1+2 land: `SAFE_TO_MUTATE = NO` for pivot source work; no executor may start WO-232/233 from this bootstrap alone.

## Checkpoint

- Phase-0 lane wrote ONLY: this WO + GE-0008 on branch `docs/pivot-2026-09-13-phase0` (worktree `A:\GitHub\_worktrees\A-Wiki-Conductor-pivot-phase0`, base `251df21`). No src/tests/COLLAB/CURRENT-WORK/handoff mutation. merge_performed=false. Human-relay actions in this Phase 0: 0.
