# WO-P1-625 — DEX-2c: A-Conductor admission/receipt end-to-end wiring

Status: IN_PROGRESS (claimed 2026-10-12 by the GLM-5.3 MAX wake lane)
Issue: #625
Parent: #526 (operator authorization comment 6109535861); dependency framing: #495. Lane issue #625 was created retroactively at merge-prep: the original numeric id 612 collides with merged PR #612 and cannot satisfy the GitHub-backed identity contract.
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

1. `src/a_conductor/dex_admission.py` — typed, frozen (in-process), idempotent admission decisions:
   - `AdmissionRequest` validation; claim-generation freshness gate (stale → typed denial);
   - replay of a decided identity returns the same decision; denials are frozen and re-raised; a replay presenting a mutated binding digest / claim reference / claim generation is a typed identity conflict — decisions are in-memory only (see §Limitations, deferred to DEX-2d);
   - authority-gated: callers present the claim view; no new claim authority is created here.
2. `src/a_conductor/dex_wire.py` — end-to-end orchestrator over an injectable transport port:
   - admit → execution-record precondition → receipt-idempotency check → ONE dispatch → collect → strict decode (expected digests from the binding, generation agreement with the admission) → idempotent receipt;
   - per-identity lock held from the fence check through receipt persistence, so concurrent in-process `run_attempt` calls cannot double-dispatch (loser observes the receipt or the fence);
   - typed outcomes for: unauthorized/stale admission denial (before any dispatch), duplicate run (skip dispatch, return existing receipt), lost/ambiguous dispatch response (identity permanently fenced, typed AMBIGUOUS, never auto-retry), collect failure after dispatch (fenced — re-dispatch would duplicate substrate effects), evidence digest mismatch/forgery (typed rejection or QUARANTINED disposition, never a silent ACCEPTED), receipt-store conflict on any immutable field (typed WIRE_RECEIPT_CONFLICT, never masked as duplicate success), receipt-persistence failure after dispatch (fenced + typed — the substrate effect already happened, so no in-process re-run can dispatch again);
   - crash-before-receipt recovery relies on substrate scope-conflict truth plus explicit reconciliation — this wire adds NO durable cross-restart fence (see §Limitations).
3. `tests/test_dex_integration.py` — deterministic RED-first integration suite:
   - successful admission → dispatch → collect → receipt; duplicate admission/dispatch at most one effect;
   - stale claim generation denied before dispatch; wrong execution/attempt/binding digest rejected by decode;
   - tampered evidence rejected; repeated receipt idempotent; LAUNCH_AMBIGUOUS path produces no duplicate effects;
   - real-substrate exercise: when env `SRM_REPO_ROOT` points at a synced SRM checkout, a Node driver invokes the REAL `ExecutionSupervisor` (dist build) to produce genuine collection evidence consumed by the same wire (recorded as local evidence; auto-skip with explicit marker when unset — hosted CI stays deterministic on the contract tier).

## Limitations — explicitly deferred to successor slice DEX-2d

This slice's guarantees are IN-PROCESS only. The following are NOT delivered here and need their own bounded work order (and, where they cross the trust boundary, their own operator decision):

1. **Durable admission journal** — admission decisions and fences live in process memory; restart loses them (a fresh issuer/ wire re-evaluates from scratch).
2. **Cross-restart at-most-once dispatch fence** — a crash between dispatch and receipt persistence is NOT prevented from re-dispatching by this wire; recovery relies on the substrate's scope-conflict truth plus explicit manual reconciliation.
3. **Contract §6 same-execution retry model** — new attempts require new execution identities in this slice; any recorded receipt conservatively blocks further dispatch under the same execution id.
4. **Contract §2 simultaneous-dispatch fencing beyond one process** — the per-identity lock serializes calls within one wire instance only; multi-process/multi-host admission is out of scope.
5. **Contract §5 TERMINAL_UNHARVESTED blocking on admission** — the wire does not yet consult unharvested-terminal substrate state as an admission precondition.

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
- [2026-10-12] Renamed from the original numeric id 612 (which collides with merged PR #612 and cannot satisfy the GitHub-backed identity contract, caught by `tests/test_work_order_identity.py` on hosted CI) to WO-P1-625, with retroactive lane issue #625. No code behavior changed; all references updated.
