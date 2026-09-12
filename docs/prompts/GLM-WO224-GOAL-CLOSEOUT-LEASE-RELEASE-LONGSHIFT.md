/goal

Execute WO-P1-224 only when this lane is eligible and does not preempt active WO221/WO223 work.

PRIMARY REPO:
A:\GitHub\A-Wiki-Conductor

PRIMARY WORK ORDER:
docs/work-orders/WO-P1-224-goal-closeout-lease-release-outcome.md

ROLE:
You are ZCode GLM-5.3 acting as the bounded long-shift implementation/test executor under GPT-5.6 Sol integration authority.

OBJECTIVE:
Repair the latent GoalCloseout lease-release truth defect where a non-throwing `LeaseReleaseOutcome(released=False, already_released=False)` can currently be followed by a durable release checkpoint. Keep the repair minimal, RED-first, deterministic, fail-closed, and fully backward compatible with proven positive paths.

STARTUP GATE:
1. Read `00-AGENT-ENTRY.md` -> `PROJECT-GRAPH.yaml` -> `AGENTS.md` -> actual Git/worktree/claim state -> `CURRENT-WORK.md` -> this WO -> task-relevant protocol files.
2. Read `DEFECT_LESSONS.md` before any `src/a_conductor/` mutation.
3. Re-pin current `origin/main`; do not trust the creation-time base if main moved.
4. Inspect Issue #214 and live claims/worktrees. If WO221/WO223 or another owner overlaps `goal_closeout.py` / `tests/test_goal_closeout.py`, checkpoint `CLAIM_CONFLICT` and STOP.
5. Use a fresh isolated worktree/branch from then-current main. Do not mutate the protected root checkout.
6. Claim exactly the WO224 mutable scope before source mutation.

SOURCE FACT TO REPRODUCE, NOT ASSUME:
At packet creation base `60aba770fd457d04f1e31040b9dfd7af3927f669`, `GoalCloseoutExecutor.execute_next()` checks `FoldOutcome.completed is True` before fold checkpointing, but after `LeaseReleasePort.release()` it does not inspect `LeaseReleaseOutcome.released`; it immediately checkpoints. Current tests only use a fake that returns `released=True`.

ARCHAEOLOGY FIRST:
Confirm the exact current source semantics for:
- `GoalCloseoutExecutor.execute_next()`;
- `LeaseReleaseOutcome`;
- `LeaseReleasePort`;
- `plan_goal_closeout()` release-stage contradiction/recovery rules;
- closeout checkpoint identities;
- related tests and any production construction/caller that may have appeared since packet creation.

If a newer accepted repair already closes the defect, do not duplicate it. Prove equivalence, record `ALREADY_RESOLVED`, and STOP.

RED-FIRST MANDATORY CASE:
Create a failing regression where the release port returns exactly:
`LeaseReleaseOutcome(released=False, already_released=False)`.

Expected repaired behavior:
- `CloseoutDecision.RECOVERY_REQUIRED`;
- stage `CloseoutStage.RELEASE_LEASE`;
- typed detail preferably `LEASE_RELEASE_NOT_CONFIRMED` unless current conventions require an equivalent name;
- no release checkpoint written;
- no COMPLETE transition;
- no blind retry.

REQUIRED POSITIVE/ADVERSARIAL MATRIX:
1. `True,False` confirms release and permits checkpoint.
2. `False,True` confirms already-released and permits checkpoint; detail remains `ALREADY_RELEASED`.
3. Preserve current accepted behavior for `True,True` unless repository authority proves it invalid.
4. Confirmed release + checkpoint write failure remains `RECOVERY_REQUIRED / CHECKPOINT_AFTER_EFFECT_FAILED`.
5. Exact ACTIVE lease + exact release checkpoint contradiction fails before calling the release port.
6. RELEASED without exact current checkpoint remains recovery-required.
7. old lease checkpoint never satisfies new lease.
8. version conflict remains `RELOAD_REPLAN`, never retry.
9. repeated invocation from an unconfirmed outcome does not gain authority from a checkpoint that should not exist.
10. mutation probe must discriminate parent/base behavior from repaired behavior.

IMPLEMENTATION:
Prefer the smallest change in `src/a_conductor/goal_closeout.py` and focused tests in `tests/test_goal_closeout.py`.

Do not introduce a second store, outbox, journal, retry engine, lease state machine, or new completion path.

Optional hardening of `LeaseReleaseOutcome` field types is allowed only if a new RED test proves malformed non-boolean values could otherwise become authority and the change is backward compatible. Do not broaden scope for cleanup/style.

ALLOWED MUTABLE SCOPE:
- `src/a_conductor/goal_closeout.py`
- `tests/test_goal_closeout.py`
- WO224 checkpoint/result evidence only

FORBIDDEN WITHOUT NEW GPT RELEASE:
- job-store implementation/schema;
- WorkerLease store/authority;
- scheduler/provider/admission;
- Zero-Relay C0/C1/WO221/WO223 source;
- fold adapter redesign;
- external providers/processes/live DB;
- A-Wiki;
- secrets/credentials;
- direct merge/self-acceptance/downstream Phase-D release.

VERIFICATION FLOOR:
- focused GoalCloseout suite;
- related job-store/lease/recovery tests based on actual call graph;
- adversarial replay for unconfirmed release;
- compile/import;
- diff/scope audit;
- strict UTF-8/no U+FFFD;
- added-line secret-shape scan;
- freeze exact SHA;
- independent exact-SHA R3 review;
- exact-head CI.

LONG-SHIFT RULE:
Use the useful work budget inside this one WO. Continue through archaeology -> RED -> minimal GREEN -> adversarial -> related regression -> self-review -> freeze/checkpoint without asking the human to relay intermediate results. Keep durable checkpoints so context compression can resume safely.

STOP CONDITIONS:
Stop/checkpoint at the first true external gate: ownership conflict, architecture scope expansion, source drift invalidating the packet, independent-review gate, nonterminal/failed CI, GPT acceptance, merge/post-main gate, or UNKNOWN authority. Do not poll or jump to unrelated backlog.

HANDOFF:
Return durable exact evidence: base/head/worktree/branch, root cause, RED discriminator, changed paths, GREEN/adversarial/regression counts, findings P0/P1/P2/P3, CI/review state, and exact next safe action. Do not merge.
