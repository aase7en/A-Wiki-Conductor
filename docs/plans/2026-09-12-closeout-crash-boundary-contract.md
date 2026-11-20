# Closeout crash boundary — proposal for WO205 consumption

Status: PROPOSED / NOT ACCEPTED PRODUCTION AUTHORITY
Owner: WO208-ASTRA-CLOSEOUT-PROOF-001 / home Mac Astra
Parent: Issue214 / WO205 (Phase-D authority retained by Sol/integrator)
Base source: 02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971

## Decision being prepared

WO205 correctly keeps GoalCloseoutExecutor as the completion authority. Its future
assembler also needs an explicit contract for external effects that happen before the
JobStore checkpoint. An exact-SHA review and a job version read are necessary but do not,
by themselves, serialize an external fold or preserve an UNKNOWN outcome across restart.

This proposal supplies missing proof detail to WO205; it does not redesign Phase C/D,
authorize source changes, create a journal, or release dependency gates. Prefer the
existing job event/recovery and effect-owner mechanisms. Parent integrator selects the
smallest supported composition after the evidence campaign, not a blanket rewrite.

## Evidence and limits

Native Mac probes use the actual GoalCloseoutExecutor and SQLiteJobStore with synthetic
fold ports that write owned temporary files. Existing tests pass (94 across closeout/store).
Source lookup found no GoalCloseoutExecutor instantiation in production src at this base;
therefore these are integration hazards at the public seam, not demonstrated live incidents.

| Probe | Observed | What follows |
|---|---|---|
| Two callers with same initial version, barrier before fold | two effects, one new checkpoint; loser RECOVERY_REQUIRED | post-effect CAS protects journal competition, not the already performed effect |
| Job advances to BLOCKED after facts snapshot | one effect; checkpoint refuses stale version | revalidation only outside effect boundary leaves a stale-owner window |
| Fold writes then reports UNKNOWN; caller reopens DB and reconstructs completed=None | two effects after two calls, no fold checkpoint | losing the returned recovery disposition must not restore eligibility |
| Committed fold + truthful facts after reopening; complete + replay | one effect, COMPLETE, then ALREADY_COMPLETE | existing positive checkpoint/reload semantics should be preserved |

The probes did not crash an OS, simulate power loss or use production fold/lease adapters.
UNKNOWN reentry deliberately models an unsafe caller that loses volatile recovery state;
existing acceptance rules already forbid blind replay. This documents how that rule must
be enforced durably by composition, not an instruction to replay and not proof of a live
bypass. Concurrent facts deliberately model missing exclusion outside the executor.

Full replay and captured output: [native Mac evidence](../reviews/WO-P1-208-closeout-crash-evidence.md).

## Source map and boundaries

| Source at base | Responsibility / limit |
|---|---|
| goal_closeout.py:370 plan_goal_closeout | pure projection over caller-supplied typed facts, not an observer |
| goal_closeout.py:641 FoldRequest | task, candidate and deterministic checkpoint ref; no current job version or ownership fencing token |
| goal_closeout.py:651 CloseoutFoldPort | effect call only; no mandated durable query/reconcile interface |
| goal_closeout.py:698 execute_next | plans once; calls external fold/release before checkpoint CAS |
| job_store.py:438 checkpoint | transaction, expected_version, ordered event and version update |
| job_store.py:357 transition | state/version mutation under one SQLite transaction |
| tests/test_goal_closeout.py | preserves identity, contradiction and recovery rules; many executor ports are fake |
| WO205 sections 8–11 | future composition owns re-observation and restart integration, source still HOLD |

