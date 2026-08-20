# WO-P1-049: Supervised Assembly Switch (Clear Leftover Decision)

Status: complete
Lane/files: `src/a_conductor/supervised_command_runner.py`, `src/a_conductor/job_control.py`, `src/a_conductor/__init__.py`, `tests/test_job_control.py`, `docs/work-orders/WO-P1-049-supervised-assembly-switch.md`, `CURRENT-WORK.md`, `handoff.md`
Branch: chunk/p1-049-supervised-default (PR)
Model tier: high

## Goal

Clear the leftover decision recorded after AC-RES-008 ("switch production resolver assembly to supervised runners by default") by providing the tested enabling path instead of an improvised default flip.

## Reuse classification

`WRAP`: composes `SupervisedCommandRunner` + real Windows supervised service + `ControlCenterNativeAdapterResolver(runner_factory=...)` (the opt-in injection added in WO-P1-047).

## Design decision

`DurableJobControlService.open(..., supervised=True)` assembles the resilient path via `build_supervised_native_adapter_resolver` (execution store + real controller/observer + runner factory). **Default stays `False`**: the resolver builds per-worker runners while fingerprint identity (job/work-order) is per-execution; a static identity is used for now (dedup stays correct per repo+argv — the operation-level duplicate dimension), and flipping the default is an explicit user deployment choice once per-job identity plumbing lands.

## Completion evidence

- `test_supervised_mode_routes_pytest_through_durable_execution` (nt, real subprocesses): create→ready→claim→gate→execute through `supervised=True` succeeded (`VERIFYING`), exactly one `execution_records` row in state `VERIFICATION_REQUIRED`, durable artifacts under `runs/exec-*/` with `result.json`.
- Bugfix loop: missing `SupervisedExecutionService` import (local import added), wrong table name and missing `os` import in the test.
- Full suite green (see PR); CI green.

## Forbidden

- No default behavior change for existing callers; no real Serena/tunnel interaction.
