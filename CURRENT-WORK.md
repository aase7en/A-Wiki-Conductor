# A-Conductor — Current Work

Last updated: 2026-08-22 (GLM 5.3, post WO-058)

## Current phase

**User picks (a)+(k) delivered: exe rebuilt+reinstalled; WO-058 worker-settings materialization merged (PR #29 -> `f45e1cc`). Remaining: (b) DECISION_REQUIRED items — detailed explanations provided to the user in chat, awaiting their answers.**

## Source-of-truth rule

Do **not** reconstruct task state from chat memory.

For resume, use in this order:
1. actual repository / GitHub state,
2. `CURRENT-WORK.md`,
3. `handoff.md`,
4. active `docs/work-orders/WO-*.md`,
5. `PROJECT-PLAN.md` + binding contracts/ADRs.

## Verified completed work (this resume session)

- WO-P1-056 — PR #27 re-verified (MERGEABLE + CI SUCCESS) then merged → main `2aca60c`; WO marked COMPLETE with merge evidence.
- WO-P1-057 — Serena onboarding / memory presence warning:
  - `inspect_memory_presence()` pure read-only helper (5 states incl. MAINTENANCE_ONLY),
  - PROJECTS panel memory-status line for the selected project + teaching tooltip,
  - PR #28 CI SUCCESS re-verified, merged → main `d2d8970`; full suite 819 passed, 0 failed.
- Known debug note: Tk `Listbox.selection_set` *adds* to selection — tests must `selection_clear` first to model a real click.

## Current verified repository state

- Branch: `main`, HEAD `d2d8970`, working tree clean (only this SSoT doc update pending commit).
- All PRs #27/#28 merged; no open PRs.

## Session addendum (post WO-058)

- (a) Portable exe rebuilt from `cad4a32` (build exit 0, 13,056,554 bytes) and installed to `%LOCALAPPDATA%\Programs\A-Conductor`. **Constraint:** automated smoke blocked by ESET Security (the active AV; Defender is off) refusing fresh unsigned builds — interactive launch will prompt and the user can allow. Code itself verified by the full suite.
- (k) WO-P1-058 merged via PR #29 (CI green, re-verified before merge): per-worker engine settings now materialize into SERENA_HOME on worker start (best-effort, fail-closed confinement). Full suite 822 passed.

## Next safe action (user picks)

1. (a) Rebuild + reinstall the shipped exe (`scripts/build_portable.py` + setup) so installed app matches main (current installed build predates PRs #16+).
2. (b) Approve/decline one of the recorded `DECISION_REQUIRED` items: MCP gateway hard enforcement; CONNECTORS project rebind; supervised-mode default flip.
3. (c) Pick the next bounded milestone from PROJECT-PLAN §13 (e.g., materializing per-worker engine settings into SERENA_HOME on worker start — brain already lands on connector start; the worker path is the remaining gap).

Open a new work order + reuse gate before any implementation.

## Mandatory boundaries

- A-Wiki remains brain/policy/memory authority; do not duplicate its memory/work-order/claim/orchestration systems.
- MCP gateway hard enforcement remains `DECISION_REQUIRED`.
- CONNECTORS project rebind remains deferred behind its user-gated decision.
- Do not restart workers/tunnels merely to fix test environment.

## Escalation rule

GLM 5.3 should do normal implementation/review itself.

Only if a genuinely hard, cross-cutting bug or architecture ambiguity prevents a safe bounded decision, STOP that micro-step, preserve repo state, and write a focused escalation prompt for **GPT-5.6 Sol UltraHigh**. Do not escalate routine coding/tests/UI work.
