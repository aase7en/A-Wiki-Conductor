---
name: a-fasttask
description: A-Sunday Conductor repo-scoped session ROUTER for substantial multi-step work only — routing a non-trivial session through entry/classify/claim/workflow selection, filling or recycling a parallel WIP lane, cross-executor continuation/takeover of a stalled lane, or explicit closeout of a temporary lane. Binds to existing 00-AGENT-ENTRY / PROJECT-GRAPH / FAST_EXECUTION / routing / claim authorities, then hands control to the selected existing workflow. NOT for trivial Q&A, single obvious mechanical edits, or work needing no claim/workflow/lane selection. Grants no mutation, transfer, cleanup, or acceptance authority.
---

# A-FastTask — repo-scoped progressive-disclosure router/binder

Router ONLY (WO-P1-245 / Issue #327). This skill binds the reading agent to the
repository's existing execution authorities and returns one routing decision.
It is not, and must not become: a scheduler, task store, claim/lease system,
reviewer, handoff SSoT, completion state machine, daemon, background cleanup
queue, or source/runtime adapter.

## Trigger (use this skill)

- Substantial repo/session routing: a multi-step task that needs entry
  recovery, risk classification, and a claimed non-overlapping lane before any
  work starts.
- Safe parallel-lane fill or recycle: choosing work for a free WIP lane within
  the existing `3 mutable + 1 read-only review` limit.
- Cross-executor continuation or takeover of a stalled/lane-lost session.
- Explicit closeout of a temporary lane/worktree at end of lane.

## Negative trigger (bypass this skill)

- Trivial Q&A about the repository.
- A single obvious mechanical edit with no claim/branch/workflow decision.
- Mid-lane execution of an already-claimed work-order packet (follow the
  packet as written; do not re-route mid-lane).
- Anything requiring no selection among executors, workflows, or lanes.

## Routing loop

1. RECOVER — run the `00-AGENT-ENTRY.md` start sequence; recover actual
   repository/worktree/remote/branch/HEAD/dirty/claim state, plus task and
   execution liveness per `docs/agent-collab/EXECUTION_LIVENESS_PROTOCOL.md`
   when a prior session exists.
2. CLASSIFY — R0/R1/R2/R3 per `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`;
   select the executor per `docs/agent-collab/CAPABILITY_MATRIX.md` and
   `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`; check WIP capacity per
   `PROJECT-GRAPH.yaml` `rules.default_wip`.
3. BRANCH — choose the one existing workflow that fits (normal fast path, R3
   high-risk path, continuation, takeover, or closeout) and read only the
   matching reference below:
   - roles / WIP / executor fallbacks → `references/conductor.md`
   - continuation / takeover / checkpoint → `references/material-boundary.md`
   - temporary-lane closeout → `references/closeout.md`
4. BIND, then HAND OFF — record/report exactly these routing fields:
   - existing task/claim reference (work order + claim identity; never
     invented here);
   - chosen existing workflow (named file/risk tier);
   - evidence destination (ignored `runs/<work-item>/<lane>/` path);
   - current blocker (typed failure code or `NONE`);
   - cleanup state (`NOT_NEEDED`, `PENDING`, `BLOCKED`, or `COMPLETE`), plus exact path/reason/evidence when applicable;
   - exact next action (one bounded command or step).
   The A-FastTask routing role ends after this decision, but the user-facing
   session does NOT stop merely because routing finished. If this agent is the
   authorized selected executor/integrator and a safe next micro-step exists,
   continue immediately under the chosen existing workflow. Stop only for a
   real blocker/approval gate/terminal state, or when the route hands work to
   a different executor that must run on another execution surface.

## Authority floor

Selection of this skill grants NO mutation, transfer, cleanup, or acceptance
authority. If any required authority item is missing or ambiguous, the routing
decision is `SAFE_TO_MUTATE = NO` plus the typed blocker and the exact next
action. No new authority path may be created to work around a missing one.
