# WO-P1-067 — Second Brain E2E verification + restart-activation warning

Created: 2026-08-25
Owner: GLM 5.3 Max (user-directed E2E question: "does Add Brain actually make workers smarter / read A-Wiki AGENTS.md / remember?")
Status: DONE (audit + fix); user action item listed below
Branch: `fix/brain-restart-note` (PR #82)

## Question under test

After Add Brain, do workers actually behave differently — do chat sessions read A-Wiki's AGENTS.md and carry rules/memory — and why did plain ChatGPT sessions through Workers appear to ignore AGENTS.md and remember nothing?

## Layer 1 — Real-machine audit (read-only, 2026-08-25)

- App DB `%LOCALAPPDATA%\A-Conductor\control-center.sqlite`, table `serena_worker_settings`, row `global-brain`: brain IS saved — folders `["A:\GitHub\A-Wiki"]`, entries `["A:\GitHub\A-Wiki\AGENTS.md", "A:\GitHub\A-Wiki\wiki\context\wiki-overview.md"]` (saved 14:52).
- All 5 connectors' `serena-home/serena_config.yml` (sunday-worker-1..5): **zero** occurrences of the brain marker `# A-CONDUCTOR SECOND BRAIN`, no `system_prompt`, no AGENTS.md/wiki-overview references. Config mtimes = last Start times (latest 14:34, worker-4).

## Layer 2 — Mechanism (code, with tests already on main)

- Injection is Start-only: `LocalInstanceOrchestrator.start()` → `_apply_brain()` (`local_instances.py:263-291`) → `apply_brain_to_serena_home()` (`worker_serena_settings.py:305-339`): appends a managed block after the marker with `system_prompt: |` instructing the agent — brain folders are the source of truth (not chat memory), must-read entry files BEFORE the task (`read_file`), state the rule before any mutation, pull more brain content on demand. Guards: no-op without config/brain, refuses foreign `system_prompt`, idempotent re-apply (strips old block first). Covered by `test_worker_serena_settings.py` (apply/idempotent/skip) and `test_local_instances.py` (start path calls applier).

## Verdict

The brain design is sound and the injected prompt asks exactly for the behavior the user expects (read AGENTS.md first; don't trust chat memory). The observed "workers ignore rules / don't remember" happened because **every running connector was started before the brain was ever saved** — and nothing told the operator that saves apply only at the next Start. Chats attached to long-running connectors therefore never received the brain.

## Fix in this branch

`save_brain_config()` now (a) logs `NOTE: restart running connectors to activate` and (b) shows the activation rule in the dialog's green status: the brain applies when a connector Starts; restart running connectors so current chats pick it up. Regression test pins the note.

## What this does NOT change (by design, recorded for GPT)

- The brain is an advisory system prompt, not automatic memory: "remembering" still depends on the agent following the injected instruction to read brain files each session. Durable cross-session memory remains A-Wiki session-memory / Serena project memory. A stronger product answer (auto-inject on save + rolling restart prompt) is an interaction-design question → GPT lane.

## USER ACTION ITEM (to activate the brain on live chats today)

In A-Sunday Conductor: Stop → Start each running connector (Sunday-Worker 1..5). After restart, each instance's serena_config.yml gains the block and new chat turns will be told to read A-Wiki AGENTS.md + wiki-overview before working. (Existing chat history is not retroactively "remembered" — the rules apply to subsequent turns.)

## Evidence

- DB row + config greps quoted above (timestamps included).
- Tests: `tests/test_desktop_ui.py::test_second_brain_dialog_saves_global_profile` (now asserts the restart note); brain apply/idempotent/skip suite green on main; focused brain tests on this branch: 2 passed, 1 transient uv-Tk skip.
