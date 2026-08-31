# WO-P1-118 — Provider Configuration Generation + Trust/Egress Policy Gate

Date: 2026-08-31
Owner: unassigned
Status: QUEUED / BLOCKED_ON_WO-P1-117
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