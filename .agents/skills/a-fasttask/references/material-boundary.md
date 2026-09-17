# A-FastTask reference — checkpoint, recovery, takeover

Material-boundary contract for cross-executor continuation/takeover
(WO-P1-245). It reuses the existing claim/lease authority and continuity
artifacts and adds no new transfer mechanism.

## Checkpoint (before any handoff or stop)

At material boundaries only (not after every micro-step), the active lane
writes its checkpoint record — branch/HEAD/worktree state, completed evidence,
blocker/decision state, exact next safe action, forbidden/ownership
constraints — ONLY to its declared result/evidence destination, then stops
mutation. An arbitrary active/bounded executor MUST NOT write
`CURRENT-WORK.md`, `handoff.md`, the active work order, or any other
coordination SSoT: those artifacts have single-writer authority — Sol/integrator,
or an executor explicitly assigned those exact coordination paths, folds
accepted state into the EXISTING WO/`CURRENT-WORK.md`/`handoff.md`. A fresh
session must be able to resume from repository state alone, without the prior
chat. Takeover serialization still uses the same existing claim/lease authority
(below), never a side channel.

## Continuation (same executor, new session)

Recover from actual runtime plus durable evidence: task/execution identity,
executor, authoritative job state, derived liveness, `last_activity_at` /
`last_progress_at`, typed blocker, evidence reference
(`docs/agent-collab/EXECUTION_LIVENESS_PROTOCOL.md`). Continue only the exact
claimed scope. A transport timeout or ownership uncertainty is
`RECOVERY_REQUIRED` — never a blind replay of a command that may already have
run.

### Fresh-session delegated-run reconciliation

Before any new dispatch or conflicting mutation, enumerate the current task's
known outstanding delegated-execution pointers from the existing job/events/
checkpoint/evidence authorities and reconcile each against actual runtime,
bounded logs/result destination, Git/worktree state, and provider/CI evidence
when applicable.

- `RUNNING`: preserve the existing owner/claim and do not duplicate-dispatch;
  unrelated non-overlapping READY work may continue.
- `TERMINAL_UNHARVESTED`: harvest the declared result/evidence first, verify its
  execution/task/exact-SHA/scope identity, then continue from the accepted or
  repair-required outcome.
- `STALLED`, `INTERRUPTED`, or `UNKNOWN`: classify `RECOVERY_REQUIRED`; inspect
  process/session side effects and replay safety before attach/recover/takeover.
  None of these states grants automatic retry.

If an intentional context/session rollover occurs while delegated work remains
outstanding, checkpoint the existing task/claim reference, execution/session or
PID identity when known, repo/worktree/branch/HEAD, scope, start time,
log/result/evidence destinations, replay-safety state, derived liveness, and the
exact next harvest/reconcile action. These are pointers into existing authority,
not a second task or execution store.

## Takeover (new executor replaces a stopped one, e.g. Codex/Astra → Sol)

Takeover is fail-closed. ALL of the following must be proven with evidence
before any takeover; any UNKNOWN => NO takeover:

1. Old writer INACTIVE — the old executor's session/task is TERMINAL, or it is
   unreachable AND no child process it started is still executing. OFFLINE is
   not INACTIVE: a rate-limited or transport-stopped executor may still have a
   running child process that can mutate state.
2. Exact state recheck — repository, worktree, remote, branch, HEAD, dirty
   inventory, untracked files, observed now, not from chat memory.
3. Pending-command inventory — no in-flight or queued command from the old
   writer can still mutate the worktree or the remote.
4. Claim/lease state — current claim owner, lease expiry, and overlap recheck
   against all live lanes.
5. Serialization — the transfer happens THROUGH the same existing claim
   authority (advance/transfer the existing claim); never a side agreement
   between executors.

After a takeover is serialized through the claim authority, the old executor
is READ-ONLY from that point. If it resurfaces, it must observe the transfer
(claim state + checkpoint) and stop writing; conflicting late writes go to Sol
adjudication with evidence — never a force rollback.

## Scenario bindings

- Codex/Astra rate-limit or transport stop => takeover only after the
  inactivity proof above; otherwise checkpoint and hold (`RATE_LIMITED` /
  `TRANSPORT_FAILURE` + `WORKER_STATE_UNKNOWN`).
- Child process still executing, or executor offline with unknown children =>
  NO takeover; wait for terminal state or recover the child through its
  documented liveness path.
- Dirty or unexplained worktree discovered during takeover =>
  `SAFE_TO_MUTATE = NO`; Sol adjudicates ownership before any write.
