# WO-P1-480 — MSP-0 collision-proof delegated-run artifact identity

Issue: #480
Parent: Issue #475 / `docs/work-orders/WO-P1-475-multi-session-provenance-collision-hardening.md` (MSP-0)
Claim: WO-P1-480-MSP0-WINDOWS-001
Topology: CONTROL_PLANE_ONLY
Risk: R3 (identity/concurrency/authority surface)
Status: IMPLEMENTED — focused verification green; left uncommitted for GPT-5.6 Sol harvest
Exact base/head: e6f96e7526742cfaca65917933fc299b21bf439e
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
  tests/test_zero_relay_author_provenance.py -q` → **142 passed**. This includes
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
