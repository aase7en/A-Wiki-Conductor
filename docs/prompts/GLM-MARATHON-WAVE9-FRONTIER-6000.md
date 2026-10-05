# GLM MARATHON WAVE 9 — FRONTIER 6,000

## ROOT `/goal`

Run this as one sustained GLM-5.3 MAX / ZCode campaign for multiple hours.
Continue automatically across child goals while there is real READY or evidence-producing work.
Do not ask the user to type `continue` between safe goals.
Do not use the user as GPT↔GLM message transport.
Checkpoint changed state to GitHub Issue #233 / relevant Issues and local ignored `runs/**` evidence surfaces.
This is a capacity envelope, not permission to manufacture work or burn tokens.

## Mandatory cold start for every resumed session

1. Read `00-AGENT-ENTRY.md` from actual `origin/main`.
2. Follow only binding routes relevant to the active child.
3. Read repo `AGENTS.md` / `AGENT.md`.
4. Fetch and re-pin repo/remote/origin-main/root/worktree/branch/HEAD/dirty state.
5. Re-pin open PRs, exact-head CI, Issues/claims/leases/owners relevant to the child.
6. Read the child WO/task packet before mutation.
7. Treat CURRENT-WORK/handoff/COLLAB as projections; actual Git/GitHub/runtime authority wins.
8. If owner/claim/lease/scope/dirty/overlap is unknown or conflicting, fail closed and checkpoint `RECONCILE_REQUIRED`.
9. Never reset/clean/stash/rebase/force-push another lane for convenience.
10. Never self-review a candidate authored in the same GLM execution/session.

## Bootstrap truth at publication

- repo `aase7en/A-Wiki-Conductor`
- publication main `f964afced5fbe0905c3667b1a6552a6fdafc09cb`
- Wave 8 / WO187 COMPLETE/consumed; do not rerun without material state change
- canonical ZRA-2 = WO-P1-165 / PR #258
- frozen Phase-A candidate `5f95fe16e95c90faaa4a36686e286515e4641708`
- Phase-A author mutation claim RELEASED
- exact-head candidate CI Windows/full + Ubuntu + macOS PASS
- independent review verdict NONE
- IR1 = RECOVERY_REQUIRED, no review verdict
- ZRA-1 real-provider proof ACCEPTED; never rerun merely for this wave

## Parent-wave authority

WO-P1-188 / this packet is orchestration only. It does NOT grant blanket mutation authority.
Parent tracked mutable scope is only:
- `docs/work-orders/WO-P1-188-glm-wave9-frontier-6000.md`
- `docs/prompts/GLM-MARATHON-WAVE9-FRONTIER-6000.md`

Any product/source/test/shared-SSoT mutation requires a fresh child WO/claim with owner, exact repo/worktree/branch/HEAD, exact mutable/forbidden paths, overlap check, dependency gate, verification ladder, and result destination.
GPT-5.6 Sol retains architecture/trust/security, exact-SHA acceptance, merge, release, and conflict adjudication.

## Campaign accounting

Wave 9 capacity:
- 24 programs `P00..P23`
- 25 families per program `F00..F24`
- 10 actions per family `A..J`
- 24 × 25 × 10 = 6,000 base actions
- recursive findings `R1..R10`
- replenishment `X0001..X2999`

Capacity is not completion. Every selected family ends as exactly one of:
`DELIVERED | CONSUMED_PROVEN | BLOCKED_WITH_OWNER | DEFERRED_BY_AUTHORITY | NO_REAL_WORK`.
Never report “6,000 completed” unless 6,000 evidence-bearing actions actually occurred.

## Standard child protocol A..J

