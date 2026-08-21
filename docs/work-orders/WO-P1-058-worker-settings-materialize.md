# WO-P1-058: Materialize Per-Worker Engine Settings on Worker Start

Status: in_progress
Lane/files: `src/a_conductor/desktop_control.py`, `tests/test_desktop_control.py`, `docs/work-orders/WO-P1-058-worker-settings-materialize.md`, `CURRENT-WORK.md`, `handoff.md`
Branch: chunk/p1-058-worker-settings-materialize
Model tier: high

## Goal (user pick (ค), 2026-08-22)

The worker Config dialog's saved settings (language backend, tools, languages, timeout, project pin, brain) must actually land in the worker's `SERENA_HOME/serena_config.yml` when that worker starts — closing the last settings-materialization gap (connectors already get the brain via WO-P1-052; the worker lifecycle path gets nothing today).

## Design

- Facade `apply_worker_settings_to_home(worker_id) -> str` (result codes):
  - `SKIPPED_NO_SETTINGS` — no saved WorkerSerenaSettings
  - `SKIPPED_NOT_CONFIGURED` — no SerenaWorkerConfig (runtime setup never done)
  - `SKIPPED_TARGET_UNSAFE` — resolved serena_home not under its configured instance_root (fail closed)
  - `APPLIED` — rendered config written atomically to `<serena_home>/serena_config.yml`
- Project pin fallback: `settings.project_path` if set, else the worker's assigned project root from the control-center snapshot, else none (`projects: []`).
- `start_worker()` calls the applier **before** lifecycle START, best-effort: failures are returned/logged, never block the start (settings are an advisory layer like the brain).
- Reuses the WO-P1-048 renderer (which already includes the brain block); no new store, no engine internals.

## Acceptance

- Facade tests (real SQLite stores + tmp dirs + fake control-center/lifecycle): APPLIED writes the file with expected keys; all skip codes; unsafe target fails closed; start_worker invokes the applier before lifecycle and still returns its result on applier failure.
- Full suite + CI green; PR merged.

## Forbidden

- No writes outside the configured serena_home. No blocking of worker start on settings failures. No A-Wiki duplication.

## Checkpoint log

- [2026-08-22] Opened from main `cad4a32` (after WO-057 close + SSoT checkpoint).
