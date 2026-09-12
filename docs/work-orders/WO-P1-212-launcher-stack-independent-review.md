# WO-P1-212 — Independent exact-SHA review of launcher forensics stack

Status: PREPARED / WAIT_REVIEW_INVOCATION
Owner: independent GLM-5.3 / ZCode reviewer only
Integrator: GPT-5.6 Sol
Parent source stack:
- PR #266 / WO-P1-194 / `8339e4c9e15c8eefd94693245ef9ef4b627c00de`
- PR #285 / WO-P1-207 / `f7d23c96690f7cdb94d2ebe62cac6d4669ad6f00`
Review branch: `review/wo-p1-212-launcher-stack`
Packet base: `02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971`
Risk: R3 source acceptance review; no live deployment authority

## 1. Purpose

Independently review the combined launcher hardening tree authored by GPT before any merge or live Worker rematerialization.

The accepted unit is exact child SHA:

`f7d23c96690f7cdb94d2ebe62cac6d4669ad6f00`

which contains:

1. WO194 legacy launcher forensics hardening;
2. WO207 structural idempotency-marker repair.

The reviewer must try to falsify both behaviors and their composition without editing candidate source.

## 2. Why independent review is required

GPT authored both the source repair and the child marker-guard repair. GPT self-tests/CI cannot serve as final independent acceptance.

Known historical findings:

- live Worker launchers use `$RuntimeProcess.WaitForExit()` inside `try/finally`, while older source hardening initially only recognized `Wait-Process -Id ...`;
- old runtime stdout evidence was overwritten/truncated on restart, and exit code could be blank;
- WO194 added archive-before-run, WaitForExit→Refresh→stable exit-code capture, and numeric lifecycle logging while preserving credential/preflight/finally content;
- later adversarial review found an early idempotency substring guard could be fooled by a harmless comment containing `runtime-archive`, leaving the stale legacy exit branch unchanged;
- WO207 replaced that broad substring guard with structural marker recognition and explicit partial-migration fail-unchanged behavior.

## 3. Immutable target

Before substantive review verify exactly:

- PR #266 head remains `8339e4c9e15c8eefd94693245ef9ef4b627c00de`;
- PR #285 base remains `fix/wo-p1-194-legacy-launcher-forensics`;
- PR #285 head remains `f7d23c96690f7cdb94d2ebe62cac6d4669ad6f00`;
- child history contains the exact parent;
- hosted CI for both exact source heads is terminal SUCCESS;
- no source drift occurred after the hashes above.

If not, return `SOURCE_DRIFT` / `BLOCKED` and stop.

## 4. Writable scope

Reviewer may write only review evidence on this review branch:

- `docs/reviews/WO-P1-212-launcher-stack-review.md`
- `runs/WO-P1-212/**` as allowed ignored evidence
- append-only review checkpoint in this WO if necessary

Candidate source/tests are READ-ONLY:

- `src/a_conductor/instance_create.py`
- `tests/test_instance_create.py`
- PR #266/#285 branches

Do not merge, rebase, cherry-pick, amend, reset, clean, force-push or deploy candidate source.

## 5. Architecture being reviewed

Function under review:

`_harden_start_script_runtime_forensics(text: str) -> str`

Required high-level semantics:

1. recognize only accepted legacy launcher terminal seams;
2. preserve unrelated credential/project/doctor/environment/preflight logic;
3. preserve indentation / surrounding `try/finally` structure;
4. archive prior stdout/stderr before the new runtime can truncate them;
5. wait for exact process exit;
6. Refresh process state;
7. capture numeric `$RuntimeExitCode` once;
8. log STOPPED/TUNNEL_START_FAILED with stable numeric exit code;
9. exit with the captured code;
10. apply idempotently;
11. unknown/ambiguous/partial structural launchers fail unchanged rather than broad regex-rewrite;
12. comments/free text containing marker words must not fake hardened state.

This is source generation/materialization behavior only. It does not authorize writing any existing live `start.ps1` or restarting Worker processes.

## 6. Required review questions

### A. Stack identity

- exact parent/child/base verified;
- child diff contains only intended marker guard + tests/work-order relative to parent;
- no unrelated source hidden in child;
- exact CI success exists for both SHAs.

### B. Legacy seam recognition

Review both supported forms:

1. legacy `Wait-Process -Id $RuntimeProcess.Id`;
2. actual live-shaped `$RuntimeProcess.WaitForExit()` followed by the old direct ExitCode failure block inside `try/finally`.

Try variants with:

- CRLF and LF where supported by contract;
- indentation changes within accepted shape;
- additional unrelated lines before/after terminal seam;
- duplicate terminal waits;
- incomplete wait/failure block;
- method-wait without expected stale direct branch;
- multiple stdout/stderr/STARTING assignments;
- reordered markers.

Unknown/ambiguous variants must not receive a partial rewrite.

### C. Credential/preflight preservation

Prove hardening does not alter or reorder unrelated sentinels representing:

- DPAPI/credential load;
- tunnel validation;
- project validation;
- doctor/preflight checks;
- environment setup;
- finally cleanup including API key / SERENA_HOME nulling.

Do not use real secrets.

Look for regex spans that could consume adjacent `finally`, doctor or credential content.

