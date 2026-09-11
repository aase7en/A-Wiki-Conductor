# WO-P1-186 — GLM Wave 7 / 1,536-unit sustained delivery campaign

Status: PACKET_AUTHORING / DOCS_ONLY
Risk: R0 transport packet; child work retains its own R0/R1/R2/R3 classification
Parent: WO-P1-155 Zero-Relay Accelerator
Coordination authority: Issue #233
Owner: GPT-5.6 Sol integrator (packet author only)
Branch: `docs/wo-p1-186-glm-wave7-1536-delivery`
Bootstrap main: `f964afced5fbe0905c3667b1a6552a6fdafc09cb`

## Goal

Give GLM-5.3/ZCode one durable root `/goal` that can productively work for several hours without requiring the user to relay `continue` messages.

Wave 7 must start from the durable Wave-6 final state, not repeat completed Wave-1..6 archaeology. It should maximize accepted evidence and delivery throughput, not token consumption by itself.

Topology:
- 12 programs;
- 16 unique families per program;
- 8 standard evidence-producing actions per family;
- 12 x 16 x 8 = **1,536 base goal units**;
- evidence-triggered recursive findings to depth 8;
- queue replenishment after the base matrix is exhausted while useful unresolved work remains.

## Bootstrap mutable scope

This docs-only authoring lane may change only:
- `docs/work-orders/WO-P1-186-glm-wave7-1536-delivery.md`
- `docs/prompts/GLM-MARATHON-WAVE7-1536-DELIVERY-GOALS.md`

No source, tests, global continuity, private data, live provider, runtime DB, process, merge, or release mutation is granted by this WO.

## Child mutation rule

The root packet is orchestration authority, not blanket mutation authority.

Any child that wants to mutate must first:
1. re-pin repo/worktree/branch/HEAD/dirty state;
2. recover current task/WO/owner/claim/lease;
3. prove non-overlap;
4. classify R0/R1/R2/R3;
5. reuse an existing compatible lane when one exists;
6. otherwise create/claim one bounded WO with exact mutable scope;
7. fail closed if `SAFE_TO_MUTATE != YES`.

R2/R3 frozen candidates require a genuinely independent exact-SHA review. GLM does not merge or self-accept its own R2/R3 candidates.

## Wave-6 facts to consume, not rerun

At Wave-6 completion:
- WO181 / PR #254 had merged as `5f36fe0ae59b6b3d4aadfd5465e817761d59ff09` and post-main CI `34543995776` later completed SUCCESS.
- WO183 / PR #255 candidate `efe2618e08f91152570410cc3a2f17ce9f98fa50` independently reviewed ACCEPT and exact-head CI succeeded; integrator subsequently merged it as `f964afced5fbe0905c3667b1a6552a6fdafc09cb`.
- ZRA-1 LIVE-3 was the next critical-path proof and must use a fresh identity/current-main lane; live execution remains GPT/integrator-authorized only.
- existing WO165 / Issue #214 is the canonical ZRA-2 implementation lane; do not create a second ZRA-2.
- `AgentRepairRequest`, `ReviewMailboxResultReader` / `ReviewResultForwarder`, `AgentResultPacket` and `GoalCloseout` are reuse authorities; no production ZRA-2 coordinator existed at the last audit.
- Wave-6 identified ready/shaped follow-ups including agent-security fixtures, bundle compatibility guard, tracked junction/reparse probes, SSoT/claim refresh, and later fan-in ambiguity tests.

All of these facts must be freshly re-pinned before acting because actual state may have moved.

## Priority model

At each family boundary, rank READY work by:
1. P0/P1 correctness and credential/process/durable-state safety;
2. Zero-Relay critical path: ZRA-1 -> WO165/ZRA-2 -> ZRA-3 -> ZRA-4;
3. frozen-candidate independent review preemption;
4. executable defect-memory / security fixtures;
5. integration/recovery/cross-platform evidence;
6. SSoT/continuity debt that can cause duplicate or unsafe work;
7. throughput/test-economy improvements;
8. lower-priority roadmap shaping.

A blocked high-priority goal does not stop the Wave. Checkpoint the blocker and route to the next safe READY family.

## Evidence rules

Each non-skipped family must leave at least one new durable artifact or decision:
- deterministic test/probe result;
- exact-SHA review verdict;
- accepted/falsified finding;
- bounded task/WO packet;
- claim/overlap/reuse decision;
- runtime/recovery evidence;
- executable defect-memory proposal/fixture;
- SSoT reconciliation packet;
- or a justified `PROVEN_NO_GAP` / `BLOCKED_WITH_OWNER` decision with exact evidence.

Do not count rereading or rerunning unchanged evidence as progress.

## Stop conditions

Continue automatically across safe child goals. Stop the root only for:
- HUMAN_DECISION_REQUIRED
- HUMAN_ACTION_REQUIRED
- AUTHORIZATION_REQUIRED
- SAFETY_BLOCK
- NO_SAFE_NEXT_ACTION
- provider/session hard limit after a durable partial checkpoint.

Before any stop, checkpoint exact repo/ref/SHA, completed families, active claims, evidence, blockers, unresolved findings, and exactly one resume pointer.

## Completion

Wave 7 is complete only when every base family has a disposition, all newly proven high-priority findings have either a bounded successor or a justified block, and the final result publishes:
- exact repos/SHAs/PRs/CI inspected;
- delivery/review/implementation outcomes;
- P0/P1/P2/P3 findings;
- ZRA-1..4 maturity delta;
- security/recovery/cross-platform delta;
- durable packet/claim inventory;
- throughput/test-economy observations;
- maximum 20 ranked next micro-WOs;
- DO_NOT_BUILD list;
- exactly one `NEXT_SAFE_ACTION`.
