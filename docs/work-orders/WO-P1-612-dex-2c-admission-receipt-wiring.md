# WO-P1-612 — DEX-2c: A-Conductor admission/receipt end-to-end wiring

Status: IN_PROGRESS (claimed 2026-10-12 by the GLM-5.3 MAX wake lane)
Issue: #526 (parent), #495 (dependency framing)
Risk: R3 STRICT — cross-repo architectural boundary with authority implications; single-repo (AWC) implementation
Owner: GLM-5.3 MAX lane (session sess_b82dd681-c3b1-49c6-990e-b1918b764209); independent exact-SHA review via Codex CLI gpt-6.1-sol
Topology: CONTROL_PLANE_ONLY implementation — SRM main already satisfies the substrate contract (DEX-2a supervisor, `sunday_dispatch`/`sunday_collect` MCP tools with strict canonical-binding schema); the missing seams are entirely AWC-side, so no SRM edits (operator authorization §4: "Do not manufacture a cross-repo code mutation when one repo needs no edits").
Architecture: `docs/adr/ADR-0002-dex-execution-admission-receipt-boundary.md`
Normative contract: `docs/contracts/execution-admission-receipt-v1.md` (§2 admission, §4 collection ingest, §5 receipt, §6 recovery)
Operator authorization: #526 comment 6109535861 (2026-10-11)

## Goal

Close the proven missing integration seams (gap matrix #526 c6107371470 §B; structured audit c6108837892) by wiring the ACCEPTED foundations end-to-end inside A-Conductor:

authority-gated admission issuer → correctly bound dispatch/collect through a transport port → strict `decode_collected_evidence` → idempotent `SQLiteExecutionStore` receipt.

## Reused foundation (do NOT duplicate)

- `src/a_conductor/dex_identity.py` — `DexBindingIdentity`, `binding_digest`, `canonicalize_existing_root`, `canonical_root_digest` (frozen byte-compat vectors vs SRM).
- `src/a_conductor/dex_evidence.py` — `decode_collected_evidence` (strict decoder, quarantine semantics).
- `src/a_conductor/execution_record.py` — `DurableExecutionReceipt`, `new_execution_receipt`, `compute_receipt_id`, `ReceiptDisposition`.
- `src/a_conductor/execution_store.py` — `SQLiteExecutionStore.record_receipt` / `get_receipt` (idempotent UNIQUE(execution_id, attempt_id, result_digest, binding_digest)).
- SRM main DEX-2a supervisor + MCP dispatch/collect tool schema (unchanged substrate).

## New deliverable (bounded)

1. `src/a_conductor/dex_admission.py` — typed, durable, idempotent admission decisions:
   - `AdmissionRequest` validation; claim-generation freshness gate (stale → typed denial);
   - duplicate admission (same execution/attempt identity) → same decision, at most one live attempt;
   - authority-gated: callers present the claim view; no new claim authority is created here.
2. `src/a_conductor/dex_wire.py` — end-to-end orchestrator over an injectable transport port:
   - admit → receipt-existence idempotency check → dispatch → collect → strict decode (expected digests from the binding) → idempotent receipt;
   - typed outcomes for: unauthorized/stale admission denial (before any dispatch), duplicate run (skip dispatch, return existing receipt), lost/ambiguous dispatch response (LAUNCH_AMBIGUOUS pending, never auto-retry), evidence digest mismatch/forgery (quarantined disposition or typed rejection, no ACCEPTED receipt), crash-before-receipt (re-run returns to at-most-once semantics via receipt idempotency).
3. `tests/test_dex_integration.py` — deterministic RED-first integration suite:
   - successful admission → dispatch → collect → receipt; duplicate admission/dispatch at most one effect;
   - stale claim generation denied before dispatch; wrong execution/attempt/binding digest rejected by decode;
   - tampered evidence rejected; repeated receipt idempotent; LAUNCH_AMBIGUOUS path produces no duplicate effects;
   - real-substrate exercise: when env `SRM_REPO_ROOT` points at a synced SRM checkout, a Node driver invokes the REAL `ExecutionSupervisor` (dist build) to produce genuine collection evidence consumed by the same wire (recorded as local evidence; auto-skip with explicit marker when unset — hosted CI stays deterministic on the contract tier).

## Forbidden

- Any SRM source mutation; any change to the frozen digest vectors or existing accepted tests.
- New scheduler/task DB/claim/admission/receipt/evidence authority beyond this module wiring.
- Real enrollment, remote transport activation, live mutation canary, secrets handling.
- Self-merge; merge requires independent exact-SHA R3 review + hosted CI + accepted merge authority.

## Compatibility gate

Implementation base: AWC `1303961070103131441aa3ca508e79f52327baae` + SRM `f4bdd57465e79874eb3c371b4b0602729a241467` (read-only substrate reference; the SRM MCP binding schema and digest semantics are pinned by the frozen vectors). Any drift before merge → re-pin + focused review.

## Stop conditions

- If independent review finds the transport-port abstraction creates a shadow transport authority → park the port seam, keep admission+decode+receipt wiring.
- If real-substrate driver reveals a substrate contract gap → park implementation, record evidence, return to #526 (do not patch SRM without a new authorization).

## Checkpoint log (append-only)

- [2026-10-12] WO created per operator authorization 6109535861; gap evidence 6107371470/6108837892; worktree `A:\GitHub\_worktrees\AWC-dex2c-integration`, branch `feat/dex2c-integration-wiring`, base `1303961`. No source mutation yet.
