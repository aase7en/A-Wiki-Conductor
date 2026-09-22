# WO-P1-480 — MSP-0 collision-proof delegated-run artifact identity

Issue: #480
Parent: Issue #475 / `docs/work-orders/WO-P1-475-multi-session-provenance-collision-hardening.md` (MSP-0)
Claim: WO-P1-480-MSP0-WINDOWS-001
Topology: CONTROL_PLANE_ONLY
Risk: R3 (identity/concurrency/authority surface)
Status: IMPLEMENTED + P1 REPAIR (attempt 3) + P2 REPAIR (attempt 4) — focused verification green; left uncommitted for GPT-5.6 Sol harvest
Exact base/head: e6f96e7526742cfaca65917933fc299b21bf439e / repaired from f3d2b412e0106c69456d84a34221d31a4bbeb7c7
Branch: feat/wo-p1-480-msp0-run-artifact-identity
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo480-msp0

## 1. Problem

Logical run identity is already strong (`DELEGATED_RUN_ID` carries a
CSPRNG random component), but physical attempt artifacts used
`attempt-NNNN/`. Independent sessions that admit the same ordinal can
overwrite each other's `task.md`, config, pointer, result, and log
artifacts (MSP-0 gap in WO-P1-475 §3).

## 2. Frozen design decision (this WO is the naming authority)

- New physical attempt directory: `attempt-NNNN-<random-id>` where
  `NNNN` is the DELEGATED_RUN_ID attempt number zero-padded to 4
  digits (extends naturally beyond 9999) and `<random-id>` is exactly
  the exact rightmost lowercase-hex segment of the accepted grammar
  `run:<TASK_ID>:<role>:<ordinal>:a<attempt>:<random-id>`. Historical
  durable runs use 8 hex; current durable dispatch evidence uses 12 hex;
  both are canonical recovery forms and neither is truncated.
- REUSE, not a second namespace: the existing random run suffix IS
  the physical uniqueness component. The ordinal stays
  human-readable and is never uniqueness authority.
- Parse-from-the-right: the four rightmost segments are anchored
  first so left-side content can never spoof the random id.
- Legacy `attempt-NNNN` directories: enumerated, recoverable via
  pointer `delegated_run_id`, never rewritten in place (module has no
  write API at all).
- Enumeration is deterministic: ascending ordinal, legacy before
  suffixed at equal ordinal, then ascending suffix. Non-attempt
  entries are ignored, never guessed into identity.
- Recovery binds each canonical suffixed directory to exactly one
  delegated run via pointer parse + ordinal agreement + exact suffix
  agreement; mismatch, malformed IDs, traversal/separator payloads,
  ambiguous/missing/undecodable pointer fields all fail closed with
  stable code-only errors (no input echo).
- Canonical suffixed names accept both proven durable forms (8-hex historical
  and 12-hex current) and require exact suffix agreement with the pointer.
  Other lowercase-hex suffix lengths stay census-visible and bind pointer-only
  with ordinal agreement.
- Recovery-only legacy alias seam (P1 repair, attempt 3): proven
  pre-grammar pointer values — ordinal segment absent (e.g.
  `run:WO-P1-478:r3-review:a1:2933deb345c2`) or non-decimal token in
  the ordinal position (e.g.
  `run:WO-P1-475:flash-architecture:acfa39d:a1:16b32a2f6ea9`) — are
  accepted ONLY when recovering an existing attempt directory from
  pointer.md / execution-pointer.json. The entire original string is
  preserved verbatim as immutable recovery identity; only the trailing
  `a<attempt>` and 8/12-hex suffix are bound (exact attempt+suffix
  agreement on suffixed directories, attempt agreement on unsuffixed
  legacy ones); missing attempt/suffix is never inferred, the pointer
  is never rewritten, nothing is ever "chosen latest", and minting /
  physical path generation (`attempt_dir_name()`/`attempt_dir_path()`)
  remain strictly canonical. Dual pointer sources must agree on the
  exact full string; all mismatch/ambiguity/malformed values fail
  closed with stable code-only errors and no input echo. The canonical
  parser was NOT broadened.
- `DELEGATED_RUN_ID` remains observation/recovery identity only. No
  DB, registry, session lock, scheduler, task store, claim/lease
  authority, or browser authority is added.

