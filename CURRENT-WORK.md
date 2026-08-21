# A-Conductor — Current Work

Last updated: 2026-08-22 (GLM 5.3 resume session, post WO-057)

## Current phase

**WO-P1-056 and WO-P1-057 both merged. Phase 1 backlog is clear of open implementation work; next steps are user-gated decisions or a fresh milestone pick.**

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
