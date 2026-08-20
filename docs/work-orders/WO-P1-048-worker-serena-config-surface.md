# WO-P1-048: Per-Worker Serena Configuration Surface

Status: in_progress
Lane/files: `src/a_conductor/worker_serena_settings.py`, `src/a_conductor/serena_config_store.py`, `src/a_conductor/desktop_ui.py`, `src/a_conductor/desktop_control.py`, `src/a_conductor/__init__.py`, `tests/test_worker_serena_settings.py`, `tests/test_serena_config_store.py`, `tests/test_desktop_ui.py`, `docs/work-orders/WO-P1-048-worker-serena-config-surface.md`, `PROJECT-PLAN.md`, `CURRENT-WORK.md`, `handoff.md`
Branch: chunk/p1-048-config-surface-docs (PR series)
Model tier: high

## Goal

Deliver the per-worker Serena configuration surface recorded in PROJECT-PLAN §7 (user requirement 2026-08-21): edit language backend, project binding, tool enable/disable, modes, and tool timeout through the Conductor desktop UI; values materialize into the worker's isolated `SERENA_HOME/serena_config.yml` and apply on worker restart. No manual YAML editing in normal operation.

## Reuse classification

`EXTEND + WRAP`: reuses `SQLiteSerenaConfigStore` (persistence), the materializer's atomic-write/confinement patterns, `SerenaProjectBinding` (project identity), and the existing Tk desktop shell/theme. Serena remains the config consumer; Conductor owns generation. No new orchestration universe.

## Design (operations-console grammar × developer-platform recipe × minimal profile)

- Typed settings model `WorkerSerenaSettings`: `language_backend` (LSP/JetBrains), `excluded_tools`, `included_optional_tools`, `fixed_tools` (mutually exclusive with the other tool lists per Serena semantics), `base_modes`, `tool_timeout`, bound `worker_id`. Strict validation, no silent defaults for invalid input.
- Full-file renderer: generates the complete `serena_config.yml` from a Conductor-owned baseline (matching the validated instance configs) with settings injected — deterministic, diff-able, reviewable.
- Confined applier: writes only under the configured instances root for that worker (`<root>/<worker>/serena-home/serena_config.yml`), atomic replace; refuses traversal outside the root.
- Persistence: additive `save/get worker settings` on `SQLiteSerenaConfigStore`.
- Desktop UI: a CLI-minimal "Worker Config" panel — select worker, edit fields, Save validates + persists; status line states values apply on next worker start. Follows §6 style rules (monospace values, semantic status colors, no decoration).

## Acceptance

- Settings round-trip store→model→renderer survives with identical values.
- Renderer output contains exactly the configured values (line-asserted) and stays valid YAML shape for the bounded key set.
- `fixed_tools` combined with excluded/included tools is rejected (Serena rule).
- Applier confines writes under the worker serena-home root; traversal attempts fail closed.
- Desktop panel: save with valid values persists; invalid values show error code and persist nothing.
- Full suite + CI green on every PR in the series.

## Forbidden

- No live worker mutation while running (config applies on restart only).
- No secrets/tunnel IDs in settings or UI.
- No cloning of the Serena dashboard; bounded subset only.
- No real Serena launch in tests.

## Micro-steps

- [x] 048-A requirements + design + this work order (user requirement recorded 2026-08-21)
- [x] 048-B RED settings model/renderer/applier tests
- [x] 048-C implement model + renderer + confined applier
- [ ] 048-D store integration (save/get settings) + tests
- [ ] 048-E desktop UI panel + control service wiring + tests
- [ ] 048-F regression + close/commit/push

## Checkpoint log

- [2026-08-21] Opened on branch chunk/p1-048-config-surface-docs; baseline main `ff2a06b`.
- [2026-08-21] 048-B/C complete on branch chunk/p1-048b-settings-model: 11/11 settings tests green (RED first: ModuleNotFoundError); bugfix loop fixed empty-list YAML spacing. Full suite 760 passed. Evidence: model validation (worker-id pattern, tool/mode identifier rules, FIXED_TOOLS_EXCLUSivity, timeout bounds), full-file renderer with line-asserted output, confined atomic applier under `<instances_root>/<worker>/serena-home/`.