## 3. Mutated scope — exactly

- `src/a_conductor/delegated_run_artifacts.py` (NEW, pure helper)
- `tests/test_delegated_run_artifacts.py` (NEW, RED-first)
- `.agents/skills/a-faster/SKILL.md` (pointer path line)
- `.agents/skills/a-faster/references/durable-lanes.md` (ATTEMPT, §3
  layout, §9 checklist)
- `docs/work-orders/WO-P1-480-msp0-run-artifact-identity.md` (this file)

## 4. RED-first evidence

`tests/test_delegated_run_artifacts.py` was written and executed
before any implementation existed: collection failed with
`ModuleNotFoundError: No module named 'a_conductor.delegated_run_artifacts'`
(RED), after which the module was implemented and the same suite went
green. Proven behaviors: same ordinal / distinct run IDs diverge;
same run ID deterministic; malformed IDs reject; mixed legacy/new
enumeration deterministic (files, malformed names, zero ordinal, and non-dir
entries ignored); legacy `pointer.md` recovery is preserved with zero rewrite;
current `execution-pointer.json` recovery is supported; dual pointer sources
must agree exactly; suffix and ordinal mismatch rejected; non-canonical suffix
recovers pointer-only; missing/ambiguous/malformed/undecodable/absent pointer
fields fail closed; traversal values fail closed; one run maps to exactly one
path (injectivity); no authority
surfaces imported (sqlite/threading/subprocess/asyncio/socket/
acquire/release absent).

## 5. Verification (deterministic, focused)

- Sol post-author repair verification: `python -m pytest
  tests/test_delegated_run_artifacts.py tests/test_work_order_identity.py
  tests/test_zero_relay_author_provenance.py -q` → **142 passed** at
  candidate freeze (pre-repair; superseded by the **190 passed**
  post-P1-repair run in §7). This includes
  historical 8-hex and current 12-hex run suffixes, `attempt-0000` rejection,
  `pointer.md`, `execution-pointer.json`, and dual-pointer disagreement.
- The author pre-repair focused/related suites were green, but their 8-hex-only
  assumption was superseded by actual durable 12-hex runtime evidence before
  candidate freeze.
- `py -3.13 -m py_compile src/a_conductor/delegated_run_artifacts.py`
  → clean.
- `git diff --check` → clean.
- All changes left uncommitted for GPT-5.6 Sol harvest per the task
  packet; no commit/push/merge/branch switch performed.

## 6. Remaining risks / follow-ups

- Adoption is documentation+helper only: dispatch-side writers of
  `runs/` artifacts (A-Faster lanes, packet generators) must start
  calling `attempt_dir_path()`; existing writers still produce
  `attempt-NNNN` names until their own WOs adopt this seam (enumeration
  keeps those recoverable, so no migration cliff).
- Legacy ordinal mismatch (`attempt-0003` holding an `a1` pointer) is
  now a typed error instead of silent data; census consumers must
  treat it as reconcile-required, not skip it.
- The dispatch directory of this very packet
  (`attempt-0001-a096ec5b8e23`, 12-hex) is current durable evidence and is now
  covered by exact canonical suffix binding. Historical 8-hex evidence remains
  equally canonical for recovery, avoiding a migration cliff.
- Pointer field parsing accepts plain/list/bold/backticked
  `delegated_run_id:` lines; pointer writers should keep the plain
  `field: value` shape to stay inside the verified envelope.
- Full-suite regression and independent R3 review remain with the
  integrator harvest gate (delivery gate sequence unchanged).

## 7. P1 repair record (attempt 3, repaired from exact head f3d2b41)

Independent exact-SHA R3 review of f3d2b41 returned CHANGES_REQUIRED
(P0/P1/P2/P3 = 0/1/0/2). Blocking P1: actual pre-MSP0 durable pointers
include structurally non-canonical run IDs that the strict parser
rejected with `RUN_ID_INVALID`, breaking the accepted promise that
legacy attempt directories remain recoverable.

Repair implemented on the same uncommitted candidate (no
commit/push/merge/rebase/branch switch):

