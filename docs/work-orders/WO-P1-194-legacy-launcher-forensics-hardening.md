# WO-P1-194 — Legacy method-wait launcher forensics hardening

Status: IMPLEMENTED / READY_TO_FREEZE_FOR_INDEPENDENT_REVIEW
Date: 2026-09-11 (Asia/Bangkok)
Risk: R3 — launcher materialization / credential-bound runtime boundary
Parent: WO-P1-192 Windows Worker runtime self-heal deployment
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo194-legacy-launcher`
Branch: `fix/wo-p1-194-legacy-launcher-forensics`
Base: `origin/main@46f90b329d4991211f5c8a26406f3aca2162e9a7`
Implementation author: GPT-5.6 Sol bounded repair lane
Independent exact-SHA reviewer: GLM-5.3 MAX / ZCode
Architecture / merge / release authority: GPT-5.6 Sol integrator after independent review + hosted CI
Result destination: `runs/WO-P1-194/result.md`

## Goal

Repair the smallest proven source gap that prevents existing Sunday Worker launchers from receiving the accepted runtime-forensics hardening.

Current source helper:

`src/a_conductor/instance_create.py::_harden_start_script_runtime_forensics`

currently recognizes a legacy shape only when the text contains:

`Wait-Process -Id $RuntimeProcess.Id`

All five live Sunday Worker launchers on `DESKTOP-7IB57R4` instead use:

`$RuntimeProcess.WaitForExit()`

but still lack:

- `runtime-archive` log preservation;
- immediate `$RuntimeProcess.Refresh()` after wait;
- stable `$RuntimeExitCode` capture;
- numeric `exit_code=` lifecycle logging.

A pure current-main reproducer using the live method-wait shape returned:

- `UNCHANGED=True`
- `HAS_ARCHIVE=False`
- `HAS_REFRESH=False`
- `HAS_EXIT_VAR=False`

This WO repairs source generation/materialization behavior only. It does not deploy or mutate any live Worker.

## Reuse / authority boundary

REUSE:

- existing `_harden_start_script_runtime_forensics()`;
- existing `create_instance()` materialization path;
- current credential/preflight logic copied from a validated reference launcher;
- existing source tests in `tests/test_instance_create.py`;
- WO156 central recovery authority and WO192 operational deployment gates.

DO NOT create:

- a second watchdog/restart loop;
- a second recovery authority;
- a second launcher format;
- any new credential store;
- any live runtime mutation path.

The helper must continue to upgrade validated legacy text rather than replace unrelated credential, project, tunnel, doctor/preflight, or environment logic.

## Mutable scope

Initial mutable source scope is exactly:

- `src/a_conductor/instance_create.py`
- `tests/test_instance_create.py`
- this WO checkpoint/result metadata if needed

Prompt/task docs are owned by the integrator activation commit.

Any need to edit another source/test file is `SCOPE_EXPANSION_REQUIRED`: stop source mutation, record evidence, and request GPT integrator adjudication.

## Forbidden scope

- `C:\AI\serena-instances\**`
- live Worker processes / PIDs / ports
- `%LOCALAPPDATA%\A-Conductor\control-center.sqlite`
- tunnel IDs, API keys, DPAPI credential files
- setup wizard or installer code unless a deterministic failing test proves this exact source repair cannot be expressed in the initial scope
- `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`
- ZRA-3 / WO191 files
- ZRA-4 files
- merge/release

## Required RED-first matrix

Before implementation, add tests using representative launcher strings.

### RED-1 — live method-wait variant is hardened

Input contains at minimum:

- `$RuntimeStdout`
- `$RuntimeStderr`
- `Write-Log "STARTING:` marker
- realistic preflight/doctor content or stable sentinel text
- `Start-Process ... -PassThru`
- `$RuntimeProcess.WaitForExit()`
- old direct `$RuntimeProcess.ExitCode` failure handling

Expected hardened output contains exactly one coherent runtime-forensics path:

- `$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'`
- archive directory creation
- timestamped move of existing stdout/stderr before next run
- `$RuntimeProcess.WaitForExit()`
- `$RuntimeProcess.Refresh()` immediately after terminal wait
- `$RuntimeExitCode = $RuntimeProcess.ExitCode`
- normal exit log with `exit_code=0`
- failure log containing numeric `exit_code={0}`
- `exit $RuntimeExitCode`

Current source must fail this test before repair.

### RED-2 — existing Wait-Process variant remains supported

Existing accepted legacy `Wait-Process -Id $RuntimeProcess.Id` input must still harden correctly. Do not regress the already-tested path.

### RED-3 — hardening is idempotent

Apply helper twice to each supported legacy variant.

`harden(harden(text)) == harden(text)` byte-for-byte.

No duplicate archive blocks, waits, refreshes, exit captures, or logs.

### RED-4 — already-hardened launcher stays byte-identical

Input that already includes `runtime-archive` and `$RuntimeExitCode` must be returned unchanged.

### RED-5 — credential/preflight content is preserved

Include sentinel lines representing:

- DPAPI read/decrypt boundary;
- tunnel ID validation;
- project-path validation;
- doctor/preflight invocation;
- environment setup/cleanup.

Assert those sentinel bytes/order remain present and unchanged after hardening except only the narrow runtime-forensics seam.

Do not use real credentials or secret values.

### RED-6 — malformed/unknown launcher fails safe

Inputs missing required stdout/stderr or recognized terminal-wait seams must return unchanged rather than partially rewriting a launcher into an unsafe state.

