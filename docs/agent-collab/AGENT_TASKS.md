# Agent Lane Index

This file is a compact lane index, not the project source of truth.
Authoritative state remains `CURRENT-WORK.md` → `handoff.md` → active work order → runtime/Git evidence.

## Active lane — 2026-08-30

| Lane | Owner / provider | Task | Mutable scope | Status |
|---|---|---|---|---|
| Integrator | GPT-5.6 Sol | WO-P1-112 / AHA-5 | work-order assigned integration/docs/tests | RUNNING |
| Candidate implement/repair | GLM-5.3 MAX | AHA-5 live vertical slice | one leased file per task | FILE_BRIDGE_READY / AUTO_PROVIDER_CONFIG_REQUIRED |
| Future agents | provider-neutral | none | none | UNCLAIMED |

### Current GLM evidence

- suitability benchmark gate completed before delegation and recorded in WO-P1-112;
- direct Z.ai execution reached the provider but returned HTTP 429 / insufficient resource package;
- installed ZCode exposes Start Plan, while full GLM-5.3 Coding Plan is currently reported not entitled;
- the user has a working external Claude-CLI GLM proxy profile; its credential remains outside tracked project state;
- automatic Conductor dispatch requires an approved external secret/profile resolver, while the file-based one-prompt fallback remains ready and needs no result copy-back.

## Required lane record

Every mutable lane must identify:
- task/work-order ID;
- owner + provider/model metadata;
- repository, absolute worktree, branch, expected HEAD;
- allowed, forbidden and mutable scope;
- acceptance + deterministic verification;
- task packet reference;
- result/evidence destination;
- current status/checkpoint + next safe action.

## Status vocabulary

`PREPARED` → `CLAIMED` → `RUNNING` → `RESULT_READY` → `VERIFIED` → `RELEASED`.

Exceptional states:
- `REVIEW_FAILED` — deterministic review found repairable defects;
- `REPAIR_READY` — bounded repair task exists and may be dispatched;
- `RECOVERY_REQUIRED` — ownership/execution certainty was lost; no blind replay;
- `EXTERNAL_PROVIDER_BLOCKED` — repo path is ready but provider/auth/quota/entitlement prevents execution;
- `DECISION_REQUIRED` — overlapping authority or a human-only policy decision is unresolved.

## No-copy-back rule

Agents communicate through task/result/evidence files or accepted durable execution artifacts.
Human copy/paste of an agent's result is never project authority.
If automatic dispatch is unavailable, the human may relay one short direction prompt that points
the agent to its task packet and result destination; the integrator reads the result itself.

## Claim / release

1. Preflight repository/worktree/branch/HEAD/dirty/claims/process ownership.
2. Record bounded scope in the work order and lease/claim authority.
3. Dispatch only from exact accepted identity.
4. Verify result with deterministic checks; `DONE` text is not acceptance.
5. Release claim only after evidence and continuity checkpoint are durable.

AHA-5 permits one mutable file per agent task. Multi-file parallel fan-out belongs to AHA-6.
