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

## Integrator repair checkpoint — 2026-08-31

GLM implementation commit `438c0a7ca2368888d35098e3f98fd9502f6f9be8` was independently source-reviewed before acceptance. The reported 51 focused / 166 related tests were not treated as authority.

Deterministic integrator fault injection found two release-blocking classes:

1. **Generation integrity rollback / coercion:** repeated `initialize()` rewrote stored generation `0` to `1`; a generation-1 stale observation became READY again after a generation-2 profile was corrupted to zero. Text generations leaked raw `ValueError`, float `1.5` was coerced through `int()`, and `2^63-1 + 1` became SQLite REAL.
2. **Policy metadata/route mismatch:** `LOCAL_MACHINE` / `NO_EGRESS` trusted the declared boundary without checking a supplied endpoint; a SECRET + network-DENIED task was allowed when the profile claimed local egress but the endpoint was external HTTPS.

A separate CAS hole was also reproduced: supplying `expected_generation=1` after the provider/endpoint row disappeared silently recreated generation 1 instead of failing stale.
Repair stays inside the accepted 118A authority:
- legacy `NULL -> 1` migration occurs only in the transaction where the generation column is first added; later corruption is never auto-healed;
- stored generations are exact SQLite integers in `1..2^63-1`, with typed `PROVIDER_GENERATION_INVALID` / `PROVIDER_GENERATION_EXHAUSTED`; no numeric coercion;
- expected-generation updates cannot recreate a missing row and every CAS update verifies `rowcount == 1`;
- endpoint fan-out validates and bounds every referencing provider generation before any mutation, then advances endpoint/providers atomically;
- `LOCAL_MACHINE` / `NO_EGRESS` with a supplied non-loopback endpoint fails `PROVIDER_EGRESS_ENDPOINT_MISMATCH`; explicit loopback and endpoint-less local seams retain intended eligibility.

Verification after repair:
- generation-integrity RED set: 7 passed after initially reproducing all defects;
- provider policy: 12 passed;
- full 118A focused suite: 61 passed;
- provider/admission/parallel/graph/lease related suite: 191 passed;
- no live provider, credential, installed control DB, Worker or tunnel was touched.

**118A is not overall WO118 completion.** Production callers still omit `expected_configuration_generation`, `is_provider_ready(... expected_generation=...)`, and `evaluate_provider_policy()` has no production caller. Resolver -> credential/launch TOCTOU and pre-elastic enforcement remain binding WO118B acceptance work after WO120 releases the shared candidate/elastic seam.

Status: **WO-P1-118A INTEGRATOR_REPAIRED / REVIEW_PENDING; WO-P1-118B BLOCKED_ON_WO-P1-120.**

## Integrator trust/egress repair checkpoint — 2026-08-31

A second GPT adversarial pass after the first PR #165 head found a real policy-classification downgrade: `TRUSTED_THIRD_PARTY` or `LOCAL` combined with `EXTERNAL_FIRST_PARTY` received first-party SENSITIVE treatment because `trust_class` only denied `UNKNOWN`.

RED: two unsafe trust classes returned `POLICY_ALLOWED_EXTERNAL_EGRESS`; the `FIRST_PARTY + EXTERNAL_FIRST_PARTY` positive control already passed.

Repair: `EXTERNAL_FIRST_PARTY` now requires `ProviderTrustClass.FIRST_PARTY`; otherwise policy fails closed with `PROVIDER_TRUST_EGRESS_MISMATCH`. Conservative `EXTERNAL_THIRD_PARTY` behavior remains unchanged, and explicit loopback local/no-egress paths remain eligible.

Verification after repair: targeted `3 passed`; full policy `15 passed`; broader provider/store/runtime/parallel/graph/lease/elastic/Claude supervised stack `254 passed`. The previously generated `wo118a-independent-review-001` packet for head `036acf29...` is superseded and must not be used.
