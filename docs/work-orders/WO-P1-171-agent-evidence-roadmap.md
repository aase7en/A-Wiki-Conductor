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

Canonical research synthesis is being captured in A-Wiki at `docs/research/agent-engineering-evidence-20260910.md`. Key public evidence includes:
- Ponytail independent benchmark #236: minimality lowers code substantially but can reduce unstated-edge robustness;
- Pydantic AI durable-execution docs + issue #6911: required durability can disappear silently when a capability is not effectively bound;
- Hugging Face smolagents: OpenTelemetry-based instrumentation for production run inspection;
- OpenTelemetry GenAI semantic conventions: common agent/tool/model/usage identity plus explicit sensitive-content warnings;
- SWE-agent trajectories: per-run config/log/exit/trajectory artifacts with evaluation kept separate;
- OWASP AI Agent Security + AgentDojo: tool data, memory, autonomy and multi-agent propagation require adversarial security testing;
- Aider issue #5058: planner/architect output must not become trusted editor authority transitively.

## Roadmap decision

Add an **Agent Efficiency, Evidence & Trust Plane (AEET)** after current Zero-Relay/active compatibility gates. It is not a new control plane; it is a set of bounded capabilities attached to existing execution/evidence authorities.

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

Do not interrupt or rewrite the frozen/current lanes. The first implementation slice may be claimed only after re-pinning actual main and active ownership. In particular:
- WO168/169 compatibility/continuity work keeps its existing authority;
- WO170 remains the stacked parent roadmap delta until PR #243 is merged/rebased/closed;
- Zero-Relay remains the throughput priority; AEET must improve its safety/measurement rather than displace it;
- before broad multi-provider autonomous pilots, the future implementation plan must explicitly decide whether effective-capability attestation and inter-agent provenance gates are prerequisites based on the then-current runtime evidence.

## Priority overlay — what may happen now vs later

The roadmap is intentionally non-preemptive:

1. **Existing P0/READY frontier wins.** WO168/169 reconciliation and the authoritative Zero-Relay sequence retain priority and mutable capacity.
2. **Read-only AEET preparation may run now.** Existing-authority archaeology, evaluator/test inventory, replay-identity audit, attestation/provenance mapping, and adversarial-case cataloging are parallel-safe when they do not mutate claimed surfaces.
3. **AEET-0 remains the normal first implementation candidate** after a fresh live gate because later optimization claims depend on evaluator truth.
4. **AEET-2 and AEET-5 are safety-prerequisite candidates**, not automatically READY. Before broad autonomous multi-provider mutation, GPT/integrator must decide from then-current evidence whether they are required blockers or already satisfied by reuse.
5. **AEET-3 precedes AEET-7** because a scoreboard cannot outrank its evidence source. **AEET-4 is audit-first** and may close as `REUSE / NO NEW IMPLEMENTATION`.
6. **AEET-1 minimality remains gated by project-specific A/B evidence** and stays off for high-risk durable/security/concurrency work until proven safe.
7. **AEET-6, AEET-7 and AEET-8** follow accepted authority/privacy/trace boundaries; none may displace Zero-Relay or release work.

## GPT × GLM parallel contract

GPT-5.6 Sol owns architecture, cross-repo authority mapping, sequencing, trust/security adjudication, exact-SHA acceptance, and merge/release decisions.

GLM/ZCode is assigned a focused **read-only cross-repo evidence audit** now. This is useful immediately because Issue #233 already blocks downstream duplicate-authority risk; the audit improves that existing gate without opening a competing architecture lane or consuming a mutable implementation slot.

### Task packet `GLM-XREPO-EVIDENCE-RO1`

Status: `READY / READ_ONLY / PARALLEL_SAFE / NO SOURCE MUTATION`

Goal: prove which A-Wiki/A-Sunday Conductor capabilities already satisfy the new roadmap nodes, identify real gaps, and produce the smallest reuse-first future slices.

