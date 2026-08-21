# WO-P1-056: Serena Activation Prompt Helper

Status: COMPLETE
Lane/files: `src/a_conductor/desktop_ui.py`, `tests/test_desktop_ui.py`, `docs/USER-GUIDE.md`, `docs/work-orders/WO-P1-056-activation-prompt-helper.md`, `CURRENT-WORK.md`, `handoff.md`
Branch: `chunk/p1-056-activation-prompt-helper`
Baseline HEAD: `2d345eb` (main after PR #26)
Model tier: high

## Goal

Reduce per-session Serena activation friction by giving the user a one-click copy helper for the documented activation prompt of the selected project.

## Reuse-before-build classification

`NEW` only at the A-Conductor desktop operator surface, reusing existing Serena documentation and existing project selection/error/logging behavior.

A-Wiki gate checked on 2026-08-21 before implementation:
- `A:\GitHub\A-Wiki` branch `main`, HEAD `1d78425448417768661aa536872786515a4abbbd`, clean working tree.
- `.tmp/agent-claims.json`: no active claims.
- `docs/work-orders/`: README/template only; no active A-Wiki work order conflicts.

This work does **not** create or modify task routing, claims, work-order semantics, memory policy, or orchestration intelligence.

## Source facts

`docs/references/serena-fulldoc-implications.md` records:
- canonical activation prompt: `Activate the current dir as project using serena`;
- ChatGPT context is multi-project and activation can be per-session friction;
- implication: surface a copy-paste activation prompt in the UI hint/guide.

## Acceptance

- PROJECTS panel exposes an `Activate` helper without keyboard shortcuts.
- With a selected project, clicking `Activate` copies a prompt containing the exact canonical Serena sentence plus the selected project path.
- With no selected project, existing `SELECT_PROJECT` teaching error path is used.
- Clipboard action is presentation-only; it does not activate Serena by itself and does not mutate the selected repository.
- Action is logged without dumping unrelated project content.
- Tooltip and in-app guide explain that the user pastes the copied prompt into the connected AI chat.
- Existing UI tests remain green.

## Micro-steps

- [x] 056-A Reuse/A-Wiki gate + bounded UX contract.
- [x] 056-B Add tests for prompt generation/copy behavior and button presence.
- [x] 056-C Implement helper + guide wording.
- [x] 056-D Targeted/full regression + review + continuity checkpoint.

## Forbidden

- No MCP gateway/proxy.
- No automatic `activate_project` call from A-Conductor.
- No repository mutation in the target project.
- No worker/tunnel restart.
- No new orchestration or memory state.

## Completion evidence

- RED contract: 4 focused tests failed before implementation because `activate_button` / `copy_activation_prompt` did not exist.
- GREEN focused contract: **4 passed**.
- Desktop UI regression: **40 passed**.
- Full suite: **812 passed**.
- `git diff --check`: clean.
- Python compile: desktop UI + desktop UI tests compiled successfully.
- No worker/tunnel restart and no target-repository mutation.
