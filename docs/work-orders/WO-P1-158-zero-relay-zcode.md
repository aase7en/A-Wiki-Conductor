# WO-P1-158 — Zero-Relay ZCode Execution (ZRA-1)

Date: 2026-09-05
Owner: GLM1 / GLM-A (implementation); GPT1 = independent review + acceptance authority
Status: PHASE_A_FROZEN (see checkpoints); stacked on Issue #213 R3 design
Priority: P0 accelerator (ZRA-1)
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo158-zra1`
Branch: `feat/wo-p1-158-zcode-zero-relay`
Base: `origin/main@f0ddd0b9245cef7a7525a670f470e1de595d4615`

## Goal

Production ZRA-1: one authorized synthetic task executes automatically through
the ZCode app-server/GLM route and returns an exact task-bound result —
reusing every existing provider/lease/admission/execution authority, with ONE
shared supervised run lifecycle.

## Phase A — shared SupervisedRunCoordinator (frozen 2026-09-05)

- NEW `src/a_conductor/supervised_run_coordinator.py`: the single shared
  orchestration authority extracted from `SupervisedCommandRunner` — execution
  fingerprint, `DuplicateExecutionGuard`, execution-record creation, run-dir
  identity, launch, poll/timeout (incl. transient-UNKNOWN observation cap),
  collect/version CAS, bounded stdout/stderr artifact mapping.
  `SupervisedRunIdentity` is the durable identity bundle.
- `SupervisedCommandRunner` is now a behavior-preserving adapter (spec/scope
  validation + delegation; two probe-compat delegations `_repo_root` /
  `_poll_until_resolved` kept so existing lifecycle tests observe the same
  surface). No behavior, thread, store, retry, or scheduler authority added.
- NEW `tests/test_supervised_run_coordinator.py` (10 tests): adapter⇄coordinator
  equivalence — same fingerprint/operation_ref; same success result, record
  shape/refs (runs/<exec-id>/{stdout,stderr,result}), identity fields, agent_ref;
  exec-id format `exec-[0-9a-f]{16}`; REUSE_COMPLETED reuses the SAME execution_id
  with zero new launches; exactly one durable record per run; zero new threads;
  identical timeout and recovery classifications; identical 64 KiB stdout cap
  (full-file digest, tail-truncated payload); scope validation unchanged;
  identity/dependency validation fail-closed; no threading/scheduler text in
  the coordinator source.
- No ZCode execution, provider-profile change, `NativeCommandSpec` extension,
  DB DDL, Worker/lease/ReviewBus change, or PR219/220 file touched.

Evidence at freeze: `test_supervised_command_runner + test_supervised_execution +
test_execution_deduplication + test_execution_artifacts + test_supervised_run_coordinator`
= **65/65 PASS**; `test_recovery_reconciliation + test_desktop_control` = **45 passed**;
`compileall` PASS; `git diff --check` PASS; strict UTF-8 PASS.

## Forbidden

Second runner/execution store/poll loop/collect-CAS/guard; ZCode live process before
Phase D gates; task content in argv; secrets in durable state; scheduler/lease/
admission/ReviewBus changes; GPT2 WO157; PR219/220; live DB.
