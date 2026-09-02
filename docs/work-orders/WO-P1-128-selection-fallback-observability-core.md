# WO-P1-128 — Selection/Fallback Observability Core (T0+T1)

Date: 2026-09-02
Owner: GLM-5.3 MAX / ZCode long-goal lane
Integrator: GPT-5.6 Sol
Status: INTEGRATOR_VERIFIED / READY_FOR_PR
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
