# WO-P1-124 - AHA-7A Truthful Provider Operator Read Model

Date: 2026-09-01
Owner: GPT-5.6 Sol integrator
Status: COMPLETE / RELEASED
Priority: P1 AHA-7 first READY slice
Base: `origin/main@9c56077817ead3974d7d335daed52c2862a1c82a`
Branch: `feat/wo-p1-124-aha7-provider-read-model`

## Goal

Create the smallest read-only provider/operator projection needed by the accepted AHA-7 Models & Agents UI. It must truthfully separate configured state from runtime READY state and expose health/quota freshness/provenance/trust without exposing secrets or inventing a second router, quota model, provider registry, or policy authority.

The roadmap explicitly permits this read-only truthful slice while WO118B is under final review. UI wiring and all Edit/Test/Disable actions remain blocked until WO118B is merged and post-main green.

## Reuse classification

`WRAP` accepted `ProviderConfigurationSnapshot`, `ProviderConfiguration`, `ProviderObservation`, `QuotaSnapshot`, and `is_provider_ready()` into a presentation-only immutable read model.

## Mutable scope

- `src/a_conductor/provider_operator_view.py` - NEW only
- `tests/test_provider_operator_view.py` - NEW only
- this work order - NEW only

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


## Implementation checkpoint - 2026-09-01

RED first failed at import because no operator read-model existed. GREEN adds one presentation-only module that consumes `ProviderConfigurationSnapshot` and delegates runtime readiness to accepted `is_provider_ready()` with exact configuration generation and freshness.

Deep bug hunt pinned a critical semantic boundary: runtime readiness is not task authorization. A provider with UNKNOWN trust/egress may still be runtime-healthy, but the row remains `task_authorization=NOT_EVALUATED`; task policy requires later task context and existing policy authority. Naive clocks fail closed. The row shape deliberately omits credential refs, endpoint/base URL and the raw provider profile.

Evidence before the final adversarial generation repair: focused operator view 21 passed; provider configuration/store/policy + operator matrix 78 passed; compileall, `git diff --check`, UTF-8 and added-line secret scan PASS. No existing tracked source was modified outside the three-file claim.

Status: COMPLETE / RELEASED


## Deep bug hunt - invalid snapshot generation

Before independent review, GPT adversarial probing constructed otherwise valid `ProviderConfigurationSnapshot` values with generation `0`, `-1`, boolean `True`, and `2^63`. Because the snapshot dataclass itself is intentionally a lightweight read carrier, the presentation layer reported `configured=True` even though the accepted SQLite authority would reject those generations. Runtime readiness stayed false, but the operator-facing configured claim was not truthful for a malformed injected snapshot.

RED: all four invalid-generation cases failed the required `configured=False` assertion. Repair adds presentation-boundary generation validation matching the accepted positive signed-64-bit store invariant and returns `PROVIDER_GENERATION_INVALID`; `None` retains the separate `PROVIDER_GENERATION_UNKNOWN` reason. No store/runtime policy was changed.

Post-repair evidence: focused operator view `25 passed`; provider configuration/store/policy + operator matrix `84 passed`; compileall and `git diff --check` PASS after EOF normalization. The previously prepared WO124 review packet at head `92849864...` is superseded and must not be dispatched.


## Release closeout - 2026-09-01

Independent GLM review002 verified exact head `be97d313c748fe5fcce0e57ecf5dc304b863e230`, task SHA `abe750450dda09dbf423681811efd0110ecfa26914cc55828b133db48a9fcf2b`, and all three pinned file hashes. Verdict: PASS, P0/P1/P2=0. Reviewer reran 25 focused + 84 provider tests and 12/12 adversarial reproductions.

PR #174 exact-head CI `33497483113` attempt 2 passed Windows/macOS/Ubuntu. The reviewed head merged as `c1cfbe780e76d3a64fb692e91dde851824bd8033`. Post-main run `33504441646` attempt 1 hit the unrelated hosted-Windows owned-process transient later fixed by WO129; attempt 2 on the same main SHA passed all three OS plus Windows Portable/Setup and Frozen install/uninstall E2E.

Status: COMPLETE / RELEASED. WO125 may consume this read model; later UI/mutation/test/selection slices must not promote runtime readiness into task authorization or expose secret/endpoint values.
