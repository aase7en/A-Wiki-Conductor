# A-Conductor — Current Work

Last updated: 2026-08-21 (session 4 end)

## Current phase

**Own-brand product shipped: setup.exe installer, icon, Start Menu, minimal no-shortcut UI, toggle settings (tools/languages/project) — installed and verified on this machine.**

## Session 4 summary (WO-P1-051, PRs #13-#17, all CI-green, main `ec16587`)

- **PR #13**: work order + recorded design decisions (brainstorm discipline; requirements user-specified).
- **PR #14**: user-facing "Serena" removed (panel → CONNECTORS etc.), credits + engine link only (README/USER-GUIDE); Ctrl+K palette + all shortcuts removed; **คู่มือ button** opens the bundled guide (dev + frozen resolution).
- **PR #15**: settings v2 — `project_path` pin + `enabled_languages` (24-language catalog incl. html/markdown; renders `ls_priorities`), PRAGMA-guarded additive store migration.
- **PR #16**: Config dialog v2 — CLI-styled toggle checklists: 21 tools ON/OFF, 24 languages ON/OFF, editable project path; advanced fields kept.
- **PR #17**: generated app icon (window + exe + installer), hardened `scripts/build_portable.py` (Defender-race-proof, exit-0 deterministic), `scripts/installer_main.py` → **A-Conductor-Setup.exe** per-user installer.

## Real-machine evidence

- Portable exe (13 MB, icon+guide bundled) `--smoke` PASS.
- Sandbox install → files/shortcuts/registry verified → sandbox uninstall clean.
- **Real install** at `%LOCALAPPDATA%\Programs\A-Conductor`: Start Menu ✓ Desktop ✓ Add/Remove "A-Conductor" ✓ → installed app `--smoke` PASS (exit 0).
- Known environment notes: automated runs of fresh unsigned exes are Defender-policy-blocked (interactive SmartScreen click-through works; documented in USER-GUIDE); one load-dependent local timing flake (never on CI).

## Final suite

787 passed, 0 failed (local); CI green on all PRs.

## Next safe action (user picks)

(a) Try the real app from Start Menu → feedback loop; (b) sign the exes (cert) to remove SmartScreen friction; (c) continue Phase 1 roadmap (materialize settings into worker SERENA_HOME at start; CONNECTORS project rebind UI). New work order + reuse gate first.
