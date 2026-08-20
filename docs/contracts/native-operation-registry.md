# A-Conductor Native Operation Registry Contract

Status: Phase 1 binding contract
Work order: `WO-P1-036`
A-Wiki classification: `EXTEND`

## Purpose

Map opaque, pre-authorized operation identifiers to a deliberately small set of fixed native adapter methods. This is the bridge between durable job execution and deterministic local tools. It is not a generic shell, planner, scheduler, or model router.

## Definition shape

An operation definition contains only:

- `operation_ref`
- enum-backed `kind`
- optional confined relative `paths`
- bounded `timeout_seconds`

Definitions must not contain executable names, argv arrays, shell strings, environment payloads, prompts, or raw commands.

## Initial fixed kinds

```text
GIT_STATUS        -> NativeGitReadAdapter.status_short()
GIT_WORKING_DIFF  -> NativeGitReadAdapter.working_diff(paths)
GIT_CACHED_DIFF   -> NativeGitReadAdapter.cached_diff(paths)
PYTEST            -> NativeVerificationAdapter.pytest(paths)
COMPILEALL        -> NativeVerificationAdapter.compileall(paths)
```

No Git mutation operation is exposed by this registry.

## Worker binding

A backend resolves the durable worker ID to an explicit pair of already-constructed native adapters. Missing workers fail code-only and do not fall back to another worker automatically.

## Result mapping

Native command success means:

- `timed_out == false`
- `exit_code == 0`

Failure classifications:

- Git read operations -> `NO_MUTATION`
- pytest/compileall failure or timeout -> `UNKNOWN`

This is intentionally conservative for verification tools because they may create caches or artifacts.

## Evidence

The backend constructs a deterministic evidence reference from safe result metadata and SHA-256 hashes already computed by the native execution layer. Raw stdout/stderr strings are never embedded in the evidence reference and are not persisted by the durable job store.

## Security boundary

The operation registry exposes no generic `run(command)`, argv, executable, shell, Git mutation, filesystem mutation, scheduler, routing, or model-selection method.

Concrete adapter construction and scope/authority remain outside this registry and must already satisfy the native execution contracts.
