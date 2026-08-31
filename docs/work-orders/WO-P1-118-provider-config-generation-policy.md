# WO-P1-118 — Provider Configuration Generation + Trust/Egress Policy Gate

Date: 2026-08-31
Owner: split — GLM-5.3 MAX (118A implementation), GPT-5.6 Sol integrator (118B architecture/merge)
Status: ACTIVE — WO-P1-118A READY; WO-P1-118B BLOCKED_ON_WO-P1-120
Repository: `aase7en/A-Wiki-Conductor`
Priority: P1 before automatic live provider dispatch

## Goal

Bind provider health/admission to the exact configuration generation that was observed, and make declared trust/egress metadata an actual fail-closed production policy input before secret resolution or launch.

## Evidence

Ultra R3/R4 were source-confirmed by the integrator:
- endpoint/profile rows overwrite independently and current observations bind only `provider_id`, not a configuration generation;
- changing endpoint/model/credential-reference/trust can therefore leave an older health observation apparently usable;
- `trust_class` / `egress_boundary` occur in configuration and tests, but no production `src/` policy consumer was found outside the configuration/storage boundary.

Classification: `EXTEND` existing provider configuration/observation/admission authority. Do not create another provider registry, secret store, quota ledger or router.
## Expected scope

- `src/a_conductor/provider_configuration.py`
- `src/a_conductor/provider_config_store.py`
- `src/a_conductor/provider_runtime_assembly.py`
- one bounded additive policy evaluator/decision type only if RED proves no accepted seam exists
- focused provider configuration/runtime tests

## Acceptance direction

1. Endpoint/provider saves are versioned or CAS-protected so stale editor/probe completion cannot authorize a newer configuration.
2. Provider observations carry and validate exact configuration generation; mismatched/stale generation is unavailable, never ready.
3. Admission and launch revalidate enabled/config generation before secret resolution/use.
4. Actual task trust/egress policy denial occurs before credential access, provider launch and elastic expansion.
5. Missing/unknown policy or quota evidence fails closed with typed reasons.
6. No endpoint health for one route authorizes another route/proxy/model implicitly.
7. Installed DB migration preserves existing user provider state and old rows become conservative/unknown until re-observed.

## Ordering

Do not implement concurrently with WO-P1-117 because both own `provider_config_store.py`. Begin only after WO-P1-117 releases that file and its admission-lifetime contract is stable. May overlap later UI read-model work if central provider store files are read-only to the UI lane.
## Integrator shaping checkpoint — 2026-08-31

Source inspection after WO-P1-117 merged proved the original WO spans two ownership seams and must be executed in two bounded slices rather than expanding scope silently.

### WO-P1-118A — READY / disjoint from PR #162

Allowed source scope remains provider-local only: `provider_configuration.py`, `provider_config_store.py`, `provider_runtime_assembly.py`, optional additive `provider_policy.py`, and focused provider tests.

118A owns:
- store-owned provider/endpoint generations with CAS on updates;
- endpoint update atomically invalidating every provider generation that references it;
- observation generation provenance and conservative migration of legacy observation rows;
- provider resolver/readiness rejecting generation mismatch before secret resolution;
- provider-admission persistence/revalidation seam for configuration generation, with backward-compatible caller wiring deferred to 118B;
- a pure deterministic trust/egress evaluator consuming task-contract security vocabulary only; no scheduler/lease/elastic mutation.

### WO-P1-118B — BLOCKED on PR #162

The accepted task authority already exists in `task-contract/v1`: `privacy_class` (`PUBLIC/INTERNAL/SENSITIVE/SECRET`), `network_policy` (`DENIED/ALLOWLISTED/INHERIT`), `network_allowlist`, and `secret_access`.

Actual pre-elastic enforcement cannot be completed inside the original provider-only scope: `ParallelReadyNodeContract` / `assemble_parallel_ready_tasks()` currently materialize provider execution and are also in WO-P1-120 / PR #162 ownership. Therefore 118B begins only after #162 merges and exact scope is re-gated.

118B must wire the accepted 118A policy decision into the existing scheduler/parallel/worker-candidate execution path so denial occurs before provider admission, worker lease, elastic expansion, credential resolution, or process launch. It must reuse `NodeEligibility`/existing dispatch gates rather than create a second scheduler or router.

### Deterministic RED already reproduced

With persisted provider state, changing the endpoint and credential reference while retaining the old observation produced `STALE_OBSERVATION_STILL_READY=True`. This is the generation-binding RED for 118A. No live provider/credential was used.

### Ordering

`WO-P1-117` is merged and its post-main CI is green. 118A may proceed now. 118B remains blocked until WO-P1-120 / PR #162 releases `worker_candidate_assembly.py` and related capacity seams.