A RECOVER — re-pin relevant actual state and record delta only.
B REUSE — classify `REUSE | WRAP | EXTEND | REPLACE | NEW`; prefer reuse.
C TRACE — trace exact authority/data path and trust transitions.
D POSITIVE CONTROL — prove valid benign path before interpreting adversarial failures.
E FALSIFY — attack the highest-risk assumption deterministically.
F DELIVER — mutate only under an explicit compatible child claim; otherwise deliver read-only evidence/reproducer/task packet.
G VERIFY — targeted tests → related tests → deterministic checks; hosted/full CI only for frozen/broad candidates.
H DEFECT MEMORY — regression test/checker/type/schema/invariant/CI beats prose-only memory.
I CHECKPOINT — persist changed-state-only evidence to relevant Issue/PR and ignored local evidence.
J ROUTE — continue to next real family, bounded repair, review wait, recovery, or authority blocker.

## PREEMPTION 0 — exact-SHA independent review of WO165 Phase A

This is the first critical-path gate ONLY if this GLM session is genuinely independent of the session that authored candidate `5f95fe16e95c90faaa4a36686e286515e4641708`.
If same author session/identity: DO NOT REVIEW IT. Mark `BLOCKED_WITH_OWNER` and continue non-overlapping work.

Review target:
- PR #258
- exact candidate `5f95fe16e95c90faaa4a36686e286515e4641708`
- changed scope must remain exactly:
  - `src/a_conductor/zero_relay.py`
  - `tests/test_zero_relay.py`
  - `docs/work-orders/WO-P1-165-zra2-review-repair-loop.md`

Before review:
- re-pin PR head == candidate
- read Issue #214 latest checkpoints
- read Phase-A independent-review checklist
- consume IR1 only as recovery/process evidence; it is NOT a review verdict
- prove reviewer execution identity differs from author execution identity

Mandatory adversarial questions:
1. Does review evidence bind the exact durable `result_sha256`, not merely `result_ref`?
2. Does it bind exact task digest as well as task ref?
3. Can changed bytes at the same task/result path reuse a stale review?
4. Does local `ReviewDisposition` duplicate/narrow existing upstream `ReviewOutcome` authority?
5. Are PASS / CHANGES_REQUIRED / BLOCKED / ESCALATE semantics preserved or safely mapped?
6. Is exactly one repair generation enforced on malformed and contradictory paths?
7. Can UNKNOWN/TIMEOUT/AMBIGUOUS ever become repair/retry permission?
8. Can reviewer prose/truthiness forge acceptance?
9. Are author/reviewer execution IDs real independent evidence?
10. Does the module remain pure and authority-light?

Verdict must classify P0/P1/P2/P3 with exact symbols/tests. R3 acceptance requires P0=0/P1=0/P2=0 on one immutable SHA. Reviewer must not mutate or merge the candidate.
Blocking finding => checkpoint exact finding packet; GPT owns adjudication; no silent repair without fresh child claim.

## P00 — IR1 duplicate-physical-execution recovery defect

Consume recovered IR1 evidence:
- one outer invocation yielded two physical executions
- both `TURN_DEADLINE_EXCEEDED`
- both durable executions `RECOVERY_REQUIRED`
- jobs BLOCKED; admissions and leases RELEASED
- child/supervisor PIDs gone; candidate remained clean
- no reviewer verdict

Goal: determine why per-invocation ephemeral stores allowed one logical review authorization to become two physical executions after caller/tool timeout.
Read-only first: trace task/job/execution/admission/lease identities; identify where stable replay identity is lost across invocation stores; compare with accepted JobStore/ExecutionStore replay contracts; classify orchestration misuse vs missing product invariant.
Do not change runtime code without separate R3 repair WO.
Deliver deterministic reproducer/non-reproducer, smallest authority-preserving repair recommendation, executable-memory candidate, owner/scope.

## P01 — PR #259 Windows owned-process CI flake

Actual failed case: `tests/test_owned_process.py::test_real_dummy_process_start_idempotent_stop`.
Second `controller.start(runtime)` returned `REFUSED / PROCESS_OWNERSHIP_UNKNOWN` instead of `ALREADY_RUNNING`.
Wave-8 PR changed docs only. Later PR #258 Windows/full CI passed the same product code family. GPT requested targeted failed-job rerun after classifying logs.
Actions: consume rerun result; distinguish transient observer race vs deterministic product defect; compare historical similar PR #222 evidence; inspect PID creation-time/process identity seams; if flaky, design deterministic stabilization without blind retry; if product defect, mint RED-first repair packet only after ownership gate; persist executable defect memory.

