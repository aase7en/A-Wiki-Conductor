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
- [2026-09-20] WO-P1-260-ROOT-DIGEST-COMPAT-001 repair (branch `feat/wo-p1-260-dex-2b-reconciliation-receipt`, base/dispatch head `ae6a421d6e7efb0beaa35ec6e3447a17bc8f4e0e`): added dedicated `canonical_root_digest(canonical_path, *, platform_tag)` to `src/a_conductor/dex_identity.py`, byte-compatible with SRM `AdmissionBinding.canonicalDigest` at frozen SRM reference `src/sunday/canonical-path.ts@251b0524289bade47ed0c6656a487ddfdc457fb1` — SHA-256 lowercase hex over UTF-8 `platform_tag + NUL + normalized canonical path`, CanonicalPlatform exactly `"win32"|"posix"`, consuming the already-normalized output of `canonicalize_existing_root` (no second resolver, no alternate normalization authority). Frozen byte-compatible vectors pinned in `tests/test_dex_identity.py`: `win32` + `c:\repo\work` -> `aa2a21e52e96d0188faca668dcbeda48d6c0c454859ab32caee8cd325ad4c786`; `posix` + `/srv/repo` -> `e316d7049a2dcb0ae2be546a7fedb07d537ac769735d567e96985a2e0a73084f`; `win32` + `\\server\share\repo` -> `b4f5a4a7b27cc64a7e11dff32f2412e63c279e11e5150b7bf3f97a8c6893c2ba`. RED-first: 20 new tests failed on unmodified head (`AttributeError: no attribute 'canonical_root_digest'`); post-repair green: 25/25 `tests/test_dex_identity.py`, 40/40 dex evidence/fake-substrate suites, 46/46 adjacent project/work-order identity suites; `py_compile`, `git diff --check`, strict UTF-8 clean; exact 3-path scope. Non-regression: full `binding_digest` untouched (pure-addition diff) with preimage `81e55bd0f4e5cf75ea314aa626465b604a4b0f060e15e5791770224b2cbb64bd` pinned unchanged. PR #403 remains draft; no merge/self-accept; next = independent exact-SHA R3 review/fan-in.
- [2026-09-20] WO-P1-260-DEX2B-NONASCII-NORMALIZATION-PARITY-REPAIR-001 (same branch, dispatch head `b2ec5a463296a25ee46bec82213ffdc4e8b33d17`): closed the independent R3 non-ASCII parity finding by changing only the final Windows canonical case normalization in `_normalize_windows_final_path` from `str.casefold()` (full folding, `Straße` -> `strasse`) to `str.lower()` (simple Unicode lowercase, `Straße` -> `straße`), matching SRM's accepted `normalizeWindowsPath` `String.toLowerCase()` semantics; UNC marker prefix recognition remains case-insensitive; POSIX path untouched. RED-first: new `test_windows_final_nonascii_case_matches_srm_lowercase_not_casefold` failed on unmodified head (`c:\repo\strasse` != `c:\repo\straße`); post-repair pins canonical `c:\repo\straße` and `canonical_root_digest` = `364893ee1c50f5c718bdaab1598cfee477a2659312ed41e7d045628dd87e996a` (SHA-256 over UTF-8 `win32\0c:\repo\straße`). All three frozen vectors and full `binding_digest` preimage (`81e55bd0...bb64bd`) unchanged. Green: 26/26 `tests/test_dex_identity.py`, 136 total with dex evidence/fake-substrate/execution record/store + work-order/project identity suites; `py_compile`, `git diff --check`, strict UTF-8/no U+FFFD, added-line secret scan clean; exact 2-path source scope + this checkpoint. Pushed to existing branch; next = exact-head CI + independent focused R3 rereview; no self-accept/merge.
