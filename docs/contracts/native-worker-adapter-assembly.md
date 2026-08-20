# A-Conductor Native Worker Adapter Assembly Contract

Status: Phase 1 binding contract
Work order: `WO-P1-037`

## Purpose

Build the exact native execution scope for a currently assigned A-Worker and construct only the fixed read/verification adapters used by the allowlisted native-operation backend.

## Source of truth

Every `resolve(worker_id)` call reads a fresh Control Center snapshot. The resolver must not cache a project path, assignment, or mutation authority across calls.

The current worker row must provide:

- exact `worker_id`
- active `assignment_id`
- `project_id`
- `project_root_path`
- boolean `mutation_allowed`

Missing values fail code-only. No other worker/project is selected automatically.

## Scope construction

`project_root_path` becomes the exact `NativeExecutionScope.root`. NativeExecutionScope itself validates that the path is absolute, exists, and is a directory.

`mutation_allowed` is copied exactly from the assignment.

Initial executable authority contains only configured Git and Python executable names. Environment override authority is empty by default.

## Adapter construction

Default output:

```text
WorkerNativeAdapters(
  git=NativeGitReadAdapter(scope),
  verification=NativeVerificationAdapter(scope),
)
```

No NativeGitTransactionAdapter or generic subprocess runner is surfaced by this resolver.

Adapter factories may be injected for deterministic tests. They receive only the already-validated NativeExecutionScope.

## Reassignment

If a worker is released/reassigned, the next resolve must derive the new assignment/root/authority. Previously returned adapter objects are snapshots of the old authority and must not be treated as dynamically authoritative by callers.

## Explicitly out of scope

- worker start/stop/restart
- tunnel/profile/process operations
- project registration or assignment mutation
- scheduler/background execution
- model/provider routing
- Git mutation adapters
