# A-Conductor — Current Work

Last updated: 2026-08-22 (GLM 5.3, post WO-P1-059)

## Current phase

**WO-P1-059 complete: all three user decisions shipped + toggle-ification + upstream check. No open work orders.**

## Source-of-truth rule

Do **not** reconstruct task state from chat memory. Use: actual repo/GitHub state → CURRENT-WORK.md → handoff.md → active work order → PROJECT-PLAN/contracts.

## Verified completed work (WO-P1-059, PRs #30-#34, main `b914dfd`)

- **PR #30 (A)**: decisions recorded (gateway→backlog, rebind→approved, supervised ON→approved); `app_preferences` store; `open_job_control()` reads the supervised pref (default ON) — supervised mode's first production consumer.
- **PR #31 (B)**: **ตั้งค่า** header button + preferences dialog with the supervised switch (full inline teaching: what/gain/cost/recommendation).
- **PR #32 (C)**: **เปลี่ยนโปรเจกต์** button — surgical 2-file rebind (instance.ps1 `$ProjectPath` + template `--project`), automatic `.bak` backups, all guards, restart notice.
- **PR #33 (D)**: `config_blurbs` module — Thai one-liners for every engine tool (danger level), every language (install quirks), both backends, every field, mode names. Config dialog: every checkbox carries a hover tooltip; every field has a muted explanation line + tooltip; backend combobox shows a live effect blurb. Coverage test guarantees 100% catalog coverage.
- **PR #34 (E)**: **เช็คอัปเดท engine** button — read-only GitHub upstream check (first network egress), themed dialog with tag/SHA/date + clickable link, logged to ACTIVITY.

## Full suite at close

838 passed, 0 failed.

## Next safe action (user picks)

(a) Rebuild + reinstall the exe to pick up PRs #18-#34 (installed copy is very stale now; ESET will prompt on first interactive launch); (b) trial the new UI surfaces (ตั้งค่า / เปลี่ยนโปรเจกต์ / เช็คอัปเดท / hover everything in Config); (c) next §13 milestone. Open a new work order + reuse gate before implementation.

## Mandatory boundaries

- MCP gateway enforcement stays `DECISION_REQUIRED` (backlog).
- A-Wiki remains brain authority. No machine-wide env changes.

## Escalation rule

GLM 5.3 owns routine implementation, TDD, regression, docs, PR/CI, merge. Escalate to GPT-5.6 Sol UltraHigh only for genuinely hard cross-cutting defects/architecture ambiguity, after checkpointing state.
