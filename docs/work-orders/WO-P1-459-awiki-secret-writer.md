# WO-P1-459 — Bounded A-Wiki secret writer (GLM-5.3 MAX author, run r2)

Issue: #459
Parent: Browser Wake / BWA-1B2
Claim: WO-P1-459-AWIKI-SECRET-WRITER-WINDOWS-002
Topology: CONTROL_PLANE_ONLY
Risk class: R3 credential/filesystem trust boundary
Repo: A-Wiki-Conductor
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo459-awiki-secret-writer-r2`
Branch: `feat/wo-p1-459-awiki-secret-writer-r2`
Dispatch base/head expected: `a37746f67631c9ed8edd23fa20b80b8ef4d3dfd9`
Status: REPAIR-CYCLE-1-COMPLETE (rollback mode-restoration repair + WO461
dependency truth applied; candidate awaiting integrator adjudication/fan-in/
freeze; not merged; freeze/acceptance blocked on WO461 post-main repair)

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
- At repair-cycle-1 time PR #466 is still awaiting/under exact-SHA
  independent rereview and merge/post-main verification.

Consequence: final WO459 freeze/acceptance remains **blocked** until the
accepted WO461 repair (PR #466 or its accepted successor) is merged and
post-main verified on the exact expected head. Only then may current main be
fanned into this lane (rebase or re-dispatch decision is integrator
authority), and the affected verification block above rerun against the
fanned-in state before any freeze.

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
  **82 passed, 1 skipped** (skip = POSIX-only mode test on Windows);
  was 80 passed + 1 skipped at author time, +2 for the new regressions
- `python -m pytest tests/test_awiki_environment_resolver.py
  tests/test_provider_configuration.py tests/test_provider_runtime_assembly.py
  tests/test_desktop_control.py tests/test_work_order_identity.py -q` —
  **117 passed**
- `python -m py_compile src/a_conductor/awiki_secret_writer.py` — OK
- `git diff --check` — clean
- Final status remains exactly the three allowed paths; added-line
  secret-shape scan shows only synthetic canaries/vocabulary

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
- Repair-cycle-1 output is a claim; integrator adjudication/fan-in/freeze
  pending, and additionally blocked until the accepted WO461 post-main repair
  (PR #466 candidate `44f1f3d`) is merged and post-main verified, after which
  this lane must re-run its verification against the fanned-in main.
