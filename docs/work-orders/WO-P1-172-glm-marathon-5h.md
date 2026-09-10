# WO-P1-172 — GLM 5-hour marathon execution prompt

Date: 2026-09-10 (Asia/Bangkok)
Status: COMPLETE / DRAFT PR #245 / DOCS CLAIM RELEASED
Owner: GPT-5.6 Sol integrator documentation lane
Priority: P0-supporting / non-preemptive to active Zero-Relay and exact-SHA review gates
Risk: R2 governance/agent-execution documentation
Classification: REUSE + EXTEND existing durable task-packet / Loop Engineer / Zero-Relay protocols
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo172-glm-marathon`
Branch: `docs/wo-p1-172-glm-marathon-5h`
Base at bootstrap: `origin/main@577d9483720c857a89a5d2c9ea9359f9c0aa50b5`
Durable coordination authority: Issue #233

## Goal

Convert the already-checkpointed `GLM-MARATHON-5H-001` Issue #233 packet into one durable,
reusable prompt file tuned for a long GLM-5.3 MAX/ZCode session.

The user explicitly wants the GLM lane to continue for a very long session — up to the
provider/account's available 5-hour window and up to the observed 120M-token allowance —
while GPT/Sol continues integration work in parallel.

The objective is maximum **productive evidence per session**, not token consumption for its
own sake. The prompt must keep selecting useful work until the queue is exhausted, a hard
provider/session limit is reached, or a typed safety/authority stop condition is reached.

## Reuse-before-build result

REUSE/EXTEND, not NEW orchestration:
- universal entry contract: `00-AGENT-ENTRY.md`;
- risk-tier execution: `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`;
- capability routing: `docs/agent-collab/CAPABILITY_MATRIX.md`;
- Zero-Relay authority: WO-P1-155 + Issues #213–#216;
- Loop Engineer protocol: WO-P1-123;
- durable cross-repo owner map/checkpoints: Issue #233;
- existing `GLM-MARATHON-5H-001` Issue #233 packet created before this WO;
- WO171 / PR #244 `GLM-XREPO-EVIDENCE-RO1` read-only audit packet.

This WO creates no scheduler, task store, retry engine, review authority, claim system,
lease system, memory system, provider registry, or model-policy authority.

## Mutable scope

Only:
- `docs/work-orders/WO-P1-172-glm-marathon-5h.md`
- `docs/prompts/GLM-MARATHON-5H-001.md`

Everything else is read-only for this docs lane.

Explicitly forbidden in this WO lane:
- `src/**`
- `tests/**`
- `CURRENT-WORK.md`
- `handoff.md`
- `COLLAB.md`
- PR #242 candidate files
- PR #238 / WO169 files
- PR #243 / WO170 files
- PR #244 / WO171 files
- private Drive secrets or credential values
- live runtime/provider DB mutation
- Worker/process mutation

The resulting GLM prompt also does **not** grant source-mutation authority by itself. During
execution, GLM may mutate source only when a separate current durable work order/claim
explicitly grants that exact mutable scope and all repository/lease/ownership gates pass.
Otherwise it remains read-only and may shape the next bounded packet.

## Long-session design requirements

1. **Fresh recovery first.** Every material stage begins by re-pinning real Git/GitHub/runtime
   state. Embedded SHAs are observations, never future authority.
2. **Priority preemption.** New P0/READY work or a new GLM-assigned durable packet outranks
   lower-priority archaeology at the next safe checkpoint.
3. **Continuous loop.** Finishing one micro-task does not end the session. Select the next
   highest-value safe item automatically.
4. **No human relay.** Do not ask the user to copy results between agents. Persist results in
   the declared file/Issue/PR destination so GPT can read them directly.
5. **No self-review substitution.** A GLM implementation result does not count as its own
   independent acceptance review.
6. **No self-merge.** GLM may never merge/release or weaken GPT/integrator acceptance gates.
7. **Evidence density.** Do not repeat tests on an unchanged exact SHA unless the repeated run
   tests a distinct host/environment/failure hypothesis.
8. **Context management.** Checkpoint before compaction/context rollover. Continue from durable
   state rather than chat/session memory.
9. **Token/time budget semantics.** The 5-hour / 120M-token figure is a ceiling available for
   useful work, not a requirement to emit or consume filler. Never fabricate token accounting.
10. **End-of-window reserve.** Keep enough time near the provider/session cutoff to write a
    durable partial/final checkpoint with exact resume identity.
11. **Typed stop conditions only.** Ordinary uncertainty triggers investigation/recovery, not a
    conversational stop. Stop mutation on HUMAN_DECISION_REQUIRED, AUTHORIZATION_REQUIRED,
    OWNERSHIP_CONFLICT, SAFETY_BLOCK, or NO_SAFE_NEXT_ACTION.
12. **Provider failure is scoped.** Provider/auth failure blocks provider-dependent proof only;
    offline/read-only work continues without blind retries.

## Initial ordered work queue

1. Independent R3 exact-SHA review of PR #242 / WO168.
2. Reconcile the live Zero-Relay ZRA-1 proof boundary from Issues #213/#233 and current source.
3. Shape/audit ZRA-2 automatic review + one bounded repair loop.
4. Shape/audit ZRA-3 automatic NEXT READY continuation.
5. Shape/audit ZRA-4 bounded 2–3 lane parallel dispatch/fan-in.
6. Execute the existing `GLM-XREPO-EVIDENCE-RO1` A-Wiki/A-Conductor reuse audit.
7. Adversarial security/evaluator audit focused on authority escalation, prompt injection,
   exfiltration, replay/ambiguity, denial-of-wallet, and recovery after uncertain side effects.
8. Risk-adaptive efficiency/minimality audit using accepted-run evidence only.
9. Prepare at most five evidence-backed future micro-WOs/repair packets.
10. Final durable closeout/checkpoint before the model/provider/session limit.

The exact order may change only when freshly recovered durable state reveals a higher-priority
READY/P0 dependency. Record the reason for any priority change.

## Acceptance

- durable prompt exists at `docs/prompts/GLM-MARATHON-5H-001.md`;
- prompt incorporates and supersedes the earlier Issue #233 marathon packet without losing its
  safety/priority semantics;
- prompt explicitly supports long productive operation through the available 5-hour / up-to-
  120M-token budget while preventing padding/runaway repetition;
- independent-review, mutation-claim, secret, protected-root, self-merge and human-relay gates
  are explicit;
- stage outputs/checkpoints have deterministic destinations and exact identity fields;
- context rollover is resumable from durable evidence;
- changed scope remains exactly the two docs files above;
- strict UTF-8, `git diff --check`, added-line credential-pattern scan, and prompt safety audit
  pass;
- branch is pushed and opened as Draft PR; no merge from this lane.

## Closeout

Prompt candidate `0aaccf3b699f20fa096037aac1dec9cd9d633742` was committed and pushed on the declared isolated branch, then Draft PR #245 was opened. Verification before that push: strict UTF-8 PASS, staged `git diff --check` PASS, credential-value pattern scan = 0 hits, and changed scope = exactly the two declared docs files.

The docs claim is released after the final Issue #233 checkpoint records the final pushed branch HEAD. The prompt may be used immediately from this isolated Windows worktree or remote branch; it does not need to merge before a read-only GLM run. PR #245 remains Draft and does not preempt PR #242 / Zero-Relay.
