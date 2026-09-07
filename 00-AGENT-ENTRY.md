# A-Sunday Conductor — Universal Agent Entry

Status: CANDIDATE / BINDING AFTER WO157 ACCEPTANCE
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

## Universal execution loop

`RECOVER -> VERIFY ACTUAL STATE -> READ MINIMUM CONTINUITY -> CLASSIFY -> CLAIM -> ROUTE -> EXECUTE -> TARGETED VERIFY -> FREEZE -> REVIEW/CI BY RISK -> GPT ACCEPT/MERGE -> CHECKPOINT`

Do not ask the user to type `continue` between safe bounded micro-steps. Stop only at a real blocker, an authority/ownership ambiguity, a required approval boundary, or a completed acceptance gate.
