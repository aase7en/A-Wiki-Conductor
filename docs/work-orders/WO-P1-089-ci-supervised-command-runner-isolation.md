# WO-P1-089 — Windows CI supervised-command isolation

Status: ACTIVE / CI REPAIR
Owner: GPT-5.6 Sol via Remote Desktop Commander
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-ci-supervised-isolation`
Branch: `fix/ci-supervised-command-runner-isolation`
Base: `origin/main@6487cb2b796bbd4351cf8c65ce9c6e90de8d96f3`

## Goal

Repair the recurring Windows hosted-runner `0x80000003` GC/faulthandler failure without weakening or skipping the affected supervised-command tests.

## Evidence / classification

- `origin/main@6487cb2` CI run `33124831162` failed in the core suite while executing `test_supervised_command_runner.py::test_timeout_leaves_durable_running_execution_then_retry_attaches`.
- PR #111 CI run `33124917942` failed at the same supervised-command scenario.
- macOS and Ubuntu smoke jobs passed.
- `DEFECT_LESSONS.md` #11 records this hosted-Windows failure class and prescribes separating subprocess-heavy suites into their own pytest process after confirming it is not a product assertion failure.

Classification: `CI/ENVIRONMENT FAILURE`, recurring hosted-runner process-isolation defect.
## Repository / ownership gate

`SAFE_TO_MUTATE = YES` only for:
- `.github/workflows/ci.yml`;
- `tests/test_supervised_command_runner.py` timeout/retry fixture only;
- this work order.

No open protected branch inspected (`#104`, `#108`, North Star, `#111`, `#112`) changes `.github/workflows/ci.yml`.

## Repair

Run `tests/test_supervised_command_runner.py` in its own Windows CI step, then exclude that file from the remaining core-suite pytest process. The test remains required; this changes process isolation only.

## Acceptance / verification

- standalone supervised-command suite passes;
- remaining core suite still runs with only explicitly separated files ignored;
- no test is deleted, skipped, or assertion-weakened;
- `git diff --check` passes;
- PR CI Windows reaches packaging/smoke after the test steps;
- Ubuntu/macOS smoke remains green.

## Stop condition

Merge only after the actual remote diff is audited and the exact PR head has green required CI. Then re-run/reconcile blocked Agent Harness PRs against repaired `main`.

## Checkpoint — local repair verification

- standalone `tests/test_supervised_command_runner.py`: **6 passed in 5.08s** with an isolated `--basetemp`;
- no open protected branch inspected touches the CI workflow or this work-order path;
- `git diff --check`: PASS;
- changed scope is exactly CI workflow + this work order;
- a long local remaining-core run outlived the transport call and later exited; its exit code was not recoverable, so it is not counted as PASS evidence and was not blindly retried.

Next safe action: commit/push, open a Draft PR, inspect the remote diff, and require GitHub Windows CI to prove the isolated step plus remaining core suite and packaging path.

## Checkpoint - PR #113 CI exposed a real timing assumption

- First PR CI no longer crashed with `0x80000003`; the isolated suite produced a normal assertion failure instead.
- Failure: the fixed two-second child completed before polling began on a slow hosted runner, so `timeout_seconds=1` returned a completed result rather than `timed_out=True`.
- Root cause is the test fixture's wall-clock race, not timeout/attach product behavior.
- Repair: hold the child on an explicit sentinel file; first call must time out while the child is provably still running, then the test releases the same child before the retry/attach call.
- No assertion or production behavior is weakened.

Next safe action: prove RED/old failure rationale by inspection, run the repaired test repeatedly plus related supervised suites, then push the exact repair and let PR CI verify on hosted Windows.

## Checkpoint - deterministic timeout fixture verified

- repaired timeout/retry scenario: 5 consecutive isolated runs passed (2.12-2.48s each);
- full `tests/test_supervised_command_runner.py`: **6 passed in 3.63s**;
- child remains live until an explicit sentinel is written, removing the fixed two-second startup race;
- production source remains unchanged.

Next safe action: commit/push the fixture repair and require PR #113 hosted-Windows CI to pass the standalone suite, remaining core suite, packaging and smoke gates.
