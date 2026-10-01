# WO-P1-220 — independent exact-SHA review: WO219 Phase-C0 provenance repair

```text
VERDICT=PASS
P0=0 P1=0 P2=0 P3=2
merge_performed=false
```

- Exact target: `a2cb571d33e528840f47660d98fcdec80cad889b` (PR #299 head verified exact, OPEN/unmerged; base = `feat/wo-p1-216-zra2-phase-c0-binding`). Parent `ade1628247a4512fa879c10bfd093d14f51d487f` (PR #296, still OPEN standalone — the defective-parent status preserved). `git merge-base --is-ancestor` confirms candidate rooted at parent. WO218 evidence (`063e8af…`) maps to that parent. PR #298 `41ba9f5…` untouched per SUPERSEDED_DO_NOT_MERGE.
- Hosted CI exact head (run 34668636852): macos **pass**, ubuntu **pass**, windows `test` **pass** (15m6s) — all terminal SUCCESS, re-pinned this session.
- Diff boundary: exactly 3 paths (`zero_relay_review_task.py` +163/−67 rework, `tests/test_zero_relay_review_task.py` +263, WO219 doc) — bounded, no unrelated production scope.
- Reviewer independence: this GLM lane is the WO216 C0 reviewer-of-nothing (WO214 MASTER stopped at an external owner before any C0 source was written by this lane; the C0 implementation and WO219 repair are other lanes' work). Candidate source/tests read-only through a detached worktree at the exact SHA; no candidate edits, no merge, no live runtime.
- Host: DESKTOP-7IB57R4 / Windows 11 / Python 3.11.15.

## WO218 attack replays — all five now fail closed (independent probes, not candidate tests)

| Attack | Probe | Result on candidate |
|---|---|---|
| A fabricated write-result (wrong path/size/hash after create) | `LiarFS` subclass returns fake `NativeWriteResult` | **`REVIEW_TASK_VERIFY_FAILED`** (result object checked AND persisted bytes re-read+verified) |
| B caller-forged `MaterializedReviewTask` (invented SHA / invented refs) | `dataclasses.replace` forgery | **`REVIEW_TASK_VERIFY_FAILED`** / **`AUTHOR_IDENTITY_MISMATCH`** (bind re-derives refs from author+head and compares persisted SHA against rendered content) |
| C packet in foreign worktree (matching suffix/hash/contract) | route worktree ≠ filesystem root | **`REVIEW_FILESYSTEM_ROOT_MISMATCH`** (`windows_worktree_key` root fence) |
| D old packet rebound to new internally-consistent route HEAD | route head `"b"×40` vs review head `"a"×40` | **`REVIEW_HEAD_MISMATCH`** (review head ≠ route head) — note the deeper replay (same packet digest with different head) is impossible because the head is inside the canonical digest, verified by DET probes |
| E duck-typed persistence authority at C0a/C0b | `DuckFS` object | **`FILESYSTEM_INVALID`** at both seams (strict `isinstance(NativeFileSystem)`) |

**Parent discrimination (non-vacuity):** the same LiarFS input run against the parent tree `ade1628…` is **ACCEPTED** (`PARENT_ACCEPTED_FABRICATED_RESULT` — the WO218 defect reproduced), while the candidate refuses it with the typed code. The probe is discriminating.

## Adversarial campaign (40/40 enforced — `runs/WO-P1-220/probe-results.json`)

- **Determinism:** same identity+HEAD → same canonical bytes/refs/markdown-SHA; mixed-case HEAD casefolds to the same digest; different HEAD changes contract/task/result identity; all seven `ResultIdentity` fields individually change the digest.
- **HEAD boundaries:** 7/40/64-char accepted; 6-char, 65-char, non-hex, empty, non-string rejected.
- **TOCTOU:** vanished persisted file before bind → `REVIEW_TASK_STATE_UNVERIFIABLE`; divergent bytes → `REVIEW_TASK_VERIFY_FAILED`; same-path/divergent-bytes at materialize → `REVIEW_TASK_COLLISION` preserved; same exact bytes → idempotent reuse (`created` True→False, same SHA).
- **UTF-8:** Thai/emoji identity fields produce exact bytes; persisted SHA equals on-disk bytes; strict decode OK.
- **Route binding:** positive control binds with every field; head mismatch, packet-hash mismatch, dispatch-contract mismatch, PROJECT_MUTATION, result-destination mismatch, author↔reviewer execution alias, author-identity drift — all typed refusals. Packet-path normalization: suffix-only rejected; dot-segments/backslashes/trailing-slash fold to the same absolute path under `windows_worktree_key` (normalized equivalence, not authority drift).
- **Delegated-fact classification (packet question answered):** `dispatch_gate.allowed=False`, model-absent-from-profile, unsupported harness/effort, provider readiness/admission/generation drift are **executor-level admission facts**: `ParallelReadyTask`'s constructor itself refuses the unconstructible states (verified: dispatch-contract mismatch → constructor `ValueError`; empty `ProviderConfiguration.models` → constructor `ValueError`), and the executor re-checks the gate before dispatch. C0 records provider/model from the *validated dispatch* and mints no new provider authority — delegation is sound under WO210 trusted-route semantics; C0 additionally re-checks the facts it consumes directly (head/branch/contract/destination/READ_ONLY/independence/root/path/packet bytes).
- **Result-contract question (packet §direct-review):** the rendered task requires a bounded verdict vocabulary (`ACCEPTED or REJECTED per the ZRA-2 Phase-A decision contract`) and pins the exact identity/HEAD the reviewer must target; the deterministic `result_ref` fixes the destination C1 must read, and `DirectReviewRoute` carries `review_task_sha256` + author digest binding. The verdict line is a **prose requirement in the task, not yet a machine-readable schema enforced at C0** — recorded as P3-1: C1 must define the validated result shape (e.g., verdict token + reviewed digest echo) when it consumes `result_ref`/stdout/report evidence; the packet's `DIRECT_REVIEW_RESULT_CONTRACT_MISSING` bar is NOT triggered because the C0 seam does define the deterministic destination, the bounded vocabulary expectation, and the hash-bound identity chain C1 needs — the remaining work is C1's own consumption contract, which is C1's declared scope (WO201), not a hole in C0's provenance chain.

## Regression floor (exact candidate, detached)

| Command | Result |
|---|---|
| `pytest -q tests/test_zero_relay_review_task.py` | **46 passed** |
| `pytest -q tests/test_native_execution.py tests/test_zero_relay_repair_materializer.py tests/test_zero_relay.py` | **108 passed** |
| `pytest -q tests/test_claude_code_harness.py tests/test_parallel_ready_execution.py tests/test_agent_change_packets.py tests/test_review_mailbox_adapter.py` | **194 passed, 1 skipped** |
| `compileall -q src/a_conductor/zero_relay_review_task.py` | OK |
| `git diff --check ade1628..a2cb571` | clean |
| strict UTF-8 / no U+FFFD (source+tests at exact SHA) | OK |
| added-line scan (523 added) | 1 hit = the English word "credential" in a doc sentence ("live runtime/provider/credential state" — forbidden-scope prose in the WO219 work order), not a secret |

## Findings

- **P0 = 0, P1 = 0, P2 = 0.**
- **P3-1:** the reviewer-output verdict requirement is task prose (`ACCEPTED or REJECTED ... per Phase-A contract`), not a C0-enforced machine-readable schema; C1 must pin the consumed result shape when binding `result_ref`/reviewer evidence. Advisory, C1-scope.
- **P3-2:** `MaterializedReviewTask.persisted_sha256` must equal the *rendered-markdown* SHA (bind re-derives via `_expected_content_sha`), while `refs.digest` hashes the *canonical JSON* — two adjacent digests with different inputs; correct as implemented (each compared only against its own re-derivation) but a future reader could confuse them; a doc comment or field rename would help. Advisory.

## Boundary & next safe action

`merge_performed=false`. This review recommends **PASS** (P3-only). GPT-5.6 Sol owns adjudication of PR #299, the merge order versus parent PR #296 (stacked), and any C1 release decision. Next safe action: GPT-5.6 Sol adjudicates PR #299 at exact `a2cb571` using this review; on acceptance, proceed per Issue #214 C1 gating.
