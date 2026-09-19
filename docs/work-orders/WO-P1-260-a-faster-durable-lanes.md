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
