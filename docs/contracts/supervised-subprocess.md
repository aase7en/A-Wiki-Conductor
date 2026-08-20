# Supervised Subprocess Contract

Status: AC-RES-002 binding contract
Parent: `docs/contracts/resilient-execution-supervisor.md`
Depends on: `docs/contracts/durable-execution-record.md`

## Purpose

Run suitable medium/long commands independently from the requesting transport session while preserving exact ownership, durable logs and recoverable result metadata.

## Reuse-first composition

```text
DurableExecutionRecord / SQLiteExecutionStore
              |
              v
SupervisedExecutionService
              |
              v
WindowsOwnedProcessController
              |
              v
A-Conductor supervisor helper process
              |
              v
Target subprocess (shell=False)
```

The existing owned-process controller remains the process ownership engine. AC-RES-002 does not create a parallel PID/termination system.

## Supervisor helper

The helper is an internal A-Conductor process, not an operator command surface. Its stable `execution_id` is present in the helper command line and is used as the existing owned-process ownership marker.

The helper:
1. receives validated runtime paths and target argv in memory/command line;
2. launches target using `shell=False`;
3. inherits the helper's sanitized environment and redirected stdout/stderr handles;
4. atomically writes child PID;
5. waits for target exit;
6. atomically writes result JSON containing only bounded metadata;
7. exits with the target exit code when representable.

Raw target argv must not be written to result JSON or SQLite.

## Durable files

Conceptual run directory:

```text
<runtime-root>/runs/<execution-id>/
  supervisor.pid
  child.pid
  stdout.log
  stderr.log
  result.json
```

AC-RES-002 does not require `metadata.json`; durable execution identity remains authoritative in SQLiteExecutionStore.

## Result JSON

Allowed fields only:
- schema_version
- execution_id
- child_pid
- exit_code
- started_at
- finished_at

No prompt, transcript, command, argv, environment, stdout, stderr, token or secret fields.

## Launch semantics

Launch is allowed only for a prevalidated `SupervisedLaunchPlan`. The service creates/persists the execution record before process mutation, transitions it through STARTING, invokes exact-owned supervisor launch, persists child/supervisor evidence when available, then returns without waiting for target completion.

A transport disconnect after launch is not execution failure.

## Inspect semantics

Inspect performs observation only. It never launches or retries. It may report bounded classifications such as:
- STARTING
- SUPERVISOR_RUNNING
- RESULT_AVAILABLE
- SUPERVISOR_EXITED_RESULT_MISSING
- RECOVERY_REQUIRED

## Collect semantics

Collect reads a complete, validated result JSON and updates durable execution metadata/state. It never reruns the target. Missing or malformed result evidence yields recovery-required/unknown classification rather than inferred success.

## Explicitly deferred

- transport reconnect policy (AC-RES-003/004)
- duplicate fingerprint attach/reuse (AC-RES-005)
- output tail/chunk APIs and richer report summaries (AC-RES-006)
- fake backend chaos matrix (AC-RES-007)
- Serena integration (AC-RES-008)
