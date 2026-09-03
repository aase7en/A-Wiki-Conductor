# Agent Capability / Routing Evidence

This file records routing evidence, not permanent model rankings.
Re-check current upstream evidence before delegating material work to a named model.

## Current researched candidate — GLM-5.3 MAX

Research date: 2026-08-30.
Primary sources: official Z.ai GLM-5.3 launch (published 2026-08-14) + official Claude Code/Coding Plan guidance, re-checked before AHA-6 review delegation.

| Evidence | Observed value | Routing implication |
|---|---:|---|
| Terminal-Bench 3.0 | 28.3 | suitable candidate for bounded terminal/agentic coding |
| DeepSWE v1.1 | 66.9 | suitable candidate for repository implementation/repair |
| Z.ai Code Bench, max effort | 34.5% | use max reasoning for difficult coding tasks |
| Coding Plan / Claude Code support | documented | compatible in principle with the existing Claude-style harness |

These values justify trying GLM-5.3 MAX for bounded implementation/repair.
They do not prove it is best for every task and do not replace GPT/integrator review.

## Fast-execution routing refresh — 2026-09-04

Fresh official ZCode evidence supports using GLM-5.3/ZCode as a sustained bounded implementation engine, not as merge/acceptance authority:
- official ZCode documentation describes GLM-5.3 as integrated for long-horizon coding with stable 1M context and continuity across goals, files, terminal output, execution modes and Git state;
- the same official documentation positions ZCode Agent for planning, coding, debugging, testing and change review inside one task;
- current ZCode execution-mode guidance explicitly recommends lower-interruption modes for clear/routine work and plan/confirm-first behavior for critical or broad changes.

Fresh sources:
- `https://zcode.z.ai/en/docs/welcome` — checked 2026-09-04;
- `https://zcode.z.ai/en/docs/agents` — checked 2026-09-04;
- `https://zcode.z.ai/en/changelog` — checked 2026-09-04.

WO154 routing profile:

| Task class | Preferred role | Notes |
|---|---|---|
| repo archaeology / call-path tracing | GLM-5.3/ZCode | bounded read/search task; return exact symbols/files/evidence |
| routine bounded implementation | GLM-5.3/ZCode | exact task contract + owned worktree/scope; targeted tests |
| mechanical multi-file refactor | GLM-5.3/ZCode | deterministic diff/reference checks remain authority |
| regression/adversarial test generation | GLM-5.3/ZCode | batch cases before independent candidate review |
| debugging / root-cause reproduction | GLM-5.3/ZCode | prefer reproducer/evidence before repair |
| batched repair | GLM-5.3/ZCode | repair confirmed findings together where scope is shared |
| architecture / trust / authorization | GPT integrator | may use GLM read-only challenge/review, but GPT retains design authority |
| cross-lane conflict / SSoT / merge / release | GPT integrator | deterministic evidence + current Git/runtime state required |
| repetitive static/hash/test/build operations | deterministic/native tools | avoid premium-model spend when tools are sufficient |

Model/provider names remain routing choices, never task semantics. Do not hard-code ZCode UI mode or thought-level labels into Conductor contracts because product options may change. Provider readiness/auth/quota/eligibility remains a separate fail-closed gate.

## Current local availability evidence

- Direct Z.ai GLM-5.3 invocation previously reached the provider but returned HTTP 429 / insufficient resource package.
- Installed ZCode 0.16.5 previously reported `builtin:zai-coding-plan` unavailable with `coding_plan_not_entitled`; Start Plan exposed GLM-5.3-Flash rather than full GLM-5.3.
- WO-P1-115 / PR #155 is merged as `a758f9e882db03e988d67a3f04f69862dd9195c2`; exact-head CI `33312763072` and post-main CI `33313201851` passed. It safely bootstraps provider tables and adds atomic provider-global admission in the existing SQLite provider authority; independent GLM review and repair re-review both found zero P0/P1/P2 defects. Installed-DB-copy E2E preserved all 12 existing tables and did not mutate the live DB.
- Cross-process admission E2E proves `max_concurrency=1` yields exactly `ADMITTED,CAPACITY_WAIT`; batch-local snapshots are no longer the production-global capacity authority when the SQLite admission store is injected.
- Current Claude CLI configuration still points to an unavailable loopback route, and current router configuration exposes no proven live GLM/CoinTH profile. Earlier GLM-proxy readiness is historical, not current readiness.
- Official Z.ai quota tooling still exposes `/api/monitor/usage/quota/limit`, but current upstream issue evidence says that endpoint lacks reset time. Because Conductor requires the full five-hour tuple, automatic dispatch remains fail-closed; the one-direction file bridge is the current safe fallback.
- Model suitability, provider route/readiness, quota evidence, credential resolution and atomic provider admission remain independent authorities.

## Routing decision record

For each delegation record:
- task class and why an external model helps;
- evidence source/date;
- provider/model/effort requested;
- current readiness/auth/quota/entitlement observation;
- assigned mutable scope and verification;
- fallback if the provider is unavailable.

