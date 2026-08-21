# A-Conductor — Current Work

Last updated: 2026-08-21 (session 6, WO-P1-055 verified)

## Current phase

**Second Brain Phase 1 delivered + usability/onboarding polish. WO-P1-055 verified; Phase 2 backlog is next.**

## Session 5 summary (WO-P1-052 + WO-P1-053, PRs #18-#24, all CI-green, main `c40c1d8`)

- **Second Brain (WO-P1-052)**: plan file (SSoT) → settings `brain_folders`/`brain_entry_files` → renderer `system_prompt` index injection (Index+Pull, no contents) → **Second Brain dialog** (global profile, A-Wiki defaults) → **materialize-on-start** (append-only, safe for validated configs; verified on a temp copy of the live instance).
- **SerenaDoc**: all 34 files read; durable implications in `docs/references/serena-fulldoc-implications.md` (chatgpt context = multi-project switching via activation prompt; onboarding context cost; dashboard port instability; serena-hooks; trusted-projects gate; slow per-language readiness; git staging side effects).
- **Usability overhaul (WO-P1-053)** from the user's 8 trial issues: tooltips everywhere + ONLINE/OFFLINE explained; quick-start 3-step hint bar; **in-app guide viewer**; Add/Assign in PROJECTS panel; scrollbars + wrapping rows + larger minsize; brain button สมอง + folder; **connector-aware Start** (root-caused: Start needed runtime setup; now the worker's Start routes to the matching CONNECTOR — works out of the box) + CONNECTOR column linking workers↔instances.

## Session 5 evidence

- Full suite **801 passed**; smoke `A-CONDUCTOR_SMOKE_OK projects=0 workers=3` on merged main.
- Real-machine: brain injection verified on temp copy (live untouched, idempotent).

## Session 5b addendum (WO-P1-054, PR #25)

New-user onboarding shipped: in-app **ตั้ง Tunnel ID** (paste-validate-save, confined write), CONNECTORS **TUNNEL** column, USER-GUIDE **เชื่อมต่อ AI แต่ละค่าย** section (ChatGPT/OpenAI/Claude/Codex/Grok/Antigravity + security note), clickable links in the in-app guide viewer. Full suite 808 passed.

## Session 6 — WO-P1-055 Alive Status + Themed Teaching Errors

Recovered a pre-existing partial working tree on branch `chunk/p1-055-alive-status-themed-errors` at baseline `2a24c5b5e59c2453add53ad2e957c3616e1327c6` and completed the bounded UI polish:

- slow semantic pulse for `ONLINE`; `OFFLINE` remains error-colored,
- themed teaching error popup with Thai explanation + stable error code + next action,
- 29 statically emitted `_handle_error("CODE")` values covered by the explanation table,
- removed duplicate activity logging, moved dim-ready color into `DesktopTheme`, removed a stray debug marker,
- removed obsolete `messagebox` import and tightened pulse assertions.

Verification:

- `git diff --check`: clean,
- targeted desktop UI: **38 passed**,
- first full-suite run: 809 passed / 1 unrelated timing failure; isolated failing test passed,
- verification full-suite rerun: **810 passed**.

Environment note: Sunday-Conducter inherited stale PyInstaller `TCL_LIBRARY`/`TK_LIBRARY` values pointing to an expired `_MEI...` directory. Tk verification succeeded using Python 3.13 with command-scoped Tcl/Tk overrides and custom `--basetemp`; no machine-wide environment or tunnel/worker config was changed.

## Next safe action

Phase 2 backlog triage + reuse gate, then open the next bounded work order before implementation. Existing candidates from the approved plan/handoff are: MCP gateway enforcement, CONNECTORS rebind UI, onboarding warnings for missing memory, and activation-prompt helper. Prefer deterministic/small-scope work first; escalate only genuinely cross-cutting architecture work.
