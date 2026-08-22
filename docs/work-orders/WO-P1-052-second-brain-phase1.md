# WO-P1-052: Second Brain Phase 1 (Index+Pull Brain Gate)

Status: complete (closed 2026-08-22: all sub-steps shipped to main — brain_folders/global-brain UI live; see CURRENT-WORK history)
Lane/files: `src/a_conductor/worker_serena_settings.py`, `src/a_conductor/serena_config_store.py`, `src/a_conductor/desktop_ui.py`, `src/a_conductor/desktop_control.py`, `src/a_conductor/local_instances.py`, `src/a_conductor/__init__.py`, `tests/test_worker_serena_settings.py`, `tests/test_local_instances.py`, `tests/test_desktop_ui.py`, `docs/plans/2026-08-21-second-brain-phase1.md`, `docs/work-orders/WO-P1-052-second-brain-phase1.md`, `CURRENT-WORK.md`, `handoff.md`
Branch: chunk/p1-052-second-brain-docs (PR series)
Model tier: high

## Goal

Every agent connecting through a connector must be greeted by the A-Wiki brain (or another chosen folder): a Global Brain Profile selects 1-2 brain folders + must-read entry files; the generated engine config injects a compact `system_prompt` index (never file contents); every connector instance materializes the profile into its `serena-home` on start.

## Reuse classification

`EXTEND + WRAP`: extends the WO-P1-048 settings model/renderer/store and the WO-P1-050 orchestrator with the already-tested `apply_worker_serena_settings`; no new orchestration universe. A-Wiki remains the brain owner (PROJECT-PLAN §15-16); A-Conductor is only the injection/materialization point.

## Acceptance

- `WorkerSerenaSettings` gains validated `brain_folders` (≤2, absolute) and `brain_entry_files` (≤2).
- Renderer emits a `system_prompt` block containing the brain index + rules only — tests assert **no file contents** are embedded.
- Store migration adds both columns (PRAGMA-guarded ALTER); legacy DB round-trips.
- Config dialog has a minimal SECOND BRAIN section editing the `global-brain` profile (defaults offered: A-Wiki + AGENTS.md + wiki/context/wiki-overview.md).
- `LocalInstanceOrchestrator.start()` applies the global profile to the instance serena-home before launching the validated start script (applier injectable; confined).
- Real verification on a temp copy of a real instance; live instances untouched by tests.

## Micro-steps

- [x] 052-A plan file + this work order
- [ ] 052-B RED model/renderer/store tests
- [ ] 052-C implement brain fields + system_prompt block + migration
- [ ] 052-D UI SECOND BRAIN section
- [ ] 052-E materialize-on-start wiring + temp-copy verification
- [ ] 052-F regression + close/push

## Forbidden

- No embedding of brain file contents into any prompt (Index+Pull only). No MCP gateway in this phase. No live-instance mutation in tests. No secrets.

## Checkpoint log

- [2026-08-21] Opened from main `7fc809d`; plan approved by user; plan file `docs/plans/2026-08-21-second-brain-phase1.md` is the record.
