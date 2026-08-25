# WO-P1-066 — Inline per-row actions (EDIT column + empty-state Add rows)

Created: 2026-08-25
Owner: GLM 5.3 Max (user-authorized substitution while GPT-5.6 Sol is on weekly limit — user approved this exact feature and scope)
Status: IN_PROGRESS — implementation + tests on branch, PR open, awaiting CI + GPT visual acceptance
Base: `origin/main` `acd77b4c9fb04101557a12657779db50d5d543dd`
Branch: `feat/inline-row-buttons`

## User request (verbatim intent)

Add per-record guidance buttons inside the data columns themselves (NOT in the panel headers, NOT new bar buttons): when a column has no records, the last row becomes a `+ Add ...` row; when records exist, each row carries an Edit action next to its text. Goal: users who do not know the operating steps can follow the table itself.

## Design decisions (recorded for GPT review)

1. **Tk constraint:** Treeview/Listbox cannot embed real widgets per row. The stable, scroll-safe equivalent is a trailing **EDIT column** whose cell text is `Edit` (accent via row tag only for add-rows; per-cell coloring is impossible in ttk.Treeview — documented limitation).
2. **Empty-state:** synthetic last row `__add_project__` / `__add_worker__` / `__add_instance__` (tag `row-add`, accent foreground, label `+ Add Project/Worker/Connector`); clicking anywhere in it opens the existing add dialog; the row disappears as soon as one real record exists.
3. **Click routing:** one shared `_handle_inline_click(tree, row, column, edit_column, on_edit, on_add)` — add-row → on_add + `"break"`; EDIT cell → select row + on_edit + `"break"`; anything else → default Tk behavior. Event adapters per tree (`_on_worker_tree_click`, `_on_instance_tree_click`, `_on_project_tree_click`) gated by `identify_region`.
4. **PROJECTS converted from Listbox to single-column Treeview** (same visual slot/scrollbar; heading `PROJECT` + `EDIT`) because Listbox cannot host per-row actions at all. `selected_project_id()` now returns the selection iid directly (iid = project_id). Empty state shows `+ Add Project`.
5. **Edit semantics per column:**
   - WORKERS Edit → existing rename dialog.
   - CONNECTORS Edit → NEW unified `open_edit_instance_dialog` (alias + Tunnel ID + project path, prefilled; Tunnel left blank = keep current because no service getter exposes the stored ID; project change goes through the same `rebind_instance` "REBOUND" flow with restart note). Saves apply only changed fields in order tunnel → rebind → rename, then one `refresh_instances()`. Values are read before `destroy()` (DEFECT_LESSONS #2); submit button label "บันทึก/Save" to avoid colliding with e2e `find_widget` "Add" matching.
   - PROJECTS Edit → `assign_selected` (the guided next step). **No project-edit capability exists in the service layer** (no rename/unregister/repath); building one is a separate work order if the user wants it. Recorded as the main open design question for GPT.
6. **Existing bars/buttons untouched** — zero changes to workflow 9-button order, connector 11-button tuple, geometry contracts.
7. i18n: new keys `dlg.edit.connector.title/header/tunnel/project` (th/en; zh-CN falls back per policy).

## Overlap check for GPT-5.6 Sol (per user's standing instruction)

- `fix/gpu-context-ui-repaint` (tip `ffff853`) touches: `src/a_conductor/gpu_particle_logo.py`, `tests/test_gpu_particle_logo.py`, `docs/work-orders/WO-P1-063-...md`, `docs/agent-collab/AGENT_TASKS.md`.
- This branch touches: `src/a_conductor/desktop_ui.py`, `src/a_conductor/i18n.py`, `tests/test_inline_row_buttons.py` (new), `tests/test_desktop_ui.py`, `tests/test_ui_usability.py`, `tests/test_e2e_all_buttons.py`, `docs/work-orders/WO-P1-066-...md` (this file), `docs/agent-collab/AGENT_TASKS.md`, `DESIGN.md`.
- **No shared source files with GPT's branch.** Only additive `AGENT_TASKS.md` rows may conflict textually (trivial). Safe to merge in either order. `DESIGN.md` is not touched by GPT's branch.

## Evidence

- TDD: `tests/test_inline_row_buttons.py` written first (16 red), then implementation → **16 passed, 1 transient uv-Tk skip**.
- Updated Listbox→Treeview call sites in `test_desktop_ui.py` (4 sites), `test_ui_usability.py` (1), `test_e2e_all_buttons.py` (1).
- Focused suites re-run on this branch (results in the PR): desktop_ui, inline_row_buttons, ui_usability, i18n, blurbs_i18n, instance_monitor, wizard_ui, graceful_shutdown.

## For GPT to review later (visual authority stays with you)

1. Real-window look: EDIT column width/anchor in WORKERS + CONNECTORS; add-row accent visibility; PROJECTS tree heading vs old plain listbox (heading row is new vertical cost in the sidebar).
2. Decide whether per-row Edit for PROJECTS should stay `assign` or whether you want a real project-edit service capability (new WO).
3. `_handle_inline_click` returns `"break"` on action cells — confirm no regression in row selection feel during your E2E pass.

## Checklist

- [x] Failing tests first
- [x] Implementation (columns, add-rows, routing, unified connector editor, projects tree, i18n)
- [x] New tests green
- [x] Existing test call-sites updated
- [ ] Focused suites green
- [ ] PR CI green (3 OS)
- [ ] GPT visual acceptance after weekly limit resets
