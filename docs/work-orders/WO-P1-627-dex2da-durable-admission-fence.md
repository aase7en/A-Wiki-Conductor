# WO-P1-627 — DEX-2dA: durable admission journal + cross-restart dispatch fence

Status: DONE — PR #628 merged 2026-10-12 at `15fd2ed` (pinned-head `390267a`); review record PR #628 comment 6115603920; claim released #627 comment 6115604167
Issue: #627
Parent: #526 (DEX lane decisions; operator DEX-2d offline continuation authorization 2026-10-12); predecessor DEX-2c #625 / WO-P1-625 / PR #624 (merged, claim released).
Risk: R3 STRICT — durability and at-most-once semantics across process restart are authority-bearing; single-repo (AWC) implementation.
Owner: GLM-5.3 MAX lane (session sess_b82dd681-c3b1-49c6-990e-b1918b764209); independent exact-SHA review via Codex CLI gpt-6.1-sol.
Topology: CONTROL_PLANE_ONLY — both deliverables are AWC control-plane state over the existing `SQLiteExecutionStore`; SRM needs no edits (DEX-2a substrate unchanged, read-only reference).
Normative contract: `docs/contracts/execution-admission-receipt-v1.md` (§2 admission, §6 recovery). Architecture: `docs/adr/ADR-0002-dex-execution-admission-receipt-boundary.md`.

## Goal

Close WO-P1-625 §Limitations items 1 and 2 ONLY:

1. **Durable admission journal** — admission decisions (acceptances AND denials) persist in the existing durable execution store; a restarted issuer replays the frozen decision with exactly the in-process semantics (frozen denial, binding-digest/claim-bound replay, typed identity conflicts). Never re-decides a decided identity across restart.
2. **Cross-restart at-most-once dispatch fence** — a durable write-ahead fence reservation is committed BEFORE physical dispatch; after any process restart, an identity whose fence is in a non-retired state (RESERVED / DISPATCHED / FENCED) and has no receipt is NEVER automatically re-dispatched — it is a typed AMBIGUOUS outcome pending explicit reconciliation.

## Reused foundation (do NOT duplicate)

- `src/a_conductor/dex_admission.py` (DEX-2c frozen-decision issuer — replay/conflict semantics are preserved verbatim behind the journal).
- `src/a_conductor/dex_wire.py` (DEX-2c locked wire; per-identity in-process lock retained; the durable fence composes with it).
- `src/a_conductor/execution_store.py` (DEX-2b store — the ONLY durable authority extended here; transactional `BEGIN IMMEDIATE` + lazy idempotent `initialize()` conventions).
- DEX-2a SRM substrate — untouched.

## New deliverable (bounded)

1. `SQLiteExecutionStore` additive extension: `admission_decisions` and `dispatch_fences` tables (created by the existing `initialize()` executescript; additive `CREATE TABLE IF NOT EXISTS`, no migration of existing tables, no schema-version bump of the provenance contract) plus typed methods: get/record admission decision (identical-row idempotent, different-row `ADMISSION_DECISION_CONFLICT`; raw values validated BEFORE any coercion on both load and record — tampered rows are `ADMISSION_JOURNAL_CORRUPT`, never normalized), reserve dispatch fence (write-ahead `RESERVED`; existing-row returns its state; binding-digest disagreement is `FENCE_BINDING_CONFLICT`), transition fence state with the exact machine `RESERVED→{DISPATCHED, FENCED, RETIRED}`, `DISPATCHED→{FENCED, RETIRED}`, `FENCED`/`RETIRED` terminal (illegal or unknown transitions `FENCE_STATE_CONFLICT`; missing row `DISPATCH_FENCE_NOT_FOUND`). All fail closed on corruption/unreadable state.
2. `dex_admission.py`: `AdmissionJournal` port + `DurableAdmissionJournal` adapter over the store; `AdmissionIssuer(journal=None)` — the default in-memory issuer is retained unchanged for DEX-2c contract tests; a journal-backed issuer checks memory → journal → fresh-decide, records every decision (including denials) through the journal in one transaction, and lets journal failures propagate fail-closed.
3. `dex_wire.py`: durable fence composition — after the execution-record probe and receipt duplicate check, the wire commits the fence reservation before `transport.dispatch`; a pre-existing non-retired fence yields typed AMBIGUOUS with zero dispatch; after receipt persistence the fence retires; every ambiguity/collect/evidence/receipt-persistence failure marks the durable fence FENCED in addition to the in-process fence.
4. `tests/test_dex_durability.py` — RED-first matrix (see §Tests).

## Failure model (crash windows)

- Crash before fence reservation → nothing durable, no substrate effect; safe fresh run.
- Crash after reservation, before dispatch → restart sees RESERVED w/o receipt → AMBIGUOUS (conservative: dispatch not disprovable), never auto-retry.
- Crash after substrate completion, before the DISPATCHED mark → fence stays RESERVED w/o receipt → AMBIGUOUS (conservative, still blocking).
- Crash after the DISPATCHED mark, before receipt → restart sees DISPATCHED w/o receipt → AMBIGUOUS.
- Crash after receipt, before fence retirement → restart's duplicate check returns the receipt (DUPLICATE); fence retirement is cleanup, not a safety precondition.
- RETIRED-without-receipt (inconsistent state, unreachable by this wire) → reserve observes created=False → AMBIGUOUS fail-closed.
- Corrupted/unreadable journal or store → typed fail-closed (WIRE_STATE_UNAVAILABLE / store code), never fail-open.