## Default role split for AHA-6

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

## WO-P1-114 routing decision - 2026-08-30

Task class: provider/runtime integration with secret/quota trust boundaries.

- GPT-5.6 Sol owns architecture, security boundary, integration adjudication, deterministic verification and merge authority.
- GLM-5.3 MAX is suitable for bounded code archaeology/adversarial review and repair after the implementation contract is exact-SHA pinned; current official Z.ai evidence remains Terminal-Bench 3.0 28.3, DeepSWE v1.1 66.9, Z.ai Code Bench Max 34.5%.
- Automatic GLM execution is itself the capability being assembled, so this work order uses the one-way file bridge until secret/readiness/quota gates are provably available.
- Deterministic repository/tests/CI remain acceptance authority.

## WO-P1-115 routing decision - 2026-08-30

Task class: SQLite concurrency/admission authority, production runtime bootstrap, and provider/quota trust boundaries.

- Official Z.ai GLM-5.3 evidence was refreshed before delegation planning: Terminal-Bench 3.0 `28.3`, DeepSWE v1.1 `66.9`, Z.ai Code Bench Max `34.5%`; Z.ai notes meaningful human-in-the-loop work remains.
- GPT-5.6 Sol owns architecture, atomic-concurrency design, trust boundaries, integration adjudication, deterministic verification and merge authority.
- GLM-5.3 MAX is suitable for later bounded adversarial/concurrency review after an exact-SHA snapshot exists; current local provider readiness is insufficient for automatic dispatch.
- No model name may imply a quota endpoint. Provider-matched readiness/quota evidence must be proven independently; otherwise dispatch fails closed.
- Deterministic repository tests, race/E2E evidence and CI remain acceptance authority.


## WO-P1-116 routing decision - 2026-08-30

Task class: production worker/candidate assembly, atomic elastic-capacity reservation, and concurrency/ownership safety.

- Official Z.ai GLM-5.3 evidence was refreshed immediately before claim: Terminal-Bench 3.0 `28.3`, DeepSWE v1.1 `66.9`, Z.ai Code Bench Max `34.5%`; Z.ai explicitly notes meaningful human-in-the-loop work remains.
- GPT-5.6 Sol owns architecture, cross-process capacity authority, trust/ownership adjudication and merge/release authority.
- GLM-5.3 MAX is suitable for a later bounded deterministic implementation or read-only adversarial review lane after exact scope/HEAD/task packet pinning.
- Deterministic tests, race/chaos evidence and actual Git/runtime state remain acceptance authority; model `DONE` claims are never sufficient.
- Automatic provider dispatch is independent and remains fail-closed until provider route/readiness/full quota evidence is proven.

## WO-P1-116 routing refresh ? 2026-08-31

Official Z.ai GLM-5.3 evidence was refreshed again before review routing: Terminal-Bench 3.0 `28.3`, DeepSWE v1.1 `66.9`, Z.ai Code Bench Max `34.5%`. This continues to support bounded repository archaeology/adversarial review, not architecture or merge authority.

For the now-implemented concurrency slice, GPT-5.6 Sol keeps worker-capacity authority design, defect adjudication and release ownership. GLM's next useful lane is independent exact-SHA read-only review with pinned file hashes and structured `result.json`; no overlapping source mutation is permitted. Provider route/readiness/credential/quota admission remains a separate fail-closed gate from model suitability.

## WO-P1-116 routing closeout - 2026-08-31

- GPT-5.6 Sol retained integration/release authority; exact reviewed head passed all deterministic gates.
- GLM-5.3 MAX independent review returned validated PASS with zero P0/P1/P2; four P3 observations are non-blocking follow-up.
- Post-main CI `33354156749` passed Windows/Ubuntu/macOS including Windows Frozen Setup E2E on merge `af5a5068aea37ce82875e4b6fff40ac19ac112c5`.
- Future Ultra/GLM read-only shaping may run concurrently, but tracked mutation requires a fresh work-order/claim/repository gate.


## Post-AHA-6B multi-model routing — 2026-08-31

- GPT-5.6 Sol Ultra is effective for broad parallel architecture/adversarial shaping: `gpt56-ultra-frontier-001` found multiple source-confirmed P1 integration hazards missed by the narrower AHA-6B exact-SHA review. It remains advisory until the integrator verifies source evidence and claims a bounded WO.
- GLM-5.3 MAX remains a strong bounded code-review/hardening agent: `glm53-capacity-hardening-001` confirmed all four AHA-6B P3 risks with exact symbols/tests and a conservative AHA-4B-compatible recovery plan.
- GPT-5.6 Sol integrator retains cross-store authority design, finding adjudication, shared SSoT, PR/merge/release authority and conflict serialization.
- Next parallel routing: integrator→117, Ultra→119, GLM→120. 118 stays queued behind 117 because file ownership overlaps.
