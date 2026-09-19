# A-Sunday Conductor — Universal Agent Entry

Status: BINDING / ACCEPTED via WO-P1-162 / PR #219 (merged 2026-09-07)
Applies to: every ChatGPT chat, GPT Work/Codex task, ZCode/GLM goal, Serena/SunDay Worker session, local model, and external coding agent doing non-trivial repository work.

This file is intentionally short. It tells an agent what to read next; it does not duplicate the full policies.

## Start here

Use this order before mutation:

1. Read this file.
2. Read `PROJECT-GRAPH.yaml` to select only the workflow nodes relevant to the task.
3. Read repo-local `AGENTS.md`.
4. Verify actual repository/worktree/remote/branch/HEAD/dirty state and current claim/ownership. Actual state overrides chat memory and stale summaries about state; it does not override user authority, safety constraints, or binding repository policy.
5. Read `CURRENT-WORK.md`.
6. Read the active `docs/work-orders/<id>.md` when one exists or has already been claimed. Read `handoff.md` only for resume/transfer work, unclear continuity, or when `CURRENT-WORK.md` points to it for material context.
7. Read only the task-relevant nodes selected by `PROJECT-GRAPH.yaml`.
8. Before any `src/a_conductor/` mutation, read `DEFECT_LESSONS.md`.
9. Classify R0/R1/R2/R3, claim a non-overlapping scope, then execute the shortest truthful loop in `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`.

If ownership is ambiguous or dirty state is unexplained:

`SAFE_TO_MUTATE = NO`

If no active work order exists for a new task, product/source mutation remains blocked. A bounded docs-only governance bootstrap may create the initial work order/claim in a clean isolated scope; immediately re-run the mutation gate after that bootstrap. This exception never grants product/source/runtime mutation authority.

## Default delivery model

`GPT GOVERNANCE -> CAPABILITY-SELECTED EXECUTION -> DETERMINISTIC VERIFY -> INDEPENDENT REVIEW AS REQUIRED -> GPT ACCEPT/MERGE`

- The implementation executor is selected by task class, risk, capability, readiness, authorization, cost, and availability using `docs/agent-collab/CAPABILITY_MATRIX.md`; GLM/ZCode is the current preferred candidate for bounded READY implementation when those gates pass.
- GPT/integrator owns architecture, trust boundaries, dependency order, claims, cross-lane conflict, SSoT, acceptance, merge, and release.
- R3 work must have GPT/integrator trust/authority framing before implementation and final GPT acceptance after deterministic/independent evidence.
- Deterministic tools/tests/CI are completion authority. Agent confidence or `DONE` is never sufficient.
- Model/provider names are routing preferences, never mutation authority.

## Prompt/relay rule

Do not regenerate a long bespoke prompt when the durable WO/task packet already contains the contract.

Preferred manual fallback until Zero-Relay is accepted:

`Read <task-packet>. Execute only that claimed lane using your supported goal/skills loop. Write result/evidence to <result-destination>. Do not merge.`

The user should relay at most that pointer command. Result copy-back is not required when the integrator can read the declared result directly.

After Zero-Relay passes its R3 gates, A-Conductor may dispatch the same packet automatically. Zero-Relay changes transport, not authority or safety rules.

## Long-running execution liveness

For any delegated/external-agent/tool/CI run that can outlive one immediate tool call, do not tell the user only that the system is "waiting". Read `docs/agent-collab/EXECUTION_LIVENESS_PROTOCOL.md` and recover status from actual runtime + durable evidence.

Required operator truth is: task/execution identity, executor, authoritative job state, derived liveness (`STARTING/RUNNING/WAITING/STALLED/TERMINAL_UNHARVESTED/INTERRUPTED/TERMINAL/UNKNOWN` per `docs/agent-collab/EXECUTION_LIVENESS_PROTOCOL.md`), `last_activity_at`, `last_progress_at`, typed blocker/reason, evidence reference, and exact next safe action. Heartbeat/activity is not proof of progress. `STALLED` is a derived warning, never permission to blind-retry; reconcile process/session/log/durable state first.

A fresh session must recover this state from runtime/Git/durable records rather than asking the user to reconstruct the prior chat. Existing job/events/checkpoints remain authority; this protocol must not create a second task/status store.

## Context/session rollover guard

Ordinary ChatGPT does not expose a trusted exact percentage of remaining context. Never invent one. When a session is materially crowded, near practical rollover, or context pressure is unknown, reuse the WO-P1-259 context-rollover contract over existing ContinuityGuard + durable checkpoint/recovery facts:

- GREEN: continue normally under the existing mutation gate;
- YELLOW: refresh/checkpoint at the next meaningful boundary before more substantial work or rotation;
- RED: start no new non-trivial mutation; checkpoint/recover/reconcile first. If the verdict says rotation is ready, the session may rotate while the new session remains fail-closed for mutation until actual state is recovered.

Context status never grants task, claim, lease, mutation, merge, or acceptance authority. Before rotation preserve the active task/WO, repo/worktree/branch/HEAD, dirty/ownership state, evidence/result pointers, outstanding execution identities/replay safety, blockers, and exact next safe action. The new session resumes from repository/runtime authority rather than requiring the user to paste the old chat.

## Cross-repo lane binding (projection)

Topology values (`CONTROL_PLANE_ONLY` / `EXECUTION_SUBSTRATE_ONLY` / `CROSS_REPO`) have one definition home: `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`. This file projects them without redefining them.

- Every mutation lane is bound to exactly one repo by the full tuple `repo -> worktree -> branch -> HEAD -> task/claim -> scope`.
- A `CROSS_REPO` freeze pins one exact-SHA compatibility set `{AUTHORITY_REPO@SHA_AUTH, EXECUTION_REPO@SHA_EXEC}`; any member head drift invalidates the set until re-pin and focused review of the affected delta.
- WIP capacity under `PROJECT-GRAPH.yaml` `rules.default_wip` is one global budget counted across all set members; `CROSS_REPO` never multiplies WIP per repository.
- `CROSS_REPO` durable evidence, review results, and closeout checkpoints fold to the authority repo, even when the mutating lane's worktree lives in an execution repo.
- Durable Windows no-console rule for execution routing: invoke the exact installed executable directly wherever possible; when PowerShell is unavoidable, launch it hidden with no new console window; background child processes use `CREATE_NO_WINDOW` / `windowsHide`; never change global shell settings or profiles; process termination targets an exact PID with verified command identity only.

## Universal execution loop

`RECOVER -> VERIFY ACTUAL STATE -> READ MINIMUM CONTINUITY -> CLASSIFY -> CLAIM -> ROUTE -> EXECUTE -> TARGETED VERIFY -> FREEZE -> REVIEW/CI BY RISK -> GPT ACCEPT/MERGE -> CHECKPOINT`

Do not ask the user to type `continue` between safe bounded micro-steps. Stop only at a real blocker, an authority/ownership ambiguity, a required approval boundary, or a completed acceptance gate.