## P02 — Phase B deterministic repair materializer

Mutation only after Phase-A exact-SHA acceptance.
Reuse `AgentRepairRequest`, `build_repair_task_markdown`, `TaskPacketFile`, confined deterministic paths.
Required: bind exact rejected task/result digests + finding/reason identity; same path/same bytes => reuse; same path/different bytes => typed collision; generation exactly 1; no raw prompt authority; no provider/review/Git/job/lease authority in materializer.
Until dependency clears: read-only shaping/tests/reuse map only.

## P03 — Phase C independent review composition

Implement only under explicit child claim.
Reuse `ReviewMailboxResultReader`, `ReviewResultForwarder`, A-Wiki ReviewBridge/ReviewBus boundary, fixed typed CLI operations where accepted.
Falsify self-review, stale reviewed SHA, foreign task/result, result-digest substitution, provider/model/reviewer drift, task-hash drift, oversized/truncated review payload, addressed-but-unverified blockers, truthy prose acceptance, second review lifecycle/store.
No A-Wiki internals import; no second ReviewBus.

## P04 — Phase D durable lifecycle composition

After B/C accepted. Compose existing JobStore, execution identity, WorkerLease, provider admission, GoalCloseout, review status authority.
Challenge provider exit 0 without verified review, REVIEW_PENDING premature COMPLETE, UNKNOWN recovery, stale HEAD, generation 2, lease rollover after candidate commit, reviewed-SHA mismatch, completion from prose. No new scheduler/store.

## P05 — ZRA-3 automatic NEXT READY

Only after ZRA-2 accepted. Reuse TaskGraph/scheduler/job authorities. Prove accepted result advances next READY automatically; completed identity does not respawn; duplicate tick no-op; UNKNOWN never blind-replays; restart preserves identity; stale lease/dirty worktree/foreign completion fail closed.

## P06 — ZRA-4 bounded 2–3 lane fan-in

Only after ZRA-3 acceptance. Use existing provider admission, WorkerLease, WIP/capacity, scheduler, durable per-task results.
Prove 2–3 independent READY lanes; sibling failure preserves good evidence; no batch rollback; deterministic partial fan-in; malformed one-lane authority result does not erase siblings; capacity uncertainty blocks launch; no duplicate execution/global barrier/new scheduler.

## P07 — ZRA-5 / ODP readiness

Read-only until ZRA-4 accepted. Map capability-first routing onto accepted zero-relay route. Mailbox remains fallback, never authority.

## P08 — exact-SHA independent review queue

When genuinely independent, preempt for frozen candidates authored by other lanes. Priority: R3 critical path; P0/P1 repair; R2 delivery-path candidate; old PR only if still materially useful. Never self-review. Candidate movement invalidates review.

## P09 — open PR debt triage

Read-only classify #222, #223, #238, #243, #244, #202, #204/#207, and new PRs as `ACTIVE_READY | REVIEW_READY | BLOCKED | SUPERSEDED | CLEANUP_CANDIDATE`. Do not close/delete/rebase from this parent wave.

## P10 — replay/idempotency authority audit

Focus JobStore CAS/version identity, ExecutionStore identity, provider admission idempotency, WorkerLease ownership, stable task hash, physical spawn identity, cross-process/cross-store replay. Use IR1 as concrete adversarial case.

## P11 — process/recovery hardening

Audit PID+creation-time identity, exact executable/argv fingerprint, orphan prevention, process-gone-before-release, supervisor/result missing, timeout ambiguity, stdout/stderr bounds, restart attach/reconcile, no broad kill surface, Windows observer race. Read-only first; mutation requires child WO.

## P12 — review trust / digest binding

Cross-check zero_relay Phase A against review mailbox and A-Wiki contract. Deliver one canonical identity map: task ref+digest, result ref+digest, attempt/generation, author exec, reviewer exec, reviewed SHA/provider/model. Do not invent second authority.

## P13 — security fixtures

