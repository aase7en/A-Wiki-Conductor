# WO-P1-459 — Bounded A-Wiki secret writer (GLM-5.3 MAX author, run r2)

Issue: #459
Parent: Browser Wake / BWA-1B2
Claim: WO-P1-459-AWIKI-SECRET-WRITER-REPAIR-WINDOWS-003
Topology: CONTROL_PLANE_ONLY
Risk class: R3 credential/filesystem trust boundary
Repo: A-Wiki-Conductor
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo459-awiki-secret-writer-r2`
Branch: `feat/wo-p1-459-awiki-secret-writer-r2`
Dispatch base/head expected: `a37746f67631c9ed8edd23fa20b80b8ef4d3dfd9`
Status: REPAIR-CYCLE2-FANIN-GREEN / FREEZE-PENDING (reviewed candidate
643891f returned CHANGES_REQUIRED P2=1; bounded repair is deterministic-green;
current main b7cd755 has been normally merged and exact post-fan-in gates pass;
final freeze waits only for the roadmap merge queue to settle before push/review)

## Binding

Author packet: `runs/WO-P1-459/author/run-postreset-a1/task.md` (this worktree).
Mutable scope (exactly three paths, all new in this lane):

- `src/a_conductor/awiki_secret_writer.py`
- `tests/test_awiki_secret_writer.py`
- `docs/work-orders/WO-P1-459-awiki-secret-writer.md`

Everything else is read-only for this lane. No live private Drive file, real
credential, provider store/config/runtime/UI/browser file, `CURRENT-WORK.md`,
or `handoff.md` was touched. No commit, push, or merge was performed.

## Delivered capability

`AWikiSecretWriter` performs exactly three operations on exactly one target —
`<authorized_drive_root>/secrets/global.env` under an explicitly authorized,
canonicalized Drive root: INSERT (absent key), ROTATE (exactly one existing
plain assignment), DELETE (exactly one existing plain assignment). Results
carry redacted metadata only (`operation`, `key`, `target`); raw values never
appear in results, representations, error codes, temporary-file names, or
exception messages.

## Authority reuse and fences

- Reuses, never changes, the accepted reader contract in
  `awiki_environment_resolver.py`: `_ENV_KEY_RE` (shape only), `_parse_env_file`
  (projection + pre-replace verification), and `AWikiDriveEnvironmentSource`
  (post-replace read-back verification and delete-absence proof).
- `_ENV_KEY_RE` is shape validation only. Every write requires an explicit
  caller-supplied `AWikiSecretWriteAuthority` (non-empty, canonical shape, no
  duplicates, cardinality <= 64, retains no values); syntactically valid but
  non-allowlisted keys fail `KEY_NOT_ALLOWED` before any disk access
  (bytes and mtime proven unchanged).
- No root auto-discovery: `A_WIKI_DRIVE_PATH`/home fallbacks are ignored; the
  root must be an existing directory supplied explicitly. Target containment
  plus symlink/junction/reparse checks fail closed with `TARGET_ESCAPE`.
- Round-trip fence: values are rejected unless the accepted reader would
  return them exactly (no surrounding whitespace, no symmetric quote wrapper,
  no NUL/CR/LF or other line-break characters). Adversarial values with `=`,
  `#`, backslashes, internal quotes, `;`, tabs and non-ASCII round-trip
  exactly through `AWikiDriveEnvironmentSource`.
