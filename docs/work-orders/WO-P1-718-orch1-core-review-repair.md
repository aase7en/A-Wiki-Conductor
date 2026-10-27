# WO-P1-718 ORCH-1 Core Review Repair

Identity schema: GITHUB_ISSUE_V1
Issue: #718

Status: AUTHOR_VERIFIED / FREEZE_FOR_INDEPENDENT_REVIEW / R3 / CONTROL_PLANE_ONLY.
Risk: R3 / CONTROL_PLANE_ONLY.
Owner: Kilo / OpenAI gpt-6.1-sol, repair AUTHOR only.
Claim: ORCH-1-CORE-REPAIR-001 / issuecomment-6436353561.
Review: https://github.com/aase7en/A-Wiki-Conductor/issues/709#issuecomment-6436277690
Base: 955822715917d5489c1bc193e6dc0cf278bc5e28.
Worktree: `A:\GitHub\_worktrees\AWC-orch1-core-repair`.
Branch: `fix/orch1-core-review-repair`.

## Bounded Scope Addendum (recorded BEFORE the extension edits)

Conforming the codec to the commissioned `orch-signal.v1` envelope renames the
DTO attribute `signal.signal_type` to `signal.kind` and changes kind literals
to the commissioned uppercase enum. `orchestration_guards.py` reads that
attribute in five places and compares lowercase literals; the outcome signal
kind is removed from the contract (the bounded outcome envelope moves to
`OrchestrationOutcome`/`encode_outcome`/`decode_outcome` in the same module).
Therefore this lane additionally admits TWO mechanical, non-semantic edits:
`src/a_conductor/orchestration_guards.py` limited to those five attribute/literal
renames (no logic change) plus one additive diagnostic-key change: the
DuplicateGuard evidence diagnostic set gains `turn_pages` because the
cursor-collected receiver now retains turn pages alongside queue pages
(diagnostics are stripped before the #583 policy call; required keys are
unchanged), and `tests/test_orchestration_guards.py` limited to
the fixture constructor reshape and dropping the removed `outcome` kind from
two non-effect parametrize lists. No other guard behavior, policy authority,
dispatcher, runtime activation, shared continuity or protected-root change is
admitted by this addendum.

## Scope And Failure Model

Explicit task permits this WO, `src/a_conductor/orchestration.py`,
`src/a_conductor/orchestration_receiver.py`, `tests/test_orchestration.py`,
and `tests/test_orchestration_receiver.py`. No other mutation is admitted.
Guards, dispatcher, runtime activation, shared continuity and protected root
remain untouched. No runtime/provider operations or merge are authorized.
Ingress must bind separately admitted source/project/task/target before any
authority read; payload assertions never grant authentication or authority.
Incomplete or ambiguous pagination must never be represented as complete.
Source work requires RED-first evidence for each of the four findings.

## Contract Repair Decisions

1. Missing source binding: conform to foundation section 3. Require separately
   admitted immutable ingress context and reject mismatches before readers/clock.
2. Envelope: conform to `orch-signal.v1` and the closed section 4 payload table.
   WO709's earlier explicit-task override explains the six-field implementation
   but provides no operational evidence justifying retaining it in this lane.
   No compatibility decoder or design amendment is authorized.
3. Bounds: conform to 16 KiB, depth 4, 64 total fields before JSON parsing.
   Earlier 64 KiB/depth 32 override contains no proof that tighter bounds are
   insufficient. Retain numeric non-conversion and strict UTF-8/duplicate checks.
4. Pagination: conform to section 5.3 for both queue and turns, explicit terminal
   cursor, at most 32 pages including empty and 512 records per listing.
   WO713's complete-list attestation is not independently verified collection.
   Add later-page fault tests; keep existing policy authorities unchanged.

## Initialization Blocker

Resolved by explicit orchestrator authorization: unique child issue #718 and
WO-P1-718 replace the originally requested duplicate WO709 filename. Parent #709
and claim ORCH-1-CORE-REPAIR-001 are unchanged. Historical blocker follows.

The requested new filename duplicates canonical WO709, already owned by
`WO-P1-709-orch1-signal-codec.md`. The identity checker rejects duplicate numeric
IDs irrespective of slug, including new untracked WOs. Previous receiver and
guard lanes resolved the same conflict through unique child issues #713/#712,
not checker changes or identity waivers.