Fake-first only: repository prompt injection, malicious tool output/metadata, authority-escalation text, reviewer spoof, result/task substitution, secret-exfil strings, endpoint/credential confusion. Each malicious fixture needs a positive semantic twin.

## P14 — secret/exfil boundary

Synthetic secrets only. Audit task/result/log/exception/argv/env/artifact paths. No real credentials/live provider call unless separately authorized.

## P15 — cross-platform filesystem/process

Target SYSTEMROOT minimal environment, path case folding, junction/symlink/reparse, Unicode/UTF-8, long path/argv, replacement semantics, process identity/permission classes.

## P16 — evaluator / AEET preparation

Respect PR #244 dependency/ownership. Read-only corpus provenance, positive/negative pairs, evaluator self-tests, false-positive/negative controls until implementation READY.

## P17 — executable defect memory

Mine recurrent/proven classes only; prove existing coverage first. Priority: malformed-probe false-success, duplicate physical execution after timeout, Windows owned-process observation race, stale exact-SHA review, result/task digest substitution.

## P18 — CI/test economy

Measure focused vs related vs hosted yield. Identify expensive redundant reruns without lowering R3 assurance. Prefer deterministic targeted isolation for flaky tests.

## P19 — continuity / durable authority

Read-only unless a single-writer fold claim exists. Compare actual Git/GitHub/runtime vs Issues/PRs vs CURRENT-WORK/handoff/COLLAB. Produce changed-state-only reconciliation; do not let many lanes edit shared projections.

## P20 — branch/worktree/PR hygiene

Cleanup candidates only after proving owner released, clean worktree, merged/superseded ancestry, no unique unmerged diff, no live task/claim dependency. Never delete/reset unknown work.

## P21 — architecture simplification

Search for duplicate authority before adding code. Prefer removing ambiguity/duplicate adapters over another store/router/retry system. Evidence required.

## P22 — next critical-path queue

Continuously maintain bounded queue with dependency, owner, risk, smallest mutable scope, proof required, blocker, and one next safe action. Only READY/unresolved evidence-backed items enter.

## P23 — leverage / replenishment

After base programs are dispositioned, replenish only from material evidence: newly unblocked critical path; fresh independent review; P0/P1/P2 reproducer/repair; missing executable defect memory; concrete security fixture gap; cross-platform proof gap; stale claim/SSoT risk; measurable throughput improvement; cleanup with deterministic ownership; removal of duplicate authority.

## Recursive findings R1..R10

Spawn only for a concrete surviving finding. Record parent program/family, exact evidence, severity, authority affected, current prevention coverage, smallest repair scope, owner/claim need, exit condition. Depth >10 forbidden. Same material failure twice without new evidence => root-cause/replan, not retry.

## Preemption rules

Preempt when: a genuinely independent exact-SHA R2/R3 review becomes READY; P0/P1 threatens an external-effect boundary; claim/ownership drift invalidates mutation; CI/merge/post-main result unblocks critical path; GPT posts a new exact child claim/task. Checkpoint before preempting and return to prior queue automatically afterward.

## Multi-session continuity

Before context/provider limits: checkpoint completed P/F/action IDs; skip/consumed set; exact SHA/PR/Issue/CI; claims and releases; blockers/current queue head; ignored evidence paths; exactly one `NEXT_SAFE_ACTION`. Resumed session must re-pin before trusting checkpoint.

## Stop conditions

Stop only for `HUMAN_DECISION_REQUIRED | HUMAN_ACTION_REQUIRED | AUTHORIZATION_REQUIRED | SAFETY_BLOCK | NO_SAFE_NEXT_ACTION`.
Do not stop because one test failed, one child is blocked while other safe work exists, a review is pending while independent evidence work exists, or context rollover approaches (checkpoint then continue in next session).

## Completion report

Report exact main seen; exact candidate/review SHAs touched; delivered evidence; deterministic test/CI evidence; P0/P1/P2/P3 findings; repaired/closed findings; blocked-with-owner items; consumed/no-repeat items; newly READY queue; claims released; exactly one NEXT_SAFE_ACTION. Evidence > model claim.
