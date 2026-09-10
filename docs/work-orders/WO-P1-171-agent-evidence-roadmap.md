# WO-P1-171 — Evidence-Native Agent Engineering Roadmap

Date: 2026-09-10
Owner: GPT-5.6 Sol integrator
Status: ROADMAP_CAPTURED / GLM_READ_ONLY_AUDIT_READY / DRAFT_PR_244
Priority: P1 SAFETY-ACCELERATOR / FUTURE CAPABILITY
Risk: R2 architecture/governance docs
Repository: `aase7en/A-Wiki-Conductor`
Branch: `docs/wo-p1-171-agent-evidence-roadmap`
Base: `origin/docs/wo-p1-170-provider-settings-roadmap@2b5ecaab309f9db031c06b24ba8490c9db61013a`
Parent dependency: Draft PR #243 / WO-P1-170

## User outcome

Extend the future A-Sunday Conductor roadmap with source-verifiable patterns from current AI engineering practice and public developer communities. Prefer reuse/copy-and-adapt where license and architecture allow it; do not rebuild a framework just because its idea is useful.

This WO is roadmap-only. It does not authorize runtime/source changes, package installation, telemetry export, provider traffic, memory promotion, secret access, or changes to active higher-priority implementation lanes.

## Reuse-before-build

Classification: `REUSE + WRAP + EXTEND`; `BUILD` only after a future implementation WO proves the capability is missing. A-Conductor already owns durable jobs, worker/provider admission, execution/recovery, ReviewBus integration, orchestration evidence, and operator state. AEET extends those authorities; it is not another scheduler, trace SSoT, router, memory store, or review lifecycle.

## External evidence basis

Canonical research synthesis is in A-Wiki `docs/research/agent-engineering-evidence-20260910.md`: Ponytail minimality benchmarks, Pydantic AI durable execution, smolagents/OpenTelemetry instrumentation, SWE-agent trajectories, OWASP agent security, AgentDojo/AgentDyn adversarial evaluation, and Aider trust-boundary failure evidence.

## Roadmap decision

Add **Agent Efficiency, Evidence & Trust Plane (AEET)** as planned future work:
1. AEET-0 evaluator self-test/baseline;
2. AEET-1 risk-adaptive minimality;
3. AEET-2 effective policy/capability attestation;
4. AEET-3 local-first structured trace;
5. AEET-4 replay/operation identity audit;
6. AEET-5 inter-agent provenance/taint;
7. AEET-6 adversarial security pack;
8. AEET-7 accepted-run efficiency/quality scoreboard;
9. AEET-8 sanitized feedback to A-Wiki.

## Priority overlay

- Existing P0/READY authority and Zero-Relay stay ahead of AEET.
- WO168/169 current review/continuity work keeps existing authority.
- WO170/PR #243 remains the stacked parent until reconciled.
- Read-only evidence preparation may proceed in parallel now.
- AEET-0 is normally the first future implementation candidate after a fresh gate; AEET-2/5 are assessed as possible scale-up prerequisites; AEET-3 precedes AEET-7; AEET-4 is audit-first and may close as REUSE; AEET-1 stays gated by project-specific A/B safety evidence.
- No node is READY merely because it appears in this roadmap.

## GPT × GLM parallel contract

GPT-5.6 Sol owns architecture, cross-repo authority mapping, sequencing, trust/security adjudication, exact-SHA acceptance, merge, and release.

GLM/ZCode receives one focused read-only evidence audit, improving existing Issue #233 without opening a competing owner map or consuming a mutable implementation slot.

### Task packet `GLM-XREPO-EVIDENCE-RO1`

Status: `READY / READ_ONLY / PARALLEL_SAFE / NO SOURCE MUTATION`

Goal: prove which A-Wiki/A-Sunday Conductor capabilities already satisfy A-Wiki Phases 12–17 and AEET-0..8, identify only real gaps, and propose the smallest reuse-first future slices.

Startup:
1. fetch both repos and record exact live SHAs;
2. A-Conductor: `00-AGENT-ENTRY -> PROJECT-GRAPH -> AGENTS -> actual Git/claims -> CURRENT-WORK -> COLLAB -> WO171 -> PROJECT-PLAN`;
3. A-Wiki: `BRAIN-ENTRY -> PROJECT-GRAPH -> AGENTS -> COLLAB -> evidence WO -> research evidence -> vNext roadmap`;
4. inspect Issue #233 and use it as the authority-dedup destination;
5. recover live PRs/branches/claims before relying on older docs.

Required result table:
`roadmap node | existing owner | exact path/symbol/test evidence | OWNER/CONSUMER/ADAPTER/FALLBACK | REUSE/WRAP/EXTEND/BUILD | proven gap | risk | dependency | smallest next slice`.

Also identify `REUSE / NO NEW IMPLEMENTATION` candidates, evaluator fixtures from existing defects, stale/conflicting authority docs, and blockers as `UNVERIFIED`. Finish with exactly one recommended next safe mutation candidate or `NONE`.

Forbidden: any repo mutation; implementation branch/worktree/claim creation; WO168/169/Zero-Relay worktrees; provider credentials/config, workers/processes, DB/private Drive/secrets; a second scheduler/task/review/claim/lease/model-policy/trace/memory authority; hidden chain-of-thought/private tool payloads.

Result destination: one durable Issue #233 comment titled `GLM-XREPO-EVIDENCE-RO1 RESULT`, including exact inspected SHAs. Do not merge.

Known blocker semantics: latest Windows independent ZCode review attempt recorded `CoinTH/Anthropic HTTP 401 invalid_key` before model execution. If still current, classify `UNVERIFIED / PROVIDER_TRANSPORT_BLOCKED`; never weaken auth or expose a credential.

## Mutable scope

Roadmap capture only: `COLLAB.md`, `PROJECT-PLAN.md`, this WO. No source/tests/private/runtime mutation.

## Dispatch checkpoint

This tracked WO is the stable pointer. At task start, pin live PR #59, PR #244, PR #243, current A-Conductor `main`, and claims. Execute only `GLM-XREPO-EVIDENCE-RO1`. GPT continues architecture/reconciliation. No AEET implementation, merge, live-provider mutation, or priority inversion is authorized.