Crash-window tests construct the abandoned durable states (RESERVED, DISPATCHED, RETIRED-without-receipt) DIRECTLY, because a test process cannot be killed mid-window — the durable state a crashed process would leave is identical, and no exception handler runs in that lifetime. Exception-path rows (dispatch throws / collect throws / tampered evidence) additionally cover the handled-failure transitions to FENCED.

## Tests (deterministic; RED-first)

- admission survives issuer restart (new issuer instance, same store) — same decision; denial survives restart; mutated binding/generation across restart is a typed conflict; tampered REAL claim_generation is typed CORRUPT (never int()/bool()-normalized into a valid decision);
- abandoned-state rows: RESERVED-without-dispatch, DISPATCHED-without-receipt, and RETIRED-without-receipt each constructed directly → a NEW wire instance is AMBIGUOUS with zero re-dispatch;
- handled-failure rows: crash-after-reserve (dispatch throws) and crash-after-dispatch (collect throws) — NEW wire instances over the same store: AMBIGUOUS, zero re-dispatch; tampered evidence durably fenced;
- reserve contention: barrier-synchronized direct reserves over two connections on one database file → exactly one created=True; gated wire-level race is event-ordered (entered-event bounded wait; the dispatch gate never silently releases on timeout and cleanup is finally-guaranteed) → the loser is strictly AMBIGUOUS with zero dispatch while the winner is provably inside dispatch. Two connections over one SQLite file are an honest single-database serialization proxy — NOT a claim of multi-host or process-kill behavior;
- full success → new wire instance: DUPLICATE with the existing receipt (immutable receipts stay idempotent); identical journal rows re-record idempotently;
- stale claim generation denial persists across restart and blocks new mutation attempts;
- store-file corruption → typed fail-closed with zero dispatch;
- fence binding-digest disagreement (same identity, different binding) → typed FENCE_BINDING_CONFLICT at the store, frozen denial at the journal layer, zero dispatch;
- fence transition conflicts keep their wire class (WIRE_FENCE_CONFLICT), including a mark failure after substrate acceptance;
- fence state-machine transitions enforced (legal set + terminal FENCED/RETIRED + missing-row typed);
- TERMINAL_UNHARVESTED-safe: a non-retired fence without a receipt is never treated as NOT_STARTED/safe-fresh on restart (asserted by every abandoned/crash row).

Real-substrate tier: NOT extended in this slice — the fence and journal are pre-dispatch control-plane state with no new substrate interaction (DEX-2c tier-2 already pins the substrate seam, and that suite runs unchanged with the fence active); recorded explicitly below.

## Explicitly deferred (dependency-gated, NOT approved here)

3. Same-execution retry authorization and new-attempt semantics (contract §6 retry model).
4. Multi-process/multi-host admission beyond the single SQLite database serialization boundary (cluster-grade fencing).
5. TERMINAL_UNHARVESTED substrate-status consultation on admission.
6. Automatic reconciliation of fenced identities (explicit operator reconciliation remains the model).
7. Windows/macOS enrollment, remote transport, live mutation canaries (human-gated).

## Forbidden

- Any SRM source mutation; any change to frozen digest vectors or accepted tests.
- A second task/claim/admission/receipt/evidence store or scheduler authority.
- Live remote mutation, enrollment, secrets handling, unsafe transport.
- Self-merge; merge requires independent exact-SHA R3 review + hosted CI.

## Compatibility gate

Base: AWC `06522c9a7c0275edea622149040d59845a814354` + SRM `f4bdd57465e79874eb3c371b4b0602729a241467` (read-only). Drift before merge → re-pin + focused review.

## Stop conditions

- If the fence/journal requires a schema-version migration of accepted tables → park and re-scope (additive-only by design).
- If cross-process semantics cannot be proven on the accepted SQLite boundary → fail closed, record the gate, do not weaken tests.

## Checkpoint log (append-only)

- [2026-10-12] WO created per the DEX-2d offline continuation authorization; lane issue #627 verified as a real issue BEFORE naming (WO-612 lesson); worktree `A:\GitHub\_worktrees\AWC-dex2d-journal`, branch `feat/dex2da-durable-fence`, base `06522c9`. No source mutation yet.
- [2026-10-12] COMPLETE — PR #628 merged at `15fd2ed` (pinned-head `390267a`). R3 review PASS after 4 exact-SHA rounds (r1 FAIL: corrupt-row coercion, abandoned-state rows, race synchronization, conflict-class preservation, WO precision; r2 FAIL: event-ordering of the race; r3 code PASS @ `b80a9d4`; r4 PASS @ `390267a` for the cockpit table-inventory companion update caught by hosted CI; chain on PR #628 comment 6115603920). Hosted CI @ `390267a`: windows `test` + ubuntu/macos `cross-platform-smoke` all SUCCESS. Post-main verify on the merged tree: 168 passed + 5 subtests (durability 23, DEX-2c integration unchanged incl. tier-1, WO identity 33, cockpit 92); full local suite pre-merge 6405 passed (two pre-existing environmental GPU-particle failures documented — reproduced identically on a clean main worktree). Delivered: `admission_decisions`/`dispatch_fences` additive schema + typed transactional methods (exact-type corruption boundary on load AND record); journal-backed `AdmissionIssuer` (decisions journaled before caching, failures fail-closed); wire write-ahead fence reservation before physical dispatch with abandoned-state (RESERVED/DISPATCHED/RETIRED-without-receipt) blocking, FENCED marks on every failure path with conflict-class preservation, best-effort retirement after verified receipts; 23-row durability matrix incl. barrier-synchronized two-connection contention (exactly one reservation winner). Process lesson banked: run the FULL tests/ suite before push (exact per-file inventory assertions live outside DEX-adjacent suites). Remaining DEX-2d gaps stay dependency-gated per §Explicitly deferred.
