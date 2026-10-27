# WO-P1-712 ORCH-1/3 Guard Composition

Identity schema: GITHUB_ISSUE_V1
Issue: #712

Parent: #709 (ORCH-1 foundation).

Status: MERGED / POST_MAIN_VERIFIED / REVIEW_DEVIATION_REMEDIATION_PENDING / R3 / CONTROL_PLANE_ONLY.
Previous status (author checkpoint): AUTHOR_VERIFIED / FREEZE_FOR_INDEPENDENT_REVIEW.
Owner: ses_e95c855c4ffe7Dd5kgKeTnRQg6 (AUTHOR, not acceptance authority).
Claim: ORCH-1-3-GUARDS-001 / issue comment 6372970861.
Base: origin/main 12eddb2 (merged signal codec PR711).
Worktree: `A:\GitHub\_worktrees\AWC-orch1-guards`.
Branch: `feat/orch1-guard-pipeline`.
Device: ff685af5-9031-4b3b-84ff-61dc8f1a840c.

## Scope And Authority

Only `src/a_conductor/orchestration_guards.py`,
`tests/test_orchestration_guards.py`, and this work order may change.
Canonical child issue #712 avoids duplicating the codec's existing WO709;
the claim clarification is on parent #709 comment 6373059129.
WRAP accepted #583 `evaluate_bootstrap_guard` and #517
`classify_utilization`; neither accepted policy is rewritten.
Explicit task authorizes implementation, testing, commit and push, NO PR/merge.
Shared CURRENT-WORK.md, handoff.md and COLLAB.md remain integrator-owned;
this packet and Issue709 carry the checkpoint for their later fold-back.
Already-delegated bounded author lane: GLM_OFFLOAD=NOT_BENEFICIAL; no
additional model/provider dispatch. Evidence is deterministic test output and
this tracked checkpoint; optional large artifacts belong in ignored runs/ORCH-1-3/.

## Frozen Contract And Failure Model

Pure evaluation only, no I/O, persistence, queue append, worker launch,
registration, claim acquisition, serialization owner or new authority store.
Inputs are the merged OrchestrationSignal, separately collected evidence dict,
UtilizationFacts, explicit scope tuple, and an application-injected authority
checker `(task_ref, scope) -> bool | None`. Payload claims never supply authority.
`GuardPipeline(authority_checker).evaluate(signal, evidence=..., utilization_facts=...,
scope=(...), lane_class=None)` is the composition seam. The receiver's optional
`queue_pages` / `turn_binding` diagnostics are accepted but never sent to #583
or used as authority; the receiver owns their provenance validation.
Ingress authentication and binding precede this seam in the admitted receiver;
pipeline revalidates the DTO but does not pretend equality proves authentication.

Order is always duplicate -> utilization -> authority; first denial returns.
GuardResult contains admitted, reason, metadata. NOT_APPLICABLE is explicit;
it cannot grant an effect. Observational signals return OBSERVED_ONLY with
admitted=False at the pipeline boundary. Effects require an exact True from
the separately injected authority checker, never truthy/unknown values.
Parent enqueue/replay duplicate evidence uses exactly the #583 kwargs; missing,
incomplete or invalid facts deny RECONCILIATION_REQUIRED. Positive duplicates
preserve DUPLICATE_TASK_SUBMISSION_PENDING and underlying reason/evidence IDs.
Worker effects cannot reuse Parent dedupe: deny reconciliation in this slice
until the existing worker admission is composed by the later dispatcher slice.
Refill-only utilization validates exact enum/bool/int types and global budgets
(at most 3 mutable / 1 review). Capacity is checked separately by application-selected
`lane_class` (`mutable` or `review`; scope is NOT a lane selector); without a selected class, both
classes must have capacity, avoiding a borrowed free review slot admitting
mutable work. Unknown quota/route/activation denies refill; underutilization
is advisory metadata, never a dispatch obligation converted into authority.
Explicit non-refill intent skips A-Faster policy; existing dispatcher WIP and
final claim/provider/lease/HEAD/serialization gates remain mandatory.
No signal dictionary is modified. Guard results are observations, not reusable
capabilities; a dispatcher must recheck the existing authorities at USE.