Creating this requested bootstrap WO does not grant source mutation. Verify the
identity failure, then stop for integrator adjudication. No failing identity test
counts as RED evidence for any product finding. No source/test edits, commits,
pushes or PRs have occurred. All four findings remain open.

Required unblock: authorize a unique child issue/WO and its matching replacement
path in mutable scope, or explicitly reconcile the duplicate identity policy.
Do not rename/delete the existing codec WO or weaken the checker here.
Shared CURRENT-WORK/handoff/COLLAB folding stays integrator-owned.

Verified blocker (2026-10-27): `python -B -m pytest -q -p no:cacheprovider
tests/test_work_order_identity.py` returned **1 failed, 32 passed in 2.68s**.
The sole failure reports duplicate canonical work-order id WO-P1-709 between
this requested new packet and the existing codec packet. Execution stopped
before source mutation. Exact next action is integrator identity adjudication,
not implementation, commit, PR creation or a blind test retry.

## Final Checkpoint (2026-10-27, author freeze)

All four findings repaired conform-to-design in the admitted scope:

1. P1 source binding — `SignalReceiver.handle` now requires a separately
   admitted `AdmittedContext` (source_ref/project_id/task_ref from the
   trusted composition root) and compares it against the signal BEFORE the
   binding reader, clock, or any authority read. New typed codes:
   `ADMITTED_CONTEXT_INVALID` (malformed/absent context) and
   `ADMITTED_CONTEXT_MISMATCH` (forged/foreign identity) — frozen catalog
   entries recorded here. Effect kinds require the admitted task identity.
2. P2 envelope — `OrchestrationSignal` is now the commissioned
   `orch-signal.v1` DTO: exact `schema_version` (refused never downgraded,
   `SIGNAL_VERSION_UNSUPPORTED`), `signal_id`, uppercase `kind`
   (ENQUEUE/REPLAY/UTILIZATION/LIFECYCLE; `outcome` removed as a signal
   kind), `occurred_at`, `source_ref`, `project_id`, effect-required
   `task_ref`/`work_order_ref`, optional `binding_ref`, closed per-kind
   payload with target-key exclusivity. The bounded outcome envelope moved
   to `OrchestrationOutcome`/`encode_outcome`/`decode_outcome` (six decision
   labels, exclusive effect refs) preserving that capability for /6.
3. P2 bounds — 16 KiB total checked on bytes before UTF-8 decode; depth<=4
   and total-field<=64 enforced in the pre-parse structural scan (every
   colon outside a string is a key separator, so counting them bounds the
   field total without parsing); encoder tree-walk enforces the same trio.
4. P2 pagination — `TurnReader` is now the same one-page protocol as
   `QueueReader` (`list_turns(thread_id, cursor) -> {items, nextCursor,
   binding}`); the receiver follows cursors until an explicit terminal None
   for BOTH listings with shared page/record budgets (32 pages incl. empty,
   512 records), duplicate-id/cursor detection, per-page binding identity
   checks, completion-clock freshness over every retained binding, and
   `EVIDENCE_OVERFLOW`/`RECONCILIATION_REQUIRED` never represented as
   complete. Guards' DuplicateGuard diagnostic set gains `turn_pages`.

Verification (author-run, Windows worktree):
- RED proof: reviewer reproductions at comment 6436277690 document base
  behavior; additionally the new contract tests fail on the unmodified base
  sources at collection (missing `OrchestrationOutcome`/`AdmittedContext`)
  — verified via stash/restore cycle, stash `1fea427e`.
- Focused: 245 passed (codec+receiver+guards, was 225 pre-repair).
- Regression selection: 559 passed (orchestration x3 + work-order identity +
  #583 queue guard + #517 utilization + hook_bus + hook_stm) — supersedes
  the prior 482 selection with equal-or-wider coverage.
- Remaining pre-commit gates (run immediately before commit): compileall,
  `git diff --check`, strict UTF-8/no-BOM, added-line secret scan.
- Independent exact-SHA R3 review, hosted CI, and acceptance NOT_RUN.
  This lane does not merge.

## Verification Plan After Unblock

Re-gate ownership and clean exact-base state; reproduce all four findings before
their fixes; run codec/receiver/guards focused suites, the prior 482 regression
selection, identity suite, compileall, UTF-8, diff check and secret scan. Record
actual counts rather than retaining historical counts. Freeze only after all
required gates pass; commit/push, create PR without merge, and post exact SHA
plus RED/GREEN evidence to #709. Independent R3 review remains external.