- RED first: new regression section in
  `tests/test_delegated_run_artifacts.py` reproducing the exact
  pre-repair failure for all five proven real-world alias shapes on
  `attempt-NNNN` directories → 12 failed / 115 passed at RED (only the
  recovery-gap tests failed; no existing test regressed), including one
  end-to-end test reproducing the exact pre-repair failure on an
  `attempt-0001` directory.
- `src/a_conductor/delegated_run_artifacts.py`: added
  `LegacyPointerRunIdentity` (verbatim original string + attempt +
  trailing suffix only), private `_parse_legacy_pointer_run_id()`
  recovery-only seam (canonical-first; reached only via
  `read_pointer_run_id` from pointer evidence), and widened
  `recover_attempt_run()` binding: legacy aliases must prove exact
  attempt + exact physical suffix agreement on any suffixed directory
  (a non-8/12-hex suffixed directory can never satisfy an 8/12-hex
  alias suffix → fail-closed) and exact attempt agreement on
  unsuffixed legacy directories. Canonical parser, `attempt_dir_name`,
  and `attempt_dir_path` untouched in strictness.
- Tests added: 38 legacy-recovery-seam tests (5 proven alias
  recoveries, end-to-end pre-repair-failure reproduction,
  execution-pointer.json alias recovery, identity-surface pins,
  suffixed-dir exact-agreement binding, non-canonical-suffix
  fail-closed, attempt mismatch, dual-source exact-string agreement
  incl. canonical-vs-legacy same-tail disagreement, decimal-ordinal
  still canonical, 24 malformed near-misses + pointer.md near-miss)
  and 10 canonical-minting strictness guards (5 canonical-parser
  rejections + 5 path-minting rejections of the proven aliases).
- P3 documentation hardening folded into
  `references/durable-lanes.md` + `SKILL.md`: (a) physical injectivity
  assumes CSPRNG random-suffix uniqueness — historical 8-hex has
  residual birthday-bound collision probability and is recovery
  compatibility, not preferred new minting entropy (12-hex current
  form preferred for new minting); (b) the pointer parser intentionally
  treats every `delegated_run_id:`-shaped line in a `pointer.md`
  (fenced included) as evidence, so example-shaped lines can
  intentionally trigger fail-closed ambiguity — live pointers keep
  exactly one plain `field: value` line and examples stay inside
  fenced examples in documentation.

Repair verification (deterministic, focused):

- `python -m pytest tests/test_delegated_run_artifacts.py
  tests/test_work_order_identity.py
  tests/test_zero_relay_author_provenance.py -q` → **190 passed**
  (127 artifact-identity incl. the repair regressions + 63 related).
- `py -3.13 -m py_compile src/a_conductor/delegated_run_artifacts.py`
  → clean.
- `git diff --check` → clean.
- Final tracked dirty paths are exactly the five allowed paths; all
  changes left uncommitted for GPT-5.6 Sol harvest.

## 8. P2 repair record (attempt 4, repaired at exact head ef61fe14)

Independent exact-SHA review of ef61fe14 (full durable-pointer
census) returned CHANGES_REQUIRED (P0/P1/P2/P3 = 0/0/1/2): three
further proven module-reachable recovery values were rejected by the
P1 seam. Blocking P2 evidence (exact values authoritative):

1. `run:WO-P1-449:r3-review:1:a1:1516601fcc` — decimal middle with a
   non-8/12 legacy tail (the packet annotates this tail as "9-hex";
   the exact string is 10 lowercase-hex chars — both inside the
   repaired window);
2. `run:WO-P1-449:r3-rereview-cycle2:1:a1:d2cc2c4` — 7-hex legacy
   recovery tail (a pinned git short-SHA);
3. `run:WO-P1-453:cutover-flash-advisory:20260922:a2:dfe48eaa88fe` —
   numeric legacy date tag `20260922` in the ordinal-position slot
   (canonical parser correctly rejects it as an out-of-range decimal
   ordinal; it must recover only as legacy evidence).

Repair implemented on the same uncommitted candidate (no
commit/push/merge/rebase/reset/stash/clean/branch switch):