## Acceptance And Verification

RED-first tests: each guard happy/deny/not-applicable; unknown/malformed facts;
ordered spies, first-deny short circuit, explicit skips, forged policy PASS
cannot bypass authority; no signal rewrite; exact budget/type edges; both
observation and Parent/worker target separation. Related suites: codec,
queue guard, utilization classifier, and work-order identity.
Freeze exact SHA after scope/diff checks, then independent R3 review and hosted
CI remain integrator gates. No production/live acceptance is claimed here.

## Checkpoint

Entry, base/remote identity, design guard section and accepted policies read.
Protected root is stale/dirty and preserved. New worktree started clean.
Receiver lane is disjoint; no delegated execution is launched in this lane.
RED first: test collection failed with the expected missing orchestration_guards
module before implementation. Initial related run was 247 passed / 1 failed:
the canonical identity checker caught duplicate WO709; fixed by allocating child
issue #712 and renaming this packet, without changing checker/legacy fixtures.

Final regression command (Python 3.11, no bytecode/cache writes):

```text
python -B -m pytest -q -p no:cacheprovider tests/test_orchestration_guards.py tests/test_orchestration.py tests/test_codex_queue_submission_guard.py tests/test_a_faster_utilization_guard.py tests/test_work_order_identity.py tests/test_hook_bus.py tests/test_hook_stm.py
```

Result: 482 passed, including 90 guard-composition cases. Coverage includes exact
512/513 evidence bounds, independent class caps, malformed enum/bool/int/budget
inputs, policy wrapper spies, partial READY capacity, exceptions/malformed guard
returns, and a forged NOT_APPLICABLE at authority refusing effect admission.
No accepted guard or codec source is changed. No runtime/queue/provider or worker
operation ran; no PR/merge. Scope is exactly three new files.

Independent exact-SHA R3 review, hosted CI, full/live integration and acceptance
are NOT_RUN, not implied by author tests. Shared continuity fold-back remains
integrator-owned. Keep worktree/branch for review (CLEANUP=PENDING).
Next safe action: freeze/push candidate and have integrator independently review
the exact SHA; runtime dispatcher wiring is outside this slice.

## Final Checkpoint - 2026-10-27

This checkpoint supersedes historical delivery-status statements above, not the
frozen scope or failure model. PR #715 merged candidate
`7434da78434ff784447cbfc7341d8fa2394d427f`, whose parent/base is
`12eddb2241659166f0ba72ec7a63444dca3503a6`. The merge-time PR base was
`aabff438f6368f1ba8bd9333c6707ff35b185633`. Exactly three new files were delivered:
`orchestration_guards.py` (191 lines), `test_orchestration_guards.py` (90 cases
reported in the preserved author checkpoint), and this WO.

Merge: `955822715917d5489c1bc193e6dc0cf278bc5e28`.
Post-main CI [40012880195](https://github.com/aase7en/A-Wiki-Conductor/actions/runs/40012880195)
completed SUCCESS on `main` at that exact merge SHA.

Merged with exact-head post-main CI green; independent exact-SHA review evidence
was NOT recorded on the PR (process deviation: no PR comments or submitted
reviews). Post-merge independent review of the three merged orchestration modules
at `main@955822715917d5489c1bc193e6dc0cf278bc5e28` is commissioned by the
orchestrator as remediation and must complete before ORCH-1 core is treated as
fully accepted. No retrospective review PASS, runtime activation or effect proof
is claimed by this documentation closeout.

Claim `ORCH-1-3-GUARDS-001` is released for the completed author scope; Issue #712
is CLOSED / completed. [Closeout record](https://github.com/aase7en/A-Wiki-Conductor/issues/712#issuecomment-6436101703).
Correct [AUTHOR RESULT / CLAIM FREEZE](https://github.com/aase7en/A-Wiki-Conductor/issues/709#issuecomment-6373185217)
is comment `6373185217`; `6372970861` is the AUTHOR CLAIM. Parent #709 remains
OPEN for review remediation and slices /4-/7. Original author worktree/branch
remain preserved; only the separately authorized docs-closeout worktree is
eligible for cleanup after its own merge inclusion and post-main CI proof.
