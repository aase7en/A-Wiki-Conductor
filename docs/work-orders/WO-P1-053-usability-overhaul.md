# WO-P1-053: Usability Overhaul (user trial feedback, 8 items)

Status: in_progress
Lane/files: `src/a_conductor/desktop_ui.py`, `src/a_conductor/desktop_control.py`, `src/a_conductor/desktop_app.py`, `src/a_conductor/__init__.py`, `tests/test_desktop_ui.py`, `docs/references/serena-fulldoc-implications.md`, `docs/USER-GUIDE.md`, `docs/work-orders/WO-P1-053-usability-overhaul.md`, `CURRENT-WORK.md`, `handoff.md`
Branch: chunk/p1-053-ux-overhaul-docs (PR series)
Model tier: high

## Goal (user trial, 2026-08-21 — verbatim issues)

1. Projects box: no scrolling; Add/Assign buttons should live with the Projects panel (they move things INTO workers).
2. After assigning a project to a worker, Start is disabled — why?
3. CONNECTORS (instances) names don't relate to worker paths — confusing.
4. Hover tooltips for every button + short beginner step-guide in the UI.
5. Guide must open IN-APP (currently opens external editor).
6. What does ONLINE mean; show/explain OFFLINE.
7. Narrow windows: buttons overflow; need scroll/responsive behavior.
8. More minimal (CLI-agent feel, prettier); keep/feature the brain-folder add.

## Root-cause analysis (from trial + SerenaDoc)

- (2) Worker Start requires completed Runtime Setup (readiness gate) which the user never ran — AND the user's real intent is starting their tunnel connectors. Fix: when the assigned project matches a discovered connector instance's project path, Start routes to that connector (works out of the box); otherwise tooltip explains Setup requirement.
- (3) Add a CONNECTOR column to the worker table showing the matching instance name (or "-").
- (6) ONLINE = local control DB reachable (snapshot.online); tooltip + guide entry.
- (5) Built-in guide viewer (monospace, scrollable) replaces external-file default; external open stays as a button inside the viewer.
- Docs grounding: `docs/references/serena-fulldoc-implications.md` (chatgpt context is multi-project; activation prompt; onboarding context cost).

## Acceptance

- Projects panel: y-scrollbar; Add Project + Assign buttons live inside the Projects panel; Release stays in Workers.
- Worker Start enabled when either lifecycle-ready OR a connector matches the assigned project; start routes accordingly; tooltip explains the active path.
- Worker table gains a CONNECTOR column with matching instance name.
- Tooltip helper on all buttons + panels + ONLINE indicator; hint bar with 3-step quick start.
- คู่มือ opens an in-app viewer (scrollable, monospace) with a secondary "เปิดไฟล์ภายนอก" button.
- Action rows wrap on narrow widths; minsize adjusted; lists scrollable; brain button labeled clearly (สมอง) with tooltip.
- Full suite + CI green per PR; real-app smoke check.

## Micro-steps

- [x] 053-A SerenaDoc implications reference + this work order
- [ ] 053-B UI pass 1: tooltips + hint bar + in-app guide + button placement + scrollbars + wrapping
- [ ] 053-C UI pass 2: connector-aware Start + CONNECTOR column (+ facade support) 
- [ ] 053-D regression + real smoke + close/push

## Forbidden

- No keyboard shortcuts (user rule). No engine internals beyond documented config surface. No live-instance mutation in tests.

## Checkpoint log

- [2026-08-21] Opened from main `cf28606` (WO-P1-052 complete: brain settings → renderer → UI → materialize-on-start, all merged PRs #18-#21).