### D. Runtime log forensics

Verify:

- existing stdout and stderr are moved before next run;
- archive target is bounded under `$LogsDir/runtime-archive`;
- archival names avoid same-run stdout/stderr aliasing;
- hardening is idempotent and does not duplicate archive blocks;
- old live output evidence is preserved before the next runtime process starts;
- successful exit logs `STOPPED ... exit_code=0`;
- failure logs numeric `exit_code=N`;
- stable exit code is captured only after WaitForExit + Refresh;
- old direct `$RuntimeProcess.ExitCode` terminal decision is removed on a successfully hardened method-wait launcher.

### E. Structural idempotency-marker guard

Independently attack WO207.

Current intended policy:

- all complete structural hardening markers -> byte-identical return;
- genuine partial structural migration marker -> fail unchanged;
- comment/free prose `runtime-archive` -> still harden legacy launcher;
- generic presence of `$RuntimeProcess.ExitCode` in legacy code is NOT evidence of complete hardening.

Try at least:

- comment with `runtime-archive`;
- quoted string with `runtime-archive`;
- unrelated variable containing marker text;
- exact archive assignment only;
- exact exit-capture assignment only;
- Refresh only;
- exit command only;
- archive + refresh but no captured exit var;
- captured exit var + exit command but no archive;
- complete hardened output with extra comments;
- structural marker with double quotes instead of single quotes;
- different but semantically similar whitespace;
- marker text inside a comment before `$`;
- duplicate complete marker lines.

Classify whether each should harden, stay byte-identical, or fail unchanged. Look especially for a false "complete" classification that could preserve unsafe stale terminal behavior.

### F. Idempotency / partial migration

Prove:

- `harden(harden(legacy)) == harden(legacy)` for both supported legacy variants;
- already-complete generated output is byte-identical;
- partial structural migration does not receive a second partial rewrite;
- a harmless comment/noise marker cannot suppress needed hardening;
- repeated calls cannot duplicate archive/Refresh/exit blocks.

### G. Live-shape read-only verification

If the current Windows Worker launchers are safely readable and ownership policy permits read-only inspection:

- read actual Worker 1–5 `start.ps1` bytes only;
- do not write/rematerialize them;
- run hardener in memory;
- report whether each is recognized and whether expected archive/Refresh/exit capture/stale-branch removal would occur;
- do not expose credentials/secrets or full launcher contents in result.

If live files are unavailable, state `LIVE_SHAPE_NOT_RECHECKED`; do not fabricate proof.

### H. No deployment authority

Confirm candidate source cannot mutate live Worker launchers merely by being merged.

Any rematerialization/restart remains under WO192 operational gates:

- exact Worker task/claim state;
- process identity;
- dirty/ownership scope;
- W2 protected lane status;
- explicit deployment authorization.

Reviewer must not deploy.

## 7. Mandatory novel counterexample

Attempt at least one adversarial case not already in candidate tests.

Good targets include:

- structural markers using alternate quoting;
- partial marker combinations not pinned by authored tests;
- CRLF edge behavior;
- misleading marker-like code outside the terminal seam;
- marker duplicates;
- complete-looking marker set attached to an otherwise stale/ambiguous terminal block.

Do not add the counterexample to candidate tests. Record result as review evidence.

## 8. Verification floor

Run exact child tree tests at minimum:

```text
python -m pytest -q tests/test_instance_create.py
python -m pytest -q tests/test_setup_wizard.py tests/test_ps1_encoding_and_quoting.py tests/test_doctor_fixes.py
python -m compileall -q src/a_conductor/instance_create.py
git diff --check 8339e4c9e15c8eefd94693245ef9ef4b627c00de..f7d23c96690f7cdb94d2ebe62cac6d4669ad6f00
```

Add deterministic string-only adversarial scripts/tests in owned review evidence or ephemeral temp files. Do not modify candidate tests.

Run strict UTF-8/no-U+FFFD and changed-scope audit on reviewed delta.

## 9. Severity

- P0/P1/P2 -> `CHANGES_REQUIRED`.
- P3 only -> may PASS with advisory.
- source/CI drift -> `SOURCE_DRIFT` / `BLOCKED`.
- inability to safely inspect live launcher is not by itself source failure; record evidence gap.
- do not label synthetic string edge as production incident unless reachable live shape/contract makes it relevant.

## 10. Required result

Write `docs/reviews/WO-P1-212-launcher-stack-review.md` with:

- exact parent/child SHA;
- PR base/head/CI evidence;
- commands/results;
- A–H answers;
- novel counterexample(s);
- findings P0/P1/P2/P3;
- live-shape check status;
- verdict exactly one of `PASS`, `CHANGES_REQUIRED`, `BLOCKED`, `SOURCE_DRIFT`;
- `merge_performed=false`;
- next safe action.

Commit/push only review evidence on this review branch, then STOP at GPT/integrator acceptance gate.

## 11. Acceptance boundary

WO212 may recommend a verdict only. It does not merge #266/#285 and does not authorize live Worker rollout.

If PASS is later accepted by GPT/integrator, the stack still needs safe fresh-main integration/provenance checks because the parent source branch is based on old main, followed by WO192 deployment gates.