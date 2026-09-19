# WO-P1-259 — DEX-2a: SunDayRemoteMCP physical execution supervision

Status: OPEN (future implementation; not yet claimed — gated behind acceptance of this architecture packet)
Issue: #348
Risk: R2 NORMAL — execution-substrate runtime behavior under control-plane authority
Owner/integrator: GPT-5.6 Sol
Topology: EXECUTION_SUBSTRATE_ONLY (label defined in `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`; authority work order is this WO in A-Wiki-Conductor)
Architecture: `docs/adr/ADR-0002-dex-execution-admission-receipt-boundary.md`
Normative contract: `docs/contracts/execution-admission-receipt-v1.md` (sections 3–4 are this WO's binding scope)

## Goal

Implement the substrate side of the DEX execution seam in SunDayRemoteMCP:
per-attempt physical supervision and immutable collection evidence, exactly as
bounded by the admission/receipt contract. SRM remains execution substrate
only; every task/claim/admission/receipt/review/acceptance decision stays in
A-Sunday Conductor.

## Dependencies

1. DEX-ARCH-1 packet accepted and merged (ADR-0002 + contract v1 + fault-injection DEX scenarios on main).
2. SunDayRemoteMCP canonical `main` re-pinned; exact compatibility set frozen per WO-P1-251 rules.
3. No overlapping mutable lane on the claimed SRM paths (global cross-repo WIP accounting).

## Scope principles

- Mutations live in the SunDayRemoteMCP repo only; A-Wiki-Conductor is mutated only by separate authority-side work orders (WO-P1-260 for the control plane).
- Implement: per-execution shim/resource-guard boundary; parent/child/descendant identity capture; descendant quiescence verification; exact PID + creation-identity + boot-epoch tracking (PID-reuse defense); repeatable immutable collect with content digests; supervisor-observed vs executor-claimed fact separation; bounded/redacted output; collection-under-drift flagging without granting mutation.
- Honor the durable Windows no-console rule (exact executable, hidden window, `CREATE_NO_WINDOW`/`windowsHide`, exact-PID-only termination).
- Deterministic fake/fault tests: implement the substrate-side halves of every DEX scenario in `docs/contracts/fault-injection.md` (admission response loss, simultaneous dispatch, shim crash before/after spawn, PID reuse, result-before-receipt, receipt response loss, reboot, path alias/junction overlap, claim/session loss while child alive, malformed/forged evidence, cross-repo SHA mismatch).
- Process/replay safety: no retry logic of any kind in SRM; `LAUNCH_AMBIGUOUS` reconciliation is observation + evidence, never respawn.

## Forbidden authority (fail-closed)

- No task, work-order, claim/lease, admission-decision, receipt, retry-authorization, review, or completion authority.
- No scheduler, task store, second SSoT, provider/quota authority, or secret store.
- No acceptance semantics in any substrate status/marker vocabulary (advisory collection state only).
- No broad process kill; no mutation of A-Wiki repos; no secret/credential persistence or raw secret argv/env in evidence.
- No new MCP/web surface beyond the typed supervision/collect operations required by the contract.

## Compatibility gate

- Freeze one exact candidate head per repo: `{A-Wiki-Conductor@SHA_AUTH, SunDayRemoteMCP@SHA_EXEC}`; any member drift invalidates the set until re-pin and focused review.
- Independent read-only exact-SHA review; hosted CI where available, otherwise the recorded deterministic fallback (WO-P1-251 precedent); authority repo merges first.

## Recovery / rollback

- Rollback disables the new supervision path without deleting legacy connectors or evidence; immutable collected evidence is retained.
- Any interrupted implementation attempt must be reconciled from actual Git/runtime evidence (`TERMINAL_UNHARVESTED` / `INTERRUPTED` / `UNKNOWN`) before retry; no blind replay.

## Verify commands (to be pinned at claim time)

- SRM build + full deterministic suite including the DEX fault scenarios above, on the exact candidate head.
- `git diff --check`, exact-path scope check, strict UTF-8, added-line secret scan, relative-reference resolution.

## Checkpoint log (append-only)

- [2026-09-19] DEX-ARCH-1 author: WO created as bounded future work; no runtime implementation started.
