# Agent Lane Index

This file is a compact lane index, not the project source of truth.
Authoritative state remains `CURRENT-WORK.md` → `handoff.md` → active work order → runtime/Git evidence.

## Latest lane checkpoint — 2026-08-30

| Lane | Owner / provider | Task | Mutable scope | Status |
|---|---|---|---|---|
| Integrator | GPT-5.6 Sol | WO-P1-113 / AHA-6 | thin parallel coordinator + tests + coordination SSoT | RELEASED |
| Parallel agent lane A | provider-neutral | AHA-6 selected READY task A | one leased file/task in isolated authorized worktree | RELEASED |
| Parallel agent lane B | provider-neutral | AHA-6 selected READY task B | one leased file/task in isolated authorized worktree | RELEASED |
| CoinTH/GLM provider lane | GLM-5.3 MAX via Claude CLI/ZCode bridge | `aha6-glm-rereview-002` repair re-review | read-only result file only | RELEASED |
| Future agents | provider-neutral | none | none | UNCLAIMED |

### Completed GLM bridge contract

- Historical task pointer: `runs/aha6-glm-rereview-002/task.md` (ignored runtime artifact; do not reuse after tracked HEAD changes).
- Historical result pointer: `runs/aha6-glm-rereview-002/result.json`.
- Human relays only the pointer prompt; human never copies the result back.
- GLM must not edit source, tests, `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`, work orders, commits or PRs in this review lane.
- GPT/Conductor validates task/model/HEAD identity, reads the result itself, and performs the only tracked SSoT fold-back.

### Current GLM evidence

- `aha6-glm-review-001` validated exact HEAD/SHA and returned `CHANGES_REQUIRED`: one accepted P2 lease-invariant fan-in defect, one accepted production-assembly capacity risk, plus P3 hardening.
- repair commit `2a4d8fd786a9d3086a8cd2a298b8ee8cfcb6adc8` closes the lease-invariant defect and P3 unknown-outcome `KeyError` risk; `aha6-glm-rereview-002` independently returned `PASS` with zero findings at exact HEAD `960bf95de9c135a44a1afb33d488f7b4973dd6c6`.
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
