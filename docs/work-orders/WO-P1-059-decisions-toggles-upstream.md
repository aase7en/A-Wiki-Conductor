# WO-P1-059: Decision Outcomes + Toggle UI + Upstream Check

Status: in_progress
Lane/files: `src/a_conductor/serena_config_store.py`, `src/a_conductor/desktop_control.py`, `src/a_conductor/desktop_ui.py`, `src/a_conductor/local_instances.py`, `src/a_conductor/upstream_check.py`, `tests/*`, `docs/work-orders/WO-P1-059-decisions-toggles-upstream.md`, `CURRENT-WORK.md`, `handoff.md`
Branch: PR series from main `b148dee`
Model tier: high

## User decisions (2026-08-22)

- **ข.1 MCP Gateway → DEFERRED**: recorded as a backlog idea (large scope); revisit as its own WO + ADR when chosen.
- **ข.2 CONNECTORS Rebind → APPROVED** (PR-C).
- **ข.3 Supervised default ON + UI switch → APPROVED** (PR-A/B).
- New asks: toggle/checkbox-style config with inline explanations everywhere (PR-D); upstream engine update-check button (PR-E).

## PR series

- **PR-A** — decisions recorded; `app_preferences` key/value store (PRAGMA-guarded); facade `open_job_control()` reading the `supervised` preference (default ON) — supervised mode gains its first production consumer.
- **PR-B** — "ตั้งค่า" preferences dialog (header button) with the supervised switch + 3-line explanation; persists immediately.
- **PR-C** — `rebind_instance_project()`: surgical rewrite of `instance.ps1` `$ProjectPath` + profile template `--project` (forward-slash) + serena_config `projects:` line; automatic `.bak` backups of both files; confinement (instance under root, new path absolute + existing); idempotent; UI button with registered-projects dropdown + free path + restart notice. (Default safety option chosen in absence of user answer; changeable later.)
- **PR-D** — toggle-ification: language backend → 2-option toggles with blurbs; base_modes → checkbox grid with per-mode one-liners; tooltips (`_attach_tip`) + short gray explanation lines on every field in Config/Runtime-Setup/Brain dialogs; numeric fields stay entries but gain explanations.
- **PR-E** — upstream check button (CONNECTORS row): read-only GET `api.github.com/repos/oraios/serena` `/releases/latest` + `/commits/{default_branch}`; shows tag/date/short-sha + clickable link; logs to ACTIVITY; injectable fetcher; explicit note: first network egress of the app (public, unauthenticated, read-only).

## Acceptance

- Preferences persist across app restarts; `open_job_control` honors the switch; default supervised=ON.
- Rebind: correct 2-file rewrite + backups + idempotence + fail-closed guards (tests on real-format fake trees).
- Every dialog field carries a tooltip and/or one-line explanation (test-verified checklist).
- Upstream dialog renders fetched data; network failure shows a clear Thai message; no DB writes.
- Full suite + CI green per PR.

## Forbidden

- No gateway implementation. No writing outside instance dirs / pref store. No credentials in network calls. No machine-wide env changes.

## Checkpoint log

- [2026-08-22] Opened from main `b148dee`; plan approved (plan mode); defaults recorded for the two unanswered questions (.bak+restart notice; show+link+log).