Required startup:
1. fetch both repositories and record exact inspected SHAs;
2. A-Sunday Conductor: `00-AGENT-ENTRY.md -> PROJECT-GRAPH.yaml -> AGENTS.md -> actual Git/claim state -> CURRENT-WORK.md -> COLLAB.md -> this WO -> PROJECT-PLAN.md`;
3. A-Wiki: `BRAIN-ENTRY.md -> docs/graph/PROJECT-GRAPH.yaml -> AGENTS.md -> COLLAB.md -> docs/work-orders/WO-AGENT-EVIDENCE-ROADMAP-20260910.md -> docs/research/agent-engineering-evidence-20260910.md -> docs/migration/awiki-vnext-plan.md`;
4. inspect existing A-Conductor Issue #233 and treat it as the authority-dedup destination, not something to duplicate;
5. recover live open branches/PRs/claims before drawing any conclusion from older docs.

Current roadmap candidates to pin before starting:
- A-Wiki PR #59 branch `docs/agent-evidence-roadmap-20260910`;
- A-Sunday Conductor PR #244 branch `docs/wo-p1-171-agent-evidence-roadmap`;
- A-Sunday Conductor parent PR #243 branch `docs/wo-p1-170-provider-settings-roadmap`;
- A-Sunday Conductor current `main` must be observed fresh, not inferred from this WO.

Audit targets:
- AEET-0..8 and A-Wiki Phases 12–17;
- current job/task/event/evidence/recovery/provider/model-policy/review/claim/lease/memory/defect/security authorities;
- existing deterministic tests and production defects that can seed evaluator/adversarial fixtures;
- cross-repo owner/consumer/adapter boundaries and any compatibility fallback needing sunset criteria;
- areas where current code already proves the roadmap invariant and should be marked `REUSE / NO NEW IMPLEMENTATION`.

Required result shape:
- table: `roadmap node | existing owner | exact path/symbol/test evidence | OWNER/CONSUMER/ADAPTER/FALLBACK | REUSE/WRAP/EXTEND/BUILD | proven gap | risk | dependency | smallest next slice`;
- separate candidate evaluator fixtures from actual implementation work;
- flag contradictory/stale authority docs explicitly instead of choosing one silently;
- record tool/transport gaps as `UNVERIFIED`, never as code failure or PASS;
- finish with exactly one recommended next safe mutation candidate, or `NONE` if the current frontier should remain untouched.

Forbidden:
- source/test/docs mutation in either repo for this task;
- branch/worktree/claim creation for implementation;
- touching WO168/169/Zero-Relay worktrees, provider credentials/config, workers/processes, Control Center DB, private Drive, secrets, or live services;
- adding a new scheduler/task store/review lifecycle/claim or lease authority/model-policy store/trace SSoT/memory store;
- treating model output as mutation authority or recording hidden chain-of-thought/private tool payloads.

Result destination: post one durable comment on A-Sunday Conductor Issue #233 titled `GLM-XREPO-EVIDENCE-RO1 RESULT`, including exact inspected repository SHAs. Do not merge anything. GPT/integrator will reconcile the result before any implementation node is activated.

Known transport note: the latest Windows independent-review attempt recorded on Issue #233 reached ZCode but failed before model review with CoinTH/Anthropic `HTTP 401 invalid_key`. Treat any recurrence as `UNVERIFIED / PROVIDER_TRANSPORT_BLOCKED`, not as a repository failure; do not weaken auth or copy secret values into GitHub to bypass it.

## Mutable scope

- `COLLAB.md` claim/checkpoint row for WO171;
- `PROJECT-PLAN.md` roadmap section only;
- this work order.

Forbidden: `src/**`, `tests/**`, secrets/private Drive, `CURRENT-WORK.md`, `handoff.md`, WO168/169 source/worktrees, and the WO170 accelerator-plan file.

## Verification

- verify stacked ancestry exactly from WO170 head;
- confirm WO170 claim is released and PR #243 remains the only parent `PROJECT-PLAN.md` delta;
- exact changed-file/scope audit;
- `git diff --check` and strict UTF-8 read;
- scan changed docs for secret/private-path values;
- source/URL/license spot-checks against public evidence;
- independent exact-SHA architecture review required before merge because this changes future trust/evaluation policy.

## Dispatch checkpoint

Roadmap capture is frozen for handoff. GPT continues architecture/reconciliation. GLM executes only `GLM-XREPO-EVIDENCE-RO1` as read-only work and posts the evidence map to Issue #233. No AEET implementation, merge, live-provider mutation, or priority inversion is authorized.