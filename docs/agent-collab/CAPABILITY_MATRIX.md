# Agent Capability / Routing Evidence

This file records routing evidence, not permanent model rankings.
Re-check current upstream evidence before delegating material work to a named model.

## Current researched candidate — GLM-5.3 MAX

Research date: 2026-08-29.
Primary source: official Z.ai GLM-5.3 materials reviewed before AHA-5 delegation.

| Evidence | Observed value | Routing implication |
|---|---:|---|
| Terminal-Bench 3.0 | 28.3 | suitable candidate for bounded terminal/agentic coding |
| DeepSWE v1.1 | 66.9 | suitable candidate for repository implementation/repair |
| Z.ai Code Bench, max effort | 34.5% | use max reasoning for difficult coding tasks |
| Coding Plan / Claude Code support | documented | compatible in principle with the existing Claude-style harness |

These values justify trying GLM-5.3 MAX for bounded implementation/repair.
They do not prove it is best for every task and do not replace GPT/integrator review.

## Current local availability evidence

- Direct Z.ai GLM-5.3 invocation reached the provider but returned HTTP 429 / insufficient resource package.
- Installed ZCode 0.16.5 reports `builtin:zai-coding-plan` unavailable with `coding_plan_not_entitled`.
- Installed ZCode Start Plan is available, but its active model set currently exposes GLM-5.3-Flash rather than full GLM-5.3.
- The user also has a working external Claude-CLI GLM proxy profile, but its credential is intentionally outside tracked project state.
- Therefore AHA-5 must distinguish **model suitability** from **provider entitlement/readiness** and from **credential/profile integration readiness**.

## Routing decision record

For each delegation record:
- task class and why an external model helps;
- evidence source/date;
- provider/model/effort requested;
- current readiness/auth/quota/entitlement observation;
- assigned mutable scope and verification;
- fallback if the provider is unavailable.

## Default role split for AHA-5

**Integrator/reviewer:** GPT-5.6 Sol — architecture, trust boundaries, deterministic
review, integration, PR/merge/release authority.

**Candidate implement/repair agent:** GLM-5.3 MAX when current provider readiness permits.
It receives a bounded task packet and returns a structured proposal; it does not own merge
or acceptance authority.

**Future agents:** use the same packet/lease/result contract. Do not encode lifecycle rules
from provider names.

## Evidence discipline

Prefer official model/provider documentation plus reproducible repository evidence.
Community leaderboards may supplement routing decisions but should not be the sole authority.
If evidence is stale or the task class changes materially, research again before delegation.
