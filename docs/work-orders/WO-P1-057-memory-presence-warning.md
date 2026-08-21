# WO-P1-057: Serena Onboarding / Memory Presence Warning

Status: complete
Lane/files: `src/a_conductor/memory_presence.py`, `src/a_conductor/desktop_ui.py`, `src/a_conductor/__init__.py`, `tests/test_memory_presence.py`, `tests/test_desktop_ui.py`, `docs/work-orders/WO-P1-057-memory-presence-warning.md`, `CURRENT-WORK.md`, `handoff.md`
Branch: chunk/p1-057-memory-presence
Model tier: high

## Goal (approved scope, CURRENT-WORK 2026-08-22)

Read-only warning for the selected project: detect Serena memory presence under `<project>/.serena/memories/`, explain that Serena onboarding triggers when no memories exist, and nudge the user to start a new AI conversation after onboarding. Grounding: `docs/references/serena-fulldoc-implications.md` (onboarding fires exactly when a project has no memories; it floods context — start a NEW conversation afterwards; `memory_maintenance` is seeded before any real memory).

## Design

- Pure read-only helper `inspect_memory_presence(project_root)` → `MemoryPresence(state, total_files, maintenance_only)`:
  - `NO_PROJECT` (root missing), `NO_MEMORIES` (`.serena/memories` missing), `EMPTY` (dir exists, no files),
    `MAINTENANCE_ONLY` (only the auto-seeded `memory_maintenance` file → onboarding not yet run),
    `HAS_MEMORIES` (usable memories present).
- UI: a single status line in the PROJECTS panel footer reflecting the *selected* project:
  - HAS_MEMORIES → "สมองโปรเจกต์: พร้อม (N ไฟล์)"
  - otherwise → "ยังไม่มีความจำ — onboarding จะทำงานเมื่อ agent เข้าโปรเจกต์ครั้งแรก · หลังจบให้เริ่มบทสนทนาใหม่"
- No new store, no mutation of the target project, read-only filesystem checks only.

## Acceptance

- Helper: all five states covered by deterministic tmp-dir tests; read-only (no writes).
- UI: selecting a project updates the label; no selection → neutral default; refresh keeps it correct.
- Full suite + CI green; PR merged.

## Forbidden

- No writing into the target project. No new memory DB. No A-Wiki duplication. No MCP gateway work.

## Checkpoint log

- [2026-08-22] Opened from main `2aca60c` (after PR #27 merge); WO-056 closed with evidence.
- [2026-08-22] Delivered via PR #28 (CI SUCCESS re-verified, merged `d2d8970`): helper 6/6 tests, UI selection test, full suite 819 passed. Debug loop: Tk `selection_set` adds rather than replaces selection — test now clears first (matches real click semantics).
