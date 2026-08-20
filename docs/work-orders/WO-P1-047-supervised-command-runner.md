# WO-P1-047: Supervised Command Runner — Wire AC-RES Supervisor into Native Operations

Status: complete
Lane/files: `src/a_conductor/supervised_command_runner.py`, `src/a_conductor/native_operation_assembly.py`, `src/a_conductor/__init__.py`, `tests/test_supervised_command_runner.py`, `docs/work-orders/WO-P1-047-supervised-command-runner.md`, `CURRENT-WORK.md`, `handoff.md`
Branch: chunk/p1-047-supervised-job-backend (PR)
Model tier: high

## Goal

Route native git/verification commands through the resilient supervisor (AC-RES-001..008) so operator jobs gain durable execution records, duplicate-execution protection, and bounded collection — by implementing the existing `NativeCommandRunner` protocol with a supervised runner, and extending `ControlCenterNativeAdapterResolver` with an injectable `runner_factory` (opt-in; default behavior unchanged).

## Reuse classification

`WRAP + EXTEND`: adapters already accept an injectable `NativeCommandRunner` — no adapter changes needed. Supervisor, dedup guard, execution store, and result mapping reuse AC-RES primitives unchanged. The resolver gains one optional factory parameter. No retry/failover/reconnect logic is added.

## Design decisions

- `SupervisedCommandRunner.run(spec)` validates exactly like `NativeSubprocessRunner` (argv, mutation gate, executable allowlist, timeout bound, cwd resolution), then: fingerprint → duplicate assessment → launch-or-attach → bounded poll of `inspect()` → `collect()` → map to `NativeCommandResult`.
- Duplicate decisions: `SAFE_TO_LAUNCH` → create record + supervised launch; `ATTACH_RUNNING`/`REUSE_COMPLETED` → wait on the existing execution (no second launch); `BLOCKED_UNKNOWN` → failure result with `SUPERVISED_DUPLICATE_BLOCKED`.
- Budget exhaustion while running → `timed_out=True` result; the durable execution stays `RUNNING` for later reconciliation (TRANSPORT != EXECUTION; no automatic retry).
- v1 constraint: `spec.cwd` must resolve to the scope root (all current adapter commands use `cwd="."`); anything else raises `CWD_UNSUPPORTED` rather than guessing.
- Failure results carry supervisor error codes in `stderr` (e.g. `SUPERVISED_LAUNCH_FAILED:SUPERVISOR_START_EXCEPTION`); exit code `None`, never a fabricated success.
- Output mapping reads durable stdout/stderr artifacts under the run directory with the scope's byte cap, full SHA-256, and tail-truncation flags.

## Acceptance

- Real end-to-end (nt): fast command → exit 0, stdout captured, durable artifacts + execution record `VERIFICATION_REQUIRED`.
- Nonzero exit maps to failure with the real exit code; record `FAILED`.
- Timeout while running → `timed_out=True`, record stays `RUNNING`, and a same-fingerprint retry attaches to the original and collects its result without a second execution record.
- `BLOCKED_UNKNOWN` duplicate → failure result, no launch.
- Mutation/allowlist/timeout/cwd validation still enforced before any launch.
- Resolver `runner_factory` injects the supervised runner into both adapter families; default factories unchanged.
- Full suite + CI pass.

## Forbidden

- No automatic retry, failover, or transport reconnect decisions.
- No real Serena/tunnel interaction; test targets are real short-lived Python child processes only.
- No change to job-state machine or coordinator semantics.

## Checkpoint log

- [2026-08-20] Opened after PR#1 (packaging) and PR#2 (CI) merged; design grounded in existing injection points (`NativeCommandRunner` protocol, adapter `runner` param, resolver factories).
- [2026-08-20] Bugfix loop round 1: wrong import location (`NativeCommandRunner` lives in `native_adapters`, not `native_execution`).
- [2026-08-20] Bugfix loop round 2 — **real upstream race found and fixed**: `SupervisedExecutionService.inspect()` checked `result.json` only once at entry; with the slow PowerShell pid observation, a helper that wrote its result and exited mid-observation was misclassified `SUPERVISOR_EXITED_RESULT_MISSING`. Fix: re-check result existence before every non-healthy conclusion (result file is authoritative over stale-pid facts). Deterministic regression test added (`test_inspect_prefers_result_written_while_supervisor_was_exiting`, RED→GREEN).
- [2026-08-20] Closed.

## Completion evidence

- 6 new runner tests pass: real end-to-end fast command (exit 0, stdout captured, record `VERIFICATION_REQUIRED`, durable artifacts under `runs/<execution_id>/`), nonzero exit 7 → `FAILED`, timeout → `timed_out=True` with record left `RUNNING` then same-fingerprint retry attaches and collects exit 0 with exactly one execution record, `BLOCKED_UNKNOWN` duplicate → `SUPERVISED_DUPLICATE_BLOCKED` without launch, mutation/allowlist/timeout/cwd validation gates, resolver `runner_factory` injection.
- Race regression test (deterministic fake observer) passes; fix is behavior-additive (wrong conclusions become correct ones only when a result file exists).
- Full suite 749 passed, 0 skipped, exit 0; compileall PASS.
- Test targets are real short-lived Python child processes only; no Serena/tunnel interaction; temp stores/repos only.