- RED first: new P2 regression section in
  `tests/test_delegated_run_artifacts.py` using the three real values
  and real directory shapes (10-hex tail on the matching suffixed
  directory; 7-hex tail on an unsuffixed legacy directory, since a
  7-hex tail can never form a recognizable suffixed name; numeric tag
  via `execution-pointer.json` on its 12-hex suffixed directory) →
  **10 failed / 154 passed at RED** — only recovery-intent tests
  failed (each real value failed with pre-repair `RUN_ID_INVALID`);
  no existing test regressed.
- `src/a_conductor/delegated_run_artifacts.py`: recovery-only
  widening inside `_parse_legacy_pointer_run_id()` only —
  (a) bounded legacy tail family `[0-9a-f]{7,12}` via a new
  `_LEGACY_RECOVERY_RANDOM_ID_RE` (the canonical `_RANDOM_ID_RE`
  stays exactly 8/12-hex); (b) new
  `_legacy_middle_token_ok()` accepting either the P1 non-decimal
  safe token or a bounded numeric legacy tag (digits only, no leading
  zero, at most 8 digits — `_MAX_LEGACY_TAG_LEN`; proven evidence is
  the 8-digit `20260922` date tag and small counters like `1` whose
  id is non-canonical for other reasons) treated as opaque, never
  normalized/reinterpreted as an ordinal. Canonical-first order
  unchanged in `read_pointer_run_id()`; `parse_delegated_run_id()`,
  `attempt_dir_name()`, `attempt_dir_path()`, and
  `parse_attempt_dir_name()` untouched in strictness (no new legacy
  alias gains minting or physical-path authority; directory-name
  grammar unchanged). Exact full-string dual-pointer agreement,
  exact suffix agreement on suffixed directories, attempt agreement
  everywhere, and fail-closed behavior on 6-/13-hex tails, uppercase,
  leading-zero/plus/decimal-point/traversal/separator payloads, and
  six-segment shapes all preserved.
- Tests (reported separately per the repair contract):
  - recovery-only: 3 real-value end-to-end recoveries (verbatim
    string preserved, pointer never rewritten), dual-source
    exact-agreement on a widened value, wrong-attempt/wrong-suffix
    rejection (`ATTEMPT_DIR_NAME_RUN_MISMATCH`), 7-hex-tail
    fail-closed on suffixed directories, full 7..12 window pinning
    (including the former 11-hex P1 near-miss, now in-window by
    contract), 10 numeric-tag near-misses (zero/leading-zero/9-digit/
    plus/decimal-point/traversal/separator/six-segment/leading-zero
    attempt), and canonical-decimal-ordinal-stays-canonical pinning
    the real canonical pointer
    `run:WO-P1-449:r3-rereview-cycle2:1:a1:e7c88021eadd`.
  - canonical-minting strictness guards: the three real values plus
    7-/10-hex tails rejected by `parse_delegated_run_id()`; the three
    real values never mint `attempt_dir_name()`/`attempt_dir_path()`
    paths (`20260922` can never mint a new attempt directory);
    directory-name grammar not widened (7-hex/uppercase dir names
    still unrecognized; 10-hex dir suffix stays non-canonical
    census-visible).
  - supersession: the P1 11-hex near-miss
    (`run:WO-P1-478:r3-review:a1:2933deb345c`) moved from
    near-miss to in-window positive; 6-hex and 13-hex near-misses
    added at the new window boundaries.
- P3 documentation hardening folded into
  `references/durable-lanes.md` + `SKILL.md`: bounded historical
  suffix variants (7..12-hex) are recovery compatibility only and
  12-hex remains the preferred current/new minting form; six-segment
  attempt-postreset evidence stays out-of-contract
  (census/reconcile-only); deterministic/pinned suffixes can repeat
  across attempts, so physical uniqueness may rely on attempt-ordinal
  divergence when the suffix is not random.

P2 repair verification (deterministic, focused):

- `python -m pytest tests/test_delegated_run_artifacts.py
  tests/test_work_order_identity.py
  tests/test_zero_relay_author_provenance.py -q` → **227 passed**
  (164 artifact-identity incl. the P2 repair regressions + 63
  related).
- `py -3.13 -m py_compile src/a_conductor/delegated_run_artifacts.py`
  → clean.
- `git diff --check` → clean.
- Final tracked dirty paths are exactly the five allowed paths; all
  changes left uncommitted for GPT-5.6 Sol harvest.