- Duplicate target assignments are detected line-level before any dict
  projection (the reader's last-wins dict cannot hide ambiguity). Comment
  text containing `KEY=`/`export KEY=` shapes is never authority
  (`_classify_line` mirrors the reader's line semantics; a corpus test proves
  equivalence against `_parse_env_file`).
- `export KEY=` assignments of the target key are explicitly rejected
  (`EXPORT_SYNTAX_UNSUPPORTED`); unrelated `export` lines are preserved
  byte-for-byte.
- Byte-preservation contract: UTF-8 BOM marker, per-line LF/CRLF terminators,
  final-newline shape, comments, spacing, invalid-key lines, and unrelated
  order are preserved. Deterministic exceptions, documented in the module:
  INSERT may append the missing terminator after an unterminated final line;
  mixed-convention files use LF for new/rewritten lines; ROTATE rewrites the
  owned line in canonical `KEY=value` form.
- Atomicity: same-directory uniquely owned temp (`.awiki-secret-writer-*`,
  never named from key or value), write + flush + fsync, pre-replace
  projection verification through the accepted reader, existing-mode
  preservation, pre-replace drift fence (captured bytes must match exactly,
  else `TARGET_DRIFTED` with the concurrent edit preserved), `os.replace`,
  read-back verification through `AWikiDriveEnvironmentSource`, and verified
  atomic rollback (`WRITE_ROLLED_BACK`) with distinct `RECOVERY_REQUIRED`
  when restoration cannot be proven. A replace exception is classified by
  exactly one target observation (unchanged / desired / third-state). No
  blind retry, no upsert, no hidden lock authority (no lock file; the drift
  fence plus fail-closed typing is the concurrency contract for this slice).
- The writer never creates a missing `secrets/` directory or `global.env`
  (`TARGET_DIRECTORY_MISSING` / `TARGET_MISSING`); therefore no
  new-file-permission path exists, and existing target mode bits are
  preserved where the platform exposes them (POSIX-tested; Windows ACL
  inheritance is the documented bounded behavior).
- The module imports only `os, re, stat, tempfile, dataclasses, pathlib,
  typing` plus the accepted resolver; no provider store/DB/network/child
  process/logging coupling (import whitelist test; monkeypatched
  subprocess/socket surfaces explode).

## RED evidence

Tests were written first; production module was a behavior-free skeleton
(public surface raising `NotImplementedError`). First execution:

- Command: `python -m pytest tests/test_awiki_secret_writer.py -q`
- Result: **78 failed, 2 passed, 1 skipped in 8.69s**
- The 2 passes are the reader-contract documentation test and the static
  import-whitelist test (they do not exercise writer behavior); the skip is
  the POSIX-only mode test. All 78 behavioral cases were real executed
  failures against the skeleton before implementation.

## GREEN evidence

Same command after implementation: **80 passed, 1 skipped in 2.26s**
(skip = POSIX-only mode-preservation test on Windows).

## Related verification (all with the repo test interpreter)

- `python -m pytest tests/test_awiki_environment_resolver.py -q` — green
- `python -m pytest tests/test_provider_configuration.py tests/test_provider_runtime_assembly.py tests/test_desktop_control.py -q` — green
  (credential_ref stays `secret-ref:`-only; `secret-ref:awiki-env/<KEY>`
  runtime support unchanged; no raw-secret coupling anywhere)
- `python -m pytest tests/test_work_order_identity.py -q` — green with this
  document present (numeric id 459, exactly one `Issue: #459` line)
- `python -m py_compile src/a_conductor/awiki_secret_writer.py` — OK
- Combined related-suite run: 117 passed, 1 warning (unrelated docs warning)

## Hygiene

- `git diff --check` — clean (no whitespace errors)
- Strict UTF-8 decode of all three mutable files — OK
- Added-line secret-shape scan — only synthetic canaries/vocabulary
  (`CANARY-WO459-SYNTHETIC-...`, `top-secret-value` style fixtures in
  pre-existing tests); no credential-shaped material
- Final `git status` contains exactly the three mutable paths (runs/ is
  gitignored evidence storage)

## Synthetic-only statement

All writer tests use synthetic temporary directories created by pytest
fixtures. No live Drive root, real env file, or real credential material was
read or written by this work. The only raw-value proxy is a unique synthetic
canary asserted absent from every result/representation/error surface.

## Dependency note (WO461 fan-in) — corrected in repair cycle 1

The earlier author-time claim that dispatch base `a37746f` already contained
the accepted WO461 post-main repair was **false**. Truth:

- `a37746f` is the PR #463 *initial* WO461 merge
  (`Merge pull request #463 ... WO461 GraphStore v2 run authority`), not the
  post-main repair.
- The WO461 post-main repair is PR #466, candidate
  `44f1f3dff4f5fa5b8662a81e2071978447b72deb`.
- PR #466 candidate `44f1f3dff4f5fa5b8662a81e2071978447b72deb`
  received an independent GLM-5.3 MAX PASS with P0/P1/P2=0, exact-head CI
  green on Windows/Ubuntu/macOS, and was merged as
  `main@cb5f9b6b5188df68abb57fa9967b70a4004cca04`.
- WO461 post-main verification then passed focused 35, graph-impact 219,
  work-order identity 33, and concurrency/replay stress 60/60; Issue #461 is
  COMPLETE / POST_MAIN_VERIFIED.

Current-main fan-in is complete in this lane. The pre-fan-in feature commit is
`8aa269fe5b7b549838fb56a8b06f6026fe961e5d`; normal merge of
`main@cb5f9b6...` produced fan-in head
`bec8d5e129b1566e45dc355cb97d7a6369db413c` with no path conflict. Final
freeze now requires rerunning the WO459 verification block on this fanned-in
state, then exact-SHA independent R3 review + hosted CI.

## Repair cycle 1 (this revision)

Integrator review of the author candidate produced two blocking findings;
both are repaired in this revision within the same three mutable paths.

1. Rollback permission-restoration proof: `_rollback()` previously ignored
   an `os.chmod(rollback_temp, original_mode)` failure, still
   replaced/restored bytes, verified bytes only, and returned success, so
   callers could report `WRITE_ROLLED_BACK` while mode restoration was
   unproven. Repair: the rollback now remembers a mode-restoration failure,
   still restores original bytes when safely possible, verifies bytes, and
   only then raises `RECOVERY_REQUIRED` (never `WRITE_ROLLED_BACK`) when
   mode restoration is unproven. No blind retry; owned rollback/temp
   artifacts are still never left; normal successful rollback behavior is
   unchanged (existing `WRITE_ROLLED_BACK` success-path tests stay green).
2. WO461 dependency evidence: corrected per the dependency note above.

RED regressions added (both fail on the pre-repair code with
`assert 'WRITE_ROLLED_BACK' == 'RECOVERY_REQUIRED'`; both exercise synthetic
tmp paths only, monkeypatching `os.chmod` to fail solely for the rollback
temp file):

- `test_rollback_mode_restoration_failure_restores_bytes_then_requires_recovery`
  (verify-mismatch rollback path; also asserts original bytes restored and
  no orphan artifacts)
- `test_ambiguous_replace_rollback_mode_restoration_failure_requires_recovery`
  (ambiguous-replace rollback path; same assertions)

Repair-cycle verification (repo test interpreter, this worktree):

- `python -m pytest tests/test_awiki_secret_writer.py -q` —
  **85 passed, 1 skipped** at frozen candidate `643891f` (skip = POSIX-only
  mode test on Windows); the earlier 82-pass note was a documentation miscount
  corrected by the independent exact-SHA review
- `python -m pytest tests/test_awiki_environment_resolver.py
  tests/test_provider_configuration.py tests/test_provider_runtime_assembly.py
  tests/test_desktop_control.py tests/test_work_order_identity.py -q` —
  **117 passed**
- `python -m py_compile src/a_conductor/awiki_secret_writer.py` — OK
- `git diff --check` — clean
- Final status remains exactly the three allowed paths; added-line
  secret-shape scan shows only synthetic canaries/vocabulary

## Repair cycle 2 — independent-review P2/P3 closure

Independent GLM-5.3 MAX review of frozen candidate
`643891fffeb2ac99da7610d9f773292da89366c1` returned
`CHANGES_REQUIRED` with P0/P1/P2/P3 = 0/0/1/2.

Blocking P2 reproduced on real Windows synthetic fixtures: a write-bit-less
target can make `os.replace` return `REPLACE_FAILED` after the owned temp has
inherited read-only mode; the former best-effort unlink could then leave a
readable secret-bearing owned temp. Repair cycle 2 replaces silent best-effort
cleanup with exact-owned-temp cleanup: first unlink, then clear only the
write/read-only bit on that exact writer-owned temp and retry unlink once. If
cleanup still cannot be proven, the operation fails typed
`RECOVERY_REQUIRED`; no unrelated path is touched and the secret write itself
is never blindly retried.

The review's P3 bare-CR/parser mirror edge is also closed fail-closed:
reader-only line boundaries accepted by `str.splitlines()` but not represented
by the writer's LF/CRLF unit model now raise
`TARGET_LINE_BOUNDARY_UNSUPPORTED` before mutation. LF and CRLF remain
accepted.

Delegated repair transport note: a later GLM-5.3 MAX repair run was classified
`TERMINAL_SECURITY_INVALID` because its process monitor observed an
MCP-specific `node.exe` descendant. That model result is not acceptance
evidence. The in-scope partial mutation was preserved, reconciled by the
integrator, and verified deterministically rather than blindly redispatched.

Cycle-2 RED/GREEN evidence on Windows, before folding the latest current main:

- RED: the new regression batch reproduced the read-only orphan and
  reader-only line-boundary failures against the pre-repair behavior.
- `python -m pytest -q tests/test_awiki_secret_writer.py` —
  **102 passed, 1 skipped** (POSIX-only mode test).
- `python -m pytest -q tests/test_awiki_environment_resolver.py
  tests/test_provider_configuration.py tests/test_provider_runtime_assembly.py
  tests/test_desktop_control.py tests/test_work_order_identity.py` —
  **117 passed**.
- `python -m py_compile src/a_conductor/awiki_secret_writer.py` — PASS.
- strict UTF-8 + `git diff --check` — PASS.
- dirty scope before fan-in is exactly the three authorized WO459 paths.

The bounded repair was checkpointed as
`3b95d67844181b3184553f2d23810594f894ede7`, then current authority main
`b7cd755c08adf889727d68489ddcaa4de51615ce` was folded by normal merge (no
rebase/reset/stash) as `89ab20d559bb1fbdd4ad45ea0c9060388152017a`.
Post-fan-in verification is green: the combined focused/related/WO458 regression
set is **267 passed, 1 skipped**; py_compile and diff-check pass; diff vs current
main remains exactly the three authorized WO459 paths. Final remote freeze/push
is intentionally delayed until the current roadmap merge queue settles, so the
candidate can absorb any immediately preceding accepted main without another
stale exact-SHA review.

## Remaining risks / blockers

- POSIX mode-preservation is exercised only where POSIX is available
  (skipped on this Windows author run); Windows ACL inheritance on replace
  is bounded-documented, not bit-asserted.
- Symlink escape tests require symlink privilege; they skip when the
  platform denies it (containment + reparse checks still execute everywhere).
- The drift fence narrows the concurrent-write window to between the final
  byte comparison and `os.replace`; a lock-file authority was deliberately
  not invented (fail-closed typing instead). If a future slice needs a
  cooperative lock, it must be its own work order.
- Repair cycle 2 is deterministic-green and has folded accepted WO458 main.
  Remaining gates are final current-main re-pin/freeze, push, fresh exact-head
  hosted CI, independent exact-SHA R3 rereview, Sol acceptance, merge and
  post-main verification.
