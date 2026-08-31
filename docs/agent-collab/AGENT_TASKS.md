# Agent Lane Index

This file is a compact lane index, not the project source of truth.
Authoritative state remains `CURRENT-WORK.md` → `handoff.md` → active work order → runtime/Git evidence.

## Active lane checkpoint — 2026-08-30

| Lane | Owner / provider | Task | Mutable scope | Status |
|---|---|---|---|---|
| Integrator | GPT-5.6 Sol | WO-P1-116 / AHA-6B | production candidate assembly + bounded elastic capacity + focused tests + SSoT | VERIFIED / RELEASED |
| Integrator | GPT-5.6 Sol | WO-P1-115 / AHA-6A.1 | provider admission/runtime wiring + tests + bounded SSoT | RELEASED |
| GLM review lane | GLM-5.3 MAX via one-way file bridge until automatic dispatch proves ready | `wo115-glm-review-001` | read-only `runs/wo115-glm-review-001/result.json` only | VERIFIED PASS / REPAIR ACCEPTED |
| GLM re-review lane | GLM-5.3 MAX via one-way file bridge until automatic dispatch proves ready | `wo115-glm-rereview-002` | read-only `runs/wo115-glm-rereview-002/result.json` only | VERIFIED PASS / RELEASED |
| Integrator | GPT-5.6 Sol | WO-P1-114 / AHA-6A | provider runtime assembly + tests + bounded SSoT | RELEASED |
| GLM review lane | GLM-5.3 MAX via one-way file bridge until auto dispatch exists | `wo114-glm-review-002` | read-only result artifact only | VERIFIED / RELEASED |
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


### WO-P1-116 lane contract

- GPT-5.6 Sol owns architecture, atomic capacity/provisioning authority, SSoT integration and merge/release adjudication.
- GLM-5.3 MAX is benchmark-eligible for a later bounded implementation/review lane only after an exact task packet and non-overlapping scope are recorded.
- External-agent task/result artifacts remain ignored under `runs/<task-id>/`; human fallback relays one pointer only and never copies result content back.
- Worker4 v0.0.13 live soak is a separate P0 evidence lane and grants no mutation authority over Workers 1/2/3/5 or shared tunnel binaries.
- Automatic GLM dispatch remains fail-closed; provider readiness/quota evidence is independent from worker elasticity.

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

### Active WO-P1-114 external review handoff

- Task ID: `wo114-glm-review-002`.
- Task pointer: `runs/wo114-glm-review-002/task.md` (generated after this tracked checkpoint so it can pin the exact final HEAD).
- Result pointer: `runs/wo114-glm-review-002/result.json`.
- GLM lane is READ-ONLY: no source/test/SSoT/Git/branch/commit/PR mutation.
- Human fallback relays only the task pointer; GPT reads and validates the result file directly.
- Automatic provider dispatch remains blocked until runtime Drive binding, fresh required quota evidence, and provider-global admission authority are proven.

### WO-P1-114 GLM review result

- Task `wo114-glm-review-002` reviewed exact HEAD `75c8e21da3d47ffb2fff6f8e37f6240b537f2522`.
- Result identity/task SHA/source/test SHA all validated by GPT integrator.
- Outcome: `PASS`; P0/P1/P2 findings: `0`; P3 hardening observations: `4`.
- P3 cache/whitespace/blank-override/.drive-path diagnostics are deferred: none changes the current fail-closed acceptance boundary, and modifying source after exact-SHA PASS would require a new review snapshot.
- Result path is historical evidence: `runs/wo114-glm-review-002/result.json`; do not reuse the packet for a later HEAD.

### WO-P1-115 released lane evidence

- Integrator lane released after PR #155 exact-head CI `33312763072`, merge `a758f9e882db03e988d67a3f04f69862dd9195c2`, and post-main CI `33313201851` passed.
- `wo115-glm-review-001` and `wo115-glm-rereview-002` are historical ignored evidence only; both are verified and must not be reused after HEAD changes.
- Human fallback carried task pointers only; GPT read/validated result artifacts directly and folded accepted findings into tracked SSoT.
- No successor lane is claimed here. Future agents must re-enter CURRENT-WORK/handoff/work-order/claims before claiming AHA-6B or another slice.

## Worker loss / fallback handoff rule

A worker becoming unreachable is never permission to replay its mutable lane. First persist task/status/HEAD/evidence and classify ownership as `RECOVERY_REQUIRED` when completion is ambiguous. A replacement worker is eligible only after a fresh repo/worktree/claim/dirty/runtime preflight proves it idle and non-overlapping.

Fallback workers consume the same durable task contract; do not create a shadow TODO/handoff. The replacement reads the active WO + `CURRENT-WORK.md` + `handoff.md` + exact `runs/<task-id>/task.md`, and writes only the contract's declared result/evidence destination. If the old worker later returns, it has no mutation authority until the current lane owner releases it.

Current WO-P1-116 snapshot (2026-08-31): Worker5 is the only clean/idle fallback candidate. Worker1 targets the protected dirty root, Worker2 has an open pharmacy cycle, Worker3 is dirty, Worker4 is reserved for P0 WO-P1-096. No worker was rebound or interrupted.

### WO-P1-116 released lane evidence

- Exact reviewed head `d06129ac943ceaa30c398d744b07a0fec9b505e1`; GLM-5.3 MAX validated PASS with P0/P1/P2 = `0` and four P3 notes.
- PR #157 exact-head CI `33352780461` passed, merged as `af5a5068aea37ce82875e4b6fff40ac19ac112c5`, and post-main CI `33354156749` passed all three OS jobs including Windows Frozen Setup E2E.
- Claim released. Ultra/GLM follow-up artifacts under ignored `runs/` remain read-only/advisory until integrator validation and a fresh successor claim.
