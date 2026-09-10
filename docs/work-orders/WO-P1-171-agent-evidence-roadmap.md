# WO-P1-171 — Evidence-Native Agent Engineering Roadmap

Date: 2026-09-10
Owner: GPT-5.6 Sol integrator
Status: ROADMAP_CAPTURED / GLM_READ_ONLY_AUDIT_READY / DRAFT_PR_244
Priority: P1 SAFETY-ACCELERATOR / FUTURE CAPABILITY
Risk: R2 architecture/governance docs
Repository: `aase7en/A-Wiki-Conductor`
Branch: `docs/wo-p1-171-agent-evidence-roadmap`
Base: `origin/docs/wo-p1-170-provider-settings-roadmap@2b5ecaab309f9db031c06b24ba8490c9db61013a`
Parent dependency: Draft PR #243 / WO-P1-170 (claim released; PROJECT-PLAN delta unmerged)

## User outcome

Extend the future A-Sunday Conductor roadmap with source-verifiable patterns from current AI engineering practice and public developer communities. Prefer reuse/copy-and-adapt where license and architecture allow it; do not rebuild a framework just because its idea is useful.

This WO is roadmap-only. It does not authorize runtime/source changes, package installation, telemetry export, provider traffic, memory promotion, secret access, or changes to active WO168/169/Zero-Relay implementation lanes.

## Reuse-before-build

Classification: `REUSE + WRAP + EXTEND`; `BUILD` only after an implementation WO proves the capability is missing.

A-Conductor already owns durable jobs, worker/provider admission, execution/recovery, ReviewBus, orchestration evidence and operator state. The new roadmap must extend those authorities rather than introduce a second scheduler, trace SSoT, router, evaluator authority, memory store or provider registry.

## External evidence basis

Canonical research synthesis is in A-Wiki at `docs/research/agent-engineering-evidence-20260910.md`. Key public evidence includes Ponytail benchmark corrections, Pydantic AI durable-execution docs/incidents, smolagents/OpenTelemetry instrumentation, SWE-agent trajectories, OWASP agent-security guidance, AgentDojo/AgentDyn adversarial evaluation, and the Aider architect-to-editor trust-boundary incident. Community popularity is corroboration, never authority.

## Roadmap decision

Add an **Agent Efficiency, Evidence & Trust Plane (AEET)** after current Zero-Relay/active compatibility gates. It is not a new control plane; it attaches bounded measurement, attestation and trust evidence to existing authorities.

Planned capabilities:
1. benchmark/evaluator self-test and task baseline;
2. risk-adaptive minimality policy for coding-agent lanes;
3. effective policy/capability attestation;
4. local-first versioned execution trace envelope;
5. stable replay/operation identity audit and idempotency gaps;
6. inter-agent provenance/taint validation;
7. adversarial agent-security eval pack;
8. accepted-run efficiency/quality scoreboard;
9. sanitized evidence feedback to A-Wiki.

## Dependency / sequencing guard

- Existing P0/READY authority and Zero-Relay remain ahead of AEET.
- WO168/169 and their current review/continuity work keep existing authority.
- WO170/PR #243 remains this roadmap branch's parent until reconciled.
- No AEET node is READY merely because it appears here.
- Read-only archaeology/evidence work may proceed now without stealing a mutable lane.
- AEET-0 is the normal first future implementation candidate after a fresh gate; AEET-2/5 are assessed as possible safety prerequisites before broad autonomous mutation; AEET-3 precedes AEET-7; AEET-4 is audit-first and may close REUSE; AEET-1 stays gated by project-specific A/B safety evidence.

## GPT × GLM parallel contract

GPT-5.6 Sol owns architecture, cross-repo authority mapping, sequencing, trust/security adjudication, exact-SHA acceptance, and merge/release decisions.

GLM/ZCode is assigned one focused read-only evidence audit that improves existing Issue #233 without opening a competing owner map or consuming a mutable implementation slot.

### Task packet `GLM-XREPO-EVIDENCE-RO1`

Status: `READY / READ_ONLY / PARALLEL_SAFE / NO SOURCE MUTATION`

Goal: prove which A-Wiki/A-Sunday Conductor capabilities already satisfy A-Wiki Phases 12–17 and AEET-0..8, identify only real gaps, and propose the smallest reuse-first future slices.

Required startup:
1. fetch both repos and record exact inspected SHAs;
2. A-Sunday Conductor: `00-AGENT-ENTRY.md -> PROJECT-GRAPH.yaml -> AGENTS.md -> actual Git/claims -> CURRENT-WORK.md -> COLLAB.md -> this WO -> PROJECT-PLAN.md`;
3. A-Wiki: `BRAIN-ENTRY.md -> docs/graph/PROJECT-GRAPH.yaml -> AGENTS.md -> COLLAB.md -> docs/work-orders/WO-AGENT-EVIDENCE-ROADMAP-20260910.md -> docs/research/agent-engineering-evidence-20260910.md -> docs/migration/awiki-vnext-plan.md`;
4. inspect A-Conductor Issue #233 and use it as the authority-dedup destination;
5. recover live PRs/branches/claims before relying on older docs.

Audit targets:
- existing job/task/event/evidence/recovery/provider/model-policy/review/claim/lease/memory/defect/security authorities;
- deterministic tests and real defects that can seed evaluator/adversarial fixtures;
- cross-repo owner/consumer/adapter boundaries and fallbacks needing sunset criteria;
- roadmap nodes already satisfied enough to close as `REUSE / NO NEW IMPLEMENTATION`.

Required result:
`roadmap node | existing owner | exact path/symbol/test evidence | OWNER/CONSUMER/ADAPTER/FALLBACK | REUSE/WRAP/EXTEND/BUILD | proven gap | risk | dependency | smallest next slice`.

Also list candidate evaluator fixtures separately, flag stale/contradictory authority docs, treat tool/transport gaps as `UNVERIFIED`, and finish with exactly one recommended next safe mutation candidate or `NONE`.

Forbidden: any repo mutation; implementation branch/worktree/claim creation; touching WO168/169/Zero-Relay worktrees, credentials/config, workers/processes, Control Center DB, private Drive/secrets; adding a second scheduler/task/review/claim/lease/model-policy/trace/memory authority; recording hidden chain-of-thought/private tool payloads.

Result destination: one durable comment on A-Sunday Conductor Issue #233 titled `GLM-XREPO-EVIDENCE-RO1 RESULT`, including exact inspected repository SHAs. Do not merge anything.

Known transport note: latest Windows independent-review attempt recorded on Issue #233 reached ZCode but failed before model review with CoinTH/Anthropic `HTTP 401 invalid_key`. Recurrence is `UNVERIFIED / PROVIDER_TRANSPORT_BLOCKED`, not a repo failure; never weaken auth or expose secret values to bypass it.

## Mutable scope

Roadmap-capture scope only: `COLLAB.md`, `PROJECT-PLAN.md`, this WO. Forbidden: `src/**`, `tests/**`, private/secret surfaces, `CURRENT-WORK.md`, `handoff.md`, WO168/169 worktrees, WO170 accelerator-plan file.

## Dispatch checkpoint

This tracked WO is the stable pointer. At GLM task start, fetch live GitHub state and pin PR #59, PR #244, PR #243, current A-Conductor `main`, and current claims. Execute only `GLM-XREPO-EVIDENCE-RO1`. GPT continues architecture/reconciliation. No source implementation, merge, live-provider mutation, or priority inversion is authorized.