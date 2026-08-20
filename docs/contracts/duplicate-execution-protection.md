# A-Conductor Duplicate Execution Protection Contract

Status: Phase 1 binding contract
Work order: `WO-AC-RES-005`

## Purpose

Repeated transport/session requests must not create duplicate substantial executions when an equivalent execution already exists durably.

This contract decides whether to attach, reuse evidence, launch a new execution, or block. It does not launch or retry anything itself.

## Canonical fingerprint

Fingerprint input is bounded and normalized in memory from:

- project ID;
- job ID;
- work-order reference;
- backend ID;
- repository root;
- branch;
- HEAD-before;
- operation reference;
- runtime-profile reference when present;
- normalized target argv.

The canonical payload is hashed with SHA-256. Raw argv is not persisted by this component.

Worker ID is deliberately not part of equivalence so duplicate requests routed to different workers cannot silently run the same durable operation twice. Backend/runtime identity remains part of the fingerprint because execution environments may not be equivalent.

## Durable identity recheck

A matching hash is evidence, not authority. After a fingerprint match, compare the durable identity fields above (except raw argv, which is represented by the fingerprint) against the request. Any mismatch returns `BLOCKED_UNKNOWN` rather than trusting the hash.

## Decisions

- `SAFE_TO_LAUNCH`: no durable equivalent exists.
- `ATTACH_RUNNING`: equivalent durable execution is queued/starting/running/process-still-running; observe the original.
- `REUSE_COMPLETED`: equivalent execution already produced a deterministic completed result state (`VERIFICATION_REQUIRED`, `SUCCEEDED`, or `FAILED`); reuse/report that evidence rather than rerun automatically.
- `BLOCKED_UNKNOWN`: equivalent execution is partial, cancelled, recovery-required, process-exited-with-unknown-result, or otherwise unsafe to classify.

A separate explicit retry policy may later authorize a new attempt after reconciliation. This module never interprets a duplicate request as retry authorization.

## Store lookup

`SQLiteExecutionStore` provides a read-only newest-first fingerprint lookup. Lookup creates no events, changes no versions, and performs no launch/process/network action.

## Forbidden

- process launch/relaunch;
- automatic retry;
- automatic failover/router behavior;
- persisted raw argv, prompt, transcript, credentials, or arbitrary environment;
- Git/filesystem mutation;
- hash-only trust without durable identity recheck.
