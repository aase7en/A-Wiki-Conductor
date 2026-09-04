# A-Sunday Conductor — Universal Agent Entry

Status: CANDIDATE / BINDING AFTER WO157 ACCEPTANCE
Applies to: every ChatGPT chat, GPT Work/Codex task, ZCode/GLM goal, Serena/SunDay Worker session, local model, and external coding agent doing non-trivial repository work.

This file is intentionally short. It tells an agent what to read next; it does not duplicate the full policies.

## Start here

Use this order before mutation:

1. Read this file.
2. Read `PROJECT-GRAPH.yaml` to select only the workflow nodes relevant to the task.
3. Read repo-local `AGENTS.md`.
4. Verify actual repository/worktree/remote/branch/HEAD/dirty state and current claim/ownership. Actual state overrides chat memory and stale summaries.
5. Read the continuity core:
   - `CURRENT-WORK.md`
   - `handoff.md`
   - the active `docs/work-orders/<id>.md`
6. Read only the task-relevant nodes selected by `PROJECT-GRAPH.yaml`.
7. Before any `src/a_conductor/` mutation, read `DEFECT_LESSONS.md`.
8. Classify R0/R1/R2/R3, claim a non-overlapping scope, then execute the shortest truthful loop in `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`.

If the active work order cannot be identified, ownership is ambiguous, or dirty state is unexplained:

`SAFE_TO_MUTATE = NO`

## Default delivery model

`GPT GOVERNANCE -> GLM/ZCODE EXECUTION -> DETERMINISTIC VERIFY -> INDEPENDENT REVIEW AS REQUIRED -> GPT ACCEPT/MERGE`

- GLM/ZCode is the default primary implementation engine for bounded READY work when it is capable, ready, authorized, and the route is allowed.
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

`RECOVER -> VERIFY ACTUAL STATE -> READ CONTINUITY -> CLASSIFY -> CLAIM -> ROUTE -> EXECUTE -> TARGETED VERIFY -> FREEZE -> REVIEW/CI BY RISK -> GPT ACCEPT/MERGE -> CHECKPOINT`

Do not ask the user to type `continue` between safe bounded micro-steps. Stop only at a real blocker, an authority/ownership ambiguity, a required approval boundary, or a completed acceptance gate.
