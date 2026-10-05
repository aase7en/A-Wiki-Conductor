# A-Sunday Conductor — Loop Engineering Adoption Roadmap

Date: 2026-09-06
Work order: `WO-P1-159`
Status: FOUNDATION ACTIVE / integration dependency-gated
Upstream reference: `cobusgreyling/loop-engineering@e1c9d5f5e23655b65d04c5617aff77ab3ad58c16`

## Outcome

Make A-Conductor safer and more autonomous by adding the best proven loop
engineering primitives while preserving its stronger control-plane,
repository-safety, worker-lifecycle, provider-authority, and SSoT model.

Target runtime shape:

```text
Trigger -> Recipe -> existing Task Contract -> existing Router/Scheduler
        -> Worker/Provider -> Attempt Evidence -> Loop Guard
        -> Verify/Review -> Continue | Repair | Escalate | Complete
```

No new scheduler, mailbox, claim store, task store, provider authority, or
parallel orchestration authority is introduced by this roadmap.

## Autonomy model

Autonomy is an explicit ceiling per recipe/project, not a global "AI mode".

| Level | Meaning | Default authority |
|---|---|---|
| `A0_MANUAL` | Human starts every material action | inspect/draft only unless separately authorized |
| `A1_OBSERVE` | Triggered loops may run read-only | report + evidence; no mutation |
| `A2_ASSISTED` | Bounded mutation through existing gates | repair/commit only where task policy permits; human gates remain |
| `A3_AUTONOMOUS` | Unattended continue/repair within admitted scope | strict guard + verifier + budget + recovery + human escalation |

Promotion is evidence-based. Configuration alone never proves A3 readiness.
A project/recipe may be demoted automatically after repeated failure,
budget breach, authority drift, recovery ambiguity, or a safety incident.

## Foundation already safe to implement under WO159

### LEA-0 — Upstream pin, licensing, and reuse map
- preserve upstream identity and MIT notice;
- record REUSE / ADAPT / EXTEND / REJECT decisions;
- credit Cobus Greyling / loop-engineering in README.

### LEA-1 — Python-native deterministic Loop Guard
- pure/no-I/O decision function;
- hard iteration cap;
- identical-failure stagnation;
- broader consecutive-failure/no-progress cap;
- token, elapsed-time, and estimated-cost caps;
- stable reason codes and metrics;
- no automatic retry side effect.

### LEA-2 — Loop Recipe schema
Adapt upstream pattern-registry ideas into a provider-neutral schema that:
- references the existing Task Contract rather than embedding another task model;
- references canonical durable state rather than creating `STATE.md` shadows;
- carries trigger, phases, autonomy ceiling, assurance tier, human gates;
- carries aggregate loop limits for circuit-breaker/cost policy;
- leaves routing and worker/provider selection to existing authorities.

## Integration frontier — after ownership gates release

### LEA-3 — Guard integration with accepted continuation seam
Dependency: WO154 accepted and the relevant WO155/ZRA continuation scope released.

Integrate the pure guard immediately before an existing authority would create
or dispatch the next attempt. Inputs must come from durable attempt/evidence
state, not model memory. A breaker decision must persist a typed escalation or
blocked state; it must never replay an ambiguous side effect.

Acceptance:
- one named integration seam only;
- existing max-attempt semantics remain compatible;
- identical-failure and resource caps are enforced from durable evidence;
- fault injection proves no second dispatch after breaker activation.

### LEA-4 — Machine-enforced action gate
**EXTEND existing gates; do not port `loop-gate` as a parallel authority.**
Compile existing Task Contract/repository/provider policy into one pre-action
decision for commit/merge/dispatch/continue operations.

Required checks should include:
- repository/worktree/HEAD/owner identity;
- allowed/forbidden scope and diff-size/file-count limits;
- secret/privacy/network policy;
- provider capability/readiness/authorization/admission;
- action-specific human approval;
- current Loop Guard decision.

### LEA-5 — A-Doctor Loop Readiness
Extend A-Doctor instead of importing `loop-audit`.

