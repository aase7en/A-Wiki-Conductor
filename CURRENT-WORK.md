# A-Conductor — Current Work

Last updated: 2026-08-21 (session 5b end)

## Current phase

**Second Brain Phase 1 delivered + usability overhaul from real user trial. Awaiting next user trial.**

## Session 5 summary (WO-P1-052 + WO-P1-053, PRs #18-#24, all CI-green, main `c40c1d8`)

- **Second Brain (WO-P1-052)**: plan file (SSoT) → settings `brain_folders`/`brain_entry_files` → renderer `system_prompt` index injection (Index+Pull, no contents) → **Second Brain dialog** (global profile, A-Wiki defaults) → **materialize-on-start** (append-only, safe for validated configs; verified on a temp copy of the live instance).
- **SerenaDoc**: all 34 files read; durable implications in `docs/references/serena-fulldoc-implications.md` (chatgpt context = multi-project switching via activation prompt; onboarding context cost; dashboard port instability; serena-hooks; trusted-projects gate; slow per-language readiness; git staging side effects).
- **Usability overhaul (WO-P1-053)** from the user's 8 trial issues: tooltips everywhere + ONLINE/OFFLINE explained; quick-start 3-step hint bar; **in-app guide viewer**; Add/Assign in PROJECTS panel; scrollbars + wrapping rows + larger minsize; brain button สมอง + folder; **connector-aware Start** (root-caused: Start needed runtime setup; now the worker's Start routes to the matching CONNECTOR — works out of the box) + CONNECTOR column linking workers↔instances.

## Evidence

- Full suite **801 passed**; smoke `A-CONDUCTOR_SMOKE_OK projects=0 workers=3` on merged main.
- Real-machine: brain injection verified on temp copy (live untouched, idempotent).

## Session 5b addendum (WO-P1-054, PR #25)

New-user onboarding shipped: in-app **ตั้ง Tunnel ID** (paste-validate-save, confined write), CONNECTORS **TUNNEL** column, USER-GUIDE **เชื่อมต่อ AI แต่ละค่าย** section (ChatGPT/OpenAI/Claude/Codex/Grok/Antigravity + security note), clickable links in the in-app guide viewer. Full suite 808 passed.

## Next safe action (user picks)

(a) Retrial the app (`a-conductor` / installed Start Menu entry) — feedback loop; (b) rebuild+reinstall the exe with `scripts/build_portable.py` to refresh the installed copy; (c) Phase 2 backlog: MCP gateway enforcement, CONNECTORS rebind UI, onboarding warnings (memory presence), activation-prompt helper. New work order + reuse gate first.