### RED-7 — no stale direct-exit branch remains

For a successfully hardened method-wait variant, prove there is exactly one terminal decision path and no second old direct `$RuntimeProcess.ExitCode` branch that could bypass the stable captured exit code.

## Implementation constraints

Prefer the smallest change to `_harden_start_script_runtime_forensics()`.

Recommended shape:

1. recognize either accepted wait seam:
   - `Wait-Process -Id $RuntimeProcess.Id`, or
   - `$RuntimeProcess.WaitForExit()` with a safely identifiable legacy post-wait exit block;
2. preserve the existing early idempotency check;
3. add the archive block only once;
4. replace only the terminal wait/exit handling seam;
5. preserve all text outside the bounded seam;
6. fail unchanged if the method-wait variant is ambiguous rather than regex-rewriting broadly.

Do not refactor unrelated instance creation code merely for style.

## Verification ladder

Required before freezing candidate:

1. RED evidence for new method-wait tests before source repair;
2. focused GREEN:
   `python -m pytest -q tests/test_instance_create.py`
3. related generation/materialization tests as applicable, at minimum:
   - `tests/test_setup_wizard.py` read-only regression if the generated contract overlaps;
   - `tests/test_ps1_encoding_and_quoting.py`;
   - `tests/test_doctor_fixes.py`;
4. `python -m compileall -q src/a_conductor`;
5. `git diff --check`;
6. strict UTF-8 / no U+FFFD;
7. changed-scope audit;
8. added-line credential-pattern scan;
9. candidate commit + push;
10. independent GPT-5.6 Sol exact-SHA review before merge.

Hosted CI is required for final acceptance because this is Windows launcher generation logic.

## Adversarial review questions

Independent review must answer:

- Can a launcher be partially rewritten if only one marker exists?
- Can a second run duplicate archival or exit logic?
- Does the regex overmatch doctor/preflight or `finally` cleanup?
- Is exit code read only after `WaitForExit()` + `Refresh()`?
- Is numeric exit code preserved even if stdout/stderr are empty?
- Are old runtime logs archived before they can be deleted/overwritten?
- Does any change expose credential content in logs?
- Does the implementation change live runtime behavior without explicit rematerialization/deployment?

## Acceptance

WO194 source is accepted only when:

- the exact live method-wait launcher shape is covered by deterministic RED→GREEN regression;
- current Wait-Process coverage remains green;
- supported variants harden idempotently;
- ambiguous inputs stay unchanged;
- credential/preflight sentinel content is preserved;
- exact changed scope is bounded;
- independent exact-SHA review has no blocking P0/P1 findings;
- required CI passes.

Acceptance of WO194 does **not** authorize editing/rerunning the five live launchers. Operational deployment remains WO192 and still requires Worker task/claim/process safety gates.

## 2026-09-11 implementation checkpoint

Actual bounded implementation was performed by GPT-5.6 Sol after WO192 proved that all five live Sunday Worker launchers use the indented `$RuntimeProcess.WaitForExit()` inside `try/finally`, while current main only hardened the older `Wait-Process -Id $RuntimeProcess.Id` shape.

RED evidence before the final repair shape:

- initial focused matrix: `3 failed, 8 passed`; all failures were the method-wait gap;
- after the first narrow repair, a live-shape `try/finally` fixture intentionally re-opened the defect and again produced `3 failed, 8 passed`, proving the first regex was too narrow;
- no live launcher was modified during either reproducer.

Final implementation:

- recognizes exactly one accepted terminal seam: legacy `Wait-Process` or the live method-wait + direct-exit block;
- requires exactly one stdout assignment, stderr assignment and STARTING marker before mutation;
- preserves indentation and the surrounding `try/finally` cleanup;
- archives prior runtime stdout/stderr before a new run;
- performs `WaitForExit()` then `Refresh()` then captures `$RuntimeExitCode` once;
- replaces the stale direct terminal exit branch with stable numeric lifecycle logging;
- returns ambiguous/incomplete launchers unchanged;
- remains byte-idempotent after hardening.

GREEN evidence:

- adversarial focused matrix: `12 passed` after adding duplicate-terminal ambiguity coverage;
- integration + related regression ladder: `61 passed` across `test_instance_create.py`, `test_setup_wizard.py`, `test_ps1_encoding_and_quoting.py`, and `test_doctor_fixes.py`;
- in-memory proof against the actual Worker 1-5 `start.ps1` files: all five report `changed=True`, `archive=True`, `refresh=True`, `exitvar=True`, `stale_direct=False`; no live file was written;
- `python -m compileall -q src/a_conductor` PASS;
- `git diff --check` PASS;
- strict UTF-8 / no U+FFFD PASS;
- changed source/test scope remains the two declared files plus this WO/review packet metadata;
- added-line credential scan found only deliberate `$null` cleanup sentinels, no credential values;
- existing Pyright findings in `_shared_paths` are pre-existing and outside this diff.

Candidate exact SHA is bound in the PR/Issue checkpoint immediately after commit/push. The implementation author must not perform the independent acceptance review.

## Result contract

Write `runs/WO-P1-194/result.md` containing:

- baseline SHA;
- final candidate SHA;
- exact changed files;
- RED command/result;
- GREEN/related test commands/results;
- concise implementation explanation;
- idempotency evidence;
- credential/preflight preservation evidence;
- encoding/diff/secret/scope checks;
- CI status if available;
- unresolved findings;
- `READY_FOR_GPT_REVIEW` or typed blocker;
- exact next safe action.

Do not self-merge or self-accept.
