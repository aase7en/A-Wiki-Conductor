# WO-P1-128 — Selection/Fallback Observability Core (T0+T1)

Date: 2026-09-02
Owner: GLM-5.3 MAX / ZCode long-goal lane
Integrator: GPT-5.6 Sol
Status: RELEASED / MERGED / POST_MAIN_GREEN
Priority: P1 AHA-7B
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo128-admissions-evidence-core`
Branch: `feat/wo-p1-128-admissions-evidence-core`
Base: `origin/main@af7a933fe27d2a3e3f29360abf9214df1e5478c5`

## Goal

Implement only the non-UI WO128 core: (T0) a bounded read-only provider-admissions listing seam following WO125 read discipline, and (T1) a pure typed evidence projection that never invents provider selection or fallback reasons.

Mandatory truth:
- `SELECTION_REASON = UNKNOWN` when no persisted authority exists.
- `FALLBACK_REASON = NOT_EVALUATED` when no persisted authority exists.
- Admission evidence may describe grants/lifecycle only; it is never a router decision.
- Missing, stale, corrupt, and not-evaluated are distinct states.
## Mutable scope

- `src/a_conductor/provider_config_store.py`
- `tests/test_provider_config_store.py`
- new pure module `src/a_conductor/provider_selection_observability.py`
- new focused tests `tests/test_provider_selection_observability.py`
- this work order only before dispatch; external agent must not edit it.

## Forbidden scope

- `src/a_conductor/desktop_ui.py`, `src/a_conductor/i18n.py`
- `src/a_conductor/desktop_control.py`
- provider write/admission acquisition/release semantics
- provider policy/readiness/router/scheduler/runtime/execution code
- graph/job/execution stores
- shared `CURRENT-WORK.md`, `handoff.md`, `AGENT_TASKS.md`, `DEFECT_LESSONS.md`, README
- live provider DB, Workers, tunnels, credentials, release/version files

## T0 acceptance

Add a read-only list seam with optional provider filter and bounded limit. Reuse `_admission_from_row`; open the existing DB read-only; no initialize/DDL/`BEGIN IMMEDIATE`; deterministic newest-first order; corruption is typed and fail-closed; no N+1 or mutation.
## T1 acceptance

Create a pure projection over provider/admission evidence. It may compare admission configuration generation to current generation and expose exact evidence timestamps/IDs/status, but it must not rank providers, infer a selected provider, infer fallback, recompute policy, or claim execution outcome from expiry.

Required adversarial cases:
- no admissions vs store/schema/read error are distinct;
- old admission generation is marked stale evidence;
- near-miss execution/task IDs are never joined/inferred;
- ACTIVE past expiry is unknown/reconcile evidence, not `RUNNING` truth;
- corrupt admission row fails typed, never partially renders/projections;
- two-provider failure fixture still yields fallback `NOT_EVALUATED` for each independently;
- projection accepts one provider at a time so cross-provider ranking is structurally absent.

## Verification / completion

Use RED-first tests, focused + provider impact matrix, repeated equal/corrupt/stale cases, compileall, `git diff --check`, strict UTF-8 and scope audit. Do not commit/push/merge. Write the declared ignored `result.md` with exact HEAD, diff, tests, findings and remaining risks. GPT integrator remains commit/PR/merge authority.

Long-goal execution should use the installed `$a-loop` workflow for decompose -> execute -> verify -> distill, but must keep this bounded WO as the only goal and must not route mutation to another model or expand scope automatically.

## GPT integrator verification

- GLM handoff: `READY_FOR_INTEGRATOR_REVIEW`; GPT independently reran the focused and impacted matrices.
- GPT found and repaired a merge-blocking newest-first LIMIT defect: ISO timestamp text is not chronologically sortable when canonical rows mix whole and fractional seconds, and valid timezone offsets can also cross the LIMIT boundary incorrectly.
- Final ordering uses a connection-local deterministic SQLite function backed by the existing typed datetime decoder to canonicalize accepted timestamps to fixed-width UTC microseconds before LIMIT, with admission ID as the stable exact-instant tie-break; malformed/naive timestamps are prioritized to the typed decoder rather than hidden beyond LIMIT. This supersedes an intermediate `julianday` repair after GPT proved SQLite precision loss at sub-millisecond offset boundaries.
- Added explicit fractional-second, timezone-offset, and sub-millisecond offset boundary regressions.
- Final local verification: WO128 focused 21 passed; provider impact 97 passed; broader admission/execution consumers 87 passed; compileall/diff-check/strict UTF-8/scope audit PASS.
- GPT remains commit/PR/merge authority; exact-head CI and independent post-freeze review remain required before merge.

## GPT pre-review persisted-corruption repair

- Before dispatching the frozen independent review, GPT adversarially inserted writer-invalid persisted admission identities and status values. RED proved `list_provider_admissions()` accepted blank `admission_id` / `provider_id` / `execution_id` / `batch_id` and an invalid persisted status instead of honoring T0 typed fail-closed corruption semantics.
- The canonical `_admission_from_row` decoder now validates those persisted identity/status invariants and maps corruption to `PROVIDER_ADMISSION_RECORD_INVALID`; generation corruption retains its existing specific typed code. The projection remains a pure consumer of already store-typed records rather than duplicating persistence validation.
- RED: 5/5 intended corruption cases failed before repair. GREEN: 5/5 pass after repair. Updated focused WO128 matrix: 26 passed; provider impact: 150 passed; broader execution/parallel consumers: 167 passed.
- The superseded review mailbox was explicitly put on HOLD before source mutation; no independent WO128 review had started and no result existed. A new exact-head packet is required after commit/push/CI freeze.

## Final acceptance checkpoint — 2026-09-02

- Final exact head: `a9f4fe6a92367650e7c22caaa9df9e8c148cf3ad`.
- GLM exact-head review `wo128-glm-review-002`: **PASS**, P0=0, P1=0, P2=0, P3=4.
- Exact-head CI `33586307363`: SUCCESS across Windows/Ubuntu/macOS.
- PR #184 merged exact head as `b6d50921035ae6ec6d32b6c05b3f723530b8c68d`.
- Post-main CI `33591789871`: SUCCESS including Windows packaging and Frozen Setup install/uninstall E2E.
- Truth remains `SELECTION_REASON=UNKNOWN` and `FALLBACK_REASON=NOT_EVALUATED`; no selection/fallback authority was added.
- T0/T1 source claim is released; WO134 owns the subsequent T2-T4 UI/detail integration.