Score evidence in separate dimensions:
- durable state/continuity;
- repository isolation/ownership;
- deterministic verifier + independent review;
- machine safety gates;
- breaker/no-progress protection;
- budget/cost observability;
- human escalation;
- recovery/idempotency;
- actual successful loop activity.

Output:
- score 0–100;
- maximum safe autonomy level A0–A3;
- missing evidence;
- exact next improvement.

Never grant A3 from files/configuration alone; require observed execution proof.

### LEA-6 — Cost and quota loop policy
Extend the existing Task Contract/provider cost-and-quota objective.

Add aggregate recipe accounting for:
- no-op/report/action paths;
- maker-checker cost;
- bounded parallel fan-out cost;
- per-run and per-day token/cost ceilings;
- early exit before expensive model calls when deterministic evidence is enough.

Local workers may additionally expose CPU/GPU time and energy estimates where
the measurement is reliable; unavailable metrics remain UNKNOWN, never zero.

### LEA-7 — Recipe catalog
Materialize only after LEA-3..6 are accepted.

Initial candidates adapted from upstream:
1. `CI Sweeper` — classify failure -> minimal repair -> verify -> escalate.
2. `PR Babysitter` — observe PR/CI/review state; bounded repair; no blind merge.
3. `Daily Project Triage` — read-only first; prioritize READY/blockers.
4. `Dependency Sweeper` — safe updates with high-risk/version gates.
5. `Post-Merge Verification` — merged-head smoke/recovery/cleanup checks.
6. `Changelog Drafter` — low-risk report/draft recipe.
7. `Issue Triage` — dedupe/classify/propose; human gate for destructive closure.

Reusable procedural definitions should live in A-Wiki when cross-project;
A-Conductor owns the pinned runtime instance/execution evidence.

### LEA-8 — Trigger runtime
Reuse/extend the accepted scheduler/event fabric.

Supported trigger classes:
- MANUAL;
- SCHEDULE;
- EVENT.

Rules:
- trigger does not grant mutation authority;
- duplicate triggers coalesce against durable execution identity;
- schedule/event retries obey the same breaker and idempotency gates;
- missed/late triggers reconcile state before acting.

### LEA-9 — Loop telemetry and operator UI
Expose useful operational truth, not decorative metrics:
- recipe + autonomy level;
- current phase/task/execution;
- attempts / cap;
- breaker state/reason;
- token/cost/time spend vs cap;
- verifier/review state;
- next safe action;
- human gate required;
- last successful run and recent failure class.

Keep raw sensitive payloads out of the UI/log stream.

## Dependency order

```text
LEA-0 -> LEA-1 + LEA-2
               |
WO154/WO155 integration ownership released
               |
             LEA-3
          /    |    \
       LEA-4  LEA-5  LEA-6
          \    |    /
             LEA-7
               |
             LEA-8
               |
             LEA-9
```

## What we deliberately do not fork

- upstream Node/TypeScript orchestration runtime;
- loop-worktree ownership/locking;
- loop-swarm scheduler;
- separate loop state files as execution authority;
- separate MCP/task/claim systems;
- vendor-specific tool lists in recipe definitions.

A-Conductor already has stronger or more authoritative equivalents. Importing
them would increase maintenance and create state/ownership ambiguity.

## Roadmap completion standard

This adoption is complete only when:
- recipes can run through existing A-Conductor authorities;
- guard/gates deterministically stop runaway or unsafe continuation;
- A-Doctor reports evidence-backed autonomy readiness;
- costs/quotas are observable and bounded;
- at least three recipes pass realistic failure/recovery E2E;
- A3 is demonstrated without blind retry, duplicate mutation, secret leakage,
  ownership collision, or human copy/paste relay;
- upstream attribution remains visible in README/notices.

## Shared-plan fold-back

`PROJECT-PLAN.md` is intentionally not edited by WO159 because WO154 currently
owns that hotspot. After WO154 releases it, reconcile this roadmap into the
authoritative plan in a bounded docs-only follow-up rather than merging
competing edits.
