# WO-P1-260 — DEX-2b: A-Sunday Conductor reconciliation and receipt

Status: OPEN (future implementation; not yet claimed — gated behind acceptance of this architecture packet)
Issue: #348
Risk: R2 NORMAL — control-plane reconciliation/receipt behavior on existing authorities
Owner/integrator: GPT-5.6 Sol
Topology: CONTROL_PLANE_ONLY (label defined in `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`)
Architecture: `docs/adr/ADR-0002-dex-execution-admission-receipt-boundary.md`
Normative contract: `docs/contracts/execution-admission-receipt-v1.md` (sections 2, 5–6, plus admission-side canonical identity formation and digest stability from section 1, are this WO's binding scope)

## Goal

Implement the control-plane side of the DEX execution seam in A-Sunday
Conductor: consumption of immutable SunDayRemoteMCP collection evidence,
task-aware idempotent receipt, and reconciliation of delegated executions —
by extending existing job/execution/operator authorities, never by duplicating
their stores.

## Dependencies

1. DEX-ARCH-1 packet accepted and merged (ADR-0002 + contract v1 + fault-injection DEX scenarios on main).
2. WO-P1-259 (DEX-2a) substrate supervision accepted, or a contract-conformant fake substrate sufficient for deterministic receipt/reconciliation tests.
3. Exact compatibility set frozen; no overlapping mutable lane on claimed A-Wiki-Conductor paths.

## Scope principles

- Consume immutable SRM evidence exactly as collected (strict decode, digest + binding verification, quarantine on mismatch); never treat substrate markers as acceptance.
- Task-aware idempotent receipt keyed by `(execution_id, attempt_id, result digest)` + binding digest, binding claim generation and pinned SHA set; repeated receipt returns the same receipt with no double-apply.
- Implement `TERMINAL_UNHARVESTED` harvest-before-conflict semantics per `EXECUTION_LIVENESS_PROTOCOL.md` and the admission/receipt contract.
- Extend existing durable job store / execution records / recovery reconciliation / `operator.v1` surfaces; no second task DB, scheduler, claim store, review state machine, completion authority, or SSoT.
- Retry authorization only through existing replay-safety classification (`NOT_STARTED`/`PARTIAL`/`COMPLETE_UNVERIFIED`/`COMPLETE_VERIFIED`/`UNKNOWN`) under the current claim generation; outcome-known never implies retry-authorized.
- Canonical path identity ownership (admission side): implement canonical worktree/repo path identity canonicalization and binding-digest formation per contract section 1 — OS final physical path resolution of the existing root (Windows `GetFinalPathNameByHandleW`-equivalent following junctions/reparse points, deterministic drive/UNC/extended-prefix normalization, case-insensitive comparison; POSIX `realpath`-equivalent, case-sensitive; lexical normalization alone is insufficient), frozen into the immutable binding tuple/digest at admission. Canonicalization failure, non-existent required root, or unresolved alias identity fails closed before admission (`REJECTED: PROJECT_IDENTITY_FAILED`). Digest stability: once accepted, the canonical identity and binding digest are immutable for the attempt; later alias spelling changes never rewrite an accepted attempt, and later physical-identity drift fails new mutation closed while immutable terminal evidence stays collectable under the drift rules. SRM-side recomputation/verification belongs to WO-P1-259 only.
- Deterministic receipt/reconciliation/fault tests: implement the control-plane halves of every v1-scope DEX scenario in `docs/contracts/fault-injection.md` — all scenarios except the future DEX-3a `NOTIFICATION_ACK_LOSS`, which v1 receipt gates MUST NOT require.

## Forbidden authority (fail-closed)

- No new scheduler, task store, claim/lease store, retry engine, review/completion authority, project SSoT, or secret store.
- No mutation of SunDayRemoteMCP; no supervision of foreign processes beyond identity verification the contract allows.
- No chat/session state as execution truth; no ChatGPT self-wake claims; wake/resume only via supported capability-proven surfaces.
- No secret/credential persistence; raw secret argv/env forbidden in any durable record.
- No broad process kill; exact-PID + verified command identity only.

## Compatibility gate

- Freeze one exact candidate head per repo in the compatibility set `{A-Wiki-Conductor@SHA_AUTH, SunDayRemoteMCP@SHA_EXEC}`; drift invalidates until re-pin.
- Independent read-only exact-SHA review; A-Wiki exact-head hosted CI required; authority repo merges first, then execution repo (if WO-P1-259 ships in the same set).

## Recovery / rollback

- Rollback disables the receipt/reconciliation path while preserving durable receipts/events (append-only); no replay of unfinished work on re-enable.
- Interrupted implementation attempts reconcile from actual Git/runtime evidence before retry; `UNKNOWN` fails closed.

## Fan-in / review / rollback sequence

1. Exact candidate head frozen on the claimed branch; deterministic checks green.
2. Independent read-only exact-SHA review returns `P0=0 P1=0 P2=0`.
3. Exact-head CI run ID recorded; expected head merged only; post-main CI run ID recorded.
4. Checkpoint on Issue #348 with merged SHA(s), review/CI evidence, and WIP ledger before closure.

## Verify commands (to be pinned at claim time)

- Full `a_conductor` test suite including new deterministic receipt/reconciliation fault tests, on the exact candidate head.
- `git diff --check`, exact-path scope check, strict UTF-8, added-line secret scan.

## Checkpoint log (append-only)

- [2026-09-19] DEX-ARCH-1 author: WO created as bounded future work; no runtime implementation started.
- [2026-09-19] DEX-ARCH-1 repair-r1: added canonical path identity ownership (admission-side canonicalization/digest formation) scope and explicit v1-scope fault-gate wording per independent review (P1, P2-2); no runtime implementation started.
