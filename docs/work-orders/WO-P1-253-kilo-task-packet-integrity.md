# WO-P1-253 — Kilo task-packet integrity harness foundation

Status: CLAIMED / IMPLEMENTATION
Issue: #354
Risk: R3 CRITICAL — external harness task-authority transport boundary
Topology: CONTROL_PLANE_ONLY
Owner/integrator: GPT-5.6 Sol
Implementation owner: SunDay-Worker 3

## Binding

- Authority repo: `A:\GitHub\A-Wiki-Conductor`
- Execution repo: N/A for this slice
- Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo253-kilo-packet`
- Branch: `feat/wo-p1-253-kilo-packet-integrity`
- Base/current start SHA: `8dd659df635b50988757414d3eae2f1cf923ba52`
- Runtime evidence: installed Kilo CLI `7.7.2`
- Durable authority: GitHub Issue #354

## Problem

Live A-FastTask evidence showed that a healthy provider/model route is not sufficient when the
harness transports the task packet incorrectly.

Two zero-source-effect failures were reproduced:

1. multiline task text passed as a positional Kilo argument reached the executor without the
   authoritative task body;
2. placing `--file <task>` before the positional message causes Kilo's array option to consume the
   following message as another file path.

A local parser probe with an invalid model proved the accepted argv order:
the positional fixed message MUST appear before `--file`. With that ordering Kilo reached model
resolution; with `--file` first it failed as `File not found: <message>`.

The same probe also confirmed that Kilo may emit a session/share URL on stderr. Such URLs are
security-sensitive evidence and must be redacted before persistence.

## Goal

Add a narrow Kilo harness foundation that preserves the existing task/claim/job authorities while
making task-packet transport deterministic and fail-closed.

## Initial claimed tracked scope

- NEW `src/a_conductor/kilo_harness.py`
- NEW `tests/test_kilo_harness.py`
- NEW `docs/work-orders/WO-P1-253-kilo-task-packet-integrity.md`

No other tracked file is mutable in this slice.

## Required invariants

1. Reuse the accepted `TaskPacketFile` identity; do not invent a second task-packet authority.
2. Re-read a bounded regular task file inside the declared worktree and verify exact SHA-256 before
   building/executing an invocation.
3. Never place raw task-packet text in argv.
4. Build Kilo argv so the fixed positional instruction appears before every `--file` option.
5. Use an injected runner only in this slice; no subprocess/network/provider call in production code.
6. Bound timeout and captured output.
7. Redact Kilo session/share URLs and declared secret values before result/evidence leaves the
   adapter boundary.
8. Exit code 0 is never sufficient for success; result classification remains explicit.
9. Missing, moved, oversized, out-of-worktree, non-regular, hash-mismatched, or contract-mismatched
   task packets fail closed before runner execution.
10. No scheduler/job/claim/review/completion/provider authority, no live Kilo dispatch, no provider
    configuration mutation, and no credential storage.

## Failure model

Typed local harness failures should distinguish at least:
- packet invalid / outside scope / hash mismatch;
- invocation policy invalid;
- timeout;
- output limit;
- runner failure;
- output invalid.

Transport failure must not imply task failure or authorize replay.

## Verification

RED/GREEN focused tests must cover:
- exact valid task packet;
- task mutation after hash creation;
- outside-worktree path;
- symlink/non-regular packet;
- bounded packet size;
- contract-ref mismatch;
- fixed message precedes `--file`;
- multiline/JSON/Unicode content absent from argv;
- Windows paths/backslashes remain a single argv element;
- share URL redaction in stdout/stderr;
- declared secret-value redaction;
- timeout/output-limit/runner failure classification;
- runner is not called on preflight failures.

Then run:
- focused `tests/test_kilo_harness.py`;
- directly related Claude harness tests as compatibility backstop;
- `git diff --check`;
- exact three-path scope check;
- added-line secret scan.

Freeze exact SHA, then independent read-only exact-SHA review before any integration.

## Forbidden

- no live Kilo/CoinTH/Claude provider dispatch;
- no `src/a_conductor/job_execution.py` or provider/runtime assembly mutation;
- no `src/a_conductor/claude_code_harness.py` refactor in this slice;
- no credentials, raw share URLs, or raw secret-bearing logs in durable evidence;
- no reset/clean/stash/rebase/force-push/broad process kill.

## Next phase after acceptance

Only after this packet-integrity foundation is accepted, claim a separate phase for a thin
`KiloJobBackend` conforming to the existing `JobExecutionBackend` and supervised execution
authority. Do not widen this slice automatically.
