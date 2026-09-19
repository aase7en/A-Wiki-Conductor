# WO-P1-260 — A-Faster Durable Lane Identity / Cross-Chat Recovery

Status: CLAIMED / BOOTSTRAP
Issue: #374
Risk: R3 coordination/continuity policy
Topology: CONTROL_PLANE_ONLY

## Binding
Authority repo: aase7en/A-Wiki-Conductor
Worktree: /Users/aase7en/GitHub/_worktrees/awiki-wo260-a-faster-durable
Branch: docs/wo-p1-260-a-faster-durable-lanes
Base: 95c4b9e78003c4b61083650d1698c6661f9bb545
Owner: GLM-5.3 MAX author under GPT-5.6 Sol integration
Claim: WO-P1-260-A-FASTER-DURABLE-LANES-001

## Goal
Extend A-Faster only as a router/profile so delegated lanes remain identifiable,
recoverable and harvestable across device/chat/session loss without a new state authority.

## Allowed mutable scope
- .agents/skills/a-faster/SKILL.md
- NEW .agents/skills/a-faster/references/durable-lanes.md
- this Work Order

Everything else is read-only.

## Required identity contract
- LANE_REF: stable human-readable task/claim/role label, never authority.
- DELEGATED_RUN_ID: unique per dispatch attempt, observation/recovery pointer only.
- ATTEMPT: pointer-local attempt number; never retry authority.
- BINDING_DIGEST: SHA-256 over canonical safe binding fields for drift detection, not encryption.
- Preserve actual task/claim/lease/execution authority IDs unchanged.
- Pointer must bind device, harness/model, repo/worktree/branch/HEAD, task/claim/scope,
  result/exit/log destinations, replay safety, and expected completion evidence.
- Never persist secret values, raw credential-bearing env/argv, cookies, share URLs.

## Recovery invariant
NEW SESSION != NEW TASK. Recover pointer/process/result/Git first; harvest
TERMINAL_UNHARVESTED before redispatch. RUNNING never redispatches. UNKNOWN,
STALLED or interrupted mutation requires side-effect/replay reconciliation.

## Acceptance
No new DB/daemon/scheduler/task/claim/review/completion authority. Global 3 mutable
+ 1 review WIP remains unchanged. 1 mutable hotspot=1 owner. Add deterministic
canonicalization/example guidance and cross-device handoff. Diff/scope/UTF-8/secret
checks, exact-SHA independent review and CI before merge.

Result destination: runs/WO-P1-260/author/
Replay safety: recover pointer/process/result/Git before redispatch.

## 2026-09-19 author checkpoint (attempt-0001) — READY_FOR_REVIEW

Executed on Windows device `DESKTOP-7IB57R4`, worktree
`A:/GitHub/_worktrees/A-Wiki-Conductor-wo260-a-faster-durable`, dispatched from
claim HEAD `ef7d3d15fce0b66ddfdadbc56a3014875aa1bcbd` on this branch
(recorded as a device re-pin from the Mac-prepared binding above; the digest
binds the actual dispatching device). Lane identity for this attempt:
`lane:WO-P1-260:author:1`, run `run:WO-P1-260:author:1:a1:352051cd`,
`BINDING_DIGEST` `cca025dd01a90d0a86f6a86b16e2a4c42f04c618cfd1df62bec160be5fa14d3f`
(canonicalization and pointer evidence under `runs/WO-P1-260/author/attempt-0001/`).

Authored exactly the three allowed paths:
- NEW `.agents/skills/a-faster/references/durable-lanes.md` — identity overlay
  (LANE_REF / DELEGATED_RUN_ID / ATTEMPT / BINDING_DIGEST with canonical
  recipe + verified worked example), `runs/<WO>/<lane>/attempt-NNNN/`
  evidence layout and minimum pointer fields, secret-redaction rules,
  recover algorithm (RUNNING never redispatch; TERMINAL_UNHARVESTED harvest
  first; STALLED/INTERRUPTED/UNKNOWN reconcile before takeover),
  cross-device handoff with digest-recompute and CONTEXT_DRIFT-as-re-pin
  semantics, invariants, safe/unsafe examples, validation checklist.
- `.agents/skills/a-faster/SKILL.md` — additive sections only: durable lane
  identity overlay summary, cross-device digest re-pin step, LANE_REF/
  DELEGATED_RUN_ID routing outputs.
- this work order — this checkpoint.

No new scheduler/DB/task/claim/lease/review/completion authority; no global
lane registry; A-FastTask router-only boundary and global 3 mutable + 1
review WIP unchanged. Deterministic gates run on the frozen candidate:
scope check (exactly the three allowed paths), `git diff --check`, UTF-8
validation, secret pattern scan, reference existence check, digest
recomputation. Next gates: independent exact-SHA read-only review + exact-head
CI before merge; GPT accept/merge only. No self-merge/self-accept.