SQLite serializes writes to its database and separates committed changes between normal
connections. That guarantee does not place the Python fold callback inside a JobStore
transaction. This conclusion combines source order with the native probe, not an SQLite
failure. [SQLite isolation](https://www.sqlite.org/isolation.html).

Database crash guarantees depend on documented filesystem/hardware assumptions. A process
exit test does not establish physical power-loss durability or atomically commit arbitrary
files/Git/network operations with a job row. [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html).

## Four distinct proof obligations

1. Evidence identity: the result/review/job/candidate/attempt being acted on is exact.
2. Effect eligibility: the owner and version remain authorized at the actual effect boundary.
3. Recovery knowledge: after interruption, durable evidence distinguishes never started,
   applied, absent-with-proof, in-progress and unknown outcomes.
4. Completion ordering: only existing GoalCloseout may complete after its current verify,
   review, merge, fold, lease and ownership obligations all agree.

Passing journal CAS does not imply item 2. Returning RECOVERY_REQUIRED once does not imply
item 3 survives restart. ALREADY_COMPLETE is a no-op observation of the same exact job,
not permission for the caller to accept a different attempt/result/candidate.

## Cut-point matrix

The ledger below describes observations, not a new lifecycle or accepted serialized schema.
Map it onto existing accepted authorities when implementation is released.

| Interruption point | Durable knowledge after reopening | Permitted next action |
|---|---|---|
| Before any accepted intent or effect | established unstarted operation, ownership current | next existing stage may execute |
| Intent recorded but effect not known | pending/unknown operation | reconcile; do not assume absent |
| External effect succeeded, acknowledgment lost | effect owner may have exact receipt, job checkpoint absent | query exact effect identity; no blind replay |
| Checkpoint commit succeeded, response lost | matching ordered job event exists | consume event plus current effect facts; do not repeat effect |
| Journal contradicts current fold/lease state | contradictory authority | RECOVERY_REQUIRED; no inferred success |
| Job/candidate/owner changes before effect | stale authorization | refuse at effect boundary or prove accepted serialization |
| Job changes after effect before checkpoint | effect may have landed, CAS may refuse | recovery retains operation identity; no generic retry |
| COMPLETE commits before response loss | same exact job durably terminal | reload; no fold/release/author execution again |

A missing completed checkpoint cannot prove the effect was never attempted. Likewise,
completed=None currently represents insufficient fold knowledge; the assembler must not
use it to erase known pending/unknown execution history and re-enter a runnable stage.

## Minimal composition options for parent decision

| Option | Supportable claim | Required evidence |
|---|---|---|
| Restrict initial Phase D to already proven effects / explicit non-required policy | closeout consumes authoritative existing evidence without starting unsupported effects | no forged NOT_REQUIRED flags; parent policy and exact receipts |
| Reuse one accepted owner and idempotent, queryable effect adapter | retries/reconciliation cannot duplicate that specific effect | same key + same payload converges; divergent payload refuses; restart lookup binds exact identity |
| Extend existing job journal with intent/recovery binding | pending work survives interruption under same authority | atomic version-bound intake, intent distinct from completed stage, old/new-reader compatibility, no new store |

These are alternatives to adjudicate, not three tasks to implement. None may weaken existing
fold/release/verification obligations. If an effect has no trustworthy query/idempotency
contract, leave its ambiguous outcome in RECOVERY_REQUIRED. Availability is not grounds to
invent success, re-run the effect or release occupied capacity.

A deterministic request key is useful only if the effect owner actually enforces it.
A pre-effect CAS alone also leaves an intent-with-unknown-effect window. Holding a SQLite
write transaction open around arbitrary external work risks contention and still needs an
external recovery contract; do not adopt that shortcut without a separate accepted design.

## Effect port obligations to prove

- Bind operation to existing job/task/attempt/candidate and stage-specific authority.
  Fold uses accepted merge/fold obligation; release uses the exact lease identity.
- Before effect, prove current ownership/exclusion using existing accepted authority.
  A caller assertion ownership.known=True is not a lock. No new lease system is introduced.
- State which input fields the effect owner can enforce. FoldRequest currently cannot
  carry all job/version/fencing facts; do not claim that it already fences them.
- Define stable identical replay versus divergent-payload collision, including two processes.
- Query/reconcile returns typed exact identity and observed outcome. Query failures and
  ambiguous receipts stay UNKNOWN; filenames, mtime or absent local logs are insufficient.
- Commit-before-ack handling consumes durable evidence. Do not synthesize a completed
  checkpoint merely because an exception was caught or the provider replied PASS.
- Lease release outcome must be checked against the actual adapter contract. The current
  executor uses already_released for detail; test released=False combinations as a port
  contract question without claiming COMPLETE is reachable through truthful ACTIVE facts.
- Recovery projection preserves identity, reason and occupancy in existing durable state.
  Only the accepted recovery authority may reconcile missing completion evidence.
- Cross-host/shared storage and malicious arbitrary external writers are outside this lab.
  Do not infer their exclusion from local SQLite or a Python threading lock.

## Safety, availability and truthful result vocabulary

Track separately: effect count, completed checkpoint count, current job state/version,
recovery knowledge, and duplicate author/provider invocation count. An effect count of two
with only one checkpoint is a useful failure; a final job that stays blocked is a safety
success even if automation cannot yet progress.

Use labels BASELINE_SEAM_COUNTEREXAMPLE, COMPOSITION_GAP, CANDIDATE_PROOF, UNSUPPORTED and
DESIGN_DECISION_REQUIRED. No P0/P1 production severity without a reachable trusted caller
and demonstrated invariant violation. A synthetic proposed adapter is not a production fix.

The two snapshots before/after reopen must name the exact same fixture authorities. Do
not hide missing durable knowledge behind a newly constructed all-green facts object.

## Delivery sequence

1. WO208 current: native Mac seam probes + bounded proposed obligations + queued GLM lab.
2. GLM lab: preserve four seeds; add real child-process exits, lost acknowledgments,
   current native Windows SQLite behavior, false-positive controls and finite state model.
3. Parent WO205 consumes the evidence and chooses supported effect/recovery contract.
4. Only after Phase B/C and explicit Issue214 release: fresh R3 source scope for the
   smallest chosen change, RED-first, related verification and independent exact-SHA review.

This task does not authorize Phase D early, co-write WO205, take WO204 review ownership,
start WO202 process cleanup or touch WO196 physical identity experiments. No new master
controller. GLM follows the selected existing goal, with this lab queued until eligible.
