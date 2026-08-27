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
