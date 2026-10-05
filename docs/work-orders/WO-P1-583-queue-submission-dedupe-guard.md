# WO-P1-583 — Codex queue-submission dedupe / duplicate-bootstrap guard

Issue: #583
(defect record; observed during #581 recovery)
Parent context: #580 lifecycle vNext consumes this guard later; #576 owns native Goal idle/pause mechanics (untouched here).
Class: CONTROL_PLANE_ONLY
Risk: R3 (deduplication/idempotency semantics adjacent to one-owner orchestration authority; no transport/persistence/authority mutation)
Executor route: Windows ZCode + GLM-5.3 MAX primary session (user topology 2026-10-05, Issue #580 comment)
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo583-queue-guard`
Branch: `docs/wo-p1-583-queue-dedupe-guard`
Bootstrap base: `6ad9fddfb8a13cf01cf11e9cf0395b146e6ac844` (= origin/main at bootstrap)

## Goal

Prevent recurrence of the #583 defect — interrupted Codex Parent turns plus queued-submission recovery creating **two governance bootstrap mutation owners for one task/claim hotspot** — by adding a pure, deterministic caller-side guard that turns observed App Server queue/turn evidence into a typed proceed/block decision **before** any governance bootstrap submission or replay side effect.

Root cause is already source-proven (Issue #583 comment `5982737256`): App Server `thread/queue/add` treats `client_user_message_id` as correlation data only — no idempotency, no dedupe; each enqueue inserts a fresh row. Therefore the missing invariant must be supplied by the caller:

**MISSING INVARIANT (frozen):** For one task/claim intent, at most one pending governance-bootstrap submission may exist, and a recovery/replay path must prove no same-intent submission is pending (and no interrupted-turn side-effect ambiguity exists) before creating any claim/worktree. `client_user_message_id` for A-Sunday governance bootstrap submissions MUST be the deterministic task key defined below, so equality on that field is meaningful duplicate evidence.

## REUSE / WRAP / EXTEND / NEW decision

- REUSE: `GoalApiOutcome.queue_entries` (`QueueEntry(submission_id, client_user_message_id)`) and `GoalApiOutcome.turns` (`TurnEvidence(turn_id, status)`) decoded projections from `src/a_conductor/codex_goal_api_adapter.py`; typed-blocker/reason-code style; RED-first focused-test pattern.
- NEW: one bounded pure policy module (no existing equivalent — verified by grep: no `DUPLICATE_TASK`/queue-guard symbol exists in `src/`).
- DO NOT EXTEND the adapter itself: its accepted contract explicitly states "Queue correlation is not a dedupe key" and keeps the translator policy-free. The guard is a separate caller-side consumer.

## Frozen source scope (mutation gate)

- NEW `src/a_conductor/codex_queue_submission_guard.py`
- NEW `tests/test_codex_queue_submission_guard.py`
- (this WO file under the docs bootstrap)

## Hard forbidden scope

- `src/a_conductor/codex_goal_api_adapter.py` + `tests/test_codex_goal_api_adapter.py` (accepted 0.159/0.160 translator stays pure; #576 lanes)
- `.codex/hooks/a_sunday_lifecycle.py` + `tests/test_codex_a_sunday_hooks.py` (#580 candidate scope)
- `src/a_conductor/codex_goal_idle_guard.py` + its tests (#576 idle/pause mechanics)
- SunDayRemoteMCP; raw Codex SQLite/session/lock edits; any transport, network, process, Git, persistence, scheduler, task/claim/lease store, retry, review/merge/completion authority
- No change to CoinTH quota hooks or JEV surfaces

## Frozen contract

1. `queue_submission_task_key(task_ref: str) -> str`
   - `task_ref` is the canonical task reference string (e.g. `"WO-P1-583"` / `"issue:581"`); non-empty, ≤128 chars, no control/whitespace-trimmed-edge characters.
   - Returns `"awc-tsk-v1:" + sha256(task_ref.encode("utf-8")).hexdigest()[:16]` — deterministic, collision-resistant, stable across attempts/sessions.
   - Invalid `task_ref` raises `QueueSubmissionGuardError("QUEUE_GUARD_TASK_REF_INVALID")` (code-only preflight; nothing invoked).
2. `evaluate_bootstrap_guard(task_ref, *, queue_entries, turns, queue_evidence_complete, turn_evidence_complete, queue_next_cursor=None, turn_next_cursor=None) -> GuardDecision`
   - Inputs are OBSERVED decoded evidence only. PROCEED requires **complete** evidence, not merely OBSERVED evidence: an OBSERVED page is only one bounded page (`next_cursor` may exist — `codex_goal_api_adapter.py` QUEUE_LIST/TURNS_LIST decode). Evidence is complete only when the caller attests `*_evidence_complete=True` from fully paginated OBSERVED outcomes AND the last observed page carried no `next_cursor`. A non-None `queue_next_cursor`/`turn_next_cursor`, or either attestation False (transport UNKNOWN/unobserved, stopped early) ⇒ fail closed: `RECONCILIATION_REQUIRED` / reason `QUEUE_GUARD_EVIDENCE_INCOMPLETE`. The guard never fabricates observations and never treats a partial scan as an absence proof.
   - Any queue entry whose `client_user_message_id` equals `queue_submission_task_key(task_ref)` is a **pending same-intent submission**. Count ≥ 1 ⇒ `DUPLICATE_TASK_SUBMISSION_PENDING` / `QUEUE_GUARD_DUPLICATE_PENDING`, listing the offending `submission_id`s (bounded, order-preserving) for caller-owned disposition (e.g. supported `thread/queue/delete`); the guard itself never deletes.
   - Any `TurnEvidence.status == "interrupted"` (unharvested/ambiguous side effects per #583) ⇒ `RECONCILIATION_REQUIRED` / `QUEUE_GUARD_TURN_INTERRUPTED` even when no duplicate is pending.
   - Otherwise ⇒ `PROCEED` / `QUEUE_GUARD_CLEAR`.
   - Foreign entries (other/unparseable `client_user_message_id` values) never match and never block.
   - Invalid/oversized evidence (wrong types, empty IDs, duplicate submission IDs, non-identifier cursor values, or more than `MAX_EVIDENCE_ITEMS = 512` entries/turns in one call) ⇒ `QueueSubmissionGuardError("QUEUE_GUARD_EVIDENCE_INVALID")` — typed rejection before scanning, never a silent PROCEED and never unbounded decision output.
3. `GuardDecision` is a frozen dataclass: `action: GuardAction` (`PROCEED` | `DUPLICATE_TASK_SUBMISSION_PENDING` | `RECONCILIATION_REQUIRED`), `reason_code: str`, `duplicate_submission_ids: tuple[str, ...] = ()`, `interrupted_turn_ids: tuple[str, ...] = ()`.
4. Priority order when multiple blockers apply: a positively observed `DUPLICATE_TASK_SUBMISSION_PENDING` outranks evidence-incompleteness and `RECONCILIATION_REQUIRED` (a visible duplicate is direct one-owner violation evidence and gives the caller actionable IDs); evidence-incompleteness outranks interrupted-turn reconciliation; interrupted turns are surfaced alongside in `interrupted_turn_ids` whenever present.
5. The module performs no I/O, holds no state, defines no retries, and confers no authority: a `PROCEED` is a policy observation over supplied complete evidence, not admission, ownership, completion, or permission to mutate.

### Contract repair note (independent R3 review round 1)

Codex GPT-6.1 Sol exact-SHA review of candidate `9020fb1` returned CHANGES_REQUIRED: P1 partial-pagination could silently PROCEED (absence proof over one bounded page), P2 evidence collections and duplicate output were unbounded. This v2 freezes the complete-evidence contract (attestation + objective last-page `next_cursor` inputs) and `MAX_EVIDENCE_ITEMS = 512` typed rejection before scanning, with duplicate-over-incompleteness priority. Repair cycles: 1 of 2 used.

## Failure model (RED matrix before implementation)

- same-key pending submission present (1 and N) ⇒ DUPLICATE_TASK_SUBMISSION_PENDING, exact IDs listed
- no duplicate, evidence known, no interrupted turns ⇒ PROCEED
- interrupted turn, no duplicate ⇒ RECONCILIATION_REQUIRED + interrupted IDs
- duplicate + interrupted turn ⇒ DUPLICATE_TASK_SUBMISSION_PENDING wins, interrupted IDs still surfaced
- unknown/incomplete queue or turn evidence (attestation False OR last-page next_cursor non-None) ⇒ fail-closed RECONCILIATION_REQUIRED / QUEUE_GUARD_EVIDENCE_INCOMPLETE, even when a duplicate is visible only as dup IDs must still not PROCEED; positively observed duplicate still outranks incompleteness
- duplicate present on a later page while first page is clear (pagination stopped early) ⇒ never PROCEED
- >512 entries or >512 turns in one call ⇒ typed QUEUE_GUARD_EVIDENCE_INVALID before scanning; exactly 512 accepted
- non-identifier or subclass cursor values ⇒ typed QUEUE_GUARD_EVIDENCE_INVALID
- foreign client_user_message_id values (random UUIDs, other prefixes) never match
- task key determinism: same ref ⇒ same key across calls; different refs ⇒ different keys
- invalid task_ref (empty/whitespace/control chars/>128) ⇒ QUEUE_GUARD_TASK_REF_INVALID
- invalid evidence shapes (non-dataclass entries, blank IDs, duplicate submission IDs) ⇒ QUEUE_GUARD_EVIDENCE_INVALID
- #583 observed-sequence regression: intent enqueued once (entry present) + second recovery attempt evaluating with same task_ref ⇒ guard must NEVER return PROCEED (one-owner invariant)
- decision objects immutable; no mutation of caller-supplied tuples

## Acceptance criteria

1. RED-first: the focused test file is committed failing against absent/near-empty module, then GREEN after implementation (no test weakening; each failure-mode row above covered).
2. Targeted suite: `tests/test_codex_queue_submission_guard.py` fully green via the project's supported test invocation.
3. Related regression: `tests/test_codex_goal_api_adapter.py` unmodified and green (translator untouched).
4. `python -m compileall` on changed files; `git diff --check` clean; strict UTF-8; added-line secret scan 0 hits; exact changed-file list equals frozen scope.
5. Exact candidate SHA frozen; independent exact-SHA R3 review (not the author session; Codex GPT-6.1 Sol read-only detached checkout preferred, else a separate GLM read-only lane) with P0/P1/P2 = 0; hosted exact-head CI SUCCESS; expected-head merge; fresh post-main CI verified.
6. DEFECT_LESSONS fold after acceptance: symptom/impact/trigger/root cause/missing invariant/fix/regression/future warning (per #583 requirement).

## Non-goals

- Wiring the guard into `.codex/hooks/a_sunday_lifecycle.py` or any runtime caller (separately claimed consumer scope, e.g. #580 phase).
- Any App Server protocol addition, queue-API change, or assumption that `thread/queue/start` is defective.
- Automatic deletion of queued submissions; automatic reconciliation; scheduler/WIP authority.

## Claim

Claim ID: `WO-P1-583-QUEUE-DEDUPE-GUARD-WIN-001`
Posted to Issue #583 at bootstrap; released only after post-main verification or explicit supersession.
