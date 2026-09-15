# WO-P1-241 — Sunday delivery priorities and economical model routing

Status: ACTIVE / DOCS_ONLY / R2
Date: 2026-09-15
Claim: WO-P1-241-DELIVERY-PRIORITIES-001
Owner: current GPT integrator; independent review required before acceptance
Branch: `codex/wo241-sunday-delivery-priorities`
Base: `67744e98e538b000579bff4a45616d3a178a824b`

## User authority and outcome

The user requested updating the development plan for continuous delivery, with
GPT-5.6 Sol as the regular integrator, GLM-5.3 through Kilo CLI or Claude Code CLI
as the implementation workforce, and GPT-6 Astra only for exceptional decisions
where precision, uncertainty or impact justifies scarce premium capacity.
This is a user routing preference, not a benchmark or current entitlement claim.

Extend the existing cost-first runbook and capability matrix rather than creating
a parallel roadmap, router, status store, or per-agent handoff. Include the earlier
approved planning direction: Zero-Relay first, A-Wiki skills/hooks as shared
infrastructure, upstream reuse, and staged Sunday-Family browser modules/local AI.

## Bounded claim and reuse gate

Allowed tracked files:
1. `docs/runbooks/cost-first-delivery.md`
2. `docs/agent-collab/CAPABILITY_MATRIX.md`
3. this work order

Bootstrap: only this new WO may be created in the clean isolated worktree; commit
it and recheck identity/clean state before editing the other two claimed files.
No source, tests, runtime, provider configuration, credentials, or A-Wiki mutation.

Reconciliation before claim:
- main and Issue #214 retain WO223 RE2-A as the source critical path; PR #319 is
  not accepted. This work never changes its branch, candidate or claim.
- Issue #317 / accepted WO231 docs reuse `JobExecutionBackend`, the existing
  Claude backend, `operator.v1`, and provider/scheduler evidence for Kilo work.
- Issue #320 / WO240 owns two browser-wake roadmap files; candidate `1fa4b880506eaf5d38331da6ba908d5adbd0383e`
  awaits independent review. Reference it without editing or accepting it.
- PR #313 owns `PROJECT-GRAPH.yaml`; PR #243/#244 contain `PROJECT-PLAN.md`
  changes; WO223/WO229 own continuity. Preserve those shared files.
- Open-PR file-scope inspection found no changes to the two claimed existing
  files. WO173/runbook PR #246 is merged. No callable live claim tool is exposed;
  checked durable GitHub claims and known worktrees instead, without asserting
  that all private runtime leases were inspected.
- A-Wiki remote main `3a4e0fba4676f0ba9425733933d5a217eb5cdd7c`: existing brain
  bridge, registry/runner/provider normalization, ReviewBus and PR #59 are reuse
  inputs; no second brain implementation or A-Wiki claim is created.

Classification: REUSE existing delivery/brain contracts; EXTEND the existing
operating plan and named routing preference. No new coordination primitive.

## Acceptance

- [ ] Current frontier is dated and distinguished from historical runbook examples.
- [ ] Sol/GLM/Astra roles, CLI-versus-model identity, escalation and de-escalation are explicit.
- [ ] Existing independent review, risk tiers and provider admission remain mandatory.
- [ ] ZRA/GE-0008/WO240 sequencing conflicts are visible, with no implicit production release.
- [ ] Brain discovery/binding, hook enforcement, learning return and reuse boundaries are actionable.
- [ ] Sunday module/local-AI priorities, upstream intake and package boundaries are recorded.
- [ ] A fresh Sol session can select the next safe action without chat history.
- [ ] Diff/UTF-8/local links/exact scope checks, independent exact-SHA review and required CI pass.

## Continuity and protected hotspots

COLLAB says: "Never edit a file owned by another live claim."
WO223/WO229 hold `CURRENT-WORK.md` and `handoff.md`; WO240 also explicitly excludes
their mutation. The entry contract's continuity requirement is satisfied for this
lane by this WO's checkpoint plus the existing runbook, without overwriting the
active integrator's global state. Shared continuity folding stays with its owner.

Discovery already exists: `00-AGENT-ENTRY.md` -> `PROJECT-GRAPH.yaml` ->
`FAST_EXECUTION_PROTOCOL.md` / `CAPABILITY_MATRIX.md` -> `cost-first-delivery.md`.
Do not add another entry file or edit the graph just to publish this update.

## Checkpoints

### 2026-09-15 — bootstrap

Created isolated branch from exact current main; protected root dirty files are
untouched. This claim owns only the three paths above. Next: commit bootstrap,
re-gate, edit the existing plan/routing documents, freeze and independently review.

`SAFE_TO_MUTATE_WO241_DOCS=YES` after bootstrap commit and clean re-gate.
`SAFE_TO_MUTATE_SOURCE=NO`.
