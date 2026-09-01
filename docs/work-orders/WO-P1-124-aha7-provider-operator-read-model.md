# WO-P1-124 ? AHA-7A Truthful Provider Operator Read Model

Date: 2026-09-01
Owner: GPT-5.6 Sol integrator
Status: ACTIVE / RED-FIRST
Priority: P1 AHA-7 first READY slice
Base: `origin/main@b1024b354a6fc45faad618a055a55aef3d9954f5`
Branch: `feat/wo-p1-124-aha7-provider-read-model`

## Goal

Create the smallest read-only provider/operator projection needed by the accepted AHA-7 Models & Agents UI. It must truthfully separate configured state from runtime READY state and expose health/quota freshness/provenance/trust without exposing secrets or inventing a second router, quota model, provider registry, or policy authority.

The roadmap explicitly permits this read-only truthful slice while WO118B is under final review. UI wiring and all Edit/Test/Disable actions remain blocked until WO118B is merged and post-main green.

## Reuse classification

`WRAP` accepted `ProviderConfigurationSnapshot`, `ProviderConfiguration`, `ProviderObservation`, `QuotaSnapshot`, and `is_provider_ready()` into a presentation-only immutable read model.

## Mutable scope

- `src/a_conductor/provider_operator_view.py` ? NEW only
- `tests/test_provider_operator_view.py` ? NEW only
- this work order ? NEW only

Forbidden until a later claimed lane: `provider_config_store.py`, provider policy/runtime execution files, `desktop_control.py`, `desktop_ui.py`, CURRENT-WORK/handoff, scheduler/router/secret/runtime mutation.

## Acceptance

1. Deterministic rows expose provider/model/harness, trust/egress, configuration generation, health, freshness/provenance, latency and the existing `QuotaSnapshot`.
2. `configured` and `runtime_ready` are separate; runtime readiness reuses `is_provider_ready()` with exact generation and freshness.
3. Missing endpoint/generation/observation, generation mismatch, stale/future observation, disabled provider and non-AVAILABLE health return stable typed display reasons and never claim READY.
4. Row shape contains no credential reference, endpoint URL, raw secret, provider profile, or secret resolver.
5. Task authorization/selection remains explicitly unevaluated without task context; this module does not become a router/policy engine.
6. Ordering is deterministic and input-order independent.
7. RED-first focused tests, related provider tests, compileall, diff/UTF-8/secret audits pass.
8. Before PR/merge, rebase/reconcile onto exact post-WO118B main and rerun evidence; this pre-merge lane cannot authorize AHA-7 write controls.


## Implementation checkpoint ? 2026-09-01

RED first failed at import because no operator read-model existed. GREEN adds one presentation-only module that consumes `ProviderConfigurationSnapshot` and delegates runtime readiness to accepted `is_provider_ready()` with exact configuration generation and freshness.

Deep bug hunt pinned a critical semantic boundary: runtime readiness is not task authorization. A provider with UNKNOWN trust/egress may still be runtime-healthy, but the row remains `task_authorization=NOT_EVALUATED`; task policy requires later task context and existing policy authority. Naive clocks fail closed. The row shape deliberately omits credential refs, endpoint/base URL and the raw provider profile.

Evidence: focused operator view 21 passed; provider configuration/store/policy + operator matrix 78 passed; compileall, `git diff --check`, UTF-8 and added-line secret scan PASS. No existing tracked source was modified outside the three-file claim.

Status: **IMPLEMENTED / SELF_REVIEWED / BLOCKED_ON_WO118B_POST_MAIN_REBASE**. Before PR, fetch exact post-WO118B main, rebase/reconcile, rerun focused + related evidence, then create an independent review packet. No UI wiring or write/Test/Disable control is authorized by this checkpoint.
