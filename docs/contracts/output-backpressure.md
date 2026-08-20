# A-Conductor Output Backpressure Contract

Status: Phase 1 binding contract
Work order: `WO-AC-RES-006`

## Purpose

A-Conductor must preserve complete local execution evidence while returning only bounded output through chat/MCP/Telegram/Discord/operator surfaces.

AC-RES-002 already owns stdout/stderr/result file creation. This contract adds a read-only evidence boundary; it does not create a second logger or process runner.

## Artifact authority

Callers select only a fixed artifact kind:

- `STDOUT` -> durable `stdout_ref`;
- `STDERR` -> durable `stderr_ref`;
- `REPORT` -> durable `report_ref`.

Callers cannot provide a raw filesystem path. The selected durable ref is re-resolved under both `repo_root` and `run_dir_ref`. Traversal and symlink escape are rejected.

## Bounded reads

Initial maximum returned artifact payload: 64 KiB per call.

Supported read shapes:

- tail: last N bytes, useful for current/failure summaries;
- chunk: offset + bounded N bytes for explicit incremental inspection;
- metadata/digest: total byte count + full SHA-256 without returning full content.

The complete raw artifact remains on disk.

## Text handling

Artifact bytes decode as UTF-8 with replacement for invalid sequences. The reader never fails merely because tool output contains invalid UTF-8.

## Pytest summary

A bounded tail may be parsed for common pytest terminal summary counts:

- passed;
- failed;
- skipped;
- warnings;
- duration seconds.

Unknown/missing fields remain `None`; the parser must not invent counts.

## Transport rule

Operator/MCP/Telegram/Discord adapters should normally request metadata + bounded tail/summary, not full raw logs. Larger inspection requires explicit chunk calls.

## Forbidden

- arbitrary caller-supplied filesystem path;
- unbounded returned file content;
- log deletion/truncation/rotation in this slice;
- process launch/retry;
- Git/network mutation;
- secret/prompt persistence changes.
