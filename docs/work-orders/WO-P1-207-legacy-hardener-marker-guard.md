# WO-P1-207 — Legacy launcher hardener structural idempotency guard repair

Status: CANDIDATE_PREPARATION
Owner: GPT-5.6 Sol bounded repair lane
Parent: WO-P1-194 / PR #266
Parent candidate: `8339e4c9e15c8eefd94693245ef9ef4b627c00de`
Branch: `fix/wo-p1-207-legacy-marker-guard`
Risk: R2 launcher transformation correctness / false idempotency detection

## Defect

Independent self-audit of PR #266 found the early idempotency shortcut:

```python
if "runtime-archive" in text and "$RuntimeProcess.ExitCode" in text:
    return text
```

The legacy method-wait launcher already contains `$RuntimeProcess.ExitCode`. Therefore an unrelated comment or note containing the text `runtime-archive` can cause the transformer to return the legacy launcher unchanged while its stale direct-exit branch remains.

Deterministic reproducer before repair:

```text
UNCHANGED=True
HAS_REFRESH=False
HAS_OLD_EXIT=True
```

Focused RED:

`test_runtime_archive_word_in_comment_does_not_fake_hardened_state` failed because `hardened == source`.

This does not describe the exact current W1-W5 live launcher shape, but it violates the WO194 review question "Can a launcher be partially rewritten if only one marker exists?" and makes idempotency recognition depend on broad substring coincidence.

## Repair policy

Use structural line markers instead of broad substring presence.

Recognize complete hardening only when all accepted structural markers are present as executable lines:

- `$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'`
- `$RuntimeProcess.Refresh()`
- `$RuntimeExitCode = $RuntimeProcess.ExitCode`
- `exit $RuntimeExitCode`

If complete: return byte-identically unchanged.

If a strong partial structural migration marker is present (`$RuntimeArchiveDir ...` or `$RuntimeExitCode = ...`) but the complete set is not present: fail unchanged rather than risk duplicating or partially re-hardening a manually migrated launcher.

A mere comment/free-text occurrence of `runtime-archive` is not structural authority and must not suppress hardening.

## Mutable scope

- `src/a_conductor/instance_create.py`
- `tests/test_instance_create.py`
- this WO

No live launcher/process/runtime mutation.

## RED/GREEN evidence

RED before repair:

```text
1 failed, 1 passed
```

Failure:

`test_runtime_archive_word_in_comment_does_not_fake_hardened_state`

GREEN after repair:

```text
9 passed, 17 deselected
```

Focused coverage includes:
- comment collision;
- partial structural marker fail-unchanged;
- live method-wait hardening;
- legacy Wait-Process hardening;
- idempotency;
- already-hardened byte identity;
- stale direct-exit removal.

Related regression:

```text
63 passed, 1 Tk/display-environment skip
```

across:
- `tests/test_instance_create.py`
- `tests/test_setup_wizard.py`
- `tests/test_ps1_encoding_and_quoting.py`
- `tests/test_doctor_fixes.py`

`python -m compileall -q src/a_conductor/instance_create.py` PASS.
`git diff --check` PASS.

## Acceptance boundary

This repair does not authorize deployment/rematerialization of live Worker launchers.

After candidate freeze/push, require hosted CI plus independent exact-SHA review before folding into PR #266 or main.
