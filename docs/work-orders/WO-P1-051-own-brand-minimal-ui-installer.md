# WO-P1-051: Own Brand, Minimal UI, Language/Tool Toggles, Setup Installer

Status: complete
Lane/files: `src/a_conductor/desktop_ui.py`, `src/a_conductor/desktop_app.py`, `src/a_conductor/worker_serena_settings.py`, `src/a_conductor/serena_config_store.py`, `src/a_conductor/__init__.py`, `assets/a-conductor.ico`, `installer.cfg`, `tests/*`, `docs/USER-GUIDE.md`, `README.md`, `docs/work-orders/WO-P1-051-own-brand-minimal-ui-installer.md`, `CURRENT-WORK.md`, `handoff.md`
Branch: PR series from main `1f28a42`
Model tier: high

## Goal (user, 2026-08-21)

Ship A-Conductor as the user's own product: setup.exe with icon + Start Menu; remove the word "Serena" from everything user-facing (credits + reference link only); ultra-minimal lightweight UI with NO keyboard shortcuts; a built-in guide button; settings toggles for active project, tools enable/disable, and programming languages (add/remove, e.g. html, markdown) in a CLI-styled dialog covering what the Serena dashboard exposes.

## Design decisions (recorded; user delegated autonomous execution)

1. **Branding**: every user-facing string drops "Serena" — panel `SERENA TUNNEL INSTANCES` → `CONNECTORS`; window title stays `A-Conductor`. Credits + reference link (https://github.com/oraios/serena) live in README, USER-GUIDE, and the app Help dialog. **Internal code identifiers (module/class names) keep their current names** — they are not user-visible, and renaming them is high-churn/zero-user-value; recorded as an explicit deferred option for the user.
2. **No shortcuts**: remove the Ctrl+K command palette + key bindings entirely; all actions are buttons. Fewer modes, anyone-can-use.
3. **Help**: a `คู่มือ` button opens the bundled USER-GUIDE (resource resolution: repo path in dev, frozen bundle dir when packaged); an About section credits the engine.
4. **Settings v2** on `WorkerSerenaSettings`: `project_path: str | None` (editable pin, rendered into `projects:`), `enabled_languages: tuple[str, ...]` (empty = auto-detect all; non-empty renders `ls_priorities` with priority 0 for every catalog language not enabled). Catalog constant holds common languages incl. html, markdown, python, typescript, javascript, css, json, yaml.
5. **Store migration**: `serena_worker_settings` gains `project_path TEXT` + `enabled_languages TEXT` (JSON) via additive `ALTER TABLE` guarded by PRAGMA column check — existing DBs upgrade in place, schema version unchanged (additive).
6. **Config dialog v2**: CLI-styled toggle lists — tools as `[x]/[ ]` ON/OFF rows from a common-tool catalog (plus existing custom names), languages as toggles from the catalog with free add/remove; project path editable. Values still apply on next start; invalid combos blocked as today.
7. **Icon**: generated minimal `assets/a-conductor.ico` (dark console plate + green/amber/red status bars — the control-console motif), used for the window and the installer; PyInstaller gets `--icon`.
8. **Installer**: `pynsist` builds a per-user NSIS `setup.exe` (no admin) with Start Menu shortcut, bundling `A-Conductor.exe` + USER-GUIDE. Verification: build artifacts checked (files present, sizes) and an extract-based content check; a silent install/uninstall round-trip is attempted only if it stays fully within per-user paths and is reversible.

## Micro-steps

- [x] 051-A this work order + design decisions
- [x] 051-B branding + minimal UI (remove palette/shortcuts, Help button, credits) + tests
- [x] 051-C settings v2 model + renderer + store migration + tests
- [x] 051-D config dialog v2 toggle lists + tests
- [x] 051-E icon + installer build + verification + docs
- [x] 051-F regression + close/push

## Forbidden

- No removal of engine credits/link. No admin-required installs. No new keyboard shortcuts. No real instance start/stop in automated tests. No secrets in installer.

## Checkpoint log

- [2026-08-21] Opened from main `1f28a42`.
- [2026-08-21] Delivered via PRs #13-#17 (CI-green, all merged; main `ec16587`). B: CONNECTORS rename + credits/link, palette/shortcuts removed, คู่มือ button (bundle-resolving). C: settings v2 + PRAGMA-guarded ALTER migration. D: dialog v2 CLI-styled toggle lists (21 tools, 24 languages) + editable project pin.
- [2026-08-21] E/F: generated icon wired to window; hardened `scripts/build_portable.py` (Defender races the cosmetic PE steps — timestamp rewrite opens the file 'wb' and a mid-write lock corrupts it; made best-effort → deterministic exit-0 builds); `A-Conductor-Setup.exe` per-user installer (files+Start Menu+Desktop+HKCU uninstall+self-contained uninstaller). Real-machine verification: sandbox install/uninstall clean; REAL install at `%LOCALAPPDATA%\Programs\A-Conductor` verified (shortcuts ✓ registry ✓) and installed app `--smoke` PASS. Automated execution of the fresh unsigned setup exe is policy-blocked by Defender (interactive SmartScreen click-through expected); logic verified via identical source-mode path. Final suite 787 passed, 0 failed.
