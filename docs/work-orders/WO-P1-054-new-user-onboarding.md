# WO-P1-054: New-User Onboarding — In-App Tunnel ID + Agent Connection Guide

Status: complete
Lane/files: `src/a_conductor/local_instances.py`, `src/a_conductor/desktop_control.py`, `src/a_conductor/desktop_ui.py`, `tests/test_local_instances.py`, `tests/test_desktop_ui.py`, `docs/USER-GUIDE.md`, `docs/work-orders/WO-P1-054-new-user-onboarding.md`
Branch: chunk/p1-054-onboarding-tunnel-id
Model tier: high

## Goal (user, 2026-08-21)

ผู้ใช้ใหม่ตั้งค่าได้จากในแอปทั้งหมด: เพิ่ม/แก้ Tunnel ID ของ connector, และมีคู่มือ/ลิงก์สอนไปขอ API Key + Tunnel ID ของแต่ละค่าย (ChatGPT/OpenAI, Claude, Antigravity, Codex, Grok ฯลฯ)

## Design

- `LocalInstance` += `tunnel_configured: bool` (discovery checks `config/tunnel-id.txt` against the validated `tunnel_[0-9a-f]{32}` format).
- Facade `set_instance_tunnel_id(name, tunnel_id)`: validate format, confine write to the instance's `config/tunnel-id.txt` (create dir), refuse instance outside the configured root; returns the written path. Activity-logged by the UI.
- UI: **ตั้ง Tunnel ID** button (CONNECTORS row) — dialog with paste field + live validation + save; CONNECTORS tree gains a **TUNNEL** column (✓ / -). Tooltip points new users to the in-app guide's connection section.
- USER-GUIDE gains "เชื่อมต่อ AI แต่ละค่าย": ChatGPT/OpenAI (MCPO + cloudflared + tunnel ID ที่ได้จากไหน), Claude (serena setup claude-code / claude mcp add), Codex, Grok, Antigravity one-liners + official doc links. The in-app guide viewer auto-links URLs (clickable → default browser).

## Acceptance

- Tunnel ID: format-validated, written confined, discovery flag correct, invalid input blocked with error surfaced, nothing written.
- TUNNEL column reflects reality; button gated on selection.
- Guide contains the connection section; viewer turns URLs into clickable links (unit-tested helper).
- Full suite + CI green.

## Forbidden

- No secret values logged or committed; tunnel ID stays inside the instance dir (untracked by git).

## Checkpoint log

- [2026-08-21] Opened from main `147d1f6`.
- [2026-08-21] Delivered on branch chunk/p1-054-onboarding-tunnel-id: discovery `tunnel_configured` flag (validated `tunnel_[0-9a-f]{32}`); facade `set_instance_tunnel_id` (format-validated, confined write to the instance config dir, INSTANCE_NOT_FOUND/OUTSIDE_ROOT guards); UI **ตั้ง Tunnel ID** button with live-validation dialog; CONNECTORS gains a **TUNNEL** column (Y/-); USER-GUIDE adds "เชื่อมต่อ AI แต่ละค่าย" (ChatGPT/OpenAI tunnel steps + MCPO/cloudflared, Claude/Codex/Grok/Antigravity one-liners, security note); in-app guide viewer auto-links URLs (clickable → browser). Debug loop notes: docstring header lost to an edit (em-dash syntax error), duplicate-instance-name test bug, event-simulation flakiness replaced by a directly callable validator, recursive button lookup + missing ttk import in tests. Full suite 808 passed, 0 failed.
