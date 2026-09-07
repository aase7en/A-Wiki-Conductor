# A-Conductor Recovery Reconciliation Contract

Status: Phase 1 binding contract
Work order: `WO-AC-RES-004`

## Purpose

After a transport reconnects, A-Conductor must reconcile the original supervised execution against durable ownership, process/result evidence, and current repository identity before any next mutation is permitted.

The recovery path never reruns merely because a transport disappeared.

## Reuse boundary

This capability is `WRAP + EXTEND` over:

- AC-RES-001 durable execution records;
- AC-RES-002 supervised launch/inspect/collect;
- AC-RES-003 transport-state + ownership preservation;
- `StrictReadOnlyGitRunner` for repository root/branch/HEAD identity;
- `NativeGitReadAdapter.status_short()` for dirty-state observation.

It does not create a second process engine, job state machine, work-order system, scheduler, or retry loop.

## Recovery decisions

A reconciliation result is one of:

- `MONITOR_ORIGINAL` — original supervisor/process remains alive; attach/observe only;
- `VERIFY_RESULT` — original result was collected successfully and deterministic verification/review is next;
- `REVIEW_FAILURE` — original result is a completed non-zero execution and needs review, not rerun;
- `RECOVERY_REQUIRED` — original process/result provenance is incomplete or malformed;
- `RECOVERY_BLOCKED` — worker/job ownership or repository identity is unsafe/mismatched.

No decision implies automatic retry.

## Required identity gate

Before allowing any next repository mutation after reconnect, verify read-only:

1. durable job belongs to the execution's `job_id`/project;
2. durable job remains claimed by the same `worker_id`;
3. repository root equals durable `repo_root`;
4. current branch equals durable `branch` when branch identity was recorded;
5. current HEAD equals durable `head_before` for this MVP slice;
6. worktree dirty state is empty before automatic continuation.

If root/branch/HEAD/dirty observation fails or mismatches, return `RECOVERY_BLOCKED`.

A dirty worktree is evidence requiring review; this slice does not guess whether the dirty state is expected output of the original operation.

## Process/result reconciliation

- If AC-RES-002 inspection says the original supervisor is still running, preserve the execution and return `MONITOR_ORIGINAL`.
- If the original durable result exists, collect that exact result; do not spawn a replacement process.
- Exit code `0` yields `VERIFY_RESULT`.
- Non-zero exit yields `REVIEW_FAILURE`.
- Supervisor exited with missing/malformed/unknown result yields `RECOVERY_REQUIRED`.

## Transport restoration

Transport restoration is ownership-gated through AC-RES-003 and may be idempotent. Reconciliation does not release claims or change job ownership.

## Forbidden

- blind retry/relaunch;
- reset/clean/stash/checkout/switch/rebase/merge;
- automatic commit/push;
- automatic failover;
- Serena-specific reconnect logic;
- mutation of A-Wiki or Phase6 repos.

## Context-window rollover rule

Chat context is transport context, not durable state. If a ChatGPT/session context becomes crowded or near its practical limit, the current agent must checkpoint repository state before recommending a new session:

- active work order and micro-step;
- branch/HEAD/worktree state;
- completed evidence/tests;
- unresolved blocker/decision;
- exact next safe action;
- forbidden actions/ownership constraints.

The new session must be able to resume without prior chat by using the universal startup core: `00-AGENT-ENTRY.md -> PROJECT-GRAPH.yaml -> AGENTS.md -> actual Git/runtime/claim state -> CURRENT-WORK.md -> handoff.md -> active work order -> task-relevant graph nodes`. Before any `src/a_conductor/` mutation it must also read `DEFECT_LESSONS.md`. `PROJECT-PLAN.md`, `DESIGN.md`, and `COLLAB.md` remain authoritative but are loaded when the project graph selects architecture/roadmap, UI/UX, or coordination scope.